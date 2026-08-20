# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14A-1
도시지역편입해제구역 기존 evidence hit 요약

목표
======================================================================
1. 14A 결과 JSON을 읽는다.
2. hit가 나온 파일명만 확인한다.
3. 각 파일에서 대표 hit 1개만 짧게 출력한다.
4. 긴 결과는 콘솔에 출력하지 않는다.
5. 실제 지정/해제 evidence인지 설명문인지 다음 단계에서 판별한다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-9-2-14A-1 "
    "도시지역편입해제구역 evidence hit summary"
)

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

INPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_inclusion_release_source_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_inclusion_release_hit_summary.json"
)


def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip()


def compact(
    value: Any,
    limit: int = 240,
) -> str:

    text = safe_string(
        value
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
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
        )


def classify_context(
    preview: str,
) -> str:

    text = safe_string(
        preview
    )

    history_tokens = [
        "지정",
        "해제",
        "고시",
        "변경",
        "편입",
        "고시번호",
        "고시일",
    ]

    description_tokens = [
        "조건",
        "UNKNOWN",
        "판정",
        "미해결",
        "검색",
        "source",
        "목표",
        "원칙",
    ]

    history_score = sum(
        token in text
        for token in history_tokens
    )

    description_score = sum(
        token in text
        for token in description_tokens
    )

    if (
        history_score >= 2
        and history_score
        > description_score
    ):

        return (
            "POSSIBLE_HISTORY_EVIDENCE"
        )

    if (
        description_score
        >= history_score
    ):

        return (
            "LIKELY_DESCRIPTION"
        )

    return (
        "UNCLASSIFIED"
    )


def main() -> int:

    data = load_json(
        INPUT_PATH
    )

    evidence = data.get(
        "existing_evidence",
        {},
    )

    results = evidence.get(
        "results",
        [],
    )

    summaries = []

    for result in results:

        hits = result.get(
            "hits",
            [],
        )

        if not hits:
            continue

        first_hit = hits[
            0
        ]

        preview = compact(
            first_hit.get(
                "preview"
            ),
            limit=240,
        )

        classification = (
            classify_context(
                preview
            )
        )

        total_hits = sum(
            int(
                hit.get(
                    "count",
                    0,
                )
            )
            for hit in hits
        )

        summaries.append(
            {
                "file": (
                    result.get(
                        "file"
                    )
                ),
                "total_hits": (
                    total_hits
                ),
                "representative_term": (
                    first_hit.get(
                        "term"
                    )
                ),
                "classification": (
                    classification
                ),
                "preview": (
                    preview
                ),
            }
        )

    possible_history = [
        item
        for item in summaries
        if item[
            "classification"
        ]
        == "POSSIBLE_HISTORY_EVIDENCE"
    ]

    result = {
        "step": STEP_NAME,

        "condition": (
            "도시지역편입해제구역"
        ),

        "hit_file_count": (
            len(
                summaries
            )
        ),

        "summaries": (
            summaries
        ),

        "possible_history_file_count": (
            len(
                possible_history
            )
        ),

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "NONE"
            ),
            "reason": (
                "hit 파일의 성격을 분류하는 단계이며 "
                "공식 지정/해제 evidence 검증 전"
            ),
        },
    }

    save_json(
        result
    )

    print(
        "Hit files:",
        len(
            summaries
        ),
    )

    for index, item in enumerate(
        summaries,
        start=1,
    ):

        print()

        print(
            f"[{index}]",
            item[
                "file"
            ],
        )

        print(
            "hits:",
            item[
                "total_hits"
            ],
        )

        print(
            "type:",
            item[
                "classification"
            ],
        )

        print(
            "preview:",
            item[
                "preview"
            ],
        )

    print()

    print(
        "Possible history files:",
        len(
            possible_history
        ),
    )

    print(
        "resolution: UNKNOWN"
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