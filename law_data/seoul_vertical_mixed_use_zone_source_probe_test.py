import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-6A "
    "입체복합구역 서울시 공식 Source 탐색 / 의미 검증"
)

TARGET_KEYWORD = "입체복합구역"


# ============================================================
# 프로젝트 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DATA_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DATA_DIR / "output"

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR / "site_spatial_query_context.json"
)

SOURCE_SNAPSHOT_PATH = (
    OUTPUT_DIR / "site_spatial_source_snapshot.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR / "seoul_vertical_mixed_use_zone_source_probe.json"
)

ENV_PATH = BASE_DIR / ".env"


# ============================================================
# 환경변수
# ============================================================

load_dotenv(ENV_PATH)

SEOUL_OPEN_API_KEY = os.getenv("SEOUL_OPEN_API_KEY")


# ============================================================
# 서울 열린데이터 API
# ============================================================

SEOUL_API_BASE = "http://openapi.seoul.go.kr:8088"

CATALOG_SERVICE = "SearchCatalogService"

CATALOG_PAGE_SIZE = 1000


# ============================================================
# 출력 함수
# ============================================================

def print_separator(char: str = "=") -> None:
    print(char * 70)


def print_title(title: str) -> None:
    print()
    print_separator("=")
    print(f"=== {title} ===")
    print_separator("=")


# ============================================================
# JSON
# ============================================================

def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"파일을 찾을 수 없습니다: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(
    path: Path,
    data: Dict[str, Any],
) -> None:

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


# ============================================================
# 값 탐색
# ============================================================

def recursive_find(
    obj: Any,
    keys: List[str],
) -> Optional[Any]:

    if isinstance(obj, dict):

        for key in keys:
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
            found = recursive_find(
                value,
                keys,
            )

            if found not in (
                None,
                "",
                [],
                {},
            ):
                return found

    elif isinstance(obj, list):

        for item in obj:
            found = recursive_find(
                item,
                keys,
            )

            if found not in (
                None,
                "",
                [],
                {},
            ):
                return found

    return None


# ============================================================
# SITE 정보
# ============================================================

def extract_site(
    context: Dict[str, Any],
) -> Dict[str, Any]:

    site_id = recursive_find(
        context,
        [
            "site_id",
            "SITE_ID",
        ],
    )

    address = recursive_find(
        context,
        [
            "address",
            "jibun_address",
            "site_address",
        ],
    )

    pnu = recursive_find(
        context,
        [
            "pnu",
            "PNU",
        ],
    )

    sigungu_code = recursive_find(
        context,
        [
            "sigungu_code",
            "sgg_cd",
            "SIGUNGU_CD",
        ],
    )

    zoning = recursive_find(
        context,
        [
            "zoning",
            "zone_name",
            "land_use_zone",
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
# 서울 카탈로그 API
# ============================================================

def request_catalog_page(
    start: int,
    end: int,
) -> Dict[str, Any]:

    url = (
        f"{SEOUL_API_BASE}/"
        f"{SEOUL_OPEN_API_KEY}/"
        f"json/"
        f"{CATALOG_SERVICE}/"
        f"{start}/"
        f"{end}/"
    )

    response = requests.get(
        url,
        timeout=30,
    )

    result: Dict[str, Any] = {
        "http_status": response.status_code,
        "url_without_key": (
            f"{SEOUL_API_BASE}/"
            f"[HIDDEN]/json/"
            f"{CATALOG_SERVICE}/"
            f"{start}/{end}/"
        ),
        "success": False,
        "rows": [],
        "total_count": 0,
        "result_code": None,
        "result_message": None,
    }

    if response.status_code != 200:
        return result

    try:
        payload = response.json()

    except Exception as exc:

        result["error"] = (
            f"JSON parsing failed: {exc}"
        )

        return result

    service = payload.get(
        CATALOG_SERVICE,
        {},
    )

    if not isinstance(
        service,
        dict,
    ):
        return result

    result_info = service.get(
        "RESULT",
        {},
    )

    if isinstance(
        result_info,
        dict,
    ):
        result["result_code"] = (
            result_info.get("CODE")
        )

        result["result_message"] = (
            result_info.get("MESSAGE")
        )

    rows = service.get(
        "row",
        [],
    )

    if not isinstance(
        rows,
        list,
    ):
        rows = []

    result["rows"] = rows

    result["total_count"] = (
        service.get(
            "list_total_count",
            0,
        )
        or 0
    )

    result["success"] = (
        result["result_code"] == "INFO-000"
    )

    return result


def fetch_all_catalog_rows() -> Dict[str, Any]:

    all_rows: List[Dict[str, Any]] = []

    first = request_catalog_page(
        1,
        CATALOG_PAGE_SIZE,
    )

    if not first["success"]:
        return {
            "success": False,
            "rows": [],
            "total_count": 0,
            "first_response": first,
        }

    all_rows.extend(
        first["rows"]
    )

    total_count = int(
        first["total_count"]
    )

    start = (
        CATALOG_PAGE_SIZE + 1
    )

    while start <= total_count:

        end = min(
            start
            + CATALOG_PAGE_SIZE
            - 1,
            total_count,
        )

        page = request_catalog_page(
            start,
            end,
        )

        if not page["success"]:
            return {
                "success": False,
                "rows": all_rows,
                "total_count": total_count,
                "failed_page": {
                    "start": start,
                    "end": end,
                    "response": page,
                },
            }

        all_rows.extend(
            page["rows"]
        )

        start = end + 1

    return {
        "success": True,
        "rows": all_rows,
        "total_count": total_count,
        "first_response": first,
    }


# ============================================================
# Catalog 검색
# ============================================================

SEARCH_FIELDS = [
    "INF_NM",
    "INF_ID",
    "CATE_NM",
    "DITC_NM",
    "MAP_CATE_NM",
    "MNG_ORGAN_NAME",
    "MNG_STATION_NAME",
    "LINK_DESC",
    "LINK_INFO",
]


def normalize_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


def row_search_text(
    row: Dict[str, Any],
) -> str:

    values = []

    for field in SEARCH_FIELDS:
        values.append(
            normalize_text(
                row.get(field)
            )
        )

    return " ".join(values)


def score_catalog_row(
    row: Dict[str, Any],
) -> Dict[str, Any]:

    inf_nm = normalize_text(
        row.get("INF_NM")
    )

    text = row_search_text(row)

    score = 0
    reasons = []

    exact_keyword = (
        TARGET_KEYWORD in text
    )

    exact_name = (
        TARGET_KEYWORD in inf_nm
    )

    if exact_name:
        score += 200
        reasons.append(
            "INF_NM_EXACT_KEYWORD"
        )

    elif exact_keyword:
        score += 150
        reasons.append(
            "ROW_EXACT_KEYWORD"
        )

    # 입체 관련 후보
    if "입체" in text:
        score += 50
        reasons.append(
            "CONTAINS_입체"
        )

    if "복합" in text:
        score += 40
        reasons.append(
            "CONTAINS_복합"
        )

    # 용도구역 / 용도지구 / 도시계획 후보
    if "용도구역" in inf_nm:
        score += 35
        reasons.append(
            "LAND_USE_AREA_DATASET"
        )

    if "용도지구" in inf_nm:
        score += 30
        reasons.append(
            "LAND_USE_DISTRICT_DATASET"
        )

    if "도시계획" in text:
        score += 15
        reasons.append(
            "URBAN_PLANNING"
        )

    if "공간정보" in inf_nm:
        score += 10
        reasons.append(
            "SPATIAL_DATASET"
        )

    return {
        "score": score,
        "reasons": reasons,
        "exact_keyword": exact_keyword,
        "exact_name": exact_name,
    }


def search_catalog_candidates(
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    candidates = []

    for row in rows:

        scored = score_catalog_row(
            row
        )

        if scored["score"] <= 0:
            continue

        candidates.append(
            {
                "score": scored["score"],
                "reasons": scored["reasons"],
                "exact_keyword": (
                    scored["exact_keyword"]
                ),
                "exact_name": (
                    scored["exact_name"]
                ),
                "row": row,
            }
        )

    candidates.sort(
        key=lambda item: (
            item["score"],
            item["exact_name"],
            item["exact_keyword"],
        ),
        reverse=True,
    )

    return candidates


# ============================================================
# 후보 출력
# ============================================================

DISPLAY_FIELDS = [
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
]


def print_candidate(
    index: int,
    candidate: Dict[str, Any],
) -> None:

    row = candidate["row"]

    print()
    print_separator("-")

    print(f"후보 {index}")
    print(
        f"score: "
        f"{candidate['score']}"
    )

    print(
        "입체복합구역 명시: "
        f"{candidate['exact_keyword']}"
    )

    print(
        "score reason: "
        + ", ".join(
            candidate["reasons"]
        )
    )

    for field in DISPLAY_FIELDS:

        value = row.get(field)

        if value not in (
            None,
            "",
        ):
            print(
                f"{field}: {value}"
            )


# ============================================================
# Source 의미 판정
# ============================================================

def classify_source(
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:

    exact = [
        item
        for item in candidates
        if item["exact_keyword"]
    ]

    if exact:

        best = exact[0]

        return {
            "source_status":
                "EXACT_KEYWORD_DATASET_FOUND",
            "source_role":
                "CANDIDATE_LAYER",
            "reason": (
                "서울시 공식 열린데이터 "
                "카탈로그에서 '입체복합구역' "
                "문자열을 직접 포함하는 "
                "dataset 후보를 확인함. "
                "다만 catalog 명칭만으로 "
                "해당 dataset의 모든 Feature를 "
                "입체복합구역으로 간주하지 않고 "
                "OpenAPI/SHP 실제 schema와 "
                "Feature 분류값을 추가 검증해야 함"
            ),
            "selected_catalog":
                best["row"],
        }

    # 입체 + 공간정보 후보
    spatial_candidates = []

    for item in candidates:

        row = item["row"]

        name = normalize_text(
            row.get("INF_NM")
        )

        text = row_search_text(row)

        if (
            "입체" in text
            and "공간정보" in name
        ):
            spatial_candidates.append(
                item
            )

    if spatial_candidates:

        best = spatial_candidates[0]

        return {
            "source_status":
                "RELATED_SPATIAL_DATASET_FOUND",
            "source_role":
                "PARENT_OR_RELATED_LAYER",
            "reason": (
                "서울시 공식 카탈로그에서 "
                "입체 관련 공간정보 dataset "
                "후보를 확인했으나 "
                "'입체복합구역' 전용 layer인지 "
                "아직 확정할 수 없음"
            ),
            "selected_catalog":
                best["row"],
        }

    return {
        "source_status":
            "SOURCE_NOT_CONFIRMED",
        "source_role":
            None,
        "reason": (
            "서울시 공식 열린데이터 "
            "카탈로그에서 입체복합구역 "
            "전용 공간정보 source를 "
            "직접 확정하지 못함. "
            "이 결과만으로 SITE를 "
            "FALSE로 판정하지 않음"
        ),
        "selected_catalog":
            None,
    }


# ============================================================
# SITE 판정
# ============================================================

def build_site_resolution(
    source_result: Dict[str, Any],
) -> Dict[str, Any]:

    status = source_result[
        "source_status"
    ]

    if status in (
        "EXACT_KEYWORD_DATASET_FOUND",
        "RELATED_SPATIAL_DATASET_FOUND",
    ):

        reason = (
            "입체복합구역 판정을 위한 "
            "공식 공간정보 source 후보는 "
            "확인했으나 대상 Parcel Polygon과 "
            "입체복합구역 Polygon의 실제 "
            "공간교차를 아직 수행하지 않았으므로 "
            "TRUE/FALSE를 확정하지 않음"
        )

    else:

        reason = (
            "입체복합구역의 공식 공간 geometry "
            "source를 아직 확정하지 못했으므로 "
            "대상 필지를 TRUE/FALSE로 "
            "판정하지 않고 UNKNOWN으로 유지함"
        )

    return {
        "query_status":
            "NOT_QUERIED",
        "resolution":
            "UNKNOWN",
        "confidence":
            "NONE",
        "reason":
            reason,
    }


# ============================================================
# 검증
# ============================================================

def run_checks(
    site: Dict[str, Any],
    catalog_result: Dict[str, Any],
    source_result: Dict[str, Any],
    site_resolution: Dict[str, Any],
) -> Dict[str, bool]:

    pnu = site.get("pnu")

    checks = {
        "서울 OpenAPI Key 존재":
            bool(SEOUL_OPEN_API_KEY),

        "SITE 주소 존재":
            bool(site.get("address")),

        "PNU 19자리":
            bool(
                pnu
                and len(pnu) == 19
                and pnu.isdigit()
            ),

        "서울 카탈로그 조회 실행":
            bool(
                catalog_result
                is not None
            ),

        "카탈로그 row 확보":
            bool(
                catalog_result.get(
                    "rows"
                )
            ),

        "입체복합구역 source 탐색 실행":
            source_result.get(
                "source_status"
            )
            is not None,

        "source 후보만으로 SITE TRUE 금지":
            site_resolution[
                "resolution"
            ] != "TRUE",

        "source 후보만으로 SITE FALSE 금지":
            site_resolution[
                "resolution"
            ] != "FALSE",

        "공간교차 전 UNKNOWN 유지":
            site_resolution[
                "resolution"
            ] == "UNKNOWN",

        "query_status 허용값":
            site_resolution[
                "query_status"
            ]
            in {
                "NOT_CONNECTED",
                "NOT_QUERIED",
                "QUERY_FAILED",
                "QUERY_SUCCESS",
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
                "NONE",
                "MEDIUM",
                "HIGH",
            },
    }

    return checks


# ============================================================
# main
# ============================================================

def main() -> int:

    print(
        f"=== {STEP_NAME} ==="
    )

    print()
    print("Query Context 입력:")
    print(QUERY_CONTEXT_PATH)

    print()
    print("Source Registry 입력:")
    print(SOURCE_SNAPSHOT_PATH)

    # --------------------------------------------------------
    # 입력
    # --------------------------------------------------------

    try:
        context = load_json(
            QUERY_CONTEXT_PATH
        )

    except Exception as exc:

        print()
        print(
            f"ERROR: Query Context 로드 실패: "
            f"{exc}"
        )

        return 1

    # Source snapshot은 참고용.
    # 없어도 공식 catalog 탐색은 계속한다.

    source_snapshot = None

    if SOURCE_SNAPSHOT_PATH.exists():

        try:
            source_snapshot = load_json(
                SOURCE_SNAPSHOT_PATH
            )

        except Exception:
            source_snapshot = None

    site = extract_site(
        context
    )

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    print_title(
        "대상 SITE"
    )

    print(
        "SITE ID:",
        site.get("site_id") or "-",
    )

    print(
        "주소:",
        site.get("address") or "-",
    )

    print(
        "용도지역:",
        site.get("zoning") or "-",
    )

    print(
        "시군구코드:",
        site.get("sigungu_code") or "-",
    )

    print(
        "PNU:",
        site.get("pnu") or "-",
    )

    # --------------------------------------------------------
    # API Key
    # --------------------------------------------------------

    print_title(
        "서울 OpenAPI 인증"
    )

    if SEOUL_OPEN_API_KEY:

        print(
            "SEOUL_OPEN_API_KEY: "
            "정상적으로 읽었습니다."
        )

    else:

        print(
            "SEOUL_OPEN_API_KEY: 없음"
        )

        return 1

    # --------------------------------------------------------
    # Catalog
    # --------------------------------------------------------

    print_title(
        "1. 서울 열린데이터 카탈로그 조회"
    )

    catalog_result = (
        fetch_all_catalog_rows()
    )

    print(
        f"service: "
        f"{CATALOG_SERVICE}"
    )

    print(
        "정상 응답:",
        catalog_result.get(
            "success",
            False,
        ),
    )

    print(
        "전체 데이터 수:",
        catalog_result.get(
            "total_count",
            0,
        ),
    )

    rows = catalog_result.get(
        "rows",
        [],
    )

    print(
        "현재 확보 row 수:",
        len(rows),
    )

    if not catalog_result.get(
        "success"
    ):

        print()
        print(
            "서울 카탈로그 조회 실패"
        )

        return 1

    # --------------------------------------------------------
    # 후보 검색
    # --------------------------------------------------------

    print_title(
        "2. 입체복합구역 Source 후보 검색"
    )

    candidates = (
        search_catalog_candidates(
            rows
        )
    )

    print(
        "후보 수:",
        len(candidates),
    )

    # 너무 많은 후보를 모두 출력하지 않는다.
    top_candidates = candidates[:30]

    for index, candidate in enumerate(
        top_candidates,
        start=1,
    ):
        print_candidate(
            index,
            candidate,
        )

    # --------------------------------------------------------
    # 의미 판정
    # --------------------------------------------------------

    print_title(
        "3. 입체복합구역 Source 의미 판정"
    )

    source_result = classify_source(
        candidates
    )

    print(
        "source_status:",
        source_result.get(
            "source_status"
        ),
    )

    print(
        "source_role:",
        source_result.get(
            "source_role"
        ),
    )

    print(
        "reason:",
        source_result.get(
            "reason"
        ),
    )

    selected = source_result.get(
        "selected_catalog"
    )

    if selected:

        print()
        print("선택 catalog:")

        for field in DISPLAY_FIELDS:

            value = selected.get(
                field
            )

            if value not in (
                None,
                "",
            ):
                print(
                    f"{field}: {value}"
                )

    # --------------------------------------------------------
    # SITE 판정
    # --------------------------------------------------------

    print_title(
        "4. 현재 입체복합구역 SITE 판정"
    )

    site_resolution = (
        build_site_resolution(
            source_result
        )
    )

    print(
        "query_status:",
        site_resolution[
            "query_status"
        ],
    )

    print(
        "resolution:",
        site_resolution[
            "resolution"
        ],
    )

    print(
        "confidence:",
        site_resolution[
            "confidence"
        ],
    )

    print(
        "reason:",
        site_resolution[
            "reason"
        ],
    )

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    print_title(
        "C-9-2-6A 검증"
    )

    checks = run_checks(
        site=site,
        catalog_result=catalog_result,
        source_result=source_result,
        site_resolution=site_resolution,
    )

    all_pass = True

    for name, passed in checks.items():

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"{name}: {status}"
        )

        if not passed:
            all_pass = False

    # --------------------------------------------------------
    # 저장
    # --------------------------------------------------------

    output = {
        "step": STEP_NAME,

        "site": site,

        "source_snapshot_loaded":
            source_snapshot is not None,

        "catalog": {
            "service":
                CATALOG_SERVICE,

            "success":
                catalog_result.get(
                    "success"
                ),

            "total_count":
                catalog_result.get(
                    "total_count"
                ),

            "row_count":
                len(rows),
        },

        "candidate_count":
            len(candidates),

        "top_candidates": [
            {
                "score":
                    item["score"],

                "reasons":
                    item["reasons"],

                "exact_keyword":
                    item[
                        "exact_keyword"
                    ],

                "exact_name":
                    item[
                        "exact_name"
                    ],

                "catalog":
                    item["row"],
            }
            for item in top_candidates
        ],

        "source_result":
            source_result,

        "site_resolution":
            site_resolution,

        "checks":
            checks,

        "all_pass":
            all_pass,
    }

    save_json(
        OUTPUT_PATH,
        output,
    )

    print()
    print_separator("=")

    print("결과 저장:")
    print(OUTPUT_PATH)

    print_separator("=")

    print()

    if all_pass:

        print(
            "STEP 17-21-C-9-2-6A 완료"
        )

        print()

        if (
            source_result[
                "source_status"
            ]
            == "SOURCE_NOT_CONFIRMED"
        ):

            print(
                "서울시 공식 카탈로그에서 "
                "입체복합구역 전용 공간 source를 "
                "아직 확정하지 못했습니다."
            )

            print()
            print(
                "현재 입체복합구역:"
            )
            print("UNKNOWN")

            print()
            print("다음 단계:")
            print(
                "STEP 17-21-C-9-2-6A-1"
            )
            print(
                "→ 국가/서울 도시계획 "
                "공간정보 source 범위 확장"
            )

        else:

            print(
                "입체복합구역 관련 공식 "
                "공간정보 source 후보를 "
                "확인했습니다."
            )

            print()
            print(
                "현재 입체복합구역:"
            )
            print("UNKNOWN")

            print()
            print("다음 단계:")
            print(
                "STEP 17-21-C-9-2-6B"
            )
            print(
                "→ 후보 OpenAPI / "
                "공간파일 schema 분석"
            )
            print(
                "→ 입체복합구역 "
                "Feature 식별 규칙 확인"
            )
            print(
                "→ Parcel Polygon과 "
                "공간교차 준비"
            )

        return 0

    print(
        "STEP 17-21-C-9-2-6A "
        "검증 미완료"
    )

    return 1


if __name__ == "__main__":
    sys.exit(main())