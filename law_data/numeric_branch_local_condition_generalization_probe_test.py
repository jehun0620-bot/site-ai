# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-4B-2A
Numeric Branch-local Condition Generalization Probe

목표
======================================================================
numeric effect가 있는 조문 전체에서 다음을 비교한다.

A. 조문 text / inherited context에 실제 존재하는 branch-local predicate
B. 현재 condition model에 등록된 predicate

A에는 있는데 B에는 없는 조건을
MISSING_BRANCH_CONDITION 후보로 추출한다.

중요
======================================================================
이번 단계에서는 applicability를 변경하지 않는다.
numeric 값도 변경하지 않는다.

오직:
    "현재 condition model이 조문 문맥을 충분히 표현하고 있는가?"
를 검증한다.


대표 예
======================================================================
clause 205

본문:
    제48조제7호부터 제10호까지의 지역에서
    관광숙박시설을 건축하는 경우 ...

기존 conditions:
    지구단위계획 TRUE
    도시계획위원회심의 TRUE

누락:
    서울조례제48조7호부터10호지역 / SITE
    관광숙박시설 / PROJECT


탐지 대상 predicate
======================================================================

SITE
----------------------------------------------------------------------
- 서울도심
- 제48조제7호~제10호 지역
- 상업지역
- 녹지지역
- 생산녹지지역
- 자연녹지지역
- 준공업지역
- 지구단위계획
- 개발진흥지구
- 방재지구
- 학교이적지
- 개발밀도관리구역

PROJECT
----------------------------------------------------------------------
- 관광숙박시설
- 관광호텔
- 한국전통호텔
- 가족호텔
- 호스텔
- 감염병대응필요시설
- 공공주택
- 임대주택
- 공동주택
- 주거복합
- 공공시설제공
- 기부채납
- 대학
- 종합의료시설
- 사회복지시설
- 공개공지
- 한옥
- 시장정비사업대상전통시장
- 도시정비형재개발사업
- 기존공장

PROCEDURE
----------------------------------------------------------------------
- 도시계획위원회심의
- 시장정비사업심의

주의
======================================================================
텍스트 검색 결과 자체를 곧바로 법적 필수조건으로 확정하지 않는다.

predicate detector는:
    HIGH
    MEDIUM

두 confidence로 나누고,
다음 단계에서 HIGH 후보부터 condition overlay한다.
"""

from __future__ import annotations

import json
import re

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple


STEP_NAME = (
    "STEP 17-21-C-10-4B-2A "
    "numeric branch-local condition generalization probe"
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

DYNAMIC_PATH = (
    OUTPUT_DIR
    / "project_procedure_dynamic_rule_evaluation.json"
)

GUARD_PATH = (
    OUTPUT_DIR
    / "dynamic_numeric_guard_reconciliation.json"
)

CLAUSE_205_PATH = (
    OUTPUT_DIR
    / "clause_205_tourism_branch_guard.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "numeric_branch_local_condition_generalization_probe.json"
)


# ============================================================
# PREDICATE DEFINITIONS
#
# detector:
#   name
#   type
#   patterns
#   confidence
#
# pattern 하나라도 context에 있으면 candidate.
# ============================================================

PREDICATE_DEFINITIONS = [

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    {
        "name": "서울도심",
        "type": "SITE",
        "patterns": [
            r"서울도심",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "서울조례제48조7호부터10호지역",
        "type": "SITE",
        "patterns": [
            r"제48조\s*제?7호부터\s*제?10호까지",
            r"제48조제7호부터제10호까지",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "상업지역",
        "type": "SITE",
        "patterns": [
            r"상업지역",
        ],
        "confidence": "MEDIUM",
    },

    {
        "name": "생산녹지지역",
        "type": "SITE",
        "patterns": [
            r"생산녹지지역",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "자연녹지지역",
        "type": "SITE",
        "patterns": [
            r"자연녹지지역",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "준공업지역",
        "type": "SITE",
        "patterns": [
            r"준공업지역",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "지구단위계획",
        "type": "SITE",
        "patterns": [
            r"지구단위계획",
        ],
        "confidence": "MEDIUM",
    },

    {
        "name": "개발진흥지구",
        "type": "SITE",
        "patterns": [
            r"개발진흥지구",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "방재지구",
        "type": "SITE",
        "patterns": [
            r"방재지구",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "학교이적지",
        "type": "SITE_HISTORY",
        "patterns": [
            r"학교이적지",
            r"학교\s*이적지",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "개발밀도관리구역",
        "type": "SITE",
        "patterns": [
            r"개발밀도관리구역",
        ],
        "confidence": "HIGH",
    },

    # --------------------------------------------------------
    # PROJECT
    # --------------------------------------------------------

    {
        "name": "관광숙박시설",
        "type": "PROJECT",
        "patterns": [
            r"관광숙박시설",
            r"관광호텔업",
            r"한국전통호텔업",
            r"가족호텔업",
            r"호스텔업",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "감염병대응필요시설",
        "type": "PROJECT",
        "patterns": [
            r"감염병\s*대응",
            r"감염병 대응 등을 위하여 필요한 경우",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "공공주택",
        "type": "PROJECT",
        "patterns": [
            r"공공주택",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "임대주택",
        "type": "PROJECT",
        "patterns": [
            r"임대주택",
            r"장기전세주택",
            r"행복주택",
            r"통합공공임대주택",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "공동주택",
        "type": "PROJECT",
        "patterns": [
            r"공동주택",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "주거복합",
        "type": "PROJECT",
        "patterns": [
            r"주거복합",
            r"주거복합건물",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "공공시설제공",
        "type": "PROJECT",
        "patterns": [
            r"공공시설",
            r"기반시설.*제공",
        ],
        "confidence": "MEDIUM",
    },

    {
        "name": "기부채납",
        "type": "PROJECT",
        "patterns": [
            r"기부채납",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "대학",
        "type": "PROJECT",
        "patterns": [
            r"도시계획시설인\s*대학",
            r"도시계획시설\s*대학",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "종합의료시설",
        "type": "PROJECT",
        "patterns": [
            r"종합의료시설",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "사회복지시설",
        "type": "PROJECT",
        "patterns": [
            r"사회복지시설",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "공개공지",
        "type": "PROJECT",
        "patterns": [
            r"공개공지",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "한옥",
        "type": "PROJECT",
        "patterns": [
            r"한옥",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "시장정비사업대상전통시장",
        "type": "PROJECT",
        "patterns": [
            r"시장정비사업\s*추진계획\s*승인대상\s*전통시장",
            r"시장정비사업.*전통시장",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "도시정비형재개발사업",
        "type": "PROJECT",
        "patterns": [
            r"도시정비형\s*재개발사업",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "기존공장",
        "type": "PROJECT",
        "patterns": [
            r"기존\s*공장",
            r"기존공장",
        ],
        "confidence": "HIGH",
    },

    # --------------------------------------------------------
    # PROCEDURE
    # --------------------------------------------------------

    {
        "name": "도시계획위원회심의",
        "type": "PROCEDURE",
        "patterns": [
            r"도시계획위원회.*심의",
            r"시도시계획위원회.*심의",
            r"지방도시계획위원회.*심의",
        ],
        "confidence": "HIGH",
    },

    {
        "name": "시장정비사업심의",
        "type": "PROCEDURE",
        "patterns": [
            r"시장정비사업심의위원회.*심의",
            r"시시장정비사업심의위원회.*심의",
        ],
        "confidence": "HIGH",
    },
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


def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


def normalize_text(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        safe_string(
            value
        ),
    ).strip()


# ============================================================
# numeric rule
# ============================================================

def is_numeric_rule(
    rule: Dict[str, Any],
) -> bool:

    return bool(
        rule.get(
            "numeric_effect"
        )
    )


# ============================================================
# current condition keys
# ============================================================

def current_condition_keys(
    rule: Dict[str, Any],
) -> set[Tuple[str, str]]:

    result = set()

    for condition in rule.get(
        "conditions",
        [],
    ):

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

        condition_type = safe_string(
            condition.get(
                "type"
            )
        )

        if not name:
            continue

        result.add(
            (
                name,
                condition_type,
            )
        )

    return result


# ============================================================
# predicate detection
# ============================================================

def detect_predicates(
    rule: Dict[str, Any],
) -> List[Dict[str, Any]]:

    text = normalize_text(
        rule.get(
            "text"
        )
    )

    inherited = normalize_text(
        rule.get(
            "inherited_context"
        )
    )

    title = normalize_text(
        rule.get(
            "rule_title"
        )
    )

    context = (
        title
        + " "
        + inherited
        + " "
        + text
    )

    detected = []

    for definition in (
        PREDICATE_DEFINITIONS
    ):

        matched_patterns = []

        for pattern in definition[
            "patterns"
        ]:

            if re.search(
                pattern,
                context,
                flags=re.IGNORECASE,
            ):

                matched_patterns.append(
                    pattern
                )

        if not matched_patterns:
            continue

        detected.append(
            {
                "name": (
                    definition[
                        "name"
                    ]
                ),

                "type": (
                    definition[
                        "type"
                    ]
                ),

                "confidence": (
                    definition[
                        "confidence"
                    ]
                ),

                "matched_patterns": (
                    matched_patterns
                ),
            }
        )

    return detected


# ============================================================
# determine missing
# ============================================================

def compare_conditions(
    rule: Dict[str, Any],
    detected: List[Dict[str, Any]],
) -> Dict[str, Any]:

    existing = (
        current_condition_keys(
            rule
        )
    )

    missing = []

    modeled = []

    for item in detected:

        key = (
            item[
                "name"
            ],
            item[
                "type"
            ],
        )

        # ----------------------------------------------------
        # SITE_HISTORY vs SITE name-only compatibility
        #
        # 기존 condition type가 일부 다른 경우를 고려.
        # 동일 name이 있으면 modeled로 취급.
        # ----------------------------------------------------

        existing_names = {
            name
            for name, _
            in existing
        }

        if (
            key in existing
            or item[
                "name"
            ]
            in existing_names
        ):

            modeled.append(
                item
            )

        else:

            missing.append(
                item
            )

    return {
        "modeled": (
            modeled
        ),

        "missing": (
            missing
        ),
    }


# ============================================================
# branch relevance
#
# inherited context에서만 검출된 broad predicate는
# child branch의 필수조건이 아닐 수 있음.
#
# HIGH confidence + child text 직접 등장 여부를 별도 표시.
# ============================================================

def mark_direct_text_presence(
    rule: Dict[str, Any],
    predicates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    text = normalize_text(
        rule.get(
            "text"
        )
    )

    result = []

    for item in predicates:

        direct_patterns = []

        for pattern in item.get(
            "matched_patterns",
            [],
        ):

            if re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):

                direct_patterns.append(
                    pattern
                )

        new_item = dict(
            item
        )

        new_item[
            "direct_in_clause_text"
        ] = bool(
            direct_patterns
        )

        new_item[
            "direct_patterns"
        ] = (
            direct_patterns
        )

        if (
            item[
                "confidence"
            ]
            == "HIGH"
            and direct_patterns
        ):

            new_item[
                "branch_priority"
            ] = "HIGH"

        elif direct_patterns:

            new_item[
                "branch_priority"
            ] = "MEDIUM"

        else:

            new_item[
                "branch_priority"
            ] = "LOW"

        result.append(
            new_item
        )

    return result


# ============================================================
# main
# ============================================================

def main() -> int:

    dynamic = load_json(
        DYNAMIC_PATH
    )

    guard = load_json(
        GUARD_PATH
    )

    clause_205_guard = load_json(
        CLAUSE_205_PATH
    )

    rules = dynamic.get(
        "rules",
        [],
    )

    numeric_rules = [
        rule
        for rule
        in rules
        if isinstance(
            rule,
            dict,
        )
        and is_numeric_rule(
            rule
        )
    ]

    results = []

    missing_counter = Counter()

    high_priority_missing = []

    active_with_missing = []

    # ========================================================
    # scan
    # ========================================================

    for rule in numeric_rules:

        detected = detect_predicates(
            rule
        )

        comparison = compare_conditions(
            rule,
            detected,
        )

        missing = mark_direct_text_presence(
            rule,
            comparison[
                "missing"
            ],
        )

        modeled = mark_direct_text_presence(
            rule,
            comparison[
                "modeled"
            ],
        )

        for item in missing:

            missing_counter[
                (
                    item[
                        "name"
                    ],
                    item[
                        "type"
                    ],
                )
            ] += 1

            if (
                item[
                    "branch_priority"
                ]
                == "HIGH"
            ):

                high_priority_missing.append(
                    {
                        "clause_index": (
                            rule.get(
                                "clause_index"
                            )
                        ),

                        "rule_title": (
                            rule.get(
                                "rule_title"
                            )
                        ),

                        **item,
                    }
                )

        current_numeric_status = (
            rule.get(
                "current_numeric_effect",
                {},
            ).get(
                "status"
            )
        )

        if (
            current_numeric_status
            == "ACTIVE_CANDIDATE"
            and missing
        ):

            active_with_missing.append(
                {
                    "clause_index": (
                        rule.get(
                            "clause_index"
                        )
                    ),

                    "rule_title": (
                        rule.get(
                            "rule_title"
                        )
                    ),

                    "missing": (
                        missing
                    ),
                }
            )

        results.append(
            {
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

                "applicability": (
                    rule.get(
                        "applicability"
                    )
                ),

                "current_numeric_status": (
                    current_numeric_status
                ),

                "effect_targets": (
                    rule.get(
                        "effect_targets",
                        []
                    )
                ),

                "numeric_effect": (
                    rule.get(
                        "numeric_effect"
                    )
                ),

                "existing_conditions": (
                    rule.get(
                        "conditions",
                        []
                    )
                ),

                "detected_predicates": (
                    detected
                ),

                "modeled_predicates": (
                    modeled
                ),

                "missing_predicates": (
                    missing
                ),

                "text": (
                    rule.get(
                        "text"
                    )
                ),

                "inherited_context": (
                    rule.get(
                        "inherited_context"
                    )
                ),
            }
        )

    # ========================================================
    # clause 205 regression check
    # ========================================================

    clause_205 = next(
        (
            item
            for item
            in results
            if int(
                item.get(
                    "clause_index",
                    -1,
                )
            )
            == 205
        ),
        None,
    )

    clause_205_missing_names = set()

    if clause_205:

        clause_205_missing_names = {
            item[
                "name"
            ]
            for item
            in clause_205[
                "missing_predicates"
            ]
        }

    clause_205_expected = {
        "서울조례제48조7호부터10호지역",
        "관광숙박시설",
    }

    # ========================================================
    # guard reconciliation relationship
    # ========================================================

    guard_active_after = {
        int(
            item.get(
                "clause_index"
            )
        )
        for item
        in guard.get(
            "active_rules",
            [],
        )
    }

    active_missing_indexes = {
        int(
            item.get(
                "clause_index"
            )
        )
        for item
        in active_with_missing
    }

    guarded_active_with_missing = (
        sorted(
            guard_active_after
            & active_missing_indexes
        )
    )

    # ========================================================
    # candidate classes
    # ========================================================

    high_candidates = [
        item
        for item
        in high_priority_missing
    ]

    medium_low_candidates = [
        {
            "clause_index": (
                result[
                    "clause_index"
                ]
            ),

            "rule_title": (
                result[
                    "rule_title"
                ]
            ),

            "predicate": (
                item
            ),
        }

        for result in results

        for item in result[
            "missing_predicates"
        ]

        if item[
            "branch_priority"
        ]
        != "HIGH"
    ]

    # ========================================================
    # summary
    # ========================================================

    missing_summary = [
        {
            "name": name,
            "type": condition_type,
            "clause_count": count,
        }

        for (
            name,
            condition_type
        ), count
        in missing_counter.most_common()
    ]

    # ========================================================
    # validations
    # ========================================================

    validations = {

        "numeric rules exist": (
            len(
                numeric_rules
            )
            > 0
        ),

        "clause205 exists": (
            clause_205
            is not None
        ),

        "clause205 zone predicate detected": (
            "서울조례제48조7호부터10호지역"
            in clause_205_missing_names
        ),

        "clause205 tourism predicate detected": (
            "관광숙박시설"
            in clause_205_missing_names
        ),

        "clause205 expected predicates complete": (
            clause_205_expected
            <= clause_205_missing_names
        ),

        "known clause205 guard passed": (
            clause_205_guard.get(
                "all_pass"
            )
            is True
        ),

        "missing predicate detection active": (
            len(
                missing_counter
            )
            > 0
        ),

        "high priority candidates exist": (
            len(
                high_candidates
            )
            > 0
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "scan": {
            "numeric_rule_count": (
                len(
                    numeric_rules
                )
            ),

            "rules_with_missing_predicate": (
                sum(
                    1
                    for item
                    in results
                    if item[
                        "missing_predicates"
                    ]
                )
            ),

            "active_rules_with_missing_predicate": (
                len(
                    active_with_missing
                )
            ),

            "high_priority_missing_count": (
                len(
                    high_candidates
                )
            ),

            "guarded_active_with_missing": (
                guarded_active_with_missing
            ),
        },

        "missing_predicate_summary": (
            missing_summary
        ),

        "high_priority_missing": (
            high_candidates
        ),

        "medium_low_priority_missing": (
            medium_low_candidates
        ),

        "active_rules_with_missing": (
            active_with_missing
        ),

        "clause_205_regression": {
            "detected_missing_names": (
                sorted(
                    clause_205_missing_names
                )
            ),

            "expected_names": (
                sorted(
                    clause_205_expected
                )
            ),

            "all_expected_detected": (
                clause_205_expected
                <= clause_205_missing_names
            ),
        },

        "rules": (
            results
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
    # concise console
    # ========================================================

    print(
        "Numeric rules:",
        len(
            numeric_rules
        ),
    )

    print(
        "Rules with missing predicates:",
        output[
            "scan"
        ][
            "rules_with_missing_predicate"
        ],
    )

    print(
        "Active rules with missing predicates:",
        len(
            active_with_missing
        ),
    )

    print(
        "HIGH-priority missing:",
        len(
            high_candidates
        ),
    )

    print()

    print(
        "Top missing predicates:"
    )

    for item in missing_summary[:15]:

        print(
            f"- {item['name']} "
            f"/ {item['type']} "
            f"/ clauses={item['clause_count']}"
        )

    print()

    print(
        "Active guarded clauses with missing predicates:",
        guarded_active_with_missing,
    )

    print()

    print(
        "=== HIGH PRIORITY ACTIVE ==="
    )

    for item in active_with_missing:

        high_missing = [
            predicate
            for predicate
            in item[
                "missing"
            ]
            if predicate[
                "branch_priority"
            ]
            == "HIGH"
        ]

        if not high_missing:
            continue

        print(
            f"[clause {item['clause_index']}] "
            f"{item['rule_title']}"
        )

        for predicate in high_missing:

            print(
                f"  - {predicate['name']} "
                f"/ {predicate['type']} "
                f"/ direct="
                f"{predicate['direct_in_clause_text']}"
            )

    print()

    print(
        "=== CLAUSE 205 REGRESSION ==="
    )

    print(
        "Detected:",
        sorted(
            clause_205_missing_names
        ),
    )

    print(
        "Expected:",
        sorted(
            clause_205_expected
        ),
    )

    print(
        "Complete:",
        (
            clause_205_expected
            <= clause_205_missing_names
        ),
    )

    print()

    print(
        "all_pass:",
        all_pass,
    )

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