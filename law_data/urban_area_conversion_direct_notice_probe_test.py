# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14C-1
도시지역편입해제구역 Direct address/PNU 결정고시 정밀 추출

목표
======================================================================
1. 직전 14C JSON을 재사용한다.
2. Direct address/PNU hit 1건을 상세 출력한다.
3. 같은 고시관리코드가 combined 후보에도 있는지 확인한다.
4. 대상 주소가 정확히 개포동 12번지인지 확인한다.
5. 고시 내용이 실제 도시지역 편입/해제인지 구분한다.
6. 아직 TRUE/FALSE 판정하지 않는다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-9-2-14C-1 "
    "Direct address/PNU 결정고시 정밀 추출"
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
    / "urban_area_conversion_announcement_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_direct_notice_probe.json"
)


def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip()


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


def main() -> int:

    data = load_json(
        INPUT_PATH
    )

    site = data.get(
        "site",
        {},
    )

    search = data.get(
        "search",
        {},
    )

    direct_hits = search.get(
        "direct_address_hits",
        [],
    )

    combined_hits = search.get(
        "combined_hits",
        [],
    )

    site_address = safe_string(
        site.get(
            "address"
        )
    )

    site_pnu = safe_string(
        site.get(
            "pnu"
        )
    )

    direct_results = []

    for item in direct_hits:

        row = item.get(
            "row",
            {},
        )

        title = safe_string(
            row.get(
                "TTL"
            )
        )

        content = safe_string(
            row.get(
                "CN"
            )
        )

        full_text = (
            title
            + " "
            + content
        )

        exact_address_match = (
            bool(
                site_address
            )
            and site_address
            in full_text
        )

        pnu_match = (
            bool(
                site_pnu
            )
            and site_pnu
            in full_text
        )

        gaepo_12_match = (
            "개포동 12"
            in full_text
        )

        # ----------------------------------------------
        # 우리가 실제 찾는 강한 history 표현
        # ----------------------------------------------

        target_event_terms = [
            "도시지역 편입",
            "도시지역편입",
            "개발제한구역 해제",
            "개발제한구역해제",
            "시가화조정구역 해제",
            "시가화조정구역해제",
            "녹지지역 해제",
            "녹지지역해제",
        ]

        matched_target_events = [
            term
            for term
            in target_event_terms
            if term in full_text
        ]

        # 일반적인 '해제'는 별도로 기록
        generic_release = (
            "해제"
            in full_text
        )

        direct_results.append(
            {
                "ANCMNT_MNG_CD": (
                    row.get(
                        "ANCMNT_MNG_CD"
                    )
                ),
                "ANCMNT_TYPE": (
                    row.get(
                        "ANCMNT_TYPE"
                    )
                ),
                "ANCMNT_NO": (
                    row.get(
                        "ANCMNT_NO"
                    )
                ),
                "ANCMNT_YMD": (
                    row.get(
                        "ANCMNT_YMD"
                    )
                ),
                "TKCG_INST": (
                    row.get(
                        "TKCG_INST"
                    )
                ),
                "ANCMNT_INST": (
                    row.get(
                        "ANCMNT_INST"
                    )
                ),
                "TTL": (
                    title
                ),
                "CN": (
                    content
                ),
                "exact_address_match": (
                    exact_address_match
                ),
                "pnu_match": (
                    pnu_match
                ),
                "gaepo_12_match": (
                    gaepo_12_match
                ),
                "matched_target_events": (
                    matched_target_events
                ),
                "generic_release": (
                    generic_release
                ),
            }
        )

    # ========================================================
    # combined 후보와 동일 고시인지 확인
    # ========================================================

    combined_codes = set()

    for item in combined_hits:

        row = item.get(
            "row",
            {},
        )

        code = safe_string(
            row.get(
                "ANCMNT_MNG_CD"
            )
        )

        if code:

            combined_codes.add(
                code
            )

    for item in direct_results:

        code = safe_string(
            item.get(
                "ANCMNT_MNG_CD"
            )
        )

        item[
            "also_in_combined_hits"
        ] = (
            code
            in combined_codes
        )

    # ========================================================
    # 분류
    # ========================================================

    direct_target_event_count = sum(
        bool(
            item.get(
                "matched_target_events"
            )
        )
        for item in direct_results
    )

    gaepo12_count = sum(
        item.get(
            "gaepo_12_match"
        )
        is True
        for item in direct_results
    )

    if direct_target_event_count > 0:

        assessment = (
            "DIRECT_TARGET_HISTORY_CANDIDATE"
        )

        reason = (
            "대상 SITE 직접 일치 고시에서 "
            "도시지역 편입 또는 관련 용도지역/구역 "
            "해제 표현이 확인됨. 고시 적용범위 "
            "geometry/필지 검증 필요"
        )

    elif direct_results:

        assessment = (
            "DIRECT_NOTICE_BUT_NOT_TARGET_HISTORY"
        )

        reason = (
            "대상 SITE 관련 직접 고시는 확인됐으나 "
            "도시지역 편입 또는 개발제한/시가화조정/"
            "녹지지역 해제에 해당하는 표현은 확인되지 않음"
        )

    else:

        assessment = (
            "NO_DIRECT_NOTICE"
        )

        reason = (
            "직접 주소/PNU 일치 고시 없음"
        )

    result = {
        "step": STEP_NAME,

        "condition": (
            "도시지역편입해제구역"
        ),

        "site": (
            site
        ),

        "direct_hit_count": (
            len(
                direct_results
            )
        ),

        "gaepo12_match_count": (
            gaepo12_count
        ),

        "direct_target_event_count": (
            direct_target_event_count
        ),

        "assessment": (
            assessment
        ),

        "reason": (
            reason
        ),

        "direct_hits": (
            direct_results
        ),

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "직접 일치 결정고시의 실제 의미를 "
                "검증하는 단계이며 적용 Parcel/geometry "
                "확정 전"
            ),
        },

        "next_step": (
            "직접 일치 고시가 target history이면 "
            "고시 적용 필지/지형도면 검증, "
            "아니면 도시지역편입해제구역 후보에서 제외"
        ),
    }

    save_json(
        result
    )

    # ========================================================
    # 초간략 콘솔
    # ========================================================

    print(
        "Direct hits:",
        len(
            direct_results
        ),
    )

    print(
        "Gaepo 12 match:",
        gaepo12_count,
    )

    print(
        "Target history hits:",
        direct_target_event_count,
    )

    for index, item in enumerate(
        direct_results,
        start=1,
    ):

        print()

        print(
            f"[{index}]"
        )

        print(
            "Date:",
            safe_string(
                item.get(
                    "ANCMNT_YMD"
                )
            ),
        )

        print(
            "Notice:",
            safe_string(
                item.get(
                    "ANCMNT_NO"
                )
            ),
        )

        print(
            "Title:",
            safe_string(
                item.get(
                    "TTL"
                )
            ),
        )

        print(
            "Address match:",
            item.get(
                "exact_address_match"
            ),
        )

        print(
            "PNU match:",
            item.get(
                "pnu_match"
            ),
        )

        print(
            "Gaepo12:",
            item.get(
                "gaepo_12_match"
            ),
        )

        print(
            "Target events:",
            item.get(
                "matched_target_events"
            ),
        )

        # 내용은 300자까지만
        content = safe_string(
            item.get(
                "CN"
            )
        )

        print(
            "Content:",
            (
                content[:300]
                + (
                    "..."
                    if len(
                        content
                    )
                    > 300
                    else ""
                )
            ),
        )

    print()

    print(
        "Assessment:",
        assessment,
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