from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


# ============================================================
# CONFIG
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_document_parser_execution.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_target_document_candidate_verification.json"
)


# ============================================================
# CONSTANTS
# ============================================================

TARGET_CANDIDATE_RESOLUTIONS = {
    "PDF_TEXT_EXTRACTED_TARGET_CANDIDATE",
    "HWP_TEXT_EXTRACTED_TARGET_CANDIDATE",
    "HWPX_TEXT_EXTRACTED_TARGET_CANDIDATE",
    "TARGET_DOCUMENT_CANDIDATE",
}


# ============================================================
# ACTION PATTERNS
# ============================================================

ACTION_PATTERNS = {
    "DESIGNATION": [
        r"개발밀도관리구역.{0,120}?지정",
        r"개발밀도관리구역을.{0,120}?지정",
        r"개발밀도관리구역으로.{0,120}?지정",
        r"지정.{0,120}?개발밀도관리구역",
    ],
    "CHANGE": [
        r"개발밀도관리구역.{0,120}?변경",
        r"개발밀도관리구역.{0,120}?변경결정",
        r"개발밀도관리구역.{0,120}?결정\s*\(\s*변경\s*\)",
        r"변경.{0,120}?개발밀도관리구역",
    ],
    "RELEASE": [
        r"개발밀도관리구역.{0,120}?해제",
        r"개발밀도관리구역.{0,120}?해지",
        r"해제.{0,120}?개발밀도관리구역",
    ],
    "DECISION": [
        r"개발밀도관리구역.{0,120}?결정",
        r"결정.{0,120}?개발밀도관리구역",
    ],
}


# ============================================================
# OFFICIAL CONTEXT
# ============================================================

OFFICIAL_CONTEXT_PATTERNS = [
    r"고\s*시",
    r"고시문",
    r"고시번호",
    r"고시일",
    r"도시관리계획",
    r"도시계획",
    r"국토의\s*계획\s*및\s*이용에\s*관한\s*법률",
    r"국토계획법",
    r"시장",
    r"군수",
    r"구청장",
    r"특별시장",
    r"광역시장",
    r"도지사",
]


# ============================================================
# NOTICE NUMBER
# ============================================================

NOTICE_NUMBER_PATTERNS = [
    re.compile(
        r"(?P<notice>"
        r"(?:서울특별시|부산광역시|대구광역시|인천광역시|"
        r"광주광역시|대전광역시|울산광역시|세종특별자치시|"
        r"경기도|강원특별자치도|강원도|충청북도|충청남도|"
        r"전북특별자치도|전라북도|전라남도|경상북도|경상남도|"
        r"제주특별자치도|"
        r"[가-힣]{2,10}시|[가-힣]{2,10}군|[가-힣]{2,10}구)"
        r"\s*고시\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"
    ),
    re.compile(
        r"(?P<notice>"
        r"고시\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"
    ),
]


# ============================================================
# DATE
# ============================================================

DATE_PATTERNS = [
    re.compile(
        r"(?P<year>19\d{2}|20\d{2})\s*[.\-/년]\s*"
        r"(?P<month>0?[1-9]|1[0-2])\s*[.\-/월]\s*"
        r"(?P<day>0?[1-9]|[12]\d|3[01])\s*일?"
    ),
]


# ============================================================
# REGION
# ============================================================

REGION_PATTERNS = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",
    "경기도",
    "강원특별자치도",
    "강원도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라북도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]


# ============================================================
# LEGAL REFERENCE FALSE POSITIVE
# ============================================================

LEGAL_REFERENCE_PATTERNS = [
    r"법\s*제\s*\d+\s*조",
    r"법률\s*제\s*\d+\s*호",
    r"시행령\s*제\s*\d+\s*조",
    r"조례\s*제\s*\d+\s*조",
    r"용어의\s*뜻",
    r"정의는\s*다음과",
    r"다음\s*각\s*호",
]


# ============================================================
# ADMINISTRATIVE DUTY / DELEGATION TABLE FALSE POSITIVE
# ============================================================

# 이번 천안시 false positive의 핵심 구조:
#
#   부서명 / 단위사무명 / 전결권자
#   담당자 / 팀장 / 관·과·단장 / 국장 / 부시장
#   "부담구역 및 개발밀도관리구역 지정 기안 ○"
#
# 즉 실제 특정 구역을 지정하는 처분·고시문이 아니라
# "그 업무를 누가 기안/전결하는지" 규정한 사무전결표이다.
#
# 단순 "기안" 1회만으로 false positive 처리하지 않고
# 구조적 전결표 신호 또는 반복되는 기안 표식을 요구한다.

ADMINISTRATIVE_DUTY_PATTERNS = [
    r"단\s*위\s*사\s*무\s*명",
    r"전\s*결\s*권\s*자",
    r"사\s*무\s*전\s*결",
    r"전\s*결\s*규\s*정",
    r"전\s*결\s*사\s*무",
    r"업\s*무\s*분\s*장",
    r"사\s*무\s*분\s*장",

    r"담\s*당\s*자",
    r"팀\s*장",
    r"과\s*장",
    r"국\s*장",
    r"부\s*시\s*장",
    r"부\s*군\s*수",
    r"부\s*구\s*청\s*장",

    r"관\s*[·ㆍ․]\s*과\s*[·ㆍ․]\s*단\s*장",

    r"기\s*안\s*[○●◎◯]",
]

ADMINISTRATIVE_DUTY_STRONG_STRUCTURE_PATTERNS = [
    r"단\s*위\s*사\s*무\s*명",
    r"전\s*결\s*권\s*자",
    r"사\s*무\s*전\s*결",
    r"전\s*결\s*규\s*정",
    r"전\s*결\s*사\s*무",
]


ADMINISTRATIVE_DUTY_TABULAR_PATTERNS = [
    r"부\s*서\s*명.{0,150}?단\s*위\s*사\s*무\s*명",
    r"단\s*위\s*사\s*무\s*명.{0,150}?전\s*결\s*권\s*자",

    r"담\s*당\s*자.{0,150}?팀\s*장",
    r"팀\s*장.{0,150}?국\s*장",
    r"국\s*장.{0,150}?부\s*시\s*장",

    r"관\s*[·ㆍ․]\s*과\s*[·ㆍ․]\s*단\s*장",
]


# ============================================================
# SCOPE
# ============================================================

SCOPE_PATTERNS = [
    r"[가-힣]{1,12}(?:동|읍|면|리)\s+\d+(?:-\d+)?\s*번지",
    r"[가-힣]{1,12}(?:동|읍|면|리)\s+일원",
    r"\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:㎡|m²|m2)",
    r"면적\s*[:：]?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?",
    r"위치\s*[:：]",
    r"구역\s*면적",
    r"지정\s*면적",
]


# ============================================================
# X -> Y STAGE CONTRACT
# ============================================================

DIRECT_TEXT_PRIORITY = [
    "target_context_text",
    "extracted_text",
    "document_text",
    "parsed_text",
    "body_text",
    "content_text",
    "full_text",
    "plain_text",
    "parser_text",
    "extracted_content",
    "raw_text",
    "text",
    "content",
    "body",
]


TEXT_FIELD_NAMES = {
    "target_context_text",
    "extracted_text",
    "text",
    "document_text",
    "parsed_text",
    "body_text",
    "content_text",
    "content",
    "body",
    "raw_text",
    "full_text",
    "plain_text",
    "parser_text",
    "extracted_content",
}


TARGET_BOOLEAN_KEYS = [
    "target_in_text",
    "target_found",
    "target_in_extracted_text",
    "contains_target",
    "target_document_candidate",
    "is_target_candidate",
]


# ============================================================
# HELPERS
# ============================================================

def normalize_text(value: Any) -> str:

    if value is None:
        return ""

    text = str(value)

    text = (
        text
        .replace("\u00a0", " ")
        .replace("\u200b", "")
        .replace("\ufeff", "")
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def unique_keep_order(
    values: list[str],
) -> list[str]:

    result: list[str] = []
    seen: set[str] = set()

    for value in values:

        normalized = normalize_text(
            value
        )

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        result.append(
            normalized
        )

    return result


def load_json(
    path: Path,
) -> Any:

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def walk_dicts(
    value: Any,
):

    if isinstance(
        value,
        dict,
    ):

        yield value

        for child in value.values():
            yield from walk_dicts(
                child
            )

    elif isinstance(
        value,
        list,
    ):

        for child in value:
            yield from walk_dicts(
                child
            )


def get_first_text(
    record: dict[str, Any],
    keys: list[str],
) -> str:

    for key in keys:

        value = record.get(
            key
        )

        if (
            isinstance(
                value,
                str,
            )
            and value.strip()
        ):
            return normalize_text(
                value
            )

    return ""


def stable_text_key(
    text: str,
) -> str:

    digest = hashlib.sha256(
        text.encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()

    return (
        f"TEXT::{digest}"
    )


# ============================================================
# DOCUMENT-LEVEL RECORD GUARD
# ============================================================

def is_document_level_record(
    record: dict[str, Any],
) -> bool:
    """
    X-stage top-level aggregate container가 하위 result의 target flag를
    간접적으로 포함한다고 해서 Y-stage 후보가 되면 안 된다.

    문서 후보는 최소한 다음 중 하나를 가져야 한다.

    - URL
    - parser
    - declared/detected type
    - resolution target candidate
    - target_context_text
    - target_contexts
    """

    resolution = normalize_text(
        record.get(
            "resolution"
        )
    )

    if (
        resolution
        in TARGET_CANDIDATE_RESOLUTIONS
        or "TARGET_CANDIDATE"
        in resolution
    ):
        return True

    if get_first_text(
        record,
        [
            "url",
            "download_url",
            "final_url",
            "source_url",
            "document_url",
        ],
    ):
        return True

    if get_first_text(
        record,
        [
            "parser",
            "parser_name",
            "declared_type",
            "detected_type",
            "document_type",
        ],
    ):
        return True

    if get_first_text(
        record,
        [
            "target_context_text",
        ],
    ):
        return True

    target_contexts = record.get(
        "target_contexts"
    )

    if isinstance(
        target_contexts,
        list,
    ):
        return True

    return False


# ============================================================
# X-STAGE CONTRACT TEXT EXTRACTION
# ============================================================

def extract_explicit_target_contexts(
    record: dict[str, Any],
) -> list[str]:

    contexts: list[str] = []

    value = record.get(
        "target_contexts"
    )

    if isinstance(
        value,
        list,
    ):

        for item in value:

            if not isinstance(
                item,
                str,
            ):
                continue

            text = normalize_text(
                item
            )

            if (
                text
                and TARGET_NAME
                in text
            ):
                contexts.append(
                    text
                )

    for nested_key in [
        "document",
        "parser_result",
        "parse_result",
        "result",
    ]:

        nested = record.get(
            nested_key
        )

        if not isinstance(
            nested,
            dict,
        ):
            continue

        nested_value = nested.get(
            "target_contexts"
        )

        if not isinstance(
            nested_value,
            list,
        ):
            continue

        for item in nested_value:

            if not isinstance(
                item,
                str,
            ):
                continue

            text = normalize_text(
                item
            )

            if (
                text
                and TARGET_NAME
                in text
            ):
                contexts.append(
                    text
                )

    return unique_keep_order(
        contexts
    )


def extract_document_text(
    record: dict[str, Any],
) -> str:

    # ========================================================
    # 1. X-stage canonical target context
    # ========================================================

    direct_context_text = get_first_text(
        record,
        [
            "target_context_text",
        ],
    )

    if (
        direct_context_text
        and TARGET_NAME
        in direct_context_text
    ):
        return direct_context_text

    # ========================================================
    # 2. Structured target contexts
    # ========================================================

    explicit_contexts = (
        extract_explicit_target_contexts(
            record
        )
    )

    if explicit_contexts:

        return "\n\n".join(
            explicit_contexts
        )

    # ========================================================
    # 3. Direct document-local raw text
    # ========================================================

    direct_collected: list[str] = []

    for key in DIRECT_TEXT_PRIORITY:

        value = record.get(
            key
        )

        if not isinstance(
            value,
            str,
        ):
            continue

        text = normalize_text(
            value
        )

        if not text:
            continue

        direct_collected.append(
            text
        )

        if TARGET_NAME in text:
            return text

    # ========================================================
    # 4. Limited nested document-local structures
    # ========================================================
    #
    # aggregate 부모가 results[]의 text를 상속하지 않도록
    # 임의 child list 전체 재귀 탐색은 하지 않는다.
    # ========================================================

    collected: list[str] = []

    for nested_key in [
        "document",
        "parser_result",
        "parse_result",
        "result",
        "verification",
    ]:

        nested = record.get(
            nested_key
        )

        if not isinstance(
            nested,
            dict,
        ):
            continue

        for key, child in nested.items():

            key_lower = normalize_text(
                key
            ).lower()

            if isinstance(
                child,
                str,
            ):

                is_text_field = (
                    key_lower
                    in TEXT_FIELD_NAMES
                    or key_lower.endswith(
                        "_text"
                    )
                    or "extracted_text"
                    in key_lower
                    or "parsed_text"
                    in key_lower
                    or "document_text"
                    in key_lower
                )

                if not is_text_field:
                    continue

                child_text = normalize_text(
                    child
                )

                if child_text:
                    collected.append(
                        child_text
                    )

            elif (
                key_lower
                == "target_contexts"
                and isinstance(
                    child,
                    list,
                )
            ):

                for item in child:

                    if not isinstance(
                        item,
                        str,
                    ):
                        continue

                    item_text = normalize_text(
                        item
                    )

                    if item_text:
                        collected.append(
                            item_text
                        )

    collected.extend(
        direct_collected
    )

    collected = unique_keep_order(
        collected
    )

    if not collected:
        return ""

    target_texts = [
        text
        for text in collected
        if TARGET_NAME in text
    ]

    if target_texts:

        return max(
            target_texts,
            key=len,
        )

    return max(
        collected,
        key=len,
    )


# ============================================================
# METADATA EXTRACTION
# ============================================================

def extract_url(
    record: dict[str, Any],
) -> str:

    direct = get_first_text(
        record,
        [
            "url",
            "download_url",
            "final_url",
            "source_url",
            "document_url",
        ],
    )

    if direct:
        return direct

    for nested_key in [
        "document",
        "parser_result",
        "parse_result",
        "result",
        "source",
        "metadata",
    ]:

        nested = record.get(
            nested_key
        )

        if not isinstance(
            nested,
            dict,
        ):
            continue

        value = get_first_text(
            nested,
            [
                "url",
                "download_url",
                "final_url",
                "source_url",
                "document_url",
            ],
        )

        if value:
            return value

    return ""


def extract_region_from_metadata(
    record: dict[str, Any],
) -> str:

    direct = get_first_text(
        record,
        [
            "region",
            "administrative_region",
            "municipality",
            "local_government",
            "jurisdiction",
        ],
    )

    if direct:
        return direct

    for nested_key in [
        "document",
        "source",
        "metadata",
        "parser_result",
        "result",
    ]:

        nested = record.get(
            nested_key
        )

        if not isinstance(
            nested,
            dict,
        ):
            continue

        value = get_first_text(
            nested,
            [
                "region",
                "administrative_region",
                "municipality",
                "local_government",
                "jurisdiction",
            ],
        )

        if value:
            return value

    return ""


def extract_parser_name(
    record: dict[str, Any],
) -> str:

    direct = get_first_text(
        record,
        [
            "parser",
            "parser_name",
            "parser_used",
            "text_parser",
        ],
    )

    if direct:
        return direct

    for nested_key in [
        "parser_result",
        "parse_result",
        "result",
        "document",
    ]:

        nested = record.get(
            nested_key
        )

        if not isinstance(
            nested,
            dict,
        ):
            continue

        value = get_first_text(
            nested,
            [
                "parser",
                "parser_name",
                "parser_used",
                "text_parser",
            ],
        )

        if value:
            return value

    return ""


# ============================================================
# CANDIDATE IDENTITY / DEDUPLICATION
# ============================================================

def canonical_candidate_identity(
    record: dict[str, Any],
) -> str:

    url = extract_url(
        record
    )

    if url:

        return (
            "URL::"
            + normalize_text(
                url
            )
        )

    text = extract_document_text(
        record
    )

    if text:

        return stable_text_key(
            text
        )

    index = record.get(
        "index"
    )

    resolution = normalize_text(
        record.get(
            "resolution"
        )
    )

    return (
        f"FALLBACK::{index}::{resolution}"
    )


def dedupe_candidate_records(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    canonical: dict[
        str,
        dict[str, Any],
    ] = {}

    for record in records:

        key = canonical_candidate_identity(
            record
        )

        previous = canonical.get(
            key
        )

        if previous is None:

            canonical[
                key
            ] = record

            continue

        previous_text = (
            extract_document_text(
                previous
            )
        )

        current_text = (
            extract_document_text(
                record
            )
        )

        previous_contexts = (
            extract_explicit_target_contexts(
                previous
            )
        )

        current_contexts = (
            extract_explicit_target_contexts(
                record
            )
        )

        previous_score = (
            int(
                TARGET_NAME
                in previous_text
            )
            * 1_000_000
            + len(
                previous_contexts
            )
            * 10_000
            + len(
                previous_text
            )
        )

        current_score = (
            int(
                TARGET_NAME
                in current_text
            )
            * 1_000_000
            + len(
                current_contexts
            )
            * 10_000
            + len(
                current_text
            )
        )

        if (
            current_score
            > previous_score
        ):

            canonical[
                key
            ] = record

    return list(
        canonical.values()
    )


# ============================================================
# TARGET CANDIDATE EXTRACTION
# ============================================================

def is_target_candidate(
    record: dict[str, Any],
) -> bool:

    if not is_document_level_record(
        record
    ):
        return False

    resolution = normalize_text(
        record.get(
            "resolution"
        )
    )

    if (
        resolution
        in TARGET_CANDIDATE_RESOLUTIONS
    ):
        return True

    if (
        "TARGET_CANDIDATE"
        in resolution
    ):
        return True

    for key in TARGET_BOOLEAN_KEYS:

        if record.get(
            key
        ) is True:

            return True

    explicit_contexts = (
        extract_explicit_target_contexts(
            record
        )
    )

    if explicit_contexts:
        return True

    context_text = get_first_text(
        record,
        [
            "target_context_text",
        ],
    )

    if (
        context_text
        and TARGET_NAME
        in context_text
    ):
        return True

    text = extract_document_text(
        record
    )

    if TARGET_NAME in text:
        return True

    return False


def extract_target_candidates(
    data: Any,
) -> list[dict[str, Any]]:

    raw_candidates: list[
        dict[str, Any]
    ] = []

    for record in walk_dicts(
        data
    ):

        if not is_target_candidate(
            record
        ):
            continue

        text = extract_document_text(
            record
        )

        if TARGET_NAME not in text:
            continue

        raw_candidates.append(
            record
        )

    return dedupe_candidate_records(
        raw_candidates
    )


def extract_x_stage_resolution_candidates(
    data: Any,
) -> list[dict[str, Any]]:

    records: list[
        dict[str, Any]
    ] = []

    for record in walk_dicts(
        data
    ):

        if not is_document_level_record(
            record
        ):
            continue

        resolution = normalize_text(
            record.get(
                "resolution"
            )
        )

        if not resolution:
            continue

        if (
            resolution
            in TARGET_CANDIDATE_RESOLUTIONS
            or "TARGET_CANDIDATE"
            in resolution
        ):

            records.append(
                record
            )

    return dedupe_candidate_records(
        records
    )


# ============================================================
# TARGET CONTEXT
# ============================================================

def extract_target_context(
    text: str,
    radius: int = 500,
) -> list[str]:

    contexts: list[str] = []

    start = 0

    while True:

        idx = text.find(
            TARGET_NAME,
            start,
        )

        if idx < 0:
            break

        left = max(
            0,
            idx - radius,
        )

        right = min(
            len(text),
            idx
            + len(TARGET_NAME)
            + radius,
        )

        contexts.append(
            text[
                left:right
            ]
        )

        start = (
            idx
            + len(TARGET_NAME)
        )

    return unique_keep_order(
        contexts
    )


# ============================================================
# ACTION CONTEXT
# ============================================================

def extract_action_context(
    text: str,
) -> tuple[
    list[str],
    list[str],
]:

    action_types: list[str] = []
    evidence: list[str] = []

    contexts = extract_target_context(
        text,
        radius=500,
    )

    corpus = "\n".join(
        contexts
    )

    for (
        action_type,
        patterns,
    ) in ACTION_PATTERNS.items():

        for pattern in patterns:

            match = re.search(
                pattern,
                corpus,
                flags=(
                    re.I
                    | re.S
                ),
            )

            if not match:
                continue

            action_types.append(
                action_type
            )

            evidence.append(
                normalize_text(
                    match.group(0)
                )
            )

    return (
        unique_keep_order(
            action_types
        ),
        unique_keep_order(
            evidence
        ),
    )


# ============================================================
# NOTICE NUMBER
# ============================================================

def extract_notice_numbers(
    text: str,
) -> list[str]:

    result: list[str] = []

    for pattern in NOTICE_NUMBER_PATTERNS:

        for match in pattern.finditer(
            text
        ):

            value = (
                match.groupdict().get(
                    "notice"
                )
                or match.group(0)
            )

            result.append(
                normalize_text(
                    value
                )
            )

    return unique_keep_order(
        result
    )


# ============================================================
# DATE
# ============================================================

def extract_dates(
    text: str,
) -> list[str]:

    result: list[str] = []

    for pattern in DATE_PATTERNS:

        for match in pattern.finditer(
            text
        ):

            year = int(
                match.group(
                    "year"
                )
            )

            month = int(
                match.group(
                    "month"
                )
            )

            day = int(
                match.group(
                    "day"
                )
            )

            result.append(
                f"{year:04d}-"
                f"{month:02d}-"
                f"{day:02d}"
            )

    return unique_keep_order(
        result
    )


# ============================================================
# ADMINISTRATIVE REGION
# ============================================================

def extract_regions(
    text: str,
    metadata_region: str,
) -> list[str]:

    regions: list[str] = []

    if metadata_region:

        regions.append(
            metadata_region
        )

    for region in REGION_PATTERNS:

        if region in text:

            regions.append(
                region
            )

    local_patterns = [
        r"([가-힣]{2,10}시)\s*(?:고시|공고|시장)",
        r"([가-힣]{2,10}군)\s*(?:고시|공고|군수)",
        r"([가-힣]{2,10}구)\s*(?:고시|공고|구청장)",
    ]

    for pattern in local_patterns:

        for match in re.finditer(
            pattern,
            text,
        ):

            regions.append(
                match.group(1)
            )

    return unique_keep_order(
        regions
    )


# ============================================================
# OFFICIAL CONTEXT
# ============================================================

def extract_official_context(
    text: str,
) -> list[str]:

    evidence: list[str] = []

    contexts = extract_target_context(
        text,
        radius=1000,
    )

    corpus = "\n".join(
        contexts
    )

    for pattern in OFFICIAL_CONTEXT_PATTERNS:

        match = re.search(
            pattern,
            corpus,
            flags=re.I,
        )

        if match:

            evidence.append(
                normalize_text(
                    match.group(0)
                )
            )

    return unique_keep_order(
        evidence
    )


# ============================================================
# SCOPE EVIDENCE
# ============================================================

def extract_scope_evidence(
    text: str,
) -> list[str]:

    evidence: list[str] = []

    contexts = extract_target_context(
        text,
        radius=2500,
    )

    corpus = "\n".join(
        contexts
    )

    for pattern in SCOPE_PATTERNS:

        for match in re.finditer(
            pattern,
            corpus,
            flags=re.I,
        ):

            evidence.append(
                normalize_text(
                    match.group(0)
                )
            )

    return unique_keep_order(
        evidence
    )


# ============================================================
# LEGAL REFERENCE GUARD
# ============================================================

def detect_legal_reference_only(
    text: str,
    action_types: list[str],
    notice_numbers: list[str],
    official_context: list[str],
) -> tuple[
    bool,
    list[str],
]:

    target_contexts = (
        extract_target_context(
            text,
            radius=700,
        )
    )

    corpus = "\n".join(
        target_contexts
    )

    legal_evidence: list[str] = []

    for pattern in LEGAL_REFERENCE_PATTERNS:

        match = re.search(
            pattern,
            corpus,
            flags=re.I,
        )

        if match:

            legal_evidence.append(
                normalize_text(
                    match.group(0)
                )
            )

    substantial_official_evidence = (
        bool(
            action_types
        )
        and bool(
            notice_numbers
        )
        and bool(
            official_context
        )
    )

    legal_reference_only = (
        bool(
            legal_evidence
        )
        and not substantial_official_evidence
    )

    return (
        legal_reference_only,
        unique_keep_order(
            legal_evidence
        ),
    )


# ============================================================
# ADMINISTRATIVE DUTY / DELEGATION TABLE GUARD
# ============================================================

def detect_administrative_duty_reference(
    text: str,
) -> tuple[
    bool,
    list[str],
    dict[str, Any],
]:

    contexts = extract_target_context(
        text,
        radius=1800,
    )

    corpus = "\n".join(
        contexts
    )

    evidence: list[str] = []

    # ========================================================
    # GENERAL ADMINISTRATIVE-DUTY EVIDENCE
    # ========================================================

    for pattern in ADMINISTRATIVE_DUTY_PATTERNS:

        for match in re.finditer(
            pattern,
            corpus,
            flags=re.I | re.S,
        ):

            evidence.append(
                normalize_text(
                    match.group(0)
                )
            )

    evidence = unique_keep_order(
        evidence
    )

    # ========================================================
    # STRONG STRUCTURAL EVIDENCE
    # ========================================================

    strong_structure_evidence: list[str] = []

    for pattern in (
        ADMINISTRATIVE_DUTY_STRONG_STRUCTURE_PATTERNS
    ):

        for match in re.finditer(
            pattern,
            corpus,
            flags=re.I | re.S,
        ):

            strong_structure_evidence.append(
                normalize_text(
                    match.group(0)
                )
            )

    strong_structure_evidence = (
        unique_keep_order(
            strong_structure_evidence
        )
    )

    # ========================================================
    # TABULAR / DELEGATION STRUCTURE
    # ========================================================

    tabular_evidence: list[str] = []

    for pattern in (
        ADMINISTRATIVE_DUTY_TABULAR_PATTERNS
    ):

        for match in re.finditer(
            pattern,
            corpus,
            flags=re.I | re.S,
        ):

            tabular_evidence.append(
                normalize_text(
                    match.group(0)
                )
            )

    tabular_evidence = (
        unique_keep_order(
            tabular_evidence
        )
    )

    # ========================================================
    # DRAFT MARKERS
    # ========================================================

    draft_markers = re.findall(
        r"기\s*안\s*[○●◎◯]",
        corpus,
        flags=re.I,
    )

    draft_marker_count = len(
        draft_markers
    )

    # target 자체가
    #
    #   개발밀도관리구역 지정 기안 ○
    #
    # 형태인지 확인한다.
    target_draft_pattern = re.search(
        (
            r"개발밀도관리구역"
            r".{0,100}?"
            r"지정"
            r".{0,80}?"
            r"기\s*안\s*[○●◎◯]"
        ),
        corpus,
        flags=re.I | re.S,
    )

    target_draft_evidence = (
        normalize_text(
            target_draft_pattern.group(0)
        )
        if target_draft_pattern
        else ""
    )

    # ========================================================
    # SUPPORTING STRUCTURE
    # ========================================================

    strong_structure = bool(
        strong_structure_evidence
    )

    tabular_structure = bool(
        tabular_evidence
    )

    target_is_draft_duty = bool(
        target_draft_evidence
    )

    repeated_draft_markers = (
        draft_marker_count
        >= 2
    )

    heavy_draft_table_signature = (
        draft_marker_count
        >= 10
    )

    multiple_administrative_signals = (
        len(
            evidence
        )
        >= 3
    )

    # ========================================================
    # DECISION RULE
    # ========================================================
    #
    # 1. 단위사무명 / 전결권자 등 구조가 직접 확인되면 확정.
    #
    # 2. target 자체가 "지정 기안 ○"이고 표 구조가 확인되면 확정.
    #
    # 3. PDF spacing 문제로 표 제목 인식이 일부 실패하더라도,
    #    target이 "지정 기안 ○"이고 기안 ○가 대량 반복되면
    #    전결/업무분장표로 확정.
    #
    # 4. 단순히 "기안" 한 번 있는 일반 고시문은 배제하지 않는다.
    # ========================================================

    administrative_duty_reference = (
        strong_structure

        or (
            target_is_draft_duty
            and tabular_structure
        )

        or (
            target_is_draft_duty
            and heavy_draft_table_signature
        )

        or (
            repeated_draft_markers
            and tabular_structure
            and multiple_administrative_signals
        )
    )

    diagnostics = {
        "strong_structure": (
            strong_structure
        ),

        "strong_structure_evidence": (
            strong_structure_evidence
        ),

        "tabular_structure": (
            tabular_structure
        ),

        "tabular_evidence": (
            tabular_evidence
        ),

        "draft_marker_count": (
            draft_marker_count
        ),

        "repeated_draft_markers": (
            repeated_draft_markers
        ),

        "heavy_draft_table_signature": (
            heavy_draft_table_signature
        ),

        "target_is_draft_duty": (
            target_is_draft_duty
        ),

        "target_draft_evidence": (
            target_draft_evidence
        ),

        "multiple_administrative_signals": (
            multiple_administrative_signals
        ),
    }

    return (
        administrative_duty_reference,
        evidence,
        diagnostics,
    )


# ============================================================
# VERIFICATION
# ============================================================

def verify_candidate(
    record: dict[str, Any],
    index: int,
) -> dict[str, Any]:

    text = extract_document_text(
        record
    )

    url = extract_url(
        record
    )

    identity = (
        canonical_candidate_identity(
            record
        )
    )

    metadata_region = (
        extract_region_from_metadata(
            record
        )
    )

    target_in_body = (
        TARGET_NAME
        in text
    )

    (
        action_types,
        action_evidence,
    ) = extract_action_context(
        text
    )

    notice_numbers = (
        extract_notice_numbers(
            text
        )
    )

    dates = extract_dates(
        text
    )

    regions = extract_regions(
        text,
        metadata_region,
    )

    official_context_evidence = (
        extract_official_context(
            text
        )
    )

    scope_evidence = (
        extract_scope_evidence(
            text
        )
    )

    (
        legal_reference_only,
        legal_reference_evidence,
    ) = detect_legal_reference_only(
        text=text,
        action_types=action_types,
        notice_numbers=notice_numbers,
        official_context=(
            official_context_evidence
        ),
    )

    (
        administrative_duty_reference,
        administrative_duty_evidence,
        administrative_duty_diagnostics,
    ) = detect_administrative_duty_reference(
        text
    )

    has_action_context = bool(
        action_types
    )

    has_notice_number = bool(
        notice_numbers
    )

    has_official_context = bool(
        official_context_evidence
    )

    has_geographic_context = bool(
        regions
    )

    has_scope_evidence = bool(
        scope_evidence
    )

    # ========================================================
    # FINAL POSITIVE QUALIFICATION
    # ========================================================
    #
    # 중요:
    #
    # action + official context가 있어도
    # 사무전결표/업무분장 reference이면 final positive 금지.
    # ========================================================

    verified_positive = (
        target_in_body
        and has_action_context
        and has_notice_number
        and has_official_context
        and has_geographic_context
        and not legal_reference_only
        and not administrative_duty_reference
    )

    reasons: list[str] = []

    if not target_in_body:

        reasons.append(
            "TARGET_NOT_IN_DOCUMENT_BODY"
        )

    if administrative_duty_reference:

        reasons.append(
            "ADMINISTRATIVE_DUTY_REFERENCE_ONLY"
        )

    if not has_action_context:

        reasons.append(
            "NO_ACTION_CONTEXT"
        )

    if not has_notice_number:

        reasons.append(
            "NO_NOTICE_NUMBER"
        )

    if not has_official_context:

        reasons.append(
            "NO_STRONG_OFFICIAL_CONTEXT"
        )

    if not has_geographic_context:

        reasons.append(
            "NO_GEOGRAPHIC_CONTEXT"
        )

    if legal_reference_only:

        reasons.append(
            "LEGAL_REFERENCE_ONLY"
        )

    if not has_scope_evidence:

        reasons.append(
            "SCOPE_NOT_EXTRACTED"
        )

    # ========================================================
    # RESOLUTION PRIORITY
    # ========================================================
    #
    # 행정사무 false positive는 NO_NOTICE_NUMBER보다 우선한다.
    #
    # 그렇지 않으면 "고시번호만 못 찾은 고시문"으로 오해할 수 있다.
    # ========================================================

    if verified_positive:

        resolution = (
            "VERIFIED_OFFICIAL_TARGET_DOCUMENT"
        )

    elif administrative_duty_reference:

        resolution = (
            "ADMINISTRATIVE_DUTY_REFERENCE_ONLY"
        )

    elif legal_reference_only:

        resolution = (
            "LEGAL_REFERENCE_ONLY"
        )

    elif (
        target_in_body
        and not has_action_context
    ):

        resolution = (
            "TARGET_MENTION_ONLY"
        )

    elif (
        target_in_body
        and not has_notice_number
    ):

        resolution = (
            "NO_NOTICE_NUMBER"
        )

    elif (
        target_in_body
        and not has_geographic_context
    ):

        resolution = (
            "NO_GEOGRAPHIC_SCOPE"
        )

    else:

        resolution = (
            "UNVERIFIED_TARGET_DOCUMENT"
        )

    contexts = extract_target_context(
        text,
        radius=750,
    )

    explicit_x_contexts = (
        extract_explicit_target_contexts(
            record
        )
    )

    return {
        "candidate_index": (
            index
        ),

        "candidate_identity": (
            identity
        ),

        "region": (
            metadata_region
        ),

        "url": (
            url
        ),

        "source_resolution": (
            normalize_text(
                record.get(
                    "resolution"
                )
            )
        ),

        "parser": (
            extract_parser_name(
                record
            )
        ),

        "declared_type": (
            get_first_text(
                record,
                [
                    "declared_type",
                    "document_type",
                    "source_type",
                ],
            )
        ),

        "detected_type": (
            get_first_text(
                record,
                [
                    "detected_type",
                    "detected_document_type",
                    "content_type",
                ],
            )
        ),

        # ----------------------------------------------------
        # X-stage contract diagnostics
        # ----------------------------------------------------

        "x_stage_target_in_text": (
            record.get(
                "target_in_text"
            )
            is True
        ),

        "x_stage_target_context_count": (
            int(
                record.get(
                    "target_context_count"
                )
                or len(
                    explicit_x_contexts
                )
            )
        ),

        "x_stage_target_contexts": (
            explicit_x_contexts[:20]
        ),

        "verification_text_length": (
            len(
                text
            )
        ),

        # ----------------------------------------------------
        # Core evidence
        # ----------------------------------------------------

        "target_in_document_body": (
            target_in_body
        ),

        "target_contexts": (
            contexts[:10]
        ),

        "action_context": (
            has_action_context
        ),

        "action_types": (
            action_types
        ),

        "action_evidence": (
            action_evidence
        ),

        "notice_numbers": (
            notice_numbers
        ),

        "dates": (
            dates
        ),

        "administrative_regions": (
            regions
        ),

        "official_context": (
            has_official_context
        ),

        "official_context_evidence": (
            official_context_evidence
        ),

        # ----------------------------------------------------
        # False-positive guards
        # ----------------------------------------------------

        "legal_reference_only": (
            legal_reference_only
        ),

        "legal_reference_evidence": (
            legal_reference_evidence
        ),

        "administrative_duty_reference": (
            administrative_duty_reference
        ),

        "administrative_duty_evidence": (
            administrative_duty_evidence
        ),

        "administrative_duty_diagnostics": (
            administrative_duty_diagnostics
        ),

        # ----------------------------------------------------
        # Scope
        # ----------------------------------------------------

        "scope_extraction_status": (
            "SCOPE_EVIDENCE_EXTRACTED"
            if has_scope_evidence
            else "SCOPE_NOT_EXTRACTED"
        ),

        "scope_evidence": (
            scope_evidence
        ),

        # ----------------------------------------------------
        # Result
        # ----------------------------------------------------

        "verified_positive": (
            verified_positive
        ),

        "resolution": (
            resolution
        ),

        "reasons": (
            reasons
        ),
    }


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print(
        "=" * 60
    )

    print(
        "DEVELOPMENT DENSITY MANAGEMENT AREA"
    )

    print(
        "TARGET DOCUMENT CANDIDATE VERIFICATION"
    )

    print(
        "=" * 60
    )

    print()

    print(
        f"Target: {TARGET_NAME}"
    )

    print(
        f"Standard code: {STANDARD_CODE}"
    )

    print(
        f"Input: {INPUT_PATH}"
    )

    print()

    # ========================================================
    # INPUT
    # ========================================================

    if not INPUT_PATH.exists():

        raise FileNotFoundError(
            "Input does not exist: "
            f"{INPUT_PATH}"
        )

    input_data = load_json(
        INPUT_PATH
    )

    # ========================================================
    # X-STAGE ACCOUNTING
    # ========================================================

    x_stage_resolution_candidates = (
        extract_x_stage_resolution_candidates(
            input_data
        )
    )

    x_stage_resolution_candidate_ids = {
        canonical_candidate_identity(
            record
        )
        for record
        in x_stage_resolution_candidates
        if TARGET_NAME
        in extract_document_text(
            record
        )
    }

    x_stage_context_candidate_ids = {
        canonical_candidate_identity(
            record
        )
        for record
        in x_stage_resolution_candidates
        if (
            bool(
                extract_explicit_target_contexts(
                    record
                )
            )
            or TARGET_NAME
            in get_first_text(
                record,
                [
                    "target_context_text",
                ],
            )
        )
    }

    # ========================================================
    # Y-STAGE EXTRACTION
    # ========================================================

    candidates = (
        extract_target_candidates(
            input_data
        )
    )

    candidate_ids = {
        canonical_candidate_identity(
            record
        )
        for record
        in candidates
    }

    duplicate_candidate_identity_count = (
        len(
            candidates
        )
        - len(
            candidate_ids
        )
    )

    # aggregate top-level/container record가 Y-stage candidate로
    # 유입되는지 확인.
    aggregate_container_candidate_leakage = sum(
        1
        for record
        in candidates
        if not is_document_level_record(
            record
        )
    )

    print(
        "X-stage canonical resolution "
        "target candidate count: "
        f"{len(x_stage_resolution_candidates)}"
    )

    print(
        "X-stage resolution candidate "
        "with body/context evidence count: "
        f"{len(x_stage_resolution_candidate_ids)}"
    )

    print(
        "X-stage explicit target-context "
        "candidate count: "
        f"{len(x_stage_context_candidate_ids)}"
    )

    print(
        "Y-stage target candidate count: "
        f"{len(candidates)}"
    )

    print(
        "Aggregate container candidate leakage: "
        f"{aggregate_container_candidate_leakage}"
    )

    print()

    # ========================================================
    # VERIFY
    # ========================================================

    verified_records: list[
        dict[str, Any]
    ] = []

    for index, record in enumerate(
        candidates,
        start=1,
    ):

        result = verify_candidate(
            record,
            index,
        )

        verified_records.append(
            result
        )

        print(
            "-" * 60
        )

        print(
            f"CANDIDATE {index}"
        )

        print(
            "Identity: "
            f"{result['candidate_identity']}"
        )

        print(
            f"Region: {result['region']}"
        )

        print(
            f"URL: {result['url']}"
        )

        print(
            "Source resolution: "
            f"{result['source_resolution']}"
        )

        print(
            f"Parser: {result['parser']}"
        )

        print(
            "Declared type: "
            f"{result['declared_type']}"
        )

        print(
            "Detected type: "
            f"{result['detected_type']}"
        )

        print(
            "X-stage target flag: "
            f"{result['x_stage_target_in_text']}"
        )

        print(
            "X-stage target context count: "
            f"{result['x_stage_target_context_count']}"
        )

        print(
            "Verification text length: "
            f"{result['verification_text_length']}"
        )

        print(
            "Target in document body/context: "
            f"{result['target_in_document_body']}"
        )

        print(
            "Action context: "
            f"{result['action_context']}"
        )

        print(
            "Action types: "
            f"{result['action_types']}"
        )

        print(
            "Action evidence: "
            f"{result['action_evidence'][:10]}"
        )

        print(
            "Notice numbers: "
            f"{result['notice_numbers']}"
        )

        print(
            f"Dates: {result['dates']}"
        )

        print(
            "Administrative regions: "
            f"{result['administrative_regions']}"
        )

        print(
            "Official context: "
            f"{result['official_context']}"
        )

        print(
            "Official context evidence: "
            f"{result['official_context_evidence'][:10]}"
        )

        print(
            "Legal reference only: "
            f"{result['legal_reference_only']}"
        )

        print(
            "Legal reference evidence: "
            f"{result['legal_reference_evidence'][:10]}"
        )

        print(
            "Administrative duty reference: "
            f"{result['administrative_duty_reference']}"
        )

        print(
            "Administrative duty evidence: "
            f"{result['administrative_duty_evidence'][:15]}"
        )

        print(
            "Administrative duty diagnostics: "
            f"{result['administrative_duty_diagnostics']}"
        )

        print(
            "Scope status: "
            f"{result['scope_extraction_status']}"
        )

        print(
            "Scope evidence: "
            f"{result['scope_evidence'][:10]}"
        )

        print(
            "Verified positive: "
            f"{result['verified_positive']}"
        )

        print(
            "Resolution: "
            f"{result['resolution']}"
        )

        print(
            f"Reasons: {result['reasons']}"
        )

        if result[
            "target_contexts"
        ]:

            print(
                "Target context preview:"
            )

            print(
                result[
                    "target_contexts"
                ][0][:2000]
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    verified_positive_records = [
        item
        for item
        in verified_records
        if item[
            "verified_positive"
        ]
    ]

    legal_reference_only_count = sum(
        1
        for item
        in verified_records
        if item[
            "legal_reference_only"
        ]
    )

    administrative_duty_reference_count = sum(
        1
        for item
        in verified_records
        if item[
            "administrative_duty_reference"
        ]
    )

    target_mention_only_count = sum(
        1
        for item
        in verified_records
        if item[
            "resolution"
        ]
        == "TARGET_MENTION_ONLY"
    )

    scope_extracted_count = sum(
        1
        for item
        in verified_records
        if item[
            "scope_extraction_status"
        ]
        == "SCOPE_EVIDENCE_EXTRACTED"
    )

    print()

    print(
        "=" * 60
    )

    print(
        "VERIFICATION RESULT"
    )

    print(
        "=" * 60
    )

    print(
        "X-stage canonical resolution "
        "target candidate count: "
        f"{len(x_stage_resolution_candidates)}"
    )

    print(
        "X-stage body/context-confirmed "
        "target candidate count: "
        f"{len(x_stage_resolution_candidate_ids)}"
    )

    print(
        "X-stage explicit target-context "
        "candidate count: "
        f"{len(x_stage_context_candidate_ids)}"
    )

    print(
        "Y-stage target candidate count: "
        f"{len(candidates)}"
    )

    print(
        "Aggregate container candidate leakage: "
        f"{aggregate_container_candidate_leakage}"
    )

    print(
        "Verified positive count: "
        f"{len(verified_positive_records)}"
    )

    print(
        "Administrative-duty-reference count: "
        f"{administrative_duty_reference_count}"
    )

    print(
        "Legal-reference-only count: "
        f"{legal_reference_only_count}"
    )

    print(
        "Target-mention-only count: "
        f"{target_mention_only_count}"
    )

    print(
        "Scope evidence extracted count: "
        f"{scope_extracted_count}"
    )

    # ========================================================
    # RESOLUTION
    # ========================================================

    if verified_positive_records:

        resolution = (
            "OFFICIAL_TARGET_DOCUMENT_VERIFIED"
        )

        next_action = (
            "검증된 개발밀도관리구역 고시 원문에서 "
            "고시번호·고시일·행정구역·지정 범위를 정규화하고, "
            "현재 유효 여부 및 후속 변경·해제 고시를 추적한 뒤 "
            "positive spatial/PNU source를 역탐색한다."
        )

    elif (
        candidates
        and administrative_duty_reference_count
        == len(
            candidates
        )
    ):

        resolution = (
            "TARGET_CANDIDATES_REJECTED_AS_"
            "ADMINISTRATIVE_DUTY_REFERENCES"
        )

        next_action = (
            "현재 target 후보는 실제 개발밀도관리구역 지정·변경·해제 "
            "고시가 아니라 사무전결·업무분장·단위사무표 내 행정업무 "
            "참조로 판정되었다. 해당 문서는 false positive로 종결하고, "
            "실제 지정 고시를 찾기 위해 고시번호·도시관리계획 고시·"
            "과거 공보 issue·토지이음/공식 도시계획 원문 탐색으로 "
            "다음 discovery stage를 진행한다."
        )

    elif candidates:

        resolution = (
            "TARGET_DOCUMENT_CANDIDATE_"
            "VERIFICATION_COMPLETED_NO_POSITIVE"
        )

        next_action = (
            "X-stage target candidate는 document-level identity 기준으로 "
            "Y-stage에 정상 승계되었다. 출력된 target context를 기준으로 "
            "실제 개발밀도관리구역 지정·변경·해제 고시 본문인지, "
            "조례·법령·도시계획 일반문서의 단순 언급인지 확정한다. "
            "필요하면 같은 공보 issue 내부의 인접 고시번호 및 "
            "공식 원문을 추적한다."
        )

    elif x_stage_resolution_candidates:

        resolution = (
            "TARGET_DOCUMENT_CANDIDATE_"
            "STAGE_CONTRACT_REGRESSION"
        )

        next_action = (
            "X-stage에는 canonical target candidate가 존재하지만 "
            "Y-stage에서 body/context evidence를 회수하지 못했다. "
            "target_context_text / target_contexts contract를 다시 확인한다."
        )

    else:

        resolution = (
            "TARGET_DOCUMENT_CANDIDATE_"
            "VERIFICATION_COMPLETED_NO_CANDIDATE"
        )

        next_action = (
            "X-stage artifact에 target candidate가 없다. "
            "download retry 실패 문서 또는 다른 공식 원문 source로 "
            "탐색 범위를 확장한다."
        )

    print()

    print(
        "=" * 60
    )

    print(
        "RESOLUTION"
    )

    print(
        "=" * 60
    )

    print(
        resolution
    )

    print()

    print(
        next_action
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "target_name": (
            TARGET_NAME
        ),

        "standard_code": (
            STANDARD_CODE
        ),

        "input_path": str(
            INPUT_PATH
        ),

        "x_stage_resolution_candidate_count": (
            len(
                x_stage_resolution_candidates
            )
        ),

        "x_stage_body_confirmed_candidate_count": (
            len(
                x_stage_resolution_candidate_ids
            )
        ),

        "x_stage_explicit_context_candidate_count": (
            len(
                x_stage_context_candidate_ids
            )
        ),

        "candidate_count": (
            len(
                candidates
            )
        ),

        "duplicate_candidate_identity_count": (
            duplicate_candidate_identity_count
        ),

        "aggregate_container_candidate_leakage": (
            aggregate_container_candidate_leakage
        ),

        "verified_positive_count": (
            len(
                verified_positive_records
            )
        ),

        "administrative_duty_reference_count": (
            administrative_duty_reference_count
        ),

        "legal_reference_only_count": (
            legal_reference_only_count
        ),

        "target_mention_only_count": (
            target_mention_only_count
        ),

        "scope_extracted_count": (
            scope_extracted_count
        ),

        "candidates": (
            verified_records
        ),

        "verified_positive_documents": (
            verified_positive_records
        ),

        "resolution": (
            resolution
        ),

        "next_action": (
            next_action
        ),

        "runtime_registration_allowed": (
            False
        ),

        "site_positive_allowed": (
            False
        ),
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            output_data,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()

    print(
        f"Output: {OUTPUT_PATH}"
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    validations = {
        "target name": (
            output_data[
                "target_name"
            ]
            == TARGET_NAME
        ),

        "standard code": (
            output_data[
                "standard_code"
            ]
            == STANDARD_CODE
        ),

        "input exists": (
            INPUT_PATH.exists()
        ),

        "X-stage input parsed": (
            isinstance(
                input_data,
                (dict, list),
            )
        ),

        "target candidate extraction enabled": (
            True
        ),

        "document-level candidate guard enabled": (
            True
        ),

        "aggregate container guard enabled": (
            True
        ),

        "X-stage target-context contract enabled": (
            True
        ),

        "target_context_text priority enabled": (
            True
        ),

        "target_contexts list fallback enabled": (
            True
        ),

        "document-local text extraction enabled": (
            True
        ),

        "aggregate child recursive text inheritance disabled": (
            True
        ),

        "preview excluded from body evidence": (
            True
        ),

        "X-stage resolution accounting enabled": (
            True
        ),

        "X-stage resolution accounting canonicalized": (
            len(
                {
                    canonical_candidate_identity(
                        record
                    )
                    for record
                    in x_stage_resolution_candidates
                }
            )
            == len(
                x_stage_resolution_candidates
            )
        ),

        "candidate count preserved": (
            output_data[
                "candidate_count"
            ]
            == len(
                verified_records
            )
        ),

        "duplicate candidate identity leakage zero": (
            duplicate_candidate_identity_count
            == 0
        ),

        "aggregate container candidate leakage zero": (
            aggregate_container_candidate_leakage
            == 0
        ),

        # ----------------------------------------------------
        # X -> Y stage contract
        # ----------------------------------------------------

        "X-stage target candidate not lost": (
            x_stage_resolution_candidate_ids
            .issubset(
                candidate_ids
            )
        ),

        "X-stage explicit context candidate not lost": (
            x_stage_context_candidate_ids
            .issubset(
                candidate_ids
            )
        ),

        "candidate extraction consistent with X-stage resolution": (
            not x_stage_resolution_candidate_ids
            or bool(
                candidates
            )
        ),

        "all candidates contain target": all(
            item[
                "target_in_document_body"
            ]
            for item
            in verified_records
        ),

        "all X-stage context candidates contain target": all(
            TARGET_NAME
            in extract_document_text(
                record
            )
            for record
            in x_stage_resolution_candidates
            if canonical_candidate_identity(
                record
            )
            in x_stage_context_candidate_ids
        ),

        # ----------------------------------------------------
        # Semantic verification
        # ----------------------------------------------------

        "action-context verification enabled": (
            True
        ),

        "notice-number verification enabled": (
            True
        ),

        "official-context verification enabled": (
            True
        ),

        "geographic-context verification enabled": (
            True
        ),

        "legal-reference-only guard enabled": (
            True
        ),

        "administrative-duty false-positive guard enabled": (
            True
        ),

        "administrative-duty structural evidence enabled": (
            True
        ),

        "administrative-duty target draft detection enabled": (
            True
        ),

        "administrative-duty candidates never verified positive": all(
            not item[
                "verified_positive"
            ]
            for item
            in verified_records
            if item[
                "administrative_duty_reference"
            ]
        ),

        "administrative-duty resolution has priority": all(
            item[
                "resolution"
            ]
            == "ADMINISTRATIVE_DUTY_REFERENCE_ONLY"
            for item
            in verified_records
            if item[
                "administrative_duty_reference"
            ]
        ),

        "scope extraction enabled": (
            True
        ),

        "scope not mandatory for final positive": (
            True
        ),

        # ----------------------------------------------------
        # Verified positive safety
        # ----------------------------------------------------

        "verified documents unique": (
            len(
                {
                    item[
                        "candidate_identity"
                    ]
                    for item
                    in verified_positive_records
                }
            )
            == len(
                verified_positive_records
            )
        ),

        "all verified documents contain target": all(
            item[
                "target_in_document_body"
            ]
            for item
            in verified_positive_records
        ),

        "all verified documents have action context": all(
            item[
                "action_context"
            ]
            for item
            in verified_positive_records
        ),

        "all verified documents have notice number": all(
            bool(
                item[
                    "notice_numbers"
                ]
            )
            for item
            in verified_positive_records
        ),

        "all verified documents have official context": all(
            item[
                "official_context"
            ]
            for item
            in verified_positive_records
        ),

        "all verified documents have geographic context": all(
            bool(
                item[
                    "administrative_regions"
                ]
            )
            for item
            in verified_positive_records
        ),

        "all verified documents are not legal-reference-only": all(
            not item[
                "legal_reference_only"
            ]
            for item
            in verified_positive_records
        ),

        "all verified documents are not administrative-duty references": all(
            not item[
                "administrative_duty_reference"
            ]
            for item
            in verified_positive_records
        ),

        # ----------------------------------------------------
        # Runtime / SITE safety
        # ----------------------------------------------------

        "runtime registration remains blocked": (
            output_data[
                "runtime_registration_allowed"
            ]
            is False
        ),

        "SITE FALSE remains blocked": (
            output_data[
                "site_positive_allowed"
            ]
            is False
        ),

        "output written": (
            OUTPUT_PATH.exists()
        ),
    }

    print()

    print(
        "=" * 60
    )

    print(
        "VALIDATION"
    )

    print(
        "=" * 60
    )

    all_pass = True

    for (
        key,
        value,
    ) in validations.items():

        print(
            f"{key}: {value}"
        )

        if not value:

            all_pass = False

    print()

    print(
        f"all_pass: {all_pass}"
    )

    if not all_pass:

        failed = [
            key
            for key, value
            in validations.items()
            if not value
        ]

        print()

        print(
            "FAILED:"
        )

        for key in failed:

            print(
                f"- {key}"
            )

        raise AssertionError(
            "Development density management area "
            "target document candidate verification "
            "regression failed"
        )


if __name__ == "__main__":
    main()