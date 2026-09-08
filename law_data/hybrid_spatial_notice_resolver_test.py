from __future__ import annotations

from itertools import product

from law_data.hybrid_spatial_notice_resolver import (
    HybridSpatialNoticeGateState,
    resolve_hybrid_spatial_notice,
)


def assert_common_safety(result: dict) -> None:
    assert result["resolution_type"] == "HYBRID_SPATIAL_NOTICE"
    assert result["resolution"] == "UNKNOWN"
    assert result["negative_evidence_allowed"] is False
    assert result["legal_absence_inference_allowed"] is False
    assert result["site_false_inference_allowed"] is False
    assert result["site_promotion_allowed"] is False
    assert result["diagnostic_discovery"]["dispositive"] is False


def main() -> int:
    cases = 0

    for identity, validity, spatial in product((False, True), repeat=3):
        gate_state = HybridSpatialNoticeGateState(
            official_designation_identity_verified=identity,
            current_validity_verified=validity,
            site_spatial_inclusion_verified=spatial,
        )
        result = resolve_hybrid_spatial_notice(gate_state)
        expected_gate = identity and validity and spatial

        assert_common_safety(result)
        assert result["minimum_registration_gate_satisfied"] is expected_gate
        assert result["runtime_registration_allowed"] is expected_gate
        cases += 1

    # search hit != designation identity verification
    hit_result = resolve_hybrid_spatial_notice(
        HybridSpatialNoticeGateState(),
        search_hit=True,
        http_200=True,
    )
    assert_common_safety(hit_result)
    assert hit_result["positive_gates"]["official_designation_identity_verified"] is False
    assert hit_result["minimum_registration_gate_satisfied"] is False
    assert hit_result["runtime_registration_allowed"] is False

    # no-hit / non-display != legal absence or SITE FALSE
    no_hit_result = resolve_hybrid_spatial_notice(
        HybridSpatialNoticeGateState(),
        search_hit=False,
        http_200=False,
        negative_evidence={
            "search_no_hit": True,
            "site_name_not_present": True,
            "candidate_layer_no_hit": True,
        },
    )
    assert_common_safety(no_hit_result)
    assert no_hit_result["legal_absence_inference_allowed"] is False
    assert no_hit_result["site_false_inference_allowed"] is False
    assert no_hit_result["runtime_registration_allowed"] is False

    # HTTP 200 alone != document identity
    http_result = resolve_hybrid_spatial_notice(
        HybridSpatialNoticeGateState(),
        http_200=True,
    )
    assert http_result["positive_gates"]["official_designation_identity_verified"] is False
    assert http_result["runtime_registration_allowed"] is False

    print("HYBRID_SPATIAL_NOTICE resolver safety contract: PASS")
    print(f"gate matrix cases: {cases}")
    print("search hit != designation: PASS")
    print("no-hit != legal absence: PASS")
    print("HTTP 200 != document identity: PASS")
    print("three positive registration gates required: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
