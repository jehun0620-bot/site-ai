from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from .legal_condition_catalogue_seed import LegalConditionCatalogueSeed
from .regulation_resolution_profile import (
    RegulationResolutionProfile,
    VALID_CONDITION_TYPES,
    VALID_RESOLUTION_TYPES,
)


VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"
CLASSIFICATION_ADMISSION_PROOF_VERSION = "STEP101_V1"


def _fingerprint(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def seed_identity_fingerprint(seed: LegalConditionCatalogueSeed) -> str:
    provenance = seed.provenance
    return _fingerprint(
        (
            seed.condition_name,
            seed.legal_basis,
            provenance.source_family,
            provenance.source_uri,
            provenance.law_id,
            provenance.law_version_id,
            provenance.effective_date,
            provenance.appendix_id,
            provenance.row_id,
            provenance.gazette_issue_id,
            provenance.publication_date,
            provenance.gazette_document_id,
            provenance.issuing_authority,
        )
    )


@dataclass(frozen=True)
class LegalConditionClassificationEvidence:
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
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def identity_fingerprint(self) -> str:
        return _fingerprint(
            (
                self.condition_name,
                self.legal_basis,
                self.seed_fingerprint,
                self.condition_type,
                self.resolution_type,
            )
        )


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
            and self.condition_identity_verified is True
            and self.legal_basis_verified is True
            and self.seed_identity_verified is True
            and self.classification_verified is True
            and bool(self.evidence_fingerprint)
        )


def verify_classification_evidence(
    seed: LegalConditionCatalogueSeed,
    evidence: LegalConditionClassificationEvidence,
) -> LegalConditionClassificationVerificationResult:
    seed_verified = seed.seed_verified is True
    condition_identity_verified = (
        seed_verified
        and evidence.condition_identity_bound is True
        and evidence.condition_name == seed.condition_name
    )
    legal_basis_verified = (
        seed_verified
        and evidence.legal_basis_bound is True
        and evidence.legal_basis == seed.legal_basis
    )
    seed_identity_verified = (
        seed_verified
        and evidence.seed_fingerprint == seed_identity_fingerprint(seed)
    )
    classification_verified = (
        seed_verified
        and evidence.official_source_qualified is True
        and evidence.classification_statement_bound is True
        and evidence.same_source_binding is True
        and evidence.condition_type in VALID_CONDITION_TYPES
        and evidence.resolution_type in VALID_RESOLUTION_TYPES
    )

    verified = (
        condition_identity_verified
        and legal_basis_verified
        and seed_identity_verified
        and classification_verified
    )
    return LegalConditionClassificationVerificationResult(
        status=VERIFIED if verified else UNVERIFIED,
        condition_identity_verified=condition_identity_verified,
        legal_basis_verified=legal_basis_verified,
        seed_identity_verified=seed_identity_verified,
        classification_verified=classification_verified,
        evidence_fingerprint=(evidence.identity_fingerprint() if verified else None),
    )


def evidence_matches_classification_verification(
    evidence: LegalConditionClassificationEvidence,
    verification: LegalConditionClassificationVerificationResult,
) -> bool:
    return (
        verification.verified
        and verification.evidence_fingerprint == evidence.identity_fingerprint()
    )


def classification_admission_proof_fingerprint(
    *,
    name: str,
    legal_basis: str,
    seed_fingerprint: str,
    classification_evidence_fingerprint: str,
    condition_type: str,
    resolution_type: str,
) -> str:
    """Bind the STEP101 admitted profile shape to its verified provenance.

    This is an integrity binding, not a secret/authentication token. STEP103 must
    still receive the exact seed/evidence/verification artifacts and recompute
    them rather than trusting profile diagnostics alone.
    """
    return _fingerprint(
        (
            CLASSIFICATION_ADMISSION_PROOF_VERSION,
            name,
            legal_basis,
            seed_fingerprint,
            classification_evidence_fingerprint,
            condition_type,
            resolution_type,
        )
    )


def admit_verified_classification_to_profile(
    seed: LegalConditionCatalogueSeed,
    evidence: LegalConditionClassificationEvidence,
    verification: LegalConditionClassificationVerificationResult,
) -> RegulationResolutionProfile:
    if seed.seed_verified is not True:
        raise ValueError("verified catalogue seed is required")
    if not evidence_matches_classification_verification(evidence, verification):
        raise ValueError("exact verified classification evidence/result pair is required")
    if evidence.condition_name != seed.condition_name:
        raise ValueError("classification condition identity does not match seed")
    if evidence.legal_basis != seed.legal_basis:
        raise ValueError("classification legal basis does not match seed")
    expected_seed_fingerprint = seed_identity_fingerprint(seed)
    if evidence.seed_fingerprint != expected_seed_fingerprint:
        raise ValueError("classification seed identity does not match seed")

    evidence_fingerprint = evidence.identity_fingerprint()
    admission_proof = classification_admission_proof_fingerprint(
        name=seed.condition_name,
        legal_basis=seed.legal_basis,
        seed_fingerprint=expected_seed_fingerprint,
        classification_evidence_fingerprint=evidence_fingerprint,
        condition_type=evidence.condition_type,
        resolution_type=evidence.resolution_type,
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
            "classification_admission_proof_version": CLASSIFICATION_ADMISSION_PROOF_VERSION,
            "seed_fingerprint": expected_seed_fingerprint,
            "classification_evidence_fingerprint": evidence_fingerprint,
            "classification_admission_proof": admission_proof,
        },
    )
