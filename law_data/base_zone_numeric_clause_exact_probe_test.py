# -*- coding: utf-8 -*-

"""
STEP 17-21-C-13-4C
Base Zone Numeric Clause Exact Probe

목표
======================================================================
314개 Rule 중에서 용도지역별 "기본" 건폐율 / 용적률 source clause를
정확히 찾아낸다.

중요
======================================================================
이번 단계에서는 다음 조문은 BASE source에서 제외한다.

- 완화
- 강화
- 특례
- 지구단위계획
- 시장정비사업
- 기부채납
- 중첩 적용
- 기타 조건부 효과

찾고자 하는 것은:

서울특별시 도시계획 조례
→ 용도지역별 건폐율 기본표
→ 용도지역별 용적률 기본표

이다.
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

RULE_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_site_complete.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "base_zone_numeric_clause_exact_probe.json"
)


# ============================================================
# zones
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
# exclude language
# ============================================================

EXCLUDE_TERMS = [

    "완화",
    "강화",
    "특례",
    "중첩",

    "지구단위계획",

    "시장정비",
    "전통시장",

    "기부채납",

    "공공시설",
    "공개공지",

    "관광숙박",

    "재해",
    "방재",

    "개발밀도",
]


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


def rule_text(
    rule: Dict[str, Any],
) -> str:

    parts = [

        str(
            rule.get(
                "law_name",
                "",
            )
        ),

        str(
            rule.get(
                "rule_title",
                "",
            )
        ),

        str(
            rule.get(
                "text",
                "",
            )
        ),

        str(
            rule.get(
                "inherited_text",
                "",
            )
        ),
    ]

    return " ".join(
        parts
    )


def numeric_values(
    rule: Dict[str, Any],
) -> List[float]:

    values = []

    # --------------------------------------------------------
    # common numeric containers
    # --------------------------------------------------------

    candidates = [

        rule.get(
            "numeric_values"
        ),

        rule.get(
            "numeric"
        ),

        rule.get(
            "numbers"
        ),
    ]

    for candidate in candidates:

        if isinstance(
            candidate,
            list,
        ):

            for value in candidate:

                if isinstance(
                    value,
                    (
                        int,
                        float,
                    ),
                ):

                    values.append(
                        float(
                            value
                        )
                    )

    # --------------------------------------------------------
    # semantic numeric
    # --------------------------------------------------------

    semantic_candidates = [

        rule.get(
            "numeric_semantic"
        ),

        rule.get(
            "semantic"
        ),

        rule.get(
            "current_numeric_effect"
        ),
    ]

    def walk(
        value: Any,
    ) -> None:

        if isinstance(
            value,
            dict,
        ):

            for key, item in (
                value.items()
            ):

                if (
                    key
                    in {
                        "value",
                        "min",
                        "max",
                    }
                    and isinstance(
                        item,
                        (
                            int,
                            float,
                        ),
                    )
                ):

                    values.append(
                        float(
                            item
                        )
                    )

                else:

                    walk(
                        item
                    )

        elif isinstance(
            value,
            list,
        ):

            for item in value:

                walk(
                    item
                )

    for candidate in (
        semantic_candidates
    ):

        walk(
            candidate
        )

    # unique preserve order
    result = []

    for value in values:

        if value not in result:

            result.append(
                value
            )

    return result


# ============================================================
# scoring
# ============================================================

def score_rule(
    rule: Dict[str, Any],
) -> Dict[str, Any]:

    text = (
        rule_text(
            rule
        )
    )

    law_name = str(
        rule.get(
            "law_name",
            "",
        )
    )

    title = str(
        rule.get(
            "rule_title",
            "",
        )
    )

    category = str(
        rule.get(
            "category",
            "",
        )
    )

    effect_targets = (
        rule.get(
            "effect_targets",
            []
        )
        or []
    )

    zones = [
        zone
        for zone in ZONES
        if zone in text
    ]

    excluded_terms = [
        term
        for term in EXCLUDE_TERMS
        if term in text
    ]

    score = 0

    # ========================================================
    # law
    # ========================================================

    if (
        law_name
        == "서울특별시 도시계획 조례"
    ):

        score += 100

    # ========================================================
    # base title / category
    # ========================================================

    if (
        "건폐율"
        in title
    ):

        score += 20

    if (
        "용적률"
        in title
    ):

        score += 20

    if (
        category
        == "건폐율"
    ):

        score += 20

    if (
        category
        == "용적률"
    ):

        score += 20

    # ========================================================
    # language
    # ========================================================

    if (
        "용도지역"
        in text
    ):

        score += 30

    if (
        "다음 각 호"
        in text
    ):

        score += 10

    if (
        "이하"
        in text
    ):

        score += 10

    if (
        "퍼센트"
        in text
    ):

        score += 15

    if zones:

        score += (
            len(
                zones
            )
            * 15
        )

    # ========================================================
    # explicit target
    # ========================================================

    if (
        "building_coverage_ratio"
        in effect_targets
    ):

        score += 15

    if (
        "floor_area_ratio"
        in effect_targets
    ):

        score += 15

    # ========================================================
    # penalties
    # ========================================================

    score -= (
        len(
            excluded_terms
        )
        * 40
    )

    return {

        "score": (
            score
        ),

        "zones": (
            zones
        ),

        "excluded_terms": (
            excluded_terms
        ),

        "numeric": (
            numeric_values(
                rule
            )
        ),

        "text": (
            text
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    data = load_json(
        RULE_PATH
    )

    rules = (
        data.get(
            "rules",
            []
        )
    )

    candidates = []

    for index, rule in enumerate(
        rules
    ):

        if not isinstance(
            rule,
            dict,
        ):

            continue

        scored = score_rule(
            rule
        )

        # ----------------------------------------------------
        # 서울 조례가 아니면 이번 base resolver 후보에서 제외
        # ----------------------------------------------------

        if (
            rule.get(
                "law_name"
            )
            != "서울특별시 도시계획 조례"
        ):

            continue

        # ----------------------------------------------------
        # 건폐율/용적률 관련이 아니면 제외
        # ----------------------------------------------------

        text = (
            scored[
                "text"
            ]
        )

        if (
            "건폐율"
            not in text
            and "용적률"
            not in text
        ):

            continue

        candidates.append(
            {

                "rule_index": (
                    index
                ),

                "clause_index": (
                    rule.get(
                        "clause_index"
                    )
                ),

                "law_name": (
                    rule.get(
                        "law_name"
                    )
                ),

                "rule_title": (
                    rule.get(
                        "rule_title"
                    )
                ),

                "category": (
                    rule.get(
                        "category"
                    )
                ),

                "paragraph": (
                    rule.get(
                        "paragraph"
                    )
                ),

                "item": (
                    rule.get(
                        "item"
                    )
                ),

                "subitem": (
                    rule.get(
                        "subitem"
                    )
                ),

                "effect_targets": (
                    rule.get(
                        "effect_targets"
                    )
                ),

                "score": (
                    scored[
                        "score"
                    ]
                ),

                "zones": (
                    scored[
                        "zones"
                    ]
                ),

                "excluded_terms": (
                    scored[
                        "excluded_terms"
                    ]
                ),

                "numeric": (
                    scored[
                        "numeric"
                    ]
                ),

                "text": (
                    rule.get(
                        "text"
                    )
                ),

                "inherited_text": (
                    rule.get(
                        "inherited_text"
                    )
                ),
            }
        )

    ranked = sorted(
        candidates,
        key=lambda item: (
            item[
                "score"
            ]
        ),
        reverse=True,
    )

    # ========================================================
    # clean base candidates
    #
    # 완화/강화 등 제외 언어가 없는 후보만 따로 본다.
    # ========================================================

    clean_candidates = [
        item
        for item in ranked
        if not item[
            "excluded_terms"
        ]
    ]

    # ========================================================
    # target-specific
    # ========================================================

    bcr_candidates = [
        item
        for item in clean_candidates
        if (
            item[
                "category"
            ]
            == "건폐율"
            or (
                item[
                    "effect_targets"
                ]
                and "building_coverage_ratio"
                in item[
                    "effect_targets"
                ]
            )
        )
    ]

    far_candidates = [
        item
        for item in clean_candidates
        if (
            item[
                "category"
            ]
            == "용적률"
            or (
                item[
                    "effect_targets"
                ]
                and "floor_area_ratio"
                in item[
                    "effect_targets"
                ]
            )
        )
    ]

    # ========================================================
    # zone coverage from CLEAN candidates
    # ========================================================

    coverage = {}

    for zone in ZONES:

        bcr_hits = [
            item
            for item in bcr_candidates
            if zone
            in item[
                "zones"
            ]
        ]

        far_hits = [
            item
            for item in far_candidates
            if zone
            in item[
                "zones"
            ]
        ]

        coverage[
            zone
        ] = {

            "bcr_hit_count": (
                len(
                    bcr_hits
                )
            ),

            "far_hit_count": (
                len(
                    far_hits
                )
            ),

            "top_bcr": (
                bcr_hits[
                    :3
                ]
            ),

            "top_far": (
                far_hits[
                    :3
                ]
            ),
        }

    zones_with_both = [
        zone
        for zone, info
        in coverage.items()
        if (
            info[
                "bcr_hit_count"
            ]
            > 0
            and info[
                "far_hit_count"
            ]
            > 0
        )
    ]

    incomplete_zones = [
        zone
        for zone
        in ZONES
        if zone
        not in zones_with_both
    ]

    # ========================================================
    # output
    # ========================================================

    output = {

        "step": (
            "STEP 17-21-C-13-4C "
            "Base Zone Numeric Clause Exact Probe"
        ),

        "rule_count": (
            len(
                rules
            )
        ),

        "candidate_count": (
            len(
                ranked
            )
        ),

        "clean_candidate_count": (
            len(
                clean_candidates
            )
        ),

        "bcr_candidate_count": (
            len(
                bcr_candidates
            )
        ),

        "far_candidate_count": (
            len(
                far_candidates
            )
        ),

        "zones_with_both": (
            zones_with_both
        ),

        "incomplete_zones": (
            incomplete_zones
        ),

        "coverage": (
            coverage
        ),

        "top_clean_candidates": (
            clean_candidates[
                :100
            ]
        ),

        "top_bcr_candidates": (
            bcr_candidates[
                :50
            ]
        ),

        "top_far_candidates": (
            far_candidates[
                :50
            ]
        ),

        "resolution": (
            "BASE_CLAUSE_CANDIDATES_READY"
            if (
                bcr_candidates
                and far_candidates
            )
            else "BASE_CLAUSE_NOT_RESOLVED"
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
        "Rules:",
        len(
            rules
        ),
    )

    print(
        "Candidates:",
        len(
            ranked
        ),
    )

    print(
        "Clean candidates:",
        len(
            clean_candidates
        ),
    )

    print()

    print(
        "BCR base candidates:",
        len(
            bcr_candidates
        ),
    )

    print(
        "FAR base candidates:",
        len(
            far_candidates
        ),
    )

    print()

    print(
        "Zones with BCR+FAR evidence:",
        len(
            zones_with_both
        ),
        "/",
        len(
            ZONES
        ),
    )

    print(
        "Incomplete zones:",
        incomplete_zones,
    )

    print()

    print(
        "=== TOP BCR BASE CANDIDATES ==="
    )

    for index, item in enumerate(
        bcr_candidates[
            :15
        ],
        start=1,
    ):

        print(
            f"[{index}] "
            f"clause={item['clause_index']} "
            f"| score={item['score']} "
            f"| title={item['rule_title']}"
        )

        print(
            " zones:",
            item[
                "zones"
            ],
        )

        print(
            " numeric:",
            item[
                "numeric"
            ],
        )

        print(
            " text:",
            str(
                item[
                    "text"
                ]
            )[
                :600
            ],
        )

        print()

    print(
        "=== TOP FAR BASE CANDIDATES ==="
    )

    for index, item in enumerate(
        far_candidates[
            :15
        ],
        start=1,
    ):

        print(
            f"[{index}] "
            f"clause={item['clause_index']} "
            f"| score={item['score']} "
            f"| title={item['rule_title']}"
        )

        print(
            " zones:",
            item[
                "zones"
            ],
        )

        print(
            " numeric:",
            item[
                "numeric"
            ],
        )

        print(
            " text:",
            str(
                item[
                    "text"
                ]
            )[
                :600
            ],
        )

        print()

    resolution = (
        output[
            "resolution"
        ]
    )

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