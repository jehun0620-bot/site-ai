# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-16-S1
Development Density Management Area
Competent Authority Detail Contract / Row Structure Probe Hardening

목표
======================================================================
T-16에서 historical page는 HTTP 200으로 순회되었지만 metadata row가 0건이었다.
T-16-S1 초판은 <tr>/<li> 전체를 폭넓게 probe하여 navigation/menu 링크가 과다
포함되었다. 본 수정본은 same-host official link와 row-local identity를 강제하여
실제 document row/detail contract 가능성이 있는 구조만 보존한다.

핵심 원칙
======================================================================
1. T-16 page_records 중 HTTP 200 page만 제한적으로 재조회한다.
2. UQQ700 target query는 실행하지 않는다.
3. target identity 판정은 하지 않는다.
4. document candidate 승격은 하지 않는다.
5. row-like container(<tr>, <li>)의 local 구조만 분석한다.
6. static href는 same-host + go.kr만 probe evidence로 보존한다.
7. cross-host / mailto / tel / fragment / generic navigation link는 버린다.
8. meaningful title + (date/notice-number/JS/data/hidden identity/detail-like href)
   구조가 함께 있어야 row probe candidate가 될 수 있다.
9. 다수 링크를 포함하는 menu/navigation LI는 배제한다.
10. verified positive / runtime registration / SITE TRUE/FALSE 자동판정 금지.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import parse_qsl, urljoin, urlparse

import requests


# ============================================================
# PATH / TARGET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_competent_authority_bounded_historical_range_traversal.json"
)

OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "development_density_management_area_competent_authority_detail_contract_probe.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False


# ============================================================
# HTTP / BUDGET
# ============================================================

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 12
MAX_PAGES_PER_FAMILY = 4
MAX_ANCHORS_PER_ROW = 8

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# HTML PATTERNS
# ============================================================

TR_PATTERN = re.compile(
    r"<tr\b(?P<attrs>[^>]*)>(?P<body>.*?)</tr>",
    re.IGNORECASE | re.DOTALL,
)

LI_PATTERN = re.compile(
    r"<li\b(?P<attrs>[^>]*)>(?P<body>.*?)</li>",
    re.IGNORECASE | re.DOTALL,
)

ANCHOR_FULL_PATTERN = re.compile(
    r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)

INPUT_PATTERN = re.compile(
    r"<input\b(?P<attrs>[^>]*)>",
    re.IGNORECASE | re.DOTALL,
)

ATTR_PATTERN = re.compile(
    r"([:\w-]+)\s*=\s*(?:[\"']([^\"']*)[\"']|([^\s>]+))",
    re.IGNORECASE | re.DOTALL,
)

TAG_PATTERN = re.compile(r"<[^>]+>", re.DOTALL)
SCRIPT_STYLE_PATTERN = re.compile(
    r"<(?:script|style)\b.*?</(?:script|style)>",
    re.IGNORECASE | re.DOTALL,
)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)

DATE_PATTERN = re.compile(
    r"(?<!\d)((?:19|20)\d{2})[.\-/년\s]+"
    r"(0?[1-9]|1[0-2])[.\-/월\s]+"
    r"(0?[1-9]|[12]\d|3[01])(?:일)?(?!\d)"
)

NOTICE_NUMBER_PATTERN = re.compile(
    r"(?:고시|공고)\s*(?:제)?\s*\d{4}\s*[-–]\s*\d+\s*호?",
    re.IGNORECASE,
)

JS_CALL_PATTERN = re.compile(
    r"(?P<func>[A-Za-z_$][\w$]*)\s*\((?P<args>[^)]*)\)"
)

QUOTED_ARG_PATTERN = re.compile(r"[\"']([^\"']+)[\"']")
NUMERIC_ARG_PATTERN = re.compile(r"(?<!\w)(\d{2,})(?!\w)")


# ============================================================
# SEMANTIC GUARDS
# ============================================================

GENERIC_TEXTS = {
    "고시 공고",
    "고시공고",
    "목록",
    "더보기",
    "이전",
    "다음",
    "처음",
    "마지막",
    "열람",
    "보기",
    "홈",
    "메인",
}

ROLE_NOISE_TERMS = {
    "로그인",
    "회원가입",
    "사이트맵",
    "개인정보",
    "오시는길",
    "조직도",
    "채용",
    "입찰",
}

IDENTITY_ATTR_HINTS = {
    "seq",
    "idx",
    "ntt",
    "board",
    "bbs",
    "article",
    "post",
    "sn",
    "notice",
    "ancmt",
}

DETAIL_QUERY_HINTS = {
    "idx",
    "seq",
    "nttid",
    "ntt_id",
    "article",
    "article_no",
    "post",
    "post_no",
    "board_seq",
    "bbsid",
    "bbs_id",
    "notice",
    "ancmt",
}

DETAIL_PATH_HINTS = (
    "/view",
    "/detail",
    "/read",
    "/select",
    "/bbs/",
    "/board/",
    "/notice/",
    "/post/",
)

NAV_PATH_HINTS = (
    "/login",
    "/member",
    "/sitemap",
    "/privacy",
    "/main",
    "/index",
)


# ============================================================
# UTIL
# ============================================================

def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_strings(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: Set[str] = set()

    for value in values:
        text = normalize_space(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)

    return result


def strip_html(raw: str) -> str:
    value = COMMENT_PATTERN.sub(" ", raw or "")
    value = SCRIPT_STYLE_PATTERN.sub(" ", value)
    value = TAG_PATTERN.sub(" ", value)
    return normalize_space(html.unescape(value))


def parse_attrs(raw_attrs: str) -> Dict[str, str]:
    result: Dict[str, str] = {}

    for match in ATTR_PATTERN.finditer(raw_attrs or ""):
        key = normalize_space(match.group(1)).lower()
        value = match.group(2) if match.group(2) is not None else match.group(3)
        if key:
            result[key] = html.unescape(normalize_space(value))

    return result


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    return bool(host) and (host == "go.kr" or host.endswith(".go.kr"))


def same_host(a: str, b: str) -> bool:
    return bool(hostname(a)) and hostname(a) == hostname(b)


def extract_dates(text: str) -> List[str]:
    result: List[str] = []

    for match in DATE_PATTERN.finditer(text or ""):
        year, month, day = match.groups()
        result.append(
            f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        )

    return unique_strings(result)


def extract_notice_numbers(text: str) -> List[str]:
    return unique_strings(
        match.group(0)
        for match in NOTICE_NUMBER_PATTERN.finditer(text or "")
    )


def is_detail_like_url(url: str, page_url: str) -> bool:
    if not url:
        return False

    if not is_government_host(hostname(url)):
        return False

    if not same_host(page_url, url):
        return False

    parsed = urlparse(url)
    path = (parsed.path or "").lower()

    if any(term in path for term in NAV_PATH_HINTS):
        return False

    if any(term in path for term in DETAIL_PATH_HINTS):
        return True

    query_keys = {
        normalize_space(key).lower()
        for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
        if normalize_space(key)
    }

    if query_keys & DETAIL_QUERY_HINTS:
        return True

    # same board path에서 list/pagination이 아닌 식별 query가 있는 경우만 보조 인정.
    if parsed.query and "curpage=" not in parsed.query.lower():
        return len(query_keys) >= 1

    return False


def decode_html(response: requests.Response, data: bytes) -> str:
    for encoding in unique_strings(
        [response.encoding, "utf-8", "cp949", "euc-kr"]
    ):
        try:
            return data.decode(encoding)
        except Exception:
            continue

    return data.decode("utf-8", errors="replace")


# ============================================================
# HTTP
# ============================================================

def fetch_page(
    session: requests.Session,
    url: str,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "http_status": None,
        "final_url": "",
        "raw_html": "",
        "response_bytes": 0,
        "error": "",
    }

    try:
        with session.get(
            url,
            timeout=TIMEOUT,
            allow_redirects=True,
            stream=True,
        ) as response:
            result["http_status"] = response.status_code
            result["final_url"] = str(response.url)

            chunks: List[bytes] = []
            total = 0

            for chunk in response.iter_content(chunk_size=128 * 1024):
                if not chunk:
                    continue

                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError("response too large")

                chunks.append(chunk)

            data = b"".join(chunks)
            result["response_bytes"] = len(data)
            result["raw_html"] = decode_html(response, data)

    except Exception as exc:
        result["error"] = repr(exc)

    return result


# ============================================================
# INPUT PAGE SELECTION
# ============================================================

def load_probe_pages(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("page_records")
    if not isinstance(raw, list):
        return []

    by_family: Dict[str, List[Dict[str, Any]]] = {}

    for item in raw:
        if not isinstance(item, dict):
            continue

        if item.get("http_status") != 200:
            continue

        family = normalize_space(item.get("source_family"))
        if not family:
            continue

        by_family.setdefault(family, []).append(item)

    selected: List[Dict[str, Any]] = []

    for family, items in sorted(by_family.items()):
        items = sorted(
            items,
            key=lambda item: int(item.get("page_number") or 0),
        )

        if not items:
            continue

        picks: List[Dict[str, Any]] = []

        for index in [0, 1, len(items) // 2, len(items) - 1]:
            if not 0 <= index < len(items):
                continue

            item = items[index]
            identity = normalize_space(
                item.get("final_url") or item.get("requested_url")
            )

            if not identity:
                continue

            if any(
                normalize_space(
                    existing.get("final_url")
                    or existing.get("requested_url")
                ) == identity
                for existing in picks
            ):
                continue

            picks.append(item)

        selected.extend(picks[:MAX_PAGES_PER_FAMILY])

    return selected[:MAX_TOTAL_REQUESTS]


# ============================================================
# ROW ANALYSIS
# ============================================================

def analyze_row(
    fragment_kind: str,
    attrs_raw: str,
    body: str,
    page_url: str,
    row_index: int,
) -> Dict[str, Any] | None:
    text = strip_html(body)

    if not text:
        return None

    if any(term in text for term in ROLE_NOISE_TERMS):
        return None

    raw_anchor_count = sum(
        1
        for _ in ANCHOR_FULL_PATTERN.finditer(body)
    )

    # 메뉴형 LI는 수십 개의 하위 anchor를 포함하는 경우가 많다.
    if fragment_kind == "LI" and raw_anchor_count > MAX_ANCHORS_PER_ROW:
        return None

    anchors: List[Dict[str, Any]] = []
    js_contracts: List[Dict[str, Any]] = []
    data_identity: List[Dict[str, str]] = []
    hidden_inputs: List[Dict[str, str]] = []

    rejected_cross_host_static = 0
    rejected_navigation_static = 0

    for match in ANCHOR_FULL_PATTERN.finditer(body):
        attrs = parse_attrs(match.group("attrs"))

        anchor_text = strip_html(match.group("body"))
        href = normalize_space(attrs.get("href"))
        onclick = normalize_space(attrs.get("onclick"))
        data_attrs = {
            key: value
            for key, value in attrs.items()
            if key.startswith("data-")
        }

        absolute_href = ""
        detail_href = ""

        if href and not href.lower().startswith(
            ("javascript:", "mailto:", "tel:", "#")
        ):
            candidate_href = urljoin(page_url, href)

            if (
                not is_government_host(hostname(candidate_href))
                or not same_host(page_url, candidate_href)
            ):
                rejected_cross_host_static += 1

            elif is_detail_like_url(candidate_href, page_url):
                absolute_href = candidate_href
                detail_href = candidate_href

            else:
                rejected_navigation_static += 1

        # javascript evidence는 href/onclick에 실제 함수 호출이 있을 때만 복원.
        for source_name, evidence in [("href", href), ("onclick", onclick)]:
            if not evidence:
                continue

            for js_match in JS_CALL_PATTERN.finditer(evidence):
                args = normalize_space(js_match.group("args"))
                quoted_args = unique_strings(
                    QUOTED_ARG_PATTERN.findall(args)
                )
                numeric_args = unique_strings(
                    NUMERIC_ARG_PATTERN.findall(args)
                )

                # argument가 전혀 없는 단순 UI 함수는 detail contract evidence로 사용하지 않는다.
                if not quoted_args and not numeric_args:
                    continue

                js_contracts.append(
                    {
                        "function": js_match.group("func"),
                        "args": args,
                        "quoted_args": quoted_args,
                        "numeric_args": numeric_args,
                        "source": source_name,
                    }
                )

        for key, value in data_attrs.items():
            lowered = key.lower()

            if (
                any(hint in lowered for hint in IDENTITY_ATTR_HINTS)
                and normalize_space(value)
            ):
                data_identity.append(
                    {
                        "name": key,
                        "value": value,
                    }
                )

        # 보존되는 anchor는 local detail/JS/data identity가 있는 anchor만.
        if (
            detail_href
            or onclick
            or href.lower().startswith("javascript:")
            or any(
                any(hint in key.lower() for hint in IDENTITY_ATTR_HINTS)
                and normalize_space(value)
                for key, value in data_attrs.items()
            )
        ):
            anchors.append(
                {
                    "text": anchor_text,
                    "href": href,
                    "absolute_href": absolute_href,
                    "onclick": onclick,
                    "data_attrs": data_attrs,
                    "id": attrs.get("id", ""),
                    "class": attrs.get("class", ""),
                }
            )

    for match in INPUT_PATTERN.finditer(body):
        attrs = parse_attrs(match.group("attrs"))

        if normalize_space(attrs.get("type")).lower() != "hidden":
            continue

        name = normalize_space(attrs.get("name"))
        ident = normalize_space(attrs.get("id"))
        value = normalize_space(attrs.get("value"))
        evidence = f"{name} {ident}".lower()

        if (
            value
            and any(hint in evidence for hint in IDENTITY_ATTR_HINTS)
        ):
            hidden_inputs.append(
                {
                    "name": name,
                    "id": ident,
                    "value": value,
                }
            )

    dates = extract_dates(text)
    notice_numbers = extract_notice_numbers(text)

    meaningful_anchor_texts = unique_strings(
        anchor.get("text")
        for anchor in anchors
        if (
            anchor.get("text")
            and normalize_space(anchor.get("text")) not in GENERIC_TEXTS
            and not normalize_space(anchor.get("text")).isdigit()
        )
    )

    static_detail_present = any(
        anchor.get("absolute_href")
        for anchor in anchors
    )

    strong_identity_present = bool(
        notice_numbers
        or js_contracts
        or data_identity
        or hidden_inputs
        or static_detail_present
    )

    # title-like anchor 없이 identity만 있는 navigation/control row는 버린다.
    if not meaningful_anchor_texts:
        return None

    if not strong_identity_present:
        return None

    # 단순 href만으로는 너무 넓으므로 날짜 또는 notice/JS/data/hidden 증거를 추가 요구.
    secondary_row_identity = bool(
        dates
        or notice_numbers
        or js_contracts
        or data_identity
        or hidden_inputs
    )

    if static_detail_present and not secondary_row_identity:
        return None

    structural_score = 0
    reasons: List[str] = []

    if meaningful_anchor_texts:
        structural_score += 30
        reasons.append("MEANINGFUL_ANCHOR_TEXT")

    if dates:
        structural_score += 25
        reasons.append("ROW_LOCAL_DATE")

    if notice_numbers:
        structural_score += 35
        reasons.append("ROW_LOCAL_NOTICE_NUMBER")

    if static_detail_present:
        structural_score += 25
        reasons.append("SAME_HOST_STATIC_DETAIL_HREF")

    if js_contracts:
        structural_score += 30
        reasons.append("JAVASCRIPT_DETAIL_CONTRACT_PRESENT")

    if data_identity:
        structural_score += 25
        reasons.append("DATA_IDENTITY_PRESENT")

    if hidden_inputs:
        structural_score += 25
        reasons.append("HIDDEN_IDENTITY_PRESENT")

    if structural_score < 55:
        return None

    return {
        "row_index": row_index,
        "fragment_kind": fragment_kind,
        "row_text": text[:2500],
        "meaningful_anchor_texts": meaningful_anchor_texts,
        "dates": dates,
        "notice_numbers": notice_numbers,
        "anchors": anchors,
        "javascript_contracts": js_contracts,
        "data_identity": data_identity,
        "hidden_identity": hidden_inputs,
        "structural_score": structural_score,
        "reasons": unique_strings(reasons),
        "rejected_cross_host_static_count": rejected_cross_host_static,
        "rejected_navigation_static_count": rejected_navigation_static,
    }


def analyze_page(
    raw_html: str,
    page_url: str,
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    row_index = 0

    for fragment_kind, pattern in [
        ("TR", TR_PATTERN),
        ("LI", LI_PATTERN),
    ]:
        for match in pattern.finditer(raw_html or ""):
            row_index += 1

            candidate = analyze_row(
                fragment_kind,
                match.group("attrs"),
                match.group("body"),
                page_url,
                row_index,
            )

            if candidate:
                result.append(candidate)

    return result


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("COMPETENT AUTHORITY DETAIL CONTRACT / ROW STRUCTURE PROBE")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Target query execution: DISABLED")
    print("Document candidate promotion: DISABLED")
    print()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"T-16 input not found: {INPUT_PATH}"
        )

    data = json.loads(
        INPUT_PATH.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise TypeError("T-16 input must be JSON object")

    pages = load_probe_pages(data)

    print("Selected probe page count:", len(pages))
    print()

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ko-KR,ko;q=0.9",
        }
    )

    request_count = 0
    http_success_count = 0
    transport_error_count = 0

    page_results: List[Dict[str, Any]] = []
    raw_candidates: List[Dict[str, Any]] = []

    for index, page in enumerate(pages, start=1):
        url = normalize_space(
            page.get("final_url")
            or page.get("requested_url")
        )

        family = normalize_space(
            page.get("source_family")
        )

        page_number = page.get("page_number")

        response = fetch_page(session, url)
        request_count += 1

        status = response.get("http_status")

        if (
            isinstance(status, int)
            and 200 <= status < 300
        ):
            http_success_count += 1

        if response.get("error"):
            transport_error_count += 1

        final_url = normalize_space(
            response.get("final_url") or url
        )

        rows = (
            analyze_page(
                str(response.get("raw_html") or ""),
                final_url,
            )
            if status == 200
            else []
        )

        for row in rows:
            row["source_family"] = family
            row["page_number"] = page_number
            row["page_url"] = final_url
            row["target_identity_evaluated"] = False
            row["target_query_executed"] = False
            row["document_candidate"] = False
            row["verified_positive"] = False
            row["runtime_registration_allowed"] = False
            row["site_positive_allowed"] = False
            row["site_negative_allowed"] = False
            row["final_positive_promotion_allowed"] = False

            raw_candidates.append(row)

        page_results.append(
            {
                "source_family": family,
                "page_number": page_number,
                "url": final_url,
                "http_status": status,
                "probe_candidate_count": len(rows),
                "error": response.get("error"),
            }
        )

        print("-" * 60)
        print(f"PAGE {index}")
        print("Family:", family)
        print("Page number:", page_number)
        print("URL:", final_url)
        print("HTTP:", status)
        print("Probe candidates:", len(rows))

    # ========================================================
    # CONTRACT SIGNATURE DEDUPE
    # ========================================================

    signature_map: Dict[
        Tuple[str, Tuple[str, ...], Tuple[str, ...]],
        Dict[str, Any],
    ] = {}

    for row in raw_candidates:
        js_functions = tuple(
            sorted(
                {
                    normalize_space(item.get("function"))
                    for item in row.get("javascript_contracts") or []
                    if normalize_space(item.get("function"))
                }
            )
        )

        static_paths = tuple(
            sorted(
                {
                    urlparse(
                        anchor.get("absolute_href") or ""
                    ).path
                    for anchor in row.get("anchors") or []
                    if anchor.get("absolute_href")
                }
            )
        )

        # static path도 JS function도 없는 data/hidden-only 구조는 별도 signature.
        data_keys = tuple(
            sorted(
                {
                    normalize_space(item.get("name")).lower()
                    for item in row.get("data_identity") or []
                    if normalize_space(item.get("name"))
                }
                | {
                    normalize_space(item.get("name")).lower()
                    for item in row.get("hidden_identity") or []
                    if normalize_space(item.get("name"))
                }
            )
        )

        identity_component = static_paths or js_functions or data_keys

        key = (
            normalize_space(row.get("source_family")),
            tuple(static_paths),
            tuple(js_functions) + tuple(identity_component),
        )

        if key not in signature_map:
            signature_map[key] = {
                "source_family": row.get("source_family"),
                "static_detail_paths": list(static_paths),
                "javascript_functions": list(js_functions),
                "identity_keys": list(data_keys),
                "sample_rows": [],
                "page_numbers": [],
                "reasons": [],
                "target_query_executed": False,
                "document_candidate": False,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            }

        contract = signature_map[key]

        if len(contract["sample_rows"]) < 5:
            contract["sample_rows"].append(
                {
                    "row_text": row.get("row_text"),
                    "meaningful_anchor_texts": row.get(
                        "meaningful_anchor_texts"
                    ),
                    "dates": row.get("dates"),
                    "notice_numbers": row.get("notice_numbers"),
                    "anchors": row.get("anchors"),
                    "javascript_contracts": row.get(
                        "javascript_contracts"
                    ),
                    "data_identity": row.get("data_identity"),
                    "hidden_identity": row.get("hidden_identity"),
                }
            )

        contract["page_numbers"] = sorted(
            set(
                contract["page_numbers"]
                + [row.get("page_number")]
            )
        )

        contract["reasons"] = unique_strings(
            contract["reasons"]
            + (row.get("reasons") or [])
        )

    contracts = list(signature_map.values())

    contracts.sort(
        key=lambda item: (
            normalize_space(item.get("source_family")),
            "|".join(item.get("static_detail_paths") or []),
            "|".join(item.get("javascript_functions") or []),
            "|".join(item.get("identity_keys") or []),
        )
    )

    next_stage_contract_pool = [
        {
            **contract,
            "requires_source_specific_row_parser": True,
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for contract in contracts
    ]

    if contracts:
        resolution = (
            "COMPETENT_AUTHORITY_DETAIL_CONTRACT_PROBE_COMPLETED"
        )
        next_action = (
            "복원된 same-host source-specific detail contract를 기반으로 "
            "T-16-S2 row parser를 작성한다."
        )
    else:
        resolution = (
            "COMPETENT_AUTHORITY_DETAIL_CONTRACT_PROBE_NO_STRUCTURE"
        )
        next_action = (
            "row-local detail contract를 복원하지 못했다. "
            "script/form 전역 contract 분석 또는 다른 archive source를 검토한다."
        )

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-T-16-S1 "
            "Competent Authority Detail Contract / Row Structure Probe Hardening"
        ),
        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "method": {
            "target_query_execution_enabled": False,
            "target_identity_evaluation_enabled": False,
            "document_candidate_promotion_enabled": False,
            "same_host_static_href_required": True,
            "official_go_kr_static_href_required": True,
            "navigation_container_guard_enabled": True,
            "row_local_identity_required": True,
        },
        "summary": {
            "selected_probe_page_count": len(pages),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "raw_probe_candidate_count": len(raw_candidates),
            "detail_contract_count": len(contracts),
            "next_stage_contract_pool_count": len(
                next_stage_contract_pool
            ),
        },
        "page_results": page_results,
        "raw_probe_candidates": raw_candidates,
        "detail_contracts": contracts,
        "next_stage_contract_pool": next_stage_contract_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            output_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    target_query_leakage = sum(
        1
        for item in raw_candidates + contracts
        if item.get("target_query_executed") is True
    )

    document_candidate_leakage = sum(
        1
        for item in raw_candidates + contracts
        if item.get("document_candidate") is True
    )

    unsafe_promotion_leakage = sum(
        1
        for item in raw_candidates + contracts
        if (
            item.get("verified_positive") is True
            or item.get("runtime_registration_allowed") is True
            or item.get("site_positive_allowed") is True
            or item.get("site_negative_allowed") is True
            or item.get("final_positive_promotion_allowed") is True
        )
    )

    cross_host_static_leakage = sum(
        1
        for row in raw_candidates
        for anchor in row.get("anchors") or []
        if (
            anchor.get("absolute_href")
            and (
                not is_government_host(
                    hostname(anchor.get("absolute_href") or "")
                )
                or not same_host(
                    row.get("page_url") or "",
                    anchor.get("absolute_href") or "",
                )
            )
        )
    )

    navigation_static_leakage = sum(
        1
        for row in raw_candidates
        for anchor in row.get("anchors") or []
        if (
            anchor.get("absolute_href")
            and not is_detail_like_url(
                anchor.get("absolute_href") or "",
                row.get("page_url") or "",
            )
        )
    )

    weak_row_leakage = sum(
        1
        for row in raw_candidates
        if not (
            row.get("meaningful_anchor_texts")
            and (
                row.get("dates")
                or row.get("notice_numbers")
                or row.get("javascript_contracts")
                or row.get("data_identity")
                or row.get("hidden_identity")
            )
        )
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "T-16 input exists": INPUT_PATH.exists(),
        "T-16 input parsed": isinstance(data, dict),
        "probe page budget respected": (
            request_count <= MAX_TOTAL_REQUESTS
        ),
        "target query execution disabled": (
            target_query_leakage == 0
        ),
        "document candidate promotion disabled": (
            document_candidate_leakage == 0
        ),
        "static detail cross-host leakage zero": (
            cross_host_static_leakage == 0
        ),
        "static navigation leakage zero": (
            navigation_static_leakage == 0
        ),
        "weak row leakage zero": (
            weak_row_leakage == 0
        ),
        "unsafe promotion leakage zero": (
            unsafe_promotion_leakage == 0
        ),
        "runtime registration remains blocked": (
            output_data["runtime_registration_allowed"] is False
        ),
        "SITE TRUE remains blocked": (
            output_data["site_positive_allowed"] is False
        ),
        "SITE FALSE remains blocked": (
            output_data["site_negative_allowed"] is False
        ),
        "output written": (
            OUTPUT_PATH.exists()
            and OUTPUT_PATH.stat().st_size > 0
        ),
    }

    print()
    print("=" * 60)
    print("DETAIL CONTRACT PROBE RESULT")
    print("=" * 60)
    print("Selected probe page count:", len(pages))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Transport error count:", transport_error_count)
    print("Raw probe candidate count:", len(raw_candidates))
    print("Detail contract count:", len(contracts))
    print(
        "Next-stage contract pool count:",
        len(next_stage_contract_pool),
    )
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)

    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)

    for name, passed in validations.items():
        print(f"{name}: {passed}")

    print()
    print("Target query leakage:", target_query_leakage)
    print("Document candidate leakage:", document_candidate_leakage)
    print(
        "Cross-host static detail leakage:",
        cross_host_static_leakage,
    )
    print(
        "Static navigation leakage:",
        navigation_static_leakage,
    )
    print("Weak row leakage:", weak_row_leakage)
    print(
        "Unsafe promotion leakage:",
        unsafe_promotion_leakage,
    )
    print()

    all_pass = all(validations.values())
    print("all_pass:", all_pass)

    if not all_pass:
        failed = [
            name
            for name, passed in validations.items()
            if not passed
        ]

        print("FAILED:")
        for name in failed:
            print("-", name)

        raise AssertionError(
            "UQQ700 detail contract probe regression failed"
        )


if __name__ == "__main__":
    main()
