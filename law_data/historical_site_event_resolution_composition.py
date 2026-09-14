"""Fail-closed composition boundary for HISTORICAL_SITE_EVENT resolution.

This module composes already-evaluated STEP22/23/24/25 assessments. It does not
search or discover sources, verify underlying evidence, infer legal absence,
produce a negative legal resolution, mutate SITE/Rule Engine/runtime state,
register production logic, write outputs, or expose a public API contract.

A positive result is only ``TRUE_CANDIDATE``. Every incomplete, mismatched, or
unverified input remains ``UNKNOWN``. ``TRUE_CANDIDATE`` is an internal
resolution candidate and is not production TRUE or SITE state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.historical_history_completeness import (
    HistoricalHistoryCompletenessAssessment,
)
from law_data.historical_site_event_qualification import (
    HistoricalSiteEventQualificationAssessment,
)
from law_data.regulation_authority_requirement import (
    RegulationAuthorityRequirementAssessment,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile
from law_data.regulation_source_policy_requirement import (
    RegulationSourcePolicyRequirementAssessment,
)


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_RESOLUTION_COMPOSITION"
HISTORICAL_RESOLUTION_TYPE = "HISTORICAL_SITE_EVENT"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"
TRUE_CANDIDATE = "TRUE_CANDIDATE"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class HistoricalSiteEventResolutionCompositionAssessment:
    """Read-only composition of independently verified historical gates."""

    boundary: str
    profile_present: bool
    profile_name: str | None
    historical_resolution_type_matched: bool
    historical_condition_type_matched: bool
    authority_profile_aligned: bool
    source_policy_profile_aligned: bool
    qualifying_historical_event_verified: bool
    history_completeness_verified: bool
    authority_requirement_satisfied: bool
    source_policy_requirement_satisfied: bool
    missing_gates: tuple[str, ...]
    positive_gate_satisfied: bool
    resolution_candidate: str

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
            "authority_profile_aligned": self.authority_profile_aligned,
            "source_policy_profile_aligned": self.source_policy_profile_aligned,
            "qualifying_historical_event_verified": (
                self.qualifying_historical_event_verified
            ),
            "history_completeness_verified": self.history_completeness_verified,
            "authority_requirement_satisfied": self.authority_requirement_satisfied,
            "source_policy_requirement_satisfied": (
                self.source_policy_requirement_satisfied
            ),
            "missing_gates": list(self.missing_gates),
            "positive_gate_satisfied": self.positive_gate_satisfied,
            "resolution_candidate": self.resolution_candidate,
            "negative_evidence_inference_allowed": False,
            "legal_absence_inference_allowed": False,
            "negative_resolution_generated": False,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "production_wiring_applied": False,
            "runtime_registry_mutated": False,
            "public_api_exposed": False,
        }


def evaluate_historical_site_event_resolution_composition(
    profile: RegulationResolutionProfile | None,
    qualification: HistoricalSiteEventQualificationAssessment | None,
    history_completeness: HistoricalHistoryCompletenessAssessment | None,
    authority_requirement: RegulationAuthorityRequirementAssessment | None,
    source_policy_requirement: RegulationSourcePolicyRequirementAssessment | None,
) -> HistoricalSiteEventResolutionCompositionAssessment:
    """Compose historical positive gates without promoting to final SITE state.

    Inputs must be the concrete assessment types produced by their respective
    boundaries. Positive boolean gates must be the literal boolean ``True``.
    Authority/source-policy assessments must also refer to the same profile name.
    Missing or mismatched inputs fail closed to ``UNKNOWN``.
    """

    profile_present = isinstance(profile, RegulationResolutionProfile)
    profile_name = profile.name if profile_present else None

    historical_resolution_type_matched = bool(
        profile_present and profile.resolution_type == HISTORICAL_RESOLUTION_TYPE
    )
    historical_condition_type_matched = bool(
        profile_present and profile.condition_type == HISTORICAL_CONDITION_TYPE
    )

    qualification_present = isinstance(
        qualification, HistoricalSiteEventQualificationAssessment
    )
    history_completeness_present = isinstance(
        history_completeness, HistoricalHistoryCompletenessAssessment
    )
    authority_present = isinstance(
        authority_requirement, RegulationAuthorityRequirementAssessment
    )
    source_policy_present = isinstance(
        source_policy_requirement, RegulationSourcePolicyRequirementAssessment
    )

    authority_profile_aligned = bool(
        profile_present
        and authority_present
        and authority_requirement.profile_name == profile_name
    )
    source_policy_profile_aligned = bool(
        profile_present
        and source_policy_present
        and source_policy_requirement.profile_name == profile_name
    )

    gates = {
        "historical_resolution_type_matched": historical_resolution_type_matched,
        "historical_condition_type_matched": historical_condition_type_matched,
        "authority_profile_aligned": authority_profile_aligned,
        "source_policy_profile_aligned": source_policy_profile_aligned,
        "qualifying_historical_event_verified": bool(
            qualification_present
            and qualification.qualifying_historical_event_verified is True
        ),
        "history_completeness_verified": bool(
            history_completeness_present
            and history_completeness.history_completeness_verified is True
        ),
        "authority_requirement_satisfied": bool(
            authority_present
            and authority_requirement.authority_requirement_satisfied is True
        ),
        "source_policy_requirement_satisfied": bool(
            source_policy_present
            and source_policy_requirement.source_policy_requirement_satisfied is True
        ),
    }

    missing_gates = tuple(name for name, passed in gates.items() if not passed)
    positive_gate_satisfied = not missing_gates
    resolution_candidate = TRUE_CANDIDATE if positive_gate_satisfied else UNKNOWN

    return HistoricalSiteEventResolutionCompositionAssessment(
        boundary=BOUNDARY_NAME,
        profile_present=profile_present,
        profile_name=profile_name,
        historical_resolution_type_matched=historical_resolution_type_matched,
        historical_condition_type_matched=historical_condition_type_matched,
        authority_profile_aligned=authority_profile_aligned,
        source_policy_profile_aligned=source_policy_profile_aligned,
        qualifying_historical_event_verified=gates[
            "qualifying_historical_event_verified"
        ],
        history_completeness_verified=gates["history_completeness_verified"],
        authority_requirement_satisfied=gates["authority_requirement_satisfied"],
        source_policy_requirement_satisfied=gates[
            "source_policy_requirement_satisfied"
        ],
        missing_gates=missing_gates,
        positive_gate_satisfied=positive_gate_satisfied,
        resolution_candidate=resolution_candidate,
    )
