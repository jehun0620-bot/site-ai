# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-3B-3
개발밀도관리구역 evidence consolidation / current-state resolution

현재 정책
======================================================================
개발밀도관리구역(UQQ700)은 HYBRID_SPATIAL_NOTICE 대상이다.
검색 no-hit, 후보 layer no-hit, SITE 페이지 미표시는 진단 evidence로만 보존한다.
이러한 negative evidence만으로 legal absence 또는 SITE FALSE를 추론하지 않는다.

따라서 official designation identity / current validity / SITE spatial inclusion의
3개 positive registration gate가 검증되기 전까지 current-state는 UNKNOWN을 유지한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from hybrid_spatial_notice_uqq700_production_adapter import (
    Uqq700ProductionAdapterInput,
    adapt_uqq700_production_state,
)


STEP_NAME = (
    "STEP 17-21-C-10-3B-3 "
    "개발밀도관리구역 evidence resolution"
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"

ANNOUNCEMENT_PATH = OUTPUT_DIR / "development_density_management_announcement_full_probe.json"
UQ145_PATH = OUTPUT_DIR / "development_density_uq145_probe.json"
SEOUL_PROBE_PATH = OUTPUT_DIR / "seoul_development_density_management_area_probe.json"
PREVIOUS_RESOLUTION_PATH = OUTPUT_DIR / "development_density_management_resolution.json"
RULE_OVERLAY_PATH = OUTPUT_DIR / "site_rule_evaluation_condition_overlay.json"
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_evidence_resolution.json"

SITE = {
    "site_id": "11680-10300-0012-0000",
    "address": "서울특별시 강남구 개포동 12번지",
    "zone": "제3종일반주거지역",
}


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"입력 파일 없음: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def main() -> int:
    announcement = load_json(ANNOUNCEMENT_PATH)
    uq145 = load_json(UQ145_PATH)
    seoul_probe = load_json(SEOUL_PROBE_PATH)
    previous = load_json(PREVIOUS_RESOLUTION_PATH)
    overlay = load_json(RULE_OVERLAY_PATH)

    announcement_api = announcement.get("api", {})
    announcement_search = announcement.get("search", {})

    announcement_query_status = announcement_api.get("query_status")
    announcement_result_code = announcement_api.get("result_code")
    announcement_total = safe_int(announcement_api.get("total_count"))
    announcement_received = safe_int(announcement_api.get("received_rows"))
    exact_hit_count = safe_int(announcement_search.get("exact_hit_count"))
    site_exact_hit_count = safe_int(announcement_search.get("site_exact_hit_count"))
    broad_hit_count = safe_int(announcement_search.get("broad_hit_count"))

    announcement_success = (
        announcement_query_status == "QUERY_SUCCESS"
        and announcement_result_code == "INFO-000"
        and announcement_total > 0
        and announcement_received == announcement_total
    )
    announcement_negative = (
        announcement_success
        and exact_hit_count == 0
        and site_exact_hit_count == 0
        and broad_hit_count == 0
    )

    uq145_layer = uq145.get("layer", {})
    uq145_target_search = uq145.get("target_search", {})
    uq145_resolution = uq145.get("resolution", {})

    uq145_feature_count = safe_int(uq145_layer.get("feature_count"))
    uq145_exact_hits = safe_int(uq145_target_search.get("exact_hit_count"))
    uq145_contains_hits = safe_int(uq145_target_search.get("contains_hit_count"))
    uq145_query_success = uq145_resolution.get("query_status") == "QUERY_SUCCESS"
    uq145_negative = (
        uq145_query_success
        and uq145_feature_count > 0
        and uq145_exact_hits == 0
        and uq145_contains_hits == 0
    )

    eum = seoul_probe.get("eum", {})
    mapplan = seoul_probe.get("mapplan_analysis", {})
    probe_resolution = seoul_probe.get("resolution", {})

    eum_http = eum.get("http_status")
    eum_name_present = bool(eum.get("target_name_present", False))
    mapplan_server = eum.get("mapplan_server")
    mapplan_http = mapplan.get("http_status")
    mapplan_entry_count = safe_int(mapplan.get("entry_count"))
    eum_query_success = (
        probe_resolution.get("query_status") == "QUERY_SUCCESS"
        and eum_http == 200
    )
    current_positive_evidence = eum_name_present
    eum_negative = eum_query_success and not eum_name_present

    unresolved_site = (
        overlay.get("input_requirements", {})
        .get("unresolved_site_conditions", [])
    )
    unresolved_entry = next(
        (
            item for item in unresolved_site
            if isinstance(item, dict)
            and item.get("name") == "개발밀도관리구역"
        ),
        None,
    )
    affected_clause_count = (
        safe_int(unresolved_entry.get("affected_clause_count"))
        if unresolved_entry else 0
    )

    evidence = {
        "announcement_database": {
            "query_status": announcement_query_status,
            "result_code": announcement_result_code,
            "total_rows": announcement_total,
            "received_rows": announcement_received,
            "exact_hits": exact_hit_count,
            "site_exact_hits": site_exact_hit_count,
            "broad_hits": broad_hit_count,
            "negative": announcement_negative,
            "dispositive": False,
        },
        "uq145_candidate_layer": {
            "query_success": uq145_query_success,
            "feature_count": uq145_feature_count,
            "exact_hits": uq145_exact_hits,
            "contains_hits": uq145_contains_hits,
            "negative": uq145_negative,
            "dispositive": False,
            "interpretation": (
                "UQ145는 확정 개발밀도관리구역 layer가 아니라 "
                "기타용도구역 후보 layer이므로 보조 evidence로만 사용"
            ),
        },
        "eum_site": {
            "query_success": eum_query_success,
            "http_status": eum_http,
            "target_name_present": eum_name_present,
            "mapplan_server_found": bool(mapplan_server),
            "mapplan_http": mapplan_http,
            "mapplan_entry_count": mapplan_entry_count,
            "direct_positive_evidence": current_positive_evidence,
            "negative": eum_negative,
            "dispositive": False,
        },
    }

    negative_evidence_count = sum(
        1 for value in (
            announcement_negative,
            uq145_negative,
            eum_negative,
        ) if value
    )

    # Production seam: legacy discovery evidence remains diagnostic only.
    # No generalized positive verification stage is wired yet, so the adapter
    # receives an intentionally empty positive-gate input and must stay fail-closed.
    adapter_result = adapt_uqq700_production_state(
        Uqq700ProductionAdapterInput(),
        search_hit=current_positive_evidence,
        http_200=(eum_http == 200),
        negative_evidence={
            "announcement_no_hit": announcement_negative,
            "candidate_layer_no_hit": uq145_negative,
            "site_non_display": eum_negative,
        },
    )

    resolution = str(adapter_result.get("resolution", "UNKNOWN"))
    confidence = "MEDIUM" if current_positive_evidence else "NONE"
    if current_positive_evidence:
        reason = (
            "토지이음 SITE 페이지에서 개발밀도관리구역 명칭 evidence가 "
            "확인되었으나 공식 지정 문서 identity/current validity/SITE spatial "
            "inclusion의 positive gate가 모두 검증되지 않아 UNKNOWN을 유지한다."
        )
    else:
        reason = (
            "공식 검색 및 후보 layer에서 no-hit가 관찰되었으나 negative evidence는 "
            "법적 부존재 또는 SITE FALSE를 증명하지 않는다. 공식 지정 문서 identity, "
            "current validity, SITE spatial inclusion이 모두 positive verification될 때까지 "
            "개발밀도관리구역은 UNKNOWN을 유지한다."
        )

    positive_gates = dict(adapter_result.get("positive_gates", {}))
    minimum_gate = bool(
        adapter_result.get("minimum_registration_gate_satisfied", False)
    )
    runtime_registration_allowed = bool(
        adapter_result.get("runtime_registration_allowed", False)
    )
    negative_evidence_allowed = bool(
        adapter_result.get("negative_evidence_allowed", False)
    )
    legal_absence_inference_allowed = bool(
        adapter_result.get("legal_absence_inference_allowed", False)
    )
    site_false_inference_allowed = bool(
        adapter_result.get("site_false_inference_allowed", False)
    )
    site_promotion_allowed = bool(
        adapter_result.get("site_promotion_allowed", False)
    )

    expected_overlay = {
        "condition": "개발밀도관리구역",
        "state": "UNKNOWN",
        "confidence": confidence,
        "affected_clause_count": affected_clause_count,
        "expected_effect": (
            "FALSE blocker 또는 NOT_APPLICABLE 승격 없이 UNKNOWN 상태 유지"
        ),
    }

    validations = {
        "announcement query success": announcement_success,
        "announcement total 43508": announcement_total == 43508,
        "announcement received all rows": announcement_received == announcement_total,
        "announcement exact hits 0": exact_hit_count == 0,
        "announcement site exact hits 0": site_exact_hit_count == 0,
        "announcement broad hits 0": broad_hit_count == 0,
        "UQ145 query success": uq145_query_success,
        "UQ145 feature 존재": uq145_feature_count > 0,
        "UQ145 exact hits 0": uq145_exact_hits == 0,
        "UQ145 contains hits 0": uq145_contains_hits == 0,
        "EUM SITE query success": eum_query_success,
        "EUM target name 없음": eum_name_present is False,
        "affected clauses 11": affected_clause_count == 11,
        "negative evidence 3종": negative_evidence_count == 3,
        "resolution UNKNOWN": resolution == "UNKNOWN",
        "identity gate unverified": positive_gates.get(
            "official_designation_identity_verified"
        ) is False,
        "validity gate unverified": positive_gates.get(
            "current_validity_verified"
        ) is False,
        "spatial gate unverified": positive_gates.get(
            "site_spatial_inclusion_verified"
        ) is False,
        "minimum gate unsatisfied": minimum_gate is False,
        "negative evidence non-dispositive": negative_evidence_allowed is False,
        "legal absence inference disabled": legal_absence_inference_allowed is False,
        "SITE FALSE inference disabled": site_false_inference_allowed is False,
        "SITE promotion disabled": site_promotion_allowed is False,
        "runtime registration disabled": runtime_registration_allowed is False,
        "production registry not mutated": adapter_result.get(
            "runtime_registry_mutated"
        ) is False,
    }
    all_pass = all(validations.values())

    output = {
        "step": STEP_NAME,
        "site": SITE,
        "condition": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "resolution_type": adapter_result.get(
            "resolution_type", "HYBRID_SPATIAL_NOTICE"
        ),
        "legal_character": {
            "designation_requires_public_notice": True,
            "current_effect": (
                "지정된 경우 해당 용도지역에 적용되는 용적률 최대한도를 강화할 수 있음"
            ),
        },
        "evidence": evidence,
        "negative_evidence_count": negative_evidence_count,
        "positive_gates": positive_gates,
        "minimum_registration_gate_satisfied": minimum_gate,
        "negative_evidence_allowed": negative_evidence_allowed,
        "legal_absence_inference_allowed": legal_absence_inference_allowed,
        "site_false_inference_allowed": site_false_inference_allowed,
        "site_promotion_allowed": site_promotion_allowed,
        "runtime_registration_allowed": runtime_registration_allowed,
        "production_adapter": {
            "wired": True,
            "positive_stage_inputs_wired": False,
            "runtime_registry_mutated": adapter_result.get(
                "runtime_registry_mutated", False
            ),
        },
        "previous_resolution": previous.get("resolution"),
        "current_resolution": {
            "status": resolution,
            "confidence": confidence,
            "reason": reason,
        },
        "affected_clause_count": affected_clause_count,
        "expected_overlay": expected_overlay,
        "validations": validations,
        "all_pass": all_pass,
    }

    save_json(output)

    print("Announcement DB:", "OK" if announcement_success else "FAIL")
    print("Rows:", announcement_total, "/ received:", announcement_received)
    print("Exact hits:", exact_hit_count)
    print("SITE exact hits:", site_exact_hit_count)
    print("Broad hits:", broad_hit_count)
    print()
    print("UQ145:", "OK" if uq145_query_success else "FAIL")
    print("Feature:", uq145_feature_count)
    print("Target hits:", uq145_exact_hits + uq145_contains_hits)
    print()
    print("EUM:", "OK" if eum_query_success else "FAIL")
    print("Name present:", eum_name_present)
    print()
    print("Negative evidence:", negative_evidence_count, "(diagnostic only)")
    print("Affected clauses:", affected_clause_count)
    print()
    print("개발밀도관리구역:", resolution, "/", confidence)
    print("Positive gates:", positive_gates)
    print("Minimum registration gate satisfied:", minimum_gate)
    print("Negative evidence allowed:", negative_evidence_allowed)
    print("Legal absence inference allowed:", legal_absence_inference_allowed)
    print("SITE FALSE inference allowed:", site_false_inference_allowed)
    print("SITE promotion allowed:", site_promotion_allowed)
    print("Runtime registration allowed:", runtime_registration_allowed)
    print()
    print("all_pass:", all_pass)
    print("OUTPUT:", OUTPUT_PATH)

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
