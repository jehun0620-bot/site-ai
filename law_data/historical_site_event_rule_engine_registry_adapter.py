"""STEP62 historical-only registry adapter; no Rule Engine injection or spatial overlay."""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Mapping
from law_data.historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_RULE_ENGINE_REGISTRY_ADAPTER"

@dataclass(frozen=True)
class HistoricalSiteEventRuleEngineRegistry:
    boundary: str
    input_present: bool
    channel_matched: bool
    provenance_matched: bool
    repairs_valid: bool
    registry_consistent: bool
    missing_gates: tuple[str, ...]
    registry_ready: bool
    historical_site_registry: Mapping[str, Mapping[str, Any]]

    def to_dict(self):
        return {
            **self.__dict__,
            "missing_gates": list(self.missing_gates),
            "historical_site_registry": copy.deepcopy(dict(self.historical_site_registry)),
            "spatial_overlay_used": False,
            "site_condition_context_merged": False,
            "runtime_conditions_merged": False,
            "rule_engine_modified": False,
            "apply_site_registry_called": False,
            "production_wiring_applied": False,
            "runtime_registered": False,
            "public_api_exposed": False,
        }

def adapt_historical_site_event_rule_engine_registry(historical_rule_input: Mapping[str, Any] | None):
    present = isinstance(historical_rule_input, Mapping)
    value = copy.deepcopy(dict(historical_rule_input)) if present else {}
    channel_matched = value.get("channel") == CHANNEL
    provenance_matched = value.get("provenance") == PROVENANCE
    repairs = value.get("repairs")
    repairs_valid = isinstance(repairs, list) and all(
        isinstance(repair, Mapping)
        and isinstance(repair.get("condition"), str)
        and bool(repair.get("condition").strip())
        and repair.get("after") in {"TRUE", "FALSE", "UNKNOWN", "UNSET"}
        and isinstance(repair.get("new_confidence"), str)
        and bool(repair.get("new_confidence").strip())
        and repair.get("new_source") == PROVENANCE
        for repair in repairs or []
    )
    registry = {}
    consistent = True
    if repairs_valid:
        for repair in repairs:
            name = repair["condition"].strip()
            resolved = {
                "state": repair["after"],
                "confidence": repair["new_confidence"],
                "source": PROVENANCE,
            }
            if name in registry and registry[name] != resolved:
                consistent = False
                registry = {}
                break
            registry[name] = resolved
    gates = (
        ("input_present", present),
        ("channel_matched", channel_matched),
        ("provenance_matched", provenance_matched),
        ("repairs_valid", repairs_valid),
        ("registry_consistent", consistent),
    )
    missing = tuple(name for name, passed in gates if not passed)
    ready = not missing
    return HistoricalSiteEventRuleEngineRegistry(
        BOUNDARY_NAME, present, channel_matched, provenance_matched,
        repairs_valid, consistent, missing, ready, registry if ready else {},
    )
