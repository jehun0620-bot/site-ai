"""STEP66 builder-to-Rule-Engine historical production handoff audit."""
from __future__ import annotations

import copy

from law_data.historical_site_event_builder_injection_payload import (
    CHANNEL,
    PROVENANCE,
)
from law_data.rule_evaluation_pipeline import evaluate_site_rules
from law_data.site_analysis_builder import build_site_analysis


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise AssertionError(name)


def find_historical_target(builder_result):
    """Find a real Rule Engine condition not occupied by builder spatial registry."""
    spatial_names = set(
        builder_result.get("rule_engine", {}).get("site_registry", {})
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
        "No non-spatial Rule Engine condition available for STEP66 test"
    )


def historical_input(condition_name):
    return {
        "channel": CHANNEL,
        "provenance": PROVENANCE,
        "repairs": [
            {
                "condition": condition_name,
                "after": "UNKNOWN",
                "new_confidence": "STEP66_TEST",
                "new_source": PROVENANCE,
            }
        ],
    }


def main():
    print("=" * 72)
    print("STEP 66 HISTORICAL RULE ENGINE PRODUCTION HANDOFF")
    print("=" * 72)

    # --------------------------------------------------------
    # legacy path
    # --------------------------------------------------------

    legacy = build_site_analysis()

    check(
        "Legacy builder path preserved",
        "historical" not in legacy.get("input", {}),
    )

    # --------------------------------------------------------
    # valid historical handoff
    # --------------------------------------------------------

    target = find_historical_target(legacy)
    historical = historical_input(target)
    historical_before = copy.deepcopy(historical)

    integrated = build_site_analysis(
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
        "Historical builder-to-Rule-Engine consumption",
        bool(repairs)
        and all(
            repair.get("new_confidence") == "STEP66_TEST"
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
    # malformed input fail-closed
    # --------------------------------------------------------

    malformed = {
        "channel": CHANNEL,
        "provenance": PROVENANCE,
        "repairs": [
            {
                "condition": target,
                "after": "UNKNOWN",
                "new_confidence": "STEP66_TEST",
                "new_source": "FORGED_SOURCE",
            }
        ],
    }

    malformed_blocked = False

    try:
        build_site_analysis(
            historical_rule_input=malformed,
        )
    except ValueError:
        malformed_blocked = True

    check(
        "Malformed historical input fail-closed",
        malformed_blocked,
    )

    # --------------------------------------------------------
    # spatial/historical same-name conflict fail-closed
    # --------------------------------------------------------

    baseline_engine = evaluate_site_rules()
    spatial_registry = baseline_engine.get("site_registry", {})

    if not spatial_registry:
        raise AssertionError(
            "No spatial registry entry available for collision test"
        )

    collision_name = next(iter(spatial_registry))
    spatial_value = spatial_registry[collision_name]

    conflicting_state = (
        "FALSE"
        if spatial_value.get("state") != "FALSE"
        else "TRUE"
    )

    collision_input = {
        "channel": CHANNEL,
        "provenance": PROVENANCE,
        "repairs": [
            {
                "condition": collision_name,
                "after": conflicting_state,
                "new_confidence": "STEP66_COLLISION_TEST",
                "new_source": PROVENANCE,
            }
        ],
    }

    collision_blocked = False

    try:
        build_site_analysis(
            historical_rule_input=collision_input,
        )
    except ValueError:
        collision_blocked = True

    check(
        "Spatial/historical collision fail-closed",
        collision_blocked,
    )

    # --------------------------------------------------------
    # spatial channel separation
    # --------------------------------------------------------

    integrated_runtime_conditions = (
        integrated.get("site", {}).get("runtime_conditions", {})
    )

    historical_provenance_in_spatial_runtime = any(
        isinstance(value, dict)
        and (
            value.get("source") == PROVENANCE
            or value.get("provenance") == PROVENANCE
        )
        for value in integrated_runtime_conditions.values()
    )

    check(
        "Historical provenance absent from spatial runtime channel",
        not historical_provenance_in_spatial_runtime,
    )

    print(
        "Historical->spatial overlay merge / runtime registration / API: NONE"
    )
    print(
        "CLASSIFICATION: "
        "STEP66_HISTORICAL_RULE_ENGINE_PRODUCTION_HANDOFF_"
        "BOUNDARY_RECONCILED"
    )


if __name__ == "__main__":
    main()
