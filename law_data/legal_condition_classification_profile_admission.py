"""Fail-closed admission from verified classification evidence to a profile.

This boundary admits only an exact seed-bound, fingerprint-bound classification
result into RegulationResolutionProfile. It does not infer classification from a
condition name, infer a standard code, decide SITE truth, or authorize
production/runtime behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any, Mapping

from .legal_condition_catalogue_seed import LegalConditionCatalogueSeed
from .regulation_resolution_profile import (
    VALID_CONDITION_TYPES,
    VALID_RESOLUTION_TYPES,
    RegulationResolutionProfile,
)

VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"


class LegalConditionClassificationProfileAdmissionError(ValueError):
    """Raised when classification evidence cannot be safely admitted."""


def _clean_required(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value.strip()


def _freeze(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping):
        raise TypeError("metadata must be a mapping")
    return MappingProxyType(dict(value))


def _fingerprint(fields: tuple[str, ...]) -> str:
    payload = json.dumps(fields, ensure_ascii=False, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def seed_identity_fingerprint(seed: LegalConditionCatalogueSeed) -> str:
    """Fingerprint the complete reproducible identity carried by a verified seed."""
    if not isinstance(seed, LegalConditionCatalogueSeed):
        raise TypeError("seed must be LegalConditionCatalogueSeed")
    provenance = seed.provenance
    return _fingerprint((
        seed.condition_name,
        seed.legal_basis,
        provenance.source_family,
        provenance.source_uri or "",
        provenance.law_id or "",
        provenance.law_version_id or "",
        provenance.effective_date or "",
        provenance.appendix_id or "",
        provenance.row_id or "",
        provenance.gazette_issue_id or "",
        provenance.publication_date or "",
        provenance.gazette_document_id or "",
        provenance.issuing_authority or "",
    ))


@dataclass(frozen=True)
class LegalConditionClassificationEvidence:
    """Explicit classification evidence already bound to one exact catalogue seed."""

    condition_name: str
    legal_basis: str
    seed_fingerprint: str
    condition_type: str
    resolution_type: str
    official_source_qualified: bool = False
    condition_identity_bound: bool = False
    legal_basis_bound: bool = False
    classification_statement_bound: bool = False
    same_source_binding: bool = False
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        for name in (
            "condition_name", "legal_basis", "seed_fingerprint",
            "condition_type", "resolution_type",
        ):
            object.__setattr__(self, name, _clean_required(getattr(self, name), name))
        object.__setattr__(self, "condition_type", self.condition_type.upper())
        object.__setattr__(self, "resolution_type", self.resolution_type.upper())
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def identity_fingerprint(self) -> str:
        return _fingerprint((
            self.condition_name,
            self.legal_basis,
            self.seed_fingerprint,
            self.condition_type,
            self.resolution_type,
        ))


@dataclass(frozen=True)
class LegalConditionClassificationVerificationResult:
    status: str
    condition_identity_verified: bool
    legal_basis_verified: bool
    seed_identity_verified: bool
    classification_verified: bool
    evidence_fingerprint: str | None = None

    @property
    def verified(self) -> bool:
        return (
            self.status == VERIFIED
            and self.condition_identity_verified
            and self.legal_basis_verified
            and self.seed_identity_verified
            and self.classification_verified
            and isinstance(self.evidence_fingerprint, str)
            and bool(self.evidence_fingerprint)
        )


def verify_classification_evidence(
    seed: LegalConditionCatalogueSeed,
    evidence: LegalConditionClassificationEvidence,
) -> LegalConditionClassificationVerificationResult:
    """Verify explicit classification evidence without inferring any classification."""
    if not isinstance(seed, LegalConditionCatalogueSeed):
        raise TypeError("seed must be LegalConditionCatalogueSeed")
    if not isinstance(evidence, LegalConditionClassificationEvidence):
        raise TypeError("evidence must be LegalConditionClassificationEvidence")

    seed_verified = seed.seed_verified is True
    condition_identity = (
        seed_verified
        and evidence.condition_name == seed.condition_name
        and evidence.condition_identity_bound is True
    )
    legal_basis = (
        seed_verified
        and evidence.legal_basis == seed.legal_basis
        and evidence.legal_basis_bound is True
    )
    seed_identity = (
        seed_verified
        and evidence.seed_fingerprint == seed_identity_fingerprint(seed)
    )
    classification = all((
        evidence.official_source_qualified is True,
        evidence.classification_statement_bound is True,
        evidence.same_source_binding is True,
        evidence.condition_type in VALID_CONDITION_TYPES,
        evidence.resolution_type in VALID_RESOLUTION_TYPES,
    ))
    verified = all((condition_identity, legal_basis, seed_identity, classification))

    return LegalConditionClassificationVerificationResult(
        status=VERIFIED if verified else UNVERIFIED,
        condition_identity_verified=condition_identity,
        legal_basis_verified=legal_basis,
        seed_identity_verified=seed_identity,
        classification_verified=classification,
        evidence_fingerprint=evidence.identity_fingerprint() if verified else None,
    )


def evidence_matches_classification_verification(
    evidence: LegalConditionClassificationEvidence,
    verification: LegalConditionClassificationVerificationResult,
) -> bool:
    if not isinstance(evidence, LegalConditionClassificationEvidence):
        return False
    if not isinstance(verification, LegalConditionClassificationVerificationResult):
        return False
    return (
        verification.verified
        and verification.evidence_fingerprint == evidence.identity_fingerprint()
    )


def admit_verified_classification_to_profile(
    seed: LegalConditionCatalogueSeed,
    evidence: LegalConditionClassificationEvidence,
    verification: LegalConditionClassificationVerificationResult,
) -> RegulationResolutionProfile:
    """Admit only an exact verified classification pair for this exact seed."""
    if not isinstance(seed, LegalConditionCatalogueSeed) or not seed.seed_verified:
        raise LegalConditionClassificationProfileAdmissionError(
            "admission requires a verified catalogue seed"
        )
    if not evidence_matches_classification_verification(evidence, verification):
        raise LegalConditionClassificationProfileAdmissionError(
            "classification evidence and verification are not an exact verified pair"
        )
    if evidence.condition_name != seed.condition_name:
        raise LegalConditionClassificationProfileAdmissionError(
            "classification condition does not match seed"
        )
    if evidence.legal_basis != seed.legal_basis:
        raise LegalConditionClassificationProfileAdmissionError(
            "classification legal basis does not match seed"
        )
    if evidence.seed_fingerprint != seed_identity_fingerprint(seed):
        raise LegalConditionClassificationProfileAdmissionError(
            "classification evidence is not bound to this exact seed"
        )

    return RegulationResolutionProfile(
        name=seed.condition_name,
        condition_type=evidence.condition_type,
        resolution_type=evidence.resolution_type,
        standard_code=None,
        standard_code_verified=False,
        authority_requirements=(),
        source_policy_requirements=(),
        authority_identity_verified=False,
        source_policy_verified=False,
        negative_evidence_allowed=False,
        legal_absence_inference_allowed=False,
        site_promotion_allowed=False,
        production_registration_allowed=False,
        runtime_registration_allowed=False,
        diagnostics={
            "classification_admission": VERIFIED,
            "seed_fingerprint": evidence.seed_fingerprint,
            "classification_evidence_fingerprint": evidence.identity_fingerprint(),
        },
    )
