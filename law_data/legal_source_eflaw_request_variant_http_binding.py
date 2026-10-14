# -*- coding: utf-8 -*-
"""Offline, fail-closed eflaw request-variant -> HTTP response association.

This is a diagnostic ONLY: caller-supplied request/HTTP outcome, metadata,
reference URI and digest are not independent provenance or legal evidence.
The exact registered (MST, requested efYd) must match the HTTP descriptor.
The returned content effective date must match the caller's declared date,
which must match efYd, but this does NOT prove the date has legal effect.
No network, disk, receipt, current-law selection, or production admission.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from law_data.legal_source_eflaw_request_variant_registry import (
    LegalSourceEflawRequestVariant,
    LegalSourceEflawRequestVariantRegistry,
)
from law_data.legal_source_http_safety_boundary import LegalSourceHttpFetchOutcome
from law_data.legal_source_response_identity_inspection import (
    NATIONAL_LIMITED, UPSTREAM_UNRESOLVED, JSON_INVALID, SHAPE_UNKNOWN,
    FIELDS_MISSING, FIELDS_MISMATCH, inspect_legal_source_response_identity,
)
from law_data.legal_source_version_evidence_binding import LegalSourceVersionEvidenceReference

_INTERNAL_RESULT_SEAL = object()
NOT_EVALUATED = "NOT_EVALUATED"
BOUND = "EFLAW_REQUEST_HTTP_IDENTITY_ALIGNED_LIMITED_UNVERIFIED_ORIGIN"
NOT_REGISTERED = "REQUEST_VARIANT_NOT_REGISTERED"
DESCRIPTOR_MISMATCH = "REQUEST_VARIANT_DESCRIPTOR_MISMATCH"
DECLARED_DATE_UNRESOLVED = "REQUEST_EFYD_DECLARED_DATE_UNRESOLVED"
DECLARED_DATE_MISMATCH = "REQUEST_EFYD_DECLARED_DATE_MISMATCH"
IDENTITY_UNRESOLVED = "REQUEST_VARIANT_RESPONSE_IDENTITY_UNRESOLVED"
INSPECTION_FAILED = "REQUEST_VARIANT_INSPECTION_FAILED"

_IDENTITY_STATUSES = frozenset((
    NOT_EVALUATED, NATIONAL_LIMITED, UPSTREAM_UNRESOLVED, JSON_INVALID,
    SHAPE_UNKNOWN, FIELDS_MISSING, FIELDS_MISMATCH,
))
_STATUSES = frozenset((
    BOUND, NOT_REGISTERED, DESCRIPTOR_MISMATCH,
    DECLARED_DATE_UNRESOLVED, DECLARED_DATE_MISMATCH,
    IDENTITY_UNRESOLVED, INSPECTION_FAILED,
))


@dataclass(frozen=True, slots=True)
class LegalSourceEflawRequestVariantHttpBinding:
    """Sanitized diagnostic, NOT authority to use the response in Rule Engine.

    No raw body, credential, evidence ID, digest, source ID or source URL is
    retained on this public result. Success remains explicitly UNVERIFIED.
    """

    status: str
    descriptor_check: str
    declared_date_check: str
    upstream_identity_status: str
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.status) is not str or self.status not in _STATUSES:
            raise ValueError("INVALID_VARIANT_HTTP_STATUS")
        if self.descriptor_check not in ("MATCH", "MISMATCH", NOT_EVALUATED):
            raise ValueError("INVALID_DESCRIPTOR_CHECK")
        if self.declared_date_check not in (
            NOT_EVALUATED, "MATCH_DECLARED_UNVERIFIED",
            "MISMATCH_DECLARED_UNVERIFIED",
        ):
            raise ValueError("INVALID_DECLARED_DATE_CHECK")
        if type(self.upstream_identity_status) is not str or self.upstream_identity_status not in _IDENTITY_STATUSES:
            raise ValueError("INVALID_UPSTREAM_IDENTITY_STATUS")
        # Do not accept user-crafted apparent success with missing checks.
        if self.status == BOUND and (
            self.descriptor_check != "MATCH"
            or self.declared_date_check != "MATCH_DECLARED_UNVERIFIED"
            or self.upstream_identity_status != NATIONAL_LIMITED
        ):
            raise ValueError("INCONSISTENT_VARIANT_HTTP_SUCCESS")
        if self._construction_seal is not _INTERNAL_RESULT_SEAL:
            raise ValueError("DIRECT_BINDING_RESULT_CONSTRUCTION_FORBIDDEN")

    def public_record(self) -> dict[str, str]:
        return {
            "record_kind": "LEGAL_EFLAW_REQUEST_VARIANT_HTTP_BINDING_V1",
            "status": self.status,
            "request_descriptor_check": self.descriptor_check,
            "requested_efyd_vs_declared_effective_date": self.declared_date_check,
            "upstream_identity_status": self.upstream_identity_status,
            "source_identity_basis": "REGISTERED_CALLER_SUPPLIED_VARIANT_AND_HTTP_OUTCOME",
            "evidence_uniqueness_scope": "REGISTERED_VARIANT_SNAPSHOT_AND_SUPPLIED_KNOWN_REFERENCES",
            "official_origin_decision": NOT_EVALUATED,
            "original_text_identity_decision": NOT_EVALUATED,
            "source_verification_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "legal_authority_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def inspect_legal_source_eflaw_request_variant_http_binding(
    registry: LegalSourceEflawRequestVariantRegistry,
    variant: LegalSourceEflawRequestVariant,
    http_outcome: LegalSourceHttpFetchOutcome,
    *,
    known_references: tuple[LegalSourceVersionEvidenceReference, ...] = (),
) -> LegalSourceEflawRequestVariantHttpBinding:
    """Check the exact registered descriptor BEFORE independent legacy checks.

    The legacy inspector recomputes the Bridge, actual payload SHA-256, and
    bounded JSON identity; it must not be replaced by a claimed success flag.
    A caller-supplied outcome is still NOT an authenticated acquisition.
    """
    if type(registry) is not LegalSourceEflawRequestVariantRegistry:
        raise TypeError("INVALID_VARIANT_REGISTRY")
    if type(variant) is not LegalSourceEflawRequestVariant:
        raise TypeError("INVALID_VARIANT")
    if type(http_outcome) is not LegalSourceHttpFetchOutcome:
        raise TypeError("INVALID_HTTP_OUTCOME")
    if type(known_references) is not tuple or any(
        type(item) is not LegalSourceVersionEvidenceReference for item in known_references
    ):
        raise TypeError("INVALID_KNOWN_REFERENCES")

    def make(status: str, descriptor_check: str = NOT_EVALUATED,
             date_check: str = NOT_EVALUATED,
             identity_status: str = NOT_EVALUATED) -> LegalSourceEflawRequestVariantHttpBinding:
        return LegalSourceEflawRequestVariantHttpBinding(
            status, descriptor_check, date_check, identity_status,
            _construction_seal=_INTERNAL_RESULT_SEAL,
        )

    # Object identity also rejects a detached record/reference with the same
    # public variant key but substituted evidence or claimed metadata.
    registered = registry.variant_exact(*variant.variant_key)
    if registered is not variant:
        return make(NOT_REGISTERED)

    if http_outcome.descriptor != variant.descriptor:
        return make(DESCRIPTOR_MISMATCH, "MISMATCH")

    declared = variant.public_record()["requested_efyd_vs_declared_effective_date"]
    if declared == NOT_EVALUATED:
        return make(DECLARED_DATE_UNRESOLVED, "MATCH")
    if declared != "MATCH_DECLARED_UNVERIFIED":
        return make(DECLARED_DATE_MISMATCH, "MATCH", declared)

    # Only the given local inventory is searched; no global ID uniqueness claim.
    from_inventory = tuple(
        other.reference for other in registry.variants if other is not variant
    )
    try:
        identity = inspect_legal_source_response_identity(
            http_outcome,
            variant.record,
            variant.reference,
            known_references=from_inventory + known_references,
        )
    except Exception:
        # Never reflect response data, paths, identifiers or raw exception text.
        return make(INSPECTION_FAILED, "MATCH", declared)

    if identity.status != NATIONAL_LIMITED or (
        identity.source_id_check != "MATCH"
        or identity.name_check != "MATCH"
        or identity.effective_date_check != "MATCH"
        or identity.response_mst_check != "NOT_PRESENT_IN_CONFIRMED_NATIONAL_SCHEMA"
        or identity.bridge.status != "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN"
    ):
        return make(IDENTITY_UNRESOLVED, "MATCH", declared, identity.status)

    return make(BOUND, "MATCH", declared, identity.status)
