from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


CONDITION_NAME = "지구단위계획"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
UNKNOWN = "UNKNOWN"


def _text(value: Any) -> str:
    return str(value or "").strip()


def verify_district_unit_plan_hybrid_resolver_result(
    resolver_execution: Mapping[str, Any] | None,
    *,
    canonical_pnu: str,
) -> dict[str, Any]:
    """Verify the district-unit-plan resolver result without deciding SITE applicability."""

    execution = dict(resolver_execution or {})
    expected_pnu = _text(canonical_pnu)
    admission = execution.get("resolver_admission")
    admission = dict(admission) if isinstance(admission, Mapping) else {}

    checks = {
        "canonical_pnu_present": bool(expected_pnu),
        "resolver_execution_verified": execution.get("resolver_execution_verified") is True,
        "condition_matches": execution.get("condition_name") == CONDITION_NAME,
        "resolution_type_matches": execution.get("resolution_type") == RESOLUTION_TYPE,
        "resolution_remains_unknown": execution.get("resolution") == UNKNOWN,
        "canonical_pnu_matches": bool(expected_pnu)
        and _text(execution.get("canonical_pnu")) == expected_pnu,
        "verified_admission_present": admission.get("resolver_input_admitted") is True,
        "admission_pnu_matches": bool(expected_pnu)
        and _text(admission.get("canonical_pnu")) == expected_pnu,
        "parcel_applicability_not_claimed": execution.get(
            "parcel_applicability_verified"
        )
        is False,
    }

    verified = all(checks.values())

    return {
        "resolver_result_verified": verified,
        "condition_name": CONDITION_NAME,
        "resolution_type": RESOLUTION_TYPE,
        "resolution": UNKNOWN,
        "canonical_pnu": expected_pnu or None,
        "checks": checks,
        "resolver_execution": deepcopy(execution) if verified else {},
        "parcel_applicability_verified": False,
        "site_decision_eligible": False,
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }
