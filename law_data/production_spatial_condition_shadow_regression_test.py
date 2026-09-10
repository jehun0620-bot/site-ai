from __future__ import annotations

import copy

from law_data.site_analysis_builder import (
    build_production_condition_contract_shadow,
)


CLASSIFICATION = "STEP18_PRODUCTION_SPATIAL_CONDITION_SHADOW_PASS"


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected={expected!r}, actual={actual!r}")


def assert_true(value, label: str) -> None:
    if value is not True:
        raise AssertionError(f"{label}: expected True, actual={value!r}")


def assert_false(value, label: str) -> None:
    if value is not False:
        raise AssertionError(f"{label}: expected False, actual={value!r}")


def make_condition(name: str, state: str, confidence: str, resolution: str):
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
            "dataset": "SYNTHETIC_DATASET",
            "crs": "EPSG:4326",
        },
        "evaluation": {
            "query_success": state in {"TRUE", "FALSE"},
            "intersects": True if state == "TRUE" else False if state == "FALSE" else None,
            "intersection_count": 1 if state == "TRUE" else 0 if state == "FALSE" else None,
        },
        "evidence": {
            "synthetic": True,
        },
    }


def main() -> None:
    legacy_context = {
        "synthetic true": make_condition(
            "synthetic true",
            "TRUE",
            "HIGH",
            "SYNTHETIC_TRUE",
        ),
        "synthetic false": make_condition(
            "synthetic false",
            "FALSE",
            "HIGH",
            "SYNTHETIC_FALSE",
        ),
        "synthetic unknown": make_condition(
            "synthetic unknown",
            "UNKNOWN",
            "MEDIUM",
            "SYNTHETIC_UNKNOWN",
        ),
    }

    before = copy.deepcopy(legacy_context)
    shadow = build_production_condition_contract_shadow(legacy_context)

    # Shadow generation must be read-only with respect to legacy Rule Engine input.
    assert_equal(legacy_context, before, "legacy context unchanged")
    assert_equal(set(shadow.keys()), set(legacy_context.keys()), "shadow names preserved")

    for name, legacy in legacy_context.items():
        contract = shadow[name]

        assert_equal(contract["name"], legacy["name"], f"{name} name equivalence")
        assert_equal(contract["condition_type"], "SITE", f"{name} condition type")
        assert_equal(contract["resolution_type"], "SPATIAL", f"{name} resolution type")
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
        assert_equal(
            contract["provenance"]["pnu"],
            legacy["pnu"],
            f"{name} PNU preservation",
        )
        assert_equal(
            contract["provenance"]["geometry_verified"],
            legacy["geometry_verified"],
            f"{name} geometry preservation",
        )
        assert_equal(
            contract["diagnostics"]["evaluation"],
            legacy["evaluation"],
            f"{name} evaluation preservation",
        )
        assert_equal(
            contract["diagnostics"]["evidence"],
            legacy["evidence"],
            f"{name} evidence preservation",
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

    # Malformed state can only fail closed in the shadow; it must not mutate the
    # legacy context that still feeds the Rule Engine in this stage.
    malformed_context = {
        "synthetic malformed": make_condition(
            "synthetic malformed",
            "QUERY_FAILED",
            "LOW",
            "SYNTHETIC_QUERY_FAILED",
        )
    }
    malformed_before = copy.deepcopy(malformed_context)
    malformed_shadow = build_production_condition_contract_shadow(malformed_context)
    assert_equal(malformed_context, malformed_before, "malformed legacy unchanged")
    assert_equal(
        malformed_shadow["synthetic malformed"]["state"],
        "UNKNOWN",
        "malformed shadow fails closed",
    )

    # Non-dict entries are ignored rather than converted into legal state.
    mixed_context = {
        "valid": make_condition("valid", "UNKNOWN", "LOW", "SYNTHETIC_UNKNOWN"),
        "invalid": "NOT_A_CONDITION",
    }
    mixed_shadow = build_production_condition_contract_shadow(mixed_context)
    assert_true("valid" in mixed_shadow, "valid condition retained")
    assert_false("invalid" in mixed_shadow, "invalid condition not manufactured")

    assert_equal(
        build_production_condition_contract_shadow(None),
        {},
        "missing context returns empty shadow",
    )

    print("=" * 72)
    print("STEP 18 PRODUCTION SPATIAL CONDITION SHADOW REGRESSION")
    print("=" * 72)
    print("Legacy runtime context mutation: NONE")
    print("TRUE/FALSE/UNKNOWN semantic equivalence: PASS")
    print("Confidence/provenance/diagnostics preservation: PASS")
    print("Malformed shadow state fail-closed: PASS")
    print("Production eligibility/runtime registration remain False: PASS")
    print("Negative/legal absence/SITE promotion remain disabled: PASS")
    print("Rule Engine input replacement: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
