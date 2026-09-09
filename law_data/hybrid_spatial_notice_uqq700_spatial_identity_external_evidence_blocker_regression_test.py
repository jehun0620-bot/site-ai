from __future__ import annotations

import sys
from pathlib import Path


LAW_DATA_DIR = Path(__file__).resolve().parent
if str(LAW_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(LAW_DATA_DIR))

from hybrid_spatial_notice_uqq700_spatial_evidence_adapter import (  # noqa: E402
    Uqq700SpatialProvenance,
    adapt_uqq700_spatial_evidence,
)


PASS_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_SPATIAL_IDENTITY_EXTERNAL_EVIDENCE_BLOCKED"
)
FAIL_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_SPATIAL_IDENTITY_BLOCKER_REGRESSION"
)

TARGET_SITE_GEOMETRY_ID = "mapplan-parcel:1168010300100120000"


def blocked_spatial_identity() -> Uqq700SpatialProvenance:
    """Synthetic Gate-1/Gate-2 positive state with real spatial identity gap preserved.

    SITE parcel geometry is treated as already bound to the target SITE so this
    regression isolates the remaining designation-side external-evidence blocker.
    No official UQQ700 spatial source, designation geometry, or positive
    intersection is manufactured.
    """

    return Uqq700SpatialProvenance(
        official_designation_identity_verified=True,
        current_validity_verified=True,
        spatial_source_id="",
        official_spatial_source_verified=False,
        designation_geometry_id="",
        designation_geometry_bound_to_verified_designation=False,
        site_geometry_id=TARGET_SITE_GEOMETRY_ID,
        site_geometry_bound_to_target_site=True,
        positive_spatial_intersection_verified=False,
    )


def replace(evidence: Uqq700SpatialProvenance, **changes) -> Uqq700SpatialProvenance:
    return Uqq700SpatialProvenance(**{**evidence.__dict__, **changes})


def main() -> int:
    checks: list[tuple[str, bool]] = []

    blocked = adapt_uqq700_spatial_evidence(
        blocked_spatial_identity(),
        diagnostics={
            "external_evidence_blocker": True,
            "official_uqq700_management_code_verified": False,
            "authoritative_spatial_dataset_layer_verified": False,
            "designation_feature_identity_verified": False,
            "designation_geometry_verified": False,
            "common_crs_transform_provenance_verified": False,
            "mapplan_candidate_code_seen": True,
            "eum_target_name_present": True,
        },
    )

    checks.append(
        (
            "SITE parcel geometry may remain bound while UQQ700 designation spatial identity is blocked",
            blocked["spatial_provenance"]["site_geometry_id"]
            == TARGET_SITE_GEOMETRY_ID
            and blocked["spatial_provenance"]["site_geometry_bound"] is True
            and blocked["spatial_provenance"]["spatial_source_id"] == ""
            and blocked["spatial_provenance"]["designation_geometry_id"] == "",
        )
    )
    checks.append(
        (
            "synthetic Gate 1 and Gate 2 cannot bypass missing authoritative spatial evidence",
            blocked["official_designation_identity_verified"] is True
            and blocked["current_validity_verified"] is True
            and blocked["site_spatial_inclusion_verified"] is False,
        )
    )
    checks.append(
        (
            "external spatial identity blocker cannot open minimum gate or runtime",
            blocked["minimum_registration_gate_satisfied"] is False
            and blocked["runtime_registration_allowed"] is False,
        )
    )
    checks.append(
        (
            "blocked spatial identity cannot infer SITE FALSE, promotion, or legal absence",
            blocked["site_false_inference_allowed"] is False
            and blocked["site_promotion_allowed"] is False
            and blocked["legal_absence_inference_allowed"] is False
            and blocked["negative_evidence_allowed"] is False,
        )
    )
    checks.append(
        (
            "EUM name presence and MapPlan candidate code remain non-dispositive",
            blocked["eum_page_presence_dispositive"] is False
            and blocked["candidate_layer_hit_dispositive"] is False
            and blocked["search_hit_dispositive"] is False
            and blocked["http_success_dispositive"] is False,
        )
    )

    source_id_without_verification = adapt_uqq700_spatial_evidence(
        replace(
            blocked_spatial_identity(),
            spatial_source_id="candidate-mapplan-layer-code",
        )
    )
    checks.append(
        (
            "candidate spatial source id without official verification fails closed",
            source_id_without_verification["spatial_provenance"]["spatial_source_id"]
            == ""
            and source_id_without_verification["site_spatial_inclusion_verified"] is False,
        )
    )

    source_flag_without_id = adapt_uqq700_spatial_evidence(
        replace(
            blocked_spatial_identity(),
            official_spatial_source_verified=True,
        )
    )
    checks.append(
        (
            "official-source boolean without authoritative source id fails closed",
            source_flag_without_id["spatial_provenance"]["official_spatial_source_verified"]
            is False
            and source_flag_without_id["site_spatial_inclusion_verified"] is False,
        )
    )

    designation_id_without_binding = adapt_uqq700_spatial_evidence(
        replace(
            blocked_spatial_identity(),
            spatial_source_id="official-source-1",
            official_spatial_source_verified=True,
            designation_geometry_id="candidate-designation-feature-1",
        )
    )
    checks.append(
        (
            "designation geometry id without verified designation binding fails closed",
            designation_id_without_binding["spatial_provenance"]["designation_geometry_id"]
            == ""
            and designation_id_without_binding["site_spatial_inclusion_verified"] is False,
        )
    )

    designation_binding_without_id = adapt_uqq700_spatial_evidence(
        replace(
            blocked_spatial_identity(),
            spatial_source_id="official-source-1",
            official_spatial_source_verified=True,
            designation_geometry_bound_to_verified_designation=True,
        )
    )
    checks.append(
        (
            "designation binding boolean without designation geometry id fails closed",
            designation_binding_without_id["spatial_provenance"]["designation_geometry_bound"]
            is False
            and designation_binding_without_id["site_spatial_inclusion_verified"] is False,
        )
    )

    no_intersection = adapt_uqq700_spatial_evidence(
        replace(
            blocked_spatial_identity(),
            spatial_source_id="official-source-1",
            official_spatial_source_verified=True,
            designation_geometry_id="verified-designation-geometry-1",
            designation_geometry_bound_to_verified_designation=True,
        )
    )
    checks.append(
        (
            "official source and bound designation geometry still require positive intersection",
            no_intersection["spatial_provenance"]["official_spatial_source_verified"] is True
            and no_intersection["spatial_provenance"]["designation_geometry_bound"] is True
            and no_intersection["spatial_provenance"]["site_geometry_bound"] is True
            and no_intersection["spatial_provenance"]["positive_spatial_intersection_verified"]
            is False
            and no_intersection["site_spatial_inclusion_verified"] is False,
        )
    )

    negative_discovery = adapt_uqq700_spatial_evidence(
        blocked_spatial_identity(),
        diagnostics={
            "search_no_hit": True,
            "candidate_layer_no_hit": True,
            "site_non_display": True,
            "source_family_exhausted": True,
        },
    )
    checks.append(
        (
            "negative discovery cannot convert external evidence blocker into SITE FALSE",
            negative_discovery["site_spatial_inclusion_verified"] is False
            and negative_discovery["negative_evidence_dispositive"] is False
            and negative_discovery["site_false_inference_allowed"] is False
            and negative_discovery["legal_absence_inference_allowed"] is False,
        )
    )

    checks.append(
        (
            "blocker regression remains pure and production-unwired",
            blocked["production_wiring_applied"] is False
            and blocked["runtime_registry_mutated"] is False
            and blocked["site_mutated"] is False,
        )
    )

    all_pass = all(passed for _, passed in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 104)
    print("UQQ700 HYBRID_SPATIAL_NOTICE SPATIAL IDENTITY EXTERNAL EVIDENCE BLOCKER REGRESSION")
    print("=" * 104)
    print("SITE parcel geometry provenance: AVAILABLE / TEST-ONLY")
    print("Authoritative UQQ700 spatial source identity: UNVERIFIED")
    print("UQQ700 designation geometry identity: UNVERIFIED")
    print("Positive spatial intersection: UNVERIFIED")
    print("Negative-evidence / SITE FALSE / legal-absence inference: DISABLED")
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
