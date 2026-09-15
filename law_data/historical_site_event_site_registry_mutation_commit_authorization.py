"""STEP50 final non-executing mutation commit authorization.

A STEP49 transaction may become eligible for a future executor only after this
explicit commit gate. This module never mutates the registry or invokes Rule
Engine behavior.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_site_registry_mutation_transaction import (
    BOUNDARY_NAME as TRANSACTION_BOUNDARY_NAME,
    MUTATION_TARGET,
    HistoricalSiteEventSiteRegistryMutationTransaction,
)
from law_data.historical_site_event_provenance_preserving_overlay_contract import (
    HISTORICAL_CONDITION_TYPE,
    HISTORICAL_REGISTRY_SOURCE,
)

BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_SITE_REGISTRY_MUTATION_COMMIT_AUTHORIZATION"
VALID_STATES = frozenset({"TRUE", "FALSE", "UNKNOWN"})

@dataclass(frozen=True)
class HistoricalSiteEventSiteRegistryMutationCommitAuthorization:
    boundary: str
    mutation_target: str
    transaction_present: bool
    transaction_boundary_matched: bool
    mutation_target_matched: bool
    mutation_transaction_ready: bool
    no_collision_policy_preserved: bool
    exactly_one_historical_condition: bool
    historical_condition_name_present: bool
    historical_condition_present: bool
    historical_type_preserved: bool
    state_valid: bool
    registry_source_matched: bool
    original_historical_source_preserved: bool
    transaction_snapshot_aligned: bool
    transaction_contract_aligned: bool
    missing_gates: tuple[str, ...]
    mutation_commit_authorized: bool
    authorized_registry_snapshot: Mapping[str, Mapping[str, Any]]
    authorized_historical_condition_name: str
    authorized_historical_condition: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.__dict__,
            "missing_gates": list(self.missing_gates),
            "authorized_registry_snapshot": copy.deepcopy(dict(self.authorized_registry_snapshot)),
            "authorized_historical_condition": copy.deepcopy(dict(self.authorized_historical_condition)),
            "mutation_executed": False,
            "original_registry_mutated": False,
            "site_registry_overlaid": False,
            "apply_site_registry_called": False,
            "refresh_rule_called": False,
            "rule_engine_state_mutated": False,
            "rule_evaluation_executed": False,
            "rule_applicability_recalculated": False,
            "rule_applicability_changed": False,
            "site_analysis_builder_modified": False,
            "production_wiring_applied": False,
            "runtime_registered": False,
            "runtime_registry_mutated": False,
            "public_api_exposed": False,
        }


def authorize_historical_site_event_site_registry_mutation_commit(
    transaction: HistoricalSiteEventSiteRegistryMutationTransaction | None,
) -> HistoricalSiteEventSiteRegistryMutationCommitAuthorization:
    transaction_present = isinstance(transaction, HistoricalSiteEventSiteRegistryMutationTransaction)
    transaction_boundary_matched = bool(transaction_present and transaction.boundary == TRANSACTION_BOUNDARY_NAME)
    mutation_target_matched = bool(transaction_present and transaction.mutation_target == MUTATION_TARGET)
    mutation_transaction_ready = bool(transaction_present and transaction.mutation_transaction_ready is True)
    no_collision_policy_preserved = bool(
        transaction_present
        and transaction.replacement_policy_matched is True
        and transaction.replacement_policy_authorized is True
        and transaction.no_collision_policy_satisfied is True
    )
    exactly_one_historical_condition = bool(transaction_present and transaction.historical_condition_count == 1)
    name = str(transaction.historical_condition_name or "").strip() if transaction_present else ""
    historical_condition_name_present = bool(name)
    condition = copy.deepcopy(dict(transaction.transaction_historical_condition)) if transaction_present else {}
    historical_condition_present = bool(condition)
    historical_type_preserved = str(condition.get("type") or "").strip() == HISTORICAL_CONDITION_TYPE
    state_valid = str(condition.get("state") or "").strip().upper() in VALID_STATES
    registry_source_matched = str(condition.get("source") or "").strip() == HISTORICAL_REGISTRY_SOURCE
    historical_source = condition.get("historical_source")
    runtime_source = condition.get("runtime_source")
    original_historical_source_preserved = bool(str(historical_source or "").strip() and historical_source == runtime_source)
    snapshot = copy.deepcopy(dict(transaction.transaction_registry_snapshot)) if transaction_present else {}
    snapshot_condition = snapshot.get(name) if name else None
    transaction_snapshot_aligned = bool(
        isinstance(snapshot_condition, Mapping) and dict(snapshot_condition) == condition
    )
    transaction_contract_aligned = bool(
        transaction_present
        and transaction.authorization_present is True
        and transaction.authorization_boundary_matched is True
        and transaction.authorized_preview_registry_present is True
        and transaction.historical_condition_present is True
        and transaction.historical_type_preserved is True
        and transaction.state_valid is True
        and transaction.registry_source_matched is True
        and transaction.original_historical_source_preserved is True
        and transaction.authorization_contract_aligned is True
    )
    gates = (
        ("transaction_present", transaction_present),
        ("transaction_boundary_matched", transaction_boundary_matched),
        ("mutation_target_matched", mutation_target_matched),
        ("mutation_transaction_ready", mutation_transaction_ready),
        ("no_collision_policy_preserved", no_collision_policy_preserved),
        ("exactly_one_historical_condition", exactly_one_historical_condition),
        ("historical_condition_name_present", historical_condition_name_present),
        ("historical_condition_present", historical_condition_present),
        ("historical_type_preserved", historical_type_preserved),
        ("state_valid", state_valid),
        ("registry_source_matched", registry_source_matched),
        ("original_historical_source_preserved", original_historical_source_preserved),
        ("transaction_snapshot_aligned", transaction_snapshot_aligned),
        ("transaction_contract_aligned", transaction_contract_aligned),
    )
    missing_gates = tuple(g for g, passed in gates if not passed)
    authorized = not missing_gates
    return HistoricalSiteEventSiteRegistryMutationCommitAuthorization(
        boundary=BOUNDARY_NAME,
        mutation_target=MUTATION_TARGET,
        transaction_present=transaction_present,
        transaction_boundary_matched=transaction_boundary_matched,
        mutation_target_matched=mutation_target_matched,
        mutation_transaction_ready=mutation_transaction_ready,
        no_collision_policy_preserved=no_collision_policy_preserved,
        exactly_one_historical_condition=exactly_one_historical_condition,
        historical_condition_name_present=historical_condition_name_present,
        historical_condition_present=historical_condition_present,
        historical_type_preserved=historical_type_preserved,
        state_valid=state_valid,
        registry_source_matched=registry_source_matched,
        original_historical_source_preserved=original_historical_source_preserved,
        transaction_snapshot_aligned=transaction_snapshot_aligned,
        transaction_contract_aligned=transaction_contract_aligned,
        missing_gates=missing_gates,
        mutation_commit_authorized=authorized,
        authorized_registry_snapshot=(snapshot if authorized else {}),
        authorized_historical_condition_name=(name if authorized else ""),
        authorized_historical_condition=(condition if authorized else {}),
    )
