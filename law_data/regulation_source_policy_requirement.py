"""Fail-closed binding for regulation source-policy requirements.

This module answers one narrow question: whether every source-policy requirement
explicitly declared by a ``RegulationResolutionProfile`` has an independently
verified positive requirement fact.

It does not discover sources, verify authorities, verify documents, evaluate
spatial inclusion or historical completeness itself, resolve SITE applicability,
infer legal absence, register production/runtime logic, mutate Rule Engine input,
or expose a public API contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from law_data.regulation_resolution_profile import RegulationResolutionProfile


BOUNDARY_NAME = "REGULATION_SOURCE_POLICY_REQUIREMENT"


def _normalize_requirement_facts(
    facts: Mapping[str, Any] | None,
) -> dict[str, bool]:
    """Normalize explicit requirement facts without manufacturing verification."""

    if not isinstance(facts, Mapping):
        return {}

    normalized: dict[str, bool] = {}
    for raw_name, raw_verified in facts.items():
        name = str(raw_name or "").strip()
        if not name:
            continue
        normalized[name] = raw_verified is True
    return normalized


@dataclass(frozen=True)
class RegulationSourcePolicyRequirementAssessment:
    """Read-only assessment of declared source-policy requirements.

    Requirement-name presence is descriptive only. Positive satisfaction requires
    a non-empty declaration and an explicit ``True`` fact for every exact declared
    requirement. Missing, false, non-boolean-truthy, or unrelated facts fail closed.
    """

    profile_present: bool
    profile_name: str | None
    source_policy_requirements: tuple[str, ...]
    source_policy_requirements_declared: bool
    verified_requirements: tuple[str, ...]
    missing_requirements: tuple[str, ...]
    unexpected_requirements: tuple[str, ...]
    source_policy_requirement_satisfied: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_name": BOUNDARY_NAME,
            "profile_present": self.profile_present,
            "profile_name": self.profile_name,
            "source_policy_requirements": list(self.source_policy_requirements),
            "source_policy_requirements_declared": (
                self.source_policy_requirements_declared
            ),
            "verified_requirements": list(self.verified_requirements),
            "missing_requirements": list(self.missing_requirements),
            "unexpected_requirements": list(self.unexpected_requirements),
            "source_policy_requirement_satisfied": (
                self.source_policy_requirement_satisfied
            ),
        }


def evaluate_regulation_source_policy_requirement(
    profile: RegulationResolutionProfile | None,
    verified_requirement_facts: Mapping[str, Any] | None,
) -> RegulationSourcePolicyRequirementAssessment:
    """Bind profile requirements to explicit independent verification facts.

    The profile's own ``source_policy_verified`` metadata is intentionally not used
    as evidence here. Contract readiness, matching names, diagnostic metadata, and
    unrelated verified requirements cannot satisfy a declared requirement.

    An empty requirement declaration never becomes vacuously satisfied.
    """

    profile_present = isinstance(profile, RegulationResolutionProfile)
    profile_name = profile.name if profile_present else None
    source_policy_requirements = (
        tuple(profile.source_policy_requirements) if profile_present else ()
    )
    source_policy_requirements_declared = bool(source_policy_requirements)

    facts = _normalize_requirement_facts(verified_requirement_facts)
    declared_set = set(source_policy_requirements)

    verified_requirements = tuple(
        requirement
        for requirement in source_policy_requirements
        if facts.get(requirement) is True
    )
    missing_requirements = tuple(
        requirement
        for requirement in source_policy_requirements
        if facts.get(requirement) is not True
    )
    unexpected_requirements = tuple(
        name
        for name, verified in facts.items()
        if verified is True and name not in declared_set
    )

    source_policy_requirement_satisfied = bool(
        profile_present
        and source_policy_requirements_declared
        and not missing_requirements
    )

    return RegulationSourcePolicyRequirementAssessment(
        profile_present=profile_present,
        profile_name=profile_name,
        source_policy_requirements=source_policy_requirements,
        source_policy_requirements_declared=source_policy_requirements_declared,
        verified_requirements=verified_requirements,
        missing_requirements=missing_requirements,
        unexpected_requirements=unexpected_requirements,
        source_policy_requirement_satisfied=source_policy_requirement_satisfied,
    )
