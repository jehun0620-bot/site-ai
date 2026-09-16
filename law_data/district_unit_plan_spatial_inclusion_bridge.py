from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


CONDITION_NAME = "지구단위계획"
EXPECTED_DATASET = "LT_C_UPISUQ161"


def bridge_district_unit_plan_spatial_inclusion(
    raw_condition: Mapping[str, Any] | None,
    *,
    canonical_pnu: str,
) -> dict[str, Any]:
    """Admit verified district-unit-plan spatial evidence into the HYBRID gate.

    This bridge is deliberately fail-closed. It does not run a spatial query,
    infer a standard code, decide SITE truth, or grant production/runtime authority.
    """

    raw = dict(raw_condition or {})
    expected_pnu = str(canonical_pnu or "").strip()
    raw_pnu = str(raw.get("pnu") or "").strip()
    source = raw.get("source") if isinstance(raw.get("source"), Mapping) else {}
    evaluation = (
        raw.get("evaluation") if isinstance(raw.get("evaluation"), Mapping) else {}
    )

    checks = {
        "canonical_pnu_present": bool(expected_pnu),
        "condition_name_matches": raw.get("name") == CONDITION_NAME,
        "condition_type_matches": raw.get("type") == "SITE",
        "pnu_matches": bool(expected_pnu) and raw_pnu == expected_pnu,
        "dataset_matches": source.get("dataset") == EXPECTED_DATASET,
        "state_true": raw.get("state") == "TRUE",
        "confidence_high": raw.get("confidence") == "HIGH",
        "geometry_verified": raw.get("geometry_verified") is True,
        "query_success": evaluation.get("query_success") is True,
        "intersects": evaluation.get("intersects") is True,
        "positive_intersection_count": isinstance(
            evaluation.get("intersection_count"), int
        )
        and not isinstance(evaluation.get("intersection_count"), bool)
        and evaluation.get("intersection_count") > 0,
    }

    verified = all(checks.values())

    return {
        "site_spatial_inclusion_verified": verified,
        "condition_name": CONDITION_NAME,
        "canonical_pnu": expected_pnu or None,
        "source_pnu": raw_pnu or None,
        "dataset": source.get("dataset"),
        "checks": checks,
        "evidence": deepcopy(raw) if verified else {},
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }
