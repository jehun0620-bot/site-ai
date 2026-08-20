# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14A
도시지역편입해제구역 공식 source / 관리체계 probe

목표
======================================================================
1. 도시지역편입해제구역 관련 공식 명칭을 프로젝트 evidence에서 탐색한다.
2. 대상 SITE/PNU 관련 기존 토지이음 evidence를 우선 재사용한다.
3. 명칭 변형 및 관리코드 후보를 수집한다.
4. 문자열 출현만으로 SITE TRUE/FALSE 판정하지 않는다.
5. source / geometry / 이력체계가 확정되지 않으면 UNKNOWN 유지한다.

판정 원칙
======================================================================
- 문자열 출현 != SITE 포함
- 문자열 부재 != FALSE
- HTTP 실패 != FALSE
- 관리코드 의미 추정 금지
- 과거 이력 조건은 현행 Polygon 부재만으로 FALSE 금지
"""

from __future__ import annotations

import json
import re

from pathlib import Path
from typing import Any, Dict, List, Tuple


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-14A "
    "도시지역편입해제구역 공식 source / 관리체계 probe"
)


# ============================================================
# 대상 조건
# ============================================================

TARGET_NAME = "도시지역편입해제구역"

SEARCH_TERMS = [
    "도시지역편입해제구역",
    "도시지역 편입 해제구역",
    "도시지역편입",
    "편입해제구역",
    "편입해제",
]


# ============================================================
# 경로
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

LAW_DATA_DIR = (
    BASE_DIR
    / "law_data"
)

OUTPUT_DIR = (
    LAW_DATA_DIR
    / "output"
)

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR
    / "site_spatial_query_context.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_inclusion_release_source_probe.json"
)


# ============================================================
# 공통
# ============================================================

def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():
        return {}

    try:

        with path.open(
            "r",
            encoding="utf-8",
        ) as f:

            return json.load(f)

    except Exception:

        return {}


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
# SITE context
# ============================================================

def load_site() -> Dict[str, str]:

    data = load_json(
        QUERY_CONTEXT_PATH
    )

    context = data.get(
        "query_context",
        {},
    )

    return {
        "site_id": safe_string(
            context.get(
                "site_id"
            )
        ),
        "address": safe_string(
            context.get(
                "address"
            )
        ),
        "pnu": safe_string(
            context.get(
                "pnu"
            )
        ),
    }


# ============================================================
# JSON / TXT 계열 검색
# ============================================================

def find_text_hits(
    text: str,
) -> List[
    Dict[str, Any]
]:

    hits = []

    for term in SEARCH_TERMS:

        count = text.count(
            term
        )

        if count <= 0:
            continue

        first_index = text.find(
            term
        )

        start = max(
            0,
            first_index - 120,
        )

        end = min(
            len(text),
            first_index + len(term) + 200,
        )

        preview = (
            text[
                start:end
            ]
            .replace(
                "\r",
                " ",
            )
            .replace(
                "\n",
                " ",
            )
        )

        hits.append(
            {
                "term": term,
                "count": count,
                "preview": preview,
            }
        )

    return hits


def search_existing_outputs() -> Tuple[
    List[Dict[str, Any]],
    int,
]:

    results = []

    scanned = 0

    if not OUTPUT_DIR.exists():
        return (
            results,
            scanned,
        )

    for path in sorted(
        OUTPUT_DIR.iterdir()
    ):

        if not path.is_file():
            continue

        if path == OUTPUT_PATH:
            continue

        if path.suffix.lower() not in (
            ".json",
            ".txt",
            ".html",
            ".xml",
        ):
            continue

        try:

            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

        except Exception:
            continue

        scanned += 1

        hits = find_text_hits(
            text
        )

        if not hits:
            continue

        results.append(
            {
                "file": path.name,
                "path": str(
                    path
                ),
                "hits": hits,
            }
        )

    return (
        results,
        scanned,
    )


# ============================================================
# 코드 후보 탐색
# ============================================================

def extract_code_candidates(
    results: List[
        Dict[str, Any]
    ],
) -> List[str]:

    candidates = set()

    # UPIS / MapPlan 계열에서 사용했던
    # UQ / UQM / UQS 형태만 "후보"로 수집한다.
    #
    # 의미를 확정하지 않는다.

    pattern = re.compile(
        r"\b"
        r"(?:UQ[A-Z]?\d{3,6})"
        r"\b",
        re.IGNORECASE,
    )

    for result in results:

        for hit in result.get(
            "hits",
            [],
        ):

            preview = safe_string(
                hit.get(
                    "preview"
                )
            )

            for match in pattern.findall(
                preview
            ):

                candidates.add(
                    match.upper()
                )

    return sorted(
        candidates
    )


# ============================================================
# 결과 분류
# ============================================================

def classify_hit_sources(
    results: List[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    mapplan_files = []
    eum_files = []
    law_files = []
    other_files = []

    for result in results:

        name = (
            result[
                "file"
            ].lower()
        )

        if (
            "mapplan" in name
        ):

            mapplan_files.append(
                result[
                    "file"
                ]
            )

        elif (
            "eum" in name
            or "landuse" in name
        ):

            eum_files.append(
                result[
                    "file"
                ]
            )

        elif (
            "law" in name
            or "ordin" in name
        ):

            law_files.append(
                result[
                    "file"
                ]
            )

        else:

            other_files.append(
                result[
                    "file"
                ]
            )

    return {
        "mapplan_files": (
            sorted(
                set(
                    mapplan_files
                )
            )
        ),
        "eum_files": (
            sorted(
                set(
                    eum_files
                )
            )
        ),
        "law_files": (
            sorted(
                set(
                    law_files
                )
            )
        ),
        "other_files": (
            sorted(
                set(
                    other_files
                )
            )
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    site = load_site()

    # --------------------------------------------------------
    # 기존 evidence 검색
    # --------------------------------------------------------

    (
        results,
        scanned_count,
    ) = search_existing_outputs()

    code_candidates = (
        extract_code_candidates(
            results
        )
    )

    source_groups = (
        classify_hit_sources(
            results
        )
    )

    hit_file_count = len(
        results
    )

    total_hit_count = sum(
        sum(
            hit.get(
                "count",
                0,
            )
            for hit in result.get(
                "hits",
                [],
            )
        )
        for result in results
    )

    # --------------------------------------------------------
    # 현재 판정
    # --------------------------------------------------------

    if hit_file_count > 0:

        reason = (
            "기존 프로젝트 evidence에서 "
            "도시지역편입해제구역 관련 문자열을 "
            "확인했으나 문자열 출현만으로 "
            "대상 SITE의 과거 편입·해제 이력을 "
            "확정할 수 없음. 공식 관리코드 및 "
            "지정/해제 고시 source 추가 검증 필요"
        )

    else:

        reason = (
            "기존 프로젝트 evidence에서 "
            "도시지역편입해제구역 관련 명칭을 "
            "확인하지 못했으나 문자열 부재는 "
            "FALSE 근거가 아님. 공식 관리체계 및 "
            "지정/해제 이력 source 추가 검증 필요"
        )

    resolution = {
        "query_status": (
            "QUERY_SUCCESS"
        ),
        "resolution": (
            "UNKNOWN"
        ),
        "confidence": (
            "NONE"
        ),
        "reason": (
            reason
        ),
    }

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    result = {
        "step": STEP_NAME,

        "condition": (
            TARGET_NAME
        ),

        "condition_type": (
            "SITE_HISTORY"
        ),

        "site": site,

        "search_terms": (
            SEARCH_TERMS
        ),

        "existing_evidence": {
            "scanned_file_count": (
                scanned_count
            ),
            "hit_file_count": (
                hit_file_count
            ),
            "total_hit_count": (
                total_hit_count
            ),
            "results": (
                results
            ),
        },

        "source_groups": (
            source_groups
        ),

        "code_candidates": (
            code_candidates
        ),

        "validation_rules": {
            "문자열 출현만으로 TRUE 금지": True,
            "문자열 부재만으로 FALSE 금지": True,
            "관리코드 의미 추정 금지": True,
            "현행 Polygon 부재만으로 과거 이력 FALSE 금지": True,
            "지정/해제 공식 evidence 필요": True,
        },

        "resolution": (
            resolution
        ),

        "next_step": (
            "검색 hit 및 관리코드 후보를 기준으로 "
            "도시지역편입해제구역 공식 지정/해제 "
            "source와 PNU 이력 연결 가능성을 검증"
        ),
    }

    save_json(
        result
    )

    # --------------------------------------------------------
    # 초간략 콘솔
    # --------------------------------------------------------

    print(
        "Condition type:",
        "SITE_HISTORY",
    )

    print(
        "Files scanned:",
        scanned_count,
    )

    print(
        "Hit files:",
        hit_file_count,
    )

    print(
        "Total hits:",
        total_hit_count,
    )

    print(
        "Code candidates:",
        code_candidates,
    )

    print(
        "MapPlan hits:",
        len(
            source_groups[
                "mapplan_files"
            ]
        ),
    )

    print(
        "EUM hits:",
        len(
            source_groups[
                "eum_files"
            ]
        ),
    )

    print(
        "resolution:",
        resolution[
            "resolution"
        ],
    )

    print(
        "confidence:",
        resolution[
            "confidence"
        ],
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