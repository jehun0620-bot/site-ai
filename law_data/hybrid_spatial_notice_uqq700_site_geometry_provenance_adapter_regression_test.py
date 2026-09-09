from __future__ import annotations

from law_data.hybrid_spatial_notice_uqq700_site_geometry_provenance_adapter import (
    Uqq700SiteGeometryProvenance,
    adapt_uqq700_site_geometry_provenance,
)


PASS_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_SITE_GEOMETRY_PROVENANCE_ADAPTER_PASS"
FAIL_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_SITE_GEOMETRY_PROVENANCE_ADAPTER_REGRESSION"

SITE_ID = "11680-10300-0012-0000"
SITE_PNU = "1168010300100120000"


def positive() -> Uqq700SiteGeometryProvenance:
    return Uqq700SiteGeometryProvenance(
        site_id=SITE_ID,
        site_pnu=SITE_PNU,
        geometry_id=f"mapplan-parcel:{SITE_PNU}",
        geometry_type="Polygon",
        geometry_present=True,
        geometry_pnu=SITE_PNU,
        source_id="stored-mapplan-parcel-snapshot",
        source_snapshot_verified=True,
    )


def replace(e: Uqq700SiteGeometryProvenance, **changes):
    return Uqq700SiteGeometryProvenance(**{**e.__dict__, **changes})


def main() -> int:
    checks: list[tuple[str, bool]] = []

    verified = adapt_uqq700_site_geometry_provenance(positive())
    checks.append(
        (
            "explicit PNU-bound polygon provenance binds SITE geometry",
            verified["site_geometry_bound_to_target_site"] is True
            and verified["site_geometry_id"] == f"mapplan-parcel:{SITE_PNU}",
        )
    )
    checks.append(
        (
            "SITE geometry binding alone cannot manufacture UQQ700 Gate 3",
            verified["official_spatial_source_verified"] is False
            and verified["designation_geometry_bound"] is False
            and verified["positive_spatial_intersection_verified"] is False
            and verified["site_spatial_inclusion_verified"] is False,
        )
    )
    checks.append(
        (
            "SITE geometry binding cannot open runtime or SITE promotion",
            verified["minimum_registration_gate_satisfied"] is False
            and verified["runtime_registration_allowed"] is False
            and verified["site_false_inference_allowed"] is False
            and verified["site_promotion_allowed"] is False
            and verified["legal_absence_inference_allowed"] is False
            and verified["negative_evidence_allowed"] is False,
        )
    )

    cases = [
        ("missing SITE id fails closed", replace(positive(), site_id="")),
        ("missing SITE PNU fails closed", replace(positive(), site_pnu="")),
        ("missing geometry id fails closed", replace(positive(), geometry_id="")),
        ("missing source id fails closed", replace(positive(), source_id="")),
        (
            "unverified source snapshot fails closed",
            replace(positive(), source_snapshot_verified=False),
        ),
        (
            "parcel PNU mismatch fails closed",
            replace(positive(), geometry_pnu="1168010300100130000"),
        ),
        (
            "missing geometry fails closed",
            replace(positive(), geometry_present=False),
        ),
        (
            "non-polygon geometry fails closed",
            replace(positive(), geometry_type="Point"),
        ),
    ]

    for label, evidence in cases:
        result = adapt_uqq700_site_geometry_provenance(evidence)
        checks.append(
            (
                label,
                result["site_geometry_bound_to_target_site"] is False
                and result["site_geometry_id"] == "",
            )
        )

    diagnostic = adapt_uqq700_site_geometry_provenance(
        replace(positive(), geometry_present=False),
        diagnostics={
            "address_match": True,
            "candidate_layer_hit": True,
            "http_200": True,
        },
    )
    checks.append(
        (
            "diagnostic signals cannot manufacture SITE geometry binding",
            diagnostic["site_geometry_bound_to_target_site"] is False
            and diagnostic["site_spatial_inclusion_verified"] is False,
        )
    )
    checks.append(
        (
            "adapter remains pure and production-unwired",
            verified["production_wiring_applied"] is False
            and verified["runtime_registry_mutated"] is False
            and verified["site_mutated"] is False,
        )
    )

    all_pass = all(passed for _, passed in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 96)
    print("UQQ700 HYBRID_SPATIAL_NOTICE SITE GEOMETRY PROVENANCE ADAPTER REGRESSION")
    print("=" * 96)
    print("SITE parcel PNU/Polygon provenance binding: ENABLED")
    print("UQQ700 designation geometry inference: DISABLED")
    print("Gate 3/intersection inference: DISABLED")
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
