# -*- coding: utf-8 -*-

"""
STEP 17-21-C-11
SITE Analysis Object Builder

목표
======================================================================
SITE 정보와 reusable Rule Evaluation Engine 결과를 결합하여
서비스 / AI 설명 / 보고서 / UI가 직접 사용할 수 있는
단일 SITE ANALYSIS 객체를 생성한다.

중요
======================================================================
이 모듈 이후 상위 서비스는 개별 law_data/output JSON을
직접 해석하지 않는다.

상위 서비스는 원칙적으로:

    build_site_analysis()

결과만 사용한다.
"""

from __future__ import annotations

import copy
import json

from pathlib import Path
from typing import Any, Dict, Optional


try:
    from .rule_evaluation_pipeline import (
        evaluate_site_rules,
    )

    from .site_identity_resolver import (
        resolve_site_identity,
    )

    from .site_spatial_payload_resolver import (
        resolve_site_spatial_payload,
    )

except ImportError:
    from rule_evaluation_pipeline import (
        evaluate_site_rules,
    )

    from site_identity_resolver import (
        resolve_site_identity,
    )

    from site_spatial_payload_resolver import (
        resolve_site_spatial_payload,
    )

# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

SITE_COMPLETE_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_site_complete.json"
)

BASE_NUMERIC_PATH = (
    OUTPUT_DIR
    / "base_numeric_regulation_hierarchy.json"
)


# ============================================================
# util
# ============================================================

def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():

        raise FileNotFoundError(
            f"입력 파일 없음: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()

# ============================================================
# land area reconciliation
# ============================================================

def build_land_area_result(
    site_input: Dict[str, Any],
    site: Dict[str, Any],
) -> Dict[str, Any]:

    official_area = (
        site_input.get(
            "land_area"
        )
    )

    parcel = (
        site.get(
            "spatial",
            {},
        ).get(
            "parcel",
            {},
        )
    )

    spatial_area = (
        parcel.get(
            "area",
            {},
        ).get(
            "value"
        )
    )

    difference = None
    difference_ratio = None

    if (
        official_area is not None
        and spatial_area is not None
    ):

        difference = (
            float(official_area)
            - float(spatial_area)
        )

        if float(official_area) != 0:

            difference_ratio = (
                abs(
                    difference
                )
                / float(official_area)
                * 100.0
            )

    return {

        "official": {
            "value": (
                official_area
            ),

            "unit": (
                "square_meter"
            ),

            "source": (
                "VWORLD_LAND_CHARACTERISTICS"
            ),

            "role": (
                "LEGAL_OR_ATTRIBUTE_LAND_AREA"
            ),
        },

        "spatial": {
            "value": (
                spatial_area
            ),

            "unit": (
                "native_crs_square_units"
            ),

            "source": (
                "MAPPLAN_PARCEL_GEOMETRY"
            ),

            "role": (
                "SPATIAL_GEOMETRY_AREA"
            ),

            "crs": (
                parcel.get(
                    "crs"
                )
            ),

            "crs_status": (
                parcel.get(
                    "crs_status"
                )
            ),
        },

        "difference": {
            "value": (
                difference
            ),

            "ratio_percent": (
                difference_ratio
            ),
        },

        "resolution": (
            "KEEP_BOTH_WITH_SOURCE_ROLES"
        ),

        "primary": (
            "official"
        ),
    }

# ============================================================
# regulation result
# ============================================================

def build_regulation_result(
    engine_result: Dict[str, Any],
) -> Dict[str, Any]:

    numeric = (
        engine_result.get(
            "numeric",
            {},
        )
    )

    return {
        "building_coverage_ratio": {
            "value": (
                numeric.get(
                    "building_coverage_ratio"
                )
            ),

            "unit": (
                "percent"
            ),

            "status": (
                "CONFIRMED"
                if numeric.get(
                    "building_coverage_ratio"
                )
                is not None
                else "PENDING"
            ),
        },

        "floor_area_ratio": {
            "value": (
                numeric.get(
                    "floor_area_ratio"
                )
            ),

            "unit": (
                "percent"
            ),

            "status": (
                "CONFIRMED"
                if numeric.get(
                    "floor_area_ratio"
                )
                is not None
                else "PENDING"
            ),
        },

        "numeric_resolution": (
            numeric.get(
                "resolution"
            )
        ),

        "direct_relaxation_count": (
            numeric.get(
                "direct_relaxation_count",
                0,
            )
        ),

        "numeric_active_before_guard": (
            numeric.get(
                "active_before_guard",
                0,
            )
        ),

        "numeric_excluded_count": (
            numeric.get(
                "excluded_count",
                0,
            )
        ),

        "numeric_retained_count": (
            numeric.get(
                "retained_count",
                0,
            )
        ),
    }


# ============================================================
# rule summary
# ============================================================

def build_rule_summary(
    engine_result: Dict[str, Any],
) -> Dict[str, Any]:

    summary = (
        engine_result.get(
            "rule_summary",
            {},
        )
    )

    applicable = int(
        summary.get(
            "APPLICABLE",
            0,
        )
        or 0
    )

    not_applicable = int(
        summary.get(
            "NOT_APPLICABLE",
            0,
        )
        or 0
    )

    conditional = int(
        summary.get(
            "CONDITIONAL",
            0,
        )
        or 0
    )

    unknown = int(
        summary.get(
            "UNKNOWN",
            0,
        )
        or 0
    )

    return {
        "total": (
            applicable
            + not_applicable
            + conditional
            + unknown
        ),

        "applicable": (
            applicable
        ),

        "not_applicable": (
            not_applicable
        ),

        "conditional": (
            conditional
        ),

        "unknown": (
            unknown
        ),
    }


# ============================================================
# input requirements
# ============================================================

def build_input_requirements(
    engine_result: Dict[str, Any],
) -> Dict[str, Any]:

    remaining = (
        engine_result.get(
            "remaining_inputs",
            {},
        )
    )

    project = copy.deepcopy(
        remaining.get(
            "project",
            [],
        )
    )

    procedure = copy.deepcopy(
        remaining.get(
            "procedure",
            [],
        )
    )

    return {
        "project": (
            project
        ),

        "procedure": (
            procedure
        ),

        "project_count": (
            len(
                project
            )
        ),

        "procedure_count": (
            len(
                procedure
            )
        ),

        "requires_additional_input": (
            bool(
                project
                or procedure
            )
        ),
    }


# ============================================================
# external dependency
# ============================================================

def build_external_dependencies(
    engine_result: Dict[str, Any],
) -> Dict[str, Any]:

    dependencies = copy.deepcopy(
        engine_result.get(
            "external_dependencies",
            {},
        )
    )

    historical = (
        dependencies.get(
            "historical",
            {},
        )
    )

    active = []

    if historical:

        active.append(
            {
                "category": (
                    "SITE_HISTORY"
                ),

                "condition": (
                    historical.get(
                        "condition"
                    )
                ),

                "status": (
                    historical.get(
                        "status"
                    )
                ),

                "confidence": (
                    historical.get(
                        "confidence"
                    )
                ),

                "automation_state": (
                    historical.get(
                        "automation_state"
                    )
                ),

                "blocking_analysis": (
                    historical.get(
                        "blocking_site_stage",
                        False,
                    )
                ),
            }
        )

    return {
        "count": (
            len(
                active
            )
        ),

        "items": (
            active
        ),
    }


# ============================================================
# analysis status
# ============================================================

def determine_analysis_status(
    engine_result: Dict[str, Any],
    regulation: Dict[str, Any],
) -> str:

    engine_ready = (
        engine_result.get(
            "pipeline",
            {},
        ).get(
            "ready"
        )
        is True
    )

    bcr_confirmed = (
        regulation.get(
            "building_coverage_ratio",
            {},
        ).get(
            "status"
        )
        == "CONFIRMED"
    )

    far_confirmed = (
        regulation.get(
            "floor_area_ratio",
            {},
        ).get(
            "status"
        )
        == "CONFIRMED"
    )

    if (
        engine_ready
        and bcr_confirmed
        and far_confirmed
    ):

        return (
            "READY"
        )

    if engine_ready:

        return (
            "PARTIAL"
        )

    return (
        "NOT_READY"
    )


# ============================================================
# public API
# ============================================================

def build_site_analysis(
    project_profile: Optional[
        Dict[str, str]
    ] = None,
    procedure_profile: Optional[
        Dict[str, str]
    ] = None,
    site_input: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:

    project_profile = (
        project_profile
        or {}
    )

    procedure_profile = (
        procedure_profile
        or {}
    )

    site_input = (
        site_input
        or {}
    )

    # ========================================================
    # source
    # ========================================================

    site_complete = load_json(
        SITE_COMPLETE_PATH
    )

    base_numeric = load_json(
        BASE_NUMERIC_PATH
    )

    # ========================================================
    # rule engine
    # ========================================================

    engine_result = (
        evaluate_site_rules(
            project_profile=(
                project_profile
            ),

            procedure_profile=(
                procedure_profile
            ),
        )
    )

    # ========================================================
    # base SITE
    # ========================================================

    base_site = copy.deepcopy(
        site_complete.get(
            "site",
            {},
        )
    )

    # --------------------------------------------------------
    # zone fallback
    # --------------------------------------------------------

    if not safe_string(
        base_site.get(
            "zone"
        )
    ):

        base_site[
            "zone"
        ] = (
            base_numeric.get(
                "site_zone"
            )
        )

    if not safe_string(
        base_site.get(
            "land_use_zone"
        )
    ):

        base_site[
            "land_use_zone"
        ] = (
            base_numeric.get(
                "site_zone"
            )
        )

    # ========================================================
    # resolved SITE identity
    #
    # priority:
    # 1. caller/site_builder input
    # 2. clean SITE baseline
    # 3. spatial query context / parcel probe
    # ========================================================

    site = resolve_site_identity(
        base_site=(
            base_site
        ),

        site_input=(
            site_input
        ),
    )

    spatial = (
        resolve_site_spatial_payload()
    )

    site[
        "spatial"
    ] = (
        spatial
    )

    land_area = (
    build_land_area_result(
        site_input=(
            site_input
        ),

        site=(
            site
        ),
    )
)
    # ========================================================
    # regulation
    # ========================================================

    regulation = (
        build_regulation_result(
            engine_result
        )
    )

    # ========================================================
    # rule summary
    # ========================================================

    rule_summary = (
        build_rule_summary(
            engine_result
        )
    )

    # ========================================================
    # input requirements
    # ========================================================

    input_requirements = (
        build_input_requirements(
            engine_result
        )
    )

    # ========================================================
    # external dependency
    # ========================================================

    external_dependencies = (
        build_external_dependencies(
            engine_result
        )
    )

    # ========================================================
    # final status
    # ========================================================

    analysis_status = (
        determine_analysis_status(
            engine_result=(
                engine_result
            ),

            regulation=(
                regulation
            ),
        )
    )

    # ========================================================
    # final object
    # ========================================================

    return {

        "analysis": {
            "status": (
                analysis_status
            ),

            "engine": (
                "RULE_EVALUATION_PIPELINE"
            ),

            "engine_version": (
                engine_result.get(
                    "pipeline",
                    {},
                ).get(
                    "version"
                )
            ),
        },

        "site": (
            site
        ),

        "input": {
            "site": (
                copy.deepcopy(
                    site_input
                )
            ),

            "project": (
                copy.deepcopy(
                    project_profile
                )
            ),

            "procedure": (
                copy.deepcopy(
                    procedure_profile
                )
            ),
        },

        "land_area": (
             land_area
        ),
        
        "regulation": (
            regulation
        ),

        "rule_evaluation": (
            rule_summary
        ),

        "input_requirements": (
            input_requirements
        ),

        "external_dependencies": (
            external_dependencies
        ),

        # ----------------------------------------------------
        # 아래는 향후 보고서 / 디버깅 / evidence 확인용
        # ----------------------------------------------------

        "rule_engine": {
            "baseline": (
                engine_result.get(
                    "baseline"
                )
            ),

            "branch_overlay": (
                engine_result.get(
                    "branch_overlay"
                )
            ),

            "dynamic_injection": (
                engine_result.get(
                    "dynamic_injection"
                )
            ),

            "site_registry": (
                engine_result.get(
                    "site_registry"
                )
            ),

            "site_repairs": (
                engine_result.get(
                    "site_repairs"
                )
            ),

            "numeric": (
                engine_result.get(
                    "numeric"
                )
            ),
        },
    }