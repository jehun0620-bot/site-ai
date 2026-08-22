# -*- coding: utf-8 -*-

"""
STEP 17-21-C-13-4E
Zone Ratio Map Layer Resolution Probe

목표
======================================================================
기존 law_zone_ratio_map.json에 이미 구축된 용도지역별
건폐율/용적률 정보를 계층별로 분해한다.

특히:

level 2
서울특별시 도시계획 조례
→ 실제 서울시 기본값 후보

level 4
국토의 계획 및 이용에 관한 법률 시행령
→ 국가 상한 / 허용 범위

를 구분한다.

이번 단계에서는 Rule Engine baseline을 아직 수정하지 않는다.
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any, Dict, List, Optional


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

INPUT_PATH = (
    OUTPUT_DIR
    / "law_zone_ratio_map.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "zone_ratio_map_layer_resolution.json"
)


# ============================================================
# TARGET
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


SEOUL_LAW_NAME = (
    "서울특별시 도시계획 조례"
)

NATIONAL_DECREE_NAME = (
    "국토의 계획 및 이용에 관한 법률 시행령"
)


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


def as_float(
    value: Any,
) -> Optional[float]:

    if isinstance(
        value,
        (
            int,
            float,
        ),
    ):

        return float(
            value
        )

    return None


# ============================================================
# candidate normalization
# ============================================================

def normalize_candidate(
    candidate: Dict[str, Any],
) -> Dict[str, Any]:

    return {

        "zone": (
            candidate.get(
                "zone"
            )
        ),

        "minimum": (
            as_float(
                candidate.get(
                    "minimum"
                )
            )
        ),

        "maximum": (
            as_float(
                candidate.get(
                    "maximum"
                )
            )
        ),

        "raw_values": (
            candidate.get(
                "raw_values",
                []
            )
        ),

        "percentage_details": (
            candidate.get(
                "percentage_details",
                []
            )
        ),

        "segment": (
            candidate.get(
                "segment"
            )
        ),

        "law_name": (
            candidate.get(
                "law_name"
            )
        ),

        "level": (
            candidate.get(
                "level"
            )
        ),

        "article_number": (
            candidate.get(
                "article_number"
            )
        ),

        "article_branch_number": (
            candidate.get(
                "article_branch_number"
            )
        ),

        "article_title": (
            candidate.get(
                "article_title"
            )
        ),

        "source_type": (
            candidate.get(
                "source_type"
            )
        ),
    }


# ============================================================
# collect candidates
# ============================================================

def collect_zone_candidates(
    zone_entry: Any,
) -> List[
    Dict[str, Any]
]:

    result = []

    if isinstance(
        zone_entry,
        dict,
    ):

        # law level 등의 key 아래 실제 candidate가 있는 구조
        for value in (
            zone_entry.values()
        ):

            if not isinstance(
                value,
                dict,
            ):

                continue

            if (
                "law_name"
                in value
                or "maximum"
                in value
                or "minimum"
                in value
            ):

                result.append(
                    normalize_candidate(
                        value
                    )
                )

            else:

                result.extend(
                    collect_zone_candidates(
                        value
                    )
                )

    elif isinstance(
        zone_entry,
        list,
    ):

        for value in zone_entry:

            result.extend(
                collect_zone_candidates(
                    value
                )
            )

    return result


# ============================================================
# choose layer
# ============================================================

def choose_candidates(
    candidates: List[
        Dict[str, Any]
    ],
    law_name: str,
) -> List[
    Dict[str, Any]
]:

    return [
        candidate
        for candidate
        in candidates
        if candidate.get(
            "law_name"
        )
        == law_name
    ]


def choose_best_max(
    candidates: List[
        Dict[str, Any]
    ],
) -> Optional[
    Dict[str, Any]
]:

    usable = [
        candidate
        for candidate
        in candidates
        if candidate.get(
            "maximum"
        )
        is not None
    ]

    if not usable:

        return None

    # 동일 법령에서 여러 후보가 있으면
    # 이번 단계에서는 임의로 숫자를 합치지 않는다.
    #
    # maximum 값이 하나뿐인지 검사하기 위해
    # 첫 candidate만 reference로 반환한다.
    return usable[
        0
    ]


# ============================================================
# main
# ============================================================

def main() -> int:

    data = load_json(
        INPUT_PATH
    )

    zone_maps = (
        data.get(
            "zone_maps",
            {}
        )
    )

    result_by_zone = {}

    unresolved = []

    ambiguous = []

    # ========================================================
    # each zone
    # ========================================================

    for zone in ZONES:

        zone_result = {}

        for category in (
            "건폐율",
            "용적률",
        ):

            category_map = (
                zone_maps.get(
                    category,
                    {}
                )
            )

            zone_entry = (
                category_map.get(
                    zone
                )
            )

            candidates = (
                collect_zone_candidates(
                    zone_entry
                )
            )

            seoul_candidates = (
                choose_candidates(
                    candidates,
                    SEOUL_LAW_NAME,
                )
            )

            national_candidates = (
                choose_candidates(
                    candidates,
                    NATIONAL_DECREE_NAME,
                )
            )

            seoul_values = sorted(
                {
                    candidate[
                        "maximum"
                    ]
                    for candidate
                    in seoul_candidates
                    if candidate.get(
                        "maximum"
                    )
                    is not None
                }
            )

            national_values = sorted(
                {
                    candidate[
                        "maximum"
                    ]
                    for candidate
                    in national_candidates
                    if candidate.get(
                        "maximum"
                    )
                    is not None
                }
            )

            seoul_best = (
                choose_best_max(
                    seoul_candidates
                )
            )

            national_best = (
                choose_best_max(
                    national_candidates
                )
            )

            status = (
                "RESOLVED"
            )

            if not seoul_values:

                status = (
                    "SEOUL_VALUE_MISSING"
                )

                unresolved.append(
                    {
                        "zone": (
                            zone
                        ),

                        "category": (
                            category
                        ),
                    }
                )

            elif (
                len(
                    seoul_values
                )
                > 1
            ):

                status = (
                    "SEOUL_VALUE_AMBIGUOUS"
                )

                ambiguous.append(
                    {
                        "zone": (
                            zone
                        ),

                        "category": (
                            category
                        ),

                        "values": (
                            seoul_values
                        ),
                    }
                )

            # -----------------------------------------------
            # national ceiling validation
            # -----------------------------------------------

            ceiling_valid = None

            if (
                len(
                    seoul_values
                )
                == 1
                and national_values
            ):

                ceiling_valid = (
                    seoul_values[
                        0
                    ]
                    <= max(
                        national_values
                    )
                )

            zone_result[
                category
            ] = {

                "status": (
                    status
                ),

                "seoul_values": (
                    seoul_values
                ),

                "national_values": (
                    national_values
                ),

                "seoul_selected": (
                    seoul_best
                ),

                "national_selected": (
                    national_best
                ),

                "national_ceiling_valid": (
                    ceiling_valid
                ),

                "all_candidates": (
                    candidates
                ),
            }

        result_by_zone[
            zone
        ] = (
            zone_result
        )

    # ========================================================
    # clean mapping
    # ========================================================

    resolved_map = {}

    for zone, info in (
        result_by_zone.items()
    ):

        bcr = (
            info[
                "건폐율"
            ]
        )

        far = (
            info[
                "용적률"
            ]
        )

        if (
            len(
                bcr[
                    "seoul_values"
                ]
            )
            == 1
            and len(
                far[
                    "seoul_values"
                ]
            )
            == 1
        ):

            resolved_map[
                zone
            ] = {

                "building_coverage_ratio": (
                    bcr[
                        "seoul_values"
                    ][
                        0
                    ]
                ),

                "floor_area_ratio": (
                    far[
                        "seoul_values"
                    ][
                        0
                    ]
                ),
            }

    # ========================================================
    # resolution
    # ========================================================

    complete = (
        len(
            resolved_map
        )
        == len(
            ZONES
        )
    )

    resolution = (
        "SEOUL_ZONE_BASE_NUMERIC_COMPLETE"
        if complete
        else "SEOUL_ZONE_BASE_NUMERIC_INCOMPLETE"
    )

    output = {

        "step": (
            "STEP 17-21-C-13-4E "
            "Zone Ratio Map Layer Resolution"
        ),

        "source": (
            str(
                INPUT_PATH
            )
        ),

        "zones": (
            ZONES
        ),

        "result_by_zone": (
            result_by_zone
        ),

        "resolved_map": (
            resolved_map
        ),

        "resolved_count": (
            len(
                resolved_map
            )
        ),

        "unresolved": (
            unresolved
        ),

        "ambiguous": (
            ambiguous
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
        "Zones:",
        len(
            ZONES
        ),
    )

    print(
        "Resolved:",
        len(
            resolved_map
        ),
    )

    print(
        "Unresolved:",
        len(
            unresolved
        ),
    )

    print(
        "Ambiguous:",
        len(
            ambiguous
        ),
    )

    print()

    print(
        "=== SEOUL BASE NUMERIC ==="
    )

    for zone in ZONES:

        info = (
            result_by_zone[
                zone
            ]
        )

        bcr = (
            info[
                "건폐율"
            ]
        )

        far = (
            info[
                "용적률"
            ]
        )

        print(
            zone
        )

        print(
            "  BCR Seoul:",
            bcr[
                "seoul_values"
            ],
            "| National:",
            bcr[
                "national_values"
            ],
            "| ceiling:",
            bcr[
                "national_ceiling_valid"
            ],
        )

        print(
            "  FAR Seoul:",
            far[
                "seoul_values"
            ],
            "| National:",
            far[
                "national_values"
            ],
            "| ceiling:",
            far[
                "national_ceiling_valid"
            ],
        )

    print()

    print(
        "=== RESOLVED MAP ==="
    )

    for zone, values in (
        resolved_map.items()
    ):

        print(
            f"{zone}: "
            f"BCR={values['building_coverage_ratio']} "
            f"| FAR={values['floor_area_ratio']}"
        )

    print()

    if unresolved:

        print(
            "=== UNRESOLVED ==="
        )

        for item in unresolved:

            print(
                "-",
                item,
            )

        print()

    if ambiguous:

        print(
            "=== AMBIGUOUS ==="
        )

        for item in ambiguous:

            print(
                "-",
                item,
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