from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


CONDITION_NAME = "지구단위계획"
IDENTITY_FIELDS = (
    "ANCMNT_MNG_CD",
    "ANCMNT_YMD",
    "ANCMNT_NO",
    "ANCMNT_INST",
    "TTL",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _identity(mapping: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(mapping, Mapping):
        return {}
    value = mapping.get("announcement_identity")
    return dict(value) if isinstance(value, Mapping) else {}


def _identity_matches(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return all(
        bool(_text(left.get(field)))
        and _text(left.get(field)) == _text(right.get(field))
        for field in IDENTITY_FIELDS
    )


def bind_district_unit_plan_hybrid_gates(
    designation_identity: Mapping[str, Any] | None,
    current_validity: Mapping[str, Any] | None,
    site_spatial_inclusion: Mapping[str, Any] | None,
    *,
    canonical_pnu: str,
) -> dict[str, Any]:
    """Fail-closed admission boundary for the three district-unit-plan HYBRID gates.

    The current contracts can bind designation identity to current-validity identity,
    and spatial inclusion to the requested canonical PNU. The spatial bridge does not
    yet carry announcement identity, so this function deliberately does not claim a
    notice-to-geometry identity binding that upstream evidence cannot prove.

    Successful admission is not SITE truth, promotion, or production/runtime
    registration authority.
    """

    designation = dict(designation_identity or {})
    validity = dict(current_validity or {})
    spatial = dict(site_spatial_inclusion or {})
    expected_pnu = _text(canonical_pnu)

    designation_announcement = _identity(designation)
    validity_announcement = _identity(validity)

    checks = {
        "canonical_pnu_present": bool(expected_pnu),
        "designation_gate_verified": designation.get(
            "official_designation_identity_verified"
        )
        is True,
        "validity_gate_verified": validity.get("current_validity_verified") is True,
        "spatial_gate_verified": spatial.get("site_spatial_inclusion_verified") is True,
        "designation_condition_matches": designation.get("condition_name")
        == CONDITION_NAME,
        "validity_condition_matches": validity.get("condition_name") == CONDITION_NAME,
        "spatial_condition_matches": spatial.get("condition_name") == CONDITION_NAME,
        "designation_validity_identity_matches": _identity_matches(
            designation_announcement,
            validity_announcement,
        ),
        "spatial_canonical_pnu_matches": bool(expected_pnu)
        and _text(spatial.get("canonical_pnu")) == expected_pnu,
        "spatial_source_pnu_matches": bool(expected_pnu)
        and _text(spatial.get("source_pnu")) == expected_pnu,
    }

    admitted = all(checks.values())

    return {
        "hybrid_gate_binding_verified": admitted,
        "condition_name": CONDITION_NAME,
        "canonical_pnu": expected_pnu or None,
        "announcement_identity": (
            deepcopy(designation_announcement) if admitted else {}
        ),
        "checks": checks,
        "binding_scope": {
            "designation_to_current_validity": admitted,
            "spatial_to_canonical_pnu": admitted,
            "designation_to_spatial_notice_identity": False,
        },
        "stage_results": (
            {
                "designation_identity": deepcopy(designation),
                "current_validity": deepcopy(validity),
                "site_spatial_inclusion": deepcopy(spatial),
            }
            if admitted
            else {}
        ),
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }
