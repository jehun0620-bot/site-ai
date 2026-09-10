"""Fail-closed binding between regulation profiles and authority source scope.

This module answers one narrow question: whether an explicitly identified
regulation profile has its authority requirement satisfied by an independently
verified ``AuthoritySourceScope``.

It does not discover or verify authorities, resolve SITE applicability, satisfy
spatial/historical source-policy requirements, infer legal absence, register
runtime logic, mutate Rule Engine input, or expose a public API contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from law_data.authority_source_scope import (
    AuthoritySourceScope,
    normalize_authority_source_scope,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile


BOUNDARY_NAME = "REGULATION_AUTHORITY_REQUIREMENT"


@dataclass(frozen=True)
class RegulationAuthorityRequirementAssessment:
    """Read-only assessment of profile-to-authority-scope alignment.

    Identity alignment is descriptive matching only. It never verifies competent
    authority by itself. ``authority_requirement_satisfied`` can become True only
    when a profile exists, declares an authority requirement, its exact condition
    identity matches the scope target, and the scope's full authority chain is
    independently verified positive.
    """

    profile_present: bool
    profile_name: str | None
    scope_target_regulation: str | None
    condition_identity_aligned: bool
    authority_requirements: tuple[str, ...]
    source_policy_requirements: tuple[str, ...]
    authority_requirements_declared: bool
    source_policy_requirements_declared: bool
    authority_chain_verified: bool
    target_regulation_compatibility_verified: bool
    target_regulation_compatible: bool | None
    authority_requirement_satisfied: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_name": BOUNDARY_NAME,
            "profile_present": self.profile_present,
            "profile_name": self.profile_name,
            "scope_target_regulation": self.scope_target_regulation,
            "condition_identity_aligned": self.condition_identity_aligned,
            "authority_requirements": list(self.authority_requirements),
            "source_policy_requirements": list(self.source_policy_requirements),
            "authority_requirements_declared": self.authority_requirements_declared,
            "source_policy_requirements_declared": self.source_policy_requirements_declared,
            "authority_chain_verified": self.authority_chain_verified,
            "target_regulation_compatibility_verified": (
                self.target_regulation_compatibility_verified
            ),
            "target_regulation_compatible": self.target_regulation_compatible,
            "authority_requirement_satisfied": self.authority_requirement_satisfied,
        }


def evaluate_regulation_authority_requirement(
    profile: RegulationResolutionProfile | None,
    authority_scope: AuthoritySourceScope | Mapping[str, Any] | None,
) -> RegulationAuthorityRequirementAssessment:
    """Evaluate profile/scope binding without manufacturing verification.

    Exact name equality only establishes condition identity alignment. A matching
    name, official-looking host, source role, or authority-scope string is not
    sufficient. Positive satisfaction requires the scope's complete explicit
    authority verification chain, which itself includes verified positive target
    regulation compatibility.

    Source-policy requirements are returned for downstream diagnostics only.
    This boundary intentionally does not evaluate spatial inclusion, historical
    completeness, provenance completeness, document validity, or SITE state.
    """

    scope = normalize_authority_source_scope(authority_scope)

    profile_present = isinstance(profile, RegulationResolutionProfile)
    profile_name = profile.name if profile_present else None
    authority_requirements = (
        tuple(profile.authority_requirements) if profile_present else ()
    )
    source_policy_requirements = (
        tuple(profile.source_policy_requirements) if profile_present else ()
    )

    condition_identity_aligned = bool(
        profile_present
        and scope.target_regulation is not None
        and profile_name == scope.target_regulation
    )
    authority_requirements_declared = bool(authority_requirements)
    source_policy_requirements_declared = bool(source_policy_requirements)

    authority_requirement_satisfied = bool(
        profile_present
        and condition_identity_aligned
        and authority_requirements_declared
        and scope.authority_chain_verified
    )

    return RegulationAuthorityRequirementAssessment(
        profile_present=profile_present,
        profile_name=profile_name,
        scope_target_regulation=scope.target_regulation,
        condition_identity_aligned=condition_identity_aligned,
        authority_requirements=authority_requirements,
        source_policy_requirements=source_policy_requirements,
        authority_requirements_declared=authority_requirements_declared,
        source_policy_requirements_declared=source_policy_requirements_declared,
        authority_chain_verified=scope.authority_chain_verified,
        target_regulation_compatibility_verified=(
            scope.target_regulation_compatibility_verified
        ),
        target_regulation_compatible=scope.target_regulation_compatible,
        authority_requirement_satisfied=authority_requirement_satisfied,
    )
