from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


CONDITION_NAME = "지구단위계획"
REQUIRED_IDENTITY_FIELDS = (
    "ANCMNT_MNG_CD",
    "ANCMNT_YMD",
    "ANCMNT_NO",
    "ANCMNT_INST",
    "TTL",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def verify_district_unit_plan_designation_identity(
    announcement: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Verify the identity of one official district-unit-plan announcement record.

    The caller supplies an upstream official announcement record. This verifier is
    deliberately fail-closed and does not fetch data, infer current validity,
    decide parcel applicability/SITE truth, or grant production/runtime authority.
    """

    raw = dict(announcement or {})
    title = _text(raw.get("TTL"))
    content = _text(raw.get("CN"))
    searchable_text = f"{title} {content}".strip()

    required_fields_present = {
        field: bool(_text(raw.get(field))) for field in REQUIRED_IDENTITY_FIELDS
    }
    district_unit_plan_named = CONDITION_NAME in searchable_text

    verified = all(required_fields_present.values()) and district_unit_plan_named

    identity = (
        {
            field: deepcopy(raw.get(field))
            for field in (
                "ANCMNT_MNG_CD",
                "ANCMNT_YMD",
                "ANCMNT_NO",
                "ANCMNT_INST",
                "TKCG_INST",
                "TTL",
                "CN",
            )
            if field in raw
        }
        if verified
        else {}
    )

    return {
        "official_designation_identity_verified": verified,
        "condition_name": CONDITION_NAME,
        "announcement_identity": identity,
        "checks": {
            "required_fields_present": required_fields_present,
            "district_unit_plan_named": district_unit_plan_named,
        },
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }
