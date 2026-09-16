"""Bridge an isolated promotion execution into the existing historical rule-input lane.

Easy model: this is a plug adapter, not a second truth path. It converts one
validated promotion result into the already-established {channel, provenance,
repairs} shape understood by the historical registry adapter. It does not call
the adapter, merge registries, run the Rule Engine, or modify the builder.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
from law_data.historical_site_event_site_truth_promotion_executor import (
    BOUNDARY_NAME as EXECUTOR_BOUNDARY_NAME,
    EXECUTED,
    HistoricalSiteEventSiteTruthPromotionExecution,
)

BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_SITE_TRUTH_PROMOTION_RULE_INPUT_BRIDGE"
READY = "READY"
REJECTED = "REJECTED"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class HistoricalSiteEventSiteTruthPromotionRuleInputBridge:
    boundary: str
    status: str
    execution_present: bool
    execution_boundary_matched: bool
    execution_succeeded: bool
    pnu_valid: bool
    condition_present: bool
    state_valid: bool
    promoted_condition_aligned: bool
    provenance_preserved: bool
    missing_gates: tuple[str, ...]
    bridge_ready: bool
    historical_rule_input: Mapping[str, Any]
    site_registry_mutated: bool = False
    registry_adapter_called: bool = False
    collision_policy_called: bool = False
    rule_engine_called: bool = False
    builder_modified: bool = False
    runtime_registered: bool = False
    public_api_exposed: bool = False

    @property
    def ready(self) -> bool:
        return bool(
            self.status == READY
            and self.bridge_ready
            and self.execution_succeeded
            and self.pnu_valid
            and self.condition_present
            and self.state_valid
            and self.promoted_condition_aligned
            and self.provenance_preserved
            and self.historical_rule_input
            and not self.missing_gates
            and not self.site_registry_mutated
            and not self.registry_adapter_called
            and not self.collision_policy_called
            and not self.rule_engine_called
            and not self.builder_modified
            and not self.runtime_registered
            and not self.public_api_exposed
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.__dict__,
            "missing_gates": list(self.missing_gates),
            "historical_rule_input": copy.deepcopy(dict(self.historical_rule_input)),
            "ready": self.ready,
        }


def bridge_historical_site_event_site_truth_promotion_rule_input(
    execution: HistoricalSiteEventSiteTruthPromotionExecution | None,
) -> HistoricalSiteEventSiteTruthPromotionRuleInputBridge:
    present = isinstance(execution, HistoricalSiteEventSiteTruthPromotionExecution)
    boundary_matched = bool(present and execution.boundary == EXECUTOR_BOUNDARY_NAME)
    succeeded = bool(present and execution.status == EXECUTED and execution.executed)
    pnu = str(execution.bound_pnu or "").strip() if present else ""
    condition = str(execution.bound_condition or "").strip() if present else ""
    state = str(execution.bound_state or "").strip().upper() if present else ""
    pnu_valid = len(pnu) == 19 and pnu.isdigit()
    condition_present = bool(condition)
    state_valid = state in {"TRUE", "FALSE"}

    promoted = execution.promoted_condition if present and isinstance(execution.promoted_condition, Mapping) else {}
    promoted_condition_aligned = bool(
        promoted
        and promoted.get("pnu") == pnu
        and str(promoted.get("state") or "").strip().upper() == state
    )
    provenance_preserved = bool(promoted and promoted.get("source") == PROVENANCE)

    gates = (
        ("execution_present", present),
        ("execution_boundary_matched", boundary_matched),
        ("execution_succeeded", succeeded),
        ("pnu_valid", pnu_valid),
        ("condition_present", condition_present),
        ("state_valid", state_valid),
        ("promoted_condition_aligned", promoted_condition_aligned),
        ("provenance_preserved", provenance_preserved),
    )
    missing = tuple(name for name, passed in gates if not passed)
    upstream_unknown = bool(present and execution.status == UNKNOWN)
    status = UNKNOWN if upstream_unknown else (REJECTED if missing else READY)
    ready = status == READY

    historical_rule_input: Mapping[str, Any] = {}
    if ready:
        historical_rule_input = {
            "channel": CHANNEL,
            "provenance": PROVENANCE,
            "repairs": [
                {
                    "condition": condition,
                    "after": state,
                    "new_confidence": str(promoted.get("confidence") or "HIGH").strip().upper(),
                    "new_source": PROVENANCE,
                    "pnu": pnu,
                }
            ],
        }

    return HistoricalSiteEventSiteTruthPromotionRuleInputBridge(
        boundary=BOUNDARY_NAME,
        status=status,
        execution_present=present,
        execution_boundary_matched=boundary_matched,
        execution_succeeded=succeeded,
        pnu_valid=pnu_valid,
        condition_present=condition_present,
        state_valid=state_valid,
        promoted_condition_aligned=promoted_condition_aligned,
        provenance_preserved=provenance_preserved,
        missing_gates=missing,
        bridge_ready=ready,
        historical_rule_input=historical_rule_input,
    )
