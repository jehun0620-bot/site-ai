# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
S225 = OUT_DIR / "development_density_management_area_local_gosi_official_entry_contract_forensic.json"
S225A = OUT_DIR / "development_density_management_area_local_gosi_official_html_js_structure_forensic.json"
S225B = OUT_DIR / "development_density_management_area_local_gosi_official_nf_form_entry_gate_replay.json"
S225C = OUT_DIR / "development_density_management_area_local_gosi_official_source_role_qualification.json"
OUT = OUT_DIR / "development_density_management_area_local_gosi_official_terminal_reconciliation.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "LOCAL_GOSI_OFFICIAL"

EXPECTED_S225 = {
    "LOCAL_GOSI_OFFICIAL_ENTRY_QUALIFIED_SEARCH_CONTRACT_UNRESOLVED",
    "LOCAL_GOSI_OFFICIAL_ENTRY_QUALIFIED_SEARCH_CONTRACT_PARTIAL",
    "LOCAL_GOSI_OFFICIAL_ENTRY_AND_POSITIVE_CONTROL_SEARCH_CONTRACT_QUALIFIED",
}
EXPECTED_S225A = "LOCAL_GOSI_OFFICIAL_HTML_JS_SEARCH_NAVIGATION_HINTS_RECOVERED"
EXPECTED_S225B = "LOCAL_GOSI_OFFICIAL_NF_FORM_ENTRY_GATE_REPLAY_APPLICATION_SURFACE_RECOVERED"
EXPECTED_S225C = "LOCAL_GOSI_SOURCE_ROLE_EXAM_RECRUITMENT_SERVICE_ONLY"
TERMINAL_CLASSIFICATION = "LOCAL_GOSI_OFFICIAL_SOURCE_FAMILY_EXCLUDED_BY_SOURCE_ROLE_WITHOUT_LEGAL_ABSENCE_INFERENCE"
TERMINAL_SEMANTIC = "LOCAL_GOSI_OFFICIAL_SOURCE_ROLE_MISMATCH_TERMINALLY_RECONCILED_WITHOUT_LEGAL_ABSENCE_INFERENCE"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    print("=" * 78)
    print("LOCAL GOSI OFFICIAL TERMINAL RECONCILIATION - S225D")
    print("=" * 78)
    print("Purpose: reconcile S225-S225C and close LOCAL_GOSI_OFFICIAL by source-role mismatch only")
    print("Network request: NOT EXECUTED")
    print("Search request: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Search no-hit != legal absence")
    print("Source-role mismatch != legal absence")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s225 = load(S225)
    s225a = load(S225A)
    s225b = load(S225B)
    s225c = load(S225C)

    gate_225 = (
        s225.get("classification") in EXPECTED_S225
        and (s225.get("summary") or {}).get("target_query_executed") is False
        and (s225.get("summary") or {}).get("legal_absence_inference_allowed") is False
        and (s225.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    gate_225a = (
        s225a.get("classification") == EXPECTED_S225A
        and (s225a.get("summary") or {}).get("search_request_executed") is False
        and (s225a.get("summary") or {}).get("target_query_executed") is False
        and (s225a.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    gate_225b = (
        s225b.get("classification") == EXPECTED_S225B
        and (s225b.get("replay") or {}).get("same_official_host") is True
        and (s225b.get("replay") or {}).get("post_gate_application_surface_recovered") is True
        and (s225b.get("summary") or {}).get("search_request_executed") is False
        and (s225b.get("summary") or {}).get("target_query_executed") is False
        and (s225b.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    role = s225c.get("role_signals") or {}
    gate_225c = (
        s225c.get("classification") == EXPECTED_S225C
        and role.get("pages_ok") is True
        and role.get("general_official_notice_role_signal") is False
        and role.get("exam_recruitment_role_signal") is True
        and role.get("source_role") == "EXAM_RECRUITMENT_SERVICE"
        and role.get("target_search_eligible") is False
        and (s225c.get("summary") or {}).get("target_query_executed") is False
        and (s225c.get("summary") or {}).get("legal_absence_inference_allowed") is False
        and (s225c.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )

    gates = {
        "S225_entry_surface": gate_225,
        "S225A_structure_forensic": gate_225a,
        "S225B_nf_form_gate_replay": gate_225b,
        "S225C_source_role": gate_225c,
    }
    all_gates = all(gates.values())

    superseded = [
        {
            "step": "S225A",
            "status": "DIAGNOSTIC_ONLY",
            "reason": "generic jQuery/NetFunnel function-name matches produced search-navigation hints without a real search endpoint; not inherited as a search contract",
        },
        {
            "step": "S225B_INITIAL_RUN",
            "status": "SUPERSEDED",
            "reason": "netloc comparison treated https default port :443 as a different host; corrected by hostname normalization before terminal reconciliation",
        },
    ]

    operational_closure = bool(all_gates)
    classification = TERMINAL_CLASSIFICATION if operational_closure else "LOCAL_GOSI_OFFICIAL_TERMINAL_RECONCILIATION_UNRESOLVED"
    semantic = TERMINAL_SEMANTIC if operational_closure else "LOCAL_GOSI_OFFICIAL_TERMINAL_RECONCILIATION_GATES_UNRESOLVED"
    next_action = (
        "PROCEED_TO_NEXT_QUALIFIED_OFFICIAL_SOURCE_FAMILY_WITH_UQQ700_UNKNOWN"
        if operational_closure
        else "HARDEN_LOCAL_GOSI_TERMINAL_GATES_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    )

    out = {
        "step": "STEP 17-21-C-16-8-T-140-S225D",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "network_request_executed": False,
        "source_gates": gates,
        "superseded_or_diagnostic": superseded,
        "source_role": "EXAM_RECRUITMENT_SERVICE" if operational_closure else "UNRESOLVED",
        "target_search_eligible": False,
        "operational_source_family_closure": operational_closure,
        "closure_basis": "SOURCE_ROLE_MISMATCH_ONLY" if operational_closure else "UNRESOLVED",
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "search_request_executed": False,
            "positive_control_search_executed": False,
            "target_query_executed": False,
            "source_role_mismatch_equals_legal_absence": False,
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

    print("\nSOURCE GATES")
    for name, value in gates.items():
        print(f"{name}: {value}")

    print("\nSUPERSEDED / DIAGNOSTIC")
    for item in superseded:
        print(f"{item['step']}: {item['status']} | {item['reason']}")

    print("\nTERMINAL SUMMARY")
    print("SOURCE ROLE:", out["source_role"])
    print("TARGET SEARCH ELIGIBLE:", out["target_search_eligible"])
    print("CLOSURE BASIS:", out["closure_basis"])
    print("OPERATIONAL SOURCE-FAMILY CLOSURE:", operational_closure)
    print("CLASSIFICATION:", classification)

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Network request executed: False")
    print("Search request executed: False")
    print("Target query executed: False")
    print("Source-role mismatch equals legal absence: False")
    print("Search no-hit equals legal absence: False")
    print("Negative evidence allowed: False")
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S225 verified": gate_225,
        "S225A verified": gate_225a,
        "S225B verified": gate_225b,
        "S225C verified": gate_225c,
        "network not executed": out["network_request_executed"] is False,
        "closure derived only from verified gates": operational_closure is all_gates,
        "source role mismatch only": out["closure_basis"] == "SOURCE_ROLE_MISMATCH_ONLY" if operational_closure else True,
        "target search ineligible": out["target_search_eligible"] is False,
        "search not executed": out["summary"]["search_request_executed"] is False,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "source-role mismatch not legal absence": out["summary"]["source_role_mismatch_equals_legal_absence"] is False,
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
        raise AssertionError("S225D local.gosi.go.kr terminal reconciliation failed")


if __name__ == "__main__":
    main()
