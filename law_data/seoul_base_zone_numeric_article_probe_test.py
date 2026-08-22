# -*- coding: utf-8 -*-

"""
STEP 17-21-C-13-4D
Seoul Base Zone Numeric Article Probe

목표
======================================================================
프로젝트 내부에 저장된 서울특별시 도시계획 조례 원문 / 상세조회 JSON에서
용도지역별 기본 건폐율 및 기본 용적률 조문을 직접 추출한다.

대상
======================================================================
- 제44조 계열: 용도지역별 건폐율
- 제48조 계열: 용도지역별 용적률

중요
======================================================================
이번 단계에서는 resolver를 만들지 않는다.

먼저 원문 source와 article text를 정확히 확보하고,
각 zone별 숫자 mapping이 실제 법문에서 완전히 복원 가능한지 확인한다.
"""

from __future__ import annotations

import json
import re

from pathlib import Path
from typing import Any, Dict, List, Tuple


# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

LAW_DIR = (
    BASE_DIR
    / "law_data"
)

OUTPUT_DIR = (
    LAW_DIR
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "seoul_base_zone_numeric_article_probe.json"
)


# ============================================================
# TARGET
# ============================================================

TARGET_LAW_TERMS = [
    "서울특별시 도시계획 조례",
    "서울특별시도시계획조례",
]

TARGET_ARTICLES = {
    "44": (
        "BUILDING_COVERAGE_RATIO"
    ),

    "48": (
        "FLOOR_AREA_RATIO"
    ),
}


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
# candidate extensions
# ============================================================

TEXT_SUFFIXES = {
    ".json",
    ".txt",
    ".md",
    ".xml",
}


# ============================================================
# util
# ============================================================

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


def read_text(
    path: Path,
) -> str:

    try:

        return path.read_text(
            encoding="utf-8",
        )

    except UnicodeDecodeError:

        try:

            return path.read_text(
                encoding="cp949",
            )

        except Exception:

            return ""

    except Exception:

        return ""


def compact(
    text: str,
    limit: int = 1200,
) -> str:

    text = (
        str(
            text
        )
        .replace(
            "\r",
            " "
        )
        .replace(
            "\n",
            " "
        )
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if len(
        text
    ) > limit:

        return (
            text[
                :limit
            ]
            + "..."
        )

    return text


def walk_json(
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

            yield from walk_json(
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

            yield from walk_json(
                value,
                f"{path}[{index}]",
            )


def object_text(
    obj: Any,
) -> str:

    if isinstance(
        obj,
        str,
    ):

        return obj

    try:

        return json.dumps(
            obj,
            ensure_ascii=False,
            default=str,
        )

    except Exception:

        return str(
            obj
        )


# ============================================================
# file discovery
# ============================================================

def discover_candidate_files() -> List[Path]:

    candidates = []

    for path in (
        LAW_DIR.rglob(
            "*"
        )
    ):

        if not path.is_file():

            continue

        if (
            path.suffix.lower()
            not in TEXT_SUFFIXES
        ):

            continue

        # generated output 중 너무 명백한 이번 probe 파일은 제외
        if (
            path.name
            == OUTPUT_PATH.name
        ):

            continue

        candidates.append(
            path
        )

    return candidates


# ============================================================
# source scoring
# ============================================================

def score_source_text(
    text: str,
) -> int:

    score = 0

    if any(
        term
        in text
        for term
        in TARGET_LAW_TERMS
    ):

        score += 100

    if (
        "제44조"
        in text
    ):

        score += 40

    if (
        "제48조"
        in text
    ):

        score += 40

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

    zone_hits = sum(
        1
        for zone
        in ZONES
        if zone
        in text
    )

    score += (
        zone_hits
        * 5
    )

    return score


# ============================================================
# article detection
# ============================================================

ARTICLE_PATTERNS = {

    "44": [
        re.compile(
            r"제\s*44\s*조"
        ),

        re.compile(
            r"제44조"
        ),
    ],

    "48": [
        re.compile(
            r"제\s*48\s*조"
        ),

        re.compile(
            r"제48조"
        ),
    ],
}


def contains_article(
    text: str,
    article_no: str,
) -> bool:

    return any(
        pattern.search(
            text
        )
        for pattern
        in ARTICLE_PATTERNS[
            article_no
        ]
    )


# ============================================================
# numeric extraction
# ============================================================

PERCENT_PATTERN = re.compile(
    r"(?P<value>\d{1,4}(?:\.\d+)?)\s*퍼센트"
)


def extract_percent_values(
    text: str,
) -> List[float]:

    values = []

    for match in (
        PERCENT_PATTERN.finditer(
            text
        )
    ):

        try:

            value = float(
                match.group(
                    "value"
                )
            )

        except Exception:

            continue

        if value not in values:

            values.append(
                value
            )

    return values


def extract_zone_contexts(
    text: str,
    window: int = 250,
) -> Dict[
    str,
    List[
        Dict[str, Any]
    ]
]:

    result = {}

    for zone in (
        ZONES
    ):

        contexts = []

        start = 0

        while True:

            index = text.find(
                zone,
                start,
            )

            if index < 0:

                break

            left = max(
                0,
                index
                - window,
            )

            right = min(
                len(
                    text
                ),
                index
                + len(
                    zone
                )
                + window,
            )

            context = (
                text[
                    left:right
                ]
            )

            contexts.append(
                {
                    "context": (
                        compact(
                            context,
                            700,
                        )
                    ),

                    "percent_values": (
                        extract_percent_values(
                            context
                        )
                    ),
                }
            )

            start = (
                index
                + len(
                    zone
                )
            )

        if contexts:

            result[
                zone
            ] = (
                contexts
            )

    return result


# ============================================================
# JSON probe
# ============================================================

def probe_json_file(
    path: Path,
) -> List[
    Dict[str, Any]
]:

    try:

        with path.open(
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(
                f
            )

    except Exception:

        return []

    hits = []

    for obj_path, obj in (
        walk_json(
            data
        )
    ):

        text = object_text(
            obj
        )

        score = score_source_text(
            text
        )

        if score < 80:

            continue

        article_hits = [
            article_no
            for article_no
            in TARGET_ARTICLES
            if contains_article(
                text,
                article_no,
            )
        ]

        if not article_hits:

            continue

        hits.append(
            {
                "file": (
                    str(
                        path.relative_to(
                            BASE_DIR
                        )
                    )
                ),

                "json_path": (
                    obj_path
                ),

                "score": (
                    score
                ),

                "articles": (
                    article_hits
                ),

                "zones": [
                    zone
                    for zone
                    in ZONES
                    if zone
                    in text
                ],

                "percent_values": (
                    extract_percent_values(
                        text
                    )
                ),

                "zone_contexts": (
                    extract_zone_contexts(
                        text
                    )
                ),

                "preview": (
                    compact(
                        text
                    )
                ),
            }
        )

    return hits


# ============================================================
# plain text probe
# ============================================================

def probe_text_file(
    path: Path,
) -> List[
    Dict[str, Any]
]:

    text = read_text(
        path
    )

    if not text:

        return []

    score = score_source_text(
        text
    )

    if score < 80:

        return []

    article_hits = [
        article_no
        for article_no
        in TARGET_ARTICLES
        if contains_article(
            text,
            article_no,
        )
    ]

    if not article_hits:

        return []

    return [
        {
            "file": (
                str(
                    path.relative_to(
                        BASE_DIR
                    )
                )
            ),

            "json_path": (
                None
            ),

            "score": (
                score
            ),

            "articles": (
                article_hits
            ),

            "zones": [
                zone
                for zone
                in ZONES
                if zone
                in text
            ],

            "percent_values": (
                extract_percent_values(
                    text
                )
            ),

            "zone_contexts": (
                extract_zone_contexts(
                    text
                )
            ),

            "preview": (
                compact(
                    text
                )
            ),
        }
    ]


# ============================================================
# ranking
# ============================================================

def rank_hits(
    hits: List[
        Dict[str, Any]
    ]
) -> List[
    Dict[str, Any]
]:

    return sorted(
        hits,
        key=lambda item: (
            item[
                "score"
            ],
            len(
                item[
                    "zones"
                ]
            ),
            len(
                item[
                    "percent_values"
                ]
            ),
        ),
        reverse=True,
    )


# ============================================================
# article summary
# ============================================================

def summarize_article(
    ranked: List[
        Dict[str, Any]
    ],
    article_no: str,
) -> Dict[str, Any]:

    article_hits = [
        item
        for item
        in ranked
        if article_no
        in item[
            "articles"
        ]
    ]

    zone_evidence = {}

    for zone in (
        ZONES
    ):

        contexts = []

        for item in (
            article_hits
        ):

            zone_contexts = (
                item.get(
                    "zone_contexts",
                    {}
                )
            )

            for context in (
                zone_contexts.get(
                    zone,
                    []
                )
            ):

                contexts.append(
                    {
                        "file": (
                            item[
                                "file"
                            ]
                        ),

                        "json_path": (
                            item[
                                "json_path"
                            ]
                        ),

                        "score": (
                            item[
                                "score"
                            ]
                        ),

                        **context,
                    }
                )

        zone_evidence[
            zone
        ] = (
            contexts[
                :10
            ]
        )

    zones_found = [
        zone
        for zone, contexts
        in zone_evidence.items()
        if contexts
    ]

    return {

        "article": (
            article_no
        ),

        "role": (
            TARGET_ARTICLES[
                article_no
            ]
        ),

        "hit_count": (
            len(
                article_hits
            )
        ),

        "zones_found": (
            zones_found
        ),

        "zones_missing": [
            zone
            for zone
            in ZONES
            if zone
            not in zones_found
        ],

        "top_hits": (
            article_hits[
                :20
            ]
        ),

        "zone_evidence": (
            zone_evidence
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    files = discover_candidate_files()

    all_hits = []

    checked = 0

    for path in (
        files
    ):

        checked += 1

        if (
            path.suffix.lower()
            == ".json"
        ):

            hits = probe_json_file(
                path
            )

        else:

            hits = probe_text_file(
                path
            )

        all_hits.extend(
            hits
        )

    ranked = rank_hits(
        all_hits
    )

    article_44 = summarize_article(
        ranked,
        "44",
    )

    article_48 = summarize_article(
        ranked,
        "48",
    )

    source_files = sorted(
        {
            item[
                "file"
            ]
            for item
            in ranked
        }
    )

    both_ready = (
        article_44[
            "hit_count"
        ]
        > 0
        and article_48[
            "hit_count"
        ]
        > 0
    )

    resolution = (
        "BASE_ARTICLE_SOURCE_FOUND"
        if both_ready
        else "BASE_ARTICLE_SOURCE_INCOMPLETE"
    )

    output = {

        "step": (
            "STEP 17-21-C-13-4D "
            "Seoul Base Zone Numeric Article Probe"
        ),

        "files_checked": (
            checked
        ),

        "candidate_hit_count": (
            len(
                ranked
            )
        ),

        "source_files": (
            source_files
        ),

        "article_44": (
            article_44
        ),

        "article_48": (
            article_48
        ),

        "top_hits": (
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
        checked,
    )

    print(
        "Candidate hits:",
        len(
            ranked
        ),
    )

    print(
        "Source files:",
        len(
            source_files
        ),
    )

    print()

    print(
        "=== ARTICLE 44 / BCR ==="
    )

    print(
        "Hits:",
        article_44[
            "hit_count"
        ],
    )

    print(
        "Zones found:",
        len(
            article_44[
                "zones_found"
            ]
        ),
        "/",
        len(
            ZONES
        ),
    )

    print(
        "Missing:",
        article_44[
            "zones_missing"
        ],
    )

    print()

    for index, item in enumerate(
        article_44[
            "top_hits"
        ][
            :10
        ],
        start=1,
    ):

        print(
            f"[44-{index}] "
            f"score={item['score']} "
            f"| {item['file']} "
            f"| {item['json_path']}"
        )

        print(
            " zones:",
            item[
                "zones"
            ],
        )

        print(
            " percent:",
            item[
                "percent_values"
            ][
                :30
            ],
        )

        print(
            " ",
            item[
                "preview"
            ][
                :700
            ],
        )

        print()

    print(
        "=== ARTICLE 48 / FAR ==="
    )

    print(
        "Hits:",
        article_48[
            "hit_count"
        ],
    )

    print(
        "Zones found:",
        len(
            article_48[
                "zones_found"
            ]
        ),
        "/",
        len(
            ZONES
        ),
    )

    print(
        "Missing:",
        article_48[
            "zones_missing"
        ],
    )

    print()

    for index, item in enumerate(
        article_48[
            "top_hits"
        ][
            :10
        ],
        start=1,
    ):

        print(
            f"[48-{index}] "
            f"score={item['score']} "
            f"| {item['file']} "
            f"| {item['json_path']}"
        )

        print(
            " zones:",
            item[
                "zones"
            ],
        )

        print(
            " percent:",
            item[
                "percent_values"
            ][
                :30
            ],
        )

        print(
            " ",
            item[
                "preview"
            ][
                :700
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