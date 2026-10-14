# -*- coding: ascii -*-
"""Offline local observation -> explicit request -> registered eflaw variant.

A local observation is not proof of a witnessed or authenticated acquisition.
Caller-supplied requested_descriptor is NOT a captured wire request. The
observed HTTP outcome comes from the existing private opt-in wrapper; its
status, bytes and digest are rechecked before the legacy identity inspector.
No HTTP call, disk write, receipt, legal determination or Rule Engine admission.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from law_data.legal_source_eflaw_local_acquisition_observation import (
    LOCAL_SUCCESS,
    LegalSourceEflawLocalAcquisitionObservation,
)
from law_data.legal_source_eflaw_request_variant_http_binding import (
    BOUND, inspect_legal_source_eflaw_request_variant_http_binding,
)
from law_data.legal_source_eflaw_request_variant_registry import (
    LegalSourceEflawRequestVariant,
    LegalSourceEflawRequestVariantRegistry,
)
from law_data.legal_source_http_safety_boundary import SUCCESS
from law_data.legal_source_public_request_descriptor import LegalSourcePublicRequestDescriptor
from law_data.legal_source_version_evidence_binding import LegalSourceVersionEvidenceReference

NOT_EVALUATED = "NOT_EVALUATED"
ALIGNED = "EFLAW_LOCAL_OBSERVATION_VARIANT_ALIGNED_LIMITED_UNVERIFIED_ORIGIN"
NOT_REGISTERED = "LOCAL_OBSERVATION_VARIANT_NOT_REGISTERED"
REQUEST_MISMATCH = "LOCAL_OBSERVATION_REQUEST_DESCRIPTOR_MISMATCH"
OUTCOME_MISMATCH = "LOCAL_OBSERVATION_OUTCOME_DESCRIPTOR_MISMATCH"
OBSERVATION_UNRESOLVED = "LOCAL_OBSERVATION_STATUS_UNRESOLVED"
BYTES_UNRESOLVED = "LOCAL_OBSERVATION_BYTES_UNRESOLVED"
BINDING_UNRESOLVED = "LOCAL_OBSERVATION_VARIANT_BINDING_UNRESOLVED"
INSPECTION_FAILED = "LOCAL_OBSERVATION_VARIANT_INSPECTION_FAILED"
_STATUSES = frozenset((
    ALIGNED, NOT_REGISTERED, REQUEST_MISMATCH, OUTCOME_MISMATCH,
    OBSERVATION_UNRESOLVED, BYTES_UNRESOLVED, BINDING_UNRESOLVED,
    INSPECTION_FAILED,
))
_CHECKS = frozenset(("MATCH", "MISMATCH", "UNRESOLVED", NOT_EVALUATED))
_SEAL = object()


@dataclass(frozen=True, slots=True)
class LegalSourceEflawLocalObservationVariantBinding:
    """Fixed diagnostic only. Never contains raw bytes, timestamps, or IDs."""
    status: str
    registered_variant_check: str
    requested_descriptor_check: str
    outcome_descriptor_check: str
    observed_bytes_check: str
    upstream_binding_check: str
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.status) is not str or self.status not in _STATUSES:
            raise ValueError("INVALID_OBSERVATION_VARIANT_STATUS")
        for name in (
            "registered_variant_check", "requested_descriptor_check",
            "outcome_descriptor_check", "observed_bytes_check", "upstream_binding_check",
        ):
            if type(getattr(self, name)) is not str or getattr(self, name) not in _CHECKS:
                raise ValueError("INVALID_OBSERVATION_VARIANT_CHECK")
        if self.status == ALIGNED and any(
            getattr(self, name) != "MATCH" for name in (
                "registered_variant_check", "requested_descriptor_check",
                "outcome_descriptor_check", "observed_bytes_check", "upstream_binding_check",
            )
        ):
            raise ValueError("INCONSISTENT_OBSERVATION_VARIANT_SUCCESS")
        if self._seal is not _SEAL:
            raise ValueError("DIRECT_OBSERVATION_VARIANT_RESULT_FORBIDDEN")

    def public_record(self) -> dict[str, str]:
        return {
            "record_kind": "LEGAL_EFLAW_LOCAL_OBSERVATION_VARIANT_BINDING_V1",
            "status": self.status,
            "registered_variant_check": self.registered_variant_check,
            "requested_descriptor_check": self.requested_descriptor_check,
            "outcome_descriptor_check": self.outcome_descriptor_check,
            "observed_bytes_check": self.observed_bytes_check,
            "upstream_binding_check": self.upstream_binding_check,
            "observation_basis": "UNATTESTED_LOCAL_OPT_IN_WRAPPER",
            "requested_descriptor_basis": "CALLER_SUPPLIED_NOT_WIRE_OBSERVED",
            "acquisition_authenticity_decision": NOT_EVALUATED,
            "official_origin_decision": NOT_EVALUATED,
            "original_text_identity_decision": NOT_EVALUATED,
            "source_verification_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "legal_authority_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def inspect_legal_source_eflaw_local_observation_variant_binding(
    registry: LegalSourceEflawRequestVariantRegistry,
    variant: LegalSourceEflawRequestVariant,
    requested_descriptor: LegalSourcePublicRequestDescriptor,
    observation: LegalSourceEflawLocalAcquisitionObservation,
    *,
    known_references: tuple[LegalSourceVersionEvidenceReference, ...] = (),
) -> LegalSourceEflawLocalObservationVariantBinding:
    """Fail-closed offline association, NOT authentication of a real fetch."""
    if type(registry) is not LegalSourceEflawRequestVariantRegistry:
        raise TypeError("INVALID_VARIANT_REGISTRY")
    if type(variant) is not LegalSourceEflawRequestVariant:
        raise TypeError("INVALID_VARIANT")
    if type(requested_descriptor) is not LegalSourcePublicRequestDescriptor:
        raise TypeError("INVALID_REQUEST_DESCRIPTOR")
    if type(observation) is not LegalSourceEflawLocalAcquisitionObservation:
        raise TypeError("INVALID_LOCAL_OBSERVATION")
    if type(known_references) is not tuple or any(
        type(x) is not LegalSourceVersionEvidenceReference for x in known_references
    ):
        raise TypeError("INVALID_KNOWN_REFERENCES")

    def make(status: str, registered: str = NOT_EVALUATED,
             requested: str = NOT_EVALUATED, outcome: str = NOT_EVALUATED,
             byte_check: str = NOT_EVALUATED,
             upstream: str = NOT_EVALUATED) -> LegalSourceEflawLocalObservationVariantBinding:
        return LegalSourceEflawLocalObservationVariantBinding(
            status, registered, requested, outcome, byte_check, upstream,
            _seal=_SEAL,
        )

    if registry.variant_exact(*variant.variant_key) is not variant:
        return make(NOT_REGISTERED, "MISMATCH")
    if requested_descriptor != variant.descriptor:
        return make(REQUEST_MISMATCH, "MATCH", "MISMATCH")
    outcome = observation.http_outcome
    if outcome.descriptor != requested_descriptor:
        return make(OUTCOME_MISMATCH, "MATCH", "MATCH", "MISMATCH")
    if (observation.status != LOCAL_SUCCESS or outcome.status != SUCCESS
            or outcome.http_status != 200 or type(outcome.payload) is not bytes):
        return make(OBSERVATION_UNRESOLVED, "MATCH", "MATCH", "MATCH", "UNRESOLVED")
    try:
        digest = hashlib.sha256(outcome.payload).hexdigest()
        if (digest != observation.response_sha256
                or len(outcome.payload) != observation.response_byte_count):
            return make(BYTES_UNRESOLVED, "MATCH", "MATCH", "MATCH", "MISMATCH")
        bound = inspect_legal_source_eflaw_request_variant_http_binding(
            registry, variant, outcome, known_references=known_references,
        )
    except Exception:
        return make(INSPECTION_FAILED, "MATCH", "MATCH", "MATCH", "UNRESOLVED")
    if bound.status != BOUND:
        return make(BINDING_UNRESOLVED, "MATCH", "MATCH", "MATCH", "MATCH", "UNRESOLVED")
    return make(ALIGNED, "MATCH", "MATCH", "MATCH", "MATCH", "MATCH")
