from __future__ import annotations

from copy import deepcopy

from law_data.hybrid_spatial_notice_uqq700_site_geometry_recovery_bridge import (
    TARGET_SITE_ID,
    TARGET_SITE_PNU,
    bridge_uqq700_site_geometry_recovery,
)


PASS_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_SITE_GEOMETRY_RECOVERY_BRIDGE_PASS"
FAIL_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_SITE_GEOMETRY_RECOVERY_BRIDGE_REGRESSION"


def positive_recovery(*, crs=None, crs_status="SOURCE_CRS_NOT_EXPLICIT"):
    return {
        "site": {"pnu": TARGET_SITE_PNU},
        "source": {
            "snapshot": "D:/site-ai/law_data/output/seoul_urban_innovation_zone_mapplan_intersection.json",
            "dataset": "MapPlan",
            "recovery": {"mode": "DIRECT_JSON", "path": "$.parcel"},
        },
        "parcel": {
            "geometry_type": "Polygon",
            "area": 120945.65223377591,
            "bounds": [962201.02522, 1943722.58159, 962711.06096, 1944220.16506],
            "crs": crs,
            "crs_status": crs_status,
            "geometry_snapshot": "D:/site-ai/law_data/output/site_parcel_spatial_snapshot.geojson",
        },
        "validations": {
            "feature recovered": True,
            "target PNU": True,
            "geometry dict": True,
            "geometry Polygon": True,
            "coordinates exist": True,
            "calculated bounds": True,
            "expected bounds match": True,
            "area evidence found": True,
            "bounds evidence found": True,
        },
        "all_pass": True,
    }


def changed(base, path, value):
    result = deepcopy(base)
    cursor = result
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    return result


def main() -> int:
    checks: list[tuple[str, bool]] = []

    recovery = positive_recovery()
    verified = bridge_uqq700_site_geometry_recovery(
        recovery,
        site_id=TARGET_SITE_ID,
        source_snapshot_verified=True,
    )

    checks.append((
        "exact target SITE/PNU and verified recovery bind SITE geometry",
        verified["exact_site_identity_verified"] is True
        and verified["recovery_validations_verified"] is True
        and verified["recovery_source_verified"] is True
        and verified["polygon_verified"] is True
        and verified["site_geometry_provenance_verified"] is True
        and verified["site_geometry_bound_to_target_site"] is True,
    ))
    checks.append((
        "non-explicit CRS stays unverified and never becomes intersection-ready",
        verified["crs_status"] == "SOURCE_CRS_NOT_EXPLICIT"
        and verified["crs_verified"] is False
        and verified["intersection_ready"] is False,
    ))
    checks.append((
        "SITE geometry bridge cannot manufacture UQQ700 Gate 3 or runtime",
        verified["official_spatial_source_verified"] is False
        and verified["designation_geometry_bound"] is False
        and verified["positive_spatial_intersection_verified"] is False
        and verified["site_spatial_inclusion_verified"] is False
        and verified["minimum_registration_gate_satisfied"] is False
        and verified["runtime_registration_allowed"] is False,
    ))
    checks.append((
        "SITE FALSE, promotion, legal absence, and negative inference remain disabled",
        verified["site_false_inference_allowed"] is False
        and verified["site_promotion_allowed"] is False
        and verified["legal_absence_inference_allowed"] is False
        and verified["negative_evidence_allowed"] is False,
    ))

    wrong_site = bridge_uqq700_site_geometry_recovery(
        recovery,
        site_id="11680-10300-0013-0000",
        source_snapshot_verified=True,
    )
    checks.append((
        "wrong SITE id fails closed even when PNU matches",
        wrong_site["exact_site_identity_verified"] is False
        and wrong_site["site_geometry_bound_to_target_site"] is False,
    ))

    wrong_pnu = bridge_uqq700_site_geometry_recovery(
        changed(recovery, ("site", "pnu"), "1168010300100130000"),
        site_id=TARGET_SITE_ID,
        source_snapshot_verified=True,
    )
    checks.append((
        "wrong recovered PNU fails closed",
        wrong_pnu["exact_site_identity_verified"] is False
        and wrong_pnu["site_geometry_bound_to_target_site"] is False,
    ))

    unverified_snapshot = bridge_uqq700_site_geometry_recovery(
        recovery,
        site_id=TARGET_SITE_ID,
        source_snapshot_verified=False,
    )
    checks.append((
        "unverified source snapshot fails closed",
        unverified_snapshot["recovery_source_verified"] is False
        and unverified_snapshot["site_geometry_bound_to_target_site"] is False,
    ))

    bad_dataset = bridge_uqq700_site_geometry_recovery(
        changed(recovery, ("source", "dataset"), "CandidateMap"),
        site_id=TARGET_SITE_ID,
        source_snapshot_verified=True,
    )
    checks.append((
        "unexpected dataset fails closed",
        bad_dataset["recovery_source_verified"] is False
        and bad_dataset["site_geometry_bound_to_target_site"] is False,
    ))

    missing_validation = bridge_uqq700_site_geometry_recovery(
        changed(recovery, ("validations", "coordinates exist"), False),
        site_id=TARGET_SITE_ID,
        source_snapshot_verified=True,
    )
    checks.append((
        "failed recovery validation fails closed",
        missing_validation["recovery_validations_verified"] is False
        and missing_validation["site_geometry_bound_to_target_site"] is False,
    ))

    false_all_pass = bridge_uqq700_site_geometry_recovery(
        changed(recovery, ("all_pass",), False),
        site_id=TARGET_SITE_ID,
        source_snapshot_verified=True,
    )
    checks.append((
        "recovery all_pass false fails closed",
        false_all_pass["recovery_validations_verified"] is False
        and false_all_pass["site_geometry_bound_to_target_site"] is False,
    ))

    explicit_crs = bridge_uqq700_site_geometry_recovery(
        positive_recovery(crs={"type": "name", "properties": {"name": "EPSG:5179"}}, crs_status="RECOVERED"),
        site_id=TARGET_SITE_ID,
        source_snapshot_verified=True,
    )
    checks.append((
        "even explicit recovered CRS does not make bridge intersection-ready",
        explicit_crs["crs_verified"] is True
        and explicit_crs["intersection_ready"] is False
        and explicit_crs["positive_spatial_intersection_verified"] is False,
    ))
    checks.append((
        "bridge remains pure and production-unwired",
        verified["production_wiring_applied"] is False
        and verified["runtime_registry_mutated"] is False
        and verified["site_mutated"] is False,
    ))

    all_pass = all(passed for _, passed in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 96)
    print("UQQ700 HYBRID_SPATIAL_NOTICE SITE GEOMETRY RECOVERY BRIDGE REGRESSION")
    print("=" * 96)
    print("Existing MapPlan parcel recovery -> SITE geometry provenance: TEST-ONLY")
    print("CRS guessing/intersection readiness: DISABLED")
    print("UQQ700 designation geometry/Gate 3: DISABLED")
    print("SITE FALSE/promotion/runtime mutation: DISABLED")
    print()

    for label, passed in checks:
        print(f"{label}: {'PASS' if passed else 'FAIL'}")

    print()
    print(f"CLASSIFICATION: {classification}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
