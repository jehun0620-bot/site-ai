# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-S-2-DIAG

Development Density Management Area
S-2 Qualified Endpoint Region Schema Inspection

목적
======================================================================

S-2 JSON에서 qualified historical endpoint의 실제 region 저장 구조를
확인한다.

판정/승격/네트워크 요청은 하지 않는다.
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any, Dict, List


# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_source_family_entry_endpoint_qualification.json"
    )
)


# ============================================================
# UTIL
# ============================================================

def walk_dicts(
    value: Any,
):

    if isinstance(
        value,
        dict,
    ):

        yield value

        for child in value.values():

            if isinstance(
                child,
                (
                    dict,
                    list,
                ),
            ):

                yield from walk_dicts(
                    child
                )

    elif isinstance(
        value,
        list,
    ):

        for child in value:

            if isinstance(
                child,
                (
                    dict,
                    list,
                ),
            ):

                yield from walk_dicts(
                    child
                )


def shorten(
    value: Any,
    limit: int = 1200,
) -> str:

    try:

        text = json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )

    except Exception:

        text = repr(
            value
        )

    if len(
        text
    ) > limit:

        text = (
            text[
                :limit
            ]
            + "\n... <truncated>"
        )

    return text


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print(
        "=" * 70
    )

    print(
        "DEVELOPMENT DENSITY MANAGEMENT AREA"
    )

    print(
        "S-2 QUALIFIED ENDPOINT REGION SCHEMA INSPECTION"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "Input:",
        INPUT_PATH,
    )

    if not INPUT_PATH.exists():

        raise FileNotFoundError(
            INPUT_PATH
        )

    data = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        data,
        dict,
    ):

        raise TypeError(
            "Input must be JSON object."
        )

    # ========================================================
    # TOP LEVEL
    # ========================================================

    print()

    print(
        "TOP-LEVEL KEYS"
    )

    print(
        "-" * 70
    )

    for key in data.keys():

        value = data.get(
            key
        )

        value_type = type(
            value
        ).__name__

        if isinstance(
            value,
            list,
        ):

            extra = (
                f"len={len(value)}"
            )

        elif isinstance(
            value,
            dict,
        ):

            extra = (
                f"keys={list(value.keys())[:20]}"
            )

        else:

            extra = ""

        print(
            f"{key}: "
            f"{value_type} "
            f"{extra}"
        )

    # ========================================================
    # LIKELY ENDPOINT LISTS
    # ========================================================

    candidate_keys = [
        "qualified_endpoints",
        "qualified_historical_entry_endpoints",
        "next_stage_endpoint_pool",
        "all_canonical_records",
        "canonical_records",
        "records",
    ]

    print()

    print(
        "LIKELY ENDPOINT COLLECTIONS"
    )

    print(
        "-" * 70
    )

    for key in candidate_keys:

        value = data.get(
            key
        )

        if not isinstance(
            value,
            list,
        ):

            print(
                f"{key}: NOT LIST"
            )

            continue

        print(
            f"{key}: {len(value)} records"
        )

        if value:

            first = value[
                0
            ]

            if isinstance(
                first,
                dict,
            ):

                print(
                    "  first record keys:",
                    sorted(
                        first.keys()
                    ),
                )

    # ========================================================
    # QUALIFIED RECORD DISCOVERY
    # ========================================================

    qualified_records: List[
        Dict[str, Any]
    ] = []

    seen_ids = set()

    for item in walk_dicts(
        data
    ):

        if not isinstance(
            item,
            dict,
        ):

            continue

        classification = str(
            item.get(
                "classification"
            )
            or item.get(
                "endpoint_class"
            )
            or ""
        )

        qualified = (
            item.get(
                "qualified"
            )
            is True
        )

        if not (
            qualified
            or classification.startswith(
                "QUALIFIED_HISTORICAL_"
            )
        ):

            continue

        url = str(
            item.get(
                "url"
            )
            or item.get(
                "final_url"
            )
            or item.get(
                "input_url"
            )
            or ""
        )

        if not url:
            continue

        identity = (
            classification,
            url,
            tuple(
                sorted(
                    item.keys()
                )
            ),
        )

        if identity in seen_ids:
            continue

        seen_ids.add(
            identity
        )

        qualified_records.append(
            item
        )

    print()

    print(
        "DISCOVERED QUALIFIED RECORD VARIANTS:",
        len(
            qualified_records
        ),
    )

    # ========================================================
    # PRINT FIRST 30 VARIANTS
    # ========================================================

    for index, item in enumerate(
        qualified_records[
            :30
        ],
        start=1,
    ):

        print()

        print(
            "=" * 70
        )

        print(
            f"QUALIFIED VARIANT {index}"
        )

        print(
            "=" * 70
        )

        print(
            "Classification:",
            item.get(
                "classification"
            )
            or item.get(
                "endpoint_class"
            ),
        )

        print(
            "Family:",
            item.get(
                "source_family"
            ),
        )

        print(
            "URL:",
            item.get(
                "url"
            )
            or item.get(
                "final_url"
            )
            or item.get(
                "input_url"
            ),
        )

        print()

        print(
            "KEYS:"
        )

        print(
            sorted(
                item.keys()
            )
        )

        # ----------------------------------------------------
        # Region-related key candidates
        # ----------------------------------------------------

        print()

        print(
            "REGION-LIKE FIELDS"
        )

        print(
            "-" * 70
        )

        region_like_found = False

        for key, value in item.items():

            lowered = str(
                key
            ).lower()

            if any(
                token in lowered
                for token in [
                    "region",
                    "municip",
                    "location",
                    "area",
                    "bound",
                    "match",
                    "reason",
                    "evidence",
                    "source",
                ]
            ):

                region_like_found = True

                print()

                print(
                    f"[{key}]"
                )

                print(
                    shorten(
                        value
                    )
                )

        if not region_like_found:

            print(
                "No region-like field names."
            )

        print()

        print(
            "FULL RECORD"
        )

        print(
            "-" * 70
        )

        print(
            shorten(
                item,
                limit=5000,
            )
        )

    # ========================================================
    # SPECIAL URL SEARCH
    # ========================================================

    probes = [
        "bsgangseo.go.kr/portal/bsgsNscvrg",
        "bsgangseo.go.kr/portal/contents.do?mid=0501020000",
        "beogeunae.dangjin.go.kr",
        "119.gg.go.kr/seongnam",
        "119.gg.go.kr/pyeongtaek",
    ]

    print()

    print(
        "=" * 70
    )

    print(
        "KNOWN QUALIFIED URL RECORD SEARCH"
    )

    print(
        "=" * 70
    )

    for probe in probes:

        matches = []

        for item in walk_dicts(
            data
        ):

            if not isinstance(
                item,
                dict,
            ):

                continue

            blob = " ".join(
                str(
                    item.get(
                        key
                    )
                    or ""
                )
                for key in [
                    "url",
                    "final_url",
                    "input_url",
                ]
            )

            if probe in blob:

                matches.append(
                    item
                )

        print()

        print(
            f"PROBE: {probe}"
        )

        print(
            f"Matches: {len(matches)}"
        )

        for match_index, item in enumerate(
            matches[
                :10
            ],
            start=1,
        ):

            print()

            print(
                f"  MATCH {match_index}"
            )

            print(
                "  Keys:",
                sorted(
                    item.keys()
                ),
            )

            print(
                "  Record:"
            )

            print(
                shorten(
                    item,
                    limit=3500,
                )
            )

    print()

    print(
        "=" * 70
    )

    print(
        "INSPECTION COMPLETED"
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()