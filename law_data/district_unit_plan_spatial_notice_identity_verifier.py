from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


CONDITION_NAME = "지구단위계획"
EXPECTED_DATASET = "LT_C_UPISUQ161"


def _text(value: Any) -> str:
    return str(value or "").strip()


def verify_district_unit_plan_spatial_notice_identity(
    designation_identity: Mapping[str, Any] | None,
    site_spatial_inclusion: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Verify the exact notice-management identity binding for spatial evidence.

    This verifier is fail-closed. It only admits an exact VWorld NTFC_SN ↔
    official ANCMNT_MNG_CD match after both upstream gates are already verified.
    It does not decide current validity, SITE truth, promotion, or registration.
    """

    designation = dict(designation_identity or {})
    spatial = dict(site_spatial_inclusion or {})
    announcement = (
        designation.get("announcement_identity")
        if isinstance(designation.get("announcement_identity"), Mapping)
        else {}
    )
    evidence = (
        spatial.get("evidence")
        if isinstance(spatial.get("evidence"), Mapping)
        else {}
    )
    source = evidence.get("source") if isinstance(evidence.get("source"), Mapping) else {}
    feature_properties = (
        evidence.get("feature_properties")
        if isinstance(evidence.get("feature_properties"), Mapping)
        else {}
    )

    announcement_code = _text(announcement.get("ANCMNT_MNG_CD"))
    spatial_notice_code = _text(feature_properties.get("ntfc_sn"))

    checks = {
        "designation_identity_verified": (
            designation.get("official_designation_identity_verified") is True
        ),
        "spatial_inclusion_verified": spatial.get("site_spatial_inclusion_verified") is True,
        "designation_condition_matches": designation.get("condition_name") == CONDITION_NAME,
        "spatial_condition_matches": spatial.get("condition_name") == CONDITION_NAME,
        "dataset_matches": spatial.get("dataset") == EXPECTED_DATASET
        and source.get("dataset") == EXPECTED_DATASET,
        "canonical_pnu_present": bool(_text(spatial.get("canonical_pnu"))),
        "source_pnu_matches": bool(_text(spatial.get("canonical_pnu")))
        and _text(spatial.get("source_pnu")) == _text(spatial.get("canonical_pnu")),
        "announcement_management_code_present": bool(announcement_code),
        "spatial_notice_code_present": bool(spatial_notice_code),
        "exact_management_code_match": bool(announcement_code)
        and bool(spatial_notice_code)
        and spatial_notice_code == announcement_code,
    }

    verified = all(checks.values())

    return {
        "designation_to_spatial_notice_identity_verified": verified,
        "condition_name": CONDITION_NAME,
        "canonical_pnu": spatial.get("canonical_pnu"),
        "dataset": spatial.get("dataset"),
        "announcement_management_code": announcement_code or None,
        "spatial_notice_code": spatial_notice_code or None,
        "checks": checks,
        "announcement_identity": deepcopy(announcement) if verified else {},
        "spatial_evidence": deepcopy(evidence) if verified else {},
        "current_validity_verified": False,
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }
