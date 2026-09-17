# -*- coding: utf-8 -*-

"""SITE Analysis Service Integration."""

from __future__ import annotations

from typing import Any, Dict, Optional

from law_data.historical_verified_rule_input_envelope import (
    HistoricalVerifiedRuleInputEnvelope,
)
from law_data.district_unit_plan_verified_registry_candidate_envelope import (
    DistrictUnitPlanVerifiedRegistryCandidateEnvelope,
)
from law_data.site_analysis_builder import build_site_analysis
from site_data.vworld_api import create_pnu


def safe_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def site_to_analysis_input(site: Any) -> Dict[str, Any]:
    """Convert the Site object into the canonical builder input."""
    if site is None:
        raise ValueError("Site 객체가 없습니다.")

    site_id = safe_string(getattr(site, "site_id", ""))
    address = safe_string(getattr(site, "address", ""))
    road_address = safe_string(getattr(site, "road_address", ""))
    sigungu_cd = safe_string(getattr(site, "sigungu_cd", ""))
    bjdong_cd = safe_string(getattr(site, "bjdong_cd", ""))
    plat_gb_cd = safe_string(getattr(site, "plat_gb_cd", ""))
    bun = safe_string(getattr(site, "bun", ""))
    ji = safe_string(getattr(site, "ji", ""))

    pnu = ""
    if sigungu_cd and bjdong_cd and bun and ji and plat_gb_cd:
        try:
            pnu = create_pnu(sigungu_cd, bjdong_cd, bun, ji, plat_gb_cd)
        except ValueError:
            pnu = ""

    result = {
        "site_id": site_id,
        "address": address,
        "road_address": road_address,
        "sigungu_cd": sigungu_cd,
        "bjdong_cd": bjdong_cd,
        "plat_gb_cd": plat_gb_cd,
        "bun": bun,
        "ji": ji,
        "sigungu_code": sigungu_cd,
        "bjdong_code": bjdong_cd,
        "main_no": bun,
        "sub_no": ji,
        "pnu": pnu,
    }

    land = getattr(site, "land", None)
    if land is not None:
        zoning = safe_string(getattr(land, "zoning", ""))
        land_area = getattr(land, "land_area", None)
        land_category = safe_string(getattr(land, "land_category", ""))
        district = safe_string(getattr(land, "district", ""))
        land_use_regulation = safe_string(
            getattr(land, "land_use_regulation", "")
        )
        if zoning:
            result["zone"] = zoning
            result["land_use_zone"] = zoning
        if land_area is not None:
            result["land_area"] = land_area
        if land_category:
            result["land_category"] = land_category
        if district:
            result["district"] = district
        if land_use_regulation:
            result["land_use_regulation"] = land_use_regulation

    return result


def analyze_site_object(
    site: Any,
    project_profile: Optional[Dict[str, str]] = None,
    procedure_profile: Optional[Dict[str, str]] = None,
    production_condition_shadow_sources: Optional[Any] = None,
    historical_rule_input: Optional[Any] = None,
    district_unit_plan_registry_candidate: Optional[Any] = None,
) -> Dict[str, Any]:
    """Convert a Site object into the final SITE Analysis Object.

    Historical and district-unit production inputs must use their typed,
    verified transport envelopes. Raw mappings fail closed here, and each
    envelope is rebound to the PNU derived from the current Site object.
    """
    site_input = site_to_analysis_input(site)

    if historical_rule_input is not None and district_unit_plan_registry_candidate is not None:
        raise ValueError(
            "historical and district-unit verified SITE inputs cannot be combined"
        )

    if district_unit_plan_registry_candidate is not None:
        if not isinstance(
            district_unit_plan_registry_candidate,
            DistrictUnitPlanVerifiedRegistryCandidateEnvelope,
        ) or not district_unit_plan_registry_candidate.ready:
            raise ValueError(
                "verified district-unit registry candidate envelope required"
            )
        if (
            district_unit_plan_registry_candidate.canonical_pnu
            != site_input.get("pnu")
        ):
            raise ValueError(
                "district-unit registry candidate envelope PNU mismatch"
            )

    if historical_rule_input is not None:
        if not isinstance(
            historical_rule_input,
            HistoricalVerifiedRuleInputEnvelope,
        ) or not historical_rule_input.ready:
            raise ValueError("verified historical rule input envelope required")
        if historical_rule_input.canonical_pnu != site_input.get("pnu"):
            raise ValueError("historical rule input envelope PNU mismatch")

    return build_site_analysis(
        site_input=site_input,
        project_profile=project_profile or {},
        procedure_profile=procedure_profile or {},
        production_condition_shadow_sources=production_condition_shadow_sources,
        historical_rule_input=historical_rule_input,
        district_unit_plan_registry_candidate=district_unit_plan_registry_candidate,
    )
