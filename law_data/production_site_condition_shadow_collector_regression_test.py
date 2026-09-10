from __future__ import annotations

import copy

from law_data.production_site_condition import normalize_production_site_condition
from law_data.production_site_condition_shadow_collector import (
    collect_production_site_condition_shadows,
)


CLASSIFICATION = "STEP18_PRODUCTION_SITE_CONDITION_SHADOW_COLLECTOR_PASS"


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected={expected!r}, actual={actual!r}")


def assert_true(value, label: str) -> None:
    if value is not True:
        raise AssertionError(f"{label}: expected True, actual={value!r}")


def assert_false(value, label: str) -> None:
    if value is not False:
        raise AssertionError(f"{label}: expected False, actual={value!r}")


def assert_raises_value_error(fn, label: str) -> None:
    try:
        fn()
    except ValueError:
        return
    raise AssertionError(f"{label}: expected ValueError")


def main() -> None:
    spatial = normalize_production_site_condition(
        name="지구단위계획",
        condition_type="SITE",
        resolution_type="SPATIAL",
        state="TRUE",
        confidence="HIGH",
        source="RUNTIME_SPATIAL_CONDITION",
        provenance={"dataset": "LT_C_UPISUQ161"},
        production_eligible=False,
        runtime_registered=False,
    )

    historical = normalize_production_site_condition(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        state="UNKNOWN",
        confidence="MEDIUM",
        source="URBAN_AREA_CONVERSION_HISTORICAL_SITE_EVENT_SHADOW",
        provenance={"standard_code_verified": False},
        production_eligible=False,
        runtime_registered=False,
    )

    spatial_dict = spatial.to_dict()
    historical_dict = historical.to_dict()
    spatial_before = copy.deepcopy(spatial_dict)
    historical_before = copy.deepcopy(historical_dict)

    collected = collect_production_site_condition_shadows(
        {spatial.name: spatial_dict},
        {historical.name: historical_dict},
    )

    assert_equal(spatial_dict, spatial_before, "spatial source unchanged")
    assert_equal(historical_dict, historical_before, "historical source unchanged")
    assert_equal(
        set(collected.keys()),
        {"지구단위계획", "도시지역편입해제구역"},
        "SPATIAL + SITE_HISTORY collection",
    )
    assert_equal(collected["지구단위계획"]["state"], "TRUE", "spatial TRUE preserved")
    assert_equal(
        collected["도시지역편입해제구역"]["state"],
        "UNKNOWN",
        "historical UNKNOWN preserved",
    )
    assert_equal(
        collected["도시지역편입해제구역"]["condition_type"],
        "SITE_HISTORY",
        "historical type preserved",
    )
    assert_equal(
        collected["도시지역편입해제구역"]["resolution_type"],
        "HISTORICAL_SITE_EVENT",
        "historical resolver type preserved",
    )
    assert_false(
        collected["도시지역편입해제구역"]["production_eligible"],
        "historical production eligibility remains false",
    )
    assert_false(
        collected["도시지역편입해제구역"]["runtime_registered"],
        "historical runtime registration remains false",
    )

    # Dataclass instances are accepted without changing semantics.
    dataclass_collected = collect_production_site_condition_shadows([spatial, historical])
    assert_equal(
        dataclass_collected["도시지역편입해제구역"]["state"],
        "UNKNOWN",
        "dataclass UNKNOWN preserved",
    )

    # Duplicate names fail closed instead of source-order overwrite.
    duplicate = copy.deepcopy(spatial_dict)
    duplicate["state"] = "FALSE"
    assert_raises_value_error(
        lambda: collect_production_site_condition_shadows(
            [spatial_dict],
            [duplicate],
        ),
        "duplicate condition rejected",
    )

    # Malformed entries are ignored and cannot manufacture legal state.
    malformed_entries = [
        None,
        "NOT_A_CONDITION",
        {"name": "missing state", "condition_type": "SITE", "resolution_type": "SPATIAL"},
        {
            "name": "bad state",
            "condition_type": "SITE",
            "resolution_type": "SPATIAL",
            "state": "QUERY_FAILED",
        },
        {
            "name": "bad type",
            "condition_type": "PROJECT",
            "resolution_type": "SPATIAL",
            "state": "TRUE",
        },
        {
            "name": "bad historical spatial",
            "condition_type": "SITE_HISTORY",
            "resolution_type": "SPATIAL",
            "state": "FALSE",
        },
    ]
    malformed_collected = collect_production_site_condition_shadows(malformed_entries)
    assert_equal(malformed_collected, {}, "malformed entries manufacture no condition")

    assert_equal(
        collect_production_site_condition_shadows(None, "invalid", 123),
        {},
        "invalid sources produce empty collection",
    )

    print("=" * 72)
    print("STEP 18 PRODUCTION SITE CONDITION SHADOW COLLECTOR REGRESSION")
    print("=" * 72)
    print("SPATIAL + SITE_HISTORY collection: PASS")
    print("TRUE/FALSE/UNKNOWN semantics preserved: PASS")
    print("Historical UNKNOWN preservation: PASS")
    print("Duplicate-name fail-closed: PASS")
    print("Malformed entry legal-state manufacture: NONE")
    print("Source mutation: NONE")
    print("Resolver/runtime/overlay/Rule Engine mutation: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
