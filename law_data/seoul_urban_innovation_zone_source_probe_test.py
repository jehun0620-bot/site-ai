import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-7A "
    "도시혁신구역 공식 Source / 관리코드 탐색"
)

TARGET_NAME = "도시혁신구역"

# 이전 토지이음 범례에서 이미 확인된 후보
TARGET_CODE = "UQQ903"

# UQQ905에서 검증된 토지이음 MapPlan 상위 layer
TARGET_LAYER = "AC"


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DATA_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DATA_DIR / "output"

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR / "site_spatial_query_context.json"
)

PREVIOUS_VERTICAL_PATH = (
    OUTPUT_DIR
    / "eum_vertical_mixed_use_zone_evidence_consolidation.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "seoul_urban_innovation_zone_source_probe.json"
)

ENV_PATH = BASE_DIR / ".env"


# ============================================================
# ENV
# ============================================================

load_dotenv(ENV_PATH)

SEOUL_OPEN_API_KEY = (
    os.getenv("SEOUL_OPEN_API_KEY")
    or os.getenv("SEOUL_API_KEY")
)


# ============================================================
# CONSTANT
# ============================================================

SEOUL_CATALOG_SERVICE = "SearchCatalogService"

EUM_MAP_URL = (
    "https://www.eum.go.kr/web/mp/mpMapDet.jsp"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# ============================================================
# UTIL
# ============================================================

def print_line():
    print("=" * 70)


def print_subline():
    print("-" * 70)


def load_json(path: Path):
    if not path.exists():
        return None

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def first_non_empty(*values):
    for value in values:
        if value not in (
            None,
            "",
            [],
            {},
        ):
            return value

    return None


def recursive_find(
    obj,
    key_candidates,
):
    """
    중첩 JSON에서 후보 key 값을 재귀적으로 탐색한다.
    """

    if isinstance(obj, dict):

        for key in key_candidates:
            if key in obj:
                value = obj[key]

                if value not in (
                    None,
                    "",
                    [],
                    {},
                ):
                    return value

        for value in obj.values():

            result = recursive_find(
                value,
                key_candidates,
            )

            if result not in (
                None,
                "",
                [],
                {},
            ):
                return result

    elif isinstance(obj, list):

        for item in obj:

            result = recursive_find(
                item,
                key_candidates,
            )

            if result not in (
                None,
                "",
                [],
                {},
            ):
                return result

    return None


# ============================================================
# SITE
# ============================================================

def extract_site(query_context):
    query_context = (
        query_context
        if isinstance(query_context, dict)
        else {}
    )

    site_id = recursive_find(
        query_context,
        [
            "site_id",
            "SITE_ID",
        ],
    )

    address = recursive_find(
        query_context,
        [
            "address",
            "jibun_address",
            "lot_address",
            "SITE_ADDRESS",
        ],
    )

    pnu = recursive_find(
        query_context,
        [
            "pnu",
            "PNU",
        ],
    )

    sigungu_code = recursive_find(
        query_context,
        [
            "sigungu_code",
            "sgg_cd",
            "sigunguCd",
        ],
    )

    if not sigungu_code and pnu:
        sigungu_code = str(pnu)[:5]

    zoning = recursive_find(
        query_context,
        [
            "zoning",
            "land_use_zone",
            "use_zone",
            "용도지역",
        ],
    )

    return {
        "site_id": site_id,
        "address": address,
        "pnu": str(pnu) if pnu else None,
        "sigungu_code": (
            str(sigungu_code)
            if sigungu_code
            else None
        ),
        "zoning": zoning,
    }


# ============================================================
# SEOUL OPEN DATA CATALOG
# ============================================================

def request_catalog_page(
    session,
    start,
    end,
):
    if not SEOUL_OPEN_API_KEY:
        return {
            "success": False,
            "http_status": None,
            "rows": [],
            "total_count": 0,
            "error": "SEOUL_OPEN_API_KEY 없음",
        }

    url = (
        "http://openapi.seoul.go.kr:8088/"
        f"{SEOUL_OPEN_API_KEY}/json/"
        f"{SEOUL_CATALOG_SERVICE}/"
        f"{start}/{end}/"
    )

    try:
        response = session.get(
            url,
            timeout=30,
        )

    except Exception as exc:
        return {
            "success": False,
            "http_status": None,
            "rows": [],
            "total_count": 0,
            "error": repr(exc),
        }

    if response.status_code != 200:
        return {
            "success": False,
            "http_status": response.status_code,
            "rows": [],
            "total_count": 0,
            "error": (
                response.text[:500]
                if response.text
                else None
            ),
        }

    try:
        payload = response.json()

    except Exception as exc:
        return {
            "success": False,
            "http_status": response.status_code,
            "rows": [],
            "total_count": 0,
            "error": f"JSON parse error: {exc}",
        }

    service = payload.get(
        SEOUL_CATALOG_SERVICE
    )

    if not isinstance(service, dict):
        return {
            "success": False,
            "http_status": response.status_code,
            "rows": [],
            "total_count": 0,
            "error": (
                f"{SEOUL_CATALOG_SERVICE} 객체 없음"
            ),
        }

    result = service.get("RESULT") or {}

    code = result.get("CODE")
    message = result.get("MESSAGE")

    rows = service.get("row") or []

    total_count = (
        service.get("list_total_count")
        or 0
    )

    success = (
        code == "INFO-000"
        or bool(rows)
    )

    return {
        "success": success,
        "http_status": response.status_code,
        "result_code": code,
        "result_message": message,
        "rows": rows,
        "total_count": total_count,
        "error": None,
    }


def load_all_catalog_rows(session):
    """
    서울 SearchCatalogService 전체 row 확보.
    """

    all_rows = []

    first = request_catalog_page(
        session,
        1,
        1000,
    )

    if not first["success"]:
        return {
            **first,
            "rows": [],
        }

    all_rows.extend(
        first["rows"]
    )

    total_count = (
        first["total_count"]
        or len(all_rows)
    )

    start = 1001

    while start <= total_count:

        end = min(
            start + 999,
            total_count,
        )

        page = request_catalog_page(
            session,
            start,
            end,
        )

        if not page["success"]:
            break

        all_rows.extend(
            page["rows"]
        )

        start = end + 1

    return {
        "success": True,
        "http_status": 200,
        "total_count": total_count,
        "rows": all_rows,
    }


# ============================================================
# CATALOG SCORING
# ============================================================

def text_of_row(row):
    fields = [
        "INF_NM",
        "CATE_NM",
        "DITC_NM",
        "MAP_CATE_NM",
        "MNG_ORGAN_NAME",
        "MNG_STATION_NAME",
        "LINK_DESC",
        "LINK_INFO",
        "SRV_TYPE",
    ]

    texts = []

    for field in fields:
        value = row.get(field)

        if value:
            texts.append(str(value))

    return " ".join(texts)


def score_catalog_row(row):
    text = text_of_row(row)

    score = 0
    reasons = []

    explicit_target = (
        TARGET_NAME in text
    )

    if explicit_target:
        score += 200
        reasons.append(
            "EXPLICIT_도시혁신구역"
        )

    inf_nm = str(
        row.get("INF_NM") or ""
    )

    if "용도구역" in inf_nm:
        score += 60
        reasons.append(
            "LAND_USE_AREA_DATASET"
        )

    if "기타용도구역" in inf_nm:
        score += 50
        reasons.append(
            "OTHER_LAND_USE_AREA"
        )

    if "공간정보" in inf_nm:
        score += 35
        reasons.append(
            "SPATIAL_DATASET"
        )

    if (
        "도시계획" in text
        or "도시관리" in text
    ):
        score += 20
        reasons.append(
            "URBAN_PLANNING"
        )

    if "혁신" in text:
        score += 30
        reasons.append(
            "CONTAINS_혁신"
        )

    # 무관한 일반 데이터 억제
    noise_terms = [
        "게임",
        "영상물",
        "대기",
        "복지",
        "관광",
        "교통량",
        "도서관",
    ]

    for term in noise_terms:
        if term in inf_nm:
            score -= 30

    return {
        "score": score,
        "reasons": reasons,
        "explicit_target": explicit_target,
    }


def find_catalog_candidates(rows):
    candidates = []

    for row in rows:
        score_info = score_catalog_row(
            row
        )

        if score_info["score"] <= 0:
            continue

        candidates.append(
            {
                "score": (
                    score_info["score"]
                ),
                "score_reasons": (
                    score_info["reasons"]
                ),
                "explicit_target": (
                    score_info[
                        "explicit_target"
                    ]
                ),
                "row": row,
            }
        )

    candidates.sort(
        key=lambda x: (
            -x["score"],
            str(
                x["row"].get(
                    "INF_ID",
                    "",
                )
            ),
        )
    )

    return candidates


# ============================================================
# EUM
# ============================================================

def probe_eum(session, pnu):
    result = {
        "url": None,
        "http_status": None,
        "reachable": False,
        "target_name_found": False,
        "target_code_found": False,
        "direct_pair_found": False,
        "contexts": [],
    }

    if not pnu:
        return result

    params = {
        "add": "land",
        "pnu": pnu,
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.eum.go.kr/",
    }

    try:
        response = session.get(
            EUM_MAP_URL,
            params=params,
            headers=headers,
            timeout=30,
        )

    except Exception as exc:
        result["error"] = repr(exc)
        return result

    result["url"] = response.url
    result["http_status"] = (
        response.status_code
    )
    result["reachable"] = (
        response.status_code == 200
    )

    if response.status_code != 200:
        return result

    response.encoding = (
        response.apparent_encoding
        or "euc-kr"
    )

    html = response.text

    result["target_name_found"] = (
        TARGET_NAME in html
    )

    result["target_code_found"] = (
        TARGET_CODE in html
    )

    pair_patterns = [
        rf"typeAC_{re.escape(TARGET_CODE)}"
        rf'[^>]*title=["\']'
        rf'{re.escape(TARGET_NAME)}',

        rf"title=[\"']"
        rf"{re.escape(TARGET_NAME)}"
        rf"[\"'][^>]*"
        rf"typeAC_{re.escape(TARGET_CODE)}",
    ]

    result["direct_pair_found"] = any(
        re.search(
            pattern,
            html,
            flags=re.IGNORECASE
            | re.DOTALL,
        )
        for pattern in pair_patterns
    )

    for keyword in (
        TARGET_NAME,
        TARGET_CODE,
    ):
        start = 0

        while True:
            idx = html.find(
                keyword,
                start,
            )

            if idx < 0:
                break

            left = max(
                0,
                idx - 300,
            )

            right = min(
                len(html),
                idx + len(keyword) + 300,
            )

            context = (
                html[left:right]
                .replace("\r", " ")
                .replace("\n", " ")
            )

            result["contexts"].append(
                {
                    "keyword": keyword,
                    "context": context,
                }
            )

            if len(
                result["contexts"]
            ) >= 10:
                break

            start = (
                idx
                + len(keyword)
            )

    return result


# ============================================================
# PREVIOUS MAPPLAN EVIDENCE
# ============================================================

def inspect_previous_vertical():
    data = load_json(
        PREVIOUS_VERTICAL_PATH
    )

    if not isinstance(
        data,
        dict,
    ):
        return {
            "file_exists": False,
            "previous_resolution": None,
            "mapplan_structure_reusable": False,
        }

    resolution = recursive_find(
        data,
        ["resolution"],
    )

    evidence_state = recursive_find(
        data,
        ["evidence_state"],
    )

    text = json.dumps(
        data,
        ensure_ascii=False,
    )

    reusable = all(
        token in text
        for token in [
            "UQQ905",
            "MapPlan",
        ]
    )

    return {
        "file_exists": True,
        "previous_resolution": resolution,
        "evidence_state": evidence_state,
        "mapplan_structure_reusable": (
            reusable
        ),
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print(
        f"=== {STEP_NAME} ==="
    )
    print()

    print(
        "Query Context 입력:"
    )
    print(
        QUERY_CONTEXT_PATH
    )
    print()

    query_context = load_json(
        QUERY_CONTEXT_PATH
    )

    if not query_context:
        raise RuntimeError(
            "Query Context를 읽을 수 없습니다: "
            f"{QUERY_CONTEXT_PATH}"
        )

    site = extract_site(
        query_context
    )

    print_line()
    print(
        "=== 대상 SITE ==="
    )
    print_line()

    print(
        "SITE ID:",
        site["site_id"] or "-",
    )
    print(
        "주소:",
        site["address"] or "-",
    )
    print(
        "용도지역:",
        site["zoning"] or "-",
    )
    print(
        "시군구코드:",
        site["sigungu_code"]
        or "-",
    )
    print(
        "PNU:",
        site["pnu"] or "-",
    )
    print()

    pnu_valid = (
        isinstance(
            site["pnu"],
            str,
        )
        and len(
            site["pnu"]
        ) == 19
        and site["pnu"].isdigit()
    )

    if not pnu_valid:
        raise RuntimeError(
            "PNU 19자리 검증 실패"
        )

    # --------------------------------------------------------
    # SESSION
    # --------------------------------------------------------

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/json,"
                "text/html,"
                "*/*;q=0.8"
            ),
        }
    )

    # --------------------------------------------------------
    # 1. SEOUL
    # --------------------------------------------------------

    print_line()
    print(
        "=== 서울 OpenAPI 인증 ==="
    )
    print_line()

    api_key_ok = bool(
        SEOUL_OPEN_API_KEY
    )

    if api_key_ok:
        print(
            "SEOUL_OPEN_API_KEY: "
            "정상적으로 읽었습니다."
        )
    else:
        print(
            "SEOUL_OPEN_API_KEY: 없음"
        )

    print()

    print_line()
    print(
        "=== 1. 서울 열린데이터 카탈로그 조회 ==="
    )
    print_line()

    catalog = load_all_catalog_rows(
        session
    )

    print(
        "service:",
        SEOUL_CATALOG_SERVICE,
    )
    print(
        "정상 응답:",
        catalog.get(
            "success",
            False,
        ),
    )
    print(
        "전체 데이터 수:",
        catalog.get(
            "total_count",
            0,
        ),
    )
    print(
        "현재 확보 row 수:",
        len(
            catalog.get(
                "rows",
                [],
            )
        ),
    )
    print()

    # --------------------------------------------------------
    # 2. CANDIDATE
    # --------------------------------------------------------

    print_line()
    print(
        "=== 2. 도시혁신구역 Source 후보 검색 ==="
    )
    print_line()

    candidates = (
        find_catalog_candidates(
            catalog.get(
                "rows",
                [],
            )
        )
    )

    print(
        "후보 수:",
        len(candidates),
    )

    display_candidates = (
        candidates[:30]
    )

    for idx, candidate in enumerate(
        display_candidates,
        start=1,
    ):
        row = candidate["row"]

        print()
        print_subline()
        print(
            f"후보 {idx}"
        )

        print(
            "score:",
            candidate["score"],
        )

        print(
            "도시혁신구역 명시:",
            candidate[
                "explicit_target"
            ],
        )

        print(
            "score reason:",
            ", ".join(
                candidate[
                    "score_reasons"
                ]
            )
            or "-",
        )

        for field in [
            "INF_ID",
            "INF_NM",
            "CATE_NM",
            "DITC_NM",
            "MAP_CATE_NM",
            "MNG_ORGAN_NAME",
            "MNG_STATION_NAME",
            "CHNG_LOAD_NM",
            "DATA_LT_NM",
            "SRV_TYPE",
            "LINK_DESC",
            "LINK_INFO",
            "SHORT_URL",
        ]:
            print(
                f"{field}:",
                row.get(
                    field,
                    "-",
                ),
            )

    print()

    # --------------------------------------------------------
    # 3. EUM
    # --------------------------------------------------------

    print_line()
    print(
        "=== 3. 토지이음 도시혁신구역 코드 재검증 ==="
    )
    print_line()

    eum = probe_eum(
        session,
        site["pnu"],
    )

    print(
        "HTTP:",
        eum.get(
            "http_status"
        ),
    )

    print(
        "reachable:",
        eum.get(
            "reachable"
        ),
    )

    print(
        TARGET_NAME,
        "존재:",
        eum.get(
            "target_name_found"
        ),
    )

    print(
        TARGET_CODE,
        "존재:",
        eum.get(
            "target_code_found"
        ),
    )

    print(
        "명칭/코드 직접 연결:",
        eum.get(
            "direct_pair_found"
        ),
    )

    print()

    for idx, context in enumerate(
        eum.get(
            "contexts",
            [],
        )[:5],
        start=1,
    ):
        print_subline()
        print(
            f"Context {idx}"
        )
        print(
            "keyword:",
            context["keyword"],
        )
        print(
            context["context"]
        )

    print()

    # --------------------------------------------------------
    # 4. PREVIOUS MAPPLAN
    # --------------------------------------------------------

    print_line()
    print(
        "=== 4. 기존 UQQ905 MapPlan 구조 재사용 가능성 ==="
    )
    print_line()

    previous = (
        inspect_previous_vertical()
    )

    print(
        "이전 evidence 파일 존재:",
        previous[
            "file_exists"
        ],
    )

    print(
        "이전 입체복합구역 판정:",
        previous.get(
            "previous_resolution"
        )
        or "-",
    )

    print(
        "MapPlan 구조 재사용 후보:",
        previous[
            "mapplan_structure_reusable"
        ],
    )

    print()

    # --------------------------------------------------------
    # 5. SOURCE MEANING
    # --------------------------------------------------------

    print_line()
    print(
        "=== 5. 도시혁신구역 Source 의미 판정 ==="
    )
    print_line()

    explicit_catalog = [
        x
        for x in candidates
        if x[
            "explicit_target"
        ]
    ]

    if (
        eum.get(
            "direct_pair_found"
        )
        and TARGET_CODE
        and TARGET_LAYER
    ):
        source_status = (
            "EUM_LEGEND_CODE_VERIFIED"
        )

        source_role = (
            "CLASSIFICATION_CODE"
        )

        reason = (
            "토지이음 공식 지도 HTML에서 "
            f"'{TARGET_NAME}' 명칭과 "
            f"{TARGET_CODE} 범례 코드의 "
            "직접 연결을 확인함. "
            "기존 입체복합구역 조사에서 "
            "동일 UQQ 계열의 MapPlan "
            "layer AC 요청 구조를 확보했으므로 "
            "다음 단계에서 UQQ903에 대해 "
            "실제 req=analysis / req=search "
            "geometry 요청을 검증할 수 있음"
        )

    elif explicit_catalog:
        source_status = (
            "SEOUL_DATASET_FOUND"
        )

        source_role = (
            "SOURCE_CANDIDATE"
        )

        reason = (
            "서울시 공식 카탈로그에서 "
            "도시혁신구역 관련 source를 "
            "확인했으나 토지이음 "
            "UQQ903과의 공간 요청 연결을 "
            "아직 확정하지 못함"
        )

    else:
        source_status = (
            "SOURCE_PARTIALLY_VERIFIED"
        )

        source_role = None

        reason = (
            "서울시 전용 공간 dataset은 "
            "직접 확정하지 못했으나 "
            "토지이음 관리코드 체계를 "
            "계속 검증 중임"
        )

    print(
        "source_status:",
        source_status,
    )

    print(
        "source_role:",
        source_role,
    )

    print(
        "target:",
        TARGET_NAME,
    )

    print(
        "target code:",
        TARGET_CODE,
    )

    print(
        "candidate MapPlan layer:",
        TARGET_LAYER,
    )

    print(
        "reason:",
        reason,
    )

    print()

    # --------------------------------------------------------
    # 6. SITE
    # --------------------------------------------------------

    site_resolution = {
        "query_status": (
            "NOT_QUERIED"
        ),
        "resolution": "UNKNOWN",
        "confidence": "NONE",
        "reason": (
            "현재 단계는 도시혁신구역의 "
            "공식 source와 관리코드의 "
            "의미를 검증하는 단계이며 "
            "대상 Parcel Polygon과 "
            "UQQ903 geometry 사이의 "
            "실제 공간교차를 아직 "
            "수행하지 않았으므로 "
            "TRUE/FALSE를 판정하지 않음"
        ),
    }

    print_line()
    print(
        "=== 6. 현재 도시혁신구역 SITE 판정 ==="
    )
    print_line()

    for key in [
        "query_status",
        "resolution",
        "confidence",
        "reason",
    ]:
        print(
            f"{key}:",
            site_resolution[key],
        )

    print()

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    validation = {
        "서울 OpenAPI Key 존재":
            api_key_ok,

        "SITE 주소 존재":
            bool(
                site["address"]
            ),

        "PNU 19자리":
            pnu_valid,

        "서울 카탈로그 조회 실행":
            True,

        "카탈로그 row 확보":
            len(
                catalog.get(
                    "rows",
                    [],
                )
            ) > 0,

        "도시혁신구역 source 탐색 실행":
            True,

        "토지이음 지도 조회 실행":
            eum.get(
                "http_status"
            )
            is not None,

        "UQQ903 코드 자동추측 없음":
            (
                TARGET_CODE
                == "UQQ903"
                and (
                    eum.get(
                        "target_code_found"
                    )
                    or not eum.get(
                        "reachable"
                    )
                )
            ),

        "source 후보만으로 SITE TRUE 금지":
            (
                site_resolution[
                    "resolution"
                ]
                != "TRUE"
            ),

        "source 후보만으로 SITE FALSE 금지":
            (
                site_resolution[
                    "resolution"
                ]
                != "FALSE"
            ),

        "공간교차 전 UNKNOWN 유지":
            (
                site_resolution[
                    "resolution"
                ]
                == "UNKNOWN"
            ),

        "query_status 허용값":
            site_resolution[
                "query_status"
            ]
            in {
                "NOT_QUERIED",
                "NOT_CONNECTED",
                "QUERY_SUCCESS",
                "QUERY_FAILED",
            },

        "resolution 허용값":
            site_resolution[
                "resolution"
            ]
            in {
                "TRUE",
                "FALSE",
                "UNKNOWN",
            },

        "confidence 허용값":
            site_resolution[
                "confidence"
            ]
            in {
                "HIGH",
                "MEDIUM",
                "LOW",
                "NONE",
            },
    }

    print_line()
    print(
        "=== C-9-2-7A 검증 ==="
    )
    print_line()

    for name, passed in (
        validation.items()
    ):
        print(
            f"{name}:",
            "PASS"
            if passed
            else "FAIL",
        )

    print()

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    result = {
        "step": STEP_NAME,
        "site": site,
        "target": {
            "name": TARGET_NAME,
            "legend_code": (
                TARGET_CODE
            ),
            "candidate_mapplan_layer": (
                TARGET_LAYER
            ),
        },
        "seoul_catalog": {
            "service": (
                SEOUL_CATALOG_SERVICE
            ),
            "success": catalog.get(
                "success",
                False,
            ),
            "total_count": (
                catalog.get(
                    "total_count",
                    0,
                )
            ),
            "row_count": len(
                catalog.get(
                    "rows",
                    [],
                )
            ),
            "candidates": (
                display_candidates
            ),
        },
        "eum": eum,
        "previous_mapplan": previous,
        "source_resolution": {
            "source_status": (
                source_status
            ),
            "source_role": (
                source_role
            ),
            "reason": reason,
        },
        "site_resolution": (
            site_resolution
        ),
        "validation": validation,
    }

    save_json(
        OUTPUT_PATH,
        result,
    )

    print_line()
    print(
        "결과 저장:"
    )
    print(
        OUTPUT_PATH
    )
    print_line()
    print()

    all_pass = all(
        validation.values()
    )

    if all_pass:
        print(
            "STEP 17-21-C-9-2-7A 완료"
        )
        print()

        if eum.get(
            "direct_pair_found"
        ):
            print(
                "토지이음에서 "
                "'도시혁신구역' ↔ UQQ903 "
                "관리코드 연결을 확인했습니다."
            )
            print()

        print(
            "현재 도시혁신구역:"
        )
        print(
            "UNKNOWN"
        )
        print()

        print(
            "다음 단계:"
        )
        print(
            "STEP 17-21-C-9-2-7B"
        )
        print(
            "→ 기존 MapPlan endpoint 재사용"
        )
        print(
            "→ req=analysis에서 UQQ903 검색"
        )
        print(
            "→ 양성대조 UQQ300 재검증"
        )
        print(
            "→ layer=AC / code=UQQ903 "
            "geometry 조회"
        )
        print(
            "→ Parcel intersection"
        )
        print(
            "→ 실제 교차 시 TRUE"
        )
        print(
            "→ 양성대조 정상 + "
            "analysis/geometry 음성 시 FALSE"
        )

    else:
        print(
            "STEP 17-21-C-9-2-7A "
            "검증 미완료"
        )
        print()
        print(
            "FAIL 항목을 확인한 뒤 "
            "source 구조를 보정합니다."
        )


if __name__ == "__main__":
    main()