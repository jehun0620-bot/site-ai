# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-1B-1
'기존공장' condition semantic probe

목표
======================================================================
1. law_special_rule_clauses.json에서 '기존공장' 조건을 가진 clause 전수 추출
2. 현재 parser가 부여한 condition type 확인
3. 법규명 / 조문 / 효과대상 / 용도지역 관련성 확인
4. clause 본문 문맥을 간략 출력
5. 기존공장이 PROJECT인지 SITE / SITE_HISTORY인지 다음 단계에서 판단

주의
======================================================================
- 문자열이 PROJECT로 분류됐다는 사실만으로 semantic 확정 금지
- 기존 건축물/공장의 존재 자체가 필요하면 SITE 성격일 수 있음
- 기존 공장의 과거 상태가 필요하면 SITE_HISTORY 성격일 수 있음
- 향후 사업계획이 공장인지 묻는 조건이면 PROJECT 성격일 수 있음
"""

from __future__ import annotations

import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-1B-1 "
    "기존공장 condition semantic probe"
)

TARGET_CONDITION = "기존공장"


# ============================================================
# 경로
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

CLAUSE_PATH = (
    OUTPUT_DIR
    / "law_special_rule_clauses.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "existing_factory_condition_probe.json"
)


# ============================================================
# util
# ============================================================

def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


def compact(
    value: Any,
    limit: int = 500,
) -> str:

    text = safe_string(value)

    text = " ".join(
        text.split()
    )

    if len(text) > limit:

        return (
            text[:limit]
            + "..."
        )

    return text


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


# ============================================================
# target condition 검사
# ============================================================

def find_target_condition(
    clause: Dict[str, Any],
) -> List[Dict[str, Any]]:

    conditions = clause.get(
        "conditions",
        [],
    )

    if not isinstance(
        conditions,
        list,
    ):
        return []

    results = []

    for condition in conditions:

        if not isinstance(
            condition,
            dict,
        ):
            continue

        name = safe_string(
            condition.get(
                "name"
            )
        )

        if name != TARGET_CONDITION:
            continue

        results.append(
            condition
        )

    return results


# ============================================================
# main
# ============================================================

def main() -> int:

    data = load_json(
        CLAUSE_PATH
    )

    clauses = data.get(
        "clauses",
        [],
    )

    if not isinstance(
        clauses,
        list,
    ):

        print(
            "ERROR: clauses invalid"
        )

        return 1

    hits = []

    declared_types = Counter()

    categories = Counter()

    zone_relevances = Counter()

    effect_targets = Counter()

    laws = Counter()

    rule_titles = Counter()

    # ========================================================
    # 전체 clause 탐색
    # ========================================================

    for index, clause in enumerate(
        clauses,
        start=1,
    ):

        if not isinstance(
            clause,
            dict,
        ):
            continue

        matched_conditions = (
            find_target_condition(
                clause
            )
        )

        if not matched_conditions:
            continue

        for condition in matched_conditions:

            condition_type = safe_string(
                condition.get(
                    "type"
                )
            )

            declared_types[
                condition_type
            ] += 1

        category = safe_string(
            clause.get(
                "category"
            )
        )

        law_name = safe_string(
            clause.get(
                "law_name"
            )
        )

        rule_title = safe_string(
            clause.get(
                "rule_title"
            )
        )

        zone_relevance = safe_string(
            clause.get(
                "zone_relevance"
            )
        )

        if category:
            categories[
                category
            ] += 1

        if law_name:
            laws[
                law_name
            ] += 1

        if rule_title:
            rule_titles[
                rule_title
            ] += 1

        if zone_relevance:
            zone_relevances[
                zone_relevance
            ] += 1

        for target in clause.get(
            "effect_targets",
            [],
        ):

            target = safe_string(
                target
            )

            if target:
                effect_targets[
                    target
                ] += 1

        hits.append(
            {
                "clause_index": (
                    index
                ),

                "category": (
                    category
                ),

                "law_name": (
                    law_name
                ),

                "rule_title": (
                    rule_title
                ),

                "paragraph": (
                    clause.get(
                        "paragraph"
                    )
                ),

                "item": (
                    clause.get(
                        "item"
                    )
                ),

                "subitem": (
                    clause.get(
                        "subitem"
                    )
                ),

                "zone_relevance": (
                    zone_relevance
                ),

                "zones": (
                    clause.get(
                        "zones",
                        [],
                    )
                ),

                "zone_groups": (
                    clause.get(
                        "zone_groups",
                        [],
                    )
                ),

                "effect_targets": (
                    clause.get(
                        "effect_targets",
                        [],
                    )
                ),

                "numeric_values": (
                    clause.get(
                        "numeric_values",
                        [],
                    )
                ),

                "conditions": (
                    clause.get(
                        "conditions",
                        [],
                    )
                ),

                "inherited_context": (
                    clause.get(
                        "inherited_context",
                        ""
                    )
                ),

                "text": (
                    clause.get(
                        "text",
                        ""
                    )
                ),
            }
        )

    # ========================================================
    # semantic hint
    #
    # 자동 최종판정이 아니라 검토용 힌트만 생성
    # ========================================================

    text_all = " ".join(
        safe_string(
            item.get(
                "text"
            )
        )
        for item
        in hits
    )

    semantic_signals = {
        "기존 공장의 현재 존재를 묻는 표현": any(
            token in text_all
            for token in (
                "기존공장",
                "기존 공장",
                "현재 공장",
            )
        ),

        "이전/종전/기존 상태 표현": any(
            token in text_all
            for token in (
                "종전",
                "이전",
                "기존",
            )
        ),

        "사업계획/건축계획 표현": any(
            token in text_all
            for token in (
                "사업계획",
                "건축계획",
                "사업시행",
                "건축하려는",
            )
        ),

        "이전·이적·폐지 history 표현": any(
            token in text_all
            for token in (
                "이전한",
                "이적",
                "폐지",
                "이전된",
            )
        ),
    }

    output = {
        "step": (
            STEP_NAME
        ),

        "target_condition": (
            TARGET_CONDITION
        ),

        "hit_count": (
            len(
                hits
            )
        ),

        "declared_condition_types": (
            dict(
                declared_types
            )
        ),

        "categories": (
            dict(
                categories
            )
        ),

        "laws": (
            dict(
                laws
            )
        ),

        "rule_titles": (
            dict(
                rule_titles
            )
        ),

        "zone_relevance": (
            dict(
                zone_relevances
            )
        ),

        "effect_targets": (
            dict(
                effect_targets
            )
        ),

        "semantic_signals": (
            semantic_signals
        ),

        "resolution": {
            "semantic_type": (
                "UNVERIFIED"
            ),

            "reason": (
                "'기존공장'은 실제 clause에 존재하지만 "
                "현재 PROJECT required-condition registry에는 누락됨. "
                "본문 문맥을 확인하여 PROJECT / SITE / "
                "SITE_HISTORY 중 정확한 semantic type을 "
                "확정해야 함"
            ),
        },

        "clauses": (
            hits
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # concise console
    # ========================================================

    print(
        "Condition:",
        TARGET_CONDITION,
    )

    print(
        "Hits:",
        len(
            hits
        ),
    )

    print(
        "Declared types:",
        dict(
            declared_types
        ),
    )

    print(
        "Categories:",
        dict(
            categories
        ),
    )

    print(
        "Effects:",
        dict(
            effect_targets
        ),
    )

    print(
        "Zone relevance:",
        dict(
            zone_relevances
        ),
    )

    print()

    for index, item in enumerate(
        hits[:17],
        start=1,
    ):

        print(
            f"[{index}] "
            f"{item['law_name']} | "
            f"{item['rule_title']} | "
            f"{item['paragraph'] or '-'} "
            f"{item['item'] or '-'} "
            f"{item['subitem'] or '-'}"
        )

        print(
            "  effect:",
            item[
                "effect_targets"
            ],
        )

        print(
            "  conditions:",
            [
                (
                    condition.get(
                        "name"
                    ),
                    condition.get(
                        "type"
                    ),
                )
                for condition
                in item[
                    "conditions"
                ]
                if isinstance(
                    condition,
                    dict,
                )
            ],
        )

        print(
            "  text:",
            compact(
                item[
                    "text"
                ],
                380,
            ),
        )

    print()

    print(
        "semantic_type: UNVERIFIED"
    )

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )