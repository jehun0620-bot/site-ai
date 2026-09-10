from __future__ import annotations

from law_data.production_site_condition import FALSE, TRUE, UNKNOWN
from law_data.production_spatial_condition_adapter import (
    ADAPTER_NAME,
    RUNTIME_SOURCE_MARKER,
    adapt_spatial_condition_to_production_contract,
)


CLASSIFICATION = "STEP18_PRODUCTION_SPATIAL_CONDITION_ADAPTER_PASS"


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected={expected!r}, actual={actual!r}")


def assert_true(value, label: str) -> None:
    if value is not True:
        raise AssertionError(f"{label}: expected True, actual={value!r}")


def assert_false(value, label: str) -> None:
    if value is not False:
        raise AssertionError(f"{label}: expected False, actual={value!r}")


def make_raw(state: str, *, geometry_verified: bool, resolution: str):
    return {
        "name": "개발진흥지구",
        "type": "SITE",
        "state": state,
        "confidence": "HIGH" if state != UNKNOWN else "MEDIUM",
        "pnu": "1168010300100120000",
        "resolution": resolution,
        "geometry_verified": geometry_verified,
        "source": {
            "provider": "VWorld",
            "dataset": "LT_C_UQ129",
            "crs": "EPSG:4326",
        },
        "evaluation": {
            "query_success": state != UNKNOWN,
            "intersects": True if state == TRUE else False if state == FALSE else None,
            "intersection_count": 1 if state == TRUE else 0 if state == FALSE else None,
        },
        "evidence": {
            "query": {"classification": "QUERY_SUCCESS" if state != UNKNOWN else "QUERY_FAILED"},
            "synthetic": True,
        },
    }


def main() -> None:
    explicit_true = adapt_spatial_condition_to_production_contract(
        make_raw(
            TRUE,
            geometry_verified=True,
            resolution="PARCEL_INTERSECTS_DEVELOPMENT_PROMOTION_DISTRICT",
        )
    )
    assert_equal(explicit_true.state, TRUE, "TRUE preserved")

    explicit_false = adapt_spatial_condition_to_production_contract(
        make_raw(
            FALSE,
            geometry_verified=True,
            resolution="PARCEL_DOES_NOT_INTERSECT_DEVELOPMENT_PROMOTION_DISTRICT",
        )
    )
    assert_equal(explicit_false.state, FALSE, "FALSE preserved")

    unknown = adapt_spatial_condition_to_production_contract(
        make_raw(
            UNKNOWN,
            geometry_verified=False,
            resolution="DEVELOPMENT_PROMOTION_DISTRICT_QUERY_FAILED",
        )
    )
    assert_equal(unknown.state, UNKNOWN, "UNKNOWN preserved")

    malformed_raw = make_raw(
        "QUERY_FAILED",
        geometry_verified=False,
        resolution="DEVELOPMENT_PROMOTION_DISTRICT_QUERY_FAILED",
    )
    malformed = adapt_spatial_condition_to_production_contract(malformed_raw)
    assert_equal(malformed.state, UNKNOWN, "malformed state fails closed")

    assert_equal(
        explicit_true.resolution_type,
        "SPATIAL",
        "resolution type fixed to SPATIAL",
    )
    assert_equal(
        explicit_true.source,
        RUNTIME_SOURCE_MARKER,
        "registry-level source marker",
    )
    assert_equal(
        explicit_true.provenance["adapter"],
        ADAPTER_NAME,
        "adapter provenance preserved",
    )
    assert_equal(
        explicit_true.provenance["pnu"],
        "1168010300100120000",
        "PNU preserved",
    )
    assert_true(
        explicit_true.provenance["geometry_verified"],
        "geometry_verified preserved",
    )
    assert_equal(
        explicit_true.provenance["resolution"],
        "PARCEL_INTERSECTS_DEVELOPMENT_PROMOTION_DISTRICT",
        "resolution preserved",
    )
    assert_equal(
        explicit_true.provenance["runtime_source"]["dataset"],
        "LT_C_UQ129",
        "runtime source preserved",
    )
    assert_equal(
        explicit_true.diagnostics["evaluation"]["intersects"],
        True,
        "evaluation preserved",
    )
    assert_true(
        explicit_true.diagnostics["evidence"]["synthetic"],
        "evidence preserved",
    )

    # Adapter must never infer production eligibility or registration from a
    # positive spatial result or verified geometry.
    assert_false(
        explicit_true.production_eligible,
        "TRUE/geometry cannot manufacture production eligibility",
    )
    assert_false(
        explicit_true.runtime_registered,
        "TRUE/geometry cannot manufacture runtime registration",
    )

    # Explicit gates are independent metadata and cannot change state.
    explicit_gates = adapt_spatial_condition_to_production_contract(
        make_raw(
            UNKNOWN,
            geometry_verified=False,
            resolution="DEVELOPMENT_PROMOTION_DISTRICT_QUERY_FAILED",
        ),
        production_eligible=True,
        runtime_registered=True,
    )
    assert_true(explicit_gates.production_eligible, "explicit eligibility preserved")
    assert_true(explicit_gates.runtime_registered, "explicit registration preserved")
    assert_equal(
        explicit_gates.state,
        UNKNOWN,
        "explicit gates cannot promote UNKNOWN",
    )

    # Query-failure diagnostics remain non-dispositive.
    assert_equal(
        unknown.diagnostics["evaluation"]["query_success"],
        False,
        "query failure diagnostic preserved",
    )
    assert_equal(
        unknown.state,
        UNKNOWN,
        "query failure cannot manufacture FALSE",
    )

    for condition, label in (
        (explicit_true, "TRUE"),
        (explicit_false, "FALSE"),
        (unknown, "UNKNOWN"),
        (malformed, "MALFORMED"),
    ):
        assert_false(
            condition.negative_evidence_allowed,
            f"{label} negative evidence disabled",
        )
        assert_false(
            condition.legal_absence_inference_allowed,
            f"{label} legal absence inference disabled",
        )
        assert_false(
            condition.site_promotion_allowed,
            f"{label} SITE promotion disabled",
        )

    print("=" * 72)
    print("STEP 18 PRODUCTION SPATIAL CONDITION ADAPTER REGRESSION")
    print("=" * 72)
    print("TRUE/FALSE/UNKNOWN preservation: PASS")
    print("Malformed state fail-closed: PASS")
    print("PNU/geometry/resolution/source/evaluation/evidence preservation: PASS")
    print("Production eligibility default False: PASS")
    print("Runtime registration default False: PASS")
    print("Query failure cannot manufacture FALSE: PASS")
    print("Geometry verification cannot manufacture eligibility: PASS")
    print("Negative/legal absence/SITE promotion disabled: PASS")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
