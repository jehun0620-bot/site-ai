# -*- coding: utf-8 -*-
"""Offline consistency inspection of a CLAIMED legal-source acquisition receipt.

Neither the receipt nor its timestamps/URLs/headers are authenticated. This
module rechecks existing source/version binding and actual-byte integrity, then
compares *caller-supplied* acquisition metadata. No network, file access,
official-origin attestation, legal determination, SITE decision or promotion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from law_data.legal_source_registry import LegalSourceRecord
from law_data.legal_source_version_evidence_binding import LegalSourceVersionEvidenceReference
from law_data.legal_source_original_payload_integrity import (
    inspect_legal_source_original_payload_integrity,
)

NOT_EVALUATED = "NOT_EVALUATED"
_HEX_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")
_UTC_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")


def _required(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_text(name: str, value: object) -> str | None:
    return None if value is None else _required(name, value)


def _optional_url(name: str, value: object) -> str | None:
    if isinstance(value, str) and any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{name} cannot contain control characters")
    url = _optional_text(name, value)
    if url is None:
        return None
    parts = urlsplit(url)
    if (parts.scheme not in {"http", "https"} or not parts.hostname
            or parts.username is not None or parts.password is not None):
        raise ValueError(f"{name} must be an absolute HTTP(S) URL without credentials")
    return url


@dataclass(frozen=True, slots=True)
class LegalSourceAcquisitionReceipt:
    """Descriptive receipt CLAIM, never evidence of a witnessed fetch.

    The acquisition ID and UTC timestamp can also be invented by a caller.
    The identity fields must match the exact source version and evidence ID.
    """

    source_system: str
    source_namespace: str
    source_id: str
    version_id: str | None
    evidence_id: str
    requested_url: str | None = None
    final_url: str | None = None
    http_status: int | None = None
    content_type: str | None = None
    response_byte_count: int | None = None
    response_sha256: str | None = None
    acquisition_id: str | None = None
    observed_at_utc: str | None = None

    def __post_init__(self) -> None:
        for name in ("source_system", "source_namespace", "source_id", "evidence_id"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        for name in ("version_id", "content_type", "acquisition_id"):
            object.__setattr__(self, name, _optional_text(name, getattr(self, name)))
        for name in ("requested_url", "final_url"):
            object.__setattr__(self, name, _optional_url(name, getattr(self, name)))
        if self.http_status is not None and (
            type(self.http_status) is not int or not 100 <= self.http_status <= 599
        ):
            raise ValueError("http_status must be an integer HTTP code or None")
        if self.response_byte_count is not None and (
            type(self.response_byte_count) is not int or self.response_byte_count < 0
        ):
            raise ValueError("response_byte_count must be a nonnegative integer or None")
        digest = _optional_text("response_sha256", self.response_sha256)
        if digest is not None and _HEX_SHA256.fullmatch(digest) is None:
            raise ValueError("response_sha256 must be a 64-digit hexadecimal digest")
        object.__setattr__(self, "response_sha256", digest.lower() if digest else None)
        stamp = _optional_text("observed_at_utc", self.observed_at_utc)
        if stamp is not None:
            if _UTC_TIMESTAMP.fullmatch(stamp) is None:
                raise ValueError("observed_at_utc must be a UTC YYYY-MM-DDTHH:MM:SSZ value")
            try:
                datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("observed_at_utc is not a valid calendar time") from exc
        object.__setattr__(self, "observed_at_utc", stamp)

    @property
    def source_key(self) -> tuple[str, str, str]:
        return self.source_system, self.source_namespace, self.source_id

    @property
    def version_key(self) -> tuple[str, str, str, str | None]:
        return (*self.source_key, self.version_id)

    @property
    def evidence_key(self) -> tuple[str, str, str]:
        return self.source_system, self.source_namespace, self.evidence_id


@dataclass(frozen=True, slots=True)
class LegalSourceAcquisitionReceiptInspection:
    """Receipt/byte consistency diagnostic; nothing is officially VERIFIED."""

    status: str
    integrity_status: str
    binding_status: str
    version_key: tuple[str, str, str, str | None]
    receipt_version_key: tuple[str, str, str, str | None]
    evidence_key: tuple[str, str, str]
    receipt_identity_aligned: bool
    receipt_byte_count_matches: bool | None
    receipt_digest_matches: bool | None
    missing_receipt_fields: tuple[str, ...]
    url_relation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "integrity_status": self.integrity_status,
            "binding_status": self.binding_status,
            "version_key": list(self.version_key),
            "receipt_version_key": list(self.receipt_version_key),
            "evidence_key": list(self.evidence_key),
            "receipt_identity_aligned": self.receipt_identity_aligned,
            "receipt_byte_count_matches": self.receipt_byte_count_matches,
            "receipt_digest_matches": self.receipt_digest_matches,
            "missing_receipt_fields": list(self.missing_receipt_fields),
            "url_relation": self.url_relation,
            "receipt_identity_basis": "CALLER_SUPPLIED_UNATTESTED",
            "acquisition_authenticity_decision": NOT_EVALUATED,
            "official_origin_decision": NOT_EVALUATED,
            "original_text_identity_decision": NOT_EVALUATED,
            "source_verification_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "legal_authority_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def inspect_legal_source_acquisition_receipt(
    record: LegalSourceRecord,
    reference: LegalSourceVersionEvidenceReference,
    payload: bytes | None,
    receipt: LegalSourceAcquisitionReceipt,
    *,
    known_references: tuple[LegalSourceVersionEvidenceReference, ...] = (),
) -> LegalSourceAcquisitionReceiptInspection:
    """Recompute byte integrity and compare it to a caller-supplied receipt.

    A clean claim is RECEIPT_CONSISTENT_UNVERIFIED_ORIGIN, *never* evidence
    that a fetch actually occurred, that TLS was valid, or that the service was
    official. Redirected responses and HTML documents need separate review.
    """
    if not isinstance(receipt, LegalSourceAcquisitionReceipt):
        raise TypeError("receipt must be LegalSourceAcquisitionReceipt")
    integrity = inspect_legal_source_original_payload_integrity(
        record, reference, payload, known_references=known_references
    )
    aligned = (
        receipt.version_id is not None
        and receipt.source_key == record.source_key == reference.source_key
        and receipt.version_key == record.version_key == reference.version_key
        and receipt.evidence_key == reference.evidence_key
    )
    required = (
        "requested_url", "final_url", "http_status", "content_type",
        "response_byte_count", "response_sha256", "acquisition_id", "observed_at_utc",
    )
    missing = tuple(name for name in required if getattr(receipt, name) is None)
    byte_match = (
        receipt.response_byte_count == integrity.payload_byte_count
        if receipt.response_byte_count is not None and integrity.payload_byte_count is not None
        else None
    )
    hash_match = (
        receipt.response_sha256 == integrity.computed_sha256
        if receipt.response_sha256 is not None and integrity.computed_sha256 is not None
        else None
    )
    relation = (
        "NOT_COMPARABLE" if receipt.requested_url is None or receipt.final_url is None
        else "UNCHANGED_DECLARED" if receipt.requested_url == receipt.final_url
        else "CHANGED_UNVERIFIED"
    )
    media_type = (receipt.content_type or "").split(";", 1)[0].strip().lower()
    sample = (payload or b"").lstrip()[:64].lower() if isinstance(payload, bytes) else b""
    html_like = sample.startswith((b"<!doctype html", b"<html", b"<head", b"<body"))

    if integrity.status != "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN":
        status = "UPSTREAM_INTEGRITY_UNRESOLVED"
    elif not aligned:
        status = "RECEIPT_IDENTITY_MISMATCH"
    elif missing:
        status = "RECEIPT_INCOMPLETE"
    elif receipt.http_status != 200:
        status = "RECEIPT_HTTP_STATUS_NOT_200"
    elif urlsplit(receipt.requested_url).scheme != "https" or urlsplit(receipt.final_url).scheme != "https":
        status = "RECEIPT_NON_HTTPS_URL_REVIEW_REQUIRED"
    elif receipt.requested_url != reference.evidence_uri:
        status = "RECEIPT_REQUEST_URL_MISMATCH"
    elif receipt.final_url != receipt.requested_url:
        status = "RECEIPT_REDIRECT_REVIEW_REQUIRED"
    elif byte_match is not True:
        status = "RECEIPT_BYTE_COUNT_MISMATCH"
    elif hash_match is not True:
        status = "RECEIPT_DIGEST_MISMATCH"
    elif media_type in {"text/html", "application/xhtml+xml"} or html_like:
        status = "RECEIPT_DOCUMENT_FORMAT_REVIEW_REQUIRED"
    else:
        status = "RECEIPT_CONSISTENT_UNVERIFIED_ORIGIN"

    return LegalSourceAcquisitionReceiptInspection(
        status=status,
        integrity_status=integrity.status,
        binding_status=integrity.binding_status,
        version_key=integrity.version_key,
        receipt_version_key=receipt.version_key,
        evidence_key=integrity.evidence_key,
        receipt_identity_aligned=aligned,
        receipt_byte_count_matches=byte_match,
        receipt_digest_matches=hash_match,
        missing_receipt_fields=missing,
        url_relation=relation,
    )
