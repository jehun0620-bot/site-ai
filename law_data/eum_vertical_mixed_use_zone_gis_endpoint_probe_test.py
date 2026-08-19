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
    "STEP 17-21-C-9-2-6A-4 "
    "토지이음 GIS Endpoint 요청 Parameter / 응답 Schema 분석"
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

NETWORK_PROBE_PATH = (
    OUTPUT_DIR / "eum_vertical_mixed_use_zone_network_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR / "eum_vertical_mixed_use_zone_gis_endpoint_probe.json"
)


# ============================================================
# 토지이음
# ============================================================

EUM_BASE_URL = "https://www.eum.go.kr"

MAP_URL = (
    EUM_BASE_URL
    + "/web/mp/mpMapDet.jsp"
)

MP_MAP_JS_URL = (
    EUM_BASE_URL
    + "/web/js/mp/mpMapDet.js"
)

TARGET_ENDPOINT = (
    EUM_BASE_URL
    + "/mp/mpMapDetGisAjaxXml.jsp"
)


# ============================================================
# 대상
# ============================================================

TARGET_NAME = "도시군계획시설입체복합구역"
TARGET_CODE = "UQQ905"


# ============================================================
# HTTP
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": (
        "https://www.eum.go.kr/"
        "web/mp/mpMapDet.jsp"
    ),
}


# ============================================================
# 유틸
# ============================================================

def print_line():
    print("=" * 70)


def print_subline():
    print("-" * 70)


def load_json(path: Path):
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
        ok = True

        for key in path:

            if not isinstance(
                current,
                dict,
            ):
                ok = False
                break

            if key not in current:
                ok = False
                break

            current = current[key]

        if (
            ok
            and current
            not in (
                None,
                "",
            )
        ):
            return current

    return None


def normalize_site_context(data):

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

    return {
        "site_id": site_id,
        "address": address,
        "pnu": pnu,
    }


# ============================================================
# HTTP
# ============================================================

def request_text(
    session,
    url,
    method="GET",
    params=None,
    data=None,
    timeout=30,
):

    result = {
        "method": method,
        "url": url,
        "params": params or {},
        "data": data or {},
        "http_status": None,
        "content_type": None,
        "text": "",
        "error": None,
        "success": False,
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

        result["success"] = (
            response.status_code == 200
        )

    except Exception as e:

        result["error"] = repr(e)

    return result


# ============================================================
# JS endpoint 호출부 추출
# ============================================================

def extract_call_contexts(
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


def compact_text(text):
    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


# ============================================================
# AJAX block 분석
# ============================================================

def extract_ajax_blocks(text):
    """
    $.ajax({...}) 주변 block을 단순 추출.
    JS parser 없이 분석용으로만 사용.
    """

    blocks = []

    patterns = [
        r"\$\.ajax\s*\(",
        r"jQuery\.ajax\s*\(",
        r"\.ajax\s*\(",
    ]

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):

            start = match.start()

            left = max(
                0,
                start - 1200,
            )

            right = min(
                len(text),
                start + 5000,
            )

            block = text[
                left:right
            ]

            if block not in blocks:
                blocks.append(
                    block
                )

    return blocks


def find_endpoint_ajax_blocks(
    text,
    endpoint_name,
):
    result = []

    for block in extract_ajax_blocks(
        text
    ):

        if endpoint_name in block:

            result.append(
                block
            )

    return result


# ============================================================
# parameter 후보 추출
# ============================================================

def extract_object_keys(text):
    """
    JS object key 추출.
    """

    patterns = [
        r"""["']([A-Za-z0-9_]+)["']\s*:""",
        r"""(?<![\w$])([A-Za-z_$][A-Za-z0-9_$]*)\s*:""",
    ]

    keys = []

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text,
        ):

            key = match.group(1)

            if key not in keys:
                keys.append(
                    key
                )

    return keys


def extract_assignments(text):
    """
    변수 = 값 패턴을 분석용으로 수집.
    """

    results = []

    pattern = (
        r"(?<![\w$])"
        r"([A-Za-z_$][A-Za-z0-9_$]*)"
        r"\s*=\s*"
        r"([^;\n]{1,300})"
    )

    for match in re.finditer(
        pattern,
        text,
    ):

        name = match.group(1)

        value = (
            match.group(2)
            .strip()
        )

        results.append(
            {
                "name": name,
                "value": value,
            }
        )

    return results


# ============================================================
# HTML에서 UQQ905 DOM 구조
# ============================================================

def analyze_target_dom(html):

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    matched = []

    for tag in soup.find_all(
        True
    ):

        classes = (
            tag.get("class")
            or []
        )

        title = safe_text(
            tag.get("title")
        )

        text = safe_text(
            tag.get_text(
                " ",
                strip=True,
            )
        )

        class_text = " ".join(
            classes
        )

        if (
            TARGET_CODE
            in class_text
            or TARGET_NAME
            == title
        ):

            matched.append(
                {
                    "tag": tag.name,
                    "class": classes,
                    "title": title,
                    "text": text,
                    "attrs": {
                        k: v
                        for k, v
                        in tag.attrs.items()
                    },
                }
            )

    return matched


# ============================================================
# endpoint response 분류
# ============================================================

def classify_response(result):

    if not result["success"]:

        return {
            "classification": (
                "HTTP_OR_NETWORK_ERROR"
            ),
            "is_xml": False,
            "is_json": False,
            "has_target_code": False,
            "has_target_name": False,
            "length": len(
                result["text"]
            ),
        }

    text = (
        result["text"]
        or ""
    )

    stripped = (
        text.strip()
    )

    is_xml = (
        stripped.startswith("<")
        or "xml" in safe_text(
            result["content_type"]
        ).lower()
    )

    is_json = (
        stripped.startswith("{")
        or stripped.startswith("[")
        or "json" in safe_text(
            result["content_type"]
        ).lower()
    )

    target_code = (
        TARGET_CODE
        in text
    )

    target_name = (
        TARGET_NAME
        in text
    )

    # JSP HTML 오류페이지 방어
    html_error = bool(
        re.search(
            r"<html|<body|Exception|오류|error",
            text,
            flags=re.IGNORECASE,
        )
    )

    if target_code or target_name:

        classification = (
            "TARGET_REFERENCE_FOUND"
        )

    elif (
        is_xml
        and not html_error
    ):

        classification = (
            "XML_RESPONSE"
        )

    elif (
        is_json
        and not html_error
    ):

        classification = (
            "JSON_RESPONSE"
        )

    elif html_error:

        classification = (
            "HTML_OR_ERROR_RESPONSE"
        )

    elif not stripped:

        classification = (
            "EMPTY_RESPONSE"
        )

    else:

        classification = (
            "UNCLASSIFIED_RESPONSE"
        )

    return {
        "classification": (
            classification
        ),
        "is_xml": is_xml,
        "is_json": is_json,
        "has_target_code": (
            target_code
        ),
        "has_target_name": (
            target_name
        ),
        "length": len(text),
    }


# ============================================================
# 안전한 probe
# ============================================================

def build_safe_probes(pnu):
    """
    여기서는 파라미터를 '확정'하지 않는다.

    endpoint가 GET/POST 중 무엇을 받는지,
    최소 parameter 조합에서 어떤 응답이 오는지만 확인한다.
    """

    return [
        {
            "name": "GET_EMPTY",
            "method": "GET",
            "params": {},
            "data": {},
        },

        {
            "name": "POST_EMPTY",
            "method": "POST",
            "params": {},
            "data": {},
        },

        {
            "name": "GET_PNU",
            "method": "GET",
            "params": {
                "pnu": pnu,
            },
            "data": {},
        },

        {
            "name": "POST_PNU",
            "method": "POST",
            "params": {},
            "data": {
                "pnu": pnu,
            },
        },

        {
            "name": "GET_PNU_CODE",
            "method": "GET",
            "params": {
                "pnu": pnu,
                "code": TARGET_CODE,
            },
            "data": {},
        },

        {
            "name": "POST_PNU_CODE",
            "method": "POST",
            "params": {},
            "data": {
                "pnu": pnu,
                "code": TARGET_CODE,
            },
        },

        {
            "name": "GET_PNU_LAYER",
            "method": "GET",
            "params": {
                "pnu": pnu,
                "layer": TARGET_CODE,
            },
            "data": {},
        },

        {
            "name": "POST_PNU_LAYER",
            "method": "POST",
            "params": {},
            "data": {
                "pnu": pnu,
                "layer": TARGET_CODE,
            },
        },
    ]


# ============================================================
# main
# ============================================================

def main():

    print(
        f"=== {STEP_NAME} ==="
    )

    print()

    # --------------------------------------------------------
    # 입력
    # --------------------------------------------------------

    if not QUERY_CONTEXT_PATH.exists():
        raise FileNotFoundError(
            QUERY_CONTEXT_PATH
        )

    context_raw = load_json(
        QUERY_CONTEXT_PATH
    )

    site = normalize_site_context(
        context_raw
    )

    pnu = site["pnu"]

    print_line()
    print("=== 대상 SITE ===")
    print_line()

    print(
        f"SITE ID: "
        f"{site['site_id'] or '-'}"
    )

    print(
        f"주소: "
        f"{site['address'] or '-'}"
    )

    print(
        f"PNU: "
        f"{pnu or '-'}"
    )

    print()

    if (
        len(pnu) != 19
        or not pnu.isdigit()
    ):
        raise RuntimeError(
            "PNU가 올바른 19자리 숫자가 아닙니다."
        )

    # --------------------------------------------------------
    # A-3 결과
    # --------------------------------------------------------

    print_line()
    print(
        "=== 1. A-3 Network Probe 결과 확인 ==="
    )
    print_line()

    network_probe = None

    if NETWORK_PROBE_PATH.exists():

        network_probe = load_json(
            NETWORK_PROBE_PATH
        )

    endpoint_verified_from_probe = False

    if isinstance(
        network_probe,
        dict,
    ):

        endpoints = (
            network_probe.get(
                "ranked_endpoint_candidates"
            )
            or []
        )

        for item in endpoints:

            endpoint = safe_text(
                item.get("endpoint")
            )

            if (
                "mpMapDetGisAjaxXml.jsp"
                in endpoint
            ):

                endpoint_verified_from_probe = True
                break

    print(
        "A-3 GIS endpoint 후보 확인:",
        endpoint_verified_from_probe,
    )

    print(
        "분석 endpoint:",
        TARGET_ENDPOINT,
    )

    print()

    # --------------------------------------------------------
    # session + 페이지 priming
    # --------------------------------------------------------

    session = requests.Session()

    print_line()
    print(
        "=== 2. 토지이음 지도 Session 초기화 ==="
    )
    print_line()

    map_result = request_text(
        session,
        MAP_URL,
        method="GET",
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
        map_result[
            "content_type"
        ],
    )

    print(
        "HTML bytes:",
        len(
            map_result["text"]
            .encode(
                "utf-8",
                errors="ignore",
            )
        ),
    )

    if not map_result["success"]:
        raise RuntimeError(
            "토지이음 지도 session 초기화 실패"
        )

    print()

    # --------------------------------------------------------
    # DOM 확인
    # --------------------------------------------------------

    print_line()
    print(
        "=== 3. UQQ905 DOM 구조 재검증 ==="
    )
    print_line()

    target_dom = analyze_target_dom(
        map_result["text"]
    )

    print(
        "UQQ905 관련 DOM 수:",
        len(target_dom),
    )

    for index, item in enumerate(
        target_dom[:10],
        start=1,
    ):

        print_subline()

        print(
            f"Element {index}"
        )

        print(
            "tag:",
            item["tag"],
        )

        print(
            "class:",
            item["class"],
        )

        print(
            "title:",
            item["title"],
        )

        print(
            "text:",
            item["text"][:500],
        )

    print()

    # --------------------------------------------------------
    # mpMapDet.js 조회
    # --------------------------------------------------------

    print_line()
    print(
        "=== 4. mpMapDet.js GIS Endpoint 호출부 분석 ==="
    )
    print_line()

    js_result = request_text(
        session,
        MP_MAP_JS_URL,
    )

    print(
        "HTTP:",
        js_result["http_status"],
    )

    print(
        "Content-Type:",
        js_result[
            "content_type"
        ],
    )

    print(
        "JS bytes:",
        len(
            js_result["text"]
            .encode(
                "utf-8",
                errors="ignore",
            )
        ),
    )

    if not js_result["success"]:
        raise RuntimeError(
            "mpMapDet.js 조회 실패"
        )

    js_text = js_result["text"]

    endpoint_name = (
        "mpMapDetGisAjaxXml.jsp"
    )

    endpoint_contexts = (
        extract_call_contexts(
            js_text,
            endpoint_name,
        )
    )

    print(
        "endpoint context 수:",
        len(endpoint_contexts),
    )

    for index, context in enumerate(
        endpoint_contexts,
        start=1,
    ):

        print_subline()

        print(
            f"Context {index}"
        )

        print(
            compact_text(
                context
            )[:6000]
        )

    print()

    # --------------------------------------------------------
    # AJAX block
    # --------------------------------------------------------

    print_line()
    print(
        "=== 5. mpMapDetGisAjaxXml.jsp AJAX Block 분석 ==="
    )
    print_line()

    ajax_blocks = (
        find_endpoint_ajax_blocks(
            js_text,
            endpoint_name,
        )
    )

    print(
        "AJAX block 수:",
        len(ajax_blocks),
    )

    ajax_analysis = []

    for index, block in enumerate(
        ajax_blocks,
        start=1,
    ):

        keys = extract_object_keys(
            block
        )

        assignments = extract_assignments(
            block
        )

        info = {
            "index": index,
            "keys": keys,
            "assignments": (
                assignments
            ),
            "text": block,
        }

        ajax_analysis.append(
            info
        )

        print_subline()

        print(
            f"AJAX Block {index}"
        )

        print(
            "Object key 후보:"
        )

        for key in keys[:100]:
            print(
                f"  - {key}"
            )

        print()

        print(
            "주요 assignment:"
        )

        for assignment in (
            assignments[:80]
        ):

            name = assignment[
                "name"
            ]

            value = assignment[
                "value"
            ]

            if (
                "pnu"
                in name.lower()
                or "layer"
                in name.lower()
                or "code"
                in name.lower()
                or "gis"
                in name.lower()
                or "map"
                in name.lower()
                or "type"
                in name.lower()
            ):

                print(
                    f"  {name} = "
                    f"{value[:500]}"
                )

    print()

    # --------------------------------------------------------
    # target 관련 키워드 주변 문맥
    # --------------------------------------------------------

    print_line()
    print(
        "=== 6. Layer / LAYER / code / pnu 호출 문맥 ==="
    )
    print_line()

    keyword_context_output = {}

    keywords = [
        "LAYER",
        "layer",
        "code",
        "pnu",
        "markerPnu",
        "mpMapDetGisAjaxXml.jsp",
    ]

    for keyword in keywords:

        contexts = extract_call_contexts(
            js_text,
            keyword,
            radius=1000,
        )

        keyword_context_output[
            keyword
        ] = contexts[:20]

        print_subline()

        print(
            f"keyword: {keyword}"
        )

        print(
            "context 수:",
            len(contexts),
        )

        for index, context in enumerate(
            contexts[:5],
            start=1,
        ):

            print()

            print(
                f"  Context {index}"
            )

            print(
                " ",
                compact_text(
                    context
                )[:2500],
            )

    print()

    # --------------------------------------------------------
    # 안전 Probe
    # --------------------------------------------------------

    print_line()
    print(
        "=== 7. GIS Endpoint 최소 요청 Probe ==="
    )
    print_line()

    probes = build_safe_probes(
        pnu
    )

    probe_results = []

    for index, probe in enumerate(
        probes,
        start=1,
    ):

        print_subline()

        print(
            f"[{index}] "
            f"{probe['name']}"
        )

        result = request_text(
            session,
            TARGET_ENDPOINT,
            method=probe["method"],
            params=probe["params"],
            data=probe["data"],
        )

        classification = (
            classify_response(
                result
            )
        )

        record = {
            "name": probe[
                "name"
            ],
            "method": probe[
                "method"
            ],
            "params": probe[
                "params"
            ],
            "data": probe[
                "data"
            ],
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
            "classification": (
                classification
            ),
            "preview": (
                result["text"][:3000]
            ),
        }

        probe_results.append(
            record
        )

        print(
            "method:",
            probe["method"],
        )

        print(
            "params:",
            probe["params"],
        )

        print(
            "data:",
            probe["data"],
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
            "classification:",
            classification[
                "classification"
            ],
        )

        print(
            "response length:",
            classification[
                "length"
            ],
        )

        print(
            f"{TARGET_CODE} 포함:",
            classification[
                "has_target_code"
            ],
        )

        print(
            f"{TARGET_NAME} 포함:",
            classification[
                "has_target_name"
            ],
        )

        preview = (
            result["text"]
            .replace(
                "\r",
                " "
            )
            .replace(
                "\n",
                " "
            )
        )

        preview = re.sub(
            r"\s+",
            " ",
            preview,
        )

        print(
            "preview:",
            preview[:1200],
        )

    print()

    # --------------------------------------------------------
    # 응답 구조 후보
    # --------------------------------------------------------

    print_line()
    print(
        "=== 8. Endpoint 응답 구조 분석 ==="
    )
    print_line()

    successful_responses = [
        item
        for item in probe_results
        if (
            item[
                "http_status"
            ]
            == 200
            and item[
                "classification"
            ][
                "classification"
            ]
            not in (
                "EMPTY_RESPONSE",
                "HTTP_OR_NETWORK_ERROR",
            )
        )
    ]

    target_reference_responses = [
        item
        for item in probe_results
        if (
            item[
                "classification"
            ][
                "has_target_code"
            ]
            or item[
                "classification"
            ][
                "has_target_name"
            ]
        )
    ]

    print(
        "내용 있는 HTTP 200 응답:",
        len(
            successful_responses
        ),
    )

    print(
        "UQQ905/입체복합구역 "
        "직접 응답:",
        len(
            target_reference_responses
        ),
    )

    for item in (
        successful_responses
    ):

        print_subline()

        print(
            "probe:",
            item["name"],
        )

        print(
            "classification:",
            item[
                "classification"
            ][
                "classification"
            ],
        )

        print(
            "content-type:",
            item[
                "content_type"
            ],
        )

    print()

    # --------------------------------------------------------
    # 판정
    # --------------------------------------------------------

    print_line()
    print(
        "=== 9. GIS Endpoint 요청구조 판정 ==="
    )
    print_line()

    ajax_endpoint_found = (
        len(
            endpoint_contexts
        )
        > 0
    )

    ajax_block_found = (
        len(
            ajax_blocks
        )
        > 0
    )

    endpoint_reachable = any(
        item[
            "http_status"
        ]
        == 200
        for item
        in probe_results
    )

    target_response_found = (
        len(
            target_reference_responses
        )
        > 0
    )

    if target_response_found:

        source_status = (
            "TARGET_CODE_ENDPOINT_RESPONSE_FOUND"
        )

        reason = (
            "mpMapDetGisAjaxXml.jsp 실제 요청 응답에서 "
            "UQQ905 또는 도시군계획시설입체복합구역 "
            "직접 참조를 확인함. 다음 단계에서 응답의 "
            "Feature/geometry 구조 및 공간범위를 검증해야 함"
        )

    elif (
        ajax_endpoint_found
        and endpoint_reachable
    ):

        source_status = (
            "GIS_ENDPOINT_VERIFIED_"
            "PARAMETER_STRUCTURE_PARTIAL"
        )

        reason = (
            "mpMapDet.js에서 mpMapDetGisAjaxXml.jsp "
            "호출 경로를 확인하고 endpoint에 실제 요청이 "
            "도달함을 확인했으나, 현재 최소 probe만으로는 "
            "UQQ905를 geometry Feature 요청으로 연결하는 "
            "정확한 parameter 조합이 확정되지 않음"
        )

    elif ajax_endpoint_found:

        source_status = (
            "GIS_ENDPOINT_CALL_FOUND_"
            "REQUEST_UNRESOLVED"
        )

        reason = (
            "mpMapDet.js에서 GIS endpoint 호출은 확인했으나 "
            "실제 요청 성공 또는 parameter 구조를 "
            "확정하지 못함"
        )

    else:

        source_status = (
            "GIS_ENDPOINT_STRUCTURE_UNRESOLVED"
        )

        reason = (
            "A-3에서 후보로 확인한 GIS endpoint의 "
            "실제 호출 구조를 mpMapDet.js에서 "
            "충분히 복원하지 못함"
        )

    print(
        "source_status:",
        source_status,
    )

    print(
        "endpoint call found:",
        ajax_endpoint_found,
    )

    print(
        "AJAX block found:",
        ajax_block_found,
    )

    print(
        "endpoint reachable:",
        endpoint_reachable,
    )

    print(
        "target response found:",
        target_response_found,
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
    print(
        "=== 10. 현재 입체복합구역 SITE 판정 ==="
    )
    print_line()

    site_resolution = {
        "query_status": (
            "NOT_CONNECTED"
        ),
        "resolution": "UNKNOWN",
        "confidence": "NONE",
        "reason": (
            "GIS endpoint의 호출 구조를 분석 중이며 "
            "아직 UQQ905 공간 geometry 전체를 정상 조회하고 "
            "대상 PNU Parcel Polygon과 공간교차를 "
            "검증하지 않았으므로 TRUE/FALSE를 판정하지 않음"
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
        "SITE 주소 존재": (
            bool(
                site["address"]
            )
        ),

        "PNU 19자리": (
            len(pnu) == 19
            and pnu.isdigit()
        ),

        "A-3 GIS endpoint 후보 확인": (
            endpoint_verified_from_probe
        ),

        "토지이음 지도 session 초기화": (
            map_result[
                "http_status"
            ]
            == 200
        ),

        "UQQ905 DOM 확인": (
            len(
                target_dom
            )
            > 0
        ),

        "mpMapDet.js 조회 성공": (
            js_result[
                "http_status"
            ]
            == 200
        ),

        "GIS endpoint 호출부 검색 실행": (
            isinstance(
                endpoint_contexts,
                list,
            )
        ),

        "AJAX 구조 분석 실행": (
            isinstance(
                ajax_analysis,
                list,
            )
        ),

        "endpoint 실제 요청 Probe 실행": (
            len(
                probe_results
            )
            == len(
                probes
            )
        ),

        "파라미터 추측만으로 TRUE 금지": (
            site_resolution[
                "resolution"
            ]
            != "TRUE"
        ),

        "파라미터 추측만으로 FALSE 금지": (
            site_resolution[
                "resolution"
            ]
            != "FALSE"
        ),

        "geometry 미확정 UNKNOWN 유지": (
            site_resolution[
                "resolution"
            ]
            == "UNKNOWN"
        ),
    }

    print_line()
    print(
        "=== C-9-2-6A-4 검증 ==="
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
    # 저장
    # --------------------------------------------------------

    output = {
        "step": STEP_NAME,

        "site": site,

        "target": {
            "name": TARGET_NAME,
            "code": TARGET_CODE,
        },

        "endpoint": (
            TARGET_ENDPOINT
        ),

        "network_probe_verified": (
            endpoint_verified_from_probe
        ),

        "target_dom": (
            target_dom
        ),

        "js_analysis": {
            "url": MP_MAP_JS_URL,
            "http_status": (
                js_result[
                    "http_status"
                ]
            ),
            "endpoint_context_count": (
                len(
                    endpoint_contexts
                )
            ),
            "endpoint_contexts": (
                endpoint_contexts
            ),
            "ajax_analysis": (
                ajax_analysis
            ),
            "keyword_contexts": (
                keyword_context_output
            ),
        },

        "probe_results": (
            probe_results
        ),

        "source_resolution": {
            "source_status": (
                source_status
            ),
            "endpoint_call_found": (
                ajax_endpoint_found
            ),
            "ajax_block_found": (
                ajax_block_found
            ),
            "endpoint_reachable": (
                endpoint_reachable
            ),
            "target_response_found": (
                target_response_found
            ),
            "reason": reason,
        },

        "site_resolution": (
            site_resolution
        ),

        "validation": (
            checks
        ),
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
            "STEP 17-21-C-9-2-6A-4 완료"
        )

        print()

        print(
            "토지이음 GIS Endpoint "
            "요청구조 분석 프레임: ALL PASS"
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2-6A-5"
        )

        print(
            "→ mpMapDetGisAjaxXml.jsp의 "
            "실제 data parameter 복원"
        )

        print(
            "→ 정상 GIS 응답에서 "
            "layer / Feature 코드 확인"
        )

        print(
            "→ UQQ905 geometry 조회 가능 여부 검증"
        )

        print(
            "→ geometry 확보 후 Parcel intersection"
        )

    else:

        print(
            "STEP 17-21-C-9-2-6A-4 검증 미완료"
        )

        print()

        print(
            "FAIL 항목과 특히 "
            "AJAX Block / endpoint 응답 preview를 "
            "확인해야 합니다."
        )


if __name__ == "__main__":
    main()