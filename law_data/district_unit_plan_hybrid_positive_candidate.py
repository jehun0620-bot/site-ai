from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


CONDITION_NAME = "지구단위계획"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_RESOLUTION = "UNKNOWN"
POSITIVE_CANDIDATE = "POSITIVE_CANDIDATE"


def _text(value: Any) -> str:
    return str(value or "").strip()


def evaluate_district_unit_plan_hybrid_positive_candidate(
    verified_resolver_result: Mapping[str, Any] | None,
    *,
    canonical_pnu: str,
) -> dict[str, Any]:
    """Recognize a provenance-bound district-unit-plan positive candidate.

    This is a non-authoritative evidence state only. It does not rewrite the verified
    HYBRID resolver resolution, claim parcel applicability, satisfy STEP114, decide
    SITE truth, or authorize promotion/production/runtime registration.
    """

    result = dict(verified_resolver_result or {})
    expected_pnu = _text(canonical_pnu)

    execution = result.get("resolver_execution")
    execution = dict(execution) if isinstance(execution, Mapping) else {}
    admission = execution.get("resolver_admission")
    admission = dict(admission) if isinstance(admission, Mapping) else {}
    binding = admission.get("hybrid_binding")
    binding = dict(binding) if isinstance(binding, Mapping) else {}
    scope = binding.get("binding_scope")
    scope = dict(scope) if isinstance(scope, Mapping) else {}

    checks = {
        "canonical_pnu_present": bool(expected_pnu),
        "resolver_result_verified": result.get("resolver_result_verified") is True,
        "condition_matches": result.get("condition_name") == CONDITION_NAME,
        "resolution_type_matches": result.get("resolution_type") == RESOLUTION_TYPE,
        "verified_resolution_remains_unknown": result.get("resolution") == SOURCE_RESOLUTION,
        "result_pnu_matches": bool(expected_pnu)
        and _text(result.get("canonical_pnu")) == expected_pnu,
        "execution_verified": execution.get("resolver_execution_verified") is True,
        "execution_pnu_matches": bool(expected_pnu)
        and _text(execution.get("canonical_pnu")) == expected_pnu,
        "admission_verified": admission.get("resolver_input_admitted") is True,
        "admission_pnu_matches": bool(expected_pnu)
        and _text(admission.get("canonical_pnu")) == expected_pnu,
        "hybrid_binding_verified": binding.get("hybrid_gate_binding_verified") is True,
        "binding_pnu_matches": bool(expected_pnu)
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
        "parcel_applicability_not_claimed": result.get(
            "parcel_applicability_verified"
        )
        is False,
        "step114_not_claimed": result.get("site_decision_eligible") is False,
    }

    candidate_verified = all(checks.values())

    return {
        "positive_candidate_verified": candidate_verified,
        "candidate_state": POSITIVE_CANDIDATE if candidate_verified else None,
        "condition_name": CONDITION_NAME,
        "resolution_type": RESOLUTION_TYPE,
        "source_resolution": SOURCE_RESOLUTION,
        "canonical_pnu": expected_pnu or None,
        "checks": checks,
        "verified_resolver_result": deepcopy(result) if candidate_verified else {},
        "parcel_applicability_verified": False,
        "site_decision_eligible": False,
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }
