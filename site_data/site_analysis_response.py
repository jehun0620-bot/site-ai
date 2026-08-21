# -*- coding: utf-8 -*-

"""
STEP 17-21-C-12-3
SITE Analysis JSON-safe API Response Builder

목표
======================================================================
Final SITE Analysis Object를
API / UI / Report가 사용할 안정적인 공개 응답으로 변환한다.

원칙
======================================================================
1. JSON serialization 가능
2. 내부 rule_engine debug payload는 기본적으로 제외
3. API schema version 명시
4. 핵심 SITE / 면적 / 규제 / rule summary 보존
5. 필요 시 debug=True로 내부 engine payload 포함 가능
"""

from __future__ import annotations

import math

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict


API_SCHEMA_VERSION = (
    "SITE_ANALYSIS_API_V1"
)


# ============================================================
# JSON safe conversion
# ============================================================

def to_json_safe(
    value: Any,
) -> Any:

    if value is None:

        return None

    if isinstance(
        value,
        (
            str,
            bool,
            int,
        ),
    ):

        return value

    if isinstance(
        value,
        float,
    ):

        if not math.isfinite(
            value
        ):

            return None

        return value

    if isinstance(
        value,
        Decimal,
    ):

        return float(
            value
        )

    if isinstance(
        value,
        Path,
    ):

        return str(
            value
        )

    if isinstance(
        value,
        (
            datetime,
            date,
        ),
    ):

        return value.isoformat()

    if is_dataclass(
        value
    ):

        return to_json_safe(
            asdict(
                value
            )
        )

    if isinstance(
        value,
        dict,
    ):

        return {
            str(
                key
            ): to_json_safe(
                item
            )

            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):

        return [
            to_json_safe(
                item
            )
            for item
            in value
        ]

    return str(
        value
    )


# ============================================================
# public response
# ============================================================

def build_site_analysis_response(
    analysis: Dict[str, Any],
    *,
    include_debug: bool = False,
) -> Dict[str, Any]:

    site = (
        analysis.get(
            "site",
            {},
        )
    )

    land_area = (
        analysis.get(
            "land_area",
            {},
        )
    )

    regulation = (
        analysis.get(
            "regulation",
            {},
        )
    )

    rule_evaluation = (
        analysis.get(
            "rule_evaluation",
            {},
        )
    )

    requirements = (
        analysis.get(
            "input_requirements",
            {},
        )
    )

    dependencies = (
        analysis.get(
            "external_dependencies",
            {},
        )
    )

    analysis_meta = (
        analysis.get(
            "analysis",
            {},
        )
    )

    # ========================================================
    # public payload
    # ========================================================

    response = {

        "schema_version": (
            API_SCHEMA_VERSION
        ),

        "status": (
            analysis_meta.get(
                "status"
            )
        ),

        "site": {
            "site_id": (
                site.get(
                    "site_id"
                )
            ),

            "address": (
                site.get(
                    "address"
                )
            ),

            "road_address": (
                site.get(
                    "road_address"
                )
            ),

            "pnu": (
                site.get(
                    "pnu"
                )
            ),

            "sigungu_code": (
                site.get(
                    "sigungu_code"
                )
            ),

            "bjdong_code": (
                site.get(
                    "bjdong_code"
                )
            ),

            "main_no": (
                site.get(
                    "main_no"
                )
            ),

            "sub_no": (
                site.get(
                    "sub_no"
                )
            ),

            "zone": (
                site.get(
                    "zone"
                )
            ),

            "coordinate": (
                site.get(
                    "coordinate"
                )
            ),

            "identity_status": (
                site.get(
                    "identity_status"
                )
            ),
        },

        "land_area": (
            land_area
        ),

        "spatial": (
            site.get(
                "spatial",
                {}
            )
        ),

        "regulation": (
            regulation
        ),

        "rule_evaluation": (
            rule_evaluation
        ),

        "requirements": {
            "project": (
                requirements.get(
                    "project",
                    []
                )
            ),

            "procedure": (
                requirements.get(
                    "procedure",
                    []
                )
            ),

            "project_count": (
                requirements.get(
                    "project_count",
                    0,
                )
            ),

            "procedure_count": (
                requirements.get(
                    "procedure_count",
                    0,
                )
            ),

            "requires_additional_input": (
                requirements.get(
                    "requires_additional_input",
                    False,
                )
            ),
        },

        "external_dependencies": (
            dependencies
        ),
    }

    # ========================================================
    # optional debug payload
    # ========================================================

    if include_debug:

        response[
            "debug"
        ] = {
            "engine": (
                analysis_meta.get(
                    "engine"
                )
            ),

            "engine_version": (
                analysis_meta.get(
                    "engine_version"
                )
            ),

            "input": (
                analysis.get(
                    "input"
                )
            ),

            "rule_engine": (
                analysis.get(
                    "rule_engine"
                )
            ),
        }

    return to_json_safe(
        response
    )