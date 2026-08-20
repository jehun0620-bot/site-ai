# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14A-2
도시지역편입해제구역 기존 source 정의 복원

목표
======================================================================
1. site_spatial_source_snapshot.json에서
   도시지역편입해제구역 정의만 추출한다.
2. query_group / query_key / source / method 등을 확인한다.
3. condition snapshot의 SITE/SITE_HISTORY 분류도 비교한다.
4. 긴 JSON은 별도 evidence 파일에 저장한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-9-2-14A-2 "
    "도시지역편입해제구역 기존 source 정의 복원"
)

TARGET = "도시지역편입해제구역"

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

SOURCE_PATH = (
    OUTPUT_DIR
    / "site_spatial_source_snapshot.json"
)

CONDITION_PATH = (
    OUTPUT_DIR
    / "site_spatial_condition_snapshot.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_inclusion_release_definition_probe.json"
)


def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():
        return {}

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


def recursive_find_target(
    value: Any,
    path: str = "$",
    results=None,
):

    if results is None:
        results = []

    if isinstance(
        value,
        dict,
    ):

        if TARGET in value:

            results.append(
                {
                    "path": path,
                    "value": value[
                        TARGET
                    ],
                }
            )

        for key, item in value.items():

            recursive_find_target(
                item,
                f"{path}.{key}",
                results,
            )

    elif isinstance(
        value,
        list,
    ):

        for index, item in enumerate(
            value
        ):

            recursive_find_target(
                item,
                f"{path}[{index}]",
                results,
            )

    return results


def find_list_membership(
    value: Any,
    path: str = "$",
    results=None,
):

    if results is None:
        results = []

    if isinstance(
        value,
        dict,
    ):

        for key, item in value.items():

            find_list_membership(
                item,
                f"{path}.{key}",
                results,
            )

    elif isinstance(
        value,
        list,
    ):

        if TARGET in value:

            results.append(
                {
                    "path": path,
                    "index": value.index(
                        TARGET
                    ),
                    "count": len(
                        value
                    ),
                }
            )

        for index, item in enumerate(
            value
        ):

            find_list_membership(
                item,
                f"{path}[{index}]",
                results,
            )

    return results


def compact_definition(
    value: Any,
) -> Dict[str, Any]:

    if not isinstance(
        value,
        dict,
    ):

        return {
            "raw_type": type(
                value
            ).__name__,
            "value": value,
        }

    # 주요 필드는 실제 존재하는 것만 출력
    candidate_keys = [
        "query_group",
        "query_key",
        "description",
        "preferred_method",
        "method",
        "priority",
        "connection_status",
        "source",
        "provider",
        "dataset",
        "endpoint",
        "api",
        "layer",
        "code",
        "geometry_source",
        "history_source",
        "fallback",
    ]

    summary = {}

    for key in candidate_keys:

        if key in value:

            summary[
                key
            ] = value[
                key
            ]

    summary[
        "all_keys"
    ] = sorted(
        value.keys()
    )

    return summary


def main() -> int:

    source_data = load_json(
        SOURCE_PATH
    )

    condition_data = load_json(
        CONDITION_PATH
    )

    source_hits = (
        recursive_find_target(
            source_data
        )
    )

    condition_object_hits = (
        recursive_find_target(
            condition_data
        )
    )

    condition_list_hits = (
        find_list_membership(
            condition_data
        )
    )

    source_summaries = []

    for hit in source_hits:

        source_summaries.append(
            {
                "path": hit[
                    "path"
                ],
                "summary": (
                    compact_definition(
                        hit[
                            "value"
                        ]
                    )
                ),
                "raw": hit[
                    "value"
                ],
            }
        )

    result = {
        "step": STEP_NAME,
        "condition": TARGET,

        "source_snapshot": {
            "hit_count": len(
                source_hits
            ),
            "hits": (
                source_summaries
            ),
        },

        "condition_snapshot": {
            "object_hit_count": len(
                condition_object_hits
            ),
            "list_hit_count": len(
                condition_list_hits
            ),
            "list_hits": (
                condition_list_hits
            ),
        },

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "NONE"
            ),
            "reason": (
                "기존 source 정의와 조건 분류를 "
                "복원하는 단계"
            ),
        },
    }

    save_json(
        result
    )

    # ========================================================
    # 간략 콘솔
    # ========================================================

    print(
        "Source definitions:",
        len(
            source_summaries
        ),
    )

    for index, item in enumerate(
        source_summaries,
        start=1,
    ):

        summary = item[
            "summary"
        ]

        print()
        print(
            f"[Source {index}]"
        )

        print(
            "path:",
            item[
                "path"
            ],
        )

        print(
            "query_group:",
            summary.get(
                "query_group"
            ),
        )

        print(
            "query_key:",
            summary.get(
                "query_key"
            ),
        )

        print(
            "preferred_method:",
            summary.get(
                "preferred_method"
            ),
        )

        print(
            "source:",
            summary.get(
                "source"
            ),
        )

        print(
            "provider:",
            summary.get(
                "provider"
            ),
        )

        print(
            "dataset:",
            summary.get(
                "dataset"
            ),
        )

        print(
            "connection_status:",
            summary.get(
                "connection_status"
            ),
        )

        description = str(
            summary.get(
                "description",
                "",
            )
        )

        if len(
            description
        ) > 180:

            description = (
                description[:180]
                + "..."
            )

        print(
            "description:",
            description,
        )

    print()

    print(
        "Condition list hits:",
        len(
            condition_list_hits
        ),
    )

    for hit in condition_list_hits:

        print(
            "-",
            hit[
                "path"
            ],
        )

    print()

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