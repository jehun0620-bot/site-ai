# -*- coding: utf-8 -*-
"""Read-only inspection of UNVERIFIED legal-source metadata.

This is not an official-source verifier, authority admission boundary, law
resolver, SITE applicability decision, or production admission path.  No
metadata (including an official-looking URI, date, version, or matching PNU
code) can grant any verified flag or legal decision here.
"""

from __future__ import annotations

from dataclasses import dataclass

from law_data.legal_jurisdiction_context import LegalJurisdictionContext
from law_data.legal_source_registry import LegalSourceRecord


# These are independent verification tasks, NOT attestations or completed checks.
INDEPENDENT_CHECKS_REQUIRED = (
    "OFFICIAL_SOURCE_IDENTITY_AND_ORIGINAL_TEXT",
    "EXACT_VERSION_AND_CURRENT_LEGAL_VALIDITY",
    "PROMULGATION_AND_EFFECTIVE_PERIOD",
    "COMPETENT_LEGAL_AUTHORITY_AND_DELEGATION",
    "CURRENT_TERRITORIAL_SCOPE_AND_REGION_BINDING",
    "TARGET_REGULATION_COMPATIBILITY",
    "SITE_SPECIFIC_APPLICABILITY",
    "PRODUCTION_ADMISSION",
)

_METADATA_FIELDS = ("version_id", "source_uri", "promulgation_date", "effective_date")


@dataclass(frozen=True, slots=True)
class LegalSourceEvidenceInspection:
    """Immutable diagnostic of metadata only; cannot assert verification."""

    source_key: tuple[str, str, str]
    version_key: tuple[str, str, str, str | None]
    source_state: str
    source_type: str
    jurisdiction_level: str
    jurisdiction_code: str | None
    version_identity_status: str
    jurisdiction_code_relation: str
    missing_metadata_fields: tuple[str, ...]
    independent_checks_required: tuple[str, ...] = INDEPENDENT_CHECKS_REQUIRED

    def to_dict(self) -> dict[str, object]:
        return {
            "source_key": list(self.source_key),
            "version_key": list(self.version_key),
            "source_state": self.source_state,
            "source_type": self.source_type,
            "jurisdiction_level": self.jurisdiction_level,
            "jurisdiction_code": self.jurisdiction_code,
            "version_identity_status": self.version_identity_status,
            "jurisdiction_code_relation": self.jurisdiction_code_relation,
            "missing_metadata_fields": list(self.missing_metadata_fields),
            "independent_checks_required": list(self.independent_checks_required),
            "source_identity_basis": "CALLER_SUPPLIED_UNVERIFIED",
            "source_verification_decision": "NOT_EVALUATED",
            "current_validity_decision": "NOT_EVALUATED",
            "legal_authority_decision": "NOT_EVALUATED",
            "legal_applicability_decision": "NOT_EVALUATED",
            "production_admission_decision": "NOT_EVALUATED",
        }


def inspect_legal_source_evidence(
    record: LegalSourceRecord,
    *,
    jurisdiction_context: LegalJurisdictionContext | None = None,
) -> LegalSourceEvidenceInspection:
    """Inspect declared metadata; make no verified or legal-authority decision.

    For local ordinances, an optional PNU context permits a *lexical* code
    comparison only.  Neither equality nor inequality validates administrative
    boundaries, ordinance scope, legal applicability, or current jurisdiction.
    """
    if not isinstance(record, LegalSourceRecord):
        raise TypeError("record must be LegalSourceRecord")
    if jurisdiction_context is not None and not isinstance(jurisdiction_context, LegalJurisdictionContext):
        raise TypeError("jurisdiction_context must be LegalJurisdictionContext or None")

    if record.jurisdiction_level == "NATIONAL":
        relation = "NO_LOCAL_CODE"
    elif jurisdiction_context is None:
        relation = "NOT_CHECKED"
    else:
        parcel_code = (
            jurisdiction_context.sido_code
            if record.jurisdiction_level == "SIDO"
            else jurisdiction_context.sigungu_code
        )
        relation = (
            "LEXICALLY_EQUAL_UNVERIFIED"
            if parcel_code == record.jurisdiction_code
            else "LEXICALLY_DIFFERENT_UNVERIFIED"
        )

    return LegalSourceEvidenceInspection(
        source_key=record.source_key,
        version_key=record.version_key,
        source_state=record.source_state,
        source_type=record.source_type,
        jurisdiction_level=record.jurisdiction_level,
        jurisdiction_code=record.jurisdiction_code,
        version_identity_status=(
            "EXPLICIT_ID_UNVERIFIED" if record.version_id is not None else "UNKNOWN"
        ),
        jurisdiction_code_relation=relation,
        missing_metadata_fields=tuple(
            field for field in _METADATA_FIELDS if getattr(record, field) is None
        ),
    )
