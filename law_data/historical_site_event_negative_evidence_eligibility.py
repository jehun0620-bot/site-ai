"""Fail-closed negative-evidence eligibility boundary for HISTORICAL_SITE_EVENT.

This module combines an existing regulation-resolution profile policy with a
STEP27 exhaustive-disproof assessment. It determines only whether independently
verified negative evidence is eligible to be consumed by a later resolution
boundary. It does not generate FALSE/FALSE_CANDIDATE, infer legal absence,
mutate SITE/Rule Engine/runtime state, register production logic, write outputs,
or expose a public API contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.historical_site_event_exhaustive_disproof import (
    HistoricalSiteEventExhaustiveDisproofAssessment,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_NEGATIVE_EVIDENCE_ELIGIBILITY"
HISTORICAL_RESOLUTION_TYPE = "HISTORICAL_SITE_EVENT"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"


def _is_explicit_true(value: object) -> bool:
    """Accept only the literal boolean True as an enabled positive gate."""

    return value is True


@dataclass(frozen=True)
class HistoricalSiteEventNegativeEvidenceEligibilityAssessment:
    """Read-only eligibility assessment; never a legal resolution result."""

    boundary: str
    profile_present: bool
    profile_name: str | None
    historical_resolution_type_matched: bool
    historical_condition_type_matched: bool
    negative_evidence_allowed: bool
    legal_absence_inference_allowed: bool
    exhaustive_disproof_assessment_present: bool
    exhaustive_disproof_verified: bool
    missing_gates: tuple[str, ...]
    negative_evidence_eligible: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "profile_present": self.profile_present,
            "profile_name": self.profile_name,
            "historical_resolution_type_matched": (
                self.historical_resolution_type_matched
            ),
            "historical_condition_type_matched": (
                self.historical_condition_type_matched
            ),
            "negative_evidence_allowed": self.negative_evidence_allowed,
            "legal_absence_inference_allowed": (
                self.legal_absence_inference_allowed
            ),
            "exhaustive_disproof_assessment_present": (
                self.exhaustive_disproof_assessment_present
            ),
            "exhaustive_disproof_verified": self.exhaustive_disproof_verified,
            "missing_gates": list(self.missing_gates),
            "negative_evidence_eligible": self.negative_evidence_eligible,
            "false_candidate_generated": False,
            "negative_resolution_generated": False,
            "legal_absence_inference_performed": False,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "production_wiring_applied": False,
            "runtime_registry_mutated": False,
            "public_api_exposed": False,
        }


def evaluate_historical_site_event_negative_evidence_eligibility(
    profile: RegulationResolutionProfile | None,
    exhaustive_disproof: HistoricalSiteEventExhaustiveDisproofAssessment | None,
) -> HistoricalSiteEventNegativeEvidenceEligibilityAssessment:
    """Evaluate whether verified historical disproof is policy-eligible.

    Eligibility requires a concrete historical SITE_HISTORY profile, explicit
    profile permission to consume negative evidence, and a concrete STEP27
    assessment whose exhaustive-disproof result is literally True.

    ``legal_absence_inference_allowed`` is diagnostic only. Exhaustive disproof
    is independently verified positive evidence and must never be treated as an
    inference from missing/search-no-hit evidence.
    """

    profile_present = isinstance(profile, RegulationResolutionProfile)
    profile_name = profile.name if profile_present else None

    historical_resolution_type_matched = (
        profile_present and profile.resolution_type == HISTORICAL_RESOLUTION_TYPE
    )
    historical_condition_type_matched = (
        profile_present and profile.condition_type == HISTORICAL_CONDITION_TYPE
    )
    negative_evidence_allowed = (
        profile_present and _is_explicit_true(profile.negative_evidence_allowed)
    )
    legal_absence_inference_allowed = (
        profile_present
        and _is_explicit_true(profile.legal_absence_inference_allowed)
    )

    exhaustive_disproof_assessment_present = isinstance(
        exhaustive_disproof,
        HistoricalSiteEventExhaustiveDisproofAssessment,
    )
    exhaustive_disproof_verified = (
        exhaustive_disproof_assessment_present
        and _is_explicit_true(exhaustive_disproof.exhaustive_disproof_verified)
    )

    gates = {
        "profile_present": profile_present,
        "historical_resolution_type_matched": historical_resolution_type_matched,
        "historical_condition_type_matched": historical_condition_type_matched,
        "negative_evidence_allowed": negative_evidence_allowed,
        "exhaustive_disproof_assessment_present": (
            exhaustive_disproof_assessment_present
        ),
        "exhaustive_disproof_verified": exhaustive_disproof_verified,
    }

    missing_gates = tuple(name for name, passed in gates.items() if not passed)
    negative_evidence_eligible = not missing_gates

    return HistoricalSiteEventNegativeEvidenceEligibilityAssessment(
        boundary=BOUNDARY_NAME,
        profile_present=profile_present,
        profile_name=profile_name,
        historical_resolution_type_matched=historical_resolution_type_matched,
        historical_condition_type_matched=historical_condition_type_matched,
        negative_evidence_allowed=negative_evidence_allowed,
        legal_absence_inference_allowed=legal_absence_inference_allowed,
        exhaustive_disproof_assessment_present=exhaustive_disproof_assessment_present,
        exhaustive_disproof_verified=exhaustive_disproof_verified,
        missing_gates=missing_gates,
        negative_evidence_eligible=negative_evidence_eligible,
    )
