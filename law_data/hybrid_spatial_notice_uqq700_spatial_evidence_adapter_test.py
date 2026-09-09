from __future__ import annotations

from hybrid_spatial_notice_uqq700_spatial_evidence_adapter import (
    Uqq700SpatialProvenance,
    adapt_uqq700_spatial_evidence,
)


PASS_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_SPATIAL_EVIDENCE_ADAPTER_PASS"
FAIL_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_SPATIAL_EVIDENCE_ADAPTER_REGRESSION"


def positive() -> Uqq700SpatialProvenance:
    return Uqq700SpatialProvenance(
        official_designation_identity_verified=True,
        current_validity_verified=True,
        spatial_source_id="official-spatial-source-1",
        official_spatial_source_verified=True,
        designation_geometry_id="designation-geometry-1",
        designation_geometry_bound_to_verified_designation=True,
        site_geometry_id="site-11680-10300-0012-0000",
        site_geometry_bound_to_target_site=True,
        positive_spatial_intersection_verified=True,
    )


def replace(e: Uqq700SpatialProvenance, **changes):
    return Uqq700SpatialProvenance(**{**e.__dict__, **changes})


def main() -> int:
    checks: list[tuple[str, bool]] = []

    verified = adapt_uqq700_spatial_evidence(positive())
    checks.append(
        (
            "complete positive spatial provenance verifies Gate 3",
            verified["site_spatial_inclusion_verified"] is True,
        )
    )
    checks.append(
        (
            "verified Gate 3 preserves official source and geometry identifiers",
            verified["spatial_provenance"]["spatial_source_id"] == "official-spatial-source-1"
            and verified["spatial_provenance"]["designation_geometry_id"] == "designation-geometry-1"
            and verified["spatial_provenance"]["site_geometry_id"] == "site-11680-10300-0012-0000",
        )
    )
    checks.append(
        (
            "Gate 3 verifier alone does not open runtime or SITE promotion",
            verified["minimum_registration_gate_satisfied"] is False
            and verified["runtime_registration_allowed"] is False
            and verified["site_false_inference_allowed"] is False
            and verified["site_promotion_allowed"] is False
            and verified["legal_absence_inference_allowed"] is False
            and verified["negative_evidence_allowed"] is False,
        )
    )

    diagnostics_only = adapt_uqq700_spatial_evidence(
        replace(
            positive(),
            official_spatial_source_verified=False,
            designation_geometry_bound_to_verified_designation=False,
            site_geometry_bound_to_target_site=False,
            positive_spatial_intersection_verified=False,
        ),
        diagnostics={
            "address_name_display": True,
            "search_hit": True,
            "candidate_layer_hit": True,
            "eum_page_presence": True,
            "http_200": True,
            "bbox_proximity": True,
            "centroid_proximity": True,
            "same_district_name": True,
        },
    )
    checks.append(
        (
            "diagnostic signals cannot manufacture Gate 3",
            diagnostics_only["site_spatial_inclusion_verified"] is False
            and diagnostics_only["address_name_display_dispositive"] is False
            and diagnostics_only["search_hit_dispositive"] is False
            and diagnostics_only["candidate_layer_hit_dispositive"] is False
            and diagnostics_only["eum_page_presence_dispositive"] is False
            and diagnostics_only["http_success_dispositive"] is False
            and diagnostics_only["bbox_proximity_dispositive"] is False
            and diagnostics_only["centroid_proximity_dispositive"] is False
            and diagnostics_only["same_district_name_dispositive"] is False,
        )
    )

    cases = [
        (
            "unverified Gate 1 fails closed",
            replace(positive(), official_designation_identity_verified=False),
        ),
        (
            "unverified Gate 2 fails closed",
            replace(positive(), current_validity_verified=False),
        ),
        (
            "missing official spatial source verification fails closed",
            replace(positive(), official_spatial_source_verified=False),
        ),
        (
            "missing spatial source id fails closed",
            replace(positive(), spatial_source_id=""),
        ),
        (
            "unbound designation geometry fails closed",
            replace(positive(), designation_geometry_bound_to_verified_designation=False),
        ),
        (
            "missing designation geometry id fails closed",
            replace(positive(), designation_geometry_id=""),
        ),
        (
            "unbound site geometry fails closed",
            replace(positive(), site_geometry_bound_to_target_site=False),
        ),
        (
            "missing site geometry id fails closed",
            replace(positive(), site_geometry_id=""),
        ),
        (
            "no positive spatial intersection fails closed",
            replace(positive(), positive_spatial_intersection_verified=False),
        ),
    ]
    for label, evidence in cases:
        result = adapt_uqq700_spatial_evidence(evidence)
        checks.append((label, result["site_spatial_inclusion_verified"] is False))

    negative = adapt_uqq700_spatial_evidence(
        replace(positive(), positive_spatial_intersection_verified=False),
        diagnostics={"candidate_layer_no_hit": True, "site_non_display": True},
    )
    checks.append(
        (
            "negative evidence cannot establish SITE FALSE or Gate 3",
            negative["site_spatial_inclusion_verified"] is False
            and negative["negative_evidence_dispositive"] is False
            and negative["site_false_inference_allowed"] is False
            and negative["legal_absence_inference_allowed"] is False,
        )
    )
    checks.append(
        (
            "adapter is pure and production-unwired",
            verified["production_wiring_applied"] is False
            and verified["runtime_registry_mutated"] is False
            and verified["site_mutated"] is False,
        )
    )

    all_pass = all(passed for _, passed in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 96)
    print("UQQ700 HYBRID_SPATIAL_NOTICE SPATIAL EVIDENCE ADAPTER TEST")
    print("=" * 96)
    print("Address/search/EUM/proximity inference: DISABLED")
    print("Negative-evidence SITE FALSE inference: DISABLED")
    print("Gate 3 requires explicit positive geometry intersection: ENABLED")
    print("Production/runtime mutation: DISABLED")
    print()

    for label, passed in checks:
        print(f"{label}: {'PASS' if passed else 'FAIL'}")

    print()
    print(f"CLASSIFICATION: {classification}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
