# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-3B-5B
학교이적지 candidate resolution

핵심 확인
======================================================================
서울시 공식 upisAnnouncement 전체 DB:
- 개포동 학교이적지 strong candidate = 1건
- 서울특별시 고시 제2015-10호

공식 고시 원문:
- 학교이적지 대상 = 강남구 개포동 153번지 일대

현재 SITE:
- 강남구 개포동 12번지
- PNU 1168010300100120000

따라서:
2015-10 고시는 현재 SITE와 다른 부지.

목표
======================================================================
1. 이전 probe 결과 로드
2. strong candidate가 2015-10 1건인지 확인
3. candidate target = 개포동 153번지로 명시적 배제
4. direct SITE school history = 0 확인
5. 현재 학교이적지를 FALSE로 확정 가능한 evidence strength 평가

판정 정책
======================================================================
다음 모두 충족:

- 서울시 공식 고시 DB 43,508건 정상 전수검색
- direct school history = 0
- strong 개포동 candidate = 1
- 해당 candidate가 개포동 153번지
- 현재 SITE는 개포동 12번지
- SITE와 candidate 주소 불일치

=> 학교이적지 FALSE / HIGH

주의
======================================================================
이 판정은 현재 SITE에 대한 도시계획상 "학교이적지" 여부만 의미.
주변에 학교가 있거나 과거 학교 관련 계획이 있었다는 의미와 다름.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-3B-5B "
    "학교이적지 candidate resolution"
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

HISTORY_PATH = (
    OUTPUT_DIR
    / "school_relocation_site_history_probe.json"
)

RULE_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_density_overlay.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "school_relocation_site_candidate_resolution.json"
)


SITE = {
    "site_id": "11680-10300-0012-0000",
    "pnu": "1168010300100120000",
    "address": "서울특별시 강남구 개포동 12번지",
    "dong": "개포동",
    "bonbun": "12",
}


KNOWN_GAEPO_SCHOOL_RELOCATION = {
    "notice": "서울특별시 고시 제2015-10호",
    "notice_date": "2015-01-15",

    "target_address": (
        "서울특별시 강남구 개포동 153번지 일대"
    ),

    "target_dong": "개포동",

    "target_bonbun": "153",

    "classification": (
        "학교이적지"
    ),

    "official_context": (
        "서울특별시 도시계획조례에 의한 학교이적지로 "
        "지형도면 고시"
    ),
}


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


def safe_int(
    value: Any,
) -> int:

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return 0


def main() -> int:

    history = load_json(
        HISTORY_PATH
    )

    rules = load_json(
        RULE_PATH
    )

    # ========================================================
    # 1. previous probe
    # ========================================================

    api = history.get(
        "api",
        {},
    )

    search = history.get(
        "search",
        {},
    )

    api_success = (
        api.get(
            "query_status"
        )
        == "QUERY_SUCCESS"
        and api.get(
            "result_code"
        )
        == "INFO-000"
        and safe_int(
            api.get(
                "total_count"
            )
        )
        == safe_int(
            api.get(
                "received_rows"
            )
        )
        and safe_int(
            api.get(
                "total_count"
            )
        )
        == 43508
    )

    direct_school_history_count = safe_int(
        search.get(
            "direct_school_history_count"
        )
    )

    strong_candidate_count = safe_int(
        search.get(
            "strong_candidate_count"
        )
    )

    gaepo_history_count = safe_int(
        search.get(
            "gaepo_school_history_count"
        )
    )

    strong_candidates = search.get(
        "strong_candidates",
        [],
    )

    # ========================================================
    # 2. 2015-10 candidate 확인
    # ========================================================

    notice_2015_10_found = False

    for item in strong_candidates:

        notice_no = str(
            item.get(
                "ANCMNT_NO",
                ""
            )
        )

        title = str(
            item.get(
                "TTL",
                ""
            )
        )

        if (
            "2015-10"
            in notice_no
            or (
                "개포택지개발지구"
                in title
                and "2015"
                in str(
                    item.get(
                        "ANCMNT_YMD",
                        ""
                    )
                )
            )
        ):

            notice_2015_10_found = True
            break

    # ========================================================
    # 3. address mismatch
    # ========================================================

    candidate_same_dong = (
        SITE[
            "dong"
        ]
        ==
        KNOWN_GAEPO_SCHOOL_RELOCATION[
            "target_dong"
        ]
    )

    candidate_same_bonbun = (
        SITE[
            "bonbun"
        ]
        ==
        KNOWN_GAEPO_SCHOOL_RELOCATION[
            "target_bonbun"
        ]
    )

    candidate_matches_site = (
        candidate_same_dong
        and candidate_same_bonbun
    )

    # ========================================================
    # 4. affected clauses
    # ========================================================

    unresolved = (
        rules.get(
            "input_requirements",
            {},
        ).get(
            "unresolved_site_conditions",
            [],
        )
    )

    school_entry = next(
        (
            item
            for item
            in unresolved
            if item.get(
                "name"
            )
            == "학교이적지"
        ),
        None,
    )

    affected_clause_count = (
        safe_int(
            school_entry.get(
                "affected_clause_count"
            )
        )
        if school_entry
        else 0
    )

    # ========================================================
    # 5. resolution
    # ========================================================

    if (
        api_success
        and direct_school_history_count
        == 0
        and strong_candidate_count
        == 1
        and gaepo_history_count
        == 1
        and notice_2015_10_found
        and not candidate_matches_site
    ):

        status = (
            "FALSE"
        )

        confidence = (
            "HIGH"
        )

        reason = (
            "서울시 공식 upisAnnouncement 43,508건 전수검색에서 "
            "현재 SITE 주소/PNU와 학교이적지 또는 학교이전 이력이 "
            "결합된 직접 evidence는 0건이었다. "
            "개포동에서 확인된 유일한 strong 학교이적지 후보는 "
            "서울특별시 고시 제2015-10호이며, 공식 고시상 대상은 "
            "개포동 153번지 일대로 현재 SITE 개포동 12번지와 "
            "명확히 다른 필지다. 따라서 현재 SITE의 "
            "학교이적지 여부를 FALSE / HIGH로 판정한다."
        )

    else:

        status = (
            "UNKNOWN"
        )

        confidence = (
            "NONE"
        )

        reason = (
            "학교이적지 current-state를 "
            "FALSE로 확정하기 위한 검증조건 미충족"
        )

    expected_overlay = None

    if status == "FALSE":

        expected_overlay = {
            "condition": (
                "학교이적지"
            ),

            "state": (
                "FALSE"
            ),

            "confidence": (
                "HIGH"
            ),

            "affected_clause_count": (
                affected_clause_count
            ),
        }

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "announcement DB complete": (
            api_success
        ),

        "direct school history 0": (
            direct_school_history_count
            == 0
        ),

        "strong candidate 1": (
            strong_candidate_count
            == 1
        ),

        "Gaepo school history 1": (
            gaepo_history_count
            == 1
        ),

        "2015-10 candidate found": (
            notice_2015_10_found
        ),

        "known candidate 153": (
            KNOWN_GAEPO_SCHOOL_RELOCATION[
                "target_bonbun"
            ]
            == "153"
        ),

        "SITE 12": (
            SITE[
                "bonbun"
            ]
            == "12"
        ),

        "candidate does not match SITE": (
            candidate_matches_site
            is False
        ),

        "affected clauses 7": (
            affected_clause_count
            == 7
        ),

        "학교이적지 FALSE": (
            status
            == "FALSE"
        ),

        "confidence HIGH": (
            confidence
            == "HIGH"
        ),
    }

    all_pass = all(
        validations.values()
    )

    output = {
        "step": (
            STEP_NAME
        ),

        "site": (
            SITE
        ),

        "known_gaepo_school_relocation": (
            KNOWN_GAEPO_SCHOOL_RELOCATION
        ),

        "evidence": {
            "announcement_database_complete": (
                api_success
            ),

            "direct_school_history_count": (
                direct_school_history_count
            ),

            "strong_candidate_count": (
                strong_candidate_count
            ),

            "gaepo_school_history_count": (
                gaepo_history_count
            ),

            "notice_2015_10_found": (
                notice_2015_10_found
            ),

            "candidate_matches_site": (
                candidate_matches_site
            ),
        },

        "affected_clause_count": (
            affected_clause_count
        ),

        "current_resolution": {
            "status": (
                status
            ),

            "confidence": (
                confidence
            ),

            "reason": (
                reason
            ),
        },

        "expected_overlay": (
            expected_overlay
        ),

        "validations": (
            validations
        ),

        "all_pass": (
            all_pass
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "Announcement DB:",
        (
            "OK"
            if api_success
            else "FAIL"
        ),
    )

    print(
        "Direct school history:",
        direct_school_history_count,
    )

    print(
        "Strong candidates:",
        strong_candidate_count,
    )

    print()

    print(
        "Known candidate:",
        KNOWN_GAEPO_SCHOOL_RELOCATION[
            "target_address"
        ],
    )

    print(
        "Current SITE:",
        SITE[
            "address"
        ],
    )

    print(
        "Candidate matches SITE:",
        candidate_matches_site,
    )

    print()

    print(
        "Affected clauses:",
        affected_clause_count,
    )

    print()

    print(
        "학교이적지:",
        status,
        "/",
        confidence,
    )

    print()

    print(
        "all_pass:",
        all_pass,
    )

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return (
        0
        if all_pass
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )