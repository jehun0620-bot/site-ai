# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_council_official_record_source_family_terminal_reconciliation.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD"
NEXT_SOURCE_FAMILY = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT"

INPUTS = {
    "S228A": OUT_DIR / "development_density_management_area_seongnam_city_council_official_record_entry_search_contract_qualification.json",
    "S228B": OUT_DIR / "development_density_management_area_seongnam_city_council_root_bootstrap_route_recovery.json",
    "S228C": OUT_DIR / "development_density_management_area_seongnam_city_council_record_search_contract_qualification.json",
    "S228D": OUT_DIR / "development_density_management_area_seongnam_city_council_uqq700_bounded_target_search.json",
}


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY COUNCIL OFFICIAL RECORD SOURCE FAMILY TERMINAL RECONCILIATION - S228E")
    print("=" * 78)
    print("Purpose: reconcile S228A-D without additional HTTP/search activity")
    print("Council source-family closure is operational only, never legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    data = {name: load_json(path) for name, path in INPUTS.items()}
    a, b, c, d = data["S228A"], data["S228B"], data["S228C"], data["S228D"]

    official_entry_verified = bool(a.get("selected_official_entry") or a.get("summary", {}).get("official_entry_verified"))
    bootstrap_route_verified = b.get("classification") == "SEONGNAM_CITY_COUNCIL_ROOT_BOOTSTRAP_ROUTE_QUALIFIED"

    family_status = c.get("family_status", {})
    minutes_contract_verified = bool(family_status.get("MINUTES", {}).get("qualified"))
    agenda_contract_verified = bool(family_status.get("AGENDA", {}).get("qualified"))
    general_search_contract_verified = bool(family_status.get("SEARCH", {}).get("qualified"))
    qualified_contract_count = int(c.get("qualified_search_contract_count", 0) or 0)

    request_count = int(d.get("request_count", 0) or 0)
    counts = d.get("counts", {})
    exact_hit = int(counts.get("exact_hit", 0) or 0)
    variant_hit = int(counts.get("variant_hit", 0) or 0)
    weak_hit = int(counts.get("weak_hit", 0) or 0)
    target_anchor_count = exact_hit + variant_hit + weak_hit
    no_hit_count = int(counts.get("no_hit", 0) or 0)
    technical_unknown = int(counts.get("technical_unknown", 0) or 0)
    notice_identity_candidate_count = int(counts.get("notice_identity_candidate", 0) or 0)

    bounded_target_search_complete = (
        d.get("summary", {}).get("target_search_executed") is True
        and d.get("summary", {}).get("target_search_bounded") is True
        and request_count == 6
        and technical_unknown == 0
    )

    source_family_operationally_closed = all([
        official_entry_verified,
        bootstrap_route_verified,
        minutes_contract_verified,
        agenda_contract_verified,
        bounded_target_search_complete,
    ])

    legal_absence_established = False
    negative_evidence_allowed = False
    legal_absence_inference_allowed = False
    site_false_inference_allowed = False
    runtime_registration_allowed = False
    official_designation_identity_verified = False
    current_validity_verified = False
    site_spatial_inclusion_verified = False
    uqq700_final_resolution = "UNKNOWN"

    if source_family_operationally_closed:
        classification = "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD_SOURCE_FAMILY_OPERATIONALLY_CLOSED_NO_TARGET_ANCHOR"
        semantic = "OFFICIAL_COUNCIL_ENTRY_SEARCH_CONTRACTS_AND_BOUNDED_TARGET_SEARCH_WERE_COMPLETED_WITHOUT_A_UQQ700_HISTORICAL_ANCHOR_AND_WITHOUT_LEGAL_ABSENCE_INFERENCE"
        next_action = "MOVE_TO_NATIONAL_OR_REGIONAL_PLANNING_RESEARCH_DOCUMENT_SOURCE_FAMILY_AS_CONTEXT_AND_REVERSE_LOOKUP_ONLY_WHILE_KEEPING_UQQ700_UNKNOWN"
    else:
        classification = "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD_SOURCE_FAMILY_RECONCILIATION_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_MORE_REQUIRED_COUNCIL_SOURCE_FAMILY_QUALIFICATION_OR_BOUNDED_SEARCH_STATES_WERE_NOT_RECONCILED"
        next_action = "HARDEN_ONLY_THE_UNRECONCILED_COUNCIL_STAGE_WITHOUT_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-161-S228E",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "inputs": {k: str(v) for k, v in INPUTS.items()},
        "reconciliation": {
            "official_entry_verified": official_entry_verified,
            "bootstrap_route_verified": bootstrap_route_verified,
            "minutes_search_contract_verified": minutes_contract_verified,
            "agenda_search_contract_verified": agenda_contract_verified,
            "general_search_contract_verified": general_search_contract_verified,
            "qualified_search_contract_count": qualified_contract_count,
            "bounded_target_search_complete": bounded_target_search_complete,
            "bounded_target_request_count": request_count,
            "exact_hit_count": exact_hit,
            "variant_hit_count": variant_hit,
            "weak_hit_count": weak_hit,
            "target_anchor_count": target_anchor_count,
            "no_hit_count": no_hit_count,
            "technical_unknown_count": technical_unknown,
            "notice_identity_candidate_count": notice_identity_candidate_count,
            "source_family_operationally_closed": source_family_operationally_closed,
            "legal_absence_established": legal_absence_established,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "next_source_family": NEXT_SOURCE_FAMILY,
            "source_family_closure_is_operational_only": True,
            "council_no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": negative_evidence_allowed,
            "legal_absence_inference_allowed": legal_absence_inference_allowed,
            "site_false_inference_allowed": site_false_inference_allowed,
            "official_designation_identity_verified": official_designation_identity_verified,
            "current_validity_verified": current_validity_verified,
            "site_spatial_inclusion_verified": site_spatial_inclusion_verified,
            "runtime_registration_allowed": runtime_registration_allowed,
            "uqq700_final_resolution": uqq700_final_resolution,
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nRECONCILIATION")
    print("-" * 78)
    print(f"OFFICIAL ENTRY VERIFIED: {official_entry_verified}")
    print(f"BOOTSTRAP ROUTE VERIFIED: {bootstrap_route_verified}")
    print(f"MINUTES SEARCH CONTRACT VERIFIED: {minutes_contract_verified}")
    print(f"AGENDA SEARCH CONTRACT VERIFIED: {agenda_contract_verified}")
    print(f"GENERAL SEARCH CONTRACT VERIFIED: {general_search_contract_verified}")
    print(f"QUALIFIED SEARCH CONTRACT COUNT: {qualified_contract_count}")
    print(f"BOUNDED TARGET SEARCH COMPLETE: {bounded_target_search_complete}")
    print(f"BOUNDED TARGET REQUEST COUNT: {request_count}")
    print(f"EXACT HIT COUNT: {exact_hit}")
    print(f"VARIANT HIT COUNT: {variant_hit}")
    print(f"WEAK HIT COUNT: {weak_hit}")
    print(f"TARGET ANCHOR COUNT: {target_anchor_count}")
    print(f"NO HIT COUNT: {no_hit_count}")
    print(f"TECHNICAL UNKNOWN COUNT: {technical_unknown}")
    print(f"NOTICE IDENTITY CANDIDATE COUNT: {notice_identity_candidate_count}")
    print(f"SOURCE FAMILY OPERATIONALLY CLOSED: {source_family_operationally_closed}")
    print(f"LEGAL ABSENCE ESTABLISHED: {legal_absence_established}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print(f"Next source family: {NEXT_SOURCE_FAMILY}")
    print("Source-family closure is operational only: True")
    print("Council no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "all four inputs loaded": len(data) == 4,
        "official entry verified": official_entry_verified,
        "bootstrap route verified": bootstrap_route_verified,
        "minutes contract verified": minutes_contract_verified,
        "agenda contract verified": agenda_contract_verified,
        "bounded target search complete": bounded_target_search_complete,
        "exact six bounded requests": request_count == 6,
        "technical unknown zero": technical_unknown == 0,
        "source family operationally closed": source_family_operationally_closed,
        "legal absence not established": legal_absence_established is False,
        "operational closure only": out["summary"]["source_family_closure_is_operational_only"] is True,
        "council no-hit not legal absence": out["summary"]["council_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "next source family set": out["summary"]["next_source_family"] == NEXT_SOURCE_FAMILY,
        "classification emitted": classification in {
            "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD_SOURCE_FAMILY_OPERATIONALLY_CLOSED_NO_TARGET_ANCHOR",
            "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD_SOURCE_FAMILY_RECONCILIATION_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S228E validation failed")


if __name__ == "__main__":
    main()
