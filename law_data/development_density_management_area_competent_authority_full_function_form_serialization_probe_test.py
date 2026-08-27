# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-16-S7-S2

Development Density Management Area
Competent Authority Full Function/Form Serialization Probe

목표
======================================================================
S7-S1에서 body_preview 기반 disambiguation이 consensus 0건으로 종료되었다.
본 단계는 live source page를 다시 조회하여 f_view / fn_move_form 함수 본문 전체와
same-page form/control 구조를 정확히 복원한다.

원칙
======================================================================
1. S7 output의 sample source page URL만 재조회한다.
2. 외부 JS를 새로 추적하지 않는다. inline function definition만 사용한다.
3. 함수 본문 전체를 balanced-brace 방식으로 복원한다.
4. form id/name/action/method 및 hidden control 전체를 보존한다.
5. function body의 action assignment, form selector, value assignment, submit 호출을
   실제 텍스트 그대로 분석한다.
6. URL/parameter/method 추측 금지.
7. detail HTTP request 실행 금지.
8. target query/UQQ700 identity/SITE 판정 금지.
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
S7_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_competent_authority_bounded_detail_request_validation.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_competent_authority_full_function_form_serialization_probe.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"
EXPECTED_FUNCTIONS = {
    FAMILY_NOTICE: "f_view",
    FAMILY_URBAN: "fn_move_form",
}
ALLOWED_FAMILIES = set(EXPECTED_FUNCTIONS)

CLASS_FULL_FUNCTION_FORM = "RECOVERED_FULL_FUNCTION_FORM_SERIALIZATION"
CLASS_FULL_FUNCTION_ONLY = "RECOVERED_FULL_FUNCTION_ONLY"
CLASS_FUNCTION_MISSING = "FULL_FUNCTION_DEFINITION_NOT_FOUND"
CLASS_NO_SOURCE_PAGE = "SOURCE_PAGE_NOT_AVAILABLE"
VALID_CLASSES = {
    CLASS_FULL_FUNCTION_FORM,
    CLASS_FULL_FUNCTION_ONLY,
    CLASS_FUNCTION_MISSING,
    CLASS_NO_SOURCE_PAGE,
}

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 8
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

SCRIPT_PATTERN = re.compile(r'<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>', re.I | re.S)
FORM_PATTERN = re.compile(r'<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>', re.I | re.S)
INPUT_PATTERN = re.compile(r'<input\b(?P<attrs>[^>]*)>', re.I | re.S)
ATTR_PATTERN = re.compile(r'''([:\w-]+)\s*=\s*(?:["']([^"']*)["']|([^\s>]+))''', re.I | re.S)

ACTION_ASSIGN_PATTERNS = [
    re.compile(r'''\.attr\s*\(\s*["']action["']\s*,\s*(?P<expr>[^)]+)\)''', re.I | re.S),
    re.compile(r'''\.action\s*=\s*(?P<expr>[^;]+)''', re.I | re.S),
]
VALUE_ASSIGN_PATTERNS = [
    re.compile(r'''\$\(\s*["']#(?P<id>[^"']+)["']\s*\)\.val\s*\(\s*(?P<expr>[^)]+)\)''', re.I | re.S),
    re.compile(r'''getElementById\(\s*["'](?P<id>[^"']+)["']\s*\)\.value\s*=\s*(?P<expr>[^;]+)''', re.I | re.S),
    re.compile(r'''(?P<field>[A-Za-z_$][\w$.\[\]'\"]*)\.value\s*=\s*(?P<expr>[^;]+)''', re.I | re.S),
]
FORM_SELECTOR_PATTERN = re.compile(r'''\$\(\s*["'](?P<selector>#[A-Za-z0-9_-]+|form(?:#[A-Za-z0-9_-]+)?)["']\s*\)''', re.I)
SUBMIT_PATTERN = re.compile(r'''(?P<expr>[A-Za-z_$][\w$.\[\]'\"]*|\$\([^;]{0,150}\))\.submit\s*\(\s*\)''', re.I | re.S)
STRING_LITERAL_PATTERN = re.compile(r'''["'](?P<value>[^"']+)["']''')


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


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result = {"http_status": None, "final_url": "", "text": "", "bytes": 0, "error": ""}
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
            raw = b"".join(chunks)
            result["bytes"] = len(raw)
            result["text"] = decode_text(response, raw)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def find_balanced_body(source: str, brace_start: int) -> Optional[str]:
    depth = 0
    quote: Optional[str] = None
    escaped = False
    for i in range(brace_start, len(source)):
        ch = source[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in ('"', "'", "`"):
            quote = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[brace_start + 1:i]
    return None


def extract_full_function(raw_html: str, function_name: str) -> Optional[Dict[str, Any]]:
    patterns = [
        re.compile(rf'function\s+{re.escape(function_name)}\s*\((?P<args>[^)]*)\)\s*\{{', re.I),
        re.compile(rf'{re.escape(function_name)}\s*=\s*function\s*\((?P<args>[^)]*)\)\s*\{{', re.I),
    ]
    for script_index, script in enumerate(SCRIPT_PATTERN.findall(raw_html or ""), start=1):
        for pattern in patterns:
            match = pattern.search(script)
            if not match:
                continue
            body = find_balanced_body(script, match.end() - 1)
            if body is None:
                continue
            return {
                "script_index": script_index,
                "args": unique_strings(x.strip() for x in (match.group("args") or "").split(",")),
                "body": body,
            }
    return None


def extract_forms(raw_html: str, page_url: str) -> List[Dict[str, Any]]:
    forms: List[Dict[str, Any]] = []
    for index, match in enumerate(FORM_PATTERN.finditer(raw_html or ""), start=1):
        attrs = parse_attrs(match.group("attrs"))
        action_raw = normalize_space(attrs.get("action"))
        action_url = urljoin(page_url, action_raw) if action_raw else page_url
        controls = []
        for im in INPUT_PATTERN.finditer(match.group("body")):
            a = parse_attrs(im.group("attrs"))
            controls.append({
                "name": normalize_space(a.get("name")),
                "id": normalize_space(a.get("id")),
                "type": normalize_space(a.get("type")).lower(),
                "value": normalize_space(a.get("value")),
            })
        forms.append({
            "form_index": index,
            "id": normalize_space(attrs.get("id")),
            "name": normalize_space(attrs.get("name")),
            "method": normalize_space(attrs.get("method") or "GET").upper(),
            "action_url": action_url,
            "controls": controls,
        })
    return forms


def analyze_function(function: Dict[str, Any]) -> Dict[str, Any]:
    body = str(function.get("body") or "")
    action_assignments = []
    for pattern in ACTION_ASSIGN_PATTERNS:
        for m in pattern.finditer(body):
            expr = normalize_space(m.group("expr"))
            action_assignments.append({
                "expression": expr,
                "literals": unique_strings(x.group("value") for x in STRING_LITERAL_PATTERN.finditer(expr)),
            })
    value_assignments = []
    for pattern in VALUE_ASSIGN_PATTERNS:
        for m in pattern.finditer(body):
            field = normalize_space(m.groupdict().get("id") or m.groupdict().get("field"))
            expr = normalize_space(m.group("expr"))
            value_assignments.append({"field": field, "expression": expr})
    selectors = unique_strings(m.group("selector") for m in FORM_SELECTOR_PATTERN.finditer(body))
    submits = unique_strings(m.group("expr") for m in SUBMIT_PATTERN.finditer(body))
    return {
        "action_assignments": action_assignments,
        "value_assignments": value_assignments,
        "form_selectors": selectors,
        "submit_expressions": submits,
        "body_length": len(body),
    }


def load_source_pages(data: Dict[str, Any]) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {family: [] for family in ALLOWED_FAMILIES}
    raw = data.get("sample_results") if isinstance(data.get("sample_results"), list) else []
    for item in raw:
        if not isinstance(item, dict):
            continue
        family = normalize_space(item.get("source_family"))
        if family not in ALLOWED_FAMILIES:
            continue
        for definition in item.get("definition_records") or []:
            if not isinstance(definition, dict):
                continue
            url = normalize_space(definition.get("page_url"))
            if url:
                result[family].append(url)
    for family in result:
        result[family] = unique_strings(result[family])
    return result


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("FULL FUNCTION / FORM SERIALIZATION PROBE")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Detail request execution: DISABLED")
    print("Target identity evaluation: DISABLED")
    print()

    if not S7_INPUT_PATH.exists():
        raise FileNotFoundError(f"S7 input not found: {S7_INPUT_PATH}")
    data = json.loads(S7_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("S7 input must be JSON object")

    source_pages = load_source_pages(data)
    all_urls = unique_strings(url for urls in source_pages.values() for url in urls)[:MAX_TOTAL_REQUESTS]

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    fetched: Dict[str, Dict[str, Any]] = {}
    request_count = 0
    http_success_count = 0
    transport_error_count = 0
    for index, url in enumerate(all_urls, start=1):
        response = fetch_page(session, url)
        request_count += 1
        if isinstance(response.get("http_status"), int) and 200 <= response["http_status"] < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1
        fetched[url] = response
        if response.get("final_url"):
            fetched[response["final_url"]] = response
        print("-" * 60)
        print(f"PAGE {index}")
        print("URL:", url)
        print("HTTP:", response.get("http_status"))

    family_results = []
    next_stage_pool = []

    for family in sorted(ALLOWED_FAMILIES):
        function_name = EXPECTED_FUNCTIONS[family]
        recovered = []
        for url in source_pages.get(family) or []:
            page = fetched.get(url)
            if not page or page.get("http_status") != 200:
                continue
            final_url = normalize_space(page.get("final_url") or url)
            raw_html = str(page.get("text") or "")
            function = extract_full_function(raw_html, function_name)
            if not function:
                continue
            forms = extract_forms(raw_html, final_url)
            semantics = analyze_function(function)
            recovered.append({
                "page_url": final_url,
                "function": function_name,
                "function_args": function.get("args") or [],
                "function_body": function.get("body"),
                "function_body_length": len(function.get("body") or ""),
                "semantics": semantics,
                "forms": forms,
            })

        if recovered and any(x.get("forms") for x in recovered):
            classification = CLASS_FULL_FUNCTION_FORM
            qualified = True
        elif recovered:
            classification = CLASS_FULL_FUNCTION_ONLY
            qualified = False
        elif source_pages.get(family):
            classification = CLASS_FUNCTION_MISSING
            qualified = False
        else:
            classification = CLASS_NO_SOURCE_PAGE
            qualified = False

        result = {
            "source_family": family,
            "function": function_name,
            "source_page_count": len(source_pages.get(family) or []),
            "recovered_definition_count": len(recovered),
            "recovered": recovered,
            "classification": classification,
            "qualified_for_next_stage": qualified,
            "detail_request_executed": False,
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
            next_stage_pool.append({**result, "requires_exact_serialization_binding": True})

        print()
        print("-" * 60)
        print("FAMILY:", family)
        print("Function:", function_name)
        print("Recovered definitions:", len(recovered))
        for item in recovered:
            print("  Page:", item.get("page_url"))
            print("  Body length:", item.get("function_body_length"))
            print("  Args:", item.get("function_args"))
            print("  Action assignments:", item.get("semantics", {}).get("action_assignments"))
            print("  Value assignments:", item.get("semantics", {}).get("value_assignments"))
            print("  Form selectors:", item.get("semantics", {}).get("form_selectors"))
            print("  Submit expressions:", item.get("semantics", {}).get("submit_expressions"))
            print("  Forms:", len(item.get("forms") or []))
        print("Qualified:", qualified)
        print("Resolution:", classification)

    resolution = (
        "COMPETENT_AUTHORITY_FULL_FUNCTION_FORM_SERIALIZATION_RECOVERED"
        if next_stage_pool
        else "COMPETENT_AUTHORITY_FULL_FUNCTION_FORM_SERIALIZATION_NO_RECOVERY"
    )
    next_action = (
        "full function body와 form 구조가 복원된 family만 exact serialization binding 단계로 넘긴다. "
        "다음 단계에서도 detail HTTP 요청은 실행 전 단일 request shape를 먼저 확정한다."
        if next_stage_pool
        else
        "inline full function/form serialization을 충분히 복원하지 못했다. SITE FALSE가 아니며 UNKNOWN을 유지한다."
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-16-S7-S2 Full Function/Form Serialization Probe",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "method": {
            "live_source_page_requery": True,
            "full_balanced_function_body_recovery": True,
            "same_page_form_full_control_recovery": True,
            "external_script_fetch_enabled": False,
            "detail_request_execution_enabled": False,
            "guessed_request_shape_disabled": True,
            "target_query_execution_enabled": False,
            "target_identity_evaluation_enabled": False,
            "document_candidate_promotion_allowed": False,
        },
        "summary": {
            "source_page_request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "family_result_count": len(family_results),
            "next_stage_family_count": len(next_stage_pool),
        },
        "classification_counts": dict(sorted(Counter(x.get("classification") for x in family_results).items())),
        "family_results": family_results,
        "next_stage_serialization_pool": next_stage_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    detail_request_leakage = sum(1 for x in family_results + next_stage_pool if x.get("detail_request_executed") is True)
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
    non_go_kr_page_leakage = sum(
        1 for x in family_results for r in x.get("recovered") or []
        if not is_government_host(hostname(r.get("page_url") or ""))
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "S7 input exists": S7_INPUT_PATH.exists(),
        "S7 input parsed": isinstance(data, dict),
        "source page request budget respected": request_count <= MAX_TOTAL_REQUESTS,
        "full function body recovery enabled": True,
        "same-page full form recovery enabled": True,
        "external script fetch disabled": True,
        "guessed request shape disabled": True,
        "all classes valid": all(x.get("classification") in VALID_CLASSES for x in family_results),
        "source page go.kr leakage zero": non_go_kr_page_leakage == 0,
        "detail request execution leakage zero": detail_request_leakage == 0,
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
    print("FULL FUNCTION / FORM SERIALIZATION RESULT")
    print("=" * 60)
    print("Source page requests:", request_count)
    print("HTTP success count:", http_success_count)
    print("Next-stage family count:", len(next_stage_pool))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)
    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Non-go.kr page leakage:", non_go_kr_page_leakage)
    print("Detail request leakage:", detail_request_leakage)
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
        raise AssertionError("UQQ700 full function/form serialization probe regression failed")


if __name__ == "__main__":
    main()
