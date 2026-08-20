# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-13A
서울 개발밀도관리구역 공식 지정 / 공간 source probe

목표
======================================================================
1. 토지이음 SITE 페이지를 정상 조회한다.
2. 개발밀도관리구역 명칭 출현 여부만 진단한다.
3. MapPlan analysis 전체 layer/code를 저장한다.
4. 개발밀도관리구역의 공식 code는 추측하지 않는다.
5. 서울시 공식 지정 evidence가 없으면 UNKNOWN 유지한다.
6. 콘솔에는 핵심 결과만 출력한다.

주의
======================================================================
- 문자열 출현 != SITE 포함
- MapPlan 임의 code 추정 금지
- HTTP 실패 != FALSE
- geometry/code 미확정 -> UNKNOWN
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import requests


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-13A "
    "서울 개발밀도관리구역 공식 지정 / 공간 source probe"
)


# ============================================================
# 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR
    / "site_spatial_query_context.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "seoul_development_density_management_area_probe.json"
)


# ============================================================
# 토지이음
# ============================================================

EUM_MAP_URL = (
    "https://www.eum.go.kr/web/mp/mpMapDet.jsp"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": (
        "ko-KR,ko;q=0.9"
    ),
}

TARGET_NAME = (
    "개발밀도관리구역"
)


# ============================================================
# 공통
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
        )


def load_site() -> Dict[str, str]:

    with QUERY_CONTEXT_PATH.open(
        "r",
        encoding="utf-8",
    ) as f:

        data = json.load(f)

    context = data.get(
        "query_context",
        {},
    )

    return {
        "site_id": str(
            context.get(
                "site_id",
                "",
            )
        ),
        "address": str(
            context.get(
                "address",
                "",
            )
        ),
        "pnu": str(
            context.get(
                "pnu",
                "",
            )
        ),
    }


def extract_mapplan_server(
    html: str,
) -> str | None:

    matches = re.findall(
        (
            r"https://www\\.eum\\.ne\\.kr:"
            r"\\d+/MapPlan"
        ),
        html,
    )

    if not matches:
        return None

    return matches[0]


def extract_versions(
    html: str,
) -> List[str]:

    versions = sorted(
        set(
            re.findall(
                r"\\b20\\d{6}\\b",
                html,
            )
        ),
        reverse=True,
    )

    return versions


def parse_analysis(
    payload: Dict[str, Any],
) -> List[Dict[str, Any]]:

    result = []

    layers = payload.get(
        "layer",
        [],
    )

    if not isinstance(
        layers,
        list,
    ):
        return result

    for layer in layers:

        if not isinstance(
            layer,
            dict,
        ):
            continue

        layer_name = str(
            layer.get(
                "name",
                "",
            )
        ).upper()

        for item in layer.get(
            "codes",
            [],
        ):

            if not isinstance(
                item,
                dict,
            ):
                continue

            result.append(
                {
                    "layer": layer_name,
                    "code": str(
                        item.get(
                            "code",
                            "",
                        )
                    ).upper(),
                    "area": item.get(
                        "area"
                    ),
                }
            )

    return result


# ============================================================
# main
# ============================================================

def main() -> int:

    site = load_site()

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    # --------------------------------------------------------
    # 1. SITE 토지이음
    # --------------------------------------------------------

    try:

        response = session.get(
            EUM_MAP_URL,
            params={
                "add": "land",
                "pnu": site[
                    "pnu"
                ],
            },
            timeout=30,
        )

    except Exception as exc:

        save_json(
            {
                "step": STEP_NAME,
                "site": site,
                "resolution": {
                    "query_status": (
                        "QUERY_FAILED"
                    ),
                    "resolution": (
                        "UNKNOWN"
                    ),
                    "confidence": (
                        "NONE"
                    ),
                    "reason": str(
                        exc
                    ),
                },
            }
        )

        print(
            "EUM: FAIL"
        )

        print(
            "resolution: UNKNOWN"
        )

        return 0

    html = response.text

    name_present = (
        TARGET_NAME
        in html
    )

    server = (
        extract_mapplan_server(
            html
        )
    )

    versions = (
        extract_versions(
            html
        )
    )

    selected_version = (
        versions[0]
        if versions
        else None
    )

    analysis_http = None
    analysis_entries = []
    analysis_error = None

    # --------------------------------------------------------
    # 2. MapPlan analysis
    # --------------------------------------------------------

    if (
        response.status_code
        == 200
        and server
        and selected_version
    ):

        endpoint = (
            server.rstrip("/")
            + "/MapPlan"
        )

        try:

            analysis_response = (
                session.get(
                    endpoint,
                    params={
                        "req": (
                            "analysis"
                        ),
                        "version": (
                            selected_version
                        ),
                        "pnus": (
                            site["pnu"]
                        ),
                    },
                    headers={
                        **HEADERS,
                        "Accept": (
                            "application/json,"
                            "text/javascript,"
                            "*/*;q=0.01"
                        ),
                        "Referer": (
                            EUM_MAP_URL
                        ),
                        "X-Requested-With": (
                            "XMLHttpRequest"
                        ),
                    },
                    timeout=30,
                )
            )

            analysis_http = (
                analysis_response.status_code
            )

            if (
                analysis_http
                == 200
            ):

                payload = (
                    analysis_response.json()
                )

                analysis_entries = (
                    parse_analysis(
                        payload
                    )
                )

        except Exception as exc:

            analysis_error = str(
                exc
            )

    # --------------------------------------------------------
    # 판정
    # --------------------------------------------------------

    resolution = {
        "query_status": (
            "QUERY_SUCCESS"
            if response.status_code == 200
            else "QUERY_FAILED"
        ),
        "resolution": (
            "UNKNOWN"
        ),
        "confidence": (
            "NONE"
        ),
        "reason": (
            "토지이음 공식 SITE 페이지 및 "
            "MapPlan code 목록을 조사했으나 "
            "개발밀도관리구역의 공식 관리코드와 "
            "Polygon geometry source를 아직 "
            "확정하지 못했으므로 UNKNOWN 유지"
        ),
    }

    result = {
        "step": STEP_NAME,

        "condition": (
            TARGET_NAME
        ),

        "site": site,

        "eum": {
            "http_status": (
                response.status_code
            ),
            "target_name_present": (
                name_present
            ),
            "mapplan_server": (
                server
            ),
            "selected_version": (
                selected_version
            ),
        },

        "mapplan_analysis": {
            "http_status": (
                analysis_http
            ),
            "entry_count": (
                len(
                    analysis_entries
                )
            ),
            "entries": (
                analysis_entries
            ),
            "error": (
                analysis_error
            ),
        },

        "resolution": (
            resolution
        ),

        "next_step": (
            "MapPlan 전체 code와 공식 지정 "
            "고시/관리코드의 의미를 대조하여 "
            "개발밀도관리구역 layer를 식별"
        ),
    }

    save_json(
        result
    )

    # --------------------------------------------------------
    # 초간략 출력
    # --------------------------------------------------------

    print(
        "EUM HTTP:",
        response.status_code,
    )

    print(
        "Name present:",
        name_present,
    )

    print(
        "MapPlan server:",
        bool(
            server
        ),
    )

    print(
        "Version:",
        selected_version,
    )

    print(
        "Analysis HTTP:",
        analysis_http,
    )

    print(
        "Analysis codes:",
        len(
            analysis_entries
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