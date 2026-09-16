"""Typed transport envelope for already-verified historical Rule Engine input.

This boundary does not decide SITE truth. It only seals a historical rule-input
mapping to the canonical PNU that the production orchestrator already verified.
Service/builder layers can therefore reject raw dict injection and rebind the
sealed input to the resolved SITE identity before consumption.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

BOUNDARY_NAME = "HISTORICAL_VERIFIED_RULE_INPUT_ENVELOPE"


@dataclass(frozen=True)
class HistoricalVerifiedRuleInputEnvelope:
    boundary: str
    canonical_pnu: str
    historical_rule_input: Mapping[str, Any]
    verified: bool

    @property
    def ready(self) -> bool:
        return bool(
            self.boundary == BOUNDARY_NAME
            and self.verified is True
            and len(self.canonical_pnu) == 19
            and self.canonical_pnu.isdigit()
            and isinstance(self.historical_rule_input, Mapping)
            and self.historical_rule_input
        )

    def to_dict(self):
        return {
            "boundary": self.boundary,
            "canonical_pnu": self.canonical_pnu,
            "historical_rule_input": copy.deepcopy(dict(self.historical_rule_input)),
            "verified": self.verified,
            "site_truth_decided": False,
            "rule_engine_called": False,
            "runtime_registered": False,
            "public_api_exposed": False,
        }


def seal_verified_historical_rule_input(
    *,
    canonical_pnu: str,
    historical_rule_input: Mapping[str, Any],
) -> HistoricalVerifiedRuleInputEnvelope:
    pnu = str(canonical_pnu or "").strip()
    value = (
        copy.deepcopy(dict(historical_rule_input))
        if isinstance(historical_rule_input, Mapping)
        else {}
    )
    verified = bool(len(pnu) == 19 and pnu.isdigit() and value)
    return HistoricalVerifiedRuleInputEnvelope(
        boundary=BOUNDARY_NAME,
        canonical_pnu=pnu,
        historical_rule_input=value if verified else {},
        verified=verified,
    )
