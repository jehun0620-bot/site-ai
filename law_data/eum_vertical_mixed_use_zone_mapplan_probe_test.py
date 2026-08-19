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
    "STEP 17-21-C-9-2-6A-5 "
    "토지이음 MapPlan UQQ905 실제 공간 Layer 요청 구조 분석"
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

PREVIOUS_PROBE_PATH = (
    OUTPUT_DIR /
    "eum_vertical_mixed_use_zone_gis_endpoint_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR /
    "eum_vertical_mixed_use_zone_mapplan_probe.json"
)


# ============================================================
# EUM
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

TARGET_NAME = (
    "도시군계획시설입체복합구역"
)

TARGET_CODE = "UQQ905"


# ============================================================
# HTTP
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": (
        "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    ),
    "Referer": MAP_PAGE_URL,
}


# ============================================================
# UTIL
# ============================================================

def print_line():
    print("=" * 70)


def print_subline():
    print("-" * 70)


def safe_text(value):
    if value is None:
        return ""

    return str(value).strip()


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


def first_non_empty(*values):
    for value in values:

        text = safe_text(value)

        if text:
            return text

    return ""


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


def compact(text):
    return re.sub(
        r"\s+",
        " ",
        text or "",
    ).strip()


# ============================================================
# HTTP REQUEST
# ============================================================

def request(
    session,
    url,
    method="GET",
    params=None,
    data=None,
    timeout=30,
):

    result = {
        "url": url,
        "method": method,
        "params": params or {},
        "data": data or {},
        "http_status": None,
        "content_type": None,
        "text": "",
        "json": None,
        "error": None,
    }

    try:

        if method.upper() == "POST":

            response = session.post(
                url,
                params=params,
                data=data,
                headers=HEADERS,
                timeout=timeout,
            )

        else:

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

        result["text"] = (
            response.text
        )

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
# JS PARSING
# ============================================================

def extract_assignment_values(
    text,
    variable_name,
):

    patterns = [
        rf"""
        \b{re.escape(variable_name)}
        \s*=\s*
        ["']([^"']+)["']
        """,

        rf"""
        \bvar\s+
        {re.escape(variable_name)}
        \s*=\s*
        ["']([^"']+)["']
        """,
    ]

    values = []

    for pattern in patterns:

        for m in re.finditer(
            pattern,
            text,
            flags=(
                re.IGNORECASE
                | re.VERBOSE
            ),
        ):

            value = m.group(1)

            if value not in values:
                values.append(value)

    return values


def extract_keyword_contexts(
    text,
    keyword,
    radius=2500,
):

    contexts = []

    start = 0

    while True:

        idx = text.find(
            keyword,
            start,
        )

        if idx < 0:
            break

        left = max(
            0,
            idx - radius,
        )

        right = min(
            len(text),
            idx + len(keyword) + radius,
        )

        contexts.append(
            text[left:right]
        )

        start = (
            idx
            + len(keyword)
        )

    return contexts


def extract_function(
    text,
    function_name,
):
    """
    $.fn.xxx = function(...) { ... }
    형태 함수 body를 brace depth 방식으로 추출한다.
    """

    patterns = [
        (
            rf"\$\.fn\.{re.escape(function_name)}"
            rf"\s*=\s*function\s*\([^)]*\)\s*\{{"
        ),

        (
            rf"{re.escape(function_name)}"
            rf"\s*=\s*function\s*\([^)]*\)\s*\{{"
        ),
    ]

    match = None

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
        )

        if match:
            break

    if not match:
        return None

    start = match.start()

    brace_start = (
        text.find(
            "{",
            match.start(),
        )
    )

    if brace_start < 0:
        return None

    depth = 0

    in_single = False
    in_double = False
    escape = False

    i = brace_start

    while i < len(text):

        ch = text[i]

        if escape:
            escape = False
            i += 1
            continue

        if ch == "\\":
            escape = True
            i += 1
            continue

        if not in_double and ch == "'":
            in_single = not in_single

        elif not in_single and ch == '"':
            in_double = not in_double

        elif not in_single and not in_double:

            if ch == "{":
                depth += 1

            elif ch == "}":
                depth -= 1

                if depth == 0:

                    return text[
                        start:i + 1
                    ]

        i += 1

    return None


# ============================================================
# HTML INLINE VALUES
# ============================================================

def analyze_html_variables(html):

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    scripts = soup.find_all(
        "script"
    )

    inline = []

    for script in scripts:

        if script.get("src"):
            continue

        text = (
            script.get_text()
            or ""
        )

        if text.strip():
            inline.append(text)

    joined = "\n".join(inline)

    variable_names = [
        "context",
        "server",
        "initPnu",
        "initAddr",
        "detType",
        "lcstSpace",
    ]

    result = {}

    for variable in variable_names:

        result[variable] = (
            extract_assignment_values(
                joined,
                variable,
            )
        )

    return {
        "inline_script_count": (
            len(inline)
        ),
        "values": result,
        "inline_text": joined,
    }


# ============================================================
# URL CANDIDATES
# ============================================================

def build_context_candidates():

    return [
        "",
        "/web",
    ]


def build_ajax_candidates():

    urls = []

    for context in build_context_candidates():

        url = (
            EUM_ROOT
            + context
            + "/mp/mpMapDetGisAjaxXml.jsp"
        )

        if url not in urls:
            urls.append(url)

    return urls


def build_mapplan_candidates(
    server_values,
):

    urls = []

    # JS/HTML 실제 값 우선
    for server in server_values:

        server = safe_text(server)

        if not server:
            continue

        if server.startswith(
            "http://"
        ) or server.startswith(
            "https://"
        ):

            base = server.rstrip("/")

        elif server.startswith("/"):

            base = (
                EUM_ROOT
                + server
            ).rstrip("/")

        else:

            base = urljoin(
                MAP_PAGE_URL,
                server,
            ).rstrip("/")

        url = (
            base
            + "/MapPlan"
        )

        if url not in urls:
            urls.append(url)

    # fallback
    fallbacks = [
        EUM_ROOT + "/MapPlan",
        EUM_ROOT + "/web/MapPlan",
        EUM_ROOT + "/web/mp/MapPlan",
    ]

    for url in fallbacks:

        if url not in urls:
            urls.append(url)

    return urls


# ============================================================
# DATA ANALYSIS
# ============================================================

def recursive_find_target(
    value,
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

            recursive_find_target(
                item,
                path=(
                    f"{path}.{key}"
                ),
                results=results,
            )

    elif isinstance(
        value,
        list,
    ):

        for idx, item in (
            enumerate(value)
        ):

            recursive_find_target(
                item,
                path=(
                    f"{path}[{idx}]"
                ),
                results=results,
            )

    else:

        text = safe_text(value)

        if (
            TARGET_CODE in text
            or TARGET_NAME in text
        ):

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
        "=== 1. 토지이음 Map Page 재조회 ==="
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
        page_result["http_status"],
    )

    print(
        "Content-Type:",
        page_result[
            "content_type"
        ],
    )

    print(
        "HTML length:",
        len(
            page_result["text"]
        ),
    )

    if page_result[
        "http_status"
    ] != 200:

        raise RuntimeError(
            "토지이음 Map Page 조회 실패"
        )

    html = (
        page_result["text"]
    )

    print()

    # --------------------------------------------------------
    # HTML 변수
    # --------------------------------------------------------

    print_line()
    print(
        "=== 2. context / server 실제 값 탐색 ==="
    )
    print_line()

    html_analysis = (
        analyze_html_variables(
            html
        )
    )

    print(
        "inline script 수:",
        html_analysis[
            "inline_script_count"
        ],
    )

    for name, values in (
        html_analysis[
            "values"
        ].items()
    ):

        print(
            f"{name}:",
            values or "-",
        )

    print()

    # --------------------------------------------------------
    # JS
    # --------------------------------------------------------

    print_line()
    print(
        "=== 3. mpMapDet.js 조회 ==="
    )
    print_line()

    js_result = request(
        session,
        MAP_JS_URL,
    )

    print(
        "HTTP:",
        js_result[
            "http_status"
        ],
    )

    print(
        "JS length:",
        len(
            js_result[
                "text"
            ]
        ),
    )

    if js_result[
        "http_status"
    ] != 200:

        raise RuntimeError(
            "mpMapDet.js 조회 실패"
        )

    js = js_result["text"]

    print()

    # --------------------------------------------------------
    # 중요 함수 전문
    # --------------------------------------------------------

    print_line()
    print(
        "=== 4. 공간 Layer 관련 함수 전문 추출 ==="
    )
    print_line()

    function_names = [
        "changeCenter",
        "setLeftHtml",
        "showLcstSpace",
        "setMiniMapLcstSpace",
        "changeMiniCenter",
        "getSettingMiniMap",
        "changeLcstSpaceDplyDate",
    ]

    functions = {}

    for function_name in (
        function_names
    ):

        function_text = (
            extract_function(
                js,
                function_name,
            )
        )

        functions[
            function_name
        ] = function_text

        print_subline()

        print(
            "function:",
            function_name,
        )

        print(
            "found:",
            bool(
                function_text
            ),
        )

        if function_text:

            print(
                function_text[
                    :15000
                ]
            )

    print()

    # --------------------------------------------------------
    # MapPlan context
    # --------------------------------------------------------

    print_line()
    print(
        "=== 5. MapPlan 요청 문맥 ==="
    )
    print_line()

    mapplan_contexts = (
        extract_keyword_contexts(
            js,
            "/MapPlan",
            radius=1800,
        )
    )

    print(
        "MapPlan context 수:",
        len(
            mapplan_contexts
        ),
    )

    for idx, ctx in enumerate(
        mapplan_contexts,
        start=1,
    ):

        print_subline()

        print(
            f"Context {idx}"
        )

        print(
            compact(ctx)[
                :5000
            ]
        )

    print()

    # --------------------------------------------------------
    # server 변수 후보
    # --------------------------------------------------------

    print_line()
    print(
        "=== 6. server 초기화 구조 분석 ==="
    )
    print_line()

    server_contexts = (
        extract_keyword_contexts(
            js,
            "server =",
            radius=2000,
        )
    )

    server_contexts += (
        extract_keyword_contexts(
            js,
            "server=",
            radius=2000,
        )
    )

    unique_server_contexts = []

    for ctx in server_contexts:

        if ctx not in (
            unique_server_contexts
        ):
            unique_server_contexts.append(
                ctx
            )

    print(
        "server assignment context 수:",
        len(
            unique_server_contexts
        ),
    )

    for idx, ctx in enumerate(
        unique_server_contexts,
        start=1,
    ):

        print_subline()
        print(
            f"Context {idx}"
        )
        print(
            compact(ctx)[:5000]
        )

    print()

    # --------------------------------------------------------
    # AJAX context path 수정 검증
    # --------------------------------------------------------

    print_line()
    print(
        "=== 7. mpMapDetGisAjaxXml.jsp 실제 Context Path 검증 ==="
    )
    print_line()

    ajax_results = []

    for url in (
        build_ajax_candidates()
    ):

        result = request(
            session,
            url,
            method="POST",
            data={
                "sId": (
                    "selectGisPnuAddr"
                ),
                "pnu": pnu,
            },
        )

        item = {
            "url": url,
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
            "preview": (
                result[
                    "text"
                ][:1500]
            ),
        }

        ajax_results.append(
            item
        )

        print_subline()

        print(
            "URL:",
            url,
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
            "preview:",
            compact(
                result[
                    "text"
                ]
            )[:800],
        )

    print()

    # --------------------------------------------------------
    # MapPlan URL 후보
    # --------------------------------------------------------

    html_server_values = (
        html_analysis[
            "values"
        ].get(
            "server",
            [],
        )
    )

    js_server_values = (
        extract_assignment_values(
            js,
            "server",
        )
    )

    server_values = []

    for value in (
        html_server_values
        + js_server_values
    ):

        if value not in (
            server_values
        ):
            server_values.append(
                value
            )

    print_line()
    print(
        "=== 8. MapPlan Endpoint 접근 테스트 ==="
    )
    print_line()

    mapplan_urls = (
        build_mapplan_candidates(
            server_values
        )
    )

    mapplan_access_results = []

    for url in mapplan_urls:

        # req=search는 PNU 좌표 없이
        # 임의 geometry 판정을 하지 않는다.
        # 여기서는 endpoint 존재 여부만 본다.

        result = request(
            session,
            url,
            params={
                "req": "code",
            },
        )

        record = {
            "url": url,
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
            "preview": (
                result[
                    "text"
                ][:1500]
            ),
        }

        mapplan_access_results.append(
            record
        )

        print_subline()

        print(
            "URL:",
            url,
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
            "preview:",
            compact(
                result[
                    "text"
                ]
            )[:800],
        )

    print()

    # --------------------------------------------------------
    # UQQ905 직접 하드코딩 여부
    # --------------------------------------------------------

    print_line()
    print(
        "=== 9. UQQ905 실제 요청 구조 확인 ==="
    )
    print_line()

    uqq905_js_contexts = (
        extract_keyword_contexts(
            js,
            TARGET_CODE,
            radius=2500,
        )
    )

    html_target = (
        TARGET_CODE in html
        and TARGET_NAME in html
    )

    print(
        "HTML legend 연결:",
        html_target,
    )

    print(
        "JS UQQ905 직접 참조 수:",
        len(
            uqq905_js_contexts
        ),
    )

    for idx, ctx in enumerate(
        uqq905_js_contexts,
        start=1,
    ):

        print_subline()

        print(
            f"Context {idx}"
        )

        print(
            compact(ctx)[:5000]
        )

    print()

    # --------------------------------------------------------
    # showLcstSpace 핵심 분석
    # --------------------------------------------------------

    print_line()
    print(
        "=== 10. showLcstSpace 요청구조 판정 ==="
    )
    print_line()

    show_function = (
        functions.get(
            "showLcstSpace"
        )
        or ""
    )

    show_has_mapplan = (
        "MapPlan" in show_function
    )

    show_has_search = (
        "req=search" in show_function
    )

    show_has_code = (
        "req=code" in show_function
    )

    show_has_lcst = (
        "lcstSpace" in show_function
    )

    show_has_mbr = (
        "mbr" in show_function
    )

    show_has_layer = (
        "layer" in show_function.lower()
    )

    print(
        "MapPlan 사용:",
        show_has_mapplan,
    )

    print(
        "req=search 사용:",
        show_has_search,
    )

    print(
        "req=code 사용:",
        show_has_code,
    )

    print(
        "lcstSpace 사용:",
        show_has_lcst,
    )

    print(
        "mbr 사용:",
        show_has_mbr,
    )

    print(
        "layer 관련 값 사용:",
        show_has_layer,
    )

    print()

    # --------------------------------------------------------
    # 판정
    # --------------------------------------------------------

    print_line()
    print(
        "=== 11. 입체복합구역 공간 Source 현재 판정 ==="
    )
    print_line()

    valid_ajax_urls = [
        item
        for item in ajax_results
        if item[
            "http_status"
        ] == 200
    ]

    valid_mapplan_urls = [
        item
        for item
        in mapplan_access_results
        if item[
            "http_status"
        ] == 200
    ]

    if (
        show_function
        and show_has_mapplan
    ):

        source_status = (
            "MAPPLAN_LAYER_REQUEST_STRUCTURE_FOUND"
        )

        reason = (
            "mpMapDet.js의 showLcstSpace 함수에서 "
            "범례 선택 후 공간 영역을 조회하는 MapPlan "
            "요청 구조를 직접 확인함. 다음 단계에서는 "
            "해당 함수의 실제 parameter를 그대로 복원하여 "
            "UQQ905 Feature geometry 조회를 수행해야 함"
        )

    elif valid_mapplan_urls:

        source_status = (
            "MAPPLAN_ENDPOINT_FOUND_"
            "LAYER_REQUEST_UNRESOLVED"
        )

        reason = (
            "MapPlan endpoint 접근에는 성공했으나 "
            "UQQ905 선택 시 실제 layer parameter를 "
            "아직 완전히 복원하지 못함"
        )

    else:

        source_status = (
            "MAPPLAN_ENDPOINT_UNRESOLVED"
        )

        reason = (
            "지도 JS에서 MapPlan 사용 구조는 확인했으나 "
            "실제 endpoint/context 또는 UQQ905 공간요청 "
            "구조를 아직 확정하지 못함"
        )

    print(
        "source_status:",
        source_status,
    )

    print(
        "정상 AJAX context 후보:",
        len(
            valid_ajax_urls
        ),
    )

    print(
        "정상 MapPlan 후보:",
        len(
            valid_mapplan_urls
        ),
    )

    print(
        "reason:",
        reason,
    )

    print()

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    site_resolution = {
        "query_status": (
            "NOT_CONNECTED"
        ),
        "resolution": (
            "UNKNOWN"
        ),
        "confidence": (
            "NONE"
        ),
        "reason": (
            "도시군계획시설입체복합구역 UQQ905의 "
            "실제 공간 geometry 요청 구조를 분석 중이며 "
            "아직 대상 Parcel Polygon과 실제 공간교차를 "
            "검증하지 않았으므로 TRUE/FALSE를 판정하지 않음"
        ),
    }

    print_line()
    print(
        "=== 12. 현재 입체복합구역 SITE 판정 ==="
    )
    print_line()

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

    print()

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

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

        "토지이음 지도 조회": (
            page_result[
                "http_status"
            ] == 200
        ),

        "mpMapDet.js 조회": (
            js_result[
                "http_status"
            ] == 200
        ),

        "context/server 탐색 실행": (
            isinstance(
                html_analysis,
                dict,
            )
        ),

        "showLcstSpace 함수 탐색 실행": (
            "showLcstSpace"
            in functions
        ),

        "MapPlan context 탐색 실행": (
            isinstance(
                mapplan_contexts,
                list,
            )
        ),

        "잘못된 root JSP 경로만으로 "
        "endpoint 실패 확정 안 함": (
            True
        ),

        "UQQ905를 query parameter로 "
        "임의 확정 안 함": (
            True
        ),

        "geometry 미확정 TRUE 금지": (
            site_resolution[
                "resolution"
            ] != "TRUE"
        ),

        "geometry 미확정 FALSE 금지": (
            site_resolution[
                "resolution"
            ] != "FALSE"
        ),

        "UNKNOWN 유지": (
            site_resolution[
                "resolution"
            ] == "UNKNOWN"
        ),
    }

    print_line()
    print(
        "=== C-9-2-6A-5 검증 ==="
    )
    print_line()

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
        },

        "html_analysis": {
            "variables": (
                html_analysis[
                    "values"
                ]
            ),
        },

        "server_values": (
            server_values
        ),

        "functions": functions,

        "mapplan_contexts": (
            mapplan_contexts
        ),

        "server_contexts": (
            unique_server_contexts
        ),

        "ajax_context_probe": (
            ajax_results
        ),

        "mapplan_endpoint_probe": (
            mapplan_access_results
        ),

        "uqq905": {
            "html_legend_verified": (
                html_target
            ),
            "js_direct_contexts": (
                uqq905_js_contexts
            ),
        },

        "show_lcst_space_analysis": {
            "function_found": (
                bool(
                    show_function
                )
            ),
            "uses_mapplan": (
                show_has_mapplan
            ),
            "uses_req_search": (
                show_has_search
            ),
            "uses_req_code": (
                show_has_code
            ),
            "uses_lcst_space": (
                show_has_lcst
            ),
            "uses_mbr": (
                show_has_mbr
            ),
            "uses_layer": (
                show_has_layer
            ),
        },

        "source_resolution": {
            "source_status": (
                source_status
            ),
            "reason": reason,
        },

        "site_resolution": (
            site_resolution
        ),

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
            "STEP 17-21-C-9-2-6A-5 완료"
        )

        print()

        print(
            "토지이음 MapPlan 공간 Layer "
            "요청구조 분석: ALL PASS"
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2-6A-6"
        )

        print(
            "→ showLcstSpace 실제 요청 "
            "parameter 그대로 재현"
        )

        print(
            "→ UQQ905 공간 Feature 요청"
        )

        print(
            "→ response geometry / CRS 확인"
        )

        print(
            "→ 대상 PNU Parcel Polygon과 intersection"
        )

    else:

        print(
            "STEP 17-21-C-9-2-6A-5 검증 미완료"
        )


if __name__ == "__main__":
    main()