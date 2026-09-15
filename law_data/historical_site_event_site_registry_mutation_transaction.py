"""STEP49 non-executing SITE registry mutation transaction for HISTORICAL_SITE_EVENT.

This boundary binds a concrete STEP48 no-collision policy authorization to an
exact future mutation target. It prepares a transaction snapshot only. It does
not mutate a registry, call apply_site_registry/refresh_rule, or evaluate rules.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_site_registry_replacement_policy_authorization import (
    BOUNDARY_NAME as POLICY_AUTHORIZATION_BOUNDARY_NAME,
    POLICY as REQUIRED_POLICY,
    HistoricalSiteEventSiteRegistryReplacementPolicyAuthorization,
)
from law_data.historical_site_event_provenance_preserving_overlay_contract import (
    HISTORICAL_CONDITION_TYPE,
    HISTORICAL_REGISTRY_SOURCE,
)


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_SITE_REGISTRY_MUTATION_TRANSACTION"
MUTATION_TARGET = "RULE_ENGINE_SITE_REGISTRY_HISTORICAL_OVERLAY"
VALID_STATES = frozenset({"TRUE", "FALSE", "UNKNOWN"})


@dataclass(frozen=True)
class HistoricalSiteEventSiteRegistryMutationTransaction:
    boundary: str
    mutation_target: str
    authorization_present: bool
    authorization_boundary_matched: bool
    replacement_policy_matched: bool
    replacement_policy_authorized: bool
    no_collision_policy_satisfied: bool
    authorized_preview_registry_present: bool
    historical_condition_count: int
    historical_condition_name: str
    historical_condition_present: bool
    historical_type_preserved: bool
    state_valid: bool
    registry_source_matched: bool
    original_historical_source_preserved: bool
    authorization_contract_aligned: bool
    missing_gates: tuple[str, ...]
    mutation_transaction_ready: bool
    transaction_registry_snapshot: Mapping[str, Mapping[str, Any]]
    transaction_historical_condition: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "mutation_target": self.mutation_target,
            "authorization_present": self.authorization_present,
            "authorization_boundary_matched": self.authorization_boundary_matched,
            "replacement_policy_matched": self.replacement_policy_matched,
            "replacement_policy_authorized": self.replacement_policy_authorized,
            "no_collision_policy_satisfied": self.no_collision_policy_satisfied,
            "authorized_preview_registry_present": self.authorized_preview_registry_present,
            "historical_condition_count": self.historical_condition_count,
            "historical_condition_name": self.historical_condition_name,
            "historical_condition_present": self.historical_condition_present,
            "historical_type_preserved": self.historical_type_preserved,
            "state_valid": self.state_valid,
            "registry_source_matched": self.registry_source_matched,
            "original_historical_source_preserved": self.original_historical_source_preserved,
            "authorization_contract_aligned": self.authorization_contract_aligned,
            "missing_gates": list(self.missing_gates),
            "mutation_transaction_ready": self.mutation_transaction_ready,
            "transaction_registry_snapshot": copy.deepcopy(dict(self.transaction_registry_snapshot)),
            "transaction_historical_condition": copy.deepcopy(dict(self.transaction_historical_condition)),
            "mutation_executed": False,
            "original_registry_mutated": False,
            "overlay_application_executed": False,
            "site_registry_overlaid": False,
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


def prepare_historical_site_event_site_registry_mutation_transaction(
    authorization: HistoricalSiteEventSiteRegistryReplacementPolicyAuthorization | None,
) -> HistoricalSiteEventSiteRegistryMutationTransaction:
    """Bind a STEP48 authorization to a future mutation transaction, without execution."""

    authorization_present = isinstance(
        authorization,
        HistoricalSiteEventSiteRegistryReplacementPolicyAuthorization,
    )
    authorization_boundary_matched = bool(
        authorization_present and authorization.boundary == POLICY_AUTHORIZATION_BOUNDARY_NAME
    )
    replacement_policy_matched = bool(
        authorization_present and authorization.policy == REQUIRED_POLICY
    )
    replacement_policy_authorized = bool(
        authorization_present and authorization.replacement_policy_authorized is True
    )
    no_collision_policy_satisfied = bool(
        authorization_present
        and authorization.no_collision_policy_satisfied is True
        and authorization.condition_name_collision is False
    )
    registry_snapshot = (
        copy.deepcopy(dict(authorization.authorized_preview_registry))
        if authorization_present
        else {}
    )
    authorized_preview_registry_present = bool(registry_snapshot)

    historical_entries = [
        (str(name or "").strip(), copy.deepcopy(dict(condition)))
        for name, condition in registry_snapshot.items()
        if isinstance(condition, Mapping)
        and str(condition.get("type") or "").strip() == HISTORICAL_CONDITION_TYPE
        and str(condition.get("source") or "").strip() == HISTORICAL_REGISTRY_SOURCE
    ]
    historical_condition_count = len(historical_entries)
    historical_condition_name = historical_entries[0][0] if historical_condition_count == 1 else ""
    historical_condition = historical_entries[0][1] if historical_condition_count == 1 else {}
    historical_condition_present = bool(historical_condition_name and historical_condition)
    historical_type_preserved = (
        str(historical_condition.get("type") or "").strip() == HISTORICAL_CONDITION_TYPE
    )
    state_valid = str(historical_condition.get("state") or "").strip().upper() in VALID_STATES
    registry_source_matched = (
        str(historical_condition.get("source") or "").strip() == HISTORICAL_REGISTRY_SOURCE
    )
    historical_source = historical_condition.get("historical_source")
    runtime_source = historical_condition.get("runtime_source")
    original_historical_source_preserved = bool(
        str(historical_source or "").strip() and historical_source == runtime_source
    )
    authorization_contract_aligned = bool(
        authorization_present
        and authorization.preview_present is True
        and authorization.preview_boundary_matched is True
        and authorization.preview_ready is True
        and authorization.no_collision_policy_satisfied is True
        and authorization.condition_name_collision is False
        and authorization.preview_registry_present is True
        and authorization.historical_condition_present is True
        and authorization.historical_type_preserved is True
        and authorization.state_valid is True
        and authorization.registry_source_matched is True
        and authorization.original_historical_source_preserved is True
        and authorization.preview_contract_aligned is True
    )

    gates = (
        ("authorization_present", authorization_present),
        ("authorization_boundary_matched", authorization_boundary_matched),
        ("replacement_policy_matched", replacement_policy_matched),
        ("replacement_policy_authorized", replacement_policy_authorized),
        ("no_collision_policy_satisfied", no_collision_policy_satisfied),
        ("authorized_preview_registry_present", authorized_preview_registry_present),
        ("exactly_one_historical_condition", historical_condition_count == 1),
        ("historical_condition_present", historical_condition_present),
        ("historical_type_preserved", historical_type_preserved),
        ("state_valid", state_valid),
        ("registry_source_matched", registry_source_matched),
        ("original_historical_source_preserved", original_historical_source_preserved),
        ("authorization_contract_aligned", authorization_contract_aligned),
    )
    missing_gates = tuple(gate for gate, passed in gates if not passed)
    mutation_transaction_ready = not missing_gates

    return HistoricalSiteEventSiteRegistryMutationTransaction(
        boundary=BOUNDARY_NAME,
        mutation_target=MUTATION_TARGET,
        authorization_present=authorization_present,
        authorization_boundary_matched=authorization_boundary_matched,
        replacement_policy_matched=replacement_policy_matched,
        replacement_policy_authorized=replacement_policy_authorized,
        no_collision_policy_satisfied=no_collision_policy_satisfied,
        authorized_preview_registry_present=authorized_preview_registry_present,
        historical_condition_count=historical_condition_count,
        historical_condition_name=(historical_condition_name if mutation_transaction_ready else ""),
        historical_condition_present=historical_condition_present,
        historical_type_preserved=historical_type_preserved,
        state_valid=state_valid,
        registry_source_matched=registry_source_matched,
        original_historical_source_preserved=original_historical_source_preserved,
        authorization_contract_aligned=authorization_contract_aligned,
        missing_gates=missing_gates,
        mutation_transaction_ready=mutation_transaction_ready,
        transaction_registry_snapshot=(registry_snapshot if mutation_transaction_ready else {}),
        transaction_historical_condition=(historical_condition if mutation_transaction_ready else {}),
    )
