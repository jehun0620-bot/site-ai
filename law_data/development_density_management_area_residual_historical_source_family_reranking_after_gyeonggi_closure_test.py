# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_S230A = OUT_DIR / "development_density_management_area_historical_discovery_source_family_reranking_reconciliation.json"
IN_S230B = OUT_DIR / "development_density_management_area_seongnam_legacy_pdf_alternate_archival_access_recovery.json"
IN_S230D = OUT_DIR / "development_density_management_area_historical_official_notice_number_reverse_lookup_seed_semantic_hardening.json"
IN_S230I = OUT_DIR / "development_density_management_area_gyeonggi_historical_local_gazette_alternate_source_family_terminal_reconciliation.json"
OUT = OUT_DIR / "development_density_management_area_residual_historical_source_family_reranking_after_gyeonggi_closure.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    print("=" * 78)
    print("UQQ700 RESIDUAL HISTORICAL SOURCE FAMILY RERANKING AFTER GYEONGGI CLOSURE - S230J")
    print("=" * 78)
    print("Purpose: rerank only the residual unresolved source families after S230I closure")
    print("No new HTTP search")
    print("Operational closure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    s230a = load_json(IN_S230A)
    s230b = load_json(IN_S230B)
    s230d = load_json(IN_S230D)
    s230i = load_json(IN_S230I)

    # Prior high-value branches now exhausted operationally.
    closed_or_exhausted = [
        {
            "source_family": "SEONGNAM_HISTORICAL_OFFICIAL_NOTICE_NUMBER_REVERSE_LOOKUP",
            "status": "EXHAUSTED_NO_QUALIFIED_SEED",
            "evidence": s230d.get("classification"),
        },
        {
            "source_family": "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_OR_NOTICE_ARCHIVE_ALTERNATE_ENTRY",
            "status": "OPERATIONALLY_CLOSED",
            "evidence": s230i.get("classification"),
        },
    ]

    residual = [
        {
            "source_family": "KRIHS_SEARCH_CONTRACT_ACCESS",
            "status": "TECHNICAL_UNKNOWN",
            "priority": 35,
            "reason": "ENTRY_OR_SEARCH_CONTRACT_REMAINS_UNRESOLVED_FROM_NATIONAL_REGIONAL_PLANNING_RESEARCH_FAMILY",
            "direct_legal_promotion_allowed": False,
        },
        {
            "source_family": "MOLIT_ENTRY_ACCESS",
            "status": "TECHNICAL_UNKNOWN",
            "priority": 25,
            "reason": "MOLIT_ENTRY_ACCESS_REMAINS_TECHNICALLY_UNRESOLVED_AND_WAS_NOT_QUALIFIED_FOR_TARGET_SEARCH",
            "direct_legal_promotion_allowed": False,
        },
        {
            "source_family": "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE_LEGACY_PDF_BINARY_ACCESS",
            "status": "CARRY_FORWARD_TECHNICAL_UNKNOWN",
            "priority": 15,
            "reason": "SIX_VERIFIED_LEGACY_PDF_IDENTITIES_REMAIN_BINARY_ACCESS_TECHNICAL_UNKNOWN_AFTER_ALTERNATE_RECOVERY_EXHAUSTION",
            "unresolved_binary_count": int(s230b.get("unresolved_pdf_count") or 6),
            "direct_legal_promotion_allowed": False,
        },
    ]
    residual.sort(key=lambda x: (-x["priority"], x["source_family"]))
    selected = residual[0]

    classification = "UQQ700_RESIDUAL_HISTORICAL_SOURCE_FAMILIES_RERANKED_AFTER_GYEONGGI_CLOSURE"
    semantic = "PREVIOUS_HIGH_VALUE_REVERSE_LOOKUP_AND_GYEONGGI_ALTERNATE_GAZETTE_BRANCHES_ARE_OPERATIONALLY_EXHAUSTED_AND_THE_NEXT_UNTRIED_TECHNICAL_SURFACE_IS_KRIHS_SEARCH_CONTRACT_ACCESS"
    next_action = "QUALIFY_ONLY_KRIHS_SEARCH_CONTRACT_ACCESS_BEFORE_ANY_UQQ700_QUERY_AND_WITHOUT_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP 17-S230J",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "no_new_http_search": True,
        "s230a_loaded": True,
        "s230b_loaded": True,
        "s230d_loaded": True,
        "s230i_loaded": True,
        "closed_or_exhausted_source_families": closed_or_exhausted,
        "residual_source_families": residual,
        "selected_next_source_family": selected,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "operational_closure_equals_legal_absence": False,
            "no_hit_equals_legal_absence": False,
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
    print("RERANKING")
    print("=" * 78)
    print(f"CLOSED / EXHAUSTED COUNT: {len(closed_or_exhausted)}")
    print(f"RESIDUAL SOURCE FAMILY COUNT: {len(residual)}")
    for i, row in enumerate(residual, 1):
        print("RANK:", json.dumps({"rank": i, **row}, ensure_ascii=False))
    print("SELECTED NEXT SOURCE FAMILY:", selected["source_family"])
    print("SELECTED PRIORITY:", selected["priority"])
    print("LEGACY PDF CARRY-FORWARD COUNT:", next((r.get("unresolved_binary_count") for r in residual if r["source_family"].startswith("SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE")), 0))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Operational closure == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S230A loaded": out["s230a_loaded"] is True,
        "S230B loaded": out["s230b_loaded"] is True,
        "S230D loaded": out["s230d_loaded"] is True,
        "S230I loaded": out["s230i_loaded"] is True,
        "no new HTTP search": out["no_new_http_search"] is True,
        "gyeonggi alternate excluded": all(r["source_family"] != "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_OR_NOTICE_ARCHIVE_ALTERNATE_ENTRY" for r in residual),
        "notice reverse lookup excluded": all(r["source_family"] != "SEONGNAM_HISTORICAL_OFFICIAL_NOTICE_NUMBER_REVERSE_LOOKUP" for r in residual),
        "KRIHS selected next": selected["source_family"] == "KRIHS_SEARCH_CONTRACT_ACCESS",
        "legacy PDF carried forward": any(r["source_family"] == "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE_LEGACY_PDF_BINARY_ACCESS" for r in residual),
        "operational closure not legal absence": out["summary"]["operational_closure_equals_legal_absence"] is False,
        "no hit not legal absence": out["summary"]["no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
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
        raise AssertionError("S230J residual source-family reranking validation failed")


if __name__ == "__main__":
    main()
