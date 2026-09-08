# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-3B-4
개발밀도관리구역 UNKNOWN guard overlay

입력
======================================================================
site_rule_evaluation_condition_overlay.json
development_density_management_evidence_resolution.json

목표
======================================================================
1. 개발밀도관리구역(UQQ700)을 UNKNOWN으로 유지한다.
2. negative evidence로 FALSE blocker를 만들지 않는다.
3. 해당 condition을 unknown_by에 유지하고 applicability를 재평가한다.
4. UQQ700 때문에 NOT_APPLICABLE로 승격하지 않는다.
5. numeric current effect와 unresolved SITE 집계를 갱신한다.
6. BCR/FAR confirmed 50 / 250을 보존한다.
"""

from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-3B-4 "
    "개발밀도관리구역 UNKNOWN guard overlay"
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
INPUT_RULE_PATH = OUTPUT_DIR / "site_rule_evaluation_condition_overlay.json"
RESOLUTION_PATH = OUTPUT_DIR / "development_density_management_evidence_resolution.json"
OUTPUT_PATH = OUTPUT_DIR / "site_rule_evaluation_density_overlay.json"


def safe_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"입력 파일 없음: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def refresh_condition_groups(rule: Dict[str, Any]) -> None:
    conditions = rule.get("conditions", [])
    rule["required_inputs"] = [
        item for item in conditions
        if isinstance(item, dict) and item.get("state") == "UNSET"
    ]
    rule["blocked_by"] = [
        item for item in conditions
        if isinstance(item, dict) and item.get("state") == "FALSE"
    ]
    rule["unknown_by"] = [
        item for item in conditions
        if isinstance(item, dict) and item.get("state") == "UNKNOWN"
    ]


def recalculate_applicability(rule: Dict[str, Any]) -> Dict[str, str]:
    blocked = rule.get("blocked_by", [])
    unknown = rule.get("unknown_by", [])
    required = rule.get("required_inputs", [])

    if blocked:
        return {
            "applicability": "NOT_APPLICABLE",
            "reason": "필수조건 FALSE: " + ", ".join(
                safe_string(item.get("name")) for item in blocked
            ),
        }

    if unknown:
        return {
            "applicability": "UNKNOWN",
            "reason": "필수조건 미확정: " + ", ".join(
                safe_string(item.get("name")) for item in unknown
            ),
        }

    if required:
        return {
            "applicability": "CONDITIONAL",
            "reason": "추가 입력 필요: " + ", ".join(
                safe_string(item.get("name")) for item in required
            ),
        }

    if rule.get("zone_relevance") == "OTHER_ZONE":
        return {
            "applicability": "NOT_APPLICABLE",
            "reason": "현재 SITE 용도지역 불일치",
        }

    return {
        "applicability": "APPLICABLE",
        "reason": "모든 필수조건 충족",
    }


def refresh_numeric_effect(rule: Dict[str, Any]) -> None:
    numeric_effect = rule.get("numeric_effect")
    if not numeric_effect:
        return

    applicability = rule.get("applicability")
    if applicability == "NOT_APPLICABLE":
        status = "INACTIVE"
    elif applicability == "CONDITIONAL":
        status = "POTENTIAL_CONDITIONAL"
    elif applicability == "UNKNOWN":
        status = "POTENTIAL_UNKNOWN"
    else:
        status = "ACTIVE_CANDIDATE"

    rule["current_numeric_effect"] = {
        "status": status,
        "effect_class": rule.get("numeric_effect_class"),
        "semantic": numeric_effect,
    }


def build_unresolved_site_conditions(
    rules: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    counter = Counter()
    for rule in rules:
        for condition in rule.get("unknown_by", []):
            if not isinstance(condition, dict):
                continue
            if safe_string(condition.get("type")) not in {"SITE", "SITE_HISTORY"}:
                continue
            name = safe_string(condition.get("name"))
            if name:
                counter[name] += 1

    return [
        {
            "name": name,
            "affected_clause_count": count,
            "site_state": "UNKNOWN",
        }
        for name, count in counter.most_common()
    ]


def build_required_inputs(
    rules: List[Dict[str, Any]],
    condition_type: str,
) -> List[Dict[str, Any]]:
    counter = Counter()
    for rule in rules:
        for condition in rule.get("required_inputs", []):
            if not isinstance(condition, dict):
                continue
            if safe_string(condition.get("type")) != condition_type:
                continue
            name = safe_string(condition.get("name"))
            if name:
                counter[name] += 1

    return [
        {
            "name": name,
            "affected_clause_count": count,
            "profile_state": "UNSET",
        }
        for name, count in counter.most_common()
    ]


def main() -> int:
    snapshot = load_json(INPUT_RULE_PATH)
    resolution = load_json(RESOLUTION_PATH)

    current_resolution = resolution.get("current_resolution", {})
    status = safe_string(current_resolution.get("status"))
    confidence = safe_string(current_resolution.get("confidence"))
    reason = safe_string(current_resolution.get("reason"))

    if status != "UNKNOWN":
        raise ValueError(
            "개발밀도관리구역 resolution은 UNKNOWN이어야 함: "
            f"actual={status or '<empty>'}"
        )

    if any(
        bool(resolution.get(key, False))
        for key in (
            "negative_evidence_allowed",
            "legal_absence_inference_allowed",
            "site_false_inference_allowed",
            "site_promotion_allowed",
            "runtime_registration_allowed",
        )
    ):
        raise ValueError("UQQ700 금지 guard 값이 활성화되어 있음")

    rules = copy.deepcopy(snapshot.get("rules", []))
    changed_rules = []
    touched_rules = 0
    uqq700_false_count = 0

    for rule in rules:
        if not isinstance(rule, dict):
            continue

        previous_applicability = rule.get("applicability")
        matched = False

        for condition in rule.get("conditions", []):
            if not isinstance(condition, dict):
                continue
            if safe_string(condition.get("name")) != "개발밀도관리구역":
                continue

            previous_state = condition.get("state")
            condition["state"] = "UNKNOWN"
            condition["confidence"] = confidence or "NONE"
            condition["source"] = "DEVELOPMENT_DENSITY_MANAGEMENT_EVIDENCE_RESOLUTION"
            condition["resolution_reason"] = reason
            condition["previous_state"] = previous_state
            matched = True

        if not matched:
            continue

        touched_rules += 1
        refresh_condition_groups(rule)
        recalculated = recalculate_applicability(rule)
        rule["applicability"] = recalculated["applicability"]
        rule["applicability_reason"] = recalculated["reason"]
        refresh_numeric_effect(rule)

        for item in rule.get("blocked_by", []):
            if (
                isinstance(item, dict)
                and safe_string(item.get("name")) == "개발밀도관리구역"
            ):
                uqq700_false_count += 1

        if previous_applicability != rule.get("applicability"):
            changed_rules.append(
                {
                    "clause_index": rule.get("clause_index"),
                    "rule_title": rule.get("rule_title"),
                    "previous_applicability": previous_applicability,
                    "new_applicability": rule.get("applicability"),
                }
            )

    applicability_counter = Counter(
        rule.get("applicability")
        for rule in rules
        if isinstance(rule, dict)
    )
    unresolved_site = build_unresolved_site_conditions(rules)
    project_inputs = build_required_inputs(rules, "PROJECT")
    procedure_inputs = build_required_inputs(rules, "PROCEDURE")

    rules_requiring_input = sum(
        1 for rule in rules if isinstance(rule, dict) and rule.get("required_inputs")
    )
    rules_with_unknown = sum(
        1 for rule in rules if isinstance(rule, dict) and rule.get("unknown_by")
    )
    rules_with_blocker = sum(
        1 for rule in rules if isinstance(rule, dict) and rule.get("blocked_by")
    )

    confirmed_regulation = snapshot.get("confirmed_regulation", {})
    confirmed_bcr = (
        confirmed_regulation.get("building_coverage_ratio", {}).get("value")
    )
    confirmed_far = (
        confirmed_regulation.get("floor_area_ratio", {}).get("value")
    )

    rule_groups = {
        "applicable_clause_indexes": [
            rule["clause_index"] for rule in rules
            if rule.get("applicability") == "APPLICABLE"
        ],
        "conditional_clause_indexes": [
            rule["clause_index"] for rule in rules
            if rule.get("applicability") == "CONDITIONAL"
        ],
        "unknown_clause_indexes": [
            rule["clause_index"] for rule in rules
            if rule.get("applicability") == "UNKNOWN"
        ],
        "not_applicable_clause_indexes": [
            rule["clause_index"] for rule in rules
            if rule.get("applicability") == "NOT_APPLICABLE"
        ],
    }

    transitions = Counter(
        (item["previous_applicability"], item["new_applicability"])
        for item in changed_rules
    )
    remaining = {
        item["name"]: item["affected_clause_count"]
        for item in unresolved_site
    }

    validations = {
        "rules 314": len(rules) == 314,
        "개발밀도관리구역 touched 11": touched_rules == 11,
        "개발밀도관리구역 UNKNOWN 유지": remaining.get("개발밀도관리구역") == 11,
        "개발밀도관리구역 FALSE blocker 없음": uqq700_false_count == 0,
        "학교이적지 유지": "학교이적지" in remaining,
        "도시지역편입해제구역 유지": "도시지역편입해제구역" in remaining,
        "unresolved SITE 3종": len(unresolved_site) == 3,
        "confirmed BCR 50": confirmed_bcr == 50.0,
        "confirmed FAR 250": confirmed_far == 250.0,
        "resolution UNKNOWN": status == "UNKNOWN",
        "negative evidence disabled": resolution.get("negative_evidence_allowed") is False,
        "legal absence inference disabled": resolution.get("legal_absence_inference_allowed") is False,
        "SITE FALSE inference disabled": resolution.get("site_false_inference_allowed") is False,
        "SITE promotion disabled": resolution.get("site_promotion_allowed") is False,
        "runtime registration disabled": resolution.get("runtime_registration_allowed") is False,
    }
    all_pass = all(validations.values())

    output = {
        "step": STEP_NAME,
        "site": snapshot.get("site", {}),
        "confirmed_regulation": confirmed_regulation,
        "overlay": {
            "condition": "개발밀도관리구역",
            "standard_code": "UQQ700",
            "state": "UNKNOWN",
            "confidence": confidence or "NONE",
            "touched_rules": touched_rules,
            "changed_rules": changed_rules,
            "transitions": {
                f"{before} -> {after}": count
                for (before, after), count in transitions.items()
            },
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "site_promotion_allowed": False,
            "runtime_registration_allowed": False,
        },
        "rule_evaluation_summary": {
            "confirmed_building_coverage_ratio": confirmed_bcr,
            "confirmed_floor_area_ratio": confirmed_far,
            "total_clauses": len(rules),
            "applicable": applicability_counter["APPLICABLE"],
            "not_applicable": applicability_counter["NOT_APPLICABLE"],
            "conditional": applicability_counter["CONDITIONAL"],
            "unknown": applicability_counter["UNKNOWN"],
            "rules_requiring_input": rules_requiring_input,
            "rules_with_unknown_condition": rules_with_unknown,
            "rules_with_false_blocker": rules_with_blocker,
        },
        "input_requirements": {
            "project": project_inputs,
            "procedure": procedure_inputs,
            "unresolved_site_conditions": unresolved_site,
        },
        "rule_groups": rule_groups,
        "rules": rules,
        "validations": validations,
        "all_pass": all_pass,
    }

    save_json(output)

    print("Overlay: 개발밀도관리구역 -> UNKNOWN")
    print("Touched rules:", touched_rules)
    print("Changed rules:", len(changed_rules))
    print(
        "Transitions:",
        {
            f"{before} -> {after}": count
            for (before, after), count in transitions.items()
        },
    )
    print()
    print("APPLICABLE:", applicability_counter["APPLICABLE"])
    print("NOT_APPLICABLE:", applicability_counter["NOT_APPLICABLE"])
    print("CONDITIONAL:", applicability_counter["CONDITIONAL"])
    print("UNKNOWN:", applicability_counter["UNKNOWN"])
    print()
    print(
        "Unresolved SITE:",
        [(item["name"], item["affected_clause_count"]) for item in unresolved_site],
    )
    print("UQQ700 FALSE blockers:", uqq700_false_count)
    print()
    print("Confirmed BCR:", confirmed_bcr)
    print("Confirmed FAR:", confirmed_far)
    print()
    print("all_pass:", all_pass)
    print("OUTPUT:", OUTPUT_PATH)

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
