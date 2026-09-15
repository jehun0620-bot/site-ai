"""Fail-closed admission from verified legal enumeration evidence to seed.

This module only converts an exact fingerprint-bound evidence/result pair into
LegalConditionCatalogueSeed. It does not acquire sources, infer codes or types,
decide SITE applicability, or authorize production/runtime behavior.
"""

from __future__ import annotations

from .legal_condition_catalogue_seed import (
    OFFICIAL_GAZETTE,
    LegalConditionCatalogueSeed,
    LegalEnumerationProvenance,
)
from .legal_enumeration_source_family_verifier import (
    LawAppendixEnumerationEvidence,
    LegalEnumerationVerificationResult,
    OfficialGazetteEnumerationEvidence,
    evidence_matches_verification,
)


class LegalEnumerationSeedAdmissionError(ValueError):
    """Raised when evidence cannot be safely admitted to the catalogue seed."""


def admit_verified_evidence_to_seed(
    evidence: LawAppendixEnumerationEvidence | OfficialGazetteEnumerationEvidence,
    verification: LegalEnumerationVerificationResult,
) -> LegalConditionCatalogueSeed:
    """Create a seed only from the exact evidence verified by ``verification``."""
    if not evidence_matches_verification(evidence, verification):
        raise LegalEnumerationSeedAdmissionError(
            "evidence and verification are not an exact verified pair"
        )

    if isinstance(evidence, LawAppendixEnumerationEvidence):
        provenance = LegalEnumerationProvenance(
            source_family=evidence.source_family,
            source_uri=evidence.source_uri,
            law_id=evidence.law_id,
            law_version_id=evidence.law_version_id,
            effective_date=evidence.effective_date,
            appendix_id=evidence.appendix_id,
            row_id=evidence.row_id,
            source_identity_verified=verification.source_identity_verified,
            row_binding_verified=verification.row_binding_verified,
        )
    elif isinstance(evidence, OfficialGazetteEnumerationEvidence):
        provenance = LegalEnumerationProvenance(
            source_family=OFFICIAL_GAZETTE,
            source_uri=evidence.source_uri,
            gazette_issue_id=evidence.gazette_issue_id,
            publication_date=evidence.publication_date,
            gazette_document_id=evidence.gazette_document_id,
            issuing_authority=evidence.issuing_authority,
            source_identity_verified=verification.source_identity_verified,
            row_binding_verified=verification.row_binding_verified,
        )
    else:
        raise LegalEnumerationSeedAdmissionError("unsupported evidence contract")

    if not provenance.provenance_verified:
        raise LegalEnumerationSeedAdmissionError(
            "admission requires verified provenance"
        )

    return LegalConditionCatalogueSeed(
        condition_name=evidence.condition_name,
        legal_basis=evidence.legal_basis,
        provenance=provenance,
    )
