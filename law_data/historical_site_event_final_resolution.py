"""Read-only semantic final resolution for HISTORICAL_SITE_EVENT.

STEP31 converts the already-normalized STEP30 internal candidate into the
standard semantic regulation states TRUE / FALSE / UNKNOWN. It does not mutate
SITE or Rule Engine state, register runtime or production behavior, write
outputs, or expose public API behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.historical_site_event_final_resolution_candidate import (
    FALSE_CANDIDATE,
    TRUE_CANDIDATE,
    UNKNOWN as CANDIDATE_UNKNOWN,
    HistoricalSiteEventFinalResolutionCandidateAssessment,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_FINAL_RESOLUTION"
HISTORICAL_RESOLUTION_TYPE = "HISTORICAL_SITE_EVENT"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"
TRUE = "TRUE"
FALSE = "FALSE"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class HistoricalSiteEventFinalResolutionAssessment:
    boundary: str
    profile_present: bool
    profile_name: str | None
    historical_resolution_type_matched: bool
    historical_condition_type_matched: bool
    candidate_assessment_present: bool
    candidate_profile_aligned: bool
    candidate_conflict_detected: bool
    final_resolution_candidate: str
    missing_gates: tuple[str, ...]
    resolution: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "profile_present": self.profile_present,
            "profile_name": self.profile_name,
            "historical_resolution_type_matched": self.historical_resolution_type_matched,
            "historical_condition_type_matched": self.historical_condition_type_matched,
            "candidate_assessment_present": self.candidate_assessment_present,
            "candidate_profile_aligned": self.candidate_profile_aligned,
            "candidate_conflict_detected": self.candidate_conflict_detected,
            "final_resolution_candidate": self.final_resolution_candidate,
            "missing_gates": list(self.missing_gates),
            "resolution": self.resolution,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "production_wiring_applied": False,
            "runtime_registry_mutated": False,
            "public_api_exposed": False,
        }


def evaluate_historical_site_event_final_resolution(
    profile: RegulationResolutionProfile | None,
    candidate: HistoricalSiteEventFinalResolutionCandidateAssessment | None,
) -> HistoricalSiteEventFinalResolutionAssessment:
    profile_present = isinstance(profile, RegulationResolutionProfile)
    profile_name = profile.name if profile_present else None
    historical_resolution_type_matched = bool(
        profile_present and profile.resolution_type == HISTORICAL_RESOLUTION_TYPE
    )
    historical_condition_type_matched = bool(
        profile_present and profile.condition_type == HISTORICAL_CONDITION_TYPE
    )
    candidate_assessment_present = isinstance(
        candidate, HistoricalSiteEventFinalResolutionCandidateAssessment
    )
    candidate_profile_aligned = bool(
        profile_present
        and candidate_assessment_present
        and candidate.profile_name == profile_name
    )
    candidate_conflict_detected = bool(
        candidate_assessment_present and candidate.conflict_detected is True
    )
    final_resolution_candidate = (
        candidate.final_resolution_candidate
        if candidate_assessment_present
        else CANDIDATE_UNKNOWN
    )

    gates = {
        "profile_present": profile_present,
        "historical_resolution_type_matched": historical_resolution_type_matched,
        "historical_condition_type_matched": historical_condition_type_matched,
        "candidate_assessment_present": candidate_assessment_present,
        "candidate_profile_aligned": candidate_profile_aligned,
        "candidate_conflict_free": not candidate_conflict_detected,
    }
    missing_gates = tuple(name for name, passed in gates.items() if not passed)

    if missing_gates:
        resolution = UNKNOWN
    elif final_resolution_candidate == TRUE_CANDIDATE:
        resolution = TRUE
    elif final_resolution_candidate == FALSE_CANDIDATE:
        resolution = FALSE
    elif final_resolution_candidate == CANDIDATE_UNKNOWN:
        resolution = UNKNOWN
    else:
        resolution = UNKNOWN

    return HistoricalSiteEventFinalResolutionAssessment(
        boundary=BOUNDARY_NAME,
        profile_present=profile_present,
        profile_name=profile_name,
        historical_resolution_type_matched=historical_resolution_type_matched,
        historical_condition_type_matched=historical_condition_type_matched,
        candidate_assessment_present=candidate_assessment_present,
        candidate_profile_aligned=candidate_profile_aligned,
        candidate_conflict_detected=candidate_conflict_detected,
        final_resolution_candidate=final_resolution_candidate,
        missing_gates=missing_gates,
        resolution=resolution,
    )
