from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


CONDITION_NAME = "지구단위계획"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"


def _text(value: Any) -> str:
    return str(value or "").strip()


def admit_district_unit_plan_hybrid_resolver_input(
    hybrid_binding: Mapping[str, Any] | None,
    *,
    canonical_pnu: str,
) -> dict[str, Any]:
    """Admit verified district-unit-plan HYBRID evidence without granting runtime authority.

    This boundary is intentionally narrower than the generic HYBRID resolver contract.
    It accepts only a fully verified district-unit-plan binding for the same canonical
    PNU and preserves the project's fail-closed authority boundary.
    """

    binding = dict(hybrid_binding or {})
    expected_pnu = _text(canonical_pnu)
    scope = binding.get("binding_scope")
    scope = dict(scope) if isinstance(scope, Mapping) else {}
    stage_results = binding.get("stage_results")
    stage_results = dict(stage_results) if isinstance(stage_results, Mapping) else {}

    checks = {
        "canonical_pnu_present": bool(expected_pnu),
        "hybrid_binding_verified": binding.get("hybrid_gate_binding_verified") is True,
        "condition_matches": binding.get("condition_name") == CONDITION_NAME,
        "canonical_pnu_matches": bool(expected_pnu)
        and _text(binding.get("canonical_pnu")) == expected_pnu,
        "designation_current_validity_bound": scope.get(
            "designation_to_current_validity"
        )
        is True,
        "spatial_canonical_pnu_bound": scope.get("spatial_to_canonical_pnu") is True,
        "designation_spatial_notice_identity_bound": scope.get(
            "designation_to_spatial_notice_identity"
        )
        is True,
        "stage_results_present": bool(stage_results),
    }

    admitted = all(checks.values())

    return {
        "resolver_input_admitted": admitted,
        "condition_name": CONDITION_NAME,
        "resolution_type": RESOLUTION_TYPE,
        "canonical_pnu": expected_pnu or None,
        "checks": checks,
        "hybrid_binding": deepcopy(binding) if admitted else {},
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }
