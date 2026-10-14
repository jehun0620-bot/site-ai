# -*- coding: utf-8 -*-
"""Offline bridge: claimed HTTP outcome -> declared legal-source byte integrity.

The HTTP outcome, registry record, evidence reference, and expected SHA-256 are
caller-provided inputs. A matching digest proves only byte equality to the
DECLARED digest, not HTTP provenance, law validity, or SITE applicability.

No network, file access, HTTP retries, receipt construction, or promotion.
Never serialize an entire result object: use public_record() explicitly.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from law_data.legal_source_http_safety_boundary import (
    SUCCESS,
    LegalSourceHttpFetchOutcome,
)
from law_data.legal_source_original_payload_integrity import (
    LegalSourceOriginalPayloadIntegrity,
    inspect_legal_source_original_payload_integrity,
)
from law_data.legal_source_public_request_descriptor import (
    SOURCE_SYSTEM,
    LegalSourcePublicRequestDescriptor,
)
from law_data.legal_source_registry import LegalSourceRecord
from law_data.legal_source_version_evidence_binding import (
    LegalSourceVersionEvidenceReference,
)

HTTP_UNRESOLVED = "HTTP_UNRESOLVED"
REQUEST_SOURCE_MISMATCH = "REQUEST_SOURCE_MISMATCH"
REQUEST_VERSION_MISMATCH = "REQUEST_VERSION_MISMATCH"
REQUEST_SCOPE_MISMATCH = "REQUEST_SCOPE_MISMATCH"
INSPECTION_FAILED = "INTEGRITY_INSPECTION_FAILED"

# The remaining statuses come only from the existing inspection function:
# EVIDENCE_BINDING_REJECTED, PAYLOAD_MISSING,
# CONTENT_DIGEST_MISMATCH, CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN.
NOT_EVALUATED = "NOT_EVALUATED"
_UNRESOLVED_STATUSES = frozenset((
    HTTP_UNRESOLVED, REQUEST_SOURCE_MISMATCH, REQUEST_VERSION_MISMATCH,
    REQUEST_SCOPE_MISMATCH, INSPECTION_FAILED,
))
_INSPECTION_STATUSES = frozenset((
    "EVIDENCE_BINDING_REJECTED", "PAYLOAD_MISSING",
    "CONTENT_DIGEST_MISMATCH", "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN",
))
_BINDING_STATUSES = frozenset((
    "SOURCE_IDENTITY_MISMATCH", "VERSION_UNKNOWN", "VERSION_MISMATCH",
    "DECLARED_SCOPE_MISMATCH", "EVIDENCE_REFERENCE_COLLISION",
    "EVIDENCE_REFERENCE_INCOMPLETE", "IDENTITY_ALIGNED_UNVERIFIED",
))


@dataclass(frozen=True, slots=True)
class LegalSourceHttpIntegrityBridgeResult:
    """INTERNAL object. Do not call dataclasses.asdict() or serialize it.

    ``inspection`` is an independent recomputation, never a claimed status.
    It may contain untrusted source identifiers and digests, and is therefore
    deliberately excluded from both repr and the public diagnostic record.
    """

    status: str
    http_outcome: LegalSourceHttpFetchOutcome = field(repr=False, compare=False)
    inspection: LegalSourceOriginalPayloadIntegrity | None = field(
        default=None, repr=False, compare=False,
    )

    def __post_init__(self) -> None:
        # Construction cannot turn arbitrary caller strings into a public log.
        if type(self.http_outcome) is not LegalSourceHttpFetchOutcome:
            raise ValueError("INVALID_HTTP_OUTCOME")
        if self.inspection is None:
            if type(self.status) is not str or self.status not in _UNRESOLVED_STATUSES:
                raise ValueError("INVALID_BRIDGE_STATUS")
        else:
            if type(self.inspection) is not LegalSourceOriginalPayloadIntegrity:
                raise ValueError("INVALID_INSPECTION")
            if (type(self.status) is not str
                    or self.status not in _INSPECTION_STATUSES
                    or self.inspection.status != self.status
                    or self.inspection.binding_status not in _BINDING_STATUSES):
                raise ValueError("INVALID_INSPECTION_STATUS")
            if (self.inspection.payload_byte_count is not None
                    and (type(self.inspection.payload_byte_count) is not int
                         or self.inspection.payload_byte_count < 0)):
                raise ValueError("INVALID_INSPECTION_BYTE_COUNT")
            if (self.inspection.digest_matches is not None
                    and type(self.inspection.digest_matches) is not bool):
                raise ValueError("INVALID_INSPECTION_DIGEST_RESULT")

        # A diagnostic result must never claim digest success after an HTTP
        # failure. These checks enforce internally consistent *claims*, not
        # external proof of HTTP origin or independent source verification.
        http = self.http_outcome
        http_success = (
            http.status == SUCCESS
            and http.http_status == 200
            and type(http.payload) is bytes
        )
        if self.inspection is None:
            # The live inspector checks source/version/scope before HTTP status.
            # REQUEST_* therefore may legitimately precede an HTTP failure.
            if self.status == HTTP_UNRESOLVED and http_success:
                raise ValueError("INCONSISTENT_HTTP_BRIDGE_STATE")
            if self.status == INSPECTION_FAILED and not http_success:
                raise ValueError("INCONSISTENT_HTTP_BRIDGE_STATE")
            return
        if not http_success:
            raise ValueError("INCONSISTENT_HTTP_BRIDGE_STATE")

        report = self.inspection
        aligned = report.binding_status == "IDENTITY_ALIGNED_UNVERIFIED"
        if self.status == "EVIDENCE_BINDING_REJECTED":
            if (aligned or report.payload_byte_count is not None
                    or report.computed_sha256 is not None
                    or report.digest_matches is not None):
                raise ValueError("INCONSISTENT_INTEGRITY_REPORT")
            return
        if not aligned:
            raise ValueError("INCONSISTENT_INTEGRITY_REPORT")
        if self.status == "PAYLOAD_MISSING":
            if (http.payload != b"" or report.payload_byte_count != 0
                    or report.computed_sha256 is not None
                    or report.digest_matches is not None):
                raise ValueError("INCONSISTENT_INTEGRITY_REPORT")
            return

        # Digest status must correspond to the exact internal response bytes.
        # The declared expected digest is caller-provided, never attested.
        actual_sha256 = hashlib.sha256(http.payload).hexdigest()
        claimed = report.declared_sha256
        if (not http.payload
                or report.payload_byte_count != len(http.payload)
                or report.computed_sha256 != actual_sha256
                or type(claimed) is not str or len(claimed) != 64
                or any(char not in "0123456789abcdef" for char in claimed)):
            raise ValueError("INCONSISTENT_INTEGRITY_REPORT")
        if self.status == "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN":
            if report.digest_matches is not True or claimed != actual_sha256:
                raise ValueError("INCONSISTENT_INTEGRITY_REPORT")
        elif self.status == "CONTENT_DIGEST_MISMATCH":
            if report.digest_matches is not False or claimed == actual_sha256:
                raise ValueError("INCONSISTENT_INTEGRITY_REPORT")

    def public_record(self) -> dict[str, object]:
        """Strict allowlist: no source-id, evidence URI, raw bytes or exception."""
        report = self.inspection
        return {
            "record_kind": "LEGAL_HTTP_INTEGRITY_BRIDGE_PUBLIC_DIAGNOSTIC_V1",
            "status": self.status,
            "http_status": self.http_outcome.http_status,
            "http_outcome_status": self.http_outcome.status,
            "public_request": self.http_outcome.descriptor.to_dict(),
            "integrity_status": report.status if report is not None else None,
            "binding_status": report.binding_status if report is not None else None,
            "response_byte_count": (
                report.payload_byte_count if report is not None else None
            ),
            "digest_matches": report.digest_matches if report is not None else None,
            "http_acquisition_basis": "CALLER_SUPPLIED_OUTCOME_UNVERIFIED",
            "evidence_basis": "CALLER_SUPPLIED_REFERENCE_AND_DIGEST",
            "requested_url_identity": NOT_EVALUATED,
            "official_origin_decision": NOT_EVALUATED,
            "original_text_identity_decision": NOT_EVALUATED,
            "source_verification_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "legal_authority_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def inspect_legal_source_http_integrity_bridge(
    http_outcome: LegalSourceHttpFetchOutcome,
    record: LegalSourceRecord,
    reference: LegalSourceVersionEvidenceReference,
    *,
    known_references: tuple[LegalSourceVersionEvidenceReference, ...] = (),
) -> LegalSourceHttpIntegrityBridgeResult:
    """Check exact request namespace and MST before inspecting original bytes.

    Only a *claimed* 200 response with actual bytes may reach the existing
    integrity inspector. It independently recomputes record/reference binding
    and byte SHA-256. Never derive a URL/receipt from the public descriptor.
    The ``efYd`` date is a request parameter, NOT proof of the law's effective
    date; ``source_id`` cannot be learned from the request alone.
    """
    if type(http_outcome) is not LegalSourceHttpFetchOutcome:
        raise TypeError("INVALID_HTTP_OUTCOME")
    if type(record) is not LegalSourceRecord:
        raise TypeError("INVALID_SOURCE_RECORD")
    if type(reference) is not LegalSourceVersionEvidenceReference:
        raise TypeError("INVALID_EVIDENCE_REFERENCE")
    if type(known_references) is not tuple or any(
        type(item) is not LegalSourceVersionEvidenceReference
        for item in known_references
    ):
        raise TypeError("INVALID_KNOWN_REFERENCES")

    descriptor: LegalSourcePublicRequestDescriptor = http_outcome.descriptor

    def unresolved(status: str) -> LegalSourceHttpIntegrityBridgeResult:
        return LegalSourceHttpIntegrityBridgeResult(
            status=status, http_outcome=http_outcome,
        )

    if record.source_system != SOURCE_SYSTEM or record.source_namespace != descriptor.target:
        return unresolved(REQUEST_SOURCE_MISMATCH)
    if record.version_id is None or record.version_id != descriptor.mst:
        return unresolved(REQUEST_VERSION_MISMATCH)
    if descriptor.target == "eflaw":
        permitted_scope = (
            record.source_type in {"NATIONAL_LAW", "NATIONAL_SUBORDINATE"}
            and record.jurisdiction_level == "NATIONAL"
        )
    else:
        permitted_scope = (
            descriptor.target == "ordin"
            and record.source_type == "LOCAL_ORDINANCE"
            and record.jurisdiction_level in {"SIDO", "SIGUNGU"}
        )
    if not permitted_scope:
        return unresolved(REQUEST_SCOPE_MISMATCH)
    if http_outcome.status != SUCCESS or http_outcome.http_status != 200:
        return unresolved(HTTP_UNRESOLVED)

    # This inspector is existing, offline code: do not trust a fabricated
    # upstream binding report or merely compare a user-supplied success flag.
    # On any unforeseen failure, return a fixed diagnostic; never propagate
    # raw exceptions containing caller-supplied identifiers or URL text.
    try:
        report = inspect_legal_source_original_payload_integrity(
            record, reference, http_outcome.payload,
            known_references=known_references,
        )
    except Exception:
        return unresolved(INSPECTION_FAILED)

    return LegalSourceHttpIntegrityBridgeResult(
        status=report.status, http_outcome=http_outcome, inspection=report,
    )
