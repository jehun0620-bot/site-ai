"""Bridge district-unit-plan promotion execution into a registry candidate.

Easy model: this is a plug adapter. It validates the isolated executor output and
translates it into a small registry-shaped candidate for a later collision/merge
boundary. It does not merge registries, call the Rule Engine, modify the builder,
or register runtime state.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from .district_unit_plan_site_truth_promotion_executor import (
    BOUNDARY_NAME as EXECUTOR_BOUNDARY_NAME,
    EXECUTED,
    REGISTRY_SOURCE,
    DistrictUnitPlanSiteTruthPromotionExecution,
)

BOUNDARY_NAME = "DISTRICT_UNIT_PLAN_SITE_TRUTH_PROMOTION_RULE_INPUT_BRIDGE"
READY = "READY"
REJECTED = "REJECTED"
CONDITION_NAME = "지구단위계획"


@dataclass(frozen=True)
class DistrictUnitPlanSiteTruthPromotionRuleInputBridge:
    boundary: str
    status: str
    execution_present: bool
    execution_boundary_matched: bool
    execution_succeeded: bool
    pnu_valid: bool
    condition_matched: bool
    state_true: bool
    promoted_condition_aligned: bool
    provenance_preserved: bool
    missing_gates: tuple[str, ...]
    bridge_ready: bool
    canonical_pnu: str
    registry_candidate: Mapping[str, Mapping[str, Any]]
    site_registry_mutated: bool = False
    registry_merged: bool = False
    collision_policy_called: bool = False
    rule_engine_called: bool = False
    builder_modified: bool = False
    runtime_registered: bool = False
    public_api_exposed: bool = False

    @property
    def ready(self) -> bool:
        return (
            self.status == READY
            and self.boundary == BOUNDARY_NAME
            and self.execution_present
            and self.execution_boundary_matched
            and self.execution_succeeded
            and self.pnu_valid
            and self.condition_matched
            and self.state_true
            and self.promoted_condition_aligned
            and self.provenance_preserved
            and not self.missing_gates
            and self.bridge_ready
            and bool(self.canonical_pnu)
            and bool(self.registry_candidate)
            and self.site_registry_mutated is False
            and self.registry_merged is False
            and self.collision_policy_called is False
            and self.rule_engine_called is False
            and self.builder_modified is False
            and self.runtime_registered is False
            and self.public_api_exposed is False
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.__dict__,
            "missing_gates": list(self.missing_gates),
            "registry_candidate": copy.deepcopy(dict(self.registry_candidate)),
            "ready": self.ready,
        }


def bridge_district_unit_plan_site_truth_promotion_rule_input(
    execution: DistrictUnitPlanSiteTruthPromotionExecution | None,
) -> DistrictUnitPlanSiteTruthPromotionRuleInputBridge:
    """Validate executor provenance and prepare one non-merged registry candidate."""

    present = isinstance(execution, DistrictUnitPlanSiteTruthPromotionExecution)
    boundary_matched = bool(present and execution.boundary == EXECUTOR_BOUNDARY_NAME)
    succeeded = bool(present and execution.status == EXECUTED and execution.executed)
    pnu = str(execution.bound_pnu or "").strip() if present else ""
    condition = str(execution.bound_condition or "").strip() if present else ""
    state = str(execution.bound_state or "").strip().upper() if present else ""
    pnu_valid = len(pnu) == 19 and pnu.isdigit()
    condition_matched = condition == CONDITION_NAME
    state_true = state == "TRUE"

    promoted = (
        execution.promoted_condition
        if present and isinstance(execution.promoted_condition, Mapping)
        else {}
    )
    promoted_condition_aligned = bool(
        promoted
        and str(promoted.get("type") or "").strip().upper() == "SITE"
        and promoted.get("pnu") == pnu
        and str(promoted.get("state") or "").strip().upper() == "TRUE"
        and str(promoted.get("confidence") or "").strip().upper() == "HIGH"
        and promoted.get("historical") is False
        and promoted.get("hybrid") is True
    )
    provenance_preserved = bool(
        promoted
        and promoted.get("source") == REGISTRY_SOURCE
        and promoted.get("provenance") == "HYBRID_SPATIAL_NOTICE_VERIFIED"
        and promoted.get("promotion_executor_boundary") == EXECUTOR_BOUNDARY_NAME
    )

    gates = (
        ("execution_present", present),
        ("execution_boundary_matched", boundary_matched),
        ("execution_succeeded", succeeded),
        ("pnu_valid", pnu_valid),
        ("condition_matched", condition_matched),
        ("state_true", state_true),
        ("promoted_condition_aligned", promoted_condition_aligned),
        ("provenance_preserved", provenance_preserved),
    )
    missing = tuple(name for name, passed in gates if not passed)
    ready = not missing

    registry_candidate: Mapping[str, Mapping[str, Any]] = {}
    if ready:
        registry_candidate = {
            CONDITION_NAME: {
                "state": "TRUE",
                "confidence": "HIGH",
                "source": REGISTRY_SOURCE,
                "pnu": pnu,
                "provenance": "HYBRID_SPATIAL_NOTICE_VERIFIED",
            }
        }

    return DistrictUnitPlanSiteTruthPromotionRuleInputBridge(
        boundary=BOUNDARY_NAME,
        status=READY if ready else REJECTED,
        execution_present=present,
        execution_boundary_matched=boundary_matched,
        execution_succeeded=succeeded,
        pnu_valid=pnu_valid,
        condition_matched=condition_matched,
        state_true=state_true,
        promoted_condition_aligned=promoted_condition_aligned,
        provenance_preserved=provenance_preserved,
        missing_gates=missing,
        bridge_ready=ready,
        canonical_pnu=pnu if ready else "",
        registry_candidate=registry_candidate,
    )
