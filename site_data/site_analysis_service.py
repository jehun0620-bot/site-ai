# -*- coding: utf-8 -*-

"""SITE Analysis Service Integration."""

from __future__ import annotations

from typing import Any, Dict, Optional

from law_data.historical_verified_rule_input_envelope import (
    HistoricalVerifiedRuleInputEnvelope,
)
from law_data.site_analysis_builder import build_site_analysis


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
    bun = safe_string(getattr(site, "bun", ""))
    ji = safe_string(getattr(site, "ji", ""))

    pnu = ""
    if (
        len(sigungu_cd) == 5
        and len(bjdong_cd) == 5
        and len(bun) == 4
        and len(ji) == 4
    ):
        # Current Site model has no mountain-lot flag, so land_gbn remains "1".
        pnu = sigungu_cd + bjdong_cd + "1" + bun + ji

    result = {
        "site_id": site_id,
        "address": address,
        "road_address": road_address,
        "sigungu_cd": sigungu_cd,
        "bjdong_cd": bjdong_cd,
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
) -> Dict[str, Any]:
    """Convert a Site object into the final SITE Analysis Object.

    Historical production input must be the typed envelope produced after the
    orchestrator's PNU/authority gates. Raw mappings fail closed here.
    """
    site_input = site_to_analysis_input(site)

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
    )
