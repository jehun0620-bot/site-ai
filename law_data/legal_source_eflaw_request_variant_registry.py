# -*- coding: utf-8 -*-
"""Offline eflaw MST + requested efYd variant inventory; NOT a law resolver.

The request date is a selector, not independent proof of the effective date.
All source metadata, evidence IDs, URLs and digests are caller-supplied. This
module does not inspect a payload, authenticate an official source, select a
current version, authorize SITE/Rule Engine use, or interact with the network.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from law_data.legal_source_public_request_descriptor import (
    SOURCE_SYSTEM,
    LegalSourcePublicRequestDescriptor,
)
from law_data.legal_source_registry import LegalSourceRecord
from law_data.legal_source_version_evidence_binding import (
    LegalSourceVersionEvidenceReference,
    bind_legal_source_version_evidence,
)

NOT_EVALUATED = "NOT_EVALUATED"
VARIANT_UNVERIFIED = "EFLAW_REQUEST_VARIANT_UNVERIFIED"


@dataclass(frozen=True, slots=True)
class LegalSourceEflawRequestVariant:
    """Private claimed (source, MST, requested efYd) + one evidence artifact.

    Keep the original record.version_id and reference.version_id equal to MST.
    Never serialize the instance: caller source IDs, URIs and digest are private.
    """

    descriptor: LegalSourcePublicRequestDescriptor = field(repr=False)
    record: LegalSourceRecord = field(repr=False)
    reference: LegalSourceVersionEvidenceReference = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.descriptor) is not LegalSourcePublicRequestDescriptor:
            raise ValueError("INVALID_VARIANT_DESCRIPTOR")
        if type(self.record) is not LegalSourceRecord:
            raise ValueError("INVALID_VARIANT_RECORD")
        if type(self.reference) is not LegalSourceVersionEvidenceReference:
            raise ValueError("INVALID_VARIANT_REFERENCE")
        d, r, e = self.descriptor, self.record, self.reference
        if d.target != "eflaw" or d.efyd is None:
            raise ValueError("EFLAW_ONLY")
        if (r.source_system != SOURCE_SYSTEM or r.source_namespace != "eflaw"
                or r.source_type not in ("NATIONAL_LAW", "NATIONAL_SUBORDINATE")
                or r.jurisdiction_level != "NATIONAL" or r.jurisdiction_code is not None):
            raise ValueError("INVALID_EFLAW_SCOPE")
        if r.version_id is None or r.version_id != d.mst or e.version_id != d.mst:
            raise ValueError("MST_REQUEST_MISMATCH")
        # Existing binding verifies only caller descriptions; a digest/URI
        # is required but is never independently certified by this inventory.
        if bind_legal_source_version_evidence(r, e).status != "IDENTITY_ALIGNED_UNVERIFIED":
            raise ValueError("EVIDENCE_BINDING_UNRESOLVED")

    @property
    def variant_key(self) -> tuple[str, str, str, str, str]:
        """Internal lookup key, not a legal-version or provenance attestation."""
        return (*self.record.source_key, self.descriptor.mst, self.descriptor.efyd)

    @property
    def evidence_key(self) -> tuple[str, str, str]:
        return self.reference.evidence_key

    def public_record(self) -> dict[str, str]:
        relation = (
            NOT_EVALUATED if self.record.effective_date is None
            else "MATCH_DECLARED_UNVERIFIED"
            if self.record.effective_date.replace("-", "") == self.descriptor.efyd
            else "MISMATCH_DECLARED_UNVERIFIED"
        )
        return {
            "record_kind": "LEGAL_EFLAW_REQUEST_VARIANT_DIAGNOSTIC_V1",
            "status": VARIANT_UNVERIFIED,
            "requested_efyd_vs_declared_effective_date": relation,
            "evidence_basis": "CALLER_SUPPLIED_REFERENCE_AND_DIGEST",
            "source_verification_decision": NOT_EVALUATED,
            "original_text_identity_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "legal_authority_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


@dataclass(frozen=True, slots=True)
class LegalSourceEflawRequestVariantRegistry:
    """Distinct request selectors may share MST, never an evidence artifact ID.

    Checks are restricted to the provided snapshot of candidate artifacts.
    There is no global uniqueness or current-validity guarantee.
    """

    variants: tuple[LegalSourceEflawRequestVariant, ...] = field(default_factory=tuple, repr=False)

    def __post_init__(self) -> None:
        if type(self.variants) is not tuple:
            raise ValueError("INVALID_VARIANT_COLLECTION")
        seen: dict[tuple[str, str, str, str, str], LegalSourceEflawRequestVariant] = {}
        evidence_use: dict[tuple[str, str, str], tuple[str, str, str, str, str]] = {}
        source_scope: dict[tuple[str, str, str], tuple[str, str, str | None]] = {}
        unique: list[LegalSourceEflawRequestVariant] = []
        for item in self.variants:
            if type(item) is not LegalSourceEflawRequestVariant:
                raise ValueError("INVALID_VARIANT_ITEM")
            key = item.variant_key
            scope = (item.record.source_type, item.record.jurisdiction_level, item.record.jurisdiction_code)
            prior_scope = source_scope.get(item.record.source_key)
            if prior_scope is not None and prior_scope != scope:
                raise ValueError("SOURCE_SCOPE_COLLISION")
            source_scope[item.record.source_key] = scope
            prior = seen.get(key)
            if prior is not None:
                if (prior.descriptor != item.descriptor
                        or prior.record != item.record
                        or prior.reference != item.reference):
                    raise ValueError("REQUEST_VARIANT_COLLISION")
                continue  # Exact duplicate, not another variant.
            previous_key = evidence_use.get(item.evidence_key)
            if previous_key is not None and previous_key != key:
                raise ValueError("EVIDENCE_ID_REUSED_ACROSS_REQUEST_VARIANTS")
            evidence_use[item.evidence_key] = key
            seen[key] = item
            unique.append(item)
        object.__setattr__(self, "variants", tuple(unique))

    def variant_exact(
        self, source_system: str, source_namespace: str, source_id: str,
        mst: str, requested_efyd: str,
    ) -> LegalSourceEflawRequestVariant | None:
        key = (source_system, source_namespace, source_id, mst, requested_efyd)
        return next((item for item in self.variants if item.variant_key == key), None)

    def variants_for(self, source_system: str, source_namespace: str,
                     source_id: str) -> tuple[LegalSourceEflawRequestVariant, ...]:
        key = (source_system, source_namespace, source_id)
        return tuple(item for item in self.variants if item.record.source_key == key)

    def public_record(self) -> dict[str, str | int]:
        return {
            "record_kind": "LEGAL_EFLAW_REQUEST_VARIANT_INVENTORY_DIAGNOSTIC_V1",
            "status": VARIANT_UNVERIFIED,
            "request_variant_count": len(self.variants),
            "evidence_uniqueness_scope": "CALLER_SUPPLIED_SNAPSHOT_ONLY",
            "source_verification_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "legal_authority_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def build_legal_source_eflaw_request_variant_registry(
    variants: tuple[LegalSourceEflawRequestVariant, ...] | list[LegalSourceEflawRequestVariant],
) -> LegalSourceEflawRequestVariantRegistry:
    """Explicit offline construction; never derive a current-law candidate."""
    if type(variants) not in (tuple, list):
        raise ValueError("INVALID_VARIANT_COLLECTION")
    return LegalSourceEflawRequestVariantRegistry(tuple(variants))
