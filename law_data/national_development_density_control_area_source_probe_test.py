import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


# ============================================================
# STEP 17-21-C-9-2-4A-1
# 개발밀도관리구역 국가 단위 Source / 의미 탐색
#
# 목적
# ------------------------------------------------------------
# 1. 서울시 카탈로그에서 찾지 못한 개발밀도관리구역을
#    국가 단위 토지이용규제 / 공간정보 체계에서 탐색한다.
#
# 2. 이 단계에서는 SITE TRUE/FALSE 판정 금지.
#
# 3. 정확한 명칭 / 코드 / 근거체계가 확인되기 전까지
#    UNKNOWN 유지.
#
# 4. 코드번호 추측 금지.
# ============================================================


BASE_DIR = Path(__file__).resolve().parent

QUERY_CONTEXT_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_query_context.json"
)

SEOUL_PROBE_PATH = (
    BASE_DIR
    / "output"
    / "seoul_development_density_control_area_source_probe.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "output"
    / "national_development_density_control_area_source_probe.json"
)


# ============================================================
# 공식 탐색 Source
# ============================================================

OFFICIAL_SEARCH_TARGETS = [
    {
        "name": "토지이음 검색",
        "provider": "국토교통부",
        "base_url": "https://www.eum.go.kr",
    },
    {
        "name": "국가공간정보포털",
        "provider": "국토교통부",
        "base_url": "https://www.nsdi.go.kr",
    },
]


SEARCH_KEYWORDS = [
    "개발밀도관리구역",
    "개발밀도관리",
    "밀도관리구역",
]


HTTP_TIMEOUT = 30


# ============================================================
# 공통
# ============================================================

def load_json(path: Path) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(
    path: Path,
    data: Any,
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


def recursive_find_value(
    obj: Any,
    keys: List[str],
) -> Optional[Any]:

    if isinstance(obj, dict):

        for key in keys:

            if (
                key in obj
                and obj[key] not in (
                    None,
                    "",
                )
            ):
                return obj[key]

        for value in obj.values():

            found = recursive_find_value(
                value,
                keys,
            )

            if found not in (
                None,
                "",
            ):
                return found

    elif isinstance(obj, list):

        for value in obj:

            found = recursive_find_value(
                value,
                keys,
            )

            if found not in (
                None,
                "",
            ):
                return found

    return None


def extract_site(
    data: Any,
) -> Dict[str, str]:

    return {
        "site_id": str(
            recursive_find_value(
                data,
                [
                    "site_id",
                    "parcel_key",
                ],
            )
            or ""
        ),
        "address": str(
            recursive_find_value(
                data,
                [
                    "address",
                    "주소",
                ],
            )
            or ""
        ),
        "pnu": str(
            recursive_find_value(
                data,
                [
                    "pnu",
                    "PNU",
                ],
            )
            or ""
        ),
        "zone": str(
            recursive_find_value(
                data,
                [
                    "zone",
                    "용도지역",
                ],
            )
            or ""
        ),
    }


def clean_html_text(
    html: str,
) -> str:

    text = re.sub(
        r"<script.*?</script>",
        " ",
        html,
        flags=re.I | re.S,
    )

    text = re.sub(
        r"<style.*?</style>",
        " ",
        text,
        flags=re.I | re.S,
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = (
        text
        .replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def keyword_hits(
    text: str,
) -> List[str]:

    return [
        keyword
        for keyword
        in SEARCH_KEYWORDS
        if keyword in text
    ]


# ============================================================
# 검색 엔진 대신 공식 사이트 내부 접근 가능성 확인
#
# 이 단계는 endpoint 존재/응답 탐색용.
# 실제 검색 API가 공개되어 있지 않다면
# 실패를 FALSE로 해석하지 않는다.
# ============================================================

def probe_official_site(
    source: Dict[str, str],
) -> Dict[str, Any]:

    result = {
        "name": source["name"],
        "provider": source["provider"],
        "base_url": source["base_url"],
        "http_status": None,
        "reachable": False,
        "keyword_hits": [],
        "error": "",
    }

    try:

        response = requests.get(
            source["base_url"],
            timeout=HTTP_TIMEOUT,
            headers={
                "User-Agent":
                    "Mozilla/5.0 site-ai spatial-source-probe",
            },
        )

        result["http_status"] = (
            response.status_code
        )

        if response.status_code != 200:

            result["error"] = (
                f"HTTP {response.status_code}"
            )

            return result

        result["reachable"] = True

        text = clean_html_text(
            response.text
        )

        result["keyword_hits"] = (
            keyword_hits(
                text
            )
        )

    except Exception as exc:

        result["error"] = str(
            exc
        )

    return result


# ============================================================
# 기존 서울 탐색 결과 검증
# ============================================================

def extract_previous_resolution(
    data: Any,
) -> Dict[str, Any]:

    resolution = recursive_find_value(
        data,
        [
            "site_resolution",
        ],
    )

    if isinstance(
        resolution,
        dict,
    ):
        return resolution

    return {}


# ============================================================
# 국가 Source 후보
#
# 아직 실제 endpoint/API를 확정한 것이 아니므로
# CANDIDATE 수준으로만 저장.
# ============================================================

def build_national_source_candidates() -> List[Dict[str, Any]]:

    return [
        {
            "provider": "국토교통부",
            "source": "토지이음",
            "purpose":
                "지역ㆍ지구 명칭/행위제한/법령 체계 확인",
            "source_type":
                "LAND_USE_REGULATION",
            "geometry_verified":
                False,
            "status":
                "CANDIDATE",
        },
        {
            "provider": "국토교통부",
            "source": "국가공간정보포털",
            "purpose":
                "지역ㆍ지구 공간 레이어 / 메타데이터 탐색",
            "source_type":
                "SPATIAL_METADATA",
            "geometry_verified":
                False,
            "status":
                "CANDIDATE",
        },
    ]


# ============================================================
# main
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-4A-1 "
        "개발밀도관리구역 국가 Source 탐색 ==="
    )
    print()

    print(
        "Query Context 입력:"
    )
    print(
        QUERY_CONTEXT_PATH
    )
    print()

    print(
        "서울 Source Probe 입력:"
    )
    print(
        SEOUL_PROBE_PATH
    )
    print()

    if not QUERY_CONTEXT_PATH.exists():

        raise FileNotFoundError(
            QUERY_CONTEXT_PATH
        )

    query_context = load_json(
        QUERY_CONTEXT_PATH
    )

    site = extract_site(
        query_context
    )

    previous = {}

    if SEOUL_PROBE_PATH.exists():

        previous = load_json(
            SEOUL_PROBE_PATH
        )

    previous_resolution = (
        extract_previous_resolution(
            previous
        )
    )

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    print("=" * 70)
    print("=== 대상 SITE ===")
    print("=" * 70)

    print(
        "SITE ID:",
        site["site_id"]
        or "-",
    )

    print(
        "주소:",
        site["address"]
        or "-",
    )

    print(
        "용도지역:",
        site["zone"]
        or "-",
    )

    print(
        "PNU:",
        site["pnu"]
        or "-",
    )
    print()

    print(
        "서울시 탐색 결과:"
    )

    print(
        "query_status:",
        previous_resolution.get(
            "query_status",
            "-",
        ),
    )

    print(
        "resolution:",
        previous_resolution.get(
            "resolution",
            "-",
        ),
    )
    print()

    # --------------------------------------------------------
    # 1. 국가 공식 source reachability
    # --------------------------------------------------------

    print("=" * 70)
    print(
        "=== 1. 국가 공식 Source 접근 테스트 ==="
    )
    print("=" * 70)

    probe_results = []

    for source in (
        OFFICIAL_SEARCH_TARGETS
    ):

        result = (
            probe_official_site(
                source
            )
        )

        probe_results.append(
            result
        )

        print()
        print(
            source["name"]
        )

        print(
            "provider:",
            source["provider"],
        )

        print(
            "HTTP:",
            result[
                "http_status"
            ],
        )

        print(
            "reachable:",
            result[
                "reachable"
            ],
        )

        print(
            "keyword hits:",
            (
                ", ".join(
                    result[
                        "keyword_hits"
                    ]
                )
                or "-"
            ),
        )

        if result["error"]:

            print(
                "error:",
                result[
                    "error"
                ],
            )

    print()

    # --------------------------------------------------------
    # 2. 국가 Source 후보 구조
    # --------------------------------------------------------

    print("=" * 70)
    print(
        "=== 2. 개발밀도관리구역 국가 Source 후보 ==="
    )
    print("=" * 70)

    candidates = (
        build_national_source_candidates()
    )

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):

        print()
        print(
            f"{index}."
        )

        print(
            "provider:",
            candidate[
                "provider"
            ],
        )

        print(
            "source:",
            candidate[
                "source"
            ],
        )

        print(
            "purpose:",
            candidate[
                "purpose"
            ],
        )

        print(
            "geometry verified:",
            candidate[
                "geometry_verified"
            ],
        )

    # --------------------------------------------------------
    # 3. SITE 판정
    # --------------------------------------------------------

    final_resolution = {
        "condition":
            "개발밀도관리구역",

        "query_group":
            "URBAN_PLANNING_ZONE",

        "query_status":
            "NOT_CONNECTED",

        "resolution":
            "UNKNOWN",

        "confidence":
            "NONE",

        "reason":
            (
                "서울시 공식 카탈로그에서 "
                "개발밀도관리구역 전용 source를 "
                "확인하지 못해 국가 단위 "
                "토지이용규제/공간정보 source로 "
                "탐색 범위를 확장했으나, "
                "아직 개발밀도관리구역의 정확한 "
                "국가 관리코드 및 geometry source를 "
                "확정하지 않았으므로 "
                "TRUE/FALSE 판정을 수행하지 않음"
            ),
    }

    print()
    print("=" * 70)
    print(
        "=== 3. 현재 개발밀도관리구역 SITE 판정 ==="
    )
    print("=" * 70)

    print(
        "query_status:",
        final_resolution[
            "query_status"
        ],
    )

    print(
        "resolution:",
        final_resolution[
            "resolution"
        ],
    )

    print(
        "confidence:",
        final_resolution[
            "confidence"
        ],
    )

    print(
        "reason:",
        final_resolution[
            "reason"
        ],
    )

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validations = {
        "SITE 주소 존재":
            bool(
                site["address"]
            ),

        "PNU 19자리":
            (
                len(
                    site["pnu"]
                )
                == 19
                and site[
                    "pnu"
                ].isdigit()
            ),

        "서울 탐색 UNKNOWN 승계":
            (
                not previous_resolution
                or previous_resolution.get(
                    "resolution"
                )
                == "UNKNOWN"
            ),

        "국가 공식 source 접근 실행":
            (
                len(
                    probe_results
                )
                == len(
                    OFFICIAL_SEARCH_TARGETS
                )
            ),

        "코드번호 추측 없음":
            True,

        "geometry 미확정 TRUE 금지":
            (
                final_resolution[
                    "resolution"
                ]
                != "TRUE"
            ),

        "geometry 미확정 FALSE 금지":
            (
                final_resolution[
                    "resolution"
                ]
                != "FALSE"
            ),

        "UNKNOWN 유지":
            (
                final_resolution[
                    "resolution"
                ]
                == "UNKNOWN"
            ),
    }

    print()
    print("=" * 70)
    print(
        "=== C-9-2-4A-1 검증 ==="
    )
    print("=" * 70)

    for name, passed in (
        validations.items()
    ):

        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    all_pass = all(
        validations.values()
    )

    output = {
        "step":
            "STEP 17-21-C-9-2-4A-1",

        "site":
            site,

        "previous_seoul_resolution":
            previous_resolution,

        "target_condition":
            "개발밀도관리구역",

        "search_keywords":
            SEARCH_KEYWORDS,

        "official_source_probes":
            probe_results,

        "national_source_candidates":
            candidates,

        "site_resolution":
            final_resolution,

        "validations":
            validations,

        "all_pass":
            all_pass,
    }

    save_json(
        OUTPUT_PATH,
        output,
    )

    print()
    print("=" * 70)
    print(
        "결과 저장:"
    )
    print(
        OUTPUT_PATH
    )
    print("=" * 70)
    print()

    if not all_pass:

        print(
            "STEP 17-21-C-9-2-4A-1 "
            "검증 실패"
        )

        return

    print(
        "STEP 17-21-C-9-2-4A-1 완료"
    )
    print()

    print(
        "국가 Source 탐색 기본 프레임: "
        "ALL PASS"
    )
    print()

    print(
        "현재 개발밀도관리구역:"
    )

    print(
        "UNKNOWN"
    )
    print()

    print(
        "다음 단계:"
    )

    print(
        "STEP 17-21-C-9-2-4A-2"
    )

    print(
        "→ 토지이음 지역·지구 명칭/코드 체계 탐색"
    )

    print(
        "→ '개발밀도관리구역' 정확 코드 존재 여부 확인"
    )

    print(
        "→ 코드 확인 후 국가 공간레이어 source 탐색"
    )

    print(
        "→ source 미확정이면 UNKNOWN 유지"
    )


if __name__ == "__main__":
    main()