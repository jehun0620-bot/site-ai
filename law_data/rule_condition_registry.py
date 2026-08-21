# -*- coding: utf-8 -*-

"""
Rule Condition Registry

C-10에서 검증한 SITE / PROJECT / PROCEDURE
branch-local predicate 정의를 실제 reusable module로 분리한다.

이 모듈은 테스트 output JSON에 의존하지 않는다.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


# ============================================================
# BRANCH PREDICATE DEFINITIONS
# ============================================================

BRANCH_PREDICATE_DEFINITIONS = [

    # ========================================================
    # SITE
    # ========================================================

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

    # ========================================================
    # PROJECT
    # ========================================================

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

    # ========================================================
    # PROCEDURE
    # ========================================================

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
# SITE zone mapping
# ============================================================

SEOUL_ARTICLE_48_ZONE_MAP = {

    "제1종전용주거지역": 1,
    "제2종전용주거지역": 2,

    "제1종일반주거지역": 3,
    "제2종일반주거지역": 4,
    "제3종일반주거지역": 5,

    "준주거지역": 6,

    "중심상업지역": 7,
    "일반상업지역": 8,
    "근린상업지역": 9,
    "유통상업지역": 10,
}


# ============================================================
# helpers
# ============================================================

def normalize_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(
            value
        ),
    ).strip()


# ============================================================
# predicate detection
# ============================================================

def detect_branch_predicates(
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
        BRANCH_PREDICATE_DEFINITIONS
    ):

        matched = []

        direct = []

        for pattern in definition[
            "patterns"
        ]:

            if re.search(
                pattern,
                context,
                flags=re.IGNORECASE,
            ):

                matched.append(
                    pattern
                )

            if re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):

                direct.append(
                    pattern
                )

        if not matched:
            continue

        if (
            definition[
                "confidence"
            ]
            == "HIGH"
            and direct
        ):

            priority = (
                "HIGH"
            )

        elif direct:

            priority = (
                "MEDIUM"
            )

        else:

            priority = (
                "LOW"
            )

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

                "direct_in_clause_text": (
                    bool(
                        direct
                    )
                ),

                "branch_priority": (
                    priority
                ),

                "matched_patterns": (
                    matched
                ),

                "direct_patterns": (
                    direct
                ),
            }
        )

    return detected


# ============================================================
# missing predicate extraction
# ============================================================

def find_missing_branch_predicates(
    rule: Dict[str, Any],
) -> List[Dict[str, Any]]:

    existing_names = {
        str(
            condition.get(
                "name"
            )
        ).strip()

        for condition
        in rule.get(
            "conditions",
            []
        )

        if isinstance(
            condition,
            dict,
        )
        and condition.get(
            "name"
        )
    }

    detected = (
        detect_branch_predicates(
            rule
        )
    )

    return [
        item
        for item
        in detected
        if (
            item[
                "name"
            ]
            not in existing_names
        )
    ]


# ============================================================
# resolve SITE branch predicate
# ============================================================

def resolve_site_branch_predicate(
    name: str,
    site_zone: str,
    site_registry: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    # --------------------------------------------------------
    # registered SITE condition
    # --------------------------------------------------------

    existing = (
        site_registry.get(
            name
        )
    )

    if existing:

        return {
            "name": (
                name
            ),

            "type": (
                existing.get(
                    "type",
                    "SITE",
                )
            ),

            "state": (
                existing[
                    "state"
                ]
            ),

            "confidence": (
                existing[
                    "confidence"
                ]
            ),

            "source": (
                existing[
                    "source"
                ]
            ),
        }

    # --------------------------------------------------------
    # Seoul Article 48 7-10
    # --------------------------------------------------------

    if (
        name
        == "서울조례제48조7호부터10호지역"
    ):

        article_number = (
            SEOUL_ARTICLE_48_ZONE_MAP.get(
                site_zone
            )
        )

        state = (
            "TRUE"

            if article_number
            in {
                7,
                8,
                9,
                10,
            }

            else "FALSE"
        )

        return {
            "name": (
                name
            ),

            "type": (
                "SITE"
            ),

            "state": (
                state
            ),

            "confidence": (
                "HIGH"
            ),

            "source": (
                "RULE_CONDITION_REGISTRY"
            ),

            "resolution_meta": {
                "site_zone": (
                    site_zone
                ),

                "article_48_number": (
                    article_number
                ),

                "required_numbers": [
                    7,
                    8,
                    9,
                    10,
                ],
            },
        }

    return {
        "name": (
            name
        ),

        "type": (
            "SITE"
        ),

        "state": (
            "UNKNOWN"
        ),

        "confidence": (
            "NONE"
        ),

        "source": (
            "RULE_CONDITION_REGISTRY"
        ),
    }


# ============================================================
# build condition
# ============================================================

def build_branch_condition(
    predicate: Dict[str, Any],
    site_zone: str,
    site_registry: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    name = (
        predicate[
            "name"
        ]
    )

    condition_type = (
        predicate[
            "type"
        ]
    )

    if condition_type in {
        "SITE",
        "SITE_HISTORY",
    }:

        result = (
            resolve_site_branch_predicate(
                name=name,
                site_zone=site_zone,
                site_registry=site_registry,
            )
        )

        result[
            "type"
        ] = (
            condition_type
        )

    else:

        result = {
            "name": (
                name
            ),

            "type": (
                condition_type
            ),

            "state": (
                "UNSET"
            ),

            "confidence": (
                "NONE"
            ),

            "source": (
                "RULE_CONDITION_REGISTRY"
            ),
        }

    result[
        "branch_local"
    ] = (
        True
    )

    result[
        "detector_confidence"
    ] = (
        predicate.get(
            "confidence"
        )
    )

    return result