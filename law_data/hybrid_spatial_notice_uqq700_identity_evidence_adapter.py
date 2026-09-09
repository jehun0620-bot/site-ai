from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hybrid_spatial_notice_designation_identity_verifier import (
    DesignationIdentityEvidence,
    verify_designation_identity,
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"


@dataclass(frozen=True)
class Uqq700IdentityEvidenceInput:
    candidate_qualified: bool = False
    authority_source_qualified: bool = False
    target_name_bound: bool = False
    designation_act_bound: bool = False
    notice_number: str = ""
    issuing_authority: str = ""
    effective_or_notice_date: str = ""
    source_url: str = ""


def _present(value: str) -> bool:
    return bool(str(value or "").strip())


def adapt_uqq700_identity_evidence(
    source: Uqq700IdentityEvidenceInput,
    *,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fail-closed bridge from provenance-bearing UQQ700 evidence to identity verification.

    This adapter performs no discovery and makes no legal inference. Text identity fields
    must be explicitly present; booleans must be explicitly supplied by an upstream
    qualification step. Missing provenance therefore cannot promote Gate 1.
    """
    evidence = DesignationIdentityEvidence(
        candidate_qualified=source.candidate_qualified is True,
        authority_source_qualified=source.authority_source_qualified is True,
        target_name_bound=source.target_name_bound is True,
        designation_act_bound=source.designation_act_bound is True,
        notice_number_bound=_present(source.notice_number),
        issuing_authority_bound=_present(source.issuing_authority),
        effective_or_notice_date_bound=_present(source.effective_or_notice_date),
    )
    verified = verify_designation_identity(evidence, diagnostics=diagnostics)
    return {
        "target": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "official_designation_identity_verified": verified[
            "official_designation_identity_verified"
        ],
        "verification": verified,
        "provenance": {
            "source_url": source.source_url,
            "notice_number": source.notice_number,
            "issuing_authority": source.issuing_authority,
            "effective_or_notice_date": source.effective_or_notice_date,
        },
        "discovery_performed": False,
        "legal_inference_performed": False,
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
        "site_mutated": False,
    }
