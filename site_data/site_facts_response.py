# -*- coding: utf-8 -*-
"""Public SITE facts response builder.

This module only projects already-canonical Site facts into the public
SITE_ANALYSIS_API_V1 shape. It does not resolve providers, verify PNU,
or make legal applicability decisions.
"""
from __future__ import annotations

from typing import Any, Dict


def build_site_facts_response(site_object: Any = None) -> Dict[str, Any]:
    land_object = (
        getattr(site_object, "land", None)
        if site_object is not None
        else None
    )
    building_objects = (
        list(getattr(site_object, "buildings", []) or [])
        if site_object is not None
        else []
    )

    return {
        "land": {
            "land_category": (
                getattr(land_object, "land_category", "")
                if land_object is not None
                else ""
            ),
            "land_area": (
                getattr(land_object, "land_area", None)
                if land_object is not None
                else None
            ),
            "zoning": (
                getattr(land_object, "zoning", "")
                if land_object is not None
                else ""
            ),
        },
        "buildings": {
            "count": len(building_objects),
            "items": [
                {
                    "management_id": getattr(
                        building, "management_id", None
                    ),
                    "dong_name": getattr(building, "dong_name", ""),
                    "building_name": getattr(
                        building, "building_name", ""
                    ),
                    "main_use": getattr(building, "main_use", ""),
                    "land_area": getattr(building, "land_area", None),
                    "building_area": getattr(
                        building, "building_area", None
                    ),
                    "total_floor_area": getattr(
                        building, "total_floor_area", None
                    ),
                    "building_coverage_ratio": getattr(
                        building, "building_coverage_ratio", None
                    ),
                    "floor_area_ratio": getattr(
                        building, "floor_area_ratio", None
                    ),
                    "ground_floor_count": getattr(
                        building, "ground_floor_count", None
                    ),
                    "underground_floor_count": getattr(
                        building, "underground_floor_count", None
                    ),
                    "household_count": getattr(
                        building, "household_count", None
                    ),
                    "approval_date": getattr(
                        building, "approval_date", ""
                    ),
                }
                for building in building_objects
            ],
        },
        "sources": {
            "land": (
                "VWORLD_LAND_CHARACTERISTICS"
                if land_object is not None
                else None
            ),
            "land_status": (
                getattr(site, "land_provider_status", "") or None
                if site is not None
                else None
            ),
            "land_retryable": (
                bool(getattr(site, "land_provider_retryable", False))
                if site is not None
                else False
            ),
            "land_reference_year": (
                getattr(
                    land_object,
                    "source_reference_year",
                    None,
                )
                if land_object is not None
                else None
            ),
            "land_last_updated_at": (
                getattr(
                    land_object,
                    "source_last_updated_at",
                    None,
                )
                if land_object is not None
                else None
            ),
            "buildings": (
                "BUILDING_HUB_TITLE"
                if building_objects
                else None
            ),
        },
    }
