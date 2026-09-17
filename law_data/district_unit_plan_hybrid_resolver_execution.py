from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


CONDITION_NAME = "지구단위계획"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
UNKNOWN = "UNKNOWN"


def _text(value: Any) -> str:
    return str(value or "").strip()


def execute_district_unit_plan_hybrid_resolver(
    resolver_admission: Mapping[str, Any] | None,
    *,
    canonical_pnu: str,
) -> dict[str, Any]:
    """Execute the district-unit-plan HYBRID envelope without authority escalation.

    Execution means the verified admission envelope may proceed to result verification.
    It does not establish parcel applicability, SITE truth, promotion, or registration.
    """

    admission = dict(resolver_admission or {})
    expected_pnu = _text(canonical_pnu)
    binding = admission.get("hybrid_binding")
    binding = dict(binding) if isinstance(binding, Mapping) else {}

    checks = {
        "canonical_pnu_present": bool(expected_pnu),
        "resolver_input_admitted": admission.get("resolver_input_admitted") is True,
        "condition_matches": admission.get("condition_name") == CONDITION_NAME,
        "resolution_type_matches": admission.get("resolution_type") == RESOLUTION_TYPE,
        "canonical_pnu_matches": bool(expected_pnu)
        and _text(admission.get("canonical_pnu")) == expected_pnu,
        "verified_hybrid_binding_present": binding.get("hybrid_gate_binding_verified")
        is True,
        "binding_pnu_matches": bool(expected_pnu)
        and _text(binding.get("canonical_pnu")) == expected_pnu,
    }

    executed = all(checks.values())

    return {
        "resolver_execution_verified": executed,
        "condition_name": CONDITION_NAME,
        "resolution_type": RESOLUTION_TYPE,
        "resolution": UNKNOWN,
        "canonical_pnu": expected_pnu or None,
        "checks": checks,
        "resolver_admission": deepcopy(admission) if executed else {},
        "parcel_applicability_verified": False,
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }
