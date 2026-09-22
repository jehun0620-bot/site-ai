# -*- coding: utf-8 -*-

"""Contract regression for production zone relevance transitions.

This test intentionally imports the current production implementation from
rule_evaluation_pipeline.  It freezes the transition semantics before any
future module extraction/refactor.
"""

from __future__ import annotations

import copy

from law_data.rule_evaluation_pipeline import (
    apply_zone_relevance_transition,
)


def _rule(
    *,
    law_name: str = "국토의 계획 및 이용에 관한 법률",
    rule_title: str = "용도지역의 건폐율",
    applicability: str = "APPLICABLE",
    reason: str = "모든 필수조건 충족",
    conditions=None,
    numeric: bool = True,
):
    rule = {
        "law_name": law_name,
        "rule_title": rule_title,
        "applicability": applicability,
        "applicability_reason": reason,
        "conditions": copy.deepcopy(conditions or []),
    }
    if numeric:
        rule["numeric_effect"] = {"kind": "LIMIT"}
        rule["numeric_effect_class"] = "BASE_LIMIT"
    return rule


def main() -> int:
    validations = {}

    # 1. A currently relevant rule becomes irrelevant to the new SITE.
    source = _rule()
    original = copy.deepcopy(source)
    result = apply_zone_relevance_transition(
        source,
        old_zone_relevance="DIRECT",
        new_zone_relevance="OTHER_ZONE",
    )
    validations["deactivation applicability"] = (
        result.get("applicability") == "NOT_APPLICABLE"
    )
    validations["deactivation transition"] = (
        result.get("zone_transition", {}).get("status")
        == "DEACTIVATED_BY_ZONE"
    )
    validations["deactivation numeric inactive"] = (
        result.get("current_numeric_effect", {}).get("status") == "INACTIVE"
    )
    validations["deactivation input immutable"] = source == original

    # 2. A verified safe base-zone reference may be reactivated.
    source = _rule(
        applicability="NOT_APPLICABLE",
        reason="현재 SITE 용도지역 불일치",
    )
    original = copy.deepcopy(source)
    result = apply_zone_relevance_transition(
        source,
        old_zone_relevance="OTHER_ZONE",
        new_zone_relevance="DIRECT",
    )
    validations["safe reactivation applicable"] = (
        result.get("applicability") == "APPLICABLE"
    )
    validations["safe reactivation transition"] = (
        result.get("zone_transition", {}).get("status")
        == "REACTIVATED_SAFE_ZONE_REFERENCE"
    )
    validations["safe reactivation numeric active"] = (
        result.get("current_numeric_effect", {}).get("status")
        == "ACTIVE_CANDIDATE"
    )
    validations["safe reactivation input immutable"] = source == original

    # 3. A non-whitelisted rule stays fail-closed even when its zone matches.
    source = _rule(
        law_name="테스트법",
        rule_title="추가요건이 있는 특례",
        applicability="NOT_APPLICABLE",
        reason="현재 SITE 용도지역 불일치",
    )
    original = copy.deepcopy(source)
    result = apply_zone_relevance_transition(
        source,
        old_zone_relevance="OTHER_ZONE",
        new_zone_relevance="GROUP",
    )
    validations["unsafe reactivation preserved"] = (
        result.get("applicability") == "NOT_APPLICABLE"
    )
    validations["unsafe reactivation deferred"] = (
        result.get("zone_transition", {}).get("status")
        == "REACTIVATION_DEFERRED"
    )
    validations["unsafe reactivation input immutable"] = source == original

    # 4. Matching a new zone must not erase a pre-existing non-zone exclusion.
    source = _rule(
        applicability="NOT_APPLICABLE",
        reason="필수조건 FALSE: 별도사업요건",
    )
    original = copy.deepcopy(source)
    result = apply_zone_relevance_transition(
        source,
        old_zone_relevance="OTHER_ZONE",
        new_zone_relevance="DIRECT",
    )
    validations["original exclusion preserved"] = (
        result.get("applicability") == "NOT_APPLICABLE"
    )
    validations["original exclusion transition"] = (
        result.get("zone_transition", {}).get("status")
        == "MATCHED_BUT_ORIGINAL_EXCLUSION_PRESERVED"
    )
    validations["original exclusion input immutable"] = source == original

    # 5. No meaningful zone transition must leave applicability untouched.
    source = _rule(applicability="CONDITIONAL", reason="추가 입력 필요: 사업요건")
    original = copy.deepcopy(source)
    result = apply_zone_relevance_transition(
        source,
        old_zone_relevance="DIRECT",
        new_zone_relevance="DIRECT",
    )
    validations["no transition applicability"] = (
        result.get("applicability") == "CONDITIONAL"
    )
    validations["no transition status"] = (
        result.get("zone_transition", {}).get("status")
        == "NO_APPLICABILITY_TRANSITION"
    )
    validations["no transition input immutable"] = source == original

    all_pass = all(validations.values())

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    print("all_pass:", all_pass)
    print(
        "CLASSIFICATION:",
        "ZONE_RELEVANCE_TRANSITION_CONTRACT_PASS"
        if all_pass
        else "ZONE_RELEVANCE_TRANSITION_CONTRACT_FAIL",
    )

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
