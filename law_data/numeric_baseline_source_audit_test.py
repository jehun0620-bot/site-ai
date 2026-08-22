# -*- coding: utf-8 -*-

"""
STEP 17-21-C-13-4A
Dynamic Numeric Baseline Source Audit

목표
======================================================================
현재 BCR=50 / FAR=250이 어떤 source에서 고정되어 들어오는지 추적한다.

검사 대상
======================================================================
1. base_numeric_regulation_hierarchy.json
2. rule_evaluation_pipeline 결과
3. build_site_analysis 결과
4. 서로 다른 zone 입력 비교

이번 단계에서는 값을 수정하지 않는다.
source와 propagation path만 확인한다.
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any, Dict


from site_data.site_data_model import (
    Land,
    Site,
)

from site_data.site_analysis_service import (
    analyze_site_object,
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

BASE_NUMERIC_PATH = (
    OUTPUT_DIR
    / "base_numeric_regulation_hierarchy.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "numeric_baseline_source_audit.json"
)


# ============================================================
# util
# ============================================================

def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():

        return {}

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


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
# test SITE
# ============================================================

def build_site(
    *,
    site_id: str,
    bun: str,
    zone: str,
) -> Site:

    site = Site(
        site_id=(
            site_id
        ),

        address=(
            f"SYNTHETIC {zone}"
        ),

        road_address=(
            f"SYNTHETIC ROAD {zone}"
        ),

        sigungu_cd=(
            "11680"
        ),

        bjdong_cd=(
            "10300"
        ),

        bun=(
            bun
        ),

        ji=(
            "0000"
        ),
    )

    site.land = Land(
        land_area=(
            1000.0
        ),

        land_category=(
            "대"
        ),

        zoning=(
            zone
        ),
    )

    return site


# ============================================================
# analysis snapshot
# ============================================================

def analyze(
    site: Site,
) -> Dict[str, Any]:

    result = (
        analyze_site_object(
            site=(
                site
            ),

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

    return {

        "site": {
            "site_id": (
                result.get(
                    "site",
                    {},
                ).get(
                    "site_id"
                )
            ),

            "pnu": (
                result.get(
                    "site",
                    {},
                ).get(
                    "pnu"
                )
            ),

            "zone": (
                result.get(
                    "site",
                    {},
                ).get(
                    "zone"
                )
            ),
        },

        "regulation": (
            result.get(
                "regulation",
                {}
            )
        ),

        "rule_engine_numeric": (
            result.get(
                "rule_engine",
                {},
            ).get(
                "numeric"
            )
        ),
    }


# ============================================================
# recursive numeric source search
# ============================================================

def walk(
    obj: Any,
    path: str = "$",
):

    yield (
        path,
        obj,
    )

    if isinstance(
        obj,
        dict,
    ):

        for key, value in (
            obj.items()
        ):

            yield from walk(
                value,
                f"{path}.{key}",
            )

    elif isinstance(
        obj,
        list,
    ):

        for index, value in enumerate(
            obj
        ):

            yield from walk(
                value,
                f"{path}[{index}]",
            )


def find_numeric_hits(
    data: Any,
) -> Dict[str, Any]:

    hits_50 = []
    hits_250 = []

    for path, value in walk(
        data
    ):

        if isinstance(
            value,
            (
                int,
                float,
            ),
        ):

            if float(
                value
            ) == 50.0:

                hits_50.append(
                    path
                )

            if float(
                value
            ) == 250.0:

                hits_250.append(
                    path
                )

    return {
        "50": (
            hits_50
        ),

        "250": (
            hits_250
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    base_numeric = load_json(
        BASE_NUMERIC_PATH
    )

    # --------------------------------------------------------
    # 서로 다른 용도지역
    # --------------------------------------------------------

    sites = {

        "R3": build_site(
            site_id=(
                "11680-10300-0012-0000"
            ),

            bun=(
                "0012"
            ),

            zone=(
                "제3종일반주거지역"
            ),
        ),

        "COMMERCIAL": build_site(
            site_id=(
                "11680-10300-0013-0000"
            ),

            bun=(
                "0013"
            ),

            zone=(
                "일반상업지역"
            ),
        ),

        "NATURAL_GREEN": build_site(
            site_id=(
                "11680-10300-0014-0000"
            ),

            bun=(
                "0014"
            ),

            zone=(
                "자연녹지지역"
            ),
        ),
    }

    analyses = {
        name: analyze(
            site
        )
        for name, site
        in sites.items()
    }

    # --------------------------------------------------------
    # numeric comparison
    # --------------------------------------------------------

    comparisons = {}

    for name, result in (
        analyses.items()
    ):

        regulation = (
            result[
                "regulation"
            ]
        )

        comparisons[
            name
        ] = {

            "zone": (
                result[
                    "site"
                ][
                    "zone"
                ]
            ),

            "bcr": (
                regulation.get(
                    "building_coverage_ratio",
                    {},
                ).get(
                    "value"
                )
            ),

            "far": (
                regulation.get(
                    "floor_area_ratio",
                    {},
                ).get(
                    "value"
                )
            ),

            "resolution": (
                regulation.get(
                    "numeric_resolution"
                )
            ),
        }

    unique_bcr = {
        item[
            "bcr"
        ]
        for item
        in comparisons.values()
    }

    unique_far = {
        item[
            "far"
        ]
        for item
        in comparisons.values()
    }

    # --------------------------------------------------------
    # source evidence
    # --------------------------------------------------------

    base_hits = (
        find_numeric_hits(
            base_numeric
        )
    )

    engine_hits = {
        name: find_numeric_hits(
            result.get(
                "rule_engine_numeric"
            )
        )
        for name, result
        in analyses.items()
    }

    baseline_fixed = (
        len(
            unique_bcr
        )
        == 1
        and len(
            unique_far
        )
        == 1
    )

    resolution = (
        "STATIC_BASELINE_CONFIRMED"
        if baseline_fixed
        else "DYNAMIC_BASELINE_PRESENT"
    )

    output = {

        "step": (
            "STEP 17-21-C-13-4A "
            "Dynamic Numeric Baseline Source Audit"
        ),

        "base_numeric_path": (
            str(
                BASE_NUMERIC_PATH
            )
        ),

        "base_numeric": (
            base_numeric
        ),

        "base_numeric_hits": (
            base_hits
        ),

        "analyses": (
            analyses
        ),

        "comparisons": (
            comparisons
        ),

        "engine_numeric_hits": (
            engine_hits
        ),

        "unique_bcr": (
            sorted(
                unique_bcr,
                key=lambda value: str(
                    value
                ),
            )
        ),

        "unique_far": (
            sorted(
                unique_far,
                key=lambda value: str(
                    value
                ),
            )
        ),

        "baseline_fixed": (
            baseline_fixed
        ),

        "resolution": (
            resolution
        ),

        "probe_pass": True,
    }

    save_json(
        output
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "=== BASE NUMERIC SNAPSHOT ==="
    )

    print(
        "SITE zone:",
        base_numeric.get(
            "site_zone"
        ),
    )

    print(
        "Base BCR:",
        base_numeric.get(
            "base_bcr"
        ),
    )

    print(
        "Base FAR:",
        base_numeric.get(
            "base_far"
        ),
    )

    print()

    print(
        "50 hits:",
        base_hits[
            "50"
        ],
    )

    print(
        "250 hits:",
        base_hits[
            "250"
        ],
    )

    print()

    print(
        "=== ZONE COMPARISON ==="
    )

    for name, item in (
        comparisons.items()
    ):

        print(
            f"{name}: "
            f"zone={item['zone']} "
            f"| BCR={item['bcr']} "
            f"| FAR={item['far']} "
            f"| resolution={item['resolution']}"
        )

    print()

    print(
        "Unique BCR:",
        unique_bcr,
    )

    print(
        "Unique FAR:",
        unique_far,
    )

    print()

    print(
        "Baseline fixed:",
        baseline_fixed,
    )

    print(
        "Resolution:",
        resolution,
    )

    print()

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    print()

    print(
        "probe_pass:",
        True,
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )