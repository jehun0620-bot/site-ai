# -*- coding: ascii -*-
"""Explicit opt-in, in-memory LOCAL observation around the existing HTTP boundary.

The legacy fetch is not changed. No raw authenticated URL, Response object,
request, headers, credential or exception is accessed/retained here. A local
clock reading and local random event ID are NOT evidence of official source,
a witnessed remote fetch, legally effective text, or acquisition authenticity.
There is no receipt construction and no disk/network work except the ONE
existing fetch initiated only by an explicit enabled=True call.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from law_data.legal_source_http_safety_boundary import (
    SUCCESS, LegalSourceHttpFetchOutcome, fetch_legal_source_http,
)
from law_data.legal_source_public_request_descriptor import (
    LegalSourcePublicRequestDescriptor,
)

NOT_EVALUATED = "NOT_EVALUATED"
NOT_OBSERVED = "NOT_OBSERVED"
LOCAL_SUCCESS = "LOCAL_FETCH_RETURNED_SUCCESS_UNVERIFIED_ORIGIN"
LOCAL_NON_SUCCESS = "LOCAL_FETCH_RETURNED_NON_SUCCESS_UNVERIFIED_ORIGIN"
LOCAL_CLOCK_ANOMALY = "LOCAL_CLOCK_ORDER_UNRESOLVED"
_STATUSES = frozenset((LOCAL_SUCCESS, LOCAL_NON_SUCCESS, LOCAL_CLOCK_ANOMALY))
_SEAL = object()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class LegalSourceEflawLocalAcquisitionObservation:
    """PRIVATE in-memory metadata. Do NOT serialize; use public_record().

    http_outcome may contain raw private response bytes. The local UTC clock,
    event ID, and self-computed digest are not authenticated acquisitions.
    """
    http_outcome: LegalSourceHttpFetchOutcome = field(repr=False, compare=False)
    local_event_id: str = field(repr=False)
    local_started_at_utc: str = field(repr=False)
    local_finished_at_utc: str = field(repr=False)
    response_sha256: str | None = field(repr=False)
    response_byte_count: int | None
    status: str
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _SEAL:
            raise ValueError("DIRECT_LOCAL_OBSERVATION_CONSTRUCTION_FORBIDDEN")
        if type(self.http_outcome) is not LegalSourceHttpFetchOutcome:
            raise ValueError("INVALID_LOCAL_HTTP_OUTCOME")
        if self.http_outcome.descriptor.target != "eflaw":
            raise ValueError("EFLAW_ONLY")
        if type(self.local_event_id) is not str or len(self.local_event_id) != 32 or any(
            character not in "0123456789abcdef" for character in self.local_event_id
        ):
            raise ValueError("INVALID_LOCAL_EVENT_ID")
        try:
            start = datetime.fromisoformat(self.local_started_at_utc.replace("Z", "+00:00"))
            end = datetime.fromisoformat(self.local_finished_at_utc.replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError):
            raise ValueError("INVALID_LOCAL_TIMESTAMP") from None
        if (start.tzinfo is None or end.tzinfo is None
                or not self.local_started_at_utc.endswith("Z")
                or not self.local_finished_at_utc.endswith("Z")):
            raise ValueError("INVALID_LOCAL_TIMESTAMP")
        if self.status not in _STATUSES:
            raise ValueError("INVALID_LOCAL_OBSERVATION_STATUS")
        payload = self.http_outcome.payload
        expected_digest = hashlib.sha256(payload).hexdigest() if payload is not None else None
        expected_count = len(payload) if payload is not None else None
        if self.response_sha256 != expected_digest or self.response_byte_count != expected_count:
            raise ValueError("INCONSISTENT_LOCAL_BYTES")
        succeeded = (self.http_outcome.status == SUCCESS and self.http_outcome.http_status == 200
                     and type(payload) is bytes)
        expected_status = (
            LOCAL_CLOCK_ANOMALY if end < start
            else LOCAL_SUCCESS if succeeded else LOCAL_NON_SUCCESS
        )
        if self.status != expected_status:
            raise ValueError("INCONSISTENT_LOCAL_OBSERVATION_STATUS")

    def public_record(self) -> dict[str, str | int | bool | None]:
        """Bounded, credential-free diagnostic; NO event ID or timestamps."""
        return {
            "record_kind": "LEGAL_EFLAW_LOCAL_ACQUISITION_OBSERVATION_V1",
            "status": self.status,
            "http_status": self.http_outcome.http_status,
            "http_outcome_status": self.http_outcome.status,
            "response_byte_count": self.response_byte_count,
            "local_event_id_created": True,
            "local_clock_values_recorded": True,
            "response_digest_locally_computed": self.response_sha256 is not None,
            "response_content_type": NOT_OBSERVED,
            "final_response_url": NOT_OBSERVED,
            "actual_authenticated_request_url": NOT_OBSERVED,
            "local_clock_basis": "UNATTESTED_LOCAL_SYSTEM_CLOCK",
            "acquisition_authenticity_decision": NOT_EVALUATED,
            "official_origin_decision": NOT_EVALUATED,
            "source_verification_decision": NOT_EVALUATED,
            "original_text_identity_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "legal_authority_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def fetch_legal_source_eflaw_with_local_observation(
    descriptor: LegalSourcePublicRequestDescriptor,
    credential: str,
    *,
    enabled: bool = False,
    timeout_seconds: float = 30.0,
) -> LegalSourceEflawLocalAcquisitionObservation:
    """Explicit opt-in; at most one call through the legacy HTTP boundary.

    The existing transport revalidates credential and timeout. This wrapper
    must not inspect response.url/request/headers or fabricate receipt fields.
    Transport exceptions are handled by the existing HTTP boundary; only a
    local observation is added around its result, not an origin attestation.
    """
    if enabled is not True:
        raise ValueError("LOCAL_OBSERVATION_OPT_IN_REQUIRED")
    if type(descriptor) is not LegalSourcePublicRequestDescriptor or descriptor.target != "eflaw":
        raise ValueError("INVALID_EFLAW_DESCRIPTOR")
    start = _utc_iso()
    local_id = uuid4().hex
    outcome = fetch_legal_source_http(
        descriptor, credential, timeout_seconds=timeout_seconds,
    )
    end = _utc_iso()
    payload = outcome.payload
    digest = hashlib.sha256(payload).hexdigest() if payload is not None else None
    count = len(payload) if payload is not None else None
    # __post_init__ checks consistency; local-clock regression fails closed.
    clock_reversed = end < start
    status = (LOCAL_CLOCK_ANOMALY if clock_reversed else
              LOCAL_SUCCESS if outcome.status == SUCCESS else LOCAL_NON_SUCCESS)
    return LegalSourceEflawLocalAcquisitionObservation(
        outcome, local_id, start, end, digest, count, status, _seal=_SEAL,
    )
