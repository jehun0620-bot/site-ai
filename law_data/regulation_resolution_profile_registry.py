from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from law_data.regulation_resolution_profile import RegulationResolutionProfile


UQQ700_CONDITION_NAME = "개발밀도관리구역"
URBAN_AREA_CONVERSION_CONDITION_NAME = "도시지역편입해제구역"


_UQQ700_PROFILE = RegulationResolutionProfile(
    name=UQQ700_CONDITION_NAME,
    condition_type="SITE",
    resolution_type="HYBRID_SPATIAL_NOTICE",
    standard_code="UQQ700",
    standard_code_verified=True,
    authority_requirements=(
        "OFFICIAL DESIGNATION IDENTITY VERIFIED",
        "CURRENT VALIDITY VERIFIED",
    ),
    source_policy_requirements=(
        "SITE SPATIAL INCLUSION VERIFIED",
    ),
    authority_identity_verified=False,
    source_policy_verified=False,
    negative_evidence_allowed=False,
    legal_absence_inference_allowed=False,
    site_promotion_allowed=False,
    production_registration_allowed=False,
    runtime_registration_allowed=False,
)


_URBAN_AREA_CONVERSION_PROFILE = RegulationResolutionProfile(
    name=URBAN_AREA_CONVERSION_CONDITION_NAME,
    condition_type="SITE_HISTORY",
    resolution_type="HISTORICAL_SITE_EVENT",
    standard_code=None,
    standard_code_verified=False,
    authority_requirements=(
        "VERIFIED QUALIFYING HISTORICAL SITE EVENT",
    ),
    source_policy_requirements=(
        "HISTORY COMPLETENESS VERIFIED",
        "PROVENANCE VERIFIED",
    ),
    authority_identity_verified=False,
    source_policy_verified=False,
    negative_evidence_allowed=False,
    legal_absence_inference_allowed=False,
    site_promotion_allowed=False,
    production_registration_allowed=False,
    runtime_registration_allowed=False,
)


_BUILTIN_PROFILES = MappingProxyType(
    {
        _UQQ700_PROFILE.name: _UQQ700_PROFILE,
        _URBAN_AREA_CONVERSION_PROFILE.name: _URBAN_AREA_CONVERSION_PROFILE,
    }
)


BUILTIN_REGULATION_RESOLUTION_PROFILES: Mapping[
    str, RegulationResolutionProfile
] = _BUILTIN_PROFILES


def get_regulation_resolution_profile(
    condition_name: str,
) -> RegulationResolutionProfile | None:
    """Return an exact-name built-in profile without inference or mutation.

    Unknown, empty, aliased, partial, or normalized-looking names intentionally
    return ``None``. This lookup does not execute resolvers, decide SITE state,
    register runtime behavior, or infer a standard code.
    """

    if not isinstance(condition_name, str):
        return None

    return BUILTIN_REGULATION_RESOLUTION_PROFILES.get(condition_name)


def list_regulation_resolution_profiles() -> tuple[RegulationResolutionProfile, ...]:
    """Return the fixed built-in profiles as an immutable tuple snapshot."""

    return tuple(BUILTIN_REGULATION_RESOLUTION_PROFILES.values())
