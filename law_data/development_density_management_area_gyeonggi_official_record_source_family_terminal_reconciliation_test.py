# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"

S222 = OUT_DIR / "development_density_management_area_gyeonggi_official_record_search_contract_forensic.json"
S223D = OUT_DIR / "development_density_management_area_gyeonggi_official_record_category_token_replay.json"
S223F = OUT_DIR / "development_density_management_area_gyeonggi_official_record_detail_metadata_hardening.json"
S224A = OUT_DIR / "development_density_management_area_gyeonggi_official_record_uqq700_no_hit_structure_forensic.json"
S224B = OUT_DIR / "development_density_management_area_gyeonggi_official_record_bounded_query_coverage_review.json"

OUT = OUT_DIR / "development_density_management_area_gyeonggi_official_record_source_family_terminal_reconciliation.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"

EXPECTED_S224B_CLASSIFICATION = (
    "GYEONGGI_OFFICIAL_RECORD_BOUNDED_SEARCH_OPERATIONALLY_CLOSED_WITHOUT_LEGAL_ABSENCE_INFERENCE"
)
EXPECTED_S224A_CLASSIFICATION = (
    "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_NO_HIT_DOM_CONTRACT_VERIFIED_WITHOUT_LEGAL_ABSENCE_INFERENCE"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    print("=" * 78)
    print("GYEONGGI OFFICIAL RECORD SOURCE-FAMILY TERMINAL RECONCILIATION - S224C")
    print("=" * 78)
    print("Purpose: reconcile verified Gyeonggi source-family evidence into terminal operational closure")
    print("Network request: NOT EXECUTED")
    print("Operational closure != legal absence")
    print("Search no-hit != SITE FALSE")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s222 = load(S222)
    s223d = load(S223D)
    s223f = load(S223F)
    s224a = load(S224A)
    s224b = load(S224B)

    gate_222 = (
        s222.get("classification") == "GYEONGGI_OFFICIAL_SEARCH_SURFACE_POSITIVE_CONTROL_QUALIFIED"
        and (s222.get("summary") or {}).get("target_query_executed") is False
        and (s222.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
        and s222.get("official_designation_identity_verified") is False
    )

    gate_223d = (
        s223d.get("classification") == "GYEONGGI_OFFICIAL_RECORD_ACTUAL_CATEGORY_TOKEN_REAL_RESULT_DOM_QUALIFIED"
        and (s223d.get("summary") or {}).get("target_query_executed") is False
        and (s223d.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )

    gate_223f = (
        s223f.get("classification") == "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_METADATA_HARDENED_QUALIFIED"
        and (s223f.get("summary") or {}).get("target_query_executed") is False
        and (s223f.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
        and s223f.get("official_designation_identity_verified") is False
    )

    gate_224a = (
        s224a.get("classification") == EXPECTED_S224A_CLASSIFICATION
        and (s224a.get("forensic") or {}).get("no_hit_dom_contract_verified") is True
        and (s224a.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )

    coverage = s224b.get("coverage") or {}
    summary_b = s224b.get("summary") or {}
    gate_224b = (
        s224b.get("classification") == EXPECTED_S224B_CLASSIFICATION
        and coverage.get("query_count") == 6
        and coverage.get("query_no_hit_count") == 6
        and coverage.get("query_hit_count") == 0
        and coverage.get("query_unknown_count") == 0
        and coverage.get("canonical_candidate_count") == 0
        and coverage.get("bounded_search_exhausted") is True
        and summary_b.get("uqq700_final_resolution") == "UNKNOWN"
    )

    source_gates = {
        "S222_search_entry_contract": gate_222,
        "S223D_real_result_dom_contract": gate_223d,
        "S223F_detail_identity_contract": gate_223f,
        "S224A_exact_target_technical_no_hit_contract": gate_224a,
        "S224B_bounded_query_coverage_exhausted": gate_224b,
    }

    all_source_gates = all(source_gates.values())

    superseded = {
        "S223": {
            "status": "SUPERSEDED",
            "reason": "global navigation/result identity false positive; not inherited",
        },
        "S223A": {
            "status": "SUPERSEDED",
            "reason": "sorting/rank candidate false positive; not inherited",
        },
        "S223B": {
            "status": "SUPERSEDED",
            "reason": "global menu-tree candidate false positive; not inherited",
        },
        "S223C": {
            "status": "DIAGNOSTIC_ONLY",
            "reason": "verified bounded region under wrong display-label token; led to actual token recovery in S223D",
        },
    }

    if all_source_gates:
        classification = "GYEONGGI_OFFICIAL_RECORD_SOURCE_FAMILY_OPERATIONALLY_CLOSED_WITHOUT_LEGAL_ABSENCE_INFERENCE"
        semantic = "GYEONGGI_OFFICIAL_RECORD_TERMINAL_OPERATIONAL_CLOSURE_VERIFIED_WITHOUT_LEGAL_ABSENCE_INFERENCE"
        next_action = "PROCEED_TO_LOCAL_GOSI_OFFICIAL_SOURCE_FAMILY_QUALIFICATION_WITH_UQQ700_UNKNOWN"
        operational_source_family_closure = True
    else:
        classification = "GYEONGGI_OFFICIAL_RECORD_SOURCE_FAMILY_TERMINAL_RECONCILIATION_UNRESOLVED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_TERMINAL_RECONCILIATION_UNRESOLVED"
        next_action = "RESOLVE_FAILED_GYEONGGI_SOURCE_GATE_BEFORE_SOURCE_FAMILY_TRANSITION"
        operational_source_family_closure = False

    out = {
        "step": "STEP 17-21-C-16-8-T-135-S224C",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": "GYEONGGI_OFFICIAL_RECORD",
        "network_request_executed": False,
        "source_gates": source_gates,
        "superseded_or_diagnostic_steps": superseded,
        "verified_chain": ["S222", "S223D", "S223F", "S224A", "S224B"],
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "operational_source_family_closure": operational_source_family_closure,
            "bounded_query_count": coverage.get("query_count"),
            "bounded_query_technical_no_hit_count": coverage.get("query_no_hit_count"),
            "bounded_query_hit_count": coverage.get("query_hit_count"),
            "bounded_query_unresolved_count": coverage.get("query_unknown_count"),
            "canonical_candidate_count": coverage.get("canonical_candidate_count"),
            "bounded_search_exhausted": coverage.get("bounded_search_exhausted"),
            "search_hit_equals_legal_fact": False,
            "search_hit_equals_designation_identity": False,
            "search_no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "official_designation_identity_verified": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("SOURCE GATES")
    for name, value in source_gates.items():
        print(f"{name}: {value}")

    print("\nSUPERSEDED / DIAGNOSTIC")
    for step, meta in superseded.items():
        print(f"{step}: {meta['status']} | {meta['reason']}")

    print("\nTERMINAL SUMMARY")
    print("BOUNDED QUERY COUNT:", coverage.get("query_count"))
    print("BOUNDED TECHNICAL NO-HIT COUNT:", coverage.get("query_no_hit_count"))
    print("BOUNDED HIT COUNT:", coverage.get("query_hit_count"))
    print("BOUNDED UNRESOLVED COUNT:", coverage.get("query_unknown_count"))
    print("CANONICAL CANDIDATE COUNT:", coverage.get("canonical_candidate_count"))
    print("BOUNDED SEARCH EXHAUSTED:", coverage.get("bounded_search_exhausted"))
    print("OPERATIONAL SOURCE-FAMILY CLOSURE:", operational_source_family_closure)
    print("CLASSIFICATION:", classification)

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Network request executed: False")
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S222 verified": gate_222,
        "S223D verified": gate_223d,
        "S223F verified": gate_223f,
        "S224A verified": gate_224a,
        "S224B verified": gate_224b,
        "network not executed": out["network_request_executed"] is False,
        "operational closure derived only from verified gates": (
            out["summary"]["operational_source_family_closure"] is all_source_gates
        ),
        "search hit not legal fact": out["summary"]["search_hit_equals_legal_fact"] is False,
        "search hit not designation identity": out["summary"]["search_hit_equals_designation_identity"] is False,
        "search no-hit not legal absence": out["summary"]["search_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["official_designation_identity_verified"] is False,
        "current validity not promoted": out["current_validity_verified"] is False,
        "site inclusion not promoted": out["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": not out["site_positive_allowed"] and not out["site_negative_allowed"],
        "runtime registration blocked": out["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nVALIDATION")
    for name, value in checks.items():
        print(f"{name}: {value}")
    print("all_pass:", all(checks.values()))

    if not all(checks.values()):
        raise AssertionError("S224C Gyeonggi terminal reconciliation failed")


if __name__ == "__main__":
    main()
