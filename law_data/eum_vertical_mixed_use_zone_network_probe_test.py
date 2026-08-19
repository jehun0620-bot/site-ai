import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-6A-3 "
    "토지이음 도시군계획시설입체복합구역 실제 Layer 요청 / Endpoint 추적"
)


# ============================================================
# 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

LAW_DATA_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DATA_DIR / "output"

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR / "site_spatial_query_context.json"
)

PREVIOUS_PROBE_PATH = (
    OUTPUT_DIR / "eum_vertical_mixed_use_zone_layer_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR / "eum_vertical_mixed_use_zone_network_probe.json"
)


# ============================================================
# 토지이음
# ============================================================

EUM_BASE_URL = "https://www.eum.go.kr"

MAP_PATH = "/web/mp/mpMapDet.jsp"

KNOWN_JS_PATHS = [
    "/web/js/mp/mpMapDet.js",
    "/web/js/mp/overlay.js",
    "/web/js/mp/ol.js",
    "/web/js/ux.js",
]


# ============================================================
# 대상 코드
# ============================================================

TARGET_NAME = "도시군계획시설입체복합구역"
TARGET_SHORT_NAME = "입체복합구역"

# A-2에서 실제 HTML class로 확인된 값
TARGET_LEGEND_CODE = "UQQ905"


# ============================================================
# HTTP
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.eum.go.kr/",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


# ============================================================
# 유틸
# ============================================================

def print_line():
    print("=" * 70)


def print_subline():
    print("-" * 70)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
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
    """
    여러 후보 경로 중 최초 유효값 반환.
    path는 tuple/list 형태.
    """

    for path in paths:

        current = data

        ok = True

        for key in path:

            if not isinstance(current, dict):
                ok = False
                break

            if key not in current:
                ok = False
                break

            current = current[key]

        if ok and current not in (None, ""):
            return current

    return None


def normalize_site_context(data):
    """
    site_spatial_query_context.json 구조 차이에 대응.
    """

    site_id = first_non_empty(
        data.get("site_id"),
        get_nested(
            data,
            ("site", "site_id"),
            ("query_context", "site_id"),
        ),
    )

    address = first_non_empty(
        data.get("address"),
        data.get("lot_address"),
        get_nested(
            data,
            ("site", "address"),
            ("site", "lot_address"),
            ("query_context", "address"),
        ),
    )

    pnu = first_non_empty(
        data.get("pnu"),
        data.get("PNU"),
        get_nested(
            data,
            ("site", "pnu"),
            ("query_context", "pnu"),
        ),
    )

    land_use_zone = first_non_empty(
        data.get("land_use_zone"),
        data.get("use_zone"),
        data.get("용도지역"),
        get_nested(
            data,
            ("site", "land_use_zone"),
            ("query_context", "land_use_zone"),
        ),
    )

    return {
        "site_id": site_id,
        "address": address,
        "pnu": pnu,
        "land_use_zone": land_use_zone,
    }


# ============================================================
# HTTP 조회
# ============================================================

def request_text(
    session: requests.Session,
    url: str,
    params=None,
    timeout=30,
):
    result = {
        "url": url,
        "params": params or {},
        "http_status": None,
        "content_type": None,
        "text": "",
        "error": None,
        "success": False,
    }

    try:

        response = session.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=timeout,
        )

        result["http_status"] = response.status_code

        result["content_type"] = response.headers.get(
            "Content-Type"
        )

        result["text"] = response.text

        result["success"] = response.status_code == 200

        return result

    except Exception as e:

        result["error"] = repr(e)

        return result


# ============================================================
# HTML script 추출
# ============================================================

def extract_script_urls(html: str):
    soup = BeautifulSoup(html, "html.parser")

    urls = []

    for tag in soup.find_all("script"):

        src = tag.get("src")

        if not src:
            continue

        src = src.strip()

        if not src:
            continue

        absolute = urljoin(
            EUM_BASE_URL,
            src,
        )

        if absolute not in urls:
            urls.append(absolute)

    return urls


def extract_inline_scripts(html: str):
    soup = BeautifulSoup(html, "html.parser")

    scripts = []

    for index, tag in enumerate(
        soup.find_all("script"),
        start=1,
    ):

        if tag.get("src"):
            continue

        text = tag.get_text(
            "\n",
            strip=False,
        )

        if not text.strip():
            continue

        scripts.append(
            {
                "index": index,
                "text": text,
            }
        )

    return scripts


# ============================================================
# 코드 context
# ============================================================

def extract_contexts(
    text: str,
    keyword: str,
    radius=500,
    max_count=30,
):
    result = []

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

        context = text[left:right]

        result.append(context)

        start = idx + len(keyword)

        if len(result) >= max_count:
            break

    return result


# ============================================================
# URL / Endpoint 추출
# ============================================================

ENDPOINT_PATTERNS = [
    # 문자열 안의 JSP
    r"""["']([^"'<>]+\.jsp(?:\?[^"'<>]*)?)["']""",

    # 문자열 안의 JSON
    r"""["']([^"'<>]+\.json(?:\?[^"'<>]*)?)["']""",

    # ajax url:
    r"""url\s*:\s*["']([^"']+)["']""",

    # fetch(...)
    r"""fetch\s*\(\s*["']([^"']+)["']""",

    # open("GET", ...)
    r"""open\s*\(\s*["'](?:GET|POST)["']\s*,\s*["']([^"']+)["']""",
]


def extract_endpoint_candidates(text: str):
    results = []

    for pattern in ENDPOINT_PATTERNS:

        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):

            candidate = safe_text(
                match.group(1)
            )

            if not candidate:
                continue

            if candidate.startswith(
                (
                    "javascript:",
                    "#",
                )
            ):
                continue

            if candidate not in results:
                results.append(candidate)

    return results


# ============================================================
# GIS 관련 키워드
# ============================================================

GIS_KEYWORDS = [
    "UQQ905",
    "typeAC_",
    "typeMiniAC_",
    "gisMapLayer",
    "layer",
    "Layer",
    "WMS",
    "wms",
    "WFS",
    "wfs",
    "GetFeature",
    "GetMap",
    "geom",
    "geometry",
    "polygon",
    "Polygon",
    "feature",
    "Feature",
    "ajax",
    "$.ajax",
    "XMLHttpRequest",
    "fetch(",
    "MapPlan",
    "KRAS",
    "land",
    "pnu",
]


def keyword_hits(text: str):
    hits = []

    for keyword in GIS_KEYWORDS:

        count = text.count(keyword)

        if count > 0:

            hits.append(
                {
                    "keyword": keyword,
                    "count": count,
                }
            )

    return hits


# ============================================================
# Parameter 후보 추출
# ============================================================

PARAMETER_PATTERNS = [
    r"""["']([A-Za-z][A-Za-z0-9_]{1,40})["']\s*:""",
    r"""data\s*:\s*\{([^{}]{0,3000})\}""",
    r"""params?\s*:\s*\{([^{}]{0,3000})\}""",
]


IMPORTANT_PARAMETER_NAMES = {
    "pnu",
    "layer",
    "layerId",
    "layer_id",
    "type",
    "code",
    "landCode",
    "regionCode",
    "zoneCode",
    "jimok",
    "service",
    "request",
    "typename",
    "typeName",
    "layers",
    "bbox",
    "srs",
    "srsName",
    "geometry",
    "geom",
    "filter",
    "mapType",
    "jType",
}


def extract_parameter_candidates(text: str):
    names = set()

    for match in re.finditer(
        PARAMETER_PATTERNS[0],
        text,
    ):

        name = match.group(1)

        if name:
            names.add(name)

    important = sorted(
        name
        for name in names
        if (
            name in IMPORTANT_PARAMETER_NAMES
            or "layer" in name.lower()
            or "code" in name.lower()
            or "geom" in name.lower()
            or "map" in name.lower()
            or "pnu" in name.lower()
        )
    )

    return important


# ============================================================
# UQQ905 주변 구조 분석
# ============================================================

def analyze_target_code(text: str):
    contexts = extract_contexts(
        text,
        TARGET_LEGEND_CODE,
        radius=800,
        max_count=50,
    )

    endpoint_near_target = []

    for context in contexts:

        eps = extract_endpoint_candidates(
            context
        )

        for ep in eps:

            if ep not in endpoint_near_target:
                endpoint_near_target.append(ep)

    return {
        "present": bool(contexts),
        "context_count": len(contexts),
        "contexts": contexts,
        "endpoint_candidates": endpoint_near_target,
    }


# ============================================================
# JS 분석
# ============================================================

def analyze_js_source(
    label: str,
    url: str,
    text: str,
):
    target = analyze_target_code(
        text
    )

    endpoints = extract_endpoint_candidates(
        text
    )

    params = extract_parameter_candidates(
        text
    )

    hits = keyword_hits(
        text
    )

    return {
        "label": label,
        "url": url,
        "size": len(text.encode("utf-8", errors="ignore")),
        "target_code_present": target["present"],
        "target_context_count": target["context_count"],
        "target_contexts": target["contexts"],
        "target_endpoint_candidates": target[
            "endpoint_candidates"
        ],
        "endpoint_candidates": endpoints,
        "parameter_candidates": params,
        "keyword_hits": hits,
    }


# ============================================================
# endpoint scoring
# ============================================================

def score_endpoint(endpoint: str):
    lower = endpoint.lower()

    score = 0
    reasons = []

    if ".jsp" in lower:
        score += 5
        reasons.append("JSP_ENDPOINT")

    if "map" in lower:
        score += 15
        reasons.append("MAP")

    if "layer" in lower:
        score += 20
        reasons.append("LAYER")

    if "gis" in lower:
        score += 20
        reasons.append("GIS")

    if "space" in lower:
        score += 15
        reasons.append("SPACE")

    if "zone" in lower:
        score += 10
        reasons.append("ZONE")

    if "land" in lower:
        score += 10
        reasons.append("LAND")

    if "ajax" in lower:
        score += 5
        reasons.append("AJAX")

    if "get" in lower:
        score += 2
        reasons.append("GET")

    return score, reasons


def rank_endpoints(endpoint_sources):
    combined = {}

    for source_name, endpoints in endpoint_sources:

        for endpoint in endpoints:

            absolute = urljoin(
                EUM_BASE_URL,
                endpoint,
            )

            if absolute not in combined:

                score, reasons = score_endpoint(
                    absolute
                )

                combined[absolute] = {
                    "endpoint": absolute,
                    "score": score,
                    "score_reasons": reasons,
                    "sources": [],
                }

            combined[absolute]["sources"].append(
                source_name
            )

    result = list(
        combined.values()
    )

    result.sort(
        key=lambda x: (
            -x["score"],
            x["endpoint"],
        )
    )

    return result


# ============================================================
# main
# ============================================================

def main():

    print(f"=== {STEP_NAME} ===")
    print()

    # --------------------------------------------------------
    # 입력
    # --------------------------------------------------------

    if not QUERY_CONTEXT_PATH.exists():
        raise FileNotFoundError(
            f"Query Context 파일이 없습니다.\n{QUERY_CONTEXT_PATH}"
        )

    query_context_raw = load_json(
        QUERY_CONTEXT_PATH
    )

    site = normalize_site_context(
        query_context_raw
    )

    previous_probe = None

    if PREVIOUS_PROBE_PATH.exists():

        previous_probe = load_json(
            PREVIOUS_PROBE_PATH
        )

    site_id = site["site_id"]
    address = site["address"]
    pnu = site["pnu"]

    print_line()
    print("=== 대상 SITE ===")
    print_line()

    print(f"SITE ID: {site_id or '-'}")
    print(f"주소: {address or '-'}")
    print(f"PNU: {pnu or '-'}")
    print()

    if len(pnu) != 19:
        raise RuntimeError(
            "PNU가 19자리가 아닙니다."
        )

    # --------------------------------------------------------
    # A-2 검증
    # --------------------------------------------------------

    print_line()
    print("=== 1. 이전 A-2 결과 확인 ===")
    print_line()

    previous_term_present = False

    if isinstance(previous_probe, dict):

        previous_term_present = bool(
            previous_probe.get("term_present")
            or previous_probe.get(
                "target_term_present"
            )
            or (
                TARGET_NAME
                in json.dumps(
                    previous_probe,
                    ensure_ascii=False,
                )
            )
        )

    print(
        "A-2 토지이음 명칭 확인:",
        previous_term_present,
    )

    print(
        "추적 대상 코드:",
        TARGET_LEGEND_CODE,
    )

    print()

    # --------------------------------------------------------
    # session
    # --------------------------------------------------------

    session = requests.Session()

    # --------------------------------------------------------
    # 지도 HTML
    # --------------------------------------------------------

    print_line()
    print("=== 2. 토지이음 지도 HTML 재조회 ===")
    print_line()

    map_url = urljoin(
        EUM_BASE_URL,
        MAP_PATH,
    )

    map_result = request_text(
        session,
        map_url,
        params={
            "add": "land",
            "pnu": pnu,
        },
    )

    print(
        "HTTP:",
        map_result["http_status"],
    )

    print(
        "Content-Type:",
        map_result["content_type"],
    )

    print(
        "HTML bytes:",
        len(
            map_result["text"].encode(
                "utf-8",
                errors="ignore",
            )
        ),
    )

    if not map_result["success"]:

        raise RuntimeError(
            "토지이음 지도 HTML 조회 실패"
        )

    html = map_result["text"]

    print(
        f"{TARGET_LEGEND_CODE} 존재:",
        TARGET_LEGEND_CODE in html,
    )

    print(
        f"{TARGET_NAME} 존재:",
        TARGET_NAME in html,
    )

    print()

    # --------------------------------------------------------
    # script 목록
    # --------------------------------------------------------

    print_line()
    print("=== 3. 지도 JavaScript Source 목록 ===")
    print_line()

    script_urls = extract_script_urls(
        html
    )

    # 이미 알려진 JS도 누락 방지
    for path in KNOWN_JS_PATHS:

        url = urljoin(
            EUM_BASE_URL,
            path,
        )

        if url not in script_urls:
            script_urls.append(url)

    print(
        "외부 script 후보 수:",
        len(script_urls),
    )

    for index, url in enumerate(
        script_urls,
        start=1,
    ):
        print(
            f"{index}. {url}"
        )

    print()

    # --------------------------------------------------------
    # inline script
    # --------------------------------------------------------

    print_line()
    print("=== 4. Inline JavaScript 분석 ===")
    print_line()

    inline_scripts = extract_inline_scripts(
        html
    )

    print(
        "inline script 수:",
        len(inline_scripts),
    )

    inline_analysis = []

    for script in inline_scripts:

        text = script["text"]

        if (
            TARGET_LEGEND_CODE not in text
            and TARGET_NAME not in text
            and "gisMapLayer" not in text
            and "$.ajax" not in text
        ):
            continue

        analysis = analyze_js_source(
            label=f"INLINE_{script['index']}",
            url=map_result["url"],
            text=text,
        )

        inline_analysis.append(
            analysis
        )

        print_subline()
        print(
            "script:",
            analysis["label"],
        )

        print(
            "size:",
            analysis["size"],
        )

        print(
            f"{TARGET_LEGEND_CODE} present:",
            analysis["target_code_present"],
        )

        print(
            "target contexts:",
            analysis["target_context_count"],
        )

        print(
            "endpoint candidates:",
            len(
                analysis[
                    "endpoint_candidates"
                ]
            ),
        )

    print()

    # --------------------------------------------------------
    # 외부 JS 실제 조회
    # --------------------------------------------------------

    print_line()
    print("=== 5. 외부 JavaScript 실제 조회 / 분석 ===")
    print_line()

    js_results = []

    for index, js_url in enumerate(
        script_urls,
        start=1,
    ):

        print_subline()
        print(
            f"[{index}] {js_url}"
        )

        js_http = request_text(
            session,
            js_url,
        )

        print(
            "HTTP:",
            js_http["http_status"],
        )

        if js_http["error"]:
            print(
                "error:",
                js_http["error"],
            )

        if not js_http["success"]:
            continue

        js_text = js_http["text"]

        analysis = analyze_js_source(
            label=Path(
                urlparse(js_url).path
            ).name,
            url=js_url,
            text=js_text,
        )

        js_results.append(
            analysis
        )

        print(
            "size:",
            analysis["size"],
        )

        print(
            f"{TARGET_LEGEND_CODE} present:",
            analysis["target_code_present"],
        )

        print(
            "target contexts:",
            analysis["target_context_count"],
        )

        print(
            "endpoint candidates:",
            len(
                analysis[
                    "endpoint_candidates"
                ]
            ),
        )

        if analysis[
            "parameter_candidates"
        ]:

            print(
                "parameter candidates:",
                ", ".join(
                    analysis[
                        "parameter_candidates"
                    ][
                        :30
                    ]
                ),
            )

        # UQQ905 주변 문맥
        contexts = analysis[
            "target_contexts"
        ]

        for c_index, context in enumerate(
            contexts[:5],
            start=1,
        ):

            print()
            print(
                f"  UQQ905 Context {c_index}"
            )

            clean = re.sub(
                r"\s+",
                " ",
                context,
            )

            print(
                " ",
                clean[:1800],
            )

    print()

    # --------------------------------------------------------
    # 전체 endpoint 후보 통합
    # --------------------------------------------------------

    print_line()
    print("=== 6. GIS / Layer Endpoint 후보 통합 ===")
    print_line()

    endpoint_sources = []

    # HTML 자체
    html_endpoints = extract_endpoint_candidates(
        html
    )

    endpoint_sources.append(
        (
            "MAP_HTML",
            html_endpoints,
        )
    )

    # inline
    for analysis in inline_analysis:

        endpoint_sources.append(
            (
                analysis["label"],
                analysis[
                    "endpoint_candidates"
                ],
            )
        )

    # external JS
    for analysis in js_results:

        endpoint_sources.append(
            (
                analysis["label"],
                analysis[
                    "endpoint_candidates"
                ],
            )
        )

    ranked_endpoints = rank_endpoints(
        endpoint_sources
    )

    print(
        "통합 endpoint 후보 수:",
        len(ranked_endpoints),
    )

    for index, item in enumerate(
        ranked_endpoints[:80],
        start=1,
    ):

        print_subline()

        print(
            f"{index}. {item['endpoint']}"
        )

        print(
            "score:",
            item["score"],
        )

        print(
            "score reason:",
            ", ".join(
                item["score_reasons"]
            )
            or "-",
        )

        print(
            "source:",
            ", ".join(
                sorted(
                    set(
                        item["sources"]
                    )
                )
            ),
        )

    print()

    # --------------------------------------------------------
    # UQQ905 직접 참조 source
    # --------------------------------------------------------

    print_line()
    print("=== 7. UQQ905 직접 참조 JavaScript ===")
    print_line()

    direct_sources = []

    for analysis in (
        inline_analysis
        + js_results
    ):

        if analysis[
            "target_code_present"
        ]:

            direct_sources.append(
                analysis
            )

    print(
        "UQQ905 직접 참조 source 수:",
        len(direct_sources),
    )

    for source in direct_sources:

        print_subline()

        print(
            "source:",
            source["label"],
        )

        print(
            "URL:",
            source["url"],
        )

        print(
            "context 수:",
            source[
                "target_context_count"
            ],
        )

        nearby = source[
            "target_endpoint_candidates"
        ]

        print(
            "주변 endpoint 후보:",
            len(nearby),
        )

        for endpoint in nearby[:20]:
            print(
                f"  - {endpoint}"
            )

    print()

    # --------------------------------------------------------
    # 판정
    # --------------------------------------------------------

    print_line()
    print("=== 8. 입체복합구역 Layer 연결 가능성 판정 ===")
    print_line()

    target_code_verified = (
        TARGET_LEGEND_CODE in html
        and TARGET_NAME in html
    )

    direct_js_reference = bool(
        direct_sources
    )

    relevant_endpoint_found = any(
        item["score"] >= 20
        for item in ranked_endpoints
    )

    if (
        target_code_verified
        and direct_js_reference
        and relevant_endpoint_found
    ):

        source_status = (
            "LEGEND_CODE_VERIFIED_"
            "NETWORK_TRACE_CANDIDATE_FOUND"
        )

        reason = (
            "토지이음 지도 HTML에서 "
            "도시군계획시설입체복합구역과 "
            "UQQ905의 직접 연결을 재확인했고, "
            "관련 JavaScript 및 GIS/Layer endpoint 후보를 "
            "추출함. 다만 실제 endpoint에 UQQ905를 전달하여 "
            "geometry Feature가 반환되는 것까지 검증하기 전에는 "
            "공간 source로 최종 확정하지 않음"
        )

    elif target_code_verified:

        source_status = (
            "LEGEND_CODE_VERIFIED_"
            "ENDPOINT_UNRESOLVED"
        )

        reason = (
            "토지이음 지도 HTML에서 "
            "도시군계획시설입체복합구역과 "
            "UQQ905 연결은 확인했으나 "
            "실제 geometry 조회 endpoint까지는 "
            "확정하지 못함"
        )

    else:

        source_status = (
            "TARGET_CODE_UNRESOLVED"
        )

        reason = (
            "토지이음 지도에서 "
            "도시군계획시설입체복합구역과 "
            "UQQ905의 연결을 재확인하지 못함"
        )

    print(
        "source_status:",
        source_status,
    )

    print(
        "target name:",
        TARGET_NAME,
    )

    print(
        "legend / classification code:",
        TARGET_LEGEND_CODE
        if target_code_verified
        else "미확정",
    )

    print(
        "direct JS reference:",
        direct_js_reference,
    )

    print(
        "network endpoint candidate:",
        relevant_endpoint_found,
    )

    print(
        "reason:",
        reason,
    )

    print()

    # --------------------------------------------------------
    # SITE 판정
    # --------------------------------------------------------

    print_line()
    print("=== 9. 현재 입체복합구역 SITE 판정 ===")
    print_line()

    site_resolution = {
        "query_status": "NOT_CONNECTED",
        "resolution": "UNKNOWN",
        "confidence": "NONE",
        "reason": (
            "토지이음에서 도시군계획시설입체복합구역 "
            "분류코드 UQQ905의 화면상 연결은 확인했으나 "
            "실제 공간 geometry endpoint 및 대상 Parcel과의 "
            "공간교차를 아직 검증하지 않았으므로 "
            "TRUE/FALSE를 판정하지 않음"
        ),
    }

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
    # 검증
    # --------------------------------------------------------

    checks = {
        "SITE 주소 존재": bool(
            address
        ),

        "PNU 19자리": (
            len(pnu) == 19
            and pnu.isdigit()
        ),

        "토지이음 지도 조회 성공": (
            map_result[
                "http_status"
            ]
            == 200
        ),

        "도시군계획시설입체복합구역 명칭 확인": (
            TARGET_NAME
            in html
        ),

        "UQQ905 HTML 확인": (
            TARGET_LEGEND_CODE
            in html
        ),

        "JS source 실제 조회 실행": (
            len(
                js_results
            )
            > 0
        ),

        "endpoint 후보 추출 실행": (
            isinstance(
                ranked_endpoints,
                list,
            )
        ),

        "UQQ905를 geometry 코드로 자동확정 안 함": (
            site_resolution[
                "resolution"
            ]
            == "UNKNOWN"
        ),

        "geometry 미확정 TRUE 금지": (
            site_resolution[
                "resolution"
            ]
            != "TRUE"
        ),

        "geometry 미확정 FALSE 금지": (
            site_resolution[
                "resolution"
            ]
            != "FALSE"
        ),

        "SITE UNKNOWN 유지": (
            site_resolution[
                "resolution"
            ]
            == "UNKNOWN"
        ),
    }

    print_line()
    print("=== C-9-2-6A-3 검증 ===")
    print_line()

    for name, passed in checks.items():

        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    # --------------------------------------------------------
    # 출력 JSON
    # --------------------------------------------------------

    output = {
        "step": STEP_NAME,

        "site": {
            "site_id": site_id,
            "address": address,
            "pnu": pnu,
        },

        "target": {
            "name": TARGET_NAME,
            "short_name": TARGET_SHORT_NAME,
            "legend_code": TARGET_LEGEND_CODE,
        },

        "map_request": {
            "url": map_result["url"],
            "params": {
                "add": "land",
                "pnu": pnu,
            },
            "http_status": map_result[
                "http_status"
            ],
            "content_type": map_result[
                "content_type"
            ],
            "html_bytes": len(
                html.encode(
                    "utf-8",
                    errors="ignore",
                )
            ),
        },

        "html_verification": {
            "target_name_present": (
                TARGET_NAME
                in html
            ),
            "target_code_present": (
                TARGET_LEGEND_CODE
                in html
            ),
        },

        "script_urls": script_urls,

        "inline_analysis": inline_analysis,

        "external_js_analysis": js_results,

        "ranked_endpoint_candidates": (
            ranked_endpoints
        ),

        "direct_target_sources": [
            {
                "label": item[
                    "label"
                ],
                "url": item[
                    "url"
                ],
                "context_count": item[
                    "target_context_count"
                ],
                "target_endpoint_candidates": (
                    item[
                        "target_endpoint_candidates"
                    ]
                ),
            }
            for item
            in direct_sources
        ],

        "source_resolution": {
            "source_status": (
                source_status
            ),
            "target_code_verified": (
                target_code_verified
            ),
            "direct_js_reference": (
                direct_js_reference
            ),
            "relevant_endpoint_found": (
                relevant_endpoint_found
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

    all_pass = all(
        checks.values()
    )

    if all_pass:

        print(
            "STEP 17-21-C-9-2-6A-3 완료"
        )

        print()

        print(
            "토지이음 UQQ905 / "
            "실제 Layer 요청 추적 프레임: ALL PASS"
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2-6A-4"
        )

        print(
            "→ UQQ905를 사용하는 실제 "
            "GIS endpoint 요청 구조 분석"
        )

        print(
            "→ endpoint parameter / "
            "response schema 검증"
        )

        print(
            "→ UQQ905 Feature geometry 확보"
        )

        print(
            "→ 대상 PNU Parcel Polygon과 intersection"
        )

        print(
            "→ 실제 교차 확인 시 TRUE"
        )

        print(
            "→ 전체 대상 layer 정상조회 + "
            "교차 없음 확인 시 FALSE"
        )

    else:

        print(
            "STEP 17-21-C-9-2-6A-3 검증 미완료"
        )

        print()

        print(
            "실패 항목을 확인하십시오."
        )


if __name__ == "__main__":
    main()