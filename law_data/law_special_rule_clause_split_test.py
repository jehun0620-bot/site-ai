import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# STEP 17-21-C-8-8
# 후속 호 경계 / container-leaf 검증 최종 보정
#
# 핵심 보정
# ------------------------------------------------------------
# 1. 개정이력 <개정 ...> 제거
# 2. 있다.1. / 범위2. / 이하3. 형태 무공백 호 경계 인식
# 3. 가. / 나. / 다. ... 목 구조 분리
# 4. 문장 종결 "다."를 다목으로 오인하지 않도록 방어
# 5. 정확한 용도지역 내부 그룹 substring 오염 방지
# 6. 상위 정확 용도지역 제한을 자식 clause가 상속
# 7. 도시지역(녹지지역만 해당) 같은 한정조건 판정
# 8. 상업/공업/녹지 부모 container를 오류로 오인하지 않음
# 9. 최종 leaf clause만 다중 목 잔존 검증
# 10. 제46조 ⑮항 제3종일반주거지역 제외
# 11. 시장정비사업 제3종 60% 나목 분리
# 12. 학교이적지 제3종 200% 바목 분리
# 13. 서울시 조례 용적률 완화 1호 사목 뒤
#     제2호~제8호가 사목에 붙지 않도록 회귀검증
# ============================================================


BASE_DIR = Path(__file__).resolve().parent

INPUT_RULES_PATH = (
    BASE_DIR
    / "output"
    / "law_special_rule_conditions.json"
)

INPUT_SITE_PATH = (
    BASE_DIR
    / "output"
    / "site_law_condition_snapshot.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "output"
    / "law_special_rule_clauses.json"
)


TARGET_DEFAULT_ZONE = "제3종일반주거지역"


# ============================================================
# 용도지역 체계
# ============================================================

EXACT_ZONES = [
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

    "보전관리지역",
    "생산관리지역",
    "계획관리지역",

    "농림지역",
    "자연환경보전지역",
]


ZONE_GROUPS = {
    "도시지역": {
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
    },

    "주거지역": {
        "제1종전용주거지역",
        "제2종전용주거지역",
        "제1종일반주거지역",
        "제2종일반주거지역",
        "제3종일반주거지역",
        "준주거지역",
    },

    "전용주거지역": {
        "제1종전용주거지역",
        "제2종전용주거지역",
    },

    "일반주거지역": {
        "제1종일반주거지역",
        "제2종일반주거지역",
        "제3종일반주거지역",
    },

    "상업지역": {
        "중심상업지역",
        "일반상업지역",
        "근린상업지역",
        "유통상업지역",
    },

    "공업지역": {
        "전용공업지역",
        "일반공업지역",
        "준공업지역",
    },

    "녹지지역": {
        "보전녹지지역",
        "생산녹지지역",
        "자연녹지지역",
    },

    "관리지역": {
        "보전관리지역",
        "생산관리지역",
        "계획관리지역",
    },
}


# ============================================================
# 조건 정의
# ============================================================

SITE_CONDITIONS = {
    "지구단위계획": [
        "지구단위계획구역",
        "지구단위계획",
    ],

    "개발진흥지구": [
        "개발진흥지구",
        "산업ㆍ유통개발진흥지구",
        "산업·유통개발진흥지구",
    ],

    "개발밀도관리구역": [
        "개발밀도관리구역",
    ],

    "산업단지": [
        "산업단지",
        "국가산업단지",
        "일반산업단지",
        "도시첨단산업단지",
        "준산업단지",
    ],

    "수산자원보호구역": [
        "수산자원보호구역",
    ],

    "입체복합구역": [
        "입체복합구역",
        "도시ㆍ군계획시설입체복합구역",
        "도시·군계획시설입체복합구역",
    ],

    "자연경관지구": [
        "자연경관지구",
    ],

    "자연공원": [
        "자연공원",
    ],

    "취락지구": [
        "취락지구",
    ],

    "도시지역편입해제구역": [
        "개발제한구역",
        "시가화조정구역",
        "공원에서 해제",
        "녹지지역에서 해제",
        "새로이 도시지역으로 편입",
        "도시지역으로 편입",
    ],
}


SITE_HISTORY_CONDITIONS = {
    "학교이적지": [
        "학교이적지",
    ],
}


PROJECT_CONDITIONS = {
    "공개공지": [
        "공개공지",
        "공개공간",
    ],

    "공공시설제공": [
        "공공시설등의 부지를 제공",
        "공공시설등을 설치하여 제공",
        "공공시설부지로 제공",
        "공공시설등 제공",
        "공공시설 제공",
    ],

    "공공주택": [
        "공공주택",
        "국민임대주택",
        "행복주택",
        "통합공공임대주택",
        "장기전세주택",
    ],

    "공동주택": [
        "공동주택",
    ],

    "기부채납": [
        "기부채납",
    ],

    "기존공장": [
        "기존 공장",
        "기존공장",
    ],

    "대학": [
        "대학",
        "고등교육법",
    ],

    "사회복지시설": [
        "사회복지시설",
    ],

    "임대주택": [
        "임대주택",
        "임대형기숙사",
        "공공임대주택",
    ],

    "종합의료시설": [
        "종합의료시설",
    ],

    "주거복합": [
        "주거복합",
        "주거복합건물",
    ],

    "한옥": [
        "한옥",
        "한옥마을",
    ],
}


PROCEDURE_CONDITIONS = {
    "도시계획위원회심의": [
        "도시계획위원회의 심의",
        "도시계획위원회 심의",
        "시도시계획위원회의 심의",
        "지방도시계획위원회의 심의",
        "공동 심의",
    ],

    "시장정비사업심의": [
        "시장정비사업심의위원회",
        "시시장정비사업심의위원회",
    ],
}


# ============================================================
# 항 / 호 / 목 표시
# ============================================================

CIRCLED_PARAGRAPHS = {
    "①", "②", "③", "④", "⑤",
    "⑥", "⑦", "⑧", "⑨", "⑩",
    "⑪", "⑫", "⑬", "⑭", "⑮",
    "⑯", "⑰", "⑱", "⑲", "⑳",
}


MOK_LETTERS = [
    "가", "나", "다", "라", "마",
    "바", "사", "아", "자", "차",
    "카", "타", "파", "하",
]


# ============================================================
# 공통 유틸
# ============================================================

def load_json(path: Path) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(
    path: Path,
    data: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def compact_spaces(text: str) -> str:

    if not text:
        return ""

    text = text.replace(
        "\r",
        " ",
    )

    text = text.replace(
        "\n",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def strip_revision_history(
    text: str,
) -> str:

    if not text:
        return ""

    patterns = [
        r"<\s*개정\b[^>]*>",
        r"<\s*신설\b[^>]*>",
        r"<\s*삭제\b[^>]*>",
        r"<\s*전문개정\b[^>]*>",
        r"<\s*본조신설\b[^>]*>",
    ]

    result = text

    for pattern in patterns:
        result = re.sub(
            pattern,
            " ",
            result,
            flags=re.IGNORECASE,
        )

    return compact_spaces(
        result
    )


def clean_text(
    text: Any,
) -> str:

    if text is None:
        return ""

    if not isinstance(
        text,
        str,
    ):
        text = str(
            text
        )

    text = strip_revision_history(
        text
    )

    return compact_spaces(
        text
    )


def first_nonempty(
    d: Dict[str, Any],
    keys: List[str],
) -> str:

    for key in keys:

        value = d.get(
            key
        )

        if (
            isinstance(
                value,
                str,
            )
            and value.strip()
        ):
            return value.strip()

    return ""


# ============================================================
# 입력 구조 유연 대응
# ============================================================

LAW_KEYS = [
    "law_name",
    "law",
    "법규",
    "법령",
    "법령명",
    "lawName",
    "statute",
]

TITLE_KEYS = [
    "rule_name",
    "rule_title",
    "title",
    "규정",
    "조문명",
    "article_title",
    "articleName",
    "name",
]

TEXT_KEYS = [
    "text",
    "본문",
    "content",
    "rule_text",
    "clause_text",
    "article_text",
    "article_content",
    "raw_text",
    "summary",
    "description",
]

CATEGORY_KEYS = [
    "category",
    "카테고리",
    "type",
    "effect_category",
]


def looks_like_rule_record(
    d: Dict[str, Any],
) -> bool:

    text = first_nonempty(
        d,
        TEXT_KEYS,
    )

    if not text:
        return False

    keywords = [
        "건폐율",
        "용적률",
        "높이",
        "지구단위계획",
        "용도지역",
        "제",
        "퍼센트",
        "%",
    ]

    return any(
        keyword in text
        for keyword in keywords
    )


def collect_rule_candidates(
    obj: Any,
    inherited_category: Optional[str] = None,
) -> List[Dict[str, Any]]:

    found: List[
        Dict[str, Any]
    ] = []

    if isinstance(
        obj,
        list,
    ):

        for item in obj:
            found.extend(
                collect_rule_candidates(
                    item,
                    inherited_category=
                    inherited_category,
                )
            )

        return found

    if not isinstance(
        obj,
        dict,
    ):
        return found

    local_category = (
        first_nonempty(
            obj,
            CATEGORY_KEYS,
        )
        or inherited_category
    )

    if looks_like_rule_record(
        obj
    ):

        found.append(
            {
                "law_name":
                    first_nonempty(
                        obj,
                        LAW_KEYS,
                    ),

                "rule_title":
                    first_nonempty(
                        obj,
                        TITLE_KEYS,
                    ),

                "category":
                    local_category
                    or "",

                "text":
                    first_nonempty(
                        obj,
                        TEXT_KEYS,
                    ),

                "source":
                    deepcopy(
                        obj
                    ),
            }
        )

    for key, value in obj.items():

        child_category = (
            local_category
        )

        key_lower = str(
            key
        ).lower()

        if "건폐" in str(
            key
        ):
            child_category = (
                "건폐율"
            )

        elif "용적" in str(
            key
        ):
            child_category = (
                "용적률"
            )

        elif key_lower in {
            "building_coverage_ratio",
            "bcr",
        }:
            child_category = (
                "건폐율"
            )

        elif key_lower in {
            "floor_area_ratio",
            "far",
        }:
            child_category = (
                "용적률"
            )

        if isinstance(
            value,
            (
                dict,
                list,
            ),
        ):

            found.extend(
                collect_rule_candidates(
                    value,
                    inherited_category=
                    child_category,
                )
            )

    unique = []
    seen = set()

    for item in found:

        key = (
            item["law_name"],
            item["rule_title"],
            item["category"],
            clean_text(
                item["text"]
            ),
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        unique.append(
            item
        )

    return unique


# ============================================================
# SITE 정보
# ============================================================

def recursive_find_value(
    obj: Any,
    target_keys: List[str],
) -> Optional[Any]:

    if isinstance(
        obj,
        dict,
    ):

        for key in target_keys:

            if (
                key in obj
                and obj[key]
                not in (
                    None,
                    "",
                )
            ):
                return obj[
                    key
                ]

        for value in obj.values():

            result = (
                recursive_find_value(
                    value,
                    target_keys,
                )
            )

            if result not in (
                None,
                "",
            ):
                return result

    elif isinstance(
        obj,
        list,
    ):

        for value in obj:

            result = (
                recursive_find_value(
                    value,
                    target_keys,
                )
            )

            if result not in (
                None,
                "",
            ):
                return result

    return None


def extract_site_info(
    site_data: Any,
) -> Dict[str, Any]:

    address = (
        recursive_find_value(
            site_data,
            [
                "address",
                "주소",
                "jibun_address",
                "parcel_address",
            ],
        )
    )

    zone = (
        recursive_find_value(
            site_data,
            [
                "zone",
                "용도지역",
                "land_use_zone",
                "use_zone",
                "zoning",
            ],
        )
    )

    return {
        "address":
            str(
                address
                or ""
            ),

        "zone":
            str(
                zone
                or TARGET_DEFAULT_ZONE
            ),
    }


# ============================================================
# 경계 보정
# ============================================================

def insert_paragraph_boundaries(
    text: str,
) -> str:

    for marker in CIRCLED_PARAGRAPHS:

        text = text.replace(
            marker,
            f"\n{marker}",
        )

    return text


def insert_no_space_ho_boundaries(
    text: str,
) -> str:
    """
    C-8-8 핵심.

    예:
        있다.1.
        범위2.
        이하3.
        적용4.
        것5.

    등을 실제 호 경계로 변환.

    제외:
        1.5
        2005.9.8
        제1조
        제2호
        1)
        2)
    """

    if not text:
        return ""

    # --------------------------------------------------------
    # 1. 문장 종결부 + 숫자.
    # --------------------------------------------------------

    terminal_pattern = re.compile(
        r"(?P<before>"
        r"(?:"
        r"다|한다|있다|없다|된다|"
        r"가능하다|정한다|적용한다|"
        r"말한다|아니한다"
        r")\."
        r")"
        r"(?P<num>[1-9][0-9]?)\."
    )

    text = terminal_pattern.sub(
        lambda m:
            (
                f"{m.group('before')}"
                f"\n"
                f"{m.group('num')}. "
            ),
        text,
    )

    # --------------------------------------------------------
    # 2. 마침표 없는 문장 끝 + 다음 호
    #
    # 예:
    # 범위2. 규칙으로...
    # 이하3. 준주거지역...
    # 적용4. ...
    # 것6. ...
    # --------------------------------------------------------

    compact_number_pattern = re.compile(
        r"(?P<before>[가-힣\)\]\}])"
        r"(?P<num>[1-9][0-9]?)\."
        r"(?=\s*(?:[가-힣「『\"“\(]))"
    )

    def replace_compact_number(
        match: re.Match,
    ) -> str:

        before = match.group(
            "before"
        )

        number = match.group(
            "num"
        )

        if before == "제":
            return match.group(
                0
            )

        return (
            f"{before}"
            f"\n"
            f"{number}. "
        )

    text = (
        compact_number_pattern.sub(
            replace_compact_number,
            text,
        )
    )

    # --------------------------------------------------------
    # 3. 공백 뒤 숫자.
    # --------------------------------------------------------

    text = re.sub(
        r"(?<!\d)"
        r"(?<!제)"
        r"(?<!\.)"
        r"\s+"
        r"([1-9][0-9]?)\.\s*",
        r"\n\1. ",
        text,
    )

    return text


# ============================================================
# 항 분리
# ============================================================

def split_paragraphs(
    text: str,
) -> List[
    Tuple[
        Optional[str],
        str,
    ]
]:

    text = clean_text(
        text
    )

    text = (
        insert_paragraph_boundaries(
            text
        )
    )

    text = (
        insert_no_space_ho_boundaries(
            text
        )
    )

    matches = list(
        re.finditer(
            r"("
            r"[①②③④⑤⑥⑦⑧⑨⑩"
            r"⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]"
            r")",
            text,
        )
    )

    if not matches:
        return [
            (
                None,
                text,
            )
        ]

    result = []

    prefix = text[
        :matches[0].start()
    ].strip()

    if prefix:
        result.append(
            (
                None,
                prefix,
            )
        )

    for i, match in enumerate(
        matches
    ):

        marker = match.group(
            1
        )

        start = match.end()

        if (
            i + 1
            < len(
                matches
            )
        ):
            end = (
                matches[
                    i + 1
                ].start()
            )
        else:
            end = len(
                text
            )

        body = text[
            start:end
        ].strip()

        if body:
            result.append(
                (
                    marker,
                    body,
                )
            )

    return result


# ============================================================
# 호 분리
# ============================================================

def is_probable_ho_marker(
    text: str,
    start: int,
    end: int,
    number: str,
) -> bool:

    before = text[
        max(
            0,
            start - 15,
        ):
        start
    ]

    after = text[
        end:
        end + 40
    ]

    if (
        start > 0
        and text[
            start - 1
        ].isdigit()
    ):
        return False

    if (
        end < len(
            text
        )
        and text[
            end:
            end + 1
        ].isdigit()
    ):
        return False

    if re.search(
        r"\d{4}\.$",
        before,
    ):
        return False

    if before.endswith(
        "제"
    ):
        return False

    if not after.strip():
        return False

    return True


def split_hos(
    text: str,
) -> List[
    Tuple[
        Optional[str],
        str,
    ]
]:

    text = (
        insert_no_space_ho_boundaries(
            text
        )
    )

    pattern = re.compile(
        r"(?:(?<=^)|(?<=\n)|(?<=\s))"
        r"([1-9][0-9]?)\.\s*"
    )

    matches = []

    for match in pattern.finditer(
        text
    ):

        if is_probable_ho_marker(
            text,
            match.start(),
            match.end(),
            match.group(
                1
            ),
        ):
            matches.append(
                match
            )

    if not matches:
        return [
            (
                None,
                text.strip(),
            )
        ]

    result = []

    prefix = text[
        :matches[
            0
        ].start()
    ].strip()

    if prefix:
        result.append(
            (
                None,
                prefix,
            )
        )

    for i, match in enumerate(
        matches
    ):

        ho = match.group(
            1
        )

        start = match.end()

        if (
            i + 1
            < len(
                matches
            )
        ):
            end = (
                matches[
                    i + 1
                ].start()
            )
        else:
            end = len(
                text
            )

        body = text[
            start:end
        ].strip()

        if body:
            result.append(
                (
                    ho,
                    body,
                )
            )

    return result


# ============================================================
# 목 분리
# ============================================================

def find_mok_candidates(
    text: str,
) -> Dict[
    str,
    List[int],
]:

    candidates = {
        letter: []
        for letter
        in MOK_LETTERS
    }

    for letter in MOK_LETTERS:

        pattern = re.compile(
            re.escape(
                letter
            )
            + r"\.\s*"
        )

        for match in pattern.finditer(
            text
        ):

            candidates[
                letter
            ].append(
                match.start()
            )

    return candidates


def choose_ordered_mok_positions(
    text: str,
) -> List[
    Tuple[
        str,
        int,
    ]
]:

    candidates = (
        find_mok_candidates(
            text
        )
    )

    if not candidates[
        "가"
    ]:
        return []

    selected: List[
        Tuple[
            str,
            int,
        ]
    ] = []

    context_positions = []

    for keyword in [
        "다음 각 목",
        "각 목",
        "다음 각목",
        "각목",
        "할 것",
    ]:

        idx = text.find(
            keyword
        )

        if idx >= 0:
            context_positions.append(
                idx
            )

    if context_positions:

        context_start = min(
            context_positions
        )

        ga_candidates = [
            pos
            for pos
            in candidates[
                "가"
            ]
            if pos
            >= context_start
        ]

        if ga_candidates:
            current_pos = (
                ga_candidates[
                    0
                ]
            )
        else:
            current_pos = (
                candidates[
                    "가"
                ][0]
            )

    else:
        current_pos = (
            candidates[
                "가"
            ][0]
        )

    selected.append(
        (
            "가",
            current_pos,
        )
    )

    for letter in MOK_LETTERS[
        1:
    ]:

        positions = [
            pos
            for pos
            in candidates[
                letter
            ]
            if pos
            > current_pos
        ]

        if not positions:
            break

        chosen = positions[
            0
        ]

        if (
            letter == "다"
            and len(
                positions
            ) > 1
        ):

            next_letter_positions = [
                pos
                for pos
                in candidates[
                    "라"
                ]
                if pos
                > current_pos
            ]

            if next_letter_positions:

                next_pos = (
                    next_letter_positions[
                        0
                    ]
                )

                before_next = [
                    pos
                    for pos
                    in positions
                    if pos
                    < next_pos
                ]

                if before_next:
                    chosen = (
                        before_next[
                            -1
                        ]
                    )

        selected.append(
            (
                letter,
                chosen,
            )
        )

        current_pos = (
            chosen
        )

    if len(
        selected
    ) < 2:
        return []

    return selected


def split_moks(
    text: str,
) -> List[
    Tuple[
        Optional[str],
        str,
    ]
]:

    positions = (
        choose_ordered_mok_positions(
            text
        )
    )

    if not positions:
        return [
            (
                None,
                text.strip(),
            )
        ]

    result = []

    first_pos = (
        positions[
            0
        ][1]
    )

    prefix = text[
        :first_pos
    ].strip()

    if prefix:
        result.append(
            (
                None,
                prefix,
            )
        )

    for i, (
        letter,
        pos,
    ) in enumerate(
        positions
    ):

        marker_end = (
            pos
            + len(
                letter
            )
            + 1
        )

        if (
            i + 1
            < len(
                positions
            )
        ):
            end = (
                positions[
                    i + 1
                ][1]
            )
        else:
            end = len(
                text
            )

        body = text[
            marker_end:
            end
        ].strip()

        if body:
            result.append(
                (
                    letter,
                    body,
                )
            )

    return result


# ============================================================
# 용도지역 추출
# ============================================================

def extract_exact_zones(
    text: str,
) -> List[str]:

    zones = []

    for zone in sorted(
        EXACT_ZONES,
        key=len,
        reverse=True,
    ):

        if zone in text:
            zones.append(
                zone
            )

    return list(
        dict.fromkeys(
            zones
        )
    )


def mask_exact_zones(
    text: str,
) -> str:

    masked = text

    for i, zone in enumerate(
        sorted(
            EXACT_ZONES,
            key=len,
            reverse=True,
        )
    ):

        masked = masked.replace(
            zone,
            f"__ZONE_{i}__",
        )

    return masked


def extract_zone_groups(
    text: str,
) -> List[str]:
    """
    정확한 용도지역 문자열을 먼저 마스킹한 뒤
    그룹명을 추출한다.

    추가로 그룹간 substring 중복도 제거한다.

    예:
        일반주거지역
    이 있으면
        주거지역
    을 중복 그룹으로 잡지 않는다.
    """

    masked = mask_exact_zones(
        text
    )

    groups = []

    ordered_groups = sorted(
        ZONE_GROUPS.keys(),
        key=len,
        reverse=True,
    )

    working = masked

    for group in ordered_groups:

        if group not in working:
            continue

        groups.append(
            group
        )

        working = (
            working.replace(
                group,
                " ",
            )
        )

    return groups


def target_belongs_to_group(
    target_zone: str,
    group: str,
) -> bool:

    return (
        target_zone
        in ZONE_GROUPS.get(
            group,
            set(),
        )
    )


# ============================================================
# 용도지역 한정표현
# ============================================================

def has_restrictive_zone_qualifier(
    text: str,
    target_zone: str,
) -> Optional[str]:
    """
    도시지역이라는 큰 그룹이 등장하더라도
    괄호 등에서 실제 적용 대상을 더 좁힌 경우 처리.

    예:
        도시지역(녹지지역만 해당한다)
        도시지역 중 녹지지역
    """

    normalized = compact_spaces(
        text
    )

    green_only_patterns = [
        r"도시지역\s*\(\s*녹지지역만\s*해당",
        r"도시지역\s*중\s*녹지지역",
        r"도시지역.*녹지지역만\s*해당",
    ]

    if any(
        re.search(
            pattern,
            normalized,
        )
        for pattern
        in green_only_patterns
    ):

        if not target_belongs_to_group(
            target_zone,
            "녹지지역",
        ):
            return (
                "도시지역 중 녹지지역에만 "
                "적용되는 한정 규정"
            )

    return None


# ============================================================
# 도시지역 외 배제
# ============================================================

def is_outside_urban_only(
    law_name: str,
    rule_title: str,
    text: str,
    target_zone: str,
) -> bool:

    combined = " ".join(
        [
            law_name,
            rule_title,
            text,
        ]
    )

    markers = [
        "도시지역 외 지구단위계획구역",
        "도시지역 외에 지정",
        "도시지역 외의 지역",
    ]

    if not any(
        marker in combined
        for marker
        in markers
    ):
        return False

    if target_belongs_to_group(
        target_zone,
        "도시지역",
    ):
        return True

    return False


# ============================================================
# 용도지역 판정
# ============================================================

def classify_zone_relevance(
    target_zone: str,
    own_text: str,
    inherited_context: str,
    law_name: str,
    rule_title: str,
) -> Dict[str, Any]:

    own_exact = (
        extract_exact_zones(
            own_text
        )
    )

    own_groups = (
        extract_zone_groups(
            own_text
        )
    )

    parent_exact = (
        extract_exact_zones(
            inherited_context
        )
    )

    parent_groups = (
        extract_zone_groups(
            inherited_context
        )
    )

    # --------------------------------------------------------
    # 0. 도시지역 외 전용
    # --------------------------------------------------------

    if is_outside_urban_only(
        law_name,
        rule_title,
        own_text
        + " "
        + inherited_context,
        target_zone,
    ):

        return {
            "status":
                "OTHER_ZONE",

            "reason":
                (
                    "도시지역 외에만 적용되는 "
                    "규정이므로 대상 도시지역 "
                    "SITE에서 제외"
                ),

            "zones":
                own_exact,

            "groups":
                own_groups,

            "matched_groups":
                [],
        }

    # --------------------------------------------------------
    # 0-1. 한정조건
    # --------------------------------------------------------

    qualifier_reason = (
        has_restrictive_zone_qualifier(
            own_text,
            target_zone,
        )
    )

    if qualifier_reason:

        return {
            "status":
                "OTHER_ZONE",

            "reason":
                qualifier_reason,

            "zones":
                own_exact,

            "groups":
                own_groups,

            "matched_groups":
                [],
        }

    # --------------------------------------------------------
    # 1. 현재 clause 정확지역
    # --------------------------------------------------------

    if own_exact:

        if target_zone in own_exact:

            return {
                "status":
                    "DIRECT",

                "reason":
                    (
                        f"{target_zone} 직접 명시"
                    ),

                "zones":
                    own_exact,

                "groups":
                    own_groups,

                "matched_groups":
                    [],
            }

        return {
            "status":
                "OTHER_ZONE",

            "reason":
                (
                    "세부 규정이 정확한 "
                    "용도지역을 열거하고 있으나 "
                    f"{target_zone}은 해당 목록에 없음"
                ),

            "zones":
                own_exact,

            "groups":
                own_groups,

            "matched_groups":
                [],
        }

    # --------------------------------------------------------
    # 2. 현재 clause 그룹
    #
    # 부모 정확지역보다 own group을 먼저 판단.
    # leaf가 명확한 그룹을 가지고 있으면 그것이 우선.
    # --------------------------------------------------------

    matched_groups = [
        group
        for group
        in own_groups
        if target_belongs_to_group(
            target_zone,
            group,
        )
    ]

    if matched_groups:

        return {
            "status":
                "GROUP",

            "reason":
                (
                    f"{', '.join(matched_groups)} "
                    f"규정에 {target_zone} 포함"
                ),

            "zones":
                [],

            "groups":
                own_groups,

            "matched_groups":
                matched_groups,
        }

    if own_groups:

        return {
            "status":
                "OTHER_ZONE",

            "reason":
                (
                    f"{', '.join(own_groups)} "
                    f"규정은 {target_zone}에 "
                    "해당하지 않음"
                ),

            "zones":
                [],

            "groups":
                own_groups,

            "matched_groups":
                [],
        }

    # --------------------------------------------------------
    # 3. 상위 정확지역
    # --------------------------------------------------------

    if parent_exact:

        if target_zone in parent_exact:

            return {
                "status":
                    "DIRECT",

                "reason":
                    (
                        "상위 문맥에서 "
                        f"{target_zone} 직접 명시"
                    ),

                "zones":
                    parent_exact,

                "groups":
                    [],

                "matched_groups":
                    [],
            }

        return {
            "status":
                "OTHER_ZONE",

            "reason":
                (
                    "상위 문맥이 정확한 "
                    "용도지역을 제한적으로 열거하며 "
                    f"{target_zone}은 해당 목록에 없음"
                ),

            "zones":
                parent_exact,

            "groups":
                [],

            "matched_groups":
                [],
        }

    # --------------------------------------------------------
    # 4. 상위 그룹
    # --------------------------------------------------------

    parent_qualifier = (
        has_restrictive_zone_qualifier(
            inherited_context,
            target_zone,
        )
    )

    if parent_qualifier:

        return {
            "status":
                "OTHER_ZONE",

            "reason":
                parent_qualifier,

            "zones":
                [],

            "groups":
                parent_groups,

            "matched_groups":
                [],
        }

    parent_matched_groups = [
        group
        for group
        in parent_groups
        if target_belongs_to_group(
            target_zone,
            group,
        )
    ]

    if parent_matched_groups:

        return {
            "status":
                "GROUP",

            "reason":
                (
                    "상위 문맥의 "
                    f"{', '.join(parent_matched_groups)} "
                    f"규정에 {target_zone} 포함"
                ),

            "zones":
                [],

            "groups":
                parent_groups,

            "matched_groups":
                parent_matched_groups,
        }

    if parent_groups:

        return {
            "status":
                "OTHER_ZONE",

            "reason":
                (
                    "상위 문맥의 "
                    f"{', '.join(parent_groups)} "
                    f"규정은 {target_zone}에 "
                    "해당하지 않음"
                ),

            "zones":
                [],

            "groups":
                parent_groups,

            "matched_groups":
                [],
        }

    return {
        "status":
            "UNSPECIFIED",

        "reason":
            (
                "세부 규정 자체와 상위 문맥에서 "
                "용도지역을 특정하지 않음"
            ),

        "zones":
            [],

        "groups":
            [],

        "matched_groups":
            [],
    }


# ============================================================
# 효과 / 수치
# ============================================================

def detect_effect_targets(
    text: str,
) -> List[str]:

    targets = []

    if "건폐율" in text:

        targets.append(
            "building_coverage_ratio"
        )

    if "용적률" in text:

        targets.append(
            "floor_area_ratio"
        )

    if (
        "높이제한" in text
        or "건축물높이" in text
        or "건축물의 높이" in text
        or re.search(
            r"\b높이\b",
            text,
        )
    ):

        targets.append(
            "height"
        )

    return targets


def extract_percent_values(
    text: str,
) -> List[float]:

    values: List[
        float
    ] = []

    normalized = re.sub(
        r"(\d)천(\d{3})",
        lambda m:
            str(
                int(
                    m.group(
                        1
                    )
                )
                * 1000
                + int(
                    m.group(
                        2
                    )
                )
            ),
        text,
    )

    normalized = re.sub(
        r"(\d)천(?=\s*퍼센트)",
        lambda m:
            str(
                int(
                    m.group(
                        1
                    )
                )
                * 1000
            ),
        normalized,
    )

    patterns = [
        r"(\d+(?:\.\d+)?)\s*퍼센트",
        r"(\d+(?:\.\d+)?)\s*%",
    ]

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            normalized,
        ):

            try:
                value = float(
                    match.group(
                        1
                    )
                )

            except ValueError:
                continue

            if value not in values:
                values.append(
                    value
                )

    return values


# ============================================================
# 조건 추출
# ============================================================

def detect_conditions(
    text: str,
) -> List[
    Dict[
        str,
        str,
    ]
]:

    result: List[
        Dict[
            str,
            str,
        ]
    ] = []

    def add_condition(
        name: str,
        condition_type: str,
    ):

        key = (
            name,
            condition_type,
        )

        if not any(
            (
                x["name"],
                x["type"],
            )
            == key
            for x
            in result
        ):

            result.append(
                {
                    "name":
                        name,

                    "type":
                        condition_type,
                }
            )

    for (
        name,
        keywords,
    ) in SITE_CONDITIONS.items():

        if any(
            keyword in text
            for keyword
            in keywords
        ):

            add_condition(
                name,
                "SITE",
            )

    for (
        name,
        keywords,
    ) in SITE_HISTORY_CONDITIONS.items():

        if any(
            keyword in text
            for keyword
            in keywords
        ):

            add_condition(
                name,
                "SITE_HISTORY",
            )

    for (
        name,
        keywords,
    ) in PROJECT_CONDITIONS.items():

        if any(
            keyword in text
            for keyword
            in keywords
        ):

            add_condition(
                name,
                "PROJECT",
            )

    for (
        name,
        keywords,
    ) in PROCEDURE_CONDITIONS.items():

        if any(
            keyword in text
            for keyword
            in keywords
        ):

            add_condition(
                name,
                "PROCEDURE",
            )

    return result


# ============================================================
# Clause 생성
# ============================================================

def make_clause(
    candidate: Dict[str, Any],
    paragraph: Optional[str],
    ho: Optional[str],
    mok: Optional[str],
    text: str,
    inherited_context: str,
    target_zone: str,
) -> Dict[str, Any]:

    law_name = (
        candidate[
            "law_name"
        ]
    )

    rule_title = (
        candidate[
            "rule_title"
        ]
    )

    category = (
        candidate[
            "category"
        ]
    )

    own_text = clean_text(
        text
    )

    parent_text = clean_text(
        inherited_context
    )

    relevance = (
        classify_zone_relevance(
            target_zone=
                target_zone,

            own_text=
                own_text,

            inherited_context=
                parent_text,

            law_name=
                law_name,

            rule_title=
                rule_title,
        )
    )

    combined_for_conditions = (
        compact_spaces(
            " ".join(
                [
                    parent_text,
                    own_text,
                ]
            )
        )
    )

    effects = (
        detect_effect_targets(
            combined_for_conditions
        )
    )

    numeric_values = (
        extract_percent_values(
            own_text
        )
    )

    conditions = (
        detect_conditions(
            combined_for_conditions
        )
    )

    return {
        "category":
            category,

        "law_name":
            law_name,

        "rule_title":
            rule_title,

        "paragraph":
            paragraph,

        "item":
            ho,

        "subitem":
            mok,

        "zone_relevance":
            relevance[
                "status"
            ],

        "zone_reason":
            relevance[
                "reason"
            ],

        "zones":
            relevance[
                "zones"
            ],

        "zone_groups":
            relevance[
                "groups"
            ],

        "matched_zone_groups":
            relevance[
                "matched_groups"
            ],

        "effect_targets":
            effects,

        "conditions":
            conditions,

        "numeric_values":
            numeric_values,

        "inherited_context":
            parent_text,

        "text":
            own_text,
    }


# ============================================================
# Clause 세분화
# ============================================================

def split_candidate(
    candidate: Dict[str, Any],
    target_zone: str,
) -> List[
    Dict[
        str,
        Any,
    ]
]:

    raw_text = clean_text(
        candidate[
            "text"
        ]
    )

    clauses: List[
        Dict[
            str,
            Any,
        ]
    ] = []

    paragraph_parts = (
        split_paragraphs(
            raw_text
        )
    )

    for (
        paragraph,
        paragraph_text,
    ) in paragraph_parts:

        # ----------------------------------------------------
        # 항 container
        # ----------------------------------------------------

        paragraph_clause = (
            make_clause(
                candidate=
                    candidate,

                paragraph=
                    paragraph,

                ho=
                    None,

                mok=
                    None,

                text=
                    paragraph_text,

                inherited_context=
                    "",

                target_zone=
                    target_zone,
            )
        )

        clauses.append(
            paragraph_clause
        )

        # ----------------------------------------------------
        # 호
        # ----------------------------------------------------

        ho_parts = split_hos(
            paragraph_text
        )

        if (
            len(
                ho_parts
            ) == 1
            and ho_parts[
                0
            ][0]
            is None
        ):

            # ----------------------------------------------
            # 호 없이 바로 목인 구조
            # ----------------------------------------------

            mok_parts = split_moks(
                paragraph_text
            )

            if (
                len(
                    mok_parts
                ) == 1
                and mok_parts[
                    0
                ][0]
                is None
            ):
                continue

            # 목 상위 문맥은 목 목록 전체가 아닌
            # 첫 목 앞의 머리문만 사용
            mok_positions = (
                choose_ordered_mok_positions(
                    paragraph_text
                )
            )

            if mok_positions:

                mok_parent_context = (
                    paragraph_text[
                        :
                        mok_positions[
                            0
                        ][1]
                    ].strip()
                )

            else:
                mok_parent_context = (
                    paragraph_text
                )

            for (
                mok,
                mok_text,
            ) in mok_parts:

                if mok is None:
                    continue

                clauses.append(
                    make_clause(
                        candidate=
                            candidate,

                        paragraph=
                            paragraph,

                        ho=
                            None,

                        mok=
                            mok,

                        text=
                            mok_text,

                        inherited_context=
                            mok_parent_context,

                        target_zone=
                            target_zone,
                    )
                )

            continue

        # ----------------------------------------------------
        # 호가 존재하는 구조
        # ----------------------------------------------------

        # 항 머리문:
        # 첫 호 이전까지만 상속
        first_real_ho_pos = None

        prepared_paragraph = (
            insert_no_space_ho_boundaries(
                paragraph_text
            )
        )

        ho_marker_match = re.search(
            r"(?:(?<=^)|(?<=\n)|(?<=\s))"
            r"[1-9][0-9]?\.\s*",
            prepared_paragraph,
        )

        if ho_marker_match:
            first_real_ho_pos = (
                ho_marker_match.start()
            )

        if (
            first_real_ho_pos
            is not None
        ):
            paragraph_parent_context = (
                prepared_paragraph[
                    :
                    first_real_ho_pos
                ].strip()
            )
        else:
            paragraph_parent_context = (
                paragraph_text
            )

        for (
            ho,
            ho_text,
        ) in ho_parts:

            if ho is None:
                continue

            # ----------------------------------------------
            # 해당 호 container
            # ----------------------------------------------

            ho_clause = (
                make_clause(
                    candidate=
                        candidate,

                    paragraph=
                        paragraph,

                    ho=
                        ho,

                    mok=
                        None,

                    text=
                        ho_text,

                    inherited_context=
                        paragraph_parent_context,

                    target_zone=
                        target_zone,
                )
            )

            clauses.append(
                ho_clause
            )

            # ----------------------------------------------
            # 목
            # ----------------------------------------------

            mok_parts = split_moks(
                ho_text
            )

            if (
                len(
                    mok_parts
                ) == 1
                and mok_parts[
                    0
                ][0]
                is None
            ):
                continue

            mok_positions = (
                choose_ordered_mok_positions(
                    ho_text
                )
            )

            if mok_positions:

                ho_intro = (
                    ho_text[
                        :
                        mok_positions[
                            0
                        ][1]
                    ].strip()
                )

            else:
                ho_intro = (
                    ho_text
                )

            child_context = (
                compact_spaces(
                    " ".join(
                        [
                            paragraph_parent_context,
                            ho_intro,
                        ]
                    )
                )
            )

            for (
                mok,
                mok_text,
            ) in mok_parts:

                if mok is None:
                    continue

                clauses.append(
                    make_clause(
                        candidate=
                            candidate,

                        paragraph=
                            paragraph,

                        ho=
                            ho,

                        mok=
                            mok,

                        text=
                            mok_text,

                        inherited_context=
                            child_context,

                        target_zone=
                            target_zone,
                    )
                )

    return clauses


# ============================================================
# 중복 제거
# ============================================================

def clause_identity(
    clause: Dict[str, Any],
) -> Tuple:

    return (
        clause.get(
            "law_name"
        ),

        clause.get(
            "rule_title"
        ),

        clause.get(
            "paragraph"
        ),

        clause.get(
            "item"
        ),

        clause.get(
            "subitem"
        ),

        clean_text(
            clause.get(
                "text",
                "",
            )
        ),
    )


def merge_duplicate_clauses(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> List[
    Dict[
        str,
        Any,
    ]
]:

    merged: Dict[
        Tuple,
        Dict[
            str,
            Any,
        ],
    ] = {}

    for clause in clauses:

        key = clause_identity(
            clause
        )

        if key not in merged:

            item = deepcopy(
                clause
            )

            source_categories = []

            if item.get(
                "category"
            ):

                source_categories.append(
                    item[
                        "category"
                    ]
                )

            item[
                "source_categories"
            ] = (
                source_categories
            )

            merged[
                key
            ] = item

            continue

        base = merged[
            key
        ]

        category = clause.get(
            "category"
        )

        if (
            category
            and category
            not in base[
                "source_categories"
            ]
        ):

            base[
                "source_categories"
            ].append(
                category
            )

        for target in clause.get(
            "effect_targets",
            [],
        ):

            if target not in base[
                "effect_targets"
            ]:

                base[
                    "effect_targets"
                ].append(
                    target
                )

        existing_conditions = {
            (
                x[
                    "name"
                ],
                x[
                    "type"
                ],
            )
            for x
            in base.get(
                "conditions",
                [],
            )
        }

        for condition in clause.get(
            "conditions",
            [],
        ):

            key2 = (
                condition[
                    "name"
                ],
                condition[
                    "type"
                ],
            )

            if (
                key2
                not in
                existing_conditions
            ):

                base[
                    "conditions"
                ].append(
                    condition
                )

                existing_conditions.add(
                    key2
                )

        for value in clause.get(
            "numeric_values",
            [],
        ):

            if value not in base[
                "numeric_values"
            ]:

                base[
                    "numeric_values"
                ].append(
                    value
                )

    return list(
        merged.values()
    )


# ============================================================
# 조건 집계
# ============================================================

def collect_condition_names(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
    condition_type: str,
) -> List[str]:

    names = set()

    for clause in clauses:

        if clause.get(
            "zone_relevance"
        ) == "OTHER_ZONE":
            continue

        for condition in clause.get(
            "conditions",
            [],
        ):

            if (
                condition.get(
                    "type"
                )
                == condition_type
            ):

                names.add(
                    condition.get(
                        "name"
                    )
                )

    return sorted(
        name
        for name
        in names
        if name
    )


# ============================================================
# 자동 검증
# ============================================================

def has_bad_revision_fragment(
    clause: Dict[str, Any],
) -> bool:

    text = clause.get(
        "text",
        "",
    )

    return bool(
        re.fullmatch(
            r"\d{1,2}\s*,?\s*\d{4}\.?",
            text.strip(),
        )
    )


def validation_revision_fragments(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> bool:

    return not any(
        has_bad_revision_fragment(
            clause
        )
        for clause
        in clauses
    )


def validation_outside_urban(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> bool:

    for clause in clauses:

        combined = " ".join(
            [
                clause.get(
                    "rule_title",
                    "",
                ),

                clause.get(
                    "text",
                    "",
                ),

                clause.get(
                    "inherited_context",
                    "",
                ),
            ]
        )

        if (
            "도시지역 외"
            in combined
            and clause.get(
                "zone_relevance"
            )
            in {
                "DIRECT",
                "GROUP",
            }
        ):
            return False

    return True


def validation_other_group_exclusion(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
    forbidden_group: str,
) -> bool:
    """
    C-8-8

    다른 용도지역의 leaf clause가
    제3종일반주거지역 관련 규정으로 살아있는지 검사.

    여러 용도지역을 한꺼번에 담은
    parent/container clause는 정상으로 인정.
    """

    transition_markers = [
        "녹지지역에서 해제",
        "공원에서 해제",
        "개발제한구역",
        "시가화조정구역",
        "도시지역으로 편입",
        "새로이 도시지역으로 편입",
    ]

    for clause in clauses:

        relevance = clause.get(
            "zone_relevance"
        )

        if relevance not in {
            "DIRECT",
            "GROUP",
        }:
            continue

        own_text = clause.get(
            "text",
            "",
        )

        if any(
            marker in own_text
            for marker
            in transition_markers
        ):
            continue

        own_exact = (
            extract_exact_zones(
                own_text
            )
        )

        own_groups = (
            extract_zone_groups(
                own_text
            )
        )

        if (
            forbidden_group
            not in own_groups
        ):
            continue

        # 정확지역 여러 개가 포함된 부모 container
        if own_exact:
            continue

        target_matching_groups = [
            group
            for group
            in own_groups
            if target_belongs_to_group(
                TARGET_DEFAULT_ZONE,
                group,
            )
        ]

        # 주거지역 등 대상 그룹도 함께 있는 부모 container
        if target_matching_groups:
            continue

        # leaf인데 금지 그룹만 있는데
        # 관련 규정으로 살아 있다면 실패
        return False

    return True


def validation_nested_zone_group_removed(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> bool:

    bad_pairs = [
        (
            "일반주거지역",
            "주거지역",
        ),
        (
            "전용주거지역",
            "주거지역",
        ),
    ]

    for clause in clauses:

        own_text = clause.get(
            "text",
            "",
        )

        groups = clause.get(
            "zone_groups",
            [],
        )

        # 문구 자체가 실제로 두 그룹을
        # 별개로 언급한 경우는 허용.
        for (
            specific,
            generic,
        ) in bad_pairs:

            if (
                specific in groups
                and generic in groups
            ):

                masked = (
                    mask_exact_zones(
                        own_text
                    )
                )

                specific_count = (
                    masked.count(
                        specific
                    )
                )

                generic_only = (
                    masked.replace(
                        specific,
                        "",
                    )
                )

                if (
                    specific_count > 0
                    and generic
                    not in generic_only
                ):
                    return False

    return True


def validation_urban_green_only_excluded(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> bool:

    for clause in clauses:

        combined = compact_spaces(
            clause.get(
                "text",
                "",
            )
            + " "
            + clause.get(
                "inherited_context",
                "",
            )
        )

        if (
            "도시지역"
            not in combined
            or "녹지지역만"
            not in combined
        ):
            continue

        if clause.get(
            "zone_relevance"
        ) in {
            "DIRECT",
            "GROUP",
        }:
            return False

    return True


def validation_multi_mok_direct(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> bool:
    """
    DIRECT 최종 목 leaf 내부에
    형제 목이 다시 남아있는 경우만 오류.

    parent 항/호 container는 허용.
    """

    for clause in clauses:

        if clause.get(
            "zone_relevance"
        ) != "DIRECT":
            continue

        if clause.get(
            "subitem"
        ) is None:
            continue

        text = clause.get(
            "text",
            "",
        )

        positions = (
            choose_ordered_mok_positions(
                text
            )
        )

        if len(
            positions
        ) >= 2:
            return False

    return True


def validation_sentence_da_not_mok(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> bool:

    for clause in clauses:

        if clause.get(
            "subitem"
        ) != "다":
            continue

        text = clause.get(
            "text",
            "",
        ).strip()

        if len(
            text
        ) <= 2:
            return False

    return True


def validation_article46_para15(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> bool:

    relevant = []

    for clause in clauses:

        if clause.get(
            "paragraph"
        ) != "⑮":
            continue

        context = (
            clause.get(
                "inherited_context",
                "",
            )
            + " "
            + clause.get(
                "text",
                "",
            )
        )

        if (
            "제1종전용주거지역"
            in context
            and
            "제2종전용주거지역"
            in context
            and
            "제1종일반주거지역"
            in context
            and
            "제2종일반주거지역"
            in context
        ):
            relevant.append(
                clause
            )

    if not relevant:
        return True

    return all(
        clause.get(
            "zone_relevance"
        )
        == "OTHER_ZONE"
        for clause
        in relevant
    )


def validation_market_mok_split(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> bool:

    candidates = [
        clause
        for clause
        in clauses
        if (
            "시장정비사업"
            in (
                clause.get(
                    "inherited_context",
                    "",
                )
                + " "
                + clause.get(
                    "text",
                    "",
                )
            )
            and
            clause.get(
                "subitem"
            )
            == "나"
            and
            "제3종일반주거지역"
            in clause.get(
                "text",
                "",
            )
        )
    ]

    if not candidates:
        return False

    return any(
        60.0
        in clause.get(
            "numeric_values",
            [],
        )
        and
        clause.get(
            "zone_relevance"
        )
        == "DIRECT"
        for clause
        in candidates
    )


def validation_market_other_zone_excluded(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> bool:

    candidates = [
        clause
        for clause
        in clauses
        if (
            "시장정비사업"
            in (
                clause.get(
                    "inherited_context",
                    "",
                )
                + " "
                + clause.get(
                    "text",
                    "",
                )
            )
            and
            clause.get(
                "subitem"
            )
            == "다"
            and
            "상업지역"
            in clause.get(
                "text",
                "",
            )
        )
    ]

    if not candidates:
        return True

    return all(
        clause.get(
            "zone_relevance"
        )
        == "OTHER_ZONE"
        for clause
        in candidates
    )


def validation_school_site_split(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> bool:

    candidates = [
        clause
        for clause
        in clauses
        if (
            clause.get(
                "subitem"
            )
            == "바"
            and
            "제3종일반주거지역"
            in clause.get(
                "text",
                "",
            )
            and
            "학교이적지"
            in (
                clause.get(
                    "inherited_context",
                    "",
                )
                + " "
                + clause.get(
                    "text",
                    "",
                )
            )
        )
    ]

    if not candidates:
        return False

    return any(
        200.0
        in clause.get(
            "numeric_values",
            [],
        )
        and
        clause.get(
            "zone_relevance"
        )
        == "DIRECT"
        for clause
        in candidates
    )


def validation_school_other_zones_excluded(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> bool:

    other_subitems = {
        "가",
        "나",
        "다",
        "라",
        "마",
    }

    found = False

    for clause in clauses:

        combined = (
            clause.get(
                "inherited_context",
                "",
            )
            + " "
            + clause.get(
                "text",
                "",
            )
        )

        if (
            "학교이적지"
            not in combined
        ):
            continue

        if clause.get(
            "subitem"
        ) not in other_subitems:
            continue

        found = True

        if clause.get(
            "zone_relevance"
        ) in {
            "DIRECT",
            "GROUP",
        }:
            return False

    return True


def validation_compact_following_ho_split(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> bool:
    """
    서울시 도시계획조례 용적률의 완화 ②항에서

        1호 사목
        2호
        3호
        ...
        8호

    가 서로 독립돼 있어야 한다.
    """

    target_clauses = [
        clause
        for clause
        in clauses
        if (
            clause.get(
                "law_name"
            )
            == "서울특별시 도시계획 조례"
            and
            clause.get(
                "rule_title"
            )
            == "용적률의 완화"
            and
            clause.get(
                "paragraph"
            )
            == "②"
        )
    ]

    if not target_clauses:
        return True

    # --------------------------------------------------------
    # 제2호 확인
    # --------------------------------------------------------

    ho2 = [
        clause
        for clause
        in target_clauses
        if (
            clause.get(
                "item"
            )
            == "2"
            and
            clause.get(
                "subitem"
            )
            is None
        )
    ]

    if not ho2:
        return False

    if not any(
        (
            "제3종일반주거지역"
            in clause.get(
                "text",
                "",
            )
            and
            300.0
            in clause.get(
                "numeric_values",
                [],
            )
        )
        for clause
        in ho2
    ):
        return False

    # --------------------------------------------------------
    # 사목 오염 검사
    # --------------------------------------------------------

    sa_clauses = [
        clause
        for clause
        in target_clauses
        if (
            clause.get(
                "item"
            )
            == "1"
            and
            clause.get(
                "subitem"
            )
            == "사"
        )
    ]

    for clause in sa_clauses:

        text = clause.get(
            "text",
            "",
        )

        forbidden_fragments = [
            "제3종일반주거지역은 300퍼센트",
            "종합의료시설 부지",
            "시장정비사업 추진계획 승인대상 전통시장",
            "도시계획시설인 대학에 세부시설조성계획",
        ]

        if any(
            fragment in text
            for fragment
            in forbidden_fragments
        ):
            return False

    # --------------------------------------------------------
    # 후속 호 존재 확인
    # --------------------------------------------------------

    expected_items = {
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
    }

    actual_items = {
        str(
            clause.get(
                "item"
            )
        )
        for clause
        in target_clauses
        if clause.get(
            "item"
        )
        is not None
    }

    if not expected_items.issubset(
        actual_items
    ):
        return False

    return True


def run_validations(
    clauses: List[
        Dict[
            str,
            Any,
        ]
    ],
) -> Dict[
    str,
    bool,
]:

    return {
        "개정일자 조각 제거":
            validation_revision_fragments(
                clauses
            ),

        "도시지역 외 배제":
            validation_outside_urban(
                clauses
            ),

        "상업지역 → 대상 주거지역 배제":
            validation_other_group_exclusion(
                clauses,
                "상업지역",
            ),

        "공업지역 → 대상 주거지역 배제":
            validation_other_group_exclusion(
                clauses,
                "공업지역",
            ),

        "녹지지역 → 대상 주거지역 배제":
            validation_other_group_exclusion(
                clauses,
                "녹지지역",
            ),

        "용도지역 그룹 substring 중복 제거":
            validation_nested_zone_group_removed(
                clauses
            ),

        "도시지역(녹지지역만) 대상 주거지역 제외":
            validation_urban_green_only_excluded(
                clauses
            ),

        "무공백 후속 호 경계 분리":
            validation_compact_following_ho_split(
                clauses
            ),

        "DIRECT 규정 내부 다중 목 잔존 없음":
            validation_multi_mok_direct(
                clauses
            ),

        "문장 종결 다. → 다목 오인 없음":
            validation_sentence_da_not_mok(
                clauses
            ),

        "제46조 ⑮항 제3종일반주거지역 제외":
            validation_article46_para15(
                clauses
            ),

        "시장정비사업 제3종 60% 나목 분리":
            validation_market_mok_split(
                clauses
            ),

        "시장정비사업 상업지역 다목 제외":
            validation_market_other_zone_excluded(
                clauses
            ),

        "학교이적지 제3종 200% 바목 분리":
            validation_school_site_split(
                clauses
            ),

        "학교이적지 타 용도지역 목 제외":
            validation_school_other_zones_excluded(
                clauses
            ),
    }


# ============================================================
# 로그 출력
# ============================================================

def print_separator(
    char: str = "=",
    width: int = 70,
):

    print(
        char * width
    )


def print_condition_section(
    title: str,
    items: List[str],
):

    print_separator()
    print(
        title
    )
    print_separator()

    if not items:
        print(
            "- 없음"
        )

    else:

        for item in items:

            print(
                f"- {item}"
            )

    print()


def short_text(
    text: str,
    length: int = 650,
) -> str:

    if len(
        text
    ) <= length:
        return text

    return (
        text[
            :length
        ]
        + "..."
    )


def print_clause_example(
    clause: Dict[
        str,
        Any,
    ],
    index: int,
):

    print(
        "-" * 70
    )

    print(
        f"예시 {index}"
    )

    print(
        "카테고리:",
        clause.get(
            "category",
            "",
        ),
    )

    print(
        "법규:",
        clause.get(
            "law_name",
            "",
        ),
    )

    print(
        "규정:",
        clause.get(
            "rule_title",
            "",
        ),
    )

    print(
        "항/호/목:",
        (
            f"{clause.get('paragraph')}"
            f" / {clause.get('item')}"
            f" / {clause.get('subitem')}"
        ),
    )

    print(
        "용도지역 판정:",
        clause.get(
            "zone_relevance"
        ),
    )

    print(
        "판정 이유:",
        clause.get(
            "zone_reason"
        ),
    )

    zones = clause.get(
        "zones",
        [],
    )

    if zones:
        print(
            "용도지역:",
            ", ".join(
                zones
            ),
        )

    groups = clause.get(
        "zone_groups",
        [],
    )

    if groups:
        print(
            "용도지역 그룹:",
            ", ".join(
                groups
            ),
        )

    matched = clause.get(
        "matched_zone_groups",
        [],
    )

    if matched:
        print(
            "실제 매칭 그룹:",
            ", ".join(
                matched
            ),
        )

    effects = clause.get(
        "effect_targets",
        [],
    )

    if effects:
        print(
            "효과 대상:",
            ", ".join(
                effects
            ),
        )

    conditions = clause.get(
        "conditions",
        [],
    )

    if conditions:

        print(
            "조건:"
        )

        for condition in conditions:

            print(
                (
                    f"  - "
                    f"{condition['name']}"
                    f" / "
                    f"{condition['type']}"
                )
            )

    values = clause.get(
        "numeric_values",
        [],
    )

    if values:

        print(
            "수치:",
            ", ".join(
                str(
                    x
                )
                for x
                in values
            ),
        )

    inherited = clause.get(
        "inherited_context",
        "",
    )

    if inherited:

        print(
            "상속 문맥:",
            short_text(
                inherited,
                800,
            ),
        )

    print(
        "본문:",
        short_text(
            clause.get(
                "text",
                "",
            ),
            1000,
        ),
    )


# ============================================================
# 메인
# ============================================================

def main():

    print(
        "=== STEP 17-21-C-8-8 "
        "후속 호 경계 / container-leaf 검증 최종 보정 테스트 ==="
    )

    print()

    print(
        "규정 입력:"
    )

    print(
        INPUT_RULES_PATH
    )

    print()

    print(
        "SITE 입력:"
    )

    print(
        INPUT_SITE_PATH
    )

    print()

    if not INPUT_RULES_PATH.exists():

        raise FileNotFoundError(
            (
                "규정 입력 파일이 없습니다: "
                f"{INPUT_RULES_PATH}"
            )
        )

    if not INPUT_SITE_PATH.exists():

        raise FileNotFoundError(
            (
                "SITE 입력 파일이 없습니다: "
                f"{INPUT_SITE_PATH}"
            )
        )

    rules_data = load_json(
        INPUT_RULES_PATH
    )

    site_data = load_json(
        INPUT_SITE_PATH
    )

    site = extract_site_info(
        site_data
    )

    target_zone = (
        site.get(
            "zone"
        )
        or TARGET_DEFAULT_ZONE
    )

    print_separator()

    print(
        "=== 대상 SITE ==="
    )

    print_separator()

    print(
        "주소:",
        site.get(
            "address",
            "",
        ),
    )

    print(
        "용도지역:",
        target_zone,
    )

    print()

    candidates = (
        collect_rule_candidates(
            rules_data
        )
    )

    print(
        "원본 규정 후보:",
        len(
            candidates
        ),
    )

    print()

    all_clauses = []

    for candidate in candidates:

        all_clauses.extend(
            split_candidate(
                candidate,
                target_zone,
            )
        )

    clauses = (
        merge_duplicate_clauses(
            all_clauses
        )
    )

    counts = {
        "DIRECT": 0,
        "GROUP": 0,
        "UNSPECIFIED": 0,
        "OTHER_ZONE": 0,
    }

    for clause in clauses:

        status = clause.get(
            "zone_relevance"
        )

        if status in counts:
            counts[
                status
            ] += 1

    print_separator()

    print(
        "=== C-8-8 세분화 결과 ==="
    )

    print_separator()

    print(
        "전체 세부 규정:",
        len(
            clauses
        ),
    )

    print(
        "직접 관련:",
        counts[
            "DIRECT"
        ],
    )

    print(
        "그룹 관련:",
        counts[
            "GROUP"
        ],
    )

    print(
        "용도지역 미특정:",
        counts[
            "UNSPECIFIED"
        ],
    )

    print(
        "다른 용도지역 / 적용 제외:",
        counts[
            "OTHER_ZONE"
        ],
    )

    print()

    validations = run_validations(
        clauses
    )

    print_separator()

    print(
        "=== 파서 핵심 검증 ==="
    )

    print_separator()

    for (
        name,
        passed,
    ) in validations.items():

        print(
            (
                f"{name}: "
                f"{'PASS' if passed else 'FAIL'}"
            )
        )

    print()

    site_conditions = (
        collect_condition_names(
            clauses,
            "SITE",
        )
    )

    site_history_conditions = (
        collect_condition_names(
            clauses,
            "SITE_HISTORY",
        )
    )

    project_conditions = (
        collect_condition_names(
            clauses,
            "PROJECT",
        )
    )

    procedure_conditions = (
        collect_condition_names(
            clauses,
            "PROCEDURE",
        )
    )

    print_condition_section(
        "=== C-8-8 재분석 후 필요한 SITE 조건 ===",
        site_conditions,
    )

    print_condition_section(
        "=== SITE HISTORY 조건 ===",
        site_history_conditions,
    )

    print_condition_section(
        "=== PROJECT 입력 조건 ===",
        project_conditions,
    )

    print_condition_section(
        "=== PROCEDURE 조건 ===",
        procedure_conditions,
    )

    relevant_clauses = [
        clause
        for clause
        in clauses
        if clause.get(
            "zone_relevance"
        )
        in {
            "DIRECT",
            "GROUP",
        }
    ]

    relevant_clauses.sort(
        key=lambda x: (
            0
            if x.get(
                "zone_relevance"
            )
            == "DIRECT"
            else 1,

            x.get(
                "law_name",
                "",
            ),

            x.get(
                "paragraph"
            )
            or "",

            int(
                x.get(
                    "item"
                )
            )
            if str(
                x.get(
                    "item"
                )
                or ""
            ).isdigit()
            else 999,

            MOK_LETTERS.index(
                x.get(
                    "subitem"
                )
            )
            if x.get(
                "subitem"
            )
            in MOK_LETTERS
            else 999,
        )
    )

    print_separator()

    print(
        "=== 핵심 관련 규정 예시 ==="
    )

    print_separator()

    print()

    for (
        index,
        clause,
    ) in enumerate(
        relevant_clauses[
            :25
        ],
        start=1,
    ):

        print_clause_example(
            clause,
            index,
        )

        print()

    # ========================================================
    # 지구단위계획 관련 규정
    # ========================================================

    district_clauses = []

    for clause in clauses:

        if clause.get(
            "zone_relevance"
        ) == "OTHER_ZONE":
            continue

        if any(
            (
                condition.get(
                    "name"
                )
                == "지구단위계획"
                and
                condition.get(
                    "type"
                )
                == "SITE"
            )
            for condition
            in clause.get(
                "conditions",
                [],
            )
        ):

            district_clauses.append(
                clause
            )

    print_separator()

    print(
        "=== 지구단위계획 관련 세부 규정 ==="
    )

    print_separator()

    print(
        "규정 수:",
        len(
            district_clauses
        ),
    )

    print()

    for (
        index,
        clause,
    ) in enumerate(
        district_clauses,
        start=1,
    ):

        print(
            f"{index}."
        )

        print(
            clause.get(
                "law_name",
                "",
            )
        )

        print(
            (
                f"{clause.get('rule_title', '')}"
                f" | 항: "
                f"{clause.get('paragraph')}"
                f" | 호: "
                f"{clause.get('item')}"
                f" | 목: "
                f"{clause.get('subitem')}"
            )
        )

        print(
            clause.get(
                "text",
                "",
            )
        )

        print()

    all_pass = all(
        validations.values()
    )

    output_data = {
        "step":
            "STEP 17-21-C-8-8",

        "site": {
            "address":
                site.get(
                    "address",
                    "",
                ),

            "zone":
                target_zone,
        },

        "summary": {
            "source_rule_candidates":
                len(
                    candidates
                ),

            "total_clauses":
                len(
                    clauses
                ),

            "direct":
                counts[
                    "DIRECT"
                ],

            "group":
                counts[
                    "GROUP"
                ],

            "unspecified":
                counts[
                    "UNSPECIFIED"
                ],

            "other_zone":
                counts[
                    "OTHER_ZONE"
                ],
        },

        "validations":
            validations,

        "all_pass":
            all_pass,

        "required_conditions": {
            "SITE":
                site_conditions,

            "SITE_HISTORY":
                site_history_conditions,

            "PROJECT":
                project_conditions,

            "PROCEDURE":
                procedure_conditions,
        },

        "clauses":
            clauses,
    }

    save_json(
        OUTPUT_PATH,
        output_data,
    )

    print_separator()

    print(
        "결과 저장:"
    )

    print(
        OUTPUT_PATH
    )

    print_separator()

    print()

    if all_pass:

        print(
            "STEP 17-21-C-8-8 완료"
        )

        print()

        print(
            "C-8 파서 최종 검증: ALL PASS"
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9"
        )

        print(
            "→ 실제 SITE 공간조건 조회"
        )

        print(
            "→ 지구단위계획 / 개발진흥지구 / "
            "개발밀도관리구역 등 필지 교차 판정"
        )

        print(
            "→ SITE 조건 True / False / UNKNOWN 확정"
        )

        print(
            "→ 특례 clause 적용 가능성 최종 필터링"
        )

    else:

        print(
            "STEP 17-21-C-8-8 검증 실패"
        )

        print()

        print(
            "FAIL 항목이 남아 있으므로 "
            "C-9로 진행하지 않습니다."
        )


if __name__ == "__main__":
    main()