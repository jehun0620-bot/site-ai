# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"

IN_S230E = OUT_DIR / "development_density_management_area_gyeonggi_historical_local_gazette_notice_archive_alternate_entry_qualification.json"
IN_S230G = OUT_DIR / "development_density_management_area_gyeonggi_ebook_gazette_archive_uqq700_bounded_target_search.json"
IN_BOARD = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_ajax_uqq700_bounded_target_search.json"
OUT = OUT_DIR / "development_density_management_area_gyeonggi_historical_local_gazette_alternate_source_family_terminal_reconciliation.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_OR_NOTICE_ARCHIVE_ALTERNATE_ENTRY"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    print("=" * 78)
    print("GYEONGGI HISTORICAL LOCAL GAZETTE ALTERNATE SOURCE FAMILY TERMINAL RECONCILIATION - S230I")
    print("=" * 78)
    print("Purpose: reconcile the two qualified Gyeonggi alternate archive entries without new search")
    print("Operational closure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    s230e = load_json(IN_S230E)
    s230g = load_json(IN_S230G)
    board = load_json(IN_BOARD)

    qualified_entry_count = int(s230e.get("qualified_entry_count", 0) or 0)
    qualified_ids = []
    for row in s230e.get("entries", s230e.get("results", [])) or []:
        if row.get("entry_qualified"):
            qualified_ids.append(row.get("source_id"))

    ebook_ok = (
        s230g.get("classification") == "GYEONGGI_EBOOK_GAZETTE_UQQ700_BOUNDED_SEARCH_NO_VERIFIED_TARGET_RESULT"
        and int(s230g.get("technical_unknown_query_count", 0) or 0) == 0
        and int(s230g.get("verified_result_row_hit_count", 0) or 0) == 0
        and int(s230g.get("verified_detail_target_hit_count", 0) or 0) == 0
    )

    board_ok = (
        board.get("classification") == "GYEONGGI_GAZETTE_BOARD_UQQ700_BOUNDED_SEARCH_NO_VERIFIED_TARGET_RESULT"
        and int(board.get("technical_unknown_query_count", 0) or 0) == 0
        and int(board.get("verified_result_row_hit_count", 0) or 0) == 0
    )

    entries_qualified = qualified_entry_count >= 2
    family_operationally_closed = bool(entries_qualified and ebook_ok and board_ok)

    if family_operationally_closed:
        classification = "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_ALTERNATE_SOURCE_FAMILY_OPERATIONALLY_CLOSED_NO_VERIFIED_UQQ700_TARGET"
        semantic = "BOTH_QUALIFIED_ALTERNATE_GYEONGGI_GAZETTE_ARCHIVE_ENTRIES_COMPLETED_BOUNDED_TARGET_SEARCH_WITHOUT_VERIFIED_TARGET_RESULT_OR_TECHNICAL_UNKNOWN"
        next_action = "RERANK_REMAINING_RESIDUAL_SOURCE_FAMILIES_WITHOUT_REPEATING_GYEONGGI_ALTERNATE_GAZETTE_SEARCHES"
    else:
        classification = "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_ALTERNATE_SOURCE_FAMILY_NOT_TERMINALLY_RECONCILED"
        semantic = "ONE_OR_MORE_REQUIRED_QUALIFICATION_OR_BOUNDED_SEARCH_TERMINAL_CONDITIONS_WERE_NOT_MET"
        next_action = "HARDEN_ONLY_THE_UNSATISFIED_GYEONGGI_ALTERNATE_ARCHIVE_CONDITION_WITHOUT_NEGATIVE_OR_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP 17-S230I",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s230e_loaded": True,
        "s230g_loaded": True,
        "board_target_loaded": True,
        "new_http_search_executed": False,
        "qualified_entry_count": qualified_entry_count,
        "qualified_entry_ids": qualified_ids,
        "ebook_terminal_no_hit": ebook_ok,
        "board_terminal_no_hit": board_ok,
        "family_operationally_closed": family_operationally_closed,
        "repeat_gyeonggi_alternate_search_allowed": False,
        "carry_forward": [
            "KRIHS_SEARCH_CONTRACT_ACCESS",
            "MOLIT_ENTRY_ACCESS",
            "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE_LEGACY_PDF_BINARY_ACCESS_TECHNICAL_UNKNOWN_6",
        ],
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
    print("RECONCILIATION")
    print("=" * 78)
    print(f"QUALIFIED ENTRY COUNT: {qualified_entry_count}")
    print(f"QUALIFIED ENTRY IDS: {qualified_ids}")
    print(f"EBOOK TERMINAL NO-HIT: {ebook_ok}")
    print(f"GG BOARD TERMINAL NO-HIT: {board_ok}")
    print(f"FAMILY OPERATIONALLY CLOSED: {family_operationally_closed}")
    print("REPEAT GYEONGGI ALTERNATE SEARCH ALLOWED: False")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Operational closure == legal absence: False")
    print("No-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "source family correct": out["source_family"] == SOURCE_FAMILY,
        "S230E loaded": out["s230e_loaded"] is True,
        "S230G loaded": out["s230g_loaded"] is True,
        "board target loaded": out["board_target_loaded"] is True,
        "no new HTTP search": out["new_http_search_executed"] is False,
        "repeat search disabled": out["repeat_gyeonggi_alternate_search_allowed"] is False,
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
        "classification emitted": classification in {
            "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_ALTERNATE_SOURCE_FAMILY_OPERATIONALLY_CLOSED_NO_VERIFIED_UQQ700_TARGET",
            "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_ALTERNATE_SOURCE_FAMILY_NOT_TERMINALLY_RECONCILED",
        },
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for key, value in validation.items():
        print(f"{key}: {value}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")
    if not all(validation.values()):
        raise AssertionError("S230I terminal reconciliation validation failed")


if __name__ == "__main__":
    main()
