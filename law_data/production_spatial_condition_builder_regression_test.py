from __future__ import annotations

import copy
from unittest.mock import patch

import law_data.site_analysis_builder as builder


CLASSIFICATION = "STEP18_PRODUCTION_SPATIAL_CONDITION_BUILDER_PASS"


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected={expected!r}, actual={actual!r}")


def assert_true(value, label: str) -> None:
    if value is not True:
        raise AssertionError(f"{label}: expected True, actual={value!r}")


def assert_false(value, label: str) -> None:
    if value is not False:
        raise AssertionError(f"{label}: expected False, actual={value!r}")


def make_runtime_condition(
    name: str,
    state: str,
    confidence: str,
    resolution: str,
) -> dict:
    return {
        "name": name,
        "type": "SITE",
        "state": state,
        "confidence": confidence,
        "pnu": "1168010300100120000",
        "resolution": resolution,
        "geometry_verified": state in {"TRUE", "FALSE"},
        "source": {
            "provider": "VWorld",
            "dataset": f"SYNTHETIC_{name}",
            "crs": "EPSG:4326",
        },
        "evaluation": {
            "query_success": state in {"TRUE", "FALSE"},
            "intersects": True if state == "TRUE" else False if state == "FALSE" else None,
            "intersection_count": 1 if state == "TRUE" else 0 if state == "FALSE" else None,
        },
        "evidence": {
            "synthetic": True,
            "name": name,
        },
    }


def main() -> None:
    runtime_results = {
        "synthetic true": make_runtime_condition(
            "synthetic true",
            "TRUE",
            "HIGH",
            "SYNTHETIC_TRUE",
        ),
        "synthetic false": make_runtime_condition(
            "synthetic false",
            "FALSE",
            "HIGH",
            "SYNTHETIC_FALSE",
        ),
        "synthetic unknown": make_runtime_condition(
            "synthetic unknown",
            "UNKNOWN",
            "MEDIUM",
            "SYNTHETIC_UNKNOWN",
        ),
    }

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
            return {
                "site_zone": "제2종일반주거지역",
            }
        raise AssertionError(f"unexpected load_json path: {path}")

    def fake_resolve_site_identity(*, base_site, site_input):
        return {
            "pnu": "1168010300100120000",
            "address": "서울특별시 강남구 개포동 12",
            "zone": base_site.get("zone"),
            "land_use_zone": base_site.get("land_use_zone"),
            "coordinate": {
                "x": 127.0,
                "y": 37.0,
                "crs": "EPSG:4326",
            },
        }

    def fake_resolve_site_spatial_payload(*, site):
        return {
            "parcel": {
                "pnu": site["pnu"],
                "geometry_loaded": True,
                "crs": "EPSG:4326",
                "area": {
                    "value": 1000.0,
                },
                "source": {
                    "provider": "SYNTHETIC_PARCEL",
                },
            }
        }

    def fake_resolve_site_spatial_condition(*, condition_name, site, parcel):
        assert_equal(site["pnu"], "1168010300100120000", "resolver SITE PNU")
        assert_equal(parcel["pnu"], site["pnu"], "resolver parcel PNU")
        return copy.deepcopy(runtime_results[condition_name])

    def fake_resolve_zone_base_numeric(zone):
        assert_equal(zone, "제2종일반주거지역", "zone base numeric input")
        return {
            "building_coverage_ratio": 60,
            "floor_area_ratio": 200,
        }

    engine_result = {
        "pipeline": {
            "ready": True,
            "version": "SYNTHETIC_ENGINE_V1",
        },
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
            "APPLICABLE": 2,
            "NOT_APPLICABLE": 1,
            "CONDITIONAL": 0,
            "UNKNOWN": 1,
        },
        "remaining_inputs": {
            "project": [],
            "procedure": [],
        },
        "external_dependencies": {},
        "baseline": {"synthetic": "baseline"},
        "branch_overlay": {"synthetic": "branch"},
        "dynamic_injection": {"synthetic": "dynamic"},
        "site_registry": {"synthetic": "registry"},
        "site_repairs": {"synthetic": "repairs"},
    }

    def fake_evaluate_site_rules(**kwargs):
        captured["site_condition_context"] = copy.deepcopy(
            kwargs["site_condition_context"]
        )
        captured["site_zone_context"] = kwargs["site_zone_context"]
        captured["base_numeric_context"] = copy.deepcopy(
            kwargs["base_numeric_context"]
        )
        return copy.deepcopy(engine_result)

    with (
        patch.object(builder, "load_json", side_effect=fake_load_json),
        patch.object(builder, "resolve_site_identity", side_effect=fake_resolve_site_identity),
        patch.object(
            builder,
            "resolve_site_spatial_payload",
            side_effect=fake_resolve_site_spatial_payload,
        ),
        patch.object(
            builder,
            "get_supported_spatial_conditions",
            return_value=list(runtime_results.keys()),
        ),
        patch.object(
            builder,
            "resolve_site_spatial_condition",
            side_effect=fake_resolve_site_spatial_condition,
        ),
        patch.object(
            builder,
            "resolve_zone_base_numeric",
            side_effect=fake_resolve_zone_base_numeric,
        ),
        patch.object(
            builder,
            "evaluate_site_rules",
            side_effect=fake_evaluate_site_rules,
        ),
    ):
        result = builder.build_site_analysis(
            site_input={
                "land_area": 1000.0,
            }
        )

    site = result["site"]
    shadow = site.get("production_condition_contracts")
    runtime_conditions = site.get("runtime_conditions")

    assert_equal(
        runtime_conditions,
        runtime_results,
        "final SITE runtime conditions preserved",
    )
    assert_equal(
        captured["site_condition_context"],
        runtime_results,
        "Rule Engine receives legacy runtime context unchanged",
    )
    assert_true(isinstance(shadow, dict), "shadow propagated to final SITE")
    assert_equal(set(shadow.keys()), set(runtime_results.keys()), "shadow coverage")

    for name, legacy in runtime_results.items():
        contract = shadow[name]
        assert_equal(contract["state"], legacy["state"], f"{name} state equivalence")
        assert_equal(
            contract["confidence"],
            legacy["confidence"],
            f"{name} confidence equivalence",
        )
        assert_equal(
            contract["provenance"]["resolution"],
            legacy["resolution"],
            f"{name} resolution preservation",
        )
        assert_false(
            contract["production_eligible"],
            f"{name} production eligibility remains false",
        )
        assert_false(
            contract["runtime_registered"],
            f"{name} runtime registration remains false",
        )
        assert_false(
            contract["negative_evidence_allowed"],
            f"{name} negative evidence disabled",
        )
        assert_false(
            contract["legal_absence_inference_allowed"],
            f"{name} legal absence inference disabled",
        )
        assert_false(
            contract["site_promotion_allowed"],
            f"{name} SITE promotion disabled",
        )

    # Rule Engine-facing/public results must equal the synthetic engine result and
    # therefore be independent of the shadow payload.
    assert_equal(result["analysis"]["status"], "READY", "analysis status unchanged")
    assert_equal(
        result["analysis"]["engine_version"],
        engine_result["pipeline"]["version"],
        "engine version unchanged",
    )
    assert_equal(
        result["regulation"]["building_coverage_ratio"]["value"],
        60,
        "BCR unchanged",
    )
    assert_equal(
        result["regulation"]["floor_area_ratio"]["value"],
        200,
        "FAR unchanged",
    )
    assert_equal(
        result["rule_evaluation"],
        {
            "total": 4,
            "applicable": 2,
            "not_applicable": 1,
            "conditional": 0,
            "unknown": 1,
        },
        "rule summary unchanged",
    )
    assert_equal(
        result["rule_engine"]["site_registry"],
        engine_result["site_registry"],
        "Rule Engine site registry unchanged",
    )
    assert_equal(
        result["rule_engine"]["numeric"],
        engine_result["numeric"],
        "Rule Engine numeric unchanged",
    )

    print("=" * 72)
    print("STEP 18 PRODUCTION SPATIAL CONDITION BUILDER REGRESSION")
    print("=" * 72)
    print("Network access required: NO")
    print("Final SITE shadow propagation: PASS")
    print("Legacy runtime_conditions preservation: PASS")
    print("Rule Engine legacy context preservation: PASS")
    print("TRUE/FALSE/UNKNOWN shadow equivalence: PASS")
    print("Production eligibility/runtime registration remain False: PASS")
    print("Rule Engine result invariance: PASS")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
