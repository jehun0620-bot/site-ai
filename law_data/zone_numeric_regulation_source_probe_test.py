# -*- coding: utf-8 -*-

"""
STEP 17-21-C-13-4B
Zone Numeric Regulation Source Probe

목표
======================================================================
기존 법규 rule dataset에서 용도지역별 기본 건폐율 / 용적률 기준을
자동으로 만들 수 있는 source clause를 찾는다.

이번 단계에서는 실제 baseline을 변경하지 않는다.

확인 대상
======================================================================
- 제1종전용주거지역
- 제2종전용주거지역
- 제1종일반주거지역
- 제2종일반주거지역
- 제3종일반주거지역
- 준주거지역
- 중심상업지역
- 일반상업지역
- 근린상업지역
- 유통상업지역
- 전용공업지역
- 일반공업지역
- 준공업지역
- 보전녹지지역
- 생산녹지지역
- 자연녹지지역

출력
======================================================================
각 zone 문자열이 등장하는 clause
numeric values
rule title
법령명
조문 path
건폐율 / 용적률 effect
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any, Dict, List


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
    / "zone_numeric_regulation_source_probe.json"
)


# ============================================================
# candidate source files
# ============================================================

CANDIDATE_FILES = [

    OUTPUT_DIR
    / "numeric_semantic_override_finalize.json",

    OUTPUT_DIR
    / "site_rule_evaluation_site_complete.json",

    OUTPUT_DIR
    / "rule_engine_final_snapshot.json",

    OUTPUT_DIR
    / "rule_evaluation_clean_pipeline.json",
]


# ============================================================
# zone names
# ============================================================

ZONES = [

    "제1종전용주거지역",
    "제2종전용주거지역",

    "제1종일반주거지역",
    "제2종일반주거지역",
    "제3종일반주거지역",

    "준주거지역",

    "중심상업지역",
    "일반상업지역",
    "근린상업지역",
    "유통상업지역",

    "전용공업지역",
    "일반공업지역",
    "준공업지역",

    "보전녹지지역",
    "생산녹지지역",
    "자연녹지지역",
]


# ============================================================
# util
# ============================================================

def load_json(
    path: Path,
) -> Any:

    if not path.exists():

        return None

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


def compact_text(
    value: Any,
    limit: int = 700,
) -> str:

    if isinstance(
        value,
        str,
    ):

        text = value

    else:

        try:

            text = json.dumps(
                value,
                ensure_ascii=False,
                default=str,
            )

        except Exception:

            text = str(
                value
            )

    text = (
        text
        .replace(
            "\r",
            " "
        )
        .replace(
            "\n",
            " "
        )
    )

    if len(
        text
    ) > limit:

        text = (
            text[
                :limit
            ]
            + "..."
        )

    return text


# ============================================================
# candidate detection
# ============================================================

def score_candidate(
    text: str,
) -> int:

    score = 0

    lower = (
        text.lower()
    )

    if (
        "건폐율"
        in text
    ):

        score += 20

    if (
        "용적률"
        in text
    ):

        score += 20

    if (
        "용도지역"
        in text
    ):

        score += 15

    if (
        "최대한도"
        in text
        or "이하"
        in text
    ):

        score += 10

    if (
        "서울특별시 도시계획 조례"
        in text
    ):

        score += 20

    if (
        "building_coverage_ratio"
        in lower
    ):

        score += 15

    if (
        "floor_area_ratio"
        in lower
    ):

        score += 15

    if (
        "numeric"
        in lower
    ):

        score += 5

    return score


def search_file(
    path: Path,
    data: Any,
) -> List[
    Dict[str, Any]
]:

    hits = []

    for obj_path, obj in walk(
        data
    ):

        # 너무 작은 scalar는 제외
        if isinstance(
            obj,
            (
                int,
                float,
                bool,
            ),
        ):

            continue

        preview = compact_text(
            obj
        )

        matched_zones = [
            zone
            for zone
            in ZONES
            if zone
            in preview
        ]

        if not matched_zones:

            continue

        score = (
            score_candidate(
                preview
            )
            + len(
                matched_zones
            )
            * 10
        )

        hits.append(
            {
                "file": (
                    path.name
                ),

                "path": (
                    obj_path
                ),

                "zones": (
                    matched_zones
                ),

                "score": (
                    score
                ),

                "preview": (
                    preview
                ),
            }
        )

    return hits


# ============================================================
# main
# ============================================================

def main() -> int:

    all_hits = []

    checked = []

    for path in (
        CANDIDATE_FILES
    ):

        exists = (
            path.exists()
        )

        checked.append(
            {
                "path": (
                    str(
                        path
                    )
                ),

                "exists": (
                    exists
                ),
            }
        )

        if not exists:

            continue

        data = load_json(
            path
        )

        all_hits.extend(
            search_file(
                path,
                data,
            )
        )

    # --------------------------------------------------------
    # deduplicate
    # --------------------------------------------------------

    dedup = {}

    for item in (
        all_hits
    ):

        key = (
            item[
                "file"
            ],
            item[
                "path"
            ],
            tuple(
                item[
                    "zones"
                ]
            ),
        )

        existing = (
            dedup.get(
                key
            )
        )

        if (
            existing is None
            or item[
                "score"
            ]
            > existing[
                "score"
            ]
        ):

            dedup[
                key
            ] = (
                item
            )

    ranked = sorted(
        dedup.values(),
        key=lambda item: (
            item[
                "score"
            ]
        ),
        reverse=True,
    )

    # --------------------------------------------------------
    # coverage
    # --------------------------------------------------------

    zone_coverage = {}

    for zone in (
        ZONES
    ):

        matches = [
            item
            for item
            in ranked
            if zone
            in item[
                "zones"
            ]
        ]

        zone_coverage[
            zone
        ] = {
            "hit_count": (
                len(
                    matches
                )
            ),

            "top_hits": (
                matches[
                    :5
                ]
            ),
        }

    covered_zones = [
        zone
        for zone, info
        in zone_coverage.items()
        if info[
            "hit_count"
        ]
        > 0
    ]

    missing_zones = [
        zone
        for zone
        in ZONES
        if zone
        not in covered_zones
    ]

    # --------------------------------------------------------
    # likely source
    # --------------------------------------------------------

    high_quality_hits = [
        item
        for item
        in ranked
        if item[
            "score"
        ]
        >= 50
    ]

    resolution = (
        "ZONE_NUMERIC_SOURCE_CANDIDATES_FOUND"
        if high_quality_hits
        else "SOURCE_NOT_RESOLVED"
    )

    output = {

        "step": (
            "STEP 17-21-C-13-4B "
            "Zone Numeric Regulation Source Probe"
        ),

        "checked_files": (
            checked
        ),

        "zones": (
            ZONES
        ),

        "hit_count": (
            len(
                ranked
            )
        ),

        "high_quality_hit_count": (
            len(
                high_quality_hits
            )
        ),

        "covered_zones": (
            covered_zones
        ),

        "missing_zones": (
            missing_zones
        ),

        "zone_coverage": (
            zone_coverage
        ),

        "ranked_hits": (
            ranked[
                :100
            ]
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
        "Files checked:",
        len(
            checked
        ),
    )

    print(
        "Existing:",
        sum(
            1
            for item
            in checked
            if item[
                "exists"
            ]
        ),
    )

    print()

    print(
        "Hits:",
        len(
            ranked
        ),
    )

    print(
        "High quality:",
        len(
            high_quality_hits
        ),
    )

    print()

    print(
        "Covered zones:",
        len(
            covered_zones
        ),
        "/",
        len(
            ZONES
        ),
    )

    print(
        "Missing zones:",
        missing_zones,
    )

    print()

    print(
        "=== TOP SOURCE CANDIDATES ==="
    )

    if not ranked:

        print(
            "NONE"
        )

    for index, item in enumerate(
        ranked[
            :25
        ],
        start=1,
    ):

        print(
            f"[{index}] "
            f"score={item['score']} "
            f"| file={item['file']} "
            f"| path={item['path']}"
        )

        print(
            "  zones:",
            item[
                "zones"
            ],
        )

        print(
            "  ",
            item[
                "preview"
            ][
                :500
            ],
        )

        print()

    print(
        "resolution:",
        resolution,
    )

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