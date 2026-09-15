"""STEP65 historical merged registry Rule Engine integration audit."""
from __future__ import annotations

import copy

from law_data.historical_merged_registry_live_consumption_authorization import (
    authorize_historical_merged_registry_live_consumption,
)
from law_data.historical_spatial_registry_collision_policy import (
    evaluate_historical_spatial_registry_collision_policy,
)
from law_data.historical_site_event_builder_injection_payload import (
    PROVENANCE,
)
from law_data.rule_evaluation_pipeline import evaluate_site_rules


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise AssertionError(name)


def find_existing_condition(result):
    for rule in result.get("rules", []):
        if not isinstance(rule, dict):
            continue

        for condition in rule.get("conditions", []):
            if not isinstance(condition, dict):
                continue

            name = str(condition.get("name", "")).strip()

            if name:
                return name, copy.deepcopy(condition)

    raise AssertionError("No existing rule condition found")


def find_condition(result, target_name):
    matches = []

    for rule in result.get("rules", []):
        if not isinstance(rule, dict):
            continue

        for condition in rule.get("conditions", []):
            if (
                isinstance(condition, dict)
                and condition.get("name") == target_name
            ):
                matches.append(copy.deepcopy(condition))

    return matches


def main():
    print("=" * 72)
    print("STEP 65 HISTORICAL MERGED REGISTRY RULE ENGINE INTEGRATION")
    print("=" * 72)

    legacy = evaluate_site_rules()

    # --------------------------------------------------------
    # zero-op authorization: legacy behavior must remain exact
    # --------------------------------------------------------

    zero_policy = evaluate_historical_spatial_registry_collision_policy(
        legacy["site_registry"],
        {},
    )
    zero_authorization = (
        authorize_historical_merged_registry_live_consumption(
            zero_policy
        )
    )

    zero_integrated = evaluate_site_rules(
        historical_registry_authorization=zero_authorization,
    )

    check(
        "Legacy default compatibility",
        legacy["site_registry"] == zero_integrated["site_registry"]
        and legacy["site_repairs"] == zero_integrated["site_repairs"],
    )

    # --------------------------------------------------------
    # actual historical Rule Engine consumption
    #
    # Use a condition already present in the clean Rule Engine
    # result so apply_site_registry() has a real target.
    #
    # The spatial side intentionally omits that name.
    # --------------------------------------------------------

    condition_name, existing = find_existing_condition(legacy)

    historical_registry = {
        condition_name: {
            "state": "UNKNOWN",
            "confidence": "STEP65_TEST",
            "source": PROVENANCE,
        }
    }

    historical_policy = (
        evaluate_historical_spatial_registry_collision_policy(
            {},
            historical_registry,
        )
    )

    historical_authorization = (
        authorize_historical_merged_registry_live_consumption(
            historical_policy
        )
    )

    authorization_before = copy.deepcopy(
        historical_authorization.to_dict()
    )

    historical_integrated = evaluate_site_rules(
        historical_registry_authorization=historical_authorization,
    )

    matches = find_condition(
        historical_integrated,
        condition_name,
    )

    historical_applied = bool(matches) and all(
        item.get("state") == "UNKNOWN"
        and item.get("confidence") == "STEP65_TEST"
        and item.get("source") == PROVENANCE
        for item in matches
    )

    repair_matches = [
        item
        for item in historical_integrated.get("site_repairs", [])
        if item.get("condition") == condition_name
    ]

    provenance_repair_recorded = bool(repair_matches) and all(
        item.get("new_source") == PROVENANCE
        for item in repair_matches
    )

    check(
        "Actual historical registry consumption",
        historical_authorization.live_consumption_authorized is True
        and historical_applied,
    )

    check(
        "Historical provenance preserved in Rule Engine",
        provenance_repair_recorded,
    )

    # --------------------------------------------------------
    # forged object must not cross STEP64 boundary
    # --------------------------------------------------------

    class ForgedAuthorization:
        boundary = (
            "HISTORICAL_MERGED_REGISTRY_LIVE_CONSUMPTION_AUTHORIZATION"
        )
        live_consumption_authorized = True
        authorized_merged_registry = {}

    forged_blocked = False

    try:
        evaluate_site_rules(
            historical_registry_authorization=ForgedAuthorization(),
        )
    except ValueError:
        forged_blocked = True

    check(
        "Forged authorization fail-closed",
        forged_blocked,
    )

    check(
        "Caller authorization immutability",
        historical_authorization.to_dict()
        == authorization_before,
    )

    check(
        "Legacy spatial registry unchanged",
        legacy["site_registry"]
        == zero_integrated["site_registry"],
    )

    print(
        "Builder wiring / spatial overlay modification / runtime / API: NONE"
    )
    print(
        "CLASSIFICATION: "
        "STEP65_HISTORICAL_MERGED_REGISTRY_RULE_ENGINE_INTEGRATION_"
        "BOUNDARY_RECONCILED"
    )


if __name__ == "__main__":
    main()
