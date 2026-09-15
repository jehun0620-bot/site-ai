"""STEP51 historical-only SITE registry mutation executor.

This is the first execution boundary in the historical registry path. It accepts
only a concrete STEP50 commit authorization and commits the already-authorized
registry snapshot as a deep-copied result. It does not call apply_site_registry,
refresh_rule, evaluate rules, or wire the builder/runtime/API.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_site_registry_mutation_commit_authorization import (
    BOUNDARY_NAME as COMMIT_AUTHORIZATION_BOUNDARY_NAME,
    HistoricalSiteEventSiteRegistryMutationCommitAuthorization,
)
from law_data.historical_site_event_site_registry_mutation_transaction import MUTATION_TARGET
from law_data.historical_site_event_provenance_preserving_overlay_contract import (
    HISTORICAL_CONDITION_TYPE,
    HISTORICAL_REGISTRY_SOURCE,
)

BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_SITE_REGISTRY_MUTATION_EXECUTOR"
VALID_STATES = frozenset({"TRUE", "FALSE", "UNKNOWN"})

@dataclass(frozen=True)
class HistoricalSiteEventSiteRegistryMutationExecution:
    boundary: str
    mutation_target: str
    authorization_present: bool
    authorization_boundary_matched: bool
    mutation_target_matched: bool
    mutation_commit_authorized: bool
    historical_condition_name_present: bool
    historical_condition_present: bool
    historical_type_preserved: bool
    state_valid: bool
    registry_source_matched: bool
    original_historical_source_preserved: bool
    authorized_snapshot_present: bool
    authorized_snapshot_aligned: bool
    authorization_contract_aligned: bool
    missing_gates: tuple[str, ...]
    mutation_executed: bool
    site_registry_overlaid: bool
    committed_registry: Mapping[str, Mapping[str, Any]]
    committed_historical_condition_name: str
    committed_historical_condition: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.__dict__,
            "missing_gates": list(self.missing_gates),
            "committed_registry": copy.deepcopy(dict(self.committed_registry)),
            "committed_historical_condition": copy.deepcopy(dict(self.committed_historical_condition)),
            "input_authorization_mutated": False,
            "apply_site_registry_called": False,
            "refresh_rule_called": False,
            "rule_evaluation_pipeline_modified": False,
            "site_analysis_builder_modified": False,
            "rule_engine_input_consumed": False,
            "rule_engine_state_mutated": False,
            "rule_evaluation_executed": False,
            "rule_applicability_recalculated": False,
            "rule_applicability_changed": False,
            "production_wiring_applied": False,
            "runtime_registered": False,
            "runtime_registry_mutated": False,
            "public_api_exposed": False,
        }


def execute_historical_site_event_site_registry_mutation(
    authorization: HistoricalSiteEventSiteRegistryMutationCommitAuthorization | None,
) -> HistoricalSiteEventSiteRegistryMutationExecution:
    authorization_present = isinstance(authorization, HistoricalSiteEventSiteRegistryMutationCommitAuthorization)
    authorization_boundary_matched = bool(authorization_present and authorization.boundary == COMMIT_AUTHORIZATION_BOUNDARY_NAME)
    mutation_target_matched = bool(authorization_present and authorization.mutation_target == MUTATION_TARGET)
    mutation_commit_authorized = bool(authorization_present and authorization.mutation_commit_authorized is True)
    name = str(authorization.authorized_historical_condition_name or "").strip() if authorization_present else ""
    historical_condition_name_present = bool(name)
    condition = copy.deepcopy(dict(authorization.authorized_historical_condition)) if authorization_present else {}
    historical_condition_present = bool(condition)
    historical_type_preserved = str(condition.get("type") or "").strip() == HISTORICAL_CONDITION_TYPE
    state_valid = str(condition.get("state") or "").strip().upper() in VALID_STATES
    registry_source_matched = str(condition.get("source") or "").strip() == HISTORICAL_REGISTRY_SOURCE
    historical_source = condition.get("historical_source")
    runtime_source = condition.get("runtime_source")
    original_historical_source_preserved = bool(str(historical_source or "").strip() and historical_source == runtime_source)
    snapshot = copy.deepcopy(dict(authorization.authorized_registry_snapshot)) if authorization_present else {}
    authorized_snapshot_present = bool(snapshot)
    snapshot_condition = snapshot.get(name) if name else None
    authorized_snapshot_aligned = bool(isinstance(snapshot_condition, Mapping) and dict(snapshot_condition) == condition)
    authorization_contract_aligned = bool(
        authorization_present
        and authorization.transaction_present is True
        and authorization.transaction_boundary_matched is True
        and authorization.mutation_target_matched is True
        and authorization.mutation_transaction_ready is True
        and authorization.no_collision_policy_preserved is True
        and authorization.exactly_one_historical_condition is True
        and authorization.historical_condition_name_present is True
        and authorization.historical_condition_present is True
        and authorization.historical_type_preserved is True
        and authorization.state_valid is True
        and authorization.registry_source_matched is True
        and authorization.original_historical_source_preserved is True
        and authorization.transaction_snapshot_aligned is True
        and authorization.transaction_contract_aligned is True
    )
    gates = (
        ("authorization_present", authorization_present),
        ("authorization_boundary_matched", authorization_boundary_matched),
        ("mutation_target_matched", mutation_target_matched),
        ("mutation_commit_authorized", mutation_commit_authorized),
        ("historical_condition_name_present", historical_condition_name_present),
        ("historical_condition_present", historical_condition_present),
        ("historical_type_preserved", historical_type_preserved),
        ("state_valid", state_valid),
        ("registry_source_matched", registry_source_matched),
        ("original_historical_source_preserved", original_historical_source_preserved),
        ("authorized_snapshot_present", authorized_snapshot_present),
        ("authorized_snapshot_aligned", authorized_snapshot_aligned),
        ("authorization_contract_aligned", authorization_contract_aligned),
    )
    missing_gates = tuple(g for g, passed in gates if not passed)
    executed = not missing_gates
    return HistoricalSiteEventSiteRegistryMutationExecution(
        boundary=BOUNDARY_NAME,
        mutation_target=MUTATION_TARGET,
        authorization_present=authorization_present,
        authorization_boundary_matched=authorization_boundary_matched,
        mutation_target_matched=mutation_target_matched,
        mutation_commit_authorized=mutation_commit_authorized,
        historical_condition_name_present=historical_condition_name_present,
        historical_condition_present=historical_condition_present,
        historical_type_preserved=historical_type_preserved,
        state_valid=state_valid,
        registry_source_matched=registry_source_matched,
        original_historical_source_preserved=original_historical_source_preserved,
        authorized_snapshot_present=authorized_snapshot_present,
        authorized_snapshot_aligned=authorized_snapshot_aligned,
        authorization_contract_aligned=authorization_contract_aligned,
        missing_gates=missing_gates,
        mutation_executed=executed,
        site_registry_overlaid=executed,
        committed_registry=(snapshot if executed else {}),
        committed_historical_condition_name=(name if executed else ""),
        committed_historical_condition=(condition if executed else {}),
    )
