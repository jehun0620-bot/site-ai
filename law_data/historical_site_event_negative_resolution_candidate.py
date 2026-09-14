"""Fail-closed negative-resolution candidate boundary for HISTORICAL_SITE_EVENT.

This module composes already-evaluated STEP27 exhaustive-disproof evidence with
STEP28 negative-evidence eligibility. It can produce only an internal
``FALSE_CANDIDATE`` or ``UNKNOWN``. It does not produce final FALSE, infer legal
absence, mutate SITE/Rule Engine/runtime state, register production logic, write
outputs, or expose a public API contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.historical_site_event_exhaustive_disproof import (
    HistoricalSiteEventExhaustiveDisproofAssessment,
)
from law_data.historical_site_event_negative_evidence_eligibility import (
    HistoricalSiteEventNegativeEvidenceEligibilityAssessment,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_NEGATIVE_RESOLUTION_CANDIDATE"
HISTORICAL_RESOLUTION_TYPE = "HISTORICAL_SITE_EVENT"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"
FALSE_CANDIDATE = "FALSE_CANDIDATE"
UNKNOWN = "UNKNOWN"


def _is_explicit_true(value: object) -> bool:
    return value is True


@dataclass(frozen=True)
class HistoricalSiteEventNegativeResolutionCandidateAssessment:
    boundary: str
    profile_present: bool
    profile_name: str | None
    historical_resolution_type_matched: bool
    historical_condition_type_matched: bool
    eligibility_assessment_present: bool
    eligibility_profile_aligned: bool
    negative_evidence_eligible: bool
    exhaustive_disproof_assessment_present: bool
    exhaustive_disproof_verified: bool
    missing_gates: tuple[str, ...]
    negative_candidate_gate_satisfied: bool
    resolution_candidate: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "profile_present": self.profile_present,
            "profile_name": self.profile_name,
            "historical_resolution_type_matched": self.historical_resolution_type_matched,
            "historical_condition_type_matched": self.historical_condition_type_matched,
            "eligibility_assessment_present": self.eligibility_assessment_present,
            "eligibility_profile_aligned": self.eligibility_profile_aligned,
            "negative_evidence_eligible": self.negative_evidence_eligible,
            "exhaustive_disproof_assessment_present": self.exhaustive_disproof_assessment_present,
            "exhaustive_disproof_verified": self.exhaustive_disproof_verified,
            "missing_gates": list(self.missing_gates),
            "negative_candidate_gate_satisfied": self.negative_candidate_gate_satisfied,
            "resolution_candidate": self.resolution_candidate,
            "final_false_generated": False,
            "legal_absence_inference_performed": False,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "production_wiring_applied": False,
            "runtime_registry_mutated": False,
            "public_api_exposed": False,
        }


def evaluate_historical_site_event_negative_resolution_candidate(
    profile: RegulationResolutionProfile | None,
    exhaustive_disproof: HistoricalSiteEventExhaustiveDisproofAssessment | None,
    eligibility: HistoricalSiteEventNegativeEvidenceEligibilityAssessment | None,
) -> HistoricalSiteEventNegativeResolutionCandidateAssessment:
    profile_present = isinstance(profile, RegulationResolutionProfile)
    profile_name = profile.name if profile_present else None
    historical_resolution_type_matched = bool(
        profile_present and profile.resolution_type == HISTORICAL_RESOLUTION_TYPE
    )
    historical_condition_type_matched = bool(
        profile_present and profile.condition_type == HISTORICAL_CONDITION_TYPE
    )
    eligibility_assessment_present = isinstance(
        eligibility, HistoricalSiteEventNegativeEvidenceEligibilityAssessment
    )
    eligibility_profile_aligned = bool(
        profile_present
        and eligibility_assessment_present
        and eligibility.profile_name == profile_name
    )
    negative_evidence_eligible = bool(
        eligibility_assessment_present
        and _is_explicit_true(eligibility.negative_evidence_eligible)
    )
    exhaustive_disproof_assessment_present = isinstance(
        exhaustive_disproof, HistoricalSiteEventExhaustiveDisproofAssessment
    )
    exhaustive_disproof_verified = bool(
        exhaustive_disproof_assessment_present
        and _is_explicit_true(exhaustive_disproof.exhaustive_disproof_verified)
    )
    gates = {
        "profile_present": profile_present,
        "historical_resolution_type_matched": historical_resolution_type_matched,
        "historical_condition_type_matched": historical_condition_type_matched,
        "eligibility_assessment_present": eligibility_assessment_present,
        "eligibility_profile_aligned": eligibility_profile_aligned,
        "negative_evidence_eligible": negative_evidence_eligible,
        "exhaustive_disproof_assessment_present": exhaustive_disproof_assessment_present,
        "exhaustive_disproof_verified": exhaustive_disproof_verified,
    }
    missing_gates = tuple(name for name, passed in gates.items() if not passed)
    negative_candidate_gate_satisfied = not missing_gates
    resolution_candidate = FALSE_CANDIDATE if negative_candidate_gate_satisfied else UNKNOWN
    return HistoricalSiteEventNegativeResolutionCandidateAssessment(
        boundary=BOUNDARY_NAME,
        profile_present=profile_present,
        profile_name=profile_name,
        historical_resolution_type_matched=historical_resolution_type_matched,
        historical_condition_type_matched=historical_condition_type_matched,
        eligibility_assessment_present=eligibility_assessment_present,
        eligibility_profile_aligned=eligibility_profile_aligned,
        negative_evidence_eligible=negative_evidence_eligible,
        exhaustive_disproof_assessment_present=exhaustive_disproof_assessment_present,
        exhaustive_disproof_verified=exhaustive_disproof_verified,
        missing_gates=missing_gates,
        negative_candidate_gate_satisfied=negative_candidate_gate_satisfied,
        resolution_candidate=resolution_candidate,
    )
