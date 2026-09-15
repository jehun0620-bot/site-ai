"""STEP67 historical production service/runtime exposure boundary audit."""
from __future__ import annotations

import copy
import inspect
from types import SimpleNamespace

from api_app import SiteAnalysisRequest
from law_data.historical_site_event_builder_injection_payload import (
    CHANNEL,
    PROVENANCE,
)
from law_data.rule_evaluation_pipeline import evaluate_site_rules
from site_data.site_analysis_orchestrator import analyze_site_by_parcel
from site_data.site_analysis_service import analyze_site_object


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise AssertionError(name)


def build_test_site():
    """Create the minimum Site-like object accepted by the service adapter."""
    return SimpleNamespace(
        site_id="STEP67-TEST-SITE",
        address="STEP67 TEST",
        road_address="",
        sigungu_cd="11680",
        bjdong_cd="10300",
        bun="0012",
        ji="0000",
        land=None,
    )


def find_historical_target(service_result):
    spatial_names = set(
        service_result.get("rule_engine", {}).get("site_registry", {})
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
        "No non-spatial Rule Engine condition available for STEP67 test"
    )


def historical_input(condition_name):
    return {
        "channel": CHANNEL,
        "provenance": PROVENANCE,
        "repairs": [
            {
                "condition": condition_name,
                "after": "UNKNOWN",
                "new_confidence": "STEP67_TEST",
                "new_source": PROVENANCE,
            }
        ],
    }


def api_fields():
    fields = getattr(SiteAnalysisRequest, "model_fields", None)
    if fields is None:
        fields = getattr(SiteAnalysisRequest, "__fields__", {})
    return fields


def main():
    print("=" * 72)
    print("STEP 67 HISTORICAL PRODUCTION RUNTIME EXPOSURE")
    print("=" * 72)

    site = build_test_site()

    # --------------------------------------------------------
    # legacy service path
    # --------------------------------------------------------

    legacy = analyze_site_object(site)

    check(
        "Legacy service path preserved",
        "historical" not in legacy.get("input", {}),
    )

    # --------------------------------------------------------
    # valid service -> builder -> Rule Engine handoff
    # --------------------------------------------------------

    target = find_historical_target(legacy)
    historical = historical_input(target)
    historical_before = copy.deepcopy(historical)

    integrated = analyze_site_object(
        site,
        historical_rule_input=historical,
    )

    repairs = [
        repair
        for repair in integrated
        .get("rule_engine", {})
        .get("site_repairs", [])
        if repair.get("condition") == target
    ]

    check(
        "Historical service-to-Rule-Engine consumption",
        bool(repairs)
        and all(
            repair.get("new_confidence") == "STEP67_TEST"
            and repair.get("new_source") == PROVENANCE
            for repair in repairs
        ),
    )

    check(
        "Historical provenance preserved",
        bool(repairs)
        and all(
            repair.get("new_source") == PROVENANCE
            for repair in repairs
        ),
    )

    check(
        "Dedicated historical input preserved",
        integrated.get("input", {}).get("historical")
        == historical_before,
    )

    check(
        "Caller historical input immutability",
        historical == historical_before,
    )

    # --------------------------------------------------------
    # malformed input must fail closed
    # --------------------------------------------------------

    malformed = historical_input(target)
    malformed["repairs"][0]["new_source"] = "FORGED_SOURCE"

    malformed_blocked = False

    try:
        analyze_site_object(
            site,
            historical_rule_input=malformed,
        )
    except ValueError:
        malformed_blocked = True

    check(
        "Malformed historical input fail-closed",
        malformed_blocked,
    )

    # --------------------------------------------------------
    # historical provenance must not enter spatial runtime
    # --------------------------------------------------------

    runtime_conditions = (
        integrated.get("site", {}).get("runtime_conditions", {})
    )

    historical_provenance_in_spatial_runtime = any(
        isinstance(value, dict)
        and (
            value.get("source") == PROVENANCE
            or value.get("provenance") == PROVENANCE
        )
        for value in runtime_conditions.values()
    )

    check(
        "Historical provenance absent from spatial runtime channel",
        not historical_provenance_in_spatial_runtime,
    )

    # --------------------------------------------------------
    # exposure boundary: service yes, orchestrator/API no
    # --------------------------------------------------------

    check(
        "Service historical seam exposed",
        "historical_rule_input"
        in inspect.signature(analyze_site_object).parameters,
    )

    check(
        "Orchestrator historical seam absent",
        "historical_rule_input"
        not in inspect.signature(analyze_site_by_parcel).parameters,
    )

    check(
        "API historical field absent",
        "historical_rule_input" not in api_fields(),
    )

    print(
        "Historical API exposure / orchestrator wiring / "
        "spatial runtime registration: NONE"
    )
    print(
        "CLASSIFICATION: "
        "STEP67_HISTORICAL_PRODUCTION_RUNTIME_EXPOSURE_"
        "BOUNDARY_RECONCILED"
    )


if __name__ == "__main__":
    main()
