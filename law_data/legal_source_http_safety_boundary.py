# -*- coding: utf-8 -*-
"""Isolated MOLEG DRF HTTP acquisition boundary with credential-free outcomes.

The OC credential is used *only* in the outgoing request. This module must
never log/return request URLs, Request/Response objects, raw exceptions or
tracebacks. The explicit public_record() is safe to serialize; the outcome
object itself is INTERNAL because success may contain arbitrary raw bytes.

No official-origin verification, legal applicability, receipt attestation,
production permission or integration with the SITE/Rule Engine is performed.
The HTTP stack, proxies and external infrastructure may have their own logs;
this module does not attest that those environments are credential-safe.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import requests

from law_data.legal_source_public_request_descriptor import (
    ENDPOINT,
    LegalSourcePublicRequestDescriptor,
)


SUCCESS = "HTTP_200_RECEIVED_UNVERIFIED_ORIGIN"
HTTP_REJECTED = "HTTP_STATUS_REJECTED"
REDIRECT_BLOCKED = "REDIRECT_BLOCKED"
TIMEOUT = "TRANSPORT_TIMEOUT"
CONNECTION_FAILED = "TRANSPORT_CONNECTION_FAILED"
TLS_FAILED = "TLS_VALIDATION_FAILED"
TRANSPORT_FAILED = "TRANSPORT_FAILED"

_ALLOWED_STATUSES = frozenset((
    SUCCESS, HTTP_REJECTED, REDIRECT_BLOCKED,
    TIMEOUT, CONNECTION_FAILED, TLS_FAILED, TRANSPORT_FAILED,
))


@dataclass(frozen=True, slots=True)
class LegalSourceHttpFetchOutcome:
    """INTERNAL-only result; serialize ONLY public_record(), never asdict().

    The payload is intentionally absent from repr() and public_record(). Its
    bytes are for subsequent independent validation by trusted local code.
    Neither this result nor an HTTP 200 status proves official provenance.
    """

    descriptor: LegalSourcePublicRequestDescriptor
    status: str
    http_status: int | None = None
    payload: bytes | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.descriptor) is not LegalSourcePublicRequestDescriptor:
            raise ValueError("INVALID_DESCRIPTOR")
        if type(self.status) is not str or self.status not in _ALLOWED_STATUSES:
            raise ValueError("INVALID_OUTCOME_STATUS")
        if self.http_status is not None and (
            type(self.http_status) is not int
            or not 100 <= self.http_status <= 599
        ):
            raise ValueError("INVALID_HTTP_STATUS")
        if self.payload is not None and type(self.payload) is not bytes:
            raise ValueError("INVALID_PAYLOAD_TYPE")
        if self.status == SUCCESS:
            if self.http_status != 200 or self.payload is None:
                raise ValueError("INCONSISTENT_SUCCESS_OUTCOME")
        elif self.payload is not None:
            raise ValueError("PAYLOAD_FORBIDDEN_FOR_FAILURE")
        if self.status == HTTP_REJECTED and (
            self.http_status is None or self.http_status == 200
            or 300 <= self.http_status <= 399
        ):
            raise ValueError("INCONSISTENT_HTTP_REJECTION")
        if self.status == REDIRECT_BLOCKED and (
            self.http_status is not None
            and not 100 <= self.http_status <= 599
        ):
            raise ValueError("INCONSISTENT_REDIRECT_OUTCOME")
        # Transport failures do not report an HTTP response code. In contrast,
        # an already-followed redirect can be blocked with final HTTP 200.
        if self.status in (TIMEOUT, CONNECTION_FAILED, TLS_FAILED, TRANSPORT_FAILED):
            if self.http_status is not None:
                raise ValueError("INCONSISTENT_TRANSPORT_OUTCOME")

    def public_record(self) -> dict[str, object]:
        """Allowlisted diagnostic record; excludes raw body, URLs and errors."""
        return {
            "record_kind": "LEGAL_HTTP_FETCH_PUBLIC_DIAGNOSTIC_V1",
            "status": self.status,
            "http_status": self.http_status,
            "public_request": self.descriptor.to_dict(),
            "response_byte_count": len(self.payload) if self.payload is not None else None,
            "source_verification": "NOT_EVALUATED",
            "legal_applicability": "NOT_EVALUATED",
            "production_admission": "NOT_EVALUATED",
        }


def _validate_inputs(
    descriptor: object, credential: object, timeout_seconds: object,
) -> None:
    # Validation errors use fixed labels, never echo untrusted input.
    if type(descriptor) is not LegalSourcePublicRequestDescriptor:
        raise ValueError("INVALID_DESCRIPTOR")
    if type(credential) is not str or not credential.strip():
        raise ValueError("INVALID_CREDENTIAL")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in credential):
        raise ValueError("INVALID_CREDENTIAL")
    if type(timeout_seconds) not in (int, float):
        raise ValueError("INVALID_TIMEOUT")
    if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 120:
        raise ValueError("INVALID_TIMEOUT")


def fetch_legal_source_http(
    descriptor: LegalSourcePublicRequestDescriptor,
    credential: str,
    *,
    timeout_seconds: float = 30.0,
) -> LegalSourceHttpFetchOutcome:
    """GET one exact public descriptor with an internal OC credential.

    This function DOES perform a live HTTP request when called normally.
    Contract tests replace requests.get with a mock and never use a real key.

    Disables automatic redirects and TLS bypass. Never invokes
    raise_for_status() and never raises/returns a raw requests exception.
    Unexpected transport/response exceptions fail closed to a fixed status.
    """
    _validate_inputs(descriptor, credential, timeout_seconds)

    try:
        response = requests.get(
            ENDPOINT,
            params={**descriptor.public_parameters(), "OC": credential},
            timeout=timeout_seconds,
            allow_redirects=False,
            verify=True,
        )
        status_code = response.status_code
        if type(status_code) is not int or not 100 <= status_code <= 599:
            return LegalSourceHttpFetchOutcome(descriptor, TRANSPORT_FAILED)
        # A nonconforming adapter might return an already-followed redirect;
        # reject it even when its final response has status 200.
        if response.history or 300 <= status_code <= 399:
            return LegalSourceHttpFetchOutcome(
                descriptor, REDIRECT_BLOCKED, http_status=status_code,
            )
        if status_code != 200:
            return LegalSourceHttpFetchOutcome(
                descriptor, HTTP_REJECTED, http_status=status_code,
            )
        payload = response.content
        if type(payload) is not bytes:
            return LegalSourceHttpFetchOutcome(descriptor, TRANSPORT_FAILED)
        return LegalSourceHttpFetchOutcome(
            descriptor, SUCCESS, http_status=200, payload=payload,
        )
    except requests.exceptions.SSLError:
        return LegalSourceHttpFetchOutcome(descriptor, TLS_FAILED)
    except requests.exceptions.Timeout:
        return LegalSourceHttpFetchOutcome(descriptor, TIMEOUT)
    except requests.exceptions.ConnectionError:
        return LegalSourceHttpFetchOutcome(descriptor, CONNECTION_FAILED)
    except requests.exceptions.RequestException:
        return LegalSourceHttpFetchOutcome(descriptor, TRANSPORT_FAILED)
    except Exception:
        # Do not return or chain an exception. Its message/URL/context may
        # include OC; the fixed result is created without referring to it.
        return LegalSourceHttpFetchOutcome(descriptor, TRANSPORT_FAILED)
