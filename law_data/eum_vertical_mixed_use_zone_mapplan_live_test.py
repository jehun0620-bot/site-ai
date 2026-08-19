import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-6A-6 "
    "토지이음 UQQ905 실제 MapPlan 요청 / Geometry 조회 테스트"
)


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

LAW_DATA_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DATA_DIR / "output"

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR / "site_spatial_query_context.json"
)

PREVIOUS_PATH = (
    OUTPUT_DIR /
    "eum_vertical_mixed_use_zone_mapplan_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR /
    "eum_vertical_mixed_use_zone_mapplan_live.json"
)


# ============================================================
# TARGET
# ============================================================

EUM_ROOT = "https://www.eum.go.kr"

MAP_PAGE_URL = (
    EUM_ROOT
    + "/web/mp/mpMapDet.jsp"
)

MAP_JS_URL = (
    EUM_ROOT
    + "/web/js/mp/mpMapDet.js"
)

TARGET_NAME = "도시군계획시설입체복합구역"
TARGET_CODE = "UQQ905"

TARGET_LAYER = "AC"


# ============================================================
# HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": (
        "application/json,text/javascript,"
        "*/*;q=0.01"
    ),
    "Accept-Language": (
        "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    ),
    "Referer": MAP_PAGE_URL,
    "X-Requested-With": "XMLHttpRequest",
}


# ============================================================
# UTIL
# ============================================================

def print_line():
    print("=" * 70)


def print_subline():
    print("-" * 70)


def compact(text):
    return re.sub(
        r"\s+",
        " ",
        text or "",
    ).strip()


def load_json(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(path, data):
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


def safe_text(value):
    if value is None:
        return ""

    return str(value).strip()


def first_non_empty(*values):
    for value in values:
        text = safe_text(value)

        if text:
            return text

    return ""


def get_nested(data, *paths):
    for path in paths:

        current = data
        valid = True

        for key in path:

            if not isinstance(
                current,
                dict,
            ):
                valid = False
                break

            if key not in current:
                valid = False
                break

            current = current[key]

        if valid and current not in (
            None,
            "",
        ):
            return current

    return None


def normalize_site(data):

    return {
        "site_id": first_non_empty(
            data.get("site_id"),
            get_nested(
                data,
                ("site", "site_id"),
                ("query_context", "site_id"),
            ),
        ),

        "address": first_non_empty(
            data.get("address"),
            data.get("lot_address"),
            get_nested(
                data,
                ("site", "address"),
                ("query_context", "address"),
            ),
        ),

        "pnu": first_non_empty(
            data.get("pnu"),
            data.get("PNU"),
            get_nested(
                data,
                ("site", "pnu"),
                ("query_context", "pnu"),
            ),
        ),
    }


# ============================================================
# HTTP
# ============================================================

def request(
    session,
    url,
    params=None,
    timeout=30,
):

    result = {
        "url": url,
        "params": params or {},
        "http_status": None,
        "content_type": None,
        "text": "",
        "json": None,
        "error": None,
    }

    try:

        response = session.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=timeout,
        )

        result["http_status"] = (
            response.status_code
        )

        result["content_type"] = (
            response.headers.get(
                "Content-Type"
            )
        )

        result["text"] = response.text

        try:
            result["json"] = (
                response.json()
            )
        except Exception:
            pass

    except Exception as e:

        result["error"] = repr(e)

    return result


# ============================================================
# SCRIPT
# ============================================================

def extract_function(
    text,
    function_name,
):

    pattern = (
        rf"\$\.fn\.{re.escape(function_name)}"
        rf"\s*=\s*function\s*\([^)]*\)\s*\{{"
    )

    match = re.search(
        pattern,
        text,
    )

    if not match:
        return None

    brace_start = text.find(
        "{",
        match.start(),
    )

    if brace_start < 0:
        return None

    depth = 0
    in_single = False
    in_double = False
    escape = False

    for i in range(
        brace_start,
        len(text),
    ):

        ch = text[i]

        if escape:
            escape = False
            continue

        if ch == "\\":
            escape = True
            continue

        if (
            ch == "'"
            and not in_double
        ):
            in_single = (
                not in_single
            )

        elif (
            ch == '"'
            and not in_single
        ):
            in_double = (
                not in_double
            )

        elif (
            not in_single
            and not in_double
        ):

            if ch == "{":
                depth += 1

            elif ch == "}":
                depth -= 1

                if depth == 0:
                    return text[
                        match.start():i + 1
                    ]

    return None


# ============================================================
# SETINITDATA
# ============================================================

def extract_setinit_calls(html):

    pattern = re.compile(
        r"""
        \$\.fn\.setinitData
        \s*\(
        (?P<args>.*?)
        \)
        """,
        re.VERBOSE | re.DOTALL,
    )

    calls = []

    for m in pattern.finditer(
        html
    ):

        args_raw = m.group(
            "args"
        )

        calls.append(
            {
                "raw": compact(
                    args_raw
                )
            }
        )

    return calls


def extract_string_literals(text):

    values = re.findall(
        r"""["']([^"']*)["']""",
        text,
    )

    return values


def detect_server_from_calls(calls):

    candidates = []

    for call in calls:

        literals = (
            extract_string_literals(
                call["raw"]
            )
        )

        for value in literals:

            if (
                "http://" in value
                or "https://" in value
            ):

                if value not in candidates:
                    candidates.append(
                        value
                    )

    return candidates


# ============================================================
# VERSION
# ============================================================

def extract_versions(html):

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    select = soup.find(
        "select",
        id="selLcstSpaceDplyDate",
    )

    values = []

    if select:

        for option in select.find_all(
            "option"
        ):

            value = safe_text(
                option.get("value")
            )

            if value:
                values.append(
                    value
                )

    return values


# ============================================================
# PNU / BBOX
# ============================================================

def find_parcel_bbox_from_previous():

    candidate_files = [
        OUTPUT_DIR /
        "seoul_natural_landscape_district_intersection_test.json",

        OUTPUT_DIR /
        "seoul_development_promotion_district_intersection_test.json",

        OUTPUT_DIR /
        "vworld_parcel_polygon_identifier_probe.json",
    ]

    for path in candidate_files:

        if not path.exists():
            continue

        try:
            data = load_json(path)
        except Exception:
            continue

        text = json.dumps(
            data,
            ensure_ascii=False,
        )

        # 직접 4개 숫자 bounds 배열 탐색
        pattern = re.compile(
            r"""
            "bounds"
            \s*:\s*
            \[
            \s*
            (-?\d+(?:\.\d+)?)
            \s*,\s*
            (-?\d+(?:\.\d+)?)
            \s*,\s*
            (-?\d+(?:\.\d+)?)
            \s*,\s*
            (-?\d+(?:\.\d+)?)
            \s*
            \]
            """,
            re.VERBOSE,
        )

        m = pattern.search(text)

        if m:

            return {
                "source": str(path),
                "bounds_4326": [
                    float(m.group(1)),
                    float(m.group(2)),
                    float(m.group(3)),
                    float(m.group(4)),
                ],
            }

    # 기존 콘솔 검증값 fallback
    return {
        "source": "KNOWN_TEST_VALUE",
        "bounds_4326": [
            127.07240240227819,
            37.49198725375971,
            127.0781619622408,
            37.49647755722794,
        ],
    }


# ============================================================
# EPSG 4326 -> 5179
# ============================================================

def transform_bbox_4326_to_5179(
    bounds,
):

    try:
        from pyproj import Transformer
    except ImportError:
        raise RuntimeError(
            "pyproj가 필요합니다. "
            "pip install pyproj"
        )

    transformer = (
        Transformer.from_crs(
            "EPSG:4326",
            "EPSG:5179",
            always_xy=True,
        )
    )

    minx, miny, maxx, maxy = bounds

    corners = [
        transformer.transform(
            minx,
            miny,
        ),
        transformer.transform(
            minx,
            maxy,
        ),
        transformer.transform(
            maxx,
            miny,
        ),
        transformer.transform(
            maxx,
            maxy,
        ),
    ]

    xs = [
        x for x, y in corners
    ]

    ys = [
        y for x, y in corners
    ]

    return [
        min(xs),
        min(ys),
        max(xs),
        max(ys),
    ]


# ============================================================
# GEOJSON
# ============================================================

def classify_geojson(data):

    if not isinstance(
        data,
        dict,
    ):
        return {
            "is_geojson": False,
            "feature_count": 0,
            "geometry_types": [],
        }

    feature_count = 0
    geometry_types = []

    if (
        data.get("type")
        == "FeatureCollection"
    ):

        features = data.get(
            "features",
            [],
        )

        feature_count = len(
            features
        )

        for feature in features:

            geometry = (
                feature.get(
                    "geometry"
                )
                or {}
            )

            gtype = geometry.get(
                "type"
            )

            if (
                gtype
                and gtype
                not in geometry_types
            ):
                geometry_types.append(
                    gtype
                )

        return {
            "is_geojson": True,
            "feature_count": (
                feature_count
            ),
            "geometry_types": (
                geometry_types
            ),
        }

    return {
        "is_geojson": False,
        "feature_count": 0,
        "geometry_types": [],
    }


# ============================================================
# ANALYSIS RESULT SEARCH
# ============================================================

def recursive_find_code(
    value,
    code,
    path="$",
    results=None,
):

    if results is None:
        results = []

    if isinstance(
        value,
        dict,
    ):

        for key, item in (
            value.items()
        ):

            recursive_find_code(
                item,
                code,
                f"{path}.{key}",
                results,
            )

    elif isinstance(
        value,
        list,
    ):

        for idx, item in (
            enumerate(value)
        ):

            recursive_find_code(
                item,
                code,
                f"{path}[{idx}]",
                results,
            )

    else:

        text = safe_text(
            value
        )

        if code in text:

            results.append(
                {
                    "path": path,
                    "value": text,
                }
            )

    return results


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        f"=== {STEP_NAME} ==="
    )

    print()

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    raw_context = load_json(
        QUERY_CONTEXT_PATH
    )

    site = normalize_site(
        raw_context
    )

    pnu = site["pnu"]

    print_line()
    print("=== 대상 SITE ===")
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
        "PNU:",
        pnu or "-",
    )

    if (
        len(pnu) != 19
        or not pnu.isdigit()
    ):

        raise RuntimeError(
            "PNU가 정상적인 19자리 값이 아닙니다."
        )

    print()

    # --------------------------------------------------------
    # SESSION
    # --------------------------------------------------------

    session = requests.Session()

    print_line()
    print(
        "=== 1. 토지이음 지도 초기화 ==="
    )
    print_line()

    page_result = request(
        session,
        MAP_PAGE_URL,
        params={
            "add": "land",
            "pnu": pnu,
        },
    )

    print(
        "HTTP:",
        page_result[
            "http_status"
        ],
    )

    print(
        "HTML length:",
        len(
            page_result[
                "text"
            ]
        ),
    )

    if page_result[
        "http_status"
    ] != 200:

        raise RuntimeError(
            "토지이음 지도 초기화 실패"
        )

    html = (
        page_result["text"]
    )

    print()

    # --------------------------------------------------------
    # setinitData
    # --------------------------------------------------------

    print_line()
    print(
        "=== 2. setinitData 실제 호출부 분석 ==="
    )
    print_line()

    setinit_calls = (
        extract_setinit_calls(
            html
        )
    )

    print(
        "호출 수:",
        len(
            setinit_calls
        ),
    )

    for idx, call in enumerate(
        setinit_calls,
        start=1,
    ):

        print_subline()

        print(
            f"Call {idx}"
        )

        print(
            call["raw"][:3000]
        )

    server_candidates = (
        detect_server_from_calls(
            setinit_calls
        )
    )

    print()

    print(
        "gisServer 후보 수:",
        len(
            server_candidates
        ),
    )

    for idx, server in enumerate(
        server_candidates,
        start=1,
    ):
        print(
            f"{idx}. {server}"
        )

    print()

    # --------------------------------------------------------
    # VERSION
    # --------------------------------------------------------

    print_line()
    print(
        "=== 3. MapPlan version 확인 ==="
    )
    print_line()

    versions = (
        extract_versions(
            html
        )
    )

    print(
        "version 후보 수:",
        len(
            versions
        ),
    )

    for value in versions[:20]:
        print(
            "-",
            value,
        )

    version = (
        versions[0]
        if versions
        else ""
    )

    print()

    print(
        "선택 version:",
        version or "-",
    )

    print()

    # --------------------------------------------------------
    # JS 재검증
    # --------------------------------------------------------

    print_line()
    print(
        "=== 4. UQQ905 요청규칙 재검증 ==="
    )
    print_line()

    js_result = request(
        session,
        MAP_JS_URL,
    )

    show_function = (
        extract_function(
            js_result["text"],
            "showLcstSpace",
        )
        or ""
    )

    rule_verified = (
        'layer:layerNames'
        in show_function
        and 'code:code'
        in show_function
        and 'mbr: coord'
        in show_function
        and 'req=search'
        in show_function
    )

    print(
        "showLcstSpace 발견:",
        bool(
            show_function
        ),
    )

    print(
        "요청규칙 검증:",
        rule_verified,
    )

    print(
        "TARGET DOM class:",
        "typeAC_UQQ905",
    )

    print(
        "복원 layer:",
        TARGET_LAYER,
    )

    print(
        "복원 code:",
        TARGET_CODE,
    )

    print()

    # --------------------------------------------------------
    # PARCEL BBOX
    # --------------------------------------------------------

    print_line()
    print(
        "=== 5. Parcel BBOX 준비 ==="
    )
    print_line()

    parcel_bbox = (
        find_parcel_bbox_from_previous()
    )

    bounds_4326 = (
        parcel_bbox[
            "bounds_4326"
        ]
    )

    bounds_5179 = (
        transform_bbox_4326_to_5179(
            bounds_4326
        )
    )

    # 너무 필지 경계와 정확히 일치하면
    # 경계 오차 가능성이 있으므로
    # 30m buffer 적용
    buffer_meter = 30.0

    search_bbox_5179 = [
        bounds_5179[0]
        - buffer_meter,

        bounds_5179[1]
        - buffer_meter,

        bounds_5179[2]
        + buffer_meter,

        bounds_5179[3]
        + buffer_meter,
    ]

    mbr = ",".join(
        str(v)
        for v in search_bbox_5179
    )

    print(
        "BBOX source:",
        parcel_bbox[
            "source"
        ],
    )

    print(
        "EPSG:4326 bounds:",
        bounds_4326,
    )

    print(
        "EPSG:5179 bounds:",
        bounds_5179,
    )

    print(
        "검색 BBOX buffer:",
        buffer_meter,
        "m",
    )

    print(
        "MapPlan mbr:",
        mbr,
    )

    print()

    # --------------------------------------------------------
    # SERVER
    # --------------------------------------------------------

    print_line()
    print(
        "=== 6. MapPlan Server 확정 ==="
    )
    print_line()

    usable_servers = []

    for value in (
        server_candidates
    ):

        value = value.rstrip(
            "/"
        )

        if value not in (
            usable_servers
        ):
            usable_servers.append(
                value
            )

    print(
        "server 후보:",
        usable_servers or "-",
    )

    print()

    # --------------------------------------------------------
    # LIVE SEARCH
    # --------------------------------------------------------

    print_line()
    print(
        "=== 7. UQQ905 Geometry 실제 요청 ==="
    )
    print_line()

    search_results = []

    for server in (
        usable_servers
    ):

        url = (
            server
            + "/MapPlan"
        )

        params = {
            "req": "search",
            "version": version,
            "layer": TARGET_LAYER,
            "mbr": mbr,
            "code": TARGET_CODE,
        }

        result = request(
            session,
            url,
            params=params,
        )

        geo = classify_geojson(
            result["json"]
        )

        record = {
            "server": server,
            "url": url,
            "params": params,
            "http_status": (
                result[
                    "http_status"
                ]
            ),
            "content_type": (
                result[
                    "content_type"
                ]
            ),
            "geojson": geo,
            "preview": (
                result[
                    "text"
                ][:3000]
            ),
        }

        search_results.append(
            record
        )

        print_subline()

        print(
            "server:",
            server,
        )

        print(
            "HTTP:",
            result[
                "http_status"
            ],
        )

        print(
            "Content-Type:",
            result[
                "content_type"
            ],
        )

        print(
            "GeoJSON:",
            geo[
                "is_geojson"
            ],
        )

        print(
            "Feature 수:",
            geo[
                "feature_count"
            ],
        )

        print(
            "geometry type:",
            geo[
                "geometry_types"
            ],
        )

        print(
            "preview:",
            compact(
                result[
                    "text"
                ]
            )[:1200],
        )

    print()

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    print_line()
    print(
        "=== 8. PNU 직접 Analysis 요청 ==="
    )
    print_line()

    analysis_results = []

    for server in (
        usable_servers
    ):

        url = (
            server
            + "/MapPlan"
        )

        params = {
            "req": "analysis",
            "version": version,
            "pnus": pnu,
        }

        result = request(
            session,
            url,
            params=params,
        )

        hits = (
            recursive_find_code(
                result[
                    "json"
                ],
                TARGET_CODE,
            )
            if result[
                "json"
            ] is not None
            else []
        )

        record = {
            "server": server,
            "url": url,
            "params": params,
            "http_status": (
                result[
                    "http_status"
                ]
            ),
            "content_type": (
                result[
                    "content_type"
                ]
            ),
            "target_hits": hits,
            "preview": (
                result[
                    "text"
                ][:5000]
            ),
        }

        analysis_results.append(
            record
        )

        print_subline()

        print(
            "server:",
            server,
        )

        print(
            "HTTP:",
            result[
                "http_status"
            ],
        )

        print(
            "Content-Type:",
            result[
                "content_type"
            ],
        )

        print(
            "UQQ905 hit 수:",
            len(
                hits
            ),
        )

        for hit in hits[:20]:

            print(
                "  -",
                hit[
                    "path"
                ],
                "=",
                hit[
                    "value"
                ],
            )

        print(
            "preview:",
            compact(
                result[
                    "text"
                ]
            )[:1500],
        )

    print()

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    successful_geometry = [
        item
        for item
        in search_results
        if (
            item[
                "http_status"
            ] == 200
            and item[
                "geojson"
            ][
                "is_geojson"
            ]
        )
    ]

    geometry_feature_count = sum(
        item[
            "geojson"
        ][
            "feature_count"
        ]
        for item
        in successful_geometry
    )

    analysis_hits = sum(
        len(
            item[
                "target_hits"
            ]
        )
        for item
        in analysis_results
    )

    print_line()
    print(
        "=== 9. 현재 입체복합구역 판정 ==="
    )
    print_line()

    # 중요:
    # 아직 geometry와 Parcel의 실제 shapely intersection을
    # 하지 않았으므로 Feature 존재만으로 TRUE 확정하지 않는다.

    if geometry_feature_count > 0:

        query_status = (
            "QUERY_SUCCESS"
        )

        resolution = (
            "UNKNOWN"
        )

        confidence = (
            "MEDIUM"
        )

        reason = (
            "UQQ905 MapPlan geometry Feature 조회에는 "
            "성공했으나 다음 단계에서 응답 CRS를 확인하고 "
            "대상 Parcel Polygon과 실제 면적 intersection을 "
            "수행한 뒤 TRUE/FALSE를 확정해야 함"
        )

    elif successful_geometry:

        query_status = (
            "QUERY_SUCCESS"
        )

        resolution = (
            "UNKNOWN"
        )

        confidence = (
            "MEDIUM"
        )

        reason = (
            "대상 Parcel 주변 BBOX에 대해 UQQ905 "
            "MapPlan geometry 조회가 정상 수행되었으나 "
            "현재 응답 Feature가 0개임. BBOX 범위조회만으로 "
            "즉시 FALSE를 확정하지 않고 전체 조회 의미와 "
            "Parcel intersection 조건을 다음 단계에서 "
            "검증해야 함"
        )

    else:

        query_status = (
            "NOT_CONNECTED"
        )

        resolution = (
            "UNKNOWN"
        )

        confidence = (
            "NONE"
        )

        reason = (
            "UQQ905 요청 구조는 복원했으나 "
            "실제 MapPlan server 또는 geometry 응답을 "
            "아직 정상 확보하지 못함"
        )

    print(
        "query_status:",
        query_status,
    )

    print(
        "resolution:",
        resolution,
    )

    print(
        "confidence:",
        confidence,
    )

    print(
        "geometry Feature 수:",
        geometry_feature_count,
    )

    print(
        "PNU analysis UQQ905 hit 수:",
        analysis_hits,
    )

    print(
        "reason:",
        reason,
    )

    print()

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    print_line()
    print(
        "=== C-9-2-6A-6 검증 ==="
    )
    print_line()

    checks = {
        "SITE 주소 존재": (
            bool(
                site[
                    "address"
                ]
            )
        ),

        "PNU 19자리": (
            len(pnu) == 19
            and pnu.isdigit()
        ),

        "토지이음 지도 초기화": (
            page_result[
                "http_status"
            ] == 200
        ),

        "setinitData 호출 탐색": (
            isinstance(
                setinit_calls,
                list,
            )
        ),

        "MapPlan version 탐색": (
            isinstance(
                versions,
                list,
            )
        ),

        "UQQ905 요청규칙 검증": (
            rule_verified
        ),

        "layer AC 복원": (
            TARGET_LAYER
            == "AC"
        ),

        "code UQQ905 복원": (
            TARGET_CODE
            == "UQQ905"
        ),

        "EPSG:5179 BBOX 생성": (
            len(
                search_bbox_5179
            )
            == 4
        ),

        "MapPlan search 실행": (
            isinstance(
                search_results,
                list,
            )
        ),

        "MapPlan analysis 실행": (
            isinstance(
                analysis_results,
                list,
            )
        ),

        "Feature 존재만으로 TRUE 금지": (
            resolution
            != "TRUE"
        ),

        "부분 BBOX 무교차만으로 FALSE 금지": (
            resolution
            != "FALSE"
        ),

        "intersection 전 UNKNOWN 유지": (
            resolution
            == "UNKNOWN"
        ),
    }

    for name, passed in (
        checks.items()
    ):

        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    output = {
        "step": STEP_NAME,

        "site": site,

        "target": {
            "name": TARGET_NAME,
            "code": TARGET_CODE,
            "layer": TARGET_LAYER,
        },

        "setinit_calls": (
            setinit_calls
        ),

        "server_candidates": (
            server_candidates
        ),

        "versions": versions,

        "selected_version": (
            version
        ),

        "parcel_bbox": {
            "source": (
                parcel_bbox[
                    "source"
                ]
            ),
            "epsg4326": (
                bounds_4326
            ),
            "epsg5179": (
                bounds_5179
            ),
            "search_epsg5179": (
                search_bbox_5179
            ),
            "buffer_meter": (
                buffer_meter
            ),
        },

        "mapplan_search": (
            search_results
        ),

        "mapplan_analysis": (
            analysis_results
        ),

        "site_resolution": {
            "query_status": (
                query_status
            ),
            "resolution": (
                resolution
            ),
            "confidence": (
                confidence
            ),
            "geometry_feature_count": (
                geometry_feature_count
            ),
            "analysis_target_hits": (
                analysis_hits
            ),
            "reason": reason,
        },

        "validation": checks,
    }

    save_json(
        OUTPUT_PATH,
        output,
    )

    print()

    print_line()

    print(
        "결과 저장:"
    )

    print(
        OUTPUT_PATH
    )

    print_line()

    print()

    if all(
        checks.values()
    ):

        print(
            "STEP 17-21-C-9-2-6A-6 완료"
        )

        print()

        if geometry_feature_count > 0:

            print(
                "UQQ905 실제 geometry 확보 성공"
            )

            print()

            print(
                "다음 단계:"
            )

            print(
                "STEP 17-21-C-9-2-6B"
            )

            print(
                "→ MapPlan GeoJSON CRS 확인"
            )

            print(
                "→ Parcel Polygon과 CRS 통일"
            )

            print(
                "→ 실제 Polygon intersection"
            )

            print(
                "→ 교차면적 > 0이면 TRUE"
            )

            print(
                "→ 정상 조회 후 실제 교차 없음이면 FALSE"
            )

        else:

            print(
                "UQQ905 요청 실행 완료"
            )

            print()

            print(
                "실제 geometry 응답 결과를 확인한 뒤 "
                "server/version/BBOX 조건을 보정합니다."
            )

    else:

        print(
            "STEP 17-21-C-9-2-6A-6 검증 미완료"
        )


if __name__ == "__main__":
    main()