# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-16-S1
Development Density Management Area
Competent Authority Detail Contract / Row Structure Probe

목표
======================================================================
T-16에서 historical page는 정상 조회되었지만 document metadata row가 0건이었다.
정적 href만 보는 parser 한계를 점검하기 위해 실제 HTML의 row-like container에서
anchor href / onclick / data-* / hidden identity / form action 구조를 복원한다.

핵심 원칙
======================================================================
1. T-16 page_records 중 HTTP 200 page만 제한적으로 재조회한다.
2. UQQ700 target query는 실행하지 않는다.
3. target identity 판정은 하지 않는다.
4. document candidate 승격은 하지 않는다.
5. row-like container(<tr>, <li>)의 local 구조만 분석한다.
6. javascript:, onclick, data-*, hidden input은 contract evidence일 뿐 legal evidence가 아니다.
7. same-host official source identity를 유지한다.
8. verified positive / runtime / SITE TRUE/FALSE 자동판정 금지.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_competent_authority_bounded_historical_range_traversal.json"
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_competent_authority_detail_contract_probe.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 12
MAX_PAGES_PER_FAMILY = 4
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

TR_PATTERN = re.compile(r"<tr\b(?P<attrs>[^>]*)>(?P<body>.*?)</tr>", re.I | re.S)
LI_PATTERN = re.compile(r"<li\b(?P<attrs>[^>]*)>(?P<body>.*?)</li>", re.I | re.S)
ANCHOR_FULL_PATTERN = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>", re.I | re.S)
INPUT_PATTERN = re.compile(r"<input\b(?P<attrs>[^>]*)>", re.I | re.S)
FORM_PATTERN = re.compile(r"<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>", re.I | re.S)
ATTR_PATTERN = re.compile(r"([:\w-]+)\s*=\s*(?:[\"']([^\"']*)[\"']|([^\s>]+))", re.I | re.S)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_PATTERN = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)

DATE_PATTERN = re.compile(r"(?<!\d)((?:19|20)\d{2})[.\-/년\s]+(0?[1-9]|1[0-2])[.\-/월\s]+(0?[1-9]|[12]\d|3[01])(?:일)?(?!\d)")
NOTICE_NUMBER_PATTERN = re.compile(r"(?:고시|공고)\s*(?:제)?\s*\d{4}\s*[-–]\s*\d+\s*호?", re.I)
JS_CALL_PATTERN = re.compile(r"(?P<func>[A-Za-z_$][\w$]*)\s*\((?P<args>[^)]*)\)")
QUOTED_ARG_PATTERN = re.compile(r"[\"']([^\"']+)[\"']")
NUMERIC_ARG_PATTERN = re.compile(r"(?<!\w)(\d{2,})(?!\w)")

GENERIC_TEXTS = {"고시 공고", "고시공고", "목록", "더보기", "이전", "다음", "처음", "마지막", "열람", "보기"}
IDENTITY_ATTR_HINTS = {"seq", "idx", "no", "ntt", "board", "bbs", "article", "post", "sn", "id"}
ROLE_NOISE_TERMS = {"로그인", "회원가입", "사이트맵", "개인정보", "오시는길", "조직도", "채용", "입찰"}


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
    out = []
    for match in DATE_PATTERN.finditer(text or ""):
        y, m, d = match.groups()
        out.append(f"{int(y):04d}-{int(m):02d}-{int(d):02d}")
    return unique_strings(out)


def extract_notice_numbers(text: str) -> List[str]:
    return unique_strings(m.group(0) for m in NOTICE_NUMBER_PATTERN.finditer(text or ""))


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


def load_probe_pages(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("page_records")
    if not isinstance(raw, list):
        return []

    by_family: Dict[str, List[Dict[str, Any]]] = {}
    for item in raw:
        if not isinstance(item, dict) or item.get("http_status") != 200:
            continue
        family = normalize_space(item.get("source_family"))
        if not family:
            continue
        by_family.setdefault(family, []).append(item)

    selected: List[Dict[str, Any]] = []
    for family, items in sorted(by_family.items()):
        items = sorted(items, key=lambda x: int(x.get("page_number") or 0))
        if not items:
            continue
        picks = []
        for idx in [0, 1, len(items) // 2, len(items) - 1]:
            if 0 <= idx < len(items):
                item = items[idx]
                if item not in picks:
                    picks.append(item)
        selected.extend(picks[:MAX_PAGES_PER_FAMILY])
    return selected[:MAX_TOTAL_REQUESTS]


def analyze_row(fragment_kind: str, attrs_raw: str, body: str, page_url: str, row_index: int) -> Dict[str, Any] | None:
    text = strip_html(body)
    if not text or any(term in text for term in ROLE_NOISE_TERMS):
        return None

    anchors = []
    js_contracts = []
    data_identity = []
    hidden_inputs = []

    for match in ANCHOR_FULL_PATTERN.finditer(body):
        attrs = parse_attrs(match.group("attrs"))
        anchor_text = strip_html(match.group("body"))
        href = normalize_space(attrs.get("href"))
        onclick = normalize_space(attrs.get("onclick"))
        data_attrs = {k: v for k, v in attrs.items() if k.startswith("data-")}

        absolute_href = ""
        if href and not href.lower().startswith(("javascript:", "#")):
            absolute_href = urljoin(page_url, href)

        anchors.append({
            "text": anchor_text,
            "href": href,
            "absolute_href": absolute_href,
            "onclick": onclick,
            "data_attrs": data_attrs,
            "id": attrs.get("id", ""),
            "class": attrs.get("class", ""),
        })

        for evidence in [href, onclick]:
            if not evidence:
                continue
            for js_match in JS_CALL_PATTERN.finditer(evidence):
                args = normalize_space(js_match.group("args"))
                js_contracts.append({
                    "function": js_match.group("func"),
                    "args": args,
                    "quoted_args": unique_strings(QUOTED_ARG_PATTERN.findall(args)),
                    "numeric_args": unique_strings(NUMERIC_ARG_PATTERN.findall(args)),
                    "source": "href" if evidence == href else "onclick",
                })

        for key, value in data_attrs.items():
            lowered = key.lower()
            if any(hint in lowered for hint in IDENTITY_ATTR_HINTS) and normalize_space(value):
                data_identity.append({"name": key, "value": value})

    for match in INPUT_PATTERN.finditer(body):
        attrs = parse_attrs(match.group("attrs"))
        if normalize_space(attrs.get("type")).lower() != "hidden":
            continue
        name = normalize_space(attrs.get("name"))
        ident = normalize_space(attrs.get("id"))
        value = normalize_space(attrs.get("value"))
        evidence = f"{name} {ident}".lower()
        if value and any(hint in evidence for hint in IDENTITY_ATTR_HINTS):
            hidden_inputs.append({"name": name, "id": ident, "value": value})

    dates = extract_dates(text)
    notice_numbers = extract_notice_numbers(text)
    meaningful_anchor_texts = unique_strings(
        a["text"] for a in anchors
        if a.get("text") and a["text"] not in GENERIC_TEXTS and not a["text"].isdigit()
    )

    structural_score = 0
    reasons = []
    if meaningful_anchor_texts:
        structural_score += 30
        reasons.append("MEANINGFUL_ANCHOR_TEXT")
    if dates:
        structural_score += 20
        reasons.append("ROW_LOCAL_DATE")
    if notice_numbers:
        structural_score += 30
        reasons.append("ROW_LOCAL_NOTICE_NUMBER")
    if any(a.get("absolute_href") for a in anchors):
        structural_score += 20
        reasons.append("STATIC_DETAIL_HREF_PRESENT")
    if js_contracts:
        structural_score += 25
        reasons.append("JAVASCRIPT_DETAIL_CONTRACT_PRESENT")
    if data_identity:
        structural_score += 20
        reasons.append("DATA_IDENTITY_PRESENT")
    if hidden_inputs:
        structural_score += 20
        reasons.append("HIDDEN_IDENTITY_PRESENT")

    # 단순 pagination/menu row는 제외하고, 상세 identity 구조가 있는 row만 probe candidate로 남긴다.
    has_detail_contract = bool(
        any(a.get("absolute_href") for a in anchors)
        or js_contracts
        or data_identity
        or hidden_inputs
    )
    if not meaningful_anchor_texts or not has_detail_contract or structural_score < 50:
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
    }


def analyze_page(raw_html: str, page_url: str) -> List[Dict[str, Any]]:
    result = []
    row_index = 0
    for kind, pattern in [("TR", TR_PATTERN), ("LI", LI_PATTERN)]:
        for match in pattern.finditer(raw_html or ""):
            row_index += 1
            candidate = analyze_row(kind, match.group("attrs"), match.group("body"), page_url, row_index)
            if candidate:
                result.append(candidate)
    return result


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
        raise FileNotFoundError(f"T-16 input not found: {INPUT_PATH}")
    data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("T-16 input must be JSON object")

    pages = load_probe_pages(data)
    print("Selected probe page count:", len(pages))
    print()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    request_count = http_success_count = transport_error_count = 0
    page_results = []
    raw_candidates = []

    for index, page in enumerate(pages, start=1):
        url = normalize_space(page.get("final_url") or page.get("requested_url"))
        family = normalize_space(page.get("source_family"))
        page_number = page.get("page_number")

        response = fetch_page(session, url)
        request_count += 1
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1

        final_url = normalize_space(response.get("final_url") or url)
        rows = analyze_page(str(response.get("raw_html") or ""), final_url) if status == 200 else []

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

        page_results.append({
            "source_family": family,
            "page_number": page_number,
            "url": final_url,
            "http_status": status,
            "probe_candidate_count": len(rows),
            "error": response.get("error"),
        })

        print("-" * 60)
        print(f"PAGE {index}")
        print("Family:", family)
        print("Page number:", page_number)
        print("URL:", final_url)
        print("HTTP:", status)
        print("Probe candidates:", len(rows))

    # Contract signature dedupe: 구조 자체를 묶는다.
    signature_map: Dict[Tuple[str, str, Tuple[str, ...]], Dict[str, Any]] = {}
    for row in raw_candidates:
        js_functions = tuple(sorted({normalize_space(x.get("function")) for x in row.get("javascript_contracts") or [] if normalize_space(x.get("function"))}))
        static_paths = tuple(sorted({urlparse(a.get("absolute_href") or "").path for a in row.get("anchors") or [] if a.get("absolute_href")}))
        key = (normalize_space(row.get("source_family")), "|".join(static_paths), js_functions)
        if key not in signature_map:
            signature_map[key] = {
                "source_family": row.get("source_family"),
                "static_detail_paths": list(static_paths),
                "javascript_functions": list(js_functions),
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
        sig = signature_map[key]
        if len(sig["sample_rows"]) < 5:
            sig["sample_rows"].append({
                "row_text": row.get("row_text"),
                "meaningful_anchor_texts": row.get("meaningful_anchor_texts"),
                "dates": row.get("dates"),
                "notice_numbers": row.get("notice_numbers"),
                "anchors": row.get("anchors"),
                "javascript_contracts": row.get("javascript_contracts"),
                "data_identity": row.get("data_identity"),
                "hidden_identity": row.get("hidden_identity"),
            })
        sig["page_numbers"] = sorted(set(sig["page_numbers"] + [row.get("page_number")]))
        sig["reasons"] = unique_strings(sig["reasons"] + (row.get("reasons") or []))

    contracts = list(signature_map.values())
    contracts.sort(key=lambda x: (normalize_space(x.get("source_family")), "|".join(x.get("static_detail_paths") or []), "|".join(x.get("javascript_functions") or [])))

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

    resolution = "COMPETENT_AUTHORITY_DETAIL_CONTRACT_PROBE_COMPLETED" if contracts else "COMPETENT_AUTHORITY_DETAIL_CONTRACT_PROBE_NO_STRUCTURE"
    next_action = (
        "복원된 source-specific detail contract를 기반으로 T-16-S2 row parser를 작성한다."
        if contracts else
        "정적 HTML row에서 detail contract를 복원하지 못했다. script/form 전역 contract 분석 또는 다른 archive source를 검토한다."
    )

    output = {
        "step": "STEP 17-21-C-16-8-T-16-S1 Competent Authority Detail Contract / Row Structure Probe",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {"resolution_type": RESOLUTION_TYPE, "negative_evidence_allowed": False, "source_failure_site_status": "UNKNOWN"},
        "summary": {
            "selected_probe_page_count": len(pages),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "raw_probe_candidate_count": len(raw_candidates),
            "detail_contract_count": len(contracts),
            "next_stage_contract_pool_count": len(next_stage_contract_pool),
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
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    target_query_leakage = sum(1 for x in raw_candidates + contracts if x.get("target_query_executed") is True)
    document_candidate_leakage = sum(1 for x in raw_candidates + contracts if x.get("document_candidate") is True)
    unsafe = sum(1 for x in raw_candidates + contracts if x.get("verified_positive") or x.get("runtime_registration_allowed") or x.get("site_positive_allowed") or x.get("site_negative_allowed") or x.get("final_positive_promotion_allowed"))
    cross_host_static_leakage = sum(
        1 for row in raw_candidates
        for anchor in row.get("anchors") or []
        if anchor.get("absolute_href") and (not is_government_host(hostname(anchor["absolute_href"])) or not same_host(row.get("page_url") or "", anchor["absolute_href"]))
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "T-16 input exists": INPUT_PATH.exists(),
        "T-16 input parsed": isinstance(data, dict),
        "probe page budget respected": request_count <= MAX_TOTAL_REQUESTS,
        "target query execution disabled": target_query_leakage == 0,
        "document candidate promotion disabled": document_candidate_leakage == 0,
        "static detail cross-host leakage zero": cross_host_static_leakage == 0,
        "unsafe promotion leakage zero": unsafe == 0,
        "runtime registration remains blocked": output["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output["site_negative_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("DETAIL CONTRACT PROBE RESULT")
    print("=" * 60)
    print("Selected probe page count:", len(pages))
    print("Request count:", request_count)
    print("Raw probe candidate count:", len(raw_candidates))
    print("Detail contract count:", len(contracts))
    print("Next-stage contract pool count:", len(next_stage_contract_pool))
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
    print("Cross-host static detail leakage:", cross_host_static_leakage)
    print("Unsafe promotion leakage:", unsafe)
    print("all_pass:", all(validations.values()))

    if not all(validations.values()):
        raise AssertionError("UQQ700 detail contract probe regression failed")


if __name__ == "__main__":
    main()
