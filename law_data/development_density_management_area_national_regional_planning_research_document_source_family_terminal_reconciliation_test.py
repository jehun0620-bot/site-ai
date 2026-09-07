# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_S229A = OUT_DIR / "development_density_management_area_national_regional_planning_research_document_source_family_entry_qualification.json"
IN_S229B = OUT_DIR / "development_density_management_area_national_regional_planning_research_document_positive_control_search_contract_qualification.json"
IN_S229C = OUT_DIR / "development_density_management_area_national_regional_planning_research_document_uqq700_bounded_target_search.json"
IN_S229D = OUT_DIR / "development_density_management_area_national_regional_planning_research_document_uqq700_search_result_semantic_hardening.json"
OUT = OUT_DIR / "development_density_management_area_national_regional_planning_research_document_source_family_terminal_reconciliation.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT"


def load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    print("=" * 78)
    print("NATIONAL / REGIONAL PLANNING RESEARCH DOCUMENT SOURCE FAMILY TERMINAL RECONCILIATION - S229E")
    print("=" * 78)
    print("Purpose: reconcile S229A-D without additional HTTP search")
    print("Source-family closure is operational only, never legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    s229a = load(IN_S229A)
    s229b = load(IN_S229B)
    s229c = load(IN_S229C)
    s229d = load(IN_S229D)

    qualified_entry_count = int(s229a.get("qualified_entry_count") or 0)
    canonical_contract_count = int(s229b.get("canonical_qualified_search_contract_count") or 0)
    request_count = int(s229c.get("request_count") or 0)
    verified_exact = int(s229d.get("verified_exact_hit_count") or 0)
    verified_variant = int(s229d.get("verified_variant_hit_count") or 0)
    verified_weak = int(s229d.get("verified_weak_hit_count") or 0)
    verified_candidates = int(s229d.get("verified_result_candidate_count") or 0)
    notice_identity_literals = int(s229d.get("notice_identity_literal_count") or 0)
    technical_unknown_count = int(s229d.get("technical_unknown_count") or 0)

    source_family_operationally_closed = (
        qualified_entry_count >= 1
        and canonical_contract_count >= 1
        and request_count == 6
        and technical_unknown_count == 0
    )

    classification = (
        "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_SOURCE_FAMILY_OPERATIONALLY_CLOSED_NO_VERIFIED_TARGET_ANCHOR"
        if source_family_operationally_closed and verified_exact == 0 and verified_variant == 0 and verified_weak == 0
        else "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_SOURCE_FAMILY_RECONCILIATION_REQUIRES_REVIEW"
    )

    semantic = (
        "QUALIFIED_PLANNING_RESEARCH_ENTRIES_SEARCH_CONTRACTS_BOUNDED_TARGET_SEARCH_AND_ECHO_HARDENING_COMPLETED_WITHOUT_A_VERIFIED_UQQ700_RESULT_ANCHOR_AND_WITHOUT_LEGAL_ABSENCE_INFERENCE"
        if source_family_operationally_closed
        else "SOURCE_FAMILY_RECONCILIATION_COULD_NOT_BE_CLOSED_CLEANLY_AND_REQUIRES_REVIEW_WITHOUT_NEGATIVE_INFERENCE"
    )

    next_action = (
        "RETURN_TO_SOURCE_FAMILY_RERANKING_OR_HISTORICAL_OFFICIAL_NOTICE_REVERSE_LOOKUP_WITH_UQQ700_REMAINING_UNKNOWN"
        if source_family_operationally_closed
        else "REVIEW_ONLY_THE_UNRESOLVED_RECONCILIATION_CONDITION_AND_KEEP_UQQ700_UNKNOWN"
    )

    out = {
        "step": "STEP 17-21-C-16-8-T-165-S229E",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "inputs": {
            "S229A": str(IN_S229A),
            "S229B": str(IN_S229B),
            "S229C": str(IN_S229C),
            "S229D": str(IN_S229D),
        },
        "qualified_entry_count": qualified_entry_count,
        "canonical_qualified_search_contract_count": canonical_contract_count,
        "bounded_target_request_count": request_count,
        "verified_exact_hit_count": verified_exact,
        "verified_variant_hit_count": verified_variant,
        "verified_weak_hit_count": verified_weak,
        "verified_result_candidate_count": verified_candidates,
        "notice_identity_literal_count": notice_identity_literals,
        "technical_unknown_count": technical_unknown_count,
        "source_family_operationally_closed": source_family_operationally_closed,
        "legal_absence_established": False,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "additional_http_search_executed": False,
            "source_family_closure_operational_only": True,
            "planning_research_hit_equals_designation_notice": False,
            "planning_research_hit_equals_current_validity": False,
            "planning_research_hit_equals_site_inclusion": False,
            "planning_research_no_hit_equals_legal_absence": False,
            "search_failure_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"QUALIFIED ENTRY COUNT: {qualified_entry_count}")
    print(f"CANONICAL SEARCH CONTRACT COUNT: {canonical_contract_count}")
    print(f"BOUNDED TARGET REQUEST COUNT: {request_count}")
    print(f"VERIFIED EXACT HIT COUNT: {verified_exact}")
    print(f"VERIFIED VARIANT HIT COUNT: {verified_variant}")
    print(f"VERIFIED WEAK HIT COUNT: {verified_weak}")
    print(f"VERIFIED RESULT CANDIDATE COUNT: {verified_candidates}")
    print(f"NOTICE IDENTITY LITERAL COUNT: {notice_identity_literals}")
    print(f"TECHNICAL UNKNOWN COUNT: {technical_unknown_count}")
    print(f"SOURCE FAMILY OPERATIONALLY CLOSED: {source_family_operationally_closed}")
    print("LEGAL ABSENCE ESTABLISHED: False")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Additional HTTP search executed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S229A loaded": IN_S229A.exists(),
        "S229B loaded": IN_S229B.exists(),
        "S229C loaded": IN_S229C.exists(),
        "S229D loaded": IN_S229D.exists(),
        "no additional HTTP search": out["summary"]["additional_http_search_executed"] is False,
        "operational closure only": out["summary"]["source_family_closure_operational_only"] is True,
        "planning research hit not designation": out["summary"]["planning_research_hit_equals_designation_notice"] is False,
        "planning research hit not validity": out["summary"]["planning_research_hit_equals_current_validity"] is False,
        "planning research hit not site inclusion": out["summary"]["planning_research_hit_equals_site_inclusion"] is False,
        "planning research no-hit not legal absence": out["summary"]["planning_research_no_hit_equals_legal_absence"] is False,
        "search failure not legal absence": out["summary"]["search_failure_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "legal absence not established": out["legal_absence_established"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_SOURCE_FAMILY_OPERATIONALLY_CLOSED_NO_VERIFIED_TARGET_ANCHOR",
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_SOURCE_FAMILY_RECONCILIATION_REQUIRES_REVIEW",
        },
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for k, v in validation.items():
        print(f"{k}: {v}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")
    if not all(validation.values()):
        raise AssertionError("S229E validation failed")


if __name__ == "__main__":
    main()
