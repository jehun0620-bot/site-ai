"""STEP68 historical orchestrator exposure authorization boundary audit."""
from __future__ import annotations

import copy
import inspect
from types import SimpleNamespace
from unittest.mock import patch

from api_app import SiteAnalysisRequest
from law_data.historical_site_event_builder_injection_payload import (
    CHANNEL,
    PROVENANCE,
)
from law_data.rule_evaluation_pipeline import evaluate_site_rules
from site_data.site_analysis_orchestrator import analyze_site_by_parcel


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise AssertionError(name)


def build_test_site():
    return SimpleNamespace(
        site_id="STEP68-TEST-SITE",
        address="STEP68 TEST",
        road_address="",
        sigungu_cd="11680",
        bjdong_cd="10300",
        bun="0012",
        ji="0000",
        land=None,
    )


def fake_building_result():
    return {
        "items": [{"step68": "mock-building-item"}],
        "total_count": 1,
        "result_code": "00",
        "result_message": "STEP68 MOCK",
    }


def call_orchestrator(*, historical_rule_input=None):
    site = build_test_site()

    with patch(
        "site_data.site_analysis_orchestrator.fetch_building_items",
        return_value=fake_building_result(),
    ) as fetch_mock, patch(
        "site_data.site_analysis_orchestrator.create_site",
        return_value=site,
    ) as create_mock:

        result = analyze_site_by_parcel(
            sigungu_cd="11680",
            bjdong_cd="10300",
            bun="0012",
            ji="0000",
            historical_rule_input=historical_rule_input,
            include_debug=True,
        )

    check(
        "External Building HUB call mocked",
        fetch_mock.call_count == 1,
    )

    check(
        "Site creation mocked",
        create_mock.call_count == 1,
    )

    return result


def find_historical_target(legacy_result):
    spatial_names = set(
        legacy_result
        .get("debug", {})
        .get("rule_engine", {})
        .get("site_registry", {})
    )

    if not spatial_names:
        raise AssertionError(
            "Legacy orchestrator spatial registry unavailable"
        )

    baseline = evaluate_site_rules()

    for rule in baseline.get("rules", []):
        if not isinstance(rule, dict):
            continue

        for condition in rule.get("conditions", []):
            if not isinstance(condition, dict):
                continue

            name = str(condition.get("name", "")).strip()

            if name and name not in spatial_names:
                return name

    raise AssertionError(
        "No non-spatial Rule Engine condition available for STEP68 test"
    )


def historical_input(condition_name):
    return {
        "channel": CHANNEL,
        "provenance": PROVENANCE,
        "repairs": [
            {
                "condition": condition_name,
                "after": "UNKNOWN",
                "new_confidence": "STEP68_TEST",
                "new_source": PROVENANCE,
            }
        ],
    }


def api_fields():
    fields = getattr(
        SiteAnalysisRequest,
        "model_fields",
        None,
    )

    if fields is None:
        fields = getattr(
            SiteAnalysisRequest,
            "__fields__",
            {},
        )

    return fields


def contains_provenance(value):
    if isinstance(value, dict):
        if (
            value.get("source") == PROVENANCE
            or value.get("provenance") == PROVENANCE
        ):
            return True

        return any(
            contains_provenance(item)
            for item in value.values()
        )

    if isinstance(value, list):
        return any(
            contains_provenance(item)
            for item in value
        )

    return False


def main():
    print("=" * 72)
    print("STEP 68 HISTORICAL ORCHESTRATOR EXPOSURE AUTHORIZATION")
    print("=" * 72)

    # --------------------------------------------------------
    # legacy orchestrator path
    # --------------------------------------------------------

    legacy = call_orchestrator()

    check(
        "Legacy orchestrator path preserved",
        not contains_provenance(legacy),
    )

    # --------------------------------------------------------
    # valid historical orchestrator handoff
    # --------------------------------------------------------

    target = find_historical_target(legacy)
    historical = historical_input(target)
    historical_before = copy.deepcopy(historical)

    integrated = call_orchestrator(
        historical_rule_input=historical,
    )

    check(
        "Caller historical input immutability",
        historical == historical_before,
    )

    repairs = [
        repair
        for repair in integrated
        .get("debug", {})
        .get("rule_engine", {})
        .get("site_repairs", [])
        if (
            isinstance(repair, dict)
            and repair.get("condition") == target
            and repair.get("new_source") == PROVENANCE
        )
    ]

    check(
        "Historical orchestrator-to-service consumption",
        bool(repairs),
    )

    check(
        "Historical provenance preserved",
        bool(repairs)
        and all(
            repair.get("new_confidence") == "STEP68_TEST"
            and repair.get("new_source") == PROVENANCE
            for repair in repairs
        ),
    )

    # --------------------------------------------------------
    # malformed input must fail closed
    # --------------------------------------------------------

    malformed = historical_input(target)
    malformed["repairs"][0]["new_source"] = "FORGED_SOURCE"

    malformed_blocked = False

    try:
        call_orchestrator(
            historical_rule_input=malformed,
        )
    except ValueError:
        malformed_blocked = True

    check(
        "Malformed historical input fail-closed",
        malformed_blocked,
    )

    # --------------------------------------------------------
    # exposure boundary
    # --------------------------------------------------------

    check(
        "Orchestrator historical seam exposed",
        "historical_rule_input"
        in inspect.signature(analyze_site_by_parcel).parameters,
    )

    check(
        "API historical field absent",
        "historical_rule_input" not in api_fields(),
    )

    print(
        "Public API historical input exposure / "
        "direct spatial runtime registration: NONE"
    )

    print(
        "CLASSIFICATION: "
        "STEP68_HISTORICAL_ORCHESTRATOR_API_EXPOSURE_"
        "AUTHORIZATION_BOUNDARY_RECONCILED"
    )


if __name__ == "__main__":
    main()
