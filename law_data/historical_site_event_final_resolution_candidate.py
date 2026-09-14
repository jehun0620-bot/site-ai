"""Fail-closed final candidate normalization for HISTORICAL_SITE_EVENT.

This module combines the existing STEP26 positive candidate and STEP29 negative
candidate into one internal candidate state. It never promotes to production
TRUE/FALSE, SITE state, Rule Engine state, runtime registration, or public API.
Conflicting positive and negative candidates fail closed to UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.historical_site_event_negative_resolution_candidate import (
    FALSE_CANDIDATE,
    UNKNOWN as NEGATIVE_UNKNOWN,
    HistoricalSiteEventNegativeResolutionCandidateAssessment,
)
from law_data.historical_site_event_resolution_composition import (
    TRUE_CANDIDATE,
    UNKNOWN as POSITIVE_UNKNOWN,
    HistoricalSiteEventResolutionCompositionAssessment,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_FINAL_RESOLUTION_CANDIDATE"
HISTORICAL_RESOLUTION_TYPE = "HISTORICAL_SITE_EVENT"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class HistoricalSiteEventFinalResolutionCandidateAssessment:
    boundary: str
    profile_present: bool
    profile_name: str | None
    historical_resolution_type_matched: bool
    historical_condition_type_matched: bool
    positive_assessment_present: bool
    positive_profile_aligned: bool
    positive_resolution_candidate: str
    negative_assessment_present: bool
    negative_profile_aligned: bool
    negative_resolution_candidate: str
    conflict_detected: bool
    missing_gates: tuple[str, ...]
    final_resolution_candidate: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "profile_present": self.profile_present,
            "profile_name": self.profile_name,
            "historical_resolution_type_matched": self.historical_resolution_type_matched,
            "historical_condition_type_matched": self.historical_condition_type_matched,
            "positive_assessment_present": self.positive_assessment_present,
            "positive_profile_aligned": self.positive_profile_aligned,
            "positive_resolution_candidate": self.positive_resolution_candidate,
            "negative_assessment_present": self.negative_assessment_present,
            "negative_profile_aligned": self.negative_profile_aligned,
            "negative_resolution_candidate": self.negative_resolution_candidate,
            "conflict_detected": self.conflict_detected,
            "missing_gates": list(self.missing_gates),
            "final_resolution_candidate": self.final_resolution_candidate,
            "production_true_generated": False,
            "production_false_generated": False,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "production_wiring_applied": False,
            "runtime_registry_mutated": False,
            "public_api_exposed": False,
        }


def evaluate_historical_site_event_final_resolution_candidate(
    profile: RegulationResolutionProfile | None,
    positive: HistoricalSiteEventResolutionCompositionAssessment | None,
    negative: HistoricalSiteEventNegativeResolutionCandidateAssessment | None,
) -> HistoricalSiteEventFinalResolutionCandidateAssessment:
    profile_present = isinstance(profile, RegulationResolutionProfile)
    profile_name = profile.name if profile_present else None
    historical_resolution_type_matched = bool(
        profile_present and profile.resolution_type == HISTORICAL_RESOLUTION_TYPE
    )
    historical_condition_type_matched = bool(
        profile_present and profile.condition_type == HISTORICAL_CONDITION_TYPE
    )

    positive_assessment_present = isinstance(
        positive, HistoricalSiteEventResolutionCompositionAssessment
    )
    positive_profile_aligned = bool(
        profile_present
        and positive_assessment_present
        and positive.profile_name == profile_name
    )
    positive_resolution_candidate = (
        positive.resolution_candidate if positive_assessment_present else POSITIVE_UNKNOWN
    )

    negative_assessment_present = isinstance(
        negative, HistoricalSiteEventNegativeResolutionCandidateAssessment
    )
    negative_profile_aligned = bool(
        profile_present
        and negative_assessment_present
        and negative.profile_name == profile_name
    )
    negative_resolution_candidate = (
        negative.resolution_candidate if negative_assessment_present else NEGATIVE_UNKNOWN
    )

    gates = {
        "profile_present": profile_present,
        "historical_resolution_type_matched": historical_resolution_type_matched,
        "historical_condition_type_matched": historical_condition_type_matched,
        "positive_assessment_present": positive_assessment_present,
        "positive_profile_aligned": positive_profile_aligned,
        "negative_assessment_present": negative_assessment_present,
        "negative_profile_aligned": negative_profile_aligned,
    }
    missing_gates = tuple(name for name, passed in gates.items() if not passed)

    positive_true = positive_resolution_candidate == TRUE_CANDIDATE
    positive_unknown = positive_resolution_candidate == POSITIVE_UNKNOWN
    negative_false = negative_resolution_candidate == FALSE_CANDIDATE
    negative_unknown = negative_resolution_candidate == NEGATIVE_UNKNOWN
    conflict_detected = positive_true and negative_false

    if missing_gates or conflict_detected:
        final_resolution_candidate = UNKNOWN
    elif positive_true and negative_unknown:
        final_resolution_candidate = TRUE_CANDIDATE
    elif positive_unknown and negative_false:
        final_resolution_candidate = FALSE_CANDIDATE
    elif positive_unknown and negative_unknown:
        final_resolution_candidate = UNKNOWN
    else:
        final_resolution_candidate = UNKNOWN

    return HistoricalSiteEventFinalResolutionCandidateAssessment(
        boundary=BOUNDARY_NAME,
        profile_present=profile_present,
        profile_name=profile_name,
        historical_resolution_type_matched=historical_resolution_type_matched,
        historical_condition_type_matched=historical_condition_type_matched,
        positive_assessment_present=positive_assessment_present,
        positive_profile_aligned=positive_profile_aligned,
        positive_resolution_candidate=positive_resolution_candidate,
        negative_assessment_present=negative_assessment_present,
        negative_profile_aligned=negative_profile_aligned,
        negative_resolution_candidate=negative_resolution_candidate,
        conflict_detected=conflict_detected,
        missing_gates=missing_gates,
        final_resolution_candidate=final_resolution_candidate,
    )
