from __future__ import annotations

from collections import Counter

from law_data.site_analysis_builder import build_site_analysis
from site_data.site_analysis_response import build_site_analysis_response


def main() -> None:
    analysis = build_site_analysis(
        project_profile={"공동주택": "TRUE"},
        procedure_profile={"도시계획위원회심의": "TRUE"},
    )

    summary = analysis["rule_evaluation"]
    details = analysis["rule_details"]
    items = details["items"]

    assert summary["total"] == 314, summary
    assert details["count"] == summary["total"], (details["count"], summary)
    assert len(items) == details["count"]

    detail_counts = Counter(item["applicability"] for item in items)
    assert detail_counts["APPLICABLE"] == summary["applicable"], detail_counts
    assert detail_counts["NOT_APPLICABLE"] == summary["not_applicable"], detail_counts
    assert detail_counts["CONDITIONAL"] == summary["conditional"], detail_counts
    assert detail_counts["UNKNOWN"] == summary["unknown"], detail_counts

    unknown_items = [item for item in items if item["applicability"] == "UNKNOWN"]
    assert len(unknown_items) == summary["unknown"]
    assert all(item["law_name"] for item in unknown_items)
    assert all(item["rule_title"] for item in unknown_items)
    assert all(item["reason"] for item in unknown_items)
    assert all(item["unresolved_conditions"] for item in unknown_items)

    conditional_items = [
        item for item in items if item["applicability"] == "CONDITIONAL"
    ]
    assert len(conditional_items) == summary["conditional"]
    assert any(item["required_inputs"] for item in conditional_items)

    response = build_site_analysis_response(analysis, include_debug=False)
    assert response["schema_version"] == "SITE_ANALYSIS_API_V1"
    assert response["rule_details"]["count"] == response["rule_evaluation"]["total"]
    assert "debug" not in response

    public_internal_keys = {
        "baseline",
        "branch_overlay",
        "site_registry",
        "site_repairs",
        "dynamic_injection",
    }
    assert public_internal_keys.isdisjoint(response["rule_details"])
    for item in response["rule_details"]["items"]:
        assert public_internal_keys.isdisjoint(item)

    print("SITE_ANALYSIS_RULE_DETAILS_REAL_DATA_REGRESSION_PASS")
    print("rule_details.count:", details["count"])
    print("APPLICABLE:", detail_counts["APPLICABLE"])
    print("NOT_APPLICABLE:", detail_counts["NOT_APPLICABLE"])
    print("CONDITIONAL:", detail_counts["CONDITIONAL"])
    print("UNKNOWN:", detail_counts["UNKNOWN"])
    for item in unknown_items:
        print(
            "UNKNOWN:",
            item["clause_index"],
            "/",
            item["law_name"],
            "/",
            item["rule_title"],
            "/",
            item["reason"],
            "/",
            ",".join(item["unresolved_conditions"]),
        )


if __name__ == "__main__":
    main()
