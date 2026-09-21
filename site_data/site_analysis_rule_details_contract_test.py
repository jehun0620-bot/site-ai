from __future__ import annotations

from law_data.site_analysis_builder import build_rule_details
from site_data.site_analysis_response import build_site_analysis_response


def main() -> None:
    rules = [
        {
            "clause_index": 1,
            "law_name": "법령 A",
            "rule_title": "적용 규정",
            "paragraph": "①",
            "item": "1",
            "subitem": "",
            "category": "건폐율",
            "applicability": "APPLICABLE",
            "applicability_reason": "모든 필수조건 충족",
            "text": "적용 규정 내용",
            "effect_targets": ["building_coverage_ratio"],
            "conditions": [{"name": "충족조건", "state": "TRUE"}],
            "numeric_effect": "80 percent",
        },
        {
            "clause_index": 2,
            "law_name": "법령 B",
            "rule_title": "조건부 규정",
            "applicability": "CONDITIONAL",
            "applicability_reason": "추가 입력 필요: 사업유형",
            "text": "조건부 규정 내용",
            "conditions": [{"name": "사업유형", "state": "UNSET"}],
        },
        {
            "clause_index": 3,
            "law_name": "법령 C",
            "rule_title": "확인 규정",
            "applicability": "UNKNOWN",
            "applicability_reason": "필수조건 미확정: 역사조건",
            "text": "확인 규정 내용",
            "conditions": [{"name": "역사조건", "state": "UNKNOWN"}],
        },
        {
            "clause_index": 4,
            "law_name": "법령 D",
            "rule_title": "미적용 규정",
            "applicability": "NOT_APPLICABLE",
            "applicability_reason": "필수조건 FALSE: 제외조건",
            "text": "미적용 규정 내용",
            "conditions": [{"name": "제외조건", "state": "FALSE"}],
        },
    ]

    details = build_rule_details({"rules": rules})
    assert details["count"] == 4
    assert [item["applicability"] for item in details["items"]] == [
        "APPLICABLE",
        "CONDITIONAL",
        "UNKNOWN",
        "NOT_APPLICABLE",
    ]
    assert details["items"][1]["required_inputs"] == ["사업유형"]
    assert details["items"][2]["unresolved_conditions"] == ["역사조건"]
    assert details["items"][3]["blocking_conditions"] == ["제외조건"]
    assert details["items"][0]["numeric_effect"] == "80 percent"

    internal_keys = {
        "baseline",
        "branch_overlay",
        "site_registry",
        "site_repairs",
        "dynamic_injection",
    }
    for item in details["items"]:
        assert internal_keys.isdisjoint(item)

    analysis = {
        "analysis": {"status": "READY", "engine": "RULE_EVALUATION_PIPELINE"},
        "site": {"site_id": "TEST", "pnu": "1168010300100120002"},
        "rule_evaluation": {
            "total": 4,
            "applicable": 1,
            "not_applicable": 1,
            "conditional": 1,
            "unknown": 1,
        },
        "rule_details": details,
        "input_requirements": {},
        "external_dependencies": {},
        "rule_engine": {
            "baseline": {"APPLICABLE": 1},
            "branch_overlay": {"internal": True},
        },
    }

    response = build_site_analysis_response(analysis, include_debug=False)
    assert response["schema_version"] == "SITE_ANALYSIS_API_V1"
    assert response["rule_details"]["count"] == response["rule_evaluation"]["total"]
    assert response["rule_details"]["items"][2]["reason"] == "필수조건 미확정: 역사조건"
    assert "debug" not in response
    assert internal_keys.isdisjoint(response["rule_details"])

    print("SITE_ANALYSIS_RULE_DETAILS_CONTRACT_PASS")


if __name__ == "__main__":
    main()
