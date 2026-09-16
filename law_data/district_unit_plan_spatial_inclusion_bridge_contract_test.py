from __future__ import annotations

from copy import deepcopy

from .district_unit_plan_spatial_inclusion_bridge import (
    bridge_district_unit_plan_spatial_inclusion,
)


PNU = "1168010300100120000"


def _verified_raw() -> dict:
    return {
        "name": "지구단위계획",
        "type": "SITE",
        "state": "TRUE",
        "confidence": "HIGH",
        "pnu": PNU,
        "resolution": "DISTRICT_UNIT_PLAN_INTERSECTION_VERIFIED",
        "geometry_verified": True,
        "source": {
            "provider": "VWorld",
            "dataset": "LT_C_UPISUQ161",
            "crs": "EPSG:4326",
        },
        "evaluation": {
            "query_success": True,
            "intersects": True,
            "intersection_count": 1,
        },
        "evidence": {"marker": "verified-spatial-evidence"},
    }


def main() -> None:
    raw = _verified_raw()
    admitted = bridge_district_unit_plan_spatial_inclusion(raw, canonical_pnu=PNU)
    assert admitted["site_spatial_inclusion_verified"] is True
    assert admitted["canonical_pnu"] == PNU
    assert admitted["source_pnu"] == PNU
    assert admitted["dataset"] == "LT_C_UPISUQ161"
    assert admitted["evidence"] == raw

    for key in (
        "site_truth_decision_allowed",
        "site_promotion_allowed",
        "production_registration_allowed",
        "runtime_registration_allowed",
    ):
        assert admitted[key] is False

    mutations = (
        ("wrong name", lambda x: x.update(name="개발진흥지구")),
        ("wrong type", lambda x: x.update(type="SITE_HISTORY")),
        ("wrong pnu", lambda x: x.update(pnu="1111010100100010000")),
        ("false state", lambda x: x.update(state="FALSE")),
        ("unknown state", lambda x: x.update(state="UNKNOWN")),
        ("low confidence", lambda x: x.update(confidence="LOW")),
        ("geometry unverified", lambda x: x.update(geometry_verified=False)),
        (
            "wrong dataset",
            lambda x: x["source"].update(dataset="LT_C_UQ129"),
        ),
        (
            "query failed",
            lambda x: x["evaluation"].update(query_success=False),
        ),
        (
            "no intersection",
            lambda x: x["evaluation"].update(intersects=False),
        ),
        (
            "zero intersection count",
            lambda x: x["evaluation"].update(intersection_count=0),
        ),
    )

    for label, mutate in mutations:
        candidate = deepcopy(raw)
        mutate(candidate)
        rejected = bridge_district_unit_plan_spatial_inclusion(
            candidate,
            canonical_pnu=PNU,
        )
        assert rejected["site_spatial_inclusion_verified"] is False, label
        assert rejected["evidence"] == {}, label

    missing_pnu = bridge_district_unit_plan_spatial_inclusion(raw, canonical_pnu="")
    assert missing_pnu["site_spatial_inclusion_verified"] is False

    malformed = bridge_district_unit_plan_spatial_inclusion(None, canonical_pnu=PNU)
    assert malformed["site_spatial_inclusion_verified"] is False
    assert malformed["evidence"] == {}

    print("DISTRICT_UNIT_PLAN_SPATIAL_INCLUSION_BRIDGE_CONTRACT_PASS")


if __name__ == "__main__":
    main()
