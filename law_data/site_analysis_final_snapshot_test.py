# -*- coding: utf-8 -*-

"""
STEP 17-21-C-11-3
Final SITE Analysis Schema Snapshot

목표
======================================================================
build_site_analysis()가 반환하는 최종 SITE ANALYSIS 객체의
schema와 핵심 값을 최종 snapshot으로 고정한다.

검증 대상
======================================================================
1. analysis status
2. SITE identity
3. representative coordinate
4. Parcel spatial payload
5. regulation
6. rule evaluation summary
7. PROJECT / PROCEDURE input requirements
8. external dependencies
9. rule engine metadata

이 snapshot은 이후
- API response
- UI
- AI explanation
- report generation

의 기준 schema가 된다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


from site_analysis_builder import (
    build_site_analysis,
)


STEP_NAME = (
    "STEP 17-21-C-11-3 "
    "Final SITE Analysis Schema Snapshot"
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

OUTPUT_PATH = (
    OUTPUT_DIR
    / "site_analysis_final_snapshot.json"
)


# ============================================================
# util
# ============================================================

def save_json(
    data: Dict[str, Any],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


# ============================================================
# main
# ============================================================

def main() -> int:

    # ========================================================
    # 대표 dynamic scenario
    # ========================================================

    result = (
        build_site_analysis(
            project_profile={
                "공동주택": (
                    "TRUE"
                ),
            },

            procedure_profile={
                "도시계획위원회심의": (
                    "TRUE"
                ),
            },
        )
    )

    analysis = (
        result.get(
            "analysis",
            {},
        )
    )

    site = (
        result.get(
            "site",
            {},
        )
    )

    coordinate = (
        site.get(
            "coordinate",
            {},
        )
    )

    spatial = (
        site.get(
            "spatial",
            {},
        )
    )

    parcel = (
        spatial.get(
            "parcel",
            {},
        )
    )

    parcel_area = (
        parcel.get(
            "area",
            {},
        )
    )

    parcel_source = (
        parcel.get(
            "source",
            {},
        )
    )

    regulation = (
        result.get(
            "regulation",
            {},
        )
    )

    rule_evaluation = (
        result.get(
            "rule_evaluation",
            {},
        )
    )

    input_requirements = (
        result.get(
            "input_requirements",
            {},
        )
    )

    external_dependencies = (
        result.get(
            "external_dependencies",
            {},
        )
    )

    rule_engine = (
        result.get(
            "rule_engine",
            {},
        )
    )

    # ========================================================
    # schema checks
    # ========================================================

    required_top_keys = {
        "analysis",
        "site",
        "input",
        "regulation",
        "rule_evaluation",
        "input_requirements",
        "external_dependencies",
        "rule_engine",
    }

    top_keys = set(
        result.keys()
    )

    missing_top_keys = sorted(
        required_top_keys
        - top_keys
    )

    # ========================================================
    # validation
    # ========================================================

    validations = {

        # ----------------------------------------------------
        # schema
        # ----------------------------------------------------

        "top schema complete": (
            not missing_top_keys
        ),

        # ----------------------------------------------------
        # analysis
        # ----------------------------------------------------

        "analysis ready": (
            analysis.get(
                "status"
            )
            == "READY"
        ),

        "engine": (
            analysis.get(
                "engine"
            )
            == "RULE_EVALUATION_PIPELINE"
        ),

        "engine version exists": (
            analysis.get(
                "engine_version"
            )
            is not None
        ),

        # ----------------------------------------------------
        # identity
        # ----------------------------------------------------

        "site id": (
            site.get(
                "site_id"
            )
            == "11680-10300-0012-0000"
        ),

        "address": (
            site.get(
                "address"
            )
            == (
                "서울특별시 강남구 개포동 12번지"
            )
        ),

        "pnu": (
            site.get(
                "pnu"
            )
            == "1168010300100120000"
        ),

        "sigungu": (
            site.get(
                "sigungu_code"
            )
            == "11680"
        ),

        "bjdong": (
            site.get(
                "bjdong_code"
            )
            == "10300"
        ),

        "main no": (
            site.get(
                "main_no"
            )
            == "0012"
        ),

        "sub no": (
            site.get(
                "sub_no"
            )
            == "0000"
        ),

        "zone": (
            site.get(
                "zone"
            )
            == "제3종일반주거지역"
        ),

        "identity complete": (
            site.get(
                "identity_status"
            )
            == "COMPLETE"
        ),

        # ----------------------------------------------------
        # coordinate
        # ----------------------------------------------------

        "coordinate confirmed": (
            site.get(
                "coordinate_status"
            )
            == "CONFIRMED"
        ),

        "coordinate x": (
            coordinate.get(
                "x"
            )
            == 127.07539280356858
        ),

        "coordinate y": (
            coordinate.get(
                "y"
            )
            == 37.494197498186885
        ),

        "coordinate crs": (
            coordinate.get(
                "crs"
            )
            == "EPSG:4326"
        ),

        # ----------------------------------------------------
        # spatial parcel
        # ----------------------------------------------------

        "parcel pnu": (
            parcel.get(
                "pnu"
            )
            == "1168010300100120000"
        ),

        "parcel geometry loaded": (
            parcel.get(
                "geometry_loaded"
            )
            is True
        ),

        "parcel polygon": (
            parcel.get(
                "geometry_type"
            )
            == "Polygon"
        ),

        "parcel geometry exists": (
            isinstance(
                parcel.get(
                    "geometry"
                ),
                dict,
            )
            and bool(
                parcel.get(
                    "geometry",
                    {},
                ).get(
                    "coordinates"
                )
            )
        ),

        "parcel area": (
            parcel_area.get(
                "value"
            )
            == 120945.65223377591
        ),

        "parcel bounds": (
            parcel.get(
                "bounds"
            )
            == [
                962201.02522,
                1943722.58159,
                962711.06096,
                1944220.16506,
            ]
        ),

        "parcel crs unknown preserved": (
            parcel.get(
                "crs"
            )
            is None
        ),

        "parcel crs status": (
            parcel.get(
                "crs_status"
            )
            == "SOURCE_CRS_NOT_EXPLICIT"
        ),

        "parcel source verified": (
            parcel_source.get(
                "verified"
            )
            is True
        ),

        # ----------------------------------------------------
        # regulation
        # ----------------------------------------------------

        "BCR 50": (
            regulation.get(
                "building_coverage_ratio",
                {},
            ).get(
                "value"
            )
            == 50.0
        ),

        "BCR confirmed": (
            regulation.get(
                "building_coverage_ratio",
                {},
            ).get(
                "status"
            )
            == "CONFIRMED"
        ),

        "FAR 250": (
            regulation.get(
                "floor_area_ratio",
                {},
            ).get(
                "value"
            )
            == 250.0
        ),

        "FAR confirmed": (
            regulation.get(
                "floor_area_ratio",
                {},
            ).get(
                "status"
            )
            == "CONFIRMED"
        ),

        "numeric resolution": (
            regulation.get(
                "numeric_resolution"
            )
            == "BASE_VALUES_RETAINED"
        ),

        "direct relaxation zero": (
            regulation.get(
                "direct_relaxation_count"
            )
            == 0
        ),

        # ----------------------------------------------------
        # rule evaluation
        # ----------------------------------------------------

        "rules total 314": (
            rule_evaluation.get(
                "total"
            )
            == 314
        ),

        "rules applicable 63": (
            rule_evaluation.get(
                "applicable"
            )
            == 63
        ),

        "rules not applicable 213": (
            rule_evaluation.get(
                "not_applicable"
            )
            == 213
        ),

        "rules conditional 36": (
            rule_evaluation.get(
                "conditional"
            )
            == 36
        ),

        "rules unknown 2": (
            rule_evaluation.get(
                "unknown"
            )
            == 2
        ),

        # ----------------------------------------------------
        # remaining inputs
        # ----------------------------------------------------

        "project requirements exist": (
            input_requirements.get(
                "project_count",
                0,
            )
            > 0
        ),

        "procedure requirements exist": (
            input_requirements.get(
                "procedure_count",
                0,
            )
            > 0
        ),

        "additional input required": (
            input_requirements.get(
                "requires_additional_input"
            )
            is True
        ),

        # ----------------------------------------------------
        # external dependency
        # ----------------------------------------------------

        "external dependency one": (
            external_dependencies.get(
                "count"
            )
            == 1
        ),

        "historical dependency pending": (
            bool(
                external_dependencies.get(
                    "items"
                )
            )
            and external_dependencies[
                "items"
            ][
                0
            ].get(
                "automation_state"
            )
            == "HISTORICAL_SOURCE_PENDING"
        ),

        "historical dependency not blocking": (
            bool(
                external_dependencies.get(
                    "items"
                )
            )
            and external_dependencies[
                "items"
            ][
                0
            ].get(
                "blocking_analysis"
            )
            is False
        ),

        # ----------------------------------------------------
        # rule engine debug payload
        # ----------------------------------------------------

        "rule engine baseline exists": (
            rule_engine.get(
                "baseline"
            )
            is not None
        ),

        "rule engine branch exists": (
            rule_engine.get(
                "branch_overlay"
            )
            is not None
        ),

        "rule engine dynamic exists": (
            rule_engine.get(
                "dynamic_injection"
            )
            is not None
        ),

        "rule engine numeric exists": (
            rule_engine.get(
                "numeric"
            )
            is not None
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # compact schema description
    # ========================================================

    schema = {
        "analysis": [
            "status",
            "engine",
            "engine_version",
        ],

        "site": [
            "site_id",
            "address",
            "road_address",
            "pnu",
            "sigungu_code",
            "bjdong_code",
            "main_no",
            "sub_no",
            "zone",
            "coordinate",
            "spatial",
        ],

        "regulation": [
            "building_coverage_ratio",
            "floor_area_ratio",
            "numeric_resolution",
            "direct_relaxation_count",
        ],

        "rule_evaluation": [
            "total",
            "applicable",
            "not_applicable",
            "conditional",
            "unknown",
        ],

        "input_requirements": [
            "project",
            "procedure",
            "project_count",
            "procedure_count",
            "requires_additional_input",
        ],

        "external_dependencies": [
            "count",
            "items",
        ],

        "rule_engine": [
            "baseline",
            "branch_overlay",
            "dynamic_injection",
            "site_registry",
            "site_repairs",
            "numeric",
        ],
    }

    # ========================================================
    # output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "schema_version": (
            "C-11-3-v1"
        ),

        "schema": (
            schema
        ),

        "analysis_object": (
            result
        ),

        "validations": (
            validations
        ),

        "all_pass": (
            all_pass
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "Schema version:",
        "C-11-3-v1",
    )

    print(
        "Analysis status:",
        analysis.get(
            "status"
        ),
    )

    print()

    print(
        "SITE:",
        site.get(
            "site_id"
        ),
    )

    print(
        "Address:",
        site.get(
            "address"
        ),
    )

    print(
        "PNU:",
        site.get(
            "pnu"
        ),
    )

    print(
        "Zone:",
        site.get(
            "zone"
        ),
    )

    print()

    print(
        "Coordinate:",
        coordinate,
    )

    print()

    print(
        "Parcel geometry:",
        parcel.get(
            "geometry_type"
        ),
    )

    print(
        "Parcel area:",
        parcel_area.get(
            "value"
        ),
    )

    print(
        "Parcel bounds:",
        parcel.get(
            "bounds"
        ),
    )

    print(
        "Parcel CRS status:",
        parcel.get(
            "crs_status"
        ),
    )

    print()

    print(
        "BCR:",
        regulation.get(
            "building_coverage_ratio",
            {},
        ).get(
            "value"
        ),
    )

    print(
        "FAR:",
        regulation.get(
            "floor_area_ratio",
            {},
        ).get(
            "value"
        ),
    )

    print()

    print(
        "Rules:",
        rule_evaluation,
    )

    print()

    print(
        "Remaining PROJECT:",
        input_requirements.get(
            "project_count"
        ),
    )

    print(
        "Remaining PROCEDURE:",
        input_requirements.get(
            "procedure_count"
        ),
    )

    print()

    print(
        "External dependencies:",
        external_dependencies.get(
            "count"
        ),
    )

    print()

    print(
        "Missing top keys:",
        missing_top_keys,
    )

    print()

    print(
        "all_pass:",
        all_pass,
    )

    if not all_pass:

        print()
        print(
            "FAILED:"
        )

        for name, passed in (
            validations.items()
        ):

            if not passed:

                print(
                    "-",
                    name,
                )

    print()

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return (
        0
        if all_pass
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )