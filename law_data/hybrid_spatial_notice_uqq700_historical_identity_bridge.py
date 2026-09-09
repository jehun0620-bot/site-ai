from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hybrid_spatial_notice_historical_candidate_resolver import (
    QUALIFIED_HISTORICAL_NOTICE_CANDIDATE,
    HistoricalNoticeCandidateResult,
)
from hybrid_spatial_notice_uqq700_identity_evidence_adapter import (
    Uqq700IdentityEvidenceInput,
    adapt_uqq700_identity_evidence,
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"


@dataclass(frozen=True)
class Uqq700HistoricalIdentityProvenance:
    designation_act_bound: bool = False
    issuing_authority: str = ""
    effective_or_notice_date_verified: bool = False


def _candidate_qualified(candidate: HistoricalNoticeCandidateResult) -> bool:
    return candidate.status == QUALIFIED_HISTORICAL_NOTICE_CANDIDATE


def bridge_uqq700_historical_candidate_to_identity(
    candidate: HistoricalNoticeCandidateResult,
    *,
    provenance: Uqq700HistoricalIdentityProvenance | None = None,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fail-closed compatibility bridge from historical candidate to Gate-1 input.

    Safe mappings are limited to fields already explicitly qualified by the
    historical-candidate stage. Designation-act binding and issuing authority are
    never inferred from document_role, URL, host, title, or authority-source
    qualification. The candidate published_date is used only when the caller
    explicitly verifies that it is the relevant notice/effective date.
    """
    extra = provenance or Uqq700HistoricalIdentityProvenance()

    effective_or_notice_date = (
        candidate.published_date
        if extra.effective_or_notice_date_verified is True
        else ""
    )

    identity_input = Uqq700IdentityEvidenceInput(
        candidate_qualified=_candidate_qualified(candidate),
        authority_source_qualified=(candidate.authority_source_qualified is True),
        target_name_bound=(candidate.target_name_present is True),
        designation_act_bound=(extra.designation_act_bound is True),
        notice_number=candidate.notice_number,
        issuing_authority=extra.issuing_authority,
        effective_or_notice_date=effective_or_notice_date,
        source_url=candidate.url,
    )

    identity_result = adapt_uqq700_identity_evidence(
        identity_input,
        diagnostics=diagnostics,
    )

    return {
        "target": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "identity_result": identity_result,
        "official_designation_identity_verified": identity_result[
            "official_designation_identity_verified"
        ],
        "mapping": {
            "candidate_status_to_candidate_qualified": True,
            "source_url_direct": True,
            "authority_source_qualified_direct": True,
            "target_name_present_to_target_name_bound": True,
            "notice_number_direct": True,
            "published_date_requires_explicit_verification": True,
            "designation_act_bound_inferred": False,
            "issuing_authority_inferred": False,
        },
        "explicit_provenance": {
            "designation_act_bound": extra.designation_act_bound is True,
            "issuing_authority": extra.issuing_authority,
            "effective_or_notice_date_verified": (
                extra.effective_or_notice_date_verified is True
            ),
        },
        "legal_inference_performed": False,
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
        "site_mutated": False,
    }
