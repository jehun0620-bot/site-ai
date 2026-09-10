from __future__ import annotations

import copy
from unittest.mock import patch

import law_data.site_analysis_builder as builder


CLASSIFICATION = "STEP18_PRODUCTION_SITE_CONDITION_BUILDER_COLLECTOR_PASS"


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected={expected!r}, actual={actual!r}")


def assert_true(value, label: str) -> None:
    if value is not True:
        raise AssertionError(f"{label}: expected True, actual={value!r}")


def assert_false(value, label: str) -> None:
    if value is not False:
        raise AssertionError(f"{label}: expected False, actual={value!r}")


def spatial_runtime() -> dict:
    return {
        "name": "synthetic spatial",
        "type": "SITE",
        "state": "TRUE",
        "confidence": "HIGH",
        "pnu": "1168010300100120000",
        "resolution": "SYNTHETIC_SPATIAL_TRUE",
        "geometry_verified": True,
        "source": {"provider": "SYNTHETIC"},
        "evaluation": {"query_success": True, "intersects": True},
        "evidence": {"synthetic": True},
    }


def historical_contract() -> dict:
    return {
        "name": "도시지역편입해제구역",
        "condition_type": "SITE_HISTORY",
        "resolution_type": "HISTORICAL_SITE_EVENT",
        "state": "UNKNOWN",
        "confidence": "MEDIUM",
        "source": "URBAN_AREA_CONVERSION_HISTORICAL_SITE_EVENT_SHADOW",
        "provenance": {
            "standard_code_verified": False,
            "provenance_policy_verified": False,
            "runtime_registration_policy_verified": False,
            "resolver_resolution": "UNKNOWN",
        },
        "production_eligible": False,
        "runtime_registered": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_promotion_allowed": False,
        "diagnostics": {"synthetic": True},
    }


def engine_result() -> dict:
    return {
        "pipeline": {"ready": True, "version": "SYNTHETIC_ENGINE_V1"},
        "numeric": {
            "building_coverage_ratio": 60,
            "floor_area_ratio": 200,
            "resolution": "SYNTHETIC_NUMERIC",
            "direct_relaxation_count": 0,
            "active_before_guard": 0,
            "excluded_count": 0,
            "retained_count": 0,
        },
        "rule_summary": {
            "APPLICABLE": 1,
            "NOT_APPLICABLE": 0,
            "CONDITIONAL": 0,
            "UNKNOWN": 0,
        },
        "remaining_inputs": {"project": [], "procedure": []},
        "external_dependencies": {},
        "baseline": {},
        "branch_overlay": {},
        "dynamic_injection": {},
        "site_registry": {},
        "site_repairs": {},
    }


def main() -> None:
    runtime = spatial_runtime()
    historical = historical_contract()
    historical_source = {historical["name"]: historical}
    historical_before = copy.deepcopy(historical_source)
    captured = {}

    def fake_load_json(path):
        if path == builder.SITE_COMPLETE_PATH:
            return {
                "site": {
                    "zone": "제2종일반주거지역",
                    "land_use_zone": "제2종일반주거지역",
                }
            }
        if path == builder.BASE_NUMERIC_PATH:
            return {"site_zone": "제2종일반주거지역"}
        raise AssertionError(f"unexpected load_json path: {path}")

    def fake_identity(*, base_site, site_input):
        return {
            "pnu": "1168010300100120000",
            "zone": base_site["zone"],
            "land_use_zone": base_site["land_use_zone"],
            "coordinate": {"x": 127.0, "y": 37.0, "crs": "EPSG:4326"},
        }

    def fake_spatial(*, site):
        return {
            "parcel": {
                "pnu": site["pnu"],
                "area": {"value": 1000.0},
                "source": {},
            }
        }

    def fake_condition(*, condition_name, site, parcel):
        assert_equal(condition_name, runtime["name"], "spatial resolver name")
        return copy.deepcopy(runtime)

    def fake_engine(**kwargs):
        captured["site_condition_context"] = copy.deepcopy(
            kwargs["site_condition_context"]
        )
        return engine_result()

    with (
        patch.object(builder, "load_json", side_effect=fake_load_json),
        patch.object(builder, "resolve_site_identity", side_effect=fake_identity),
        patch.object(builder, "resolve_site_spatial_payload", side_effect=fake_spatial),
        patch.object(
            builder,
            "get_supported_spatial_conditions",
            return_value=[runtime["name"]],
        ),
        patch.object(
            builder,
            "resolve_site_spatial_condition",
            side_effect=fake_condition,
        ),
        patch.object(
            builder,
            "resolve_zone_base_numeric",
            return_value={"building_coverage_ratio": 60, "floor_area_ratio": 200},
        ),
        patch.object(builder, "evaluate_site_rules", side_effect=fake_engine),
    ):
        result = builder.build_site_analysis(
            site_input={"land_area": 1000.0},
            production_condition_shadow_sources=historical_source,
        )

    site = result["site"]
    contracts = site["production_condition_contracts"]

    assert_equal(historical_source, historical_before, "external shadow source unchanged")
    assert_equal(
        captured["site_condition_context"],
        {runtime["name"]: runtime},
        "Rule Engine receives spatial runtime context only",
    )
    assert_equal(
        site["runtime_conditions"],
        {runtime["name"]: runtime},
        "legacy runtime conditions unchanged",
    )
    assert_equal(
        set(contracts),
        {runtime["name"], historical["name"]},
        "SPATIAL + SITE_HISTORY collected",
    )

    spatial_contract = contracts[runtime["name"]]
    historical_result = contracts[historical["name"]]
    assert_equal(spatial_contract["state"], "TRUE", "spatial TRUE preserved")
    assert_equal(spatial_contract["condition_type"], "SITE", "spatial SITE type")
    assert_equal(spatial_contract["resolution_type"], "SPATIAL", "spatial type")
    assert_equal(historical_result["state"], "UNKNOWN", "historical UNKNOWN preserved")
    assert_equal(
        historical_result["condition_type"],
        "SITE_HISTORY",
        "historical SITE_HISTORY type",
    )
    assert_equal(
        historical_result["resolution_type"],
        "HISTORICAL_SITE_EVENT",
        "historical resolution type",
    )
    assert_false(
        historical_result["production_eligible"],
        "historical production eligibility remains false",
    )
    assert_false(
        historical_result["runtime_registered"],
        "historical runtime registration remains false",
    )
    assert_false(
        historical_result["negative_evidence_allowed"],
        "historical negative evidence disabled",
    )
    assert_false(
        historical_result["legal_absence_inference_allowed"],
        "historical legal absence disabled",
    )
    assert_false(
        historical_result["site_promotion_allowed"],
        "historical SITE promotion disabled",
    )
    assert_equal(result["analysis"]["status"], "READY", "analysis unchanged")
    assert_equal(
        result["regulation"]["building_coverage_ratio"]["value"],
        60,
        "Rule Engine BCR unchanged",
    )

    duplicate = {runtime["name"]: copy.deepcopy(spatial_contract)}
    duplicate_before = copy.deepcopy(duplicate)
    duplicate_blocked = False
    with (
        patch.object(builder, "load_json", side_effect=fake_load_json),
        patch.object(builder, "resolve_site_identity", side_effect=fake_identity),
        patch.object(builder, "resolve_site_spatial_payload", side_effect=fake_spatial),
        patch.object(
            builder,
            "get_supported_spatial_conditions",
            return_value=[runtime["name"]],
        ),
        patch.object(
            builder,
            "resolve_site_spatial_condition",
            side_effect=fake_condition,
        ),
    ):
        try:
            builder.build_site_analysis(
                production_condition_shadow_sources=duplicate,
            )
        except ValueError:
            duplicate_blocked = True

    assert_true(duplicate_blocked, "duplicate condition fail-closed")
    assert_equal(duplicate, duplicate_before, "duplicate source unchanged")

    print("=" * 72)
    print("STEP 18 PRODUCTION SITE CONDITION BUILDER COLLECTOR REGRESSION")
    print("=" * 72)
    print("SPATIAL + SITE_HISTORY final collection: PASS")
    print("Historical UNKNOWN preservation: PASS")
    print("Rule Engine spatial-context isolation: PASS")
    print("Legacy runtime_conditions preservation: PASS")
    print("External shadow source mutation: NONE")
    print("Duplicate-name fail-closed: PASS")
    print("Production eligibility/runtime registration promotion: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
