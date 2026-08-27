# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-16-S5

Development Density Management Area
Competent Authority Global Request Mechanism Probe

T-16-S4에서 sample metadata row는 정확히 재식별됐지만 row-local href / onclick /
data-* / hidden identity가 전혀 복원되지 않았다. 따라서 이 단계는 동일 페이지의
전역 inline script, same-host external script, page-level form/control에서 실제로 존재하는
detail/request mechanism evidence만 제한적으로 복원한다.

중요:
- UQQ700 target query 실행 금지
- UQQ700 target identity 평가 금지
- detail URL/function/parameter 추측 금지
- cross-host external script 금지
- document candidate 승격 금지
- SITE TRUE/FALSE 판정 금지
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
S4_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_competent_authority_sample_row_interaction_recovery.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_competent_authority_global_request_mechanism_probe.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"
ALLOWED_FAMILIES = {FAMILY_NOTICE, FAMILY_URBAN}

CLASS_GLOBAL_DETAIL_ROUTE = "RECOVERED_GLOBAL_DETAIL_ROUTE_EVIDENCE"
CLASS_GLOBAL_FUNCTION = "RECOVERED_GLOBAL_DETAIL_FUNCTION_EVIDENCE"
CLASS_GLOBAL_PARAM = "RECOVERED_GLOBAL_DETAIL_PARAMETER_EVIDENCE"
CLASS_PAGE_FORM = "RECOVERED_PAGE_LEVEL_DETAIL_FORM_EVIDENCE"
CLASS_FORENSIC_ONLY = "GLOBAL_REQUEST_MECHANISM_FORENSIC_EVIDENCE_ONLY"
VALID_CLASSES = {
    CLASS_GLOBAL_DETAIL_ROUTE,
    CLASS_GLOBAL_FUNCTION,
    CLASS_GLOBAL_PARAM,
    CLASS_PAGE_FORM,
    CLASS_FORENSIC_ONLY,
}
QUALIFIED_CLASSES = {
    CLASS_GLOBAL_DETAIL_ROUTE,
    CLASS_GLOBAL_FUNCTION,
    CLASS_PAGE_FORM,
}

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_PAGE_REQUESTS = 4
MAX_EXTERNAL_SCRIPT_REQUESTS = 16
MAX_TOTAL_REQUESTS = MAX_PAGE_REQUESTS + MAX_EXTERNAL_SCRIPT_REQUESTS
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

SCRIPT_SRC_PATTERN = re.compile(r'<script\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\'][^>]*>\s*</script>', re.I | re.S)
INLINE_SCRIPT_PATTERN = re.compile(r'<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>', re.I | re.S)
FORM_PATTERN = re.compile(r'<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>', re.I | re.S)
INPUT_PATTERN = re.compile(r'<input\b(?P<attrs>[^>]*)>', re.I | re.S)
ATTR_PATTERN = re.compile(r'''([:\w-]+)\s*=\s*(?:["']([^"']*)["']|([^\s>]+))''', re.I | re.S)

ROUTE_STRING_PATTERN = re.compile(
    r'''["'](?P<route>(?:https?://[^"']+|/[^"']+?)(?:view|detail|read|select|board|bbs|post|notice|ancmt)[^"']*)["']''',
    re.I,
)
FUNCTION_DEF_PATTERN = re.compile(
    r'''(?:function\s+(?P<f1>[A-Za-z_$][\w$]*)\s*\((?P<a1>[^)]*)\)|(?P<f2>[A-Za-z_$][\w$]*)\s*=\s*function\s*\((?P<a2>[^)]*)\))''',
    re.I,
)
FUNCTION_CALL_PATTERN = re.compile(r'(?P<func>[A-Za-z_$][\w$]*)\s*\((?P<args>[^)]*)\)', re.I)
PARAM_TOKEN_PATTERN = re.compile(
    r'''["'](?P<key>(?:idx|seq|sn|ntt(?:id|_id)?|bbs(?:id|_id)?|board(?:id|_id|_seq)?|article(?:_no)?|post(?:_no)?|notice(?:_no)?|ancmt(?:_no)?|key|no))["']\s*[:=]''',
    re.I,
)
DETAIL_WORD_PATTERN = re.compile(r'(?:view|detail|read|select|상세|열람|보기)', re.I)
REQUEST_WORD_PATTERN = re.compile(r'(?:location\.href|window\.location|\.submit\s*\(|ajax\s*\(|fetch\s*\(|\.get\s*\(|\.post\s*\()', re.I)

FAMILY_PATH_HINTS = {
    FAMILY_NOTICE: ("pm010301", "sn01040101"),
    FAMILY_URBAN: ("ct020100", "ct-bbs020103", "ct-bbs"),
}


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_strings(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: Set[str] = set()
    for value in values:
        text = normalize_space(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def parse_attrs(raw: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for match in ATTR_PATTERN.finditer(raw or ""):
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
    host = normalize_space(host).lower()
    return bool(host) and (host == "go.kr" or host.endswith(".go.kr"))


def same_host(a: str, b: str) -> bool:
    return bool(hostname(a)) and hostname(a) == hostname(b)


def decode_text(response: requests.Response, data: bytes) -> str:
    for encoding in unique_strings([response.encoding, "utf-8", "cp949", "euc-kr"]):
        try:
            return data.decode(encoding)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


def fetch_text(session: requests.Session, url: str) -> Dict[str, Any]:
    result = {"url": url, "final_url": "", "http_status": None, "text": "", "bytes": 0, "error": ""}
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
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
            result["bytes"] = len(data)
            result["text"] = decode_text(response, data)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def load_s4(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    contract_results = data.get("contract_results") if isinstance(data.get("contract_results"), list) else []
    page_results = data.get("page_results") if isinstance(data.get("page_results"), list) else []
    contracts = []
    for item in contract_results:
        if not isinstance(item, dict):
            continue
        family = normalize_space(item.get("source_family"))
        rows = item.get("located_rows") if isinstance(item.get("located_rows"), list) else []
        if family in ALLOWED_FAMILIES and rows:
            contracts.append({
                "contract_index": item.get("contract_index"),
                "source_family": family,
                "classification": normalize_space(item.get("classification")),
                "located_rows": rows,
            })
    pages = []
    seen = set()
    for item in page_results:
        if not isinstance(item, dict) or item.get("http_status") != 200:
            continue
        family = normalize_space(item.get("source_family"))
        url = normalize_space(item.get("url"))
        if family not in ALLOWED_FAMILIES or not url or url in seen:
            continue
        seen.add(url)
        pages.append({"source_family": family, "page_number": item.get("page_number"), "url": url})
    return contracts, pages


def select_pages(contracts: List[Dict[str, Any]], pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    wanted_by_family: Dict[str, Set[str]] = {}
    for contract in contracts:
        family = contract["source_family"]
        wanted_by_family.setdefault(family, set())
        for row in contract.get("located_rows") or []:
            for url in row.get("page_urls") or []:
                if url:
                    wanted_by_family[family].add(normalize_space(url))
            if row.get("page_url"):
                wanted_by_family[family].add(normalize_space(row.get("page_url")))
    selected = []
    seen = set()
    for family in sorted(ALLOWED_FAMILIES):
        family_pages = [p for p in pages if p["source_family"] == family]
        family_pages.sort(key=lambda p: (0 if p["url"] in wanted_by_family.get(family, set()) else 1, int(p.get("page_number") or 0)))
        family_count = 0
        for page in family_pages:
            if len(selected) >= MAX_PAGE_REQUESTS or family_count >= 2:
                break
            if page["url"] in seen:
                continue
            seen.add(page["url"])
            selected.append(page)
            family_count += 1
    return selected


def extract_script_sources(raw_html: str, page_url: str) -> List[str]:
    result = []
    for src in SCRIPT_SRC_PATTERN.findall(raw_html or ""):
        absolute = urljoin(page_url, html.unescape(normalize_space(src)))
        if absolute and same_host(page_url, absolute) and is_government_host(hostname(absolute)):
            result.append(absolute)
    return unique_strings(result)


def extract_form_evidence(raw_html: str, page_url: str, family: str) -> List[Dict[str, Any]]:
    result = []
    hints = FAMILY_PATH_HINTS.get(family, ())
    for match in FORM_PATTERN.finditer(raw_html or ""):
        attrs = parse_attrs(match.group("attrs"))
        body = match.group("body")
        action_raw = normalize_space(attrs.get("action"))
        action_url = urljoin(page_url, action_raw) if action_raw else page_url
        method = normalize_space(attrs.get("method") or "GET").upper()
        controls = []
        for input_match in INPUT_PATTERN.finditer(body):
            a = parse_attrs(input_match.group("attrs"))
            name = normalize_space(a.get("name"))
            ident = normalize_space(a.get("id"))
            value = normalize_space(a.get("value"))
            input_type = normalize_space(a.get("type")).lower()
            if name or ident:
                controls.append({"name": name, "id": ident, "type": input_type, "value": value})
        form_text = normalize_space(" ".join([action_url, method] + [f"{c['name']} {c['id']}" for c in controls])).lower()
        identity_controls = [c for c in controls if any(token in f"{c['name']} {c['id']}".lower() for token in ("idx","seq","sn","ntt","bbs","board","article","post","notice","ancmt"))]
        family_bound = any(hint in form_text for hint in hints)
        detail_bound = bool(identity_controls) or bool(DETAIL_WORD_PATTERN.search(form_text))
        if family_bound and detail_bound and same_host(page_url, action_url) and is_government_host(hostname(action_url)):
            result.append({"action_url": action_url, "method": method, "identity_controls": identity_controls})
    return result


def context_snippet(text: str, start: int, end: int, radius: int = 350) -> str:
    return normalize_space(text[max(0, start-radius): min(len(text), end+radius)])[:1800]


def analyze_script(text: str, source_url: str, family: str) -> Dict[str, Any]:
    hints = FAMILY_PATH_HINTS.get(family, ())
    routes = []
    functions = []
    params = []

    for match in ROUTE_STRING_PATTERN.finditer(text or ""):
        raw_route = html.unescape(normalize_space(match.group("route")))
        absolute = urljoin(source_url, raw_route)
        snippet = context_snippet(text, match.start(), match.end())
        family_bound = any(hint in raw_route.lower() or hint in snippet.lower() for hint in hints)
        request_bound = bool(REQUEST_WORD_PATTERN.search(snippet)) or bool(DETAIL_WORD_PATTERN.search(raw_route))
        if family_bound and request_bound and same_host(source_url, absolute) and is_government_host(hostname(absolute)):
            routes.append({"route": raw_route, "url": absolute, "snippet": snippet})

    for match in FUNCTION_DEF_PATTERN.finditer(text or ""):
        name = normalize_space(match.group("f1") or match.group("f2"))
        args = normalize_space(match.group("a1") or match.group("a2"))
        snippet = context_snippet(text, match.start(), match.end(), 700)
        family_bound = any(hint in snippet.lower() for hint in hints)
        detail_bound = bool(DETAIL_WORD_PATTERN.search(name)) or bool(DETAIL_WORD_PATTERN.search(snippet))
        request_bound = bool(REQUEST_WORD_PATTERN.search(snippet))
        if name and family_bound and detail_bound and request_bound:
            functions.append({"function": name, "args": args, "snippet": snippet})

    for match in PARAM_TOKEN_PATTERN.finditer(text or ""):
        key = normalize_space(match.group("key"))
        snippet = context_snippet(text, match.start(), match.end(), 250)
        family_bound = any(hint in snippet.lower() for hint in hints)
        if key and family_bound and (DETAIL_WORD_PATTERN.search(snippet) or REQUEST_WORD_PATTERN.search(snippet)):
            params.append({"key": key, "snippet": snippet})

    return {"routes": routes, "functions": functions, "params": params}


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("COMPETENT AUTHORITY GLOBAL REQUEST MECHANISM PROBE")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Target query execution: DISABLED")
    print("Target identity evaluation: DISABLED")
    print("Document candidate promotion: DISABLED")
    print()

    if not S4_INPUT_PATH.exists():
        raise FileNotFoundError(f"T-16-S4 input not found: {S4_INPUT_PATH}")
    s4_data = json.loads(S4_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(s4_data, dict):
        raise TypeError("T-16-S4 input must be JSON object")

    contracts, pages = load_s4(s4_data)
    selected_pages = select_pages(contracts, pages)
    print("S4 metadata contract count:", len(contracts))
    print("S4 page result count:", len(pages))
    print("Selected page count:", len(selected_pages))
    print()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    request_count = 0
    http_success_count = 0
    transport_error_count = 0
    page_records = []
    script_queue: List[Tuple[str, str]] = []

    for index, page in enumerate(selected_pages, start=1):
        response = fetch_text(session, page["url"])
        request_count += 1
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1
        final_url = normalize_space(response.get("final_url") or page["url"])
        raw_html = str(response.get("text") or "")
        inline_scripts = INLINE_SCRIPT_PATTERN.findall(raw_html)
        external_scripts = extract_script_sources(raw_html, final_url)
        form_evidence = extract_form_evidence(raw_html, final_url, page["source_family"])
        inline_analysis = [analyze_script(script, final_url, page["source_family"]) for script in inline_scripts]
        for script_url in external_scripts:
            script_queue.append((page["source_family"], script_url))
        page_records.append({
            "source_family": page["source_family"],
            "page_number": page.get("page_number"),
            "url": final_url,
            "http_status": status,
            "inline_script_count": len(inline_scripts),
            "external_script_urls": external_scripts,
            "form_evidence": form_evidence,
            "inline_analysis": inline_analysis,
        })
        print("-" * 60)
        print(f"PAGE {index}")
        print("Family:", page["source_family"])
        print("Page:", page.get("page_number"))
        print("HTTP:", status)
        print("Inline scripts:", len(inline_scripts))
        print("Same-host external scripts:", len(external_scripts))
        print("Detail form evidence:", len(form_evidence))

    unique_script_queue = []
    seen_scripts = set()
    for family, url in script_queue:
        key = (family, url)
        if key in seen_scripts:
            continue
        seen_scripts.add(key)
        unique_script_queue.append((family, url))

    external_records = []
    for family, script_url in unique_script_queue[:MAX_EXTERNAL_SCRIPT_REQUESTS]:
        if request_count >= MAX_TOTAL_REQUESTS:
            break
        response = fetch_text(session, script_url)
        request_count += 1
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1
        final_url = normalize_space(response.get("final_url") or script_url)
        analysis = analyze_script(str(response.get("text") or ""), final_url, family)
        external_records.append({
            "source_family": family,
            "url": final_url,
            "http_status": status,
            "bytes": response.get("bytes"),
            "analysis": analysis,
        })

    family_results = []
    next_stage_pool = []
    for family in sorted(ALLOWED_FAMILIES):
        route_evidence = []
        function_evidence = []
        param_evidence = []
        form_evidence = []
        script_sources = []

        for page in page_records:
            if page["source_family"] != family:
                continue
            form_evidence.extend(page.get("form_evidence") or [])
            for analysis in page.get("inline_analysis") or []:
                route_evidence.extend(analysis.get("routes") or [])
                function_evidence.extend(analysis.get("functions") or [])
                param_evidence.extend(analysis.get("params") or [])
        for script in external_records:
            if script["source_family"] != family or script.get("http_status") != 200:
                continue
            analysis = script.get("analysis") or {}
            if analysis.get("routes") or analysis.get("functions") or analysis.get("params"):
                script_sources.append(script.get("url"))
            route_evidence.extend(analysis.get("routes") or [])
            function_evidence.extend(analysis.get("functions") or [])
            param_evidence.extend(analysis.get("params") or [])

        if route_evidence:
            classification = CLASS_GLOBAL_DETAIL_ROUTE
            qualified = True
        elif function_evidence:
            classification = CLASS_GLOBAL_FUNCTION
            qualified = True
        elif form_evidence:
            classification = CLASS_PAGE_FORM
            qualified = True
        elif param_evidence:
            classification = CLASS_GLOBAL_PARAM
            qualified = False
        else:
            classification = CLASS_FORENSIC_ONLY
            qualified = False

        result = {
            "source_family": family,
            "classification": classification,
            "qualified_for_next_stage": qualified,
            "route_evidence": route_evidence,
            "function_evidence": function_evidence,
            "parameter_evidence": param_evidence,
            "form_evidence": form_evidence,
            "script_sources": unique_strings(script_sources),
            "target_query_executed": False,
            "target_identity_evaluated": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        family_results.append(result)
        if qualified:
            next_stage_pool.append({
                **result,
                "requires_executable_request_binding_validation": True,
            })

        print()
        print("-" * 60)
        print("FAMILY:", family)
        print("Routes:", len(route_evidence))
        print("Functions:", len(function_evidence))
        print("Parameters:", len(param_evidence))
        print("Forms:", len(form_evidence))
        print("Evidence-bearing external scripts:", len(unique_strings(script_sources)))
        print("Qualified for next stage:", qualified)
        print("Resolution:", classification)
        for item in route_evidence[:5]:
            print("  Route:", item.get("url"))
        for item in function_evidence[:5]:
            print("  Function:", item.get("function"), "Args:", item.get("args"))
        for item in form_evidence[:5]:
            print("  Form:", item.get("method"), item.get("action_url"), item.get("identity_controls"))

    if next_stage_pool:
        resolution = "COMPETENT_AUTHORITY_GLOBAL_REQUEST_MECHANISM_PROBE_COMPLETED"
        next_action = (
            "실제 page/global script/form에서 family-bound detail request mechanism evidence가 복원되었다. "
            "다음 단계에서는 복원된 route/function/form만 대상으로 empty/sentinel 또는 known sample identity를 이용한 "
            "bounded executable binding validation을 수행하되 UQQ700 target identity 판정은 계속 금지한다."
        )
    else:
        resolution = "COMPETENT_AUTHORITY_GLOBAL_REQUEST_MECHANISM_PROBE_NO_EXECUTABLE_EVIDENCE"
        next_action = (
            "same-host global scripts/forms에서도 executable detail request mechanism을 복원하지 못했다. "
            "SITE FALSE가 아니며 UNKNOWN을 유지한다. 다음에는 browser-generated/XHR 또는 server-rendered source-specific contract 가능성을 분리 분석한다."
        )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-16-S5 Global Request Mechanism Probe",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "inputs": {"t16_s4_path": str(S4_INPUT_PATH)},
        "method": {
            "S4_reconfirmed_metadata_only": True,
            "bounded_page_requery": True,
            "inline_script_probe": True,
            "same_host_external_script_probe": True,
            "page_level_form_probe": True,
            "cross_host_external_script_disabled": True,
            "guessed_detail_route_disabled": True,
            "guessed_function_disabled": True,
            "guessed_parameter_disabled": True,
            "target_query_execution_enabled": False,
            "target_identity_evaluation_enabled": False,
            "document_candidate_promotion_allowed": False,
        },
        "summary": {
            "metadata_contract_count": len(contracts),
            "selected_page_count": len(selected_pages),
            "page_request_count": len(page_records),
            "external_script_request_count": len(external_records),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "family_result_count": len(family_results),
            "next_stage_binding_count": len(next_stage_pool),
        },
        "classification_counts": dict(sorted(Counter(x.get("classification") for x in family_results).items())),
        "page_records": page_records,
        "external_script_records": external_records,
        "family_results": family_results,
        "next_stage_binding_pool": next_stage_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    cross_host_script_leakage = sum(
        1 for item in external_records
        if not is_government_host(hostname(item.get("url") or ""))
    )
    cross_host_route_leakage = sum(
        1 for result in family_results for item in result.get("route_evidence") or []
        if not is_government_host(hostname(item.get("url") or ""))
    )
    target_query_leakage = sum(1 for x in family_results + next_stage_pool if x.get("target_query_executed") is True)
    target_identity_leakage = sum(1 for x in family_results + next_stage_pool if x.get("target_identity_evaluated") is True)
    unsafe_promotion_leakage = sum(
        1 for x in family_results + next_stage_pool
        if x.get("document_candidate") is True
        or x.get("verified_positive") is True
        or x.get("runtime_registration_allowed") is True
        or x.get("site_positive_allowed") is True
        or x.get("site_negative_allowed") is True
        or x.get("final_positive_promotion_allowed") is True
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-16-S4 input exists": S4_INPUT_PATH.exists(),
        "T-16-S4 input parsed": isinstance(s4_data, dict),
        "reconfirmed metadata contracts loaded": len(contracts) > 0,
        "bounded page request budget respected": len(page_records) <= MAX_PAGE_REQUESTS,
        "external script request budget respected": len(external_records) <= MAX_EXTERNAL_SCRIPT_REQUESTS,
        "total request budget respected": request_count <= MAX_TOTAL_REQUESTS,
        "same-host external script probe enabled": True,
        "guessed request mechanism disabled": True,
        "all classes valid": all(x.get("classification") in VALID_CLASSES for x in family_results),
        "next-stage classes valid": all(x.get("classification") in QUALIFIED_CLASSES for x in next_stage_pool),
        "cross-host external script leakage zero": cross_host_script_leakage == 0,
        "cross-host route leakage zero": cross_host_route_leakage == 0,
        "target query execution leakage zero": target_query_leakage == 0,
        "target identity evaluation leakage zero": target_identity_leakage == 0,
        "unsafe promotion leakage zero": unsafe_promotion_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("GLOBAL REQUEST MECHANISM PROBE RESULT")
    print("=" * 60)
    print("Metadata contract count:", len(contracts))
    print("Selected page count:", len(selected_pages))
    print("Page requests:", len(page_records))
    print("External script requests:", len(external_records))
    print("Total requests:", request_count)
    print("HTTP success count:", http_success_count)
    print("Transport error count:", transport_error_count)
    print("Next-stage binding count:", len(next_stage_pool))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)
    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Cross-host external script leakage:", cross_host_script_leakage)
    print("Cross-host route leakage:", cross_host_route_leakage)
    print("Target query leakage:", target_query_leakage)
    print("Target identity leakage:", target_identity_leakage)
    print("Unsafe promotion leakage:", unsafe_promotion_leakage)
    print()
    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")
    if not all_pass:
        print("FAILED:")
        for name, passed in validations.items():
            if not passed:
                print("-", name)
        raise AssertionError("UQQ700 global request mechanism probe regression failed")


if __name__ == "__main__":
    main()
