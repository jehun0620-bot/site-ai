# -*- coding: utf-8 -*-
"""Read-only integrity comparison for caller-supplied legal-source payload bytes.

The expected digest and bytes are supplied by the caller. Equality proves only
that THOSE bytes match THAT declared digest. It does not prove independent
acquisition, official origin, an authentic original, legal validity, competent
authority, SITE applicability, or production admission. No files/network are read.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

from law_data.legal_source_registry import LegalSourceRecord
from law_data.legal_source_version_evidence_binding import (
    LegalSourceVersionEvidenceReference,
    bind_legal_source_version_evidence,
)

NOT_EVALUATED = "NOT_EVALUATED"
ALIGNED = "IDENTITY_ALIGNED_UNVERIFIED"


@dataclass(frozen=True, slots=True)
class LegalSourceOriginalPayloadIntegrity:
    """Immutable byte-integrity diagnostic, never an official-source attestation."""

    status: str
    binding_status: str
    source_key: tuple[str, str, str]
    version_key: tuple[str, str, str, str | None]
    reference_version_key: tuple[str, str, str, str | None]
    evidence_key: tuple[str, str, str]
    payload_byte_count: int | None
    computed_sha256: str | None
    declared_sha256: str | None
    digest_matches: bool | None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "binding_status": self.binding_status,
            "source_key": list(self.source_key),
            "version_key": list(self.version_key),
            "reference_version_key": list(self.reference_version_key),
            "evidence_key": list(self.evidence_key),
            "payload_byte_count": self.payload_byte_count,
            "computed_sha256": self.computed_sha256,
            "declared_sha256": self.declared_sha256,
            "digest_matches": self.digest_matches,
            "payload_identity_basis": "CALLER_SUPPLIED_BYTES_AND_DIGEST",
            "source_identity_basis": "CALLER_SUPPLIED_UNVERIFIED",
            "official_origin_decision": NOT_EVALUATED,
            "original_text_identity_decision": NOT_EVALUATED,
            "source_verification_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "legal_authority_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def inspect_legal_source_original_payload_integrity(
    record: LegalSourceRecord,
    reference: LegalSourceVersionEvidenceReference,
    payload: bytes | None,
    *,
    known_references: tuple[LegalSourceVersionEvidenceReference, ...] = (),
) -> LegalSourceOriginalPayloadIntegrity:
    """Re-check exact version/evidence identity before hashing actual bytes.

    ``payload`` MUST be the exact byte sequence independently furnished by the
    caller; do not decode, re-encode, strip, parse, or normalize it here.  Empty
    or missing payloads are unresolved. A caller-provided expected SHA-256 value
    is never an independent source of truth. ``known_references`` is only a
    local collision snapshot, NOT a global uniqueness check.

    A digest is computed only when the full existing binding is aligned, which
    also requires an evidence URI and a declared SHA-256. No upstream VERIFIED
    flags or downstream authorization flags are accepted or returned.
    """
    if payload is not None and not isinstance(payload, bytes):
        raise TypeError("payload must be bytes or None (not text, path, or mutable bytes)")

    # Never trust a caller-constructed Binding assessment in place of recomputing
    # the exact record/reference/known-references contract.
    binding = bind_legal_source_version_evidence(
        record, reference, known_references=known_references
    )
    if binding.status != ALIGNED:
        status = "EVIDENCE_BINDING_REJECTED"
        actual_digest = None
        matches = None
        byte_count = None
    elif not payload:
        status = "PAYLOAD_MISSING"
        actual_digest = None
        matches = None
        byte_count = 0 if payload is not None else None
    else:
        actual_digest = hashlib.sha256(payload).hexdigest()
        # On an ALIGNED binding the declared hash is guaranteed to be present
        # and normalized to lowercase by LegalSourceVersionEvidenceReference.
        matches = hmac.compare_digest(actual_digest, reference.declared_sha256)
        status = (
            "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN"
            if matches else "CONTENT_DIGEST_MISMATCH"
        )
        byte_count = len(payload)

    return LegalSourceOriginalPayloadIntegrity(
        status=status,
        binding_status=binding.status,
        source_key=binding.source_key,
        version_key=binding.version_key,
        reference_version_key=binding.reference_version_key,
        evidence_key=binding.evidence_key,
        payload_byte_count=byte_count,
        computed_sha256=actual_digest,
        declared_sha256=reference.declared_sha256,
        digest_matches=matches,
    )
