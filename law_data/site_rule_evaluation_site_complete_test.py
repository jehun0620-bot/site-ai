# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-3B-8
SITE Rule Evaluation guarded snapshot

현재 상태
======================================================================
서울도심: FALSE / HIGH
개발밀도관리구역(UQQ700): UNKNOWN / promotion blocked
학교이적지: FALSE / HIGH
도시지역편입해제구역: UNKNOWN / HISTORICAL_SOURCE_PENDING

UQQ700은 official designation identity, current validity, SITE spatial inclusion의
positive gate가 모두 검증되기 전까지 UNKNOWN을 유지한다. 따라서 이 snapshot은
UQQ700을 해결 완료로 간주하거나 SITE stage/runtime registration을 완료 처리하지 않는다.
"""

from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict

STEP_NAME = "STEP 17-21-C-10-3B-8 SITE Rule Evaluation guarded snapshot"
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
RULE_PATH = OUTPUT_DIR / "site_rule_evaluation_school_overlay.json"
HISTORY_PATH = OUTPUT_DIR / "urban_area_conversion_history_final_resolution.json"
OUTPUT_PATH = OUTPUT_DIR / "site_rule_evaluation_site_complete.json"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"입력 파일 없음: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def main() -> int:
    snapshot = load_json(RULE_PATH)
    history = load_json(HISTORY_PATH)
    rules = copy.deepcopy(snapshot.get("rules", []))

    history_resolution = history.get("current_resolution", {})
    history_status = history_resolution.get("status")
    history_confidence = history_resolution.get("confidence")
    automation_state = history_resolution.get("automation_state")
    history_reason = history_resolution.get("reason")
    overlay_action = history.get("overlay_policy", {}).get("action")
    affected_clause_count = int(history.get("affected_clause_count", 0) or 0)

    if history_status != "UNKNOWN" or automation_state != "HISTORICAL_SOURCE_PENDING" or overlay_action != "KEEP_UNKNOWN":
        raise ValueError("도시지역편입해제구역 historical pending 상태가 아님")

    touched_rules = []
    unknown_dependency_rules = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        matched = False
        for condition in rule.get("conditions", []):
            if not isinstance(condition, dict) or condition.get("name") != "도시지역편입해제구역":
                continue
            matched = True
            condition["state"] = "UNKNOWN"
            condition["confidence"] = history_confidence
            condition["source"] = "URBAN_AREA_CONVERSION_HISTORY_FINAL_RESOLUTION"
            condition["external_dependency"] = "HISTORICAL_SOURCE_PENDING"
            condition["resolution_reason"] = history_reason
        if not matched:
            continue
        dependency = {
            "type": "HISTORICAL_SOURCE",
            "condition": "도시지역편입해제구역",
            "status": "PENDING",
            "automation_state": "HISTORICAL_SOURCE_PENDING",
            "required_source": "1988~1989 대치택지개발 관련 미구축 고시 또는 국가기록원 원기록",
            "blocking_system_completion": False,
            "blocking_rule_resolution": rule.get("applicability") == "UNKNOWN",
        }
        rule["external_dependencies"] = [dependency]
        touched_rules.append(rule.get("clause_index"))
        if rule.get("applicability") == "UNKNOWN":
            unknown_dependency_rules.append({
                "clause_index": rule.get("clause_index"),
                "law_name": rule.get("law_name"),
                "rule_title": rule.get("rule_title"),
                "reason": rule.get("applicability_reason"),
            })

    applicability_counter = Counter(rule.get("applicability") for rule in rules if isinstance(rule, dict))
    ordinary_unresolved = []
    external_unresolved = []
    source_unresolved = snapshot.get("input_requirements", {}).get("unresolved_site_conditions", [])
    for item in source_unresolved:
        if item.get("name") == "도시지역편입해제구역":
            external_unresolved.append({
                "name": "도시지역편입해제구역", "type": "SITE_HISTORY", "state": "UNKNOWN",
                "confidence": history_confidence, "affected_clause_count": item.get("affected_clause_count"),
                "automation_state": automation_state, "blocking_site_stage": False,
                "resolution_path": "국가기록원 원문 또는 미구축 historic notice 확보",
            })
        else:
            ordinary_unresolved.append(item)

    confirmed_regulation = snapshot.get("confirmed_regulation", {})
    confirmed_bcr = confirmed_regulation.get("building_coverage_ratio", {}).get("value")
    confirmed_far = confirmed_regulation.get("floor_area_ratio", {}).get("value")

    uqq700_conditions = []
    uqq700_false_blockers = 0
    for rule in rules:
        for condition in rule.get("conditions", []):
            if isinstance(condition, dict) and condition.get("name") == "개발밀도관리구역":
                uqq700_conditions.append(condition)
        for condition in rule.get("blocked_by", []):
            if isinstance(condition, dict) and condition.get("name") == "개발밀도관리구역":
                uqq700_false_blockers += 1
    uqq700_unknown_count = sum(1 for condition in uqq700_conditions if condition.get("state") == "UNKNOWN")
    ordinary_names = {item.get("name") for item in ordinary_unresolved}

    site_stage_status = "INCOMPLETE_GUARDED_UQQ700_UNKNOWN"
    site_rule_engine_ready = False

    validations = {
        "rules 314": len(rules) == 314,
        "affected history rules 3": len(touched_rules) == affected_clause_count == 3,
        "UQQ700 ordinary unresolved": "개발밀도관리구역" in ordinary_names,
        "ordinary unresolved 1": len(ordinary_unresolved) == 1,
        "external unresolved 1": len(external_unresolved) == 1,
        "external dependency historical pending": bool(external_unresolved) and external_unresolved[0]["automation_state"] == "HISTORICAL_SOURCE_PENDING",
        "UQQ700 conditions 11": len(uqq700_conditions) == 11,
        "UQQ700 UNKNOWN 11": uqq700_unknown_count == 11,
        "UQQ700 FALSE blockers 0": uqq700_false_blockers == 0,
        "confirmed BCR 50": confirmed_bcr == 50.0,
        "confirmed FAR 250": confirmed_far == 250.0,
        "SITE stage guarded incomplete": site_stage_status == "INCOMPLETE_GUARDED_UQQ700_UNKNOWN",
        "SITE rule engine not ready": site_rule_engine_ready is False,
        "SITE promotion disabled": True,
        "runtime registration disabled": True,
    }
    all_pass = all(validations.values())

    output = {
        "step": STEP_NAME,
        "site": snapshot.get("site", {}),
        "site_stage": {"status": site_stage_status, "rule_engine_ready": site_rule_engine_ready,
            "policy": "UQQ700은 positive registration gate 3종 검증 전까지 UNKNOWN을 유지하며 SITE promotion 및 runtime registration을 차단한다."},
        "uqq700_guard": {"condition": "개발밀도관리구역", "standard_code": "UQQ700", "resolution": "UNKNOWN",
            "condition_count": len(uqq700_conditions), "unknown_count": uqq700_unknown_count, "false_blocker_count": uqq700_false_blockers,
            "negative_evidence_allowed": False, "legal_absence_inference_allowed": False, "site_false_inference_allowed": False,
            "site_promotion_allowed": False, "runtime_registration_allowed": False},
        "confirmed_regulation": confirmed_regulation,
        "rule_evaluation_summary": {"total_clauses": len(rules), "applicable": applicability_counter["APPLICABLE"],
            "not_applicable": applicability_counter["NOT_APPLICABLE"], "conditional": applicability_counter["CONDITIONAL"],
            "unknown": applicability_counter["UNKNOWN"], "confirmed_building_coverage_ratio": confirmed_bcr, "confirmed_floor_area_ratio": confirmed_far},
        "site_dependencies": {"ordinary_unresolved": ordinary_unresolved, "external_historical_dependencies": external_unresolved},
        "historical_dependency": {"condition": "도시지역편입해제구역", "status": history_status, "confidence": history_confidence,
            "automation_state": automation_state, "affected_clause_count": affected_clause_count, "unknown_rule_count": len(unknown_dependency_rules),
            "unknown_rules": unknown_dependency_rules, "blocking_site_stage": False},
        "input_requirements": {"project": snapshot.get("input_requirements", {}).get("project", []),
            "procedure": snapshot.get("input_requirements", {}).get("procedure", []), "unresolved_site_conditions": source_unresolved},
        "rule_groups": snapshot.get("rule_groups", {}), "rules": rules, "validations": validations, "all_pass": all_pass,
    }
    save_json(output)

    print("SITE stage:", site_stage_status)
    print("SITE rule engine ready:", site_rule_engine_ready)
    print("UQQ700 resolution: UNKNOWN")
    print("UQQ700 UNKNOWN conditions:", uqq700_unknown_count)
    print("UQQ700 FALSE blockers:", uqq700_false_blockers)
    print("Ordinary unresolved:", [(item.get("name"), item.get("affected_clause_count")) for item in ordinary_unresolved])
    print("External unresolved:", [(item.get("name"), item.get("affected_clause_count")) for item in external_unresolved])
    print("Negative evidence allowed: False")
    print("Legal absence inference allowed: False")
    print("SITE promotion allowed: False")
    print("Runtime registration allowed: False")
    print("Confirmed BCR:", confirmed_bcr)
    print("Confirmed FAR:", confirmed_far)
    print("all_pass:", all_pass)
    print("OUTPUT:", OUTPUT_PATH)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
