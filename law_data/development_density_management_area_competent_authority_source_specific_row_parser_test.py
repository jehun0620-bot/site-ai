# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-16-S2
Development Density Management Area
Competent Authority Source-Specific Row Parser Recovery

목표
======================================================================
T-16-S1에서 hardening된 detail contract 2개를 기반으로 실제 historical page에서
source-specific document metadata row를 복원한다.

핵심 원칙
======================================================================
1. T-16-S1 next_stage_contract_pool만 contract evidence로 사용한다.
2. T-16 page_records의 bounded page만 제한 재조회한다.
3. UQQ700 target query/target identity 평가는 하지 않는다.
4. row-local title/date/notice-number와 detail identity 구조만 복원한다.
5. same-host go.kr static detail URL만 직접 URL로 인정한다.
6. JS-only detail contract는 함수/인자 identity만 보존하고 URL을 추측하지 않는다.
7. document metadata row 복원 ≠ target document verified.
8. verified positive/runtime/SITE TRUE/SITE FALSE 승격 금지.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import parse_qsl, urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
S1_INPUT_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_competent_authority_detail_contract_probe.json"
T16_INPUT_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_competent_authority_bounded_historical_range_traversal.json"
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_competent_authority_source_specific_row_parser.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 18
MAX_PAGES_PER_FAMILY = 9
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

TR_PATTERN = re.compile(r"<tr\b(?P<attrs>[^>]*)>(?P<body>.*?)</tr>", re.I | re.S)
LI_PATTERN = re.compile(r"<li\b(?P<attrs>[^>]*)>(?P<body>.*?)</li>", re.I | re.S)
ANCHOR_PATTERN = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>", re.I | re.S)
INPUT_PATTERN = re.compile(r"<input\b(?P<attrs>[^>]*)>", re.I | re.S)
ATTR_PATTERN = re.compile(r"([:\w-]+)\s*=\s*(?:[\"']([^\"']*)[\"']|([^\s>]+))", re.I | re.S)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_PATTERN = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)
DATE_PATTERN = re.compile(r"(?<!\d)((?:19|20)\d{2})[.\-/년\s]+(0?[1-9]|1[0-2])[.\-/월\s]+(0?[1-9]|[12]\d|3[01])(?:일)?(?!\d)")
NOTICE_NUMBER_PATTERN = re.compile(r"(?:고시|공고)\s*(?:제)?\s*\d{4}\s*[-–]\s*\d+\s*호?", re.I)
JS_CALL_PATTERN = re.compile(r"(?P<func>[A-Za-z_$][\w$]*)\s*\((?P<args>[^)]*)\)")
QUOTED_ARG_PATTERN = re.compile(r"[\"']([^\"']+)[\"']")
NUMERIC_ARG_PATTERN = re.compile(r"(?<!\w)(\d{2,})(?!\w)")

GENERIC_TEXTS = {"고시 공고", "고시공고", "목록", "더보기", "이전", "다음", "처음", "마지막", "열람", "보기", "홈", "메인"}
ROLE_NOISE_TERMS = {"로그인", "회원가입", "사이트맵", "개인정보", "오시는길", "조직도", "채용", "입찰"}
IDENTITY_ATTR_HINTS = {"seq", "idx", "ntt", "board", "bbs", "article", "post", "sn", "notice", "ancmt"}
DETAIL_QUERY_HINTS = {"idx", "seq", "nttid", "ntt_id", "article", "article_no", "post", "post_no", "board_seq", "bbsid", "bbs_id", "notice", "ancmt"}
DETAIL_PATH_HINTS = ("/view", "/detail", "/read", "/select", "/bbs/", "/board/", "/notice/", "/post/")


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_strings(values: Iterable[Any]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for value in values:
        text = normalize_space(value)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def strip_html(raw: str) -> str:
    value = COMMENT_PATTERN.sub(" ", raw or "")
    value = SCRIPT_STYLE_PATTERN.sub(" ", value)
    value = TAG_PATTERN.sub(" ", value)
    return normalize_space(html.unescape(value))


def parse_attrs(raw_attrs: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for match in ATTR_PATTERN.finditer(raw_attrs or ""):
        key = normalize_space(match.group(1)).lower()
        value = match.group(2) if match.group(2) is not None else match.group(3)
        if key:
            out[key] = html.unescape(normalize_space(value))
    return out


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
    result = []
    for match in DATE_PATTERN.finditer(text or ""):
        y, m, d = match.groups()
        result.append(f"{int(y):04d}-{int(m):02d}-{int(d):02d}")
    return unique_strings(result)


def extract_notice_numbers(text: str) -> List[str]:
    return unique_strings(match.group(0) for match in NOTICE_NUMBER_PATTERN.finditer(text or ""))


def is_detail_like_url(url: str, page_url: str) -> bool:
    if not url or not is_government_host(hostname(url)) or not same_host(page_url, url):
        return False
    parsed = urlparse(url)
    path = (parsed.path or "").lower()
    if any(hint in path for hint in DETAIL_PATH_HINTS):
        return True
    keys = {normalize_space(k).lower() for k, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    return bool(keys & DETAIL_QUERY_HINTS)


def decode_html(response: requests.Response, data: bytes) -> str:
    for enc in unique_strings([response.encoding, "utf-8", "cp949", "euc-kr"]):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    out = {"http_status": None, "final_url": "", "raw_html": "", "response_bytes": 0, "error": ""}
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            out["http_status"] = response.status_code
            out["final_url"] = str(response.url)
            chunks, total = [], 0
            for chunk in response.iter_content(chunk_size=128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError("response too large")
                chunks.append(chunk)
            data = b"".join(chunks)
            out["response_bytes"] = len(data)
            out["raw_html"] = decode_html(response, data)
    except Exception as exc:
        out["error"] = repr(exc)
    return out


def load_contracts(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("next_stage_contract_pool")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def load_pages(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("page_records")
    if not isinstance(raw, list):
        return []
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in raw:
        if not isinstance(item, dict) or item.get("http_status") != 200:
            continue
        family = normalize_space(item.get("source_family"))
        grouped.setdefault(family, []).append(item)
    result = []
    for family, items in sorted(grouped.items()):
        items = sorted(items, key=lambda x: int(x.get("page_number") or 0))
        if len(items) <= MAX_PAGES_PER_FAMILY:
            picks = items
        else:
            indexes = sorted(set([0, 1, 2, len(items)//4, len(items)//2, (3*len(items))//4, len(items)-3, len(items)-2, len(items)-1]))
            picks = [items[i] for i in indexes if 0 <= i < len(items)]
        result.extend(picks[:MAX_PAGES_PER_FAMILY])
    return result[:MAX_TOTAL_REQUESTS]


def contract_allows_row(contract: Dict[str, Any], static_paths: Set[str], js_functions: Set[str], identity_keys: Set[str]) -> bool:
    c_paths = set(contract.get("static_detail_paths") or [])
    c_js = set(contract.get("javascript_functions") or [])
    c_ids = set(contract.get("identity_keys") or [])
    if c_paths and static_paths & c_paths:
        return True
    if c_js and js_functions & c_js:
        return True
    if c_ids and identity_keys & c_ids:
        return True
    return False


def analyze_row(kind: str, body: str, page_url: str, contracts: List[Dict[str, Any]], row_index: int) -> Dict[str, Any] | None:
    text = strip_html(body)
    if not text or any(term in text for term in ROLE_NOISE_TERMS):
        return None

    anchors = []
    meaningful_titles = []
    static_urls = []
    js_contracts = []
    identity_items = []

    for match in ANCHOR_PATTERN.finditer(body):
        attrs = parse_attrs(match.group("attrs"))
        title = strip_html(match.group("body"))
        href = normalize_space(attrs.get("href"))
        onclick = normalize_space(attrs.get("onclick"))
        data_attrs = {k: v for k, v in attrs.items() if k.startswith("data-")}

        if title and title not in GENERIC_TEXTS and not title.isdigit():
            meaningful_titles.append(title)

        absolute = ""
        if href and not href.lower().startswith(("javascript:", "mailto:", "tel:", "#")):
            candidate = urljoin(page_url, href)
            if is_detail_like_url(candidate, page_url):
                absolute = candidate
                static_urls.append(candidate)

        for source, evidence in [("href", href), ("onclick", onclick)]:
            if not evidence:
                continue
            for js_match in JS_CALL_PATTERN.finditer(evidence):
                args = normalize_space(js_match.group("args"))
                quoted = unique_strings(QUOTED_ARG_PATTERN.findall(args))
                numeric = unique_strings(NUMERIC_ARG_PATTERN.findall(args))
                if not quoted and not numeric:
                    continue
                js_contracts.append({"function": js_match.group("func"), "args": args, "quoted_args": quoted, "numeric_args": numeric, "source": source})

        for key, value in data_attrs.items():
            if normalize_space(value) and any(hint in key.lower() for hint in IDENTITY_ATTR_HINTS):
                identity_items.append({"name": key.lower(), "value": value})

        anchors.append({"text": title, "href": href, "absolute_href": absolute, "onclick": onclick, "data_attrs": data_attrs})

    for match in INPUT_PATTERN.finditer(body):
        attrs = parse_attrs(match.group("attrs"))
        if normalize_space(attrs.get("type")).lower() != "hidden":
            continue
        name = normalize_space(attrs.get("name")).lower()
        ident = normalize_space(attrs.get("id")).lower()
        value = normalize_space(attrs.get("value"))
        evidence = f"{name} {ident}"
        if value and any(hint in evidence for hint in IDENTITY_ATTR_HINTS):
            identity_items.append({"name": name or ident, "value": value})

    titles = unique_strings(meaningful_titles)
    dates = extract_dates(text)
    notice_numbers = extract_notice_numbers(text)
    static_paths = {urlparse(url).path for url in static_urls}
    js_functions = {normalize_space(item.get("function")) for item in js_contracts if normalize_space(item.get("function"))}
    identity_keys = {normalize_space(item.get("name")).lower() for item in identity_items if normalize_space(item.get("name"))}

    if not titles:
        return None
    if not any(contract_allows_row(contract, static_paths, js_functions, identity_keys) for contract in contracts):
        return None
    if not (dates or notice_numbers or static_urls or js_contracts or identity_items):
        return None

    # 가장 구체적인 제목: 너무 짧지 않고 generic이 아닌 첫 anchor text.
    title = sorted(titles, key=lambda value: (-len(value), value))[0]
    if len(title) < 2:
        return None

    detail_identity_type = "STATIC_URL" if static_urls else "JAVASCRIPT_CONTRACT" if js_contracts else "ROW_IDENTITY"
    detail_identity = static_urls[0] if static_urls else {
        "javascript_contracts": js_contracts,
        "identity_items": identity_items,
    }

    score = 40
    reasons = ["CONTRACT_MATCHED_ROW", "ROW_LOCAL_TITLE"]
    if dates:
        score += 20
        reasons.append("ROW_LOCAL_DATE")
    if notice_numbers:
        score += 30
        reasons.append("ROW_LOCAL_NOTICE_NUMBER")
    if static_urls:
        score += 30
        reasons.append("SAME_HOST_DETAIL_URL")
    if js_contracts:
        score += 25
        reasons.append("JAVASCRIPT_DETAIL_IDENTITY")
    if identity_items:
        score += 20
        reasons.append("ROW_IDENTITY_ATTRIBUTE")

    return {
        "classification": "RECOVERED_SOURCE_SPECIFIC_DOCUMENT_METADATA_ROW",
        "row_index": row_index,
        "fragment_kind": kind,
        "title": title,
        "dates": dates,
        "notice_numbers": notice_numbers,
        "detail_identity_type": detail_identity_type,
        "detail_url": static_urls[0] if static_urls else None,
        "javascript_contracts": js_contracts,
        "identity_items": identity_items,
        "detail_identity": detail_identity,
        "row_text": text[:2500],
        "metadata_score": score,
        "reasons": unique_strings(reasons),
        "target_identity_evaluated": False,
        "target_query_executed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }


def analyze_page(raw_html: str, page_url: str, contracts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    row_index = 0
    for kind, pattern in [("TR", TR_PATTERN), ("LI", LI_PATTERN)]:
        for match in pattern.finditer(raw_html or ""):
            row_index += 1
            row = analyze_row(kind, match.group("body"), page_url, contracts, row_index)
            if row:
                result.append(row)
    return result


def canonical_identity(row: Dict[str, Any]) -> str:
    if row.get("detail_url"):
        return f"URL:{normalize_space(row.get('detail_url'))}"
    js = row.get("javascript_contracts") or []
    ids = row.get("identity_items") or []
    js_part = "|".join(sorted(f"{normalize_space(x.get('function'))}:{normalize_space(x.get('args'))}" for x in js))
    id_part = "|".join(sorted(f"{normalize_space(x.get('name'))}:{normalize_space(x.get('value'))}" for x in ids))
    return f"JS:{js_part}#ID:{id_part}#TITLE:{normalize_space(row.get('title'))}"


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SOURCE-SPECIFIC ROW PARSER RECOVERY")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Target query execution: DISABLED")
    print("Target identity evaluation: DISABLED")
    print()

    if not S1_INPUT_PATH.exists() or not T16_INPUT_PATH.exists():
        raise FileNotFoundError("required T-16-S1/T-16 input missing")

    s1 = json.loads(S1_INPUT_PATH.read_text(encoding="utf-8"))
    t16 = json.loads(T16_INPUT_PATH.read_text(encoding="utf-8"))
    contracts = load_contracts(s1)
    pages = load_pages(t16)

    print("Detail contract count:", len(contracts))
    print("Selected page count:", len(pages))
    print()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    request_count = http_success_count = transport_error_count = 0
    raw_rows = []
    page_results = []

    contracts_by_family: Dict[str, List[Dict[str, Any]]] = {}
    for contract in contracts:
        contracts_by_family.setdefault(normalize_space(contract.get("source_family")), []).append(contract)

    for index, page in enumerate(pages, start=1):
        family = normalize_space(page.get("source_family"))
        family_contracts = contracts_by_family.get(family, [])
        if not family_contracts:
            continue
        url = normalize_space(page.get("final_url") or page.get("requested_url"))
        response = fetch_page(session, url)
        request_count += 1
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1
        final_url = normalize_space(response.get("final_url") or url)
        rows = analyze_page(str(response.get("raw_html") or ""), final_url, family_contracts) if status == 200 else []
        for row in rows:
            row["source_family"] = family
            row["regions"] = page.get("regions") or []
            row["page_number"] = page.get("page_number")
            row["page_url"] = final_url
            raw_rows.append(row)
        page_results.append({"source_family": family, "page_number": page.get("page_number"), "url": final_url, "http_status": status, "recovered_row_count": len(rows), "error": response.get("error")})
        print("-" * 60)
        print(f"PAGE {index}")
        print("Family:", family)
        print("Page number:", page.get("page_number"))
        print("Recovered rows:", len(rows))

    row_map: Dict[str, Dict[str, Any]] = {}
    duplicate_removed = 0
    for row in raw_rows:
        key = canonical_identity(row)
        if key in row_map:
            duplicate_removed += 1
            existing = row_map[key]
            existing["dates"] = unique_strings((existing.get("dates") or []) + (row.get("dates") or []))
            existing["notice_numbers"] = unique_strings((existing.get("notice_numbers") or []) + (row.get("notice_numbers") or []))
            existing["page_numbers"] = sorted(set((existing.get("page_numbers") or []) + [row.get("page_number")]))
            existing["source_pages"] = unique_strings((existing.get("source_pages") or []) + [row.get("page_url")])
            existing["metadata_score"] = max(int(existing.get("metadata_score") or 0), int(row.get("metadata_score") or 0))
            continue
        canonical = dict(row)
        canonical["canonical_identity"] = key
        canonical["page_numbers"] = [row.get("page_number")]
        canonical["source_pages"] = [row.get("page_url")]
        row_map[key] = canonical

    canonical_rows = list(row_map.values())
    canonical_rows.sort(key=lambda x: x.get("canonical_identity") or "")

    next_stage_pool = [{
        "classification": row.get("classification"),
        "source_family": row.get("source_family"),
        "regions": row.get("regions") or [],
        "title": row.get("title"),
        "dates": row.get("dates") or [],
        "notice_numbers": row.get("notice_numbers") or [],
        "detail_identity_type": row.get("detail_identity_type"),
        "detail_url": row.get("detail_url"),
        "javascript_contracts": row.get("javascript_contracts") or [],
        "identity_items": row.get("identity_items") or [],
        "canonical_identity": row.get("canonical_identity"),
        "page_numbers": row.get("page_numbers") or [],
        "source_pages": row.get("source_pages") or [],
        "metadata_score": row.get("metadata_score"),
        "requires_target_identity_filter": True,
        "requires_direct_document_verification": True,
        "target_identity_evaluated": False,
        "target_query_executed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    } for row in canonical_rows]

    resolution = "COMPETENT_AUTHORITY_SOURCE_SPECIFIC_ROW_PARSER_RECOVERY_COMPLETED" if next_stage_pool else "COMPETENT_AUTHORITY_SOURCE_SPECIFIC_ROW_PARSER_RECOVERY_NO_ROWS"
    next_action = "복원된 canonical metadata row만 T-17 UQQ700 row-local target identity filter로 넘긴다." if next_stage_pool else "source-specific parser로도 문서행을 복원하지 못했다. UNKNOWN을 유지하고 전역 script/form contract를 추가 분석한다."

    output = {
        "step": "STEP 17-21-C-16-8-T-16-S2 Competent Authority Source-Specific Row Parser Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {"resolution_type": RESOLUTION_TYPE, "negative_evidence_allowed": False, "source_failure_site_status": "UNKNOWN"},
        "summary": {"detail_contract_count": len(contracts), "selected_page_count": len(pages), "request_count": request_count, "http_success_count": http_success_count, "transport_error_count": transport_error_count, "raw_row_count": len(raw_rows), "duplicate_row_removed": duplicate_removed, "canonical_row_count": len(canonical_rows), "next_stage_pool_count": len(next_stage_pool)},
        "page_results": page_results,
        "canonical_rows": canonical_rows,
        "next_stage_document_metadata_pool": next_stage_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    target_identity_leakage = sum(1 for x in canonical_rows + next_stage_pool if x.get("target_identity_evaluated") is True)
    target_query_leakage = sum(1 for x in canonical_rows + next_stage_pool if x.get("target_query_executed") is True)
    unsafe = sum(1 for x in canonical_rows + next_stage_pool if x.get("verified_positive") or x.get("runtime_registration_allowed") or x.get("site_positive_allowed") or x.get("site_negative_allowed") or x.get("final_positive_promotion_allowed"))
    cross_host_detail_leakage = sum(1 for x in canonical_rows if x.get("detail_url") and (not is_government_host(hostname(x.get("detail_url") or "")) or not same_host(x.get("page_url") or "", x.get("detail_url") or "")))
    weak_row_leakage = sum(1 for x in canonical_rows if not normalize_space(x.get("title")) or int(x.get("metadata_score") or 0) < 60)
    identity_keys = [x.get("canonical_identity") for x in canonical_rows]
    next_keys = [x.get("canonical_identity") for x in next_stage_pool]

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "T-16-S1 input exists": S1_INPUT_PATH.exists(),
        "T-16 input exists": T16_INPUT_PATH.exists(),
        "detail contracts loaded": len(contracts) > 0,
        "request budget respected": request_count <= MAX_TOTAL_REQUESTS,
        "target identity evaluation disabled": target_identity_leakage == 0,
        "target query execution disabled": target_query_leakage == 0,
        "canonical identities unique": len(identity_keys) == len(set(identity_keys)),
        "next-stage identities unique": len(next_keys) == len(set(next_keys)),
        "canonical and next-stage parity": set(identity_keys) == set(next_keys),
        "detail cross-host leakage zero": cross_host_detail_leakage == 0,
        "weak row leakage zero": weak_row_leakage == 0,
        "unsafe promotion leakage zero": unsafe == 0,
        "runtime registration remains blocked": output["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output["site_negative_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("SOURCE-SPECIFIC ROW PARSER RESULT")
    print("=" * 60)
    print("Request count:", request_count)
    print("Raw row count:", len(raw_rows))
    print("Duplicate row removed:", duplicate_removed)
    print("Canonical row count:", len(canonical_rows))
    print("Next-stage pool count:", len(next_stage_pool))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)
    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Cross-host detail leakage:", cross_host_detail_leakage)
    print("Weak row leakage:", weak_row_leakage)
    print("Target identity leakage:", target_identity_leakage)
    print("Target query leakage:", target_query_leakage)
    print("Unsafe promotion leakage:", unsafe)
    print("all_pass:", all(validations.values()))

    if not all(validations.values()):
        failed = [name for name, passed in validations.items() if not passed]
        print("FAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError("UQQ700 source-specific row parser regression failed")


if __name__ == "__main__":
    main()
