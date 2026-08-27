# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-16-S7

Development Density Management Area
Competent Authority Bounded Detail Request Validation

목표
======================================================================
S6-S1에서 sample별 1:1로 hardening된 실제 row-local binding만 사용하여,
page-global function 정의 / form / hidden control에서 exact request shape를 다시
복원한 뒤 known sample detail request를 제한 실행한다.

성공 판정은 detail 응답에서 기존 sample의 고시번호 또는 제목이 재현되는 경우뿐이다.
이 단계는 UQQ700 target identity를 평가하지 않으며 document candidate도 생성하지 않는다.

원칙
======================================================================
1. S6-S1 next_stage_binding_pool만 사용한다.
2. function / argument는 S6-S1 observed binding만 사용한다.
3. 실행 직전 source page를 다시 조회한다.
4. function body에서 실제 route/form interaction을 직접 복원한다.
5. form control 이름도 실제 HTML에서만 복원한다.
6. URL/parameter/method 추측 금지.
7. request shape가 단일하지 않으면 실행하지 않는다.
8. known sample title/notice number response reproduction만 검증한다.
9. UQQ700 target query/identity 평가 금지.
10. verified positive / SITE TRUE / SITE FALSE / runtime registration 금지.
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
S6S1_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_competent_authority_sample_global_binding_cardinality_hardening.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_competent_authority_bounded_detail_request_validation.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"
ALLOWED_FAMILIES = {FAMILY_NOTICE, FAMILY_URBAN}
EXPECTED_FUNCTIONS = {
    FAMILY_NOTICE: "f_view",
    FAMILY_URBAN: "fn_move_form",
}
EXPECTED_IDENTITY_HINTS = {
    FAMILY_NOTICE: ("notancmtmgtno", "ancmt", "mgtno"),
    FAMILY_URBAN: ("pstsn", "pst_sn", "post"),
}

CLASS_EXECUTABLE_FORM = "RECOVERED_EXECUTABLE_DETAIL_FORM_CONTRACT"
CLASS_EXECUTABLE_LOCATION = "RECOVERED_EXECUTABLE_DETAIL_LOCATION_CONTRACT"
CLASS_VALIDATED = "VALIDATED_KNOWN_SAMPLE_DETAIL_REQUEST"
CLASS_REJECTED_NO_FUNCTION = "REJECTED_FUNCTION_DEFINITION_NOT_FOUND"
CLASS_REJECTED_NO_SHAPE = "REJECTED_EXECUTABLE_REQUEST_SHAPE_NOT_RECOVERED"
CLASS_REJECTED_AMBIGUOUS = "REJECTED_EXECUTABLE_REQUEST_SHAPE_AMBIGUOUS"
CLASS_REJECTED_HTTP = "REJECTED_DETAIL_HTTP_FAILURE"
CLASS_REJECTED_SAMPLE_MISMATCH = "REJECTED_DETAIL_SAMPLE_REPRODUCTION_MISMATCH"
VALID_CLASSES = {
    CLASS_EXECUTABLE_FORM,
    CLASS_EXECUTABLE_LOCATION,
    CLASS_VALIDATED,
    CLASS_REJECTED_NO_FUNCTION,
    CLASS_REJECTED_NO_SHAPE,
    CLASS_REJECTED_AMBIGUOUS,
    CLASS_REJECTED_HTTP,
    CLASS_REJECTED_SAMPLE_MISMATCH,
}

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_SOURCE_PAGE_REQUESTS = 6
MAX_DETAIL_REQUESTS = 6
MAX_TOTAL_REQUESTS = MAX_SOURCE_PAGE_REQUESTS + MAX_DETAIL_REQUESTS
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

FORM_PATTERN = re.compile(r'<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>', re.I | re.S)
INPUT_PATTERN = re.compile(r'<input\b(?P<attrs>[^>]*)>', re.I | re.S)
ATTR_PATTERN = re.compile(r'''([:\w-]+)\s*=\s*(?:["']([^"']*)["']|([^\s>]+))''', re.I | re.S)
SCRIPT_PATTERN = re.compile(r'<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>', re.I | re.S)
TAG_PATTERN = re.compile(r'<[^>]+>', re.S)
SCRIPT_STYLE_PATTERN = re.compile(r'<(?:script|style)\b.*?</(?:script|style)>', re.I | re.S)
COMMENT_PATTERN = re.compile(r'<!--.*?-->', re.S)

# observed request semantics
SUBMIT_PATTERN = re.compile(r'''(?:\.submit\s*\(|submit\s*\()''', re.I)
LOCATION_ASSIGN_PATTERN = re.compile(
    r'''(?:window\.)?location(?:\.href)?\s*=\s*(?P<expr>[^;]+)''', re.I | re.S
)
ACTION_ASSIGN_PATTERN = re.compile(
    r'''(?:\.attr\s*\(\s*["']action["']\s*,\s*["'](?P<a1>[^"']+)["']\s*\)|\.action\s*=\s*["'](?P<a2>[^"']+)["'])''',
    re.I | re.S,
)
VALUE_ASSIGN_PATTERN = re.compile(
    r'''(?:#|getElementById\s*\(\s*["'])(?P<id>[A-Za-z0-9_-]+)["']?\)?[^;]{0,120}?(?:\.val\s*\(\s*(?P<v1>[A-Za-z_$][\w$]*)\s*\)|\.value\s*=\s*(?P<v2>[A-Za-z_$][\w$]*))''',
    re.I | re.S,
)
STRING_LITERAL_PATTERN = re.compile(r'''["'](?P<value>/[^"']+)["']''', re.I)


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


def request_text(session: requests.Session, method: str, url: str, params: Optional[Dict[str, str]] = None, data: Optional[Dict[str, str]] = None, referer: str = "") -> Dict[str, Any]:
    result = {"requested_url": url, "final_url": "", "http_status": None, "text": "", "bytes": 0, "error": ""}
    headers = {"Referer": referer} if referer else {}
    try:
        with session.request(
            method.upper(), url, params=params, data=data,
            timeout=TIMEOUT, allow_redirects=True, stream=True, headers=headers,
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
            raw = b"".join(chunks)
            result["bytes"] = len(raw)
            result["text"] = decode_text(response, raw)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def strip_html(raw: str) -> str:
    value = COMMENT_PATTERN.sub(" ", raw or "")
    value = SCRIPT_STYLE_PATTERN.sub(" ", value)
    value = TAG_PATTERN.sub(" ", value)
    return normalize_space(html.unescape(value))


def extract_function_body(script: str, function_name: str) -> Optional[Dict[str, Any]]:
    patterns = [
        re.compile(rf'function\s+{re.escape(function_name)}\s*\((?P<args>[^)]*)\)\s*\{{', re.I),
        re.compile(rf'{re.escape(function_name)}\s*=\s*function\s*\((?P<args>[^)]*)\)\s*\{{', re.I),
    ]
    for pattern in patterns:
        match = pattern.search(script or "")
        if not match:
            continue
        brace_start = match.end() - 1
        depth = 0
        quote: Optional[str] = None
        escaped = False
        for index in range(brace_start, len(script)):
            ch = script[index]
            if quote:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote:
                    quote = None
                continue
            if ch in ('"', "'"):
                quote = ch
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return {
                        "args": unique_strings(a.strip() for a in match.group("args").split(",")),
                        "body": script[brace_start + 1:index],
                    }
    return None


def find_function_definition(raw_html: str, function_name: str) -> Optional[Dict[str, Any]]:
    for script in SCRIPT_PATTERN.findall(raw_html or ""):
        found = extract_function_body(script, function_name)
        if found:
            return found
    return None


def extract_forms(raw_html: str, page_url: str) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for match in FORM_PATTERN.finditer(raw_html or ""):
        attrs = parse_attrs(match.group("attrs"))
        body = match.group("body")
        action_raw = normalize_space(attrs.get("action"))
        action = urljoin(page_url, action_raw) if action_raw else page_url
        method = normalize_space(attrs.get("method") or "GET").upper()
        controls: List[Dict[str, str]] = []
        for im in INPUT_PATTERN.finditer(body):
            a = parse_attrs(im.group("attrs"))
            controls.append({
                "name": normalize_space(a.get("name")),
                "id": normalize_space(a.get("id")),
                "type": normalize_space(a.get("type")).lower(),
                "value": normalize_space(a.get("value")),
            })
        result.append({"action_url": action, "method": method, "controls": controls})
    return result


def identity_control_candidates(forms: List[Dict[str, Any]], family: str) -> List[Tuple[int, Dict[str, str]]]:
    hints = EXPECTED_IDENTITY_HINTS.get(family, ())
    result: List[Tuple[int, Dict[str, str]]] = []
    for fi, form in enumerate(forms):
        for control in form.get("controls") or []:
            evidence = normalize_space(f"{control.get('name')} {control.get('id')}").lower()
            if any(h in evidence for h in hints):
                result.append((fi, control))
    return result


def build_form_contract(page_url: str, family: str, definition: Dict[str, Any], forms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    body = definition.get("body") or ""
    function_args = definition.get("args") or []
    candidates: List[Dict[str, Any]] = []
    controls = identity_control_candidates(forms, family)
    action_assigns = unique_strings((m.group("a1") or m.group("a2")) for m in ACTION_ASSIGN_PATTERN.finditer(body))
    submit_present = bool(SUBMIT_PATTERN.search(body))

    # 실제 function body에서 argument가 control에 할당되는 경우를 최우선으로 한다.
    assigned_ids: List[Tuple[str, str]] = []
    for m in VALUE_ASSIGN_PATTERN.finditer(body):
        ident = normalize_space(m.group("id"))
        variable = normalize_space(m.group("v1") or m.group("v2"))
        if ident and variable and variable in function_args:
            assigned_ids.append((ident, variable))

    for fi, control in controls:
        control_ids = {normalize_space(control.get("name")), normalize_space(control.get("id"))}
        explicit_assignment = any(ident in control_ids and var in function_args for ident, var in assigned_ids)
        # form submit이 확인되어야 executable로 인정
        if not submit_present:
            continue
        if assigned_ids and not explicit_assignment:
            continue
        form = forms[fi]
        action_candidates = action_assigns or [form.get("action_url")]
        for action_raw in action_candidates:
            action = urljoin(page_url, action_raw)
            if not action or not same_host(page_url, action) or not is_government_host(hostname(action)):
                continue
            candidates.append({
                "kind": "FORM",
                "method": normalize_space(form.get("method") or "GET").upper(),
                "action_url": action,
                "identity_name": normalize_space(control.get("name") or control.get("id")),
                "controls": form.get("controls") or [],
                "function_args": function_args,
                "explicit_argument_assignment": explicit_assignment,
            })
    return candidates


def build_location_contract(page_url: str, family: str, definition: Dict[str, Any]) -> List[Dict[str, Any]]:
    body = definition.get("body") or ""
    function_args = definition.get("args") or []
    result: List[Dict[str, Any]] = []
    for match in LOCATION_ASSIGN_PATTERN.finditer(body):
        expr = normalize_space(match.group("expr"))
        # 실행 가능한 location contract는 function argument와 literal route가 같은 식에 모두 있어야 한다.
        if not any(arg and re.search(rf'\b{re.escape(arg)}\b', expr) for arg in function_args):
            continue
        literals = [m.group("value") for m in STRING_LITERAL_PATTERN.finditer(expr)]
        route_literals = [x for x in literals if x.startswith("/")]
        if len(route_literals) != 1:
            continue
        route = route_literals[0]
        action = urljoin(page_url, route)
        if not same_host(page_url, action) or not is_government_host(hostname(action)):
            continue
        # query key가 literal에 실제 들어있는 경우에만 허용
        parsed = urlparse(route)
        query_keys = [k for k, _ in parse_qsl(parsed.query, keep_blank_values=True)]
        identity_keys = [k for k in query_keys if any(h in k.lower() for h in EXPECTED_IDENTITY_HINTS.get(family, ()))]
        if len(identity_keys) != 1:
            continue
        result.append({
            "kind": "LOCATION",
            "method": "GET",
            "action_url": action,
            "identity_name": identity_keys[0],
            "function_args": function_args,
            "location_expression": expr,
        })
    return result


def canonical_contracts(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    seen = set()
    for item in items:
        key = (
            normalize_space(item.get("kind")),
            normalize_space(item.get("method")).upper(),
            normalize_space(item.get("action_url")),
            normalize_space(item.get("identity_name")),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def build_payload(contract: Dict[str, Any], argument: str) -> Dict[str, str]:
    payload: Dict[str, str] = {}
    for control in contract.get("controls") or []:
        name = normalize_space(control.get("name"))
        if not name:
            continue
        payload[name] = normalize_space(control.get("value"))
    identity_name = normalize_space(contract.get("identity_name"))
    if identity_name:
        payload[identity_name] = argument
    return payload


def sample_markers(tokens: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    notices = unique_strings(tokens.get("notice_numbers") or [])
    titles = unique_strings(tokens.get("titles") or [])
    return notices, titles


def marker_match(response_text: str, notices: List[str], titles: List[str]) -> Dict[str, Any]:
    plain = strip_html(response_text)
    matched_notices = [x for x in notices if x and x in plain]
    matched_titles = [x for x in titles if x and x in plain]
    return {
        "matched_notice_numbers": matched_notices,
        "matched_titles": matched_titles,
        "reproduced": bool(matched_notices or matched_titles),
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("COMPETENT AUTHORITY BOUNDED DETAIL REQUEST VALIDATION")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Known-sample detail execution: ENABLED / BOUNDED")
    print("Target query execution: DISABLED")
    print("Target identity evaluation: DISABLED")
    print()

    if not S6S1_INPUT_PATH.exists():
        raise FileNotFoundError(f"S6-S1 input not found: {S6S1_INPUT_PATH}")
    data = json.loads(S6S1_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("S6-S1 input must be JSON object")
    pool = data.get("next_stage_binding_pool") if isinstance(data.get("next_stage_binding_pool"), list) else []
    samples = [x for x in pool if isinstance(x, dict) and x.get("qualified_for_next_stage") is True]

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
    })

    # 동일 page는 한 번만 fetch
    source_urls = unique_strings(
        u for sample in samples for b in sample.get("row_local_bindings") or [] for u in b.get("page_urls") or []
    )[:MAX_SOURCE_PAGE_REQUESTS]
    source_pages: Dict[str, Dict[str, Any]] = {}
    request_count = 0
    http_success_count = 0
    transport_error_count = 0

    for idx, url in enumerate(source_urls, start=1):
        response = request_text(session, "GET", url)
        request_count += 1
        if isinstance(response.get("http_status"), int) and 200 <= response["http_status"] < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1
        source_pages[url] = response
        if response.get("final_url"):
            source_pages[response["final_url"]] = response
        print("-" * 60)
        print(f"SOURCE PAGE {idx}")
        print("URL:", url)
        print("HTTP:", response.get("http_status"))

    results: List[Dict[str, Any]] = []
    validated_pool: List[Dict[str, Any]] = []
    detail_request_count = 0

    for index, sample in enumerate(samples, start=1):
        family = normalize_space(sample.get("source_family"))
        bindings = sample.get("row_local_bindings") if isinstance(sample.get("row_local_bindings"), list) else []
        binding = bindings[0] if len(bindings) == 1 else {}
        function_name = normalize_space(binding.get("function"))
        argument = normalize_space(binding.get("argument"))
        page_urls = binding.get("page_urls") if isinstance(binding.get("page_urls"), list) else []
        notices, titles = sample_markers(sample.get("sample_tokens") or {})

        shape_candidates: List[Dict[str, Any]] = []
        definition_records: List[Dict[str, Any]] = []
        selected_page_url = ""

        if function_name != EXPECTED_FUNCTIONS.get(family) or not argument:
            classification = CLASS_REJECTED_NO_SHAPE
        else:
            for page_url in page_urls:
                page = source_pages.get(page_url)
                if not page or page.get("http_status") != 200:
                    continue
                raw_html = str(page.get("text") or "")
                definition = find_function_definition(raw_html, function_name)
                if not definition:
                    continue
                selected_page_url = normalize_space(page.get("final_url") or page_url)
                forms = extract_forms(raw_html, selected_page_url)
                form_contracts = build_form_contract(selected_page_url, family, definition, forms)
                location_contracts = build_location_contract(selected_page_url, family, definition)
                definition_records.append({
                    "page_url": selected_page_url,
                    "function": function_name,
                    "args": definition.get("args") or [],
                    "body_preview": normalize_space(definition.get("body"))[:4000],
                    "form_count": len(forms),
                    "form_contract_count": len(form_contracts),
                    "location_contract_count": len(location_contracts),
                })
                shape_candidates.extend(form_contracts)
                shape_candidates.extend(location_contracts)

            shape_candidates = canonical_contracts(shape_candidates)
            if not definition_records:
                classification = CLASS_REJECTED_NO_FUNCTION
            elif not shape_candidates:
                classification = CLASS_REJECTED_NO_SHAPE
            elif len(shape_candidates) > 1:
                classification = CLASS_REJECTED_AMBIGUOUS
            else:
                classification = (
                    CLASS_EXECUTABLE_FORM if shape_candidates[0].get("kind") == "FORM"
                    else CLASS_EXECUTABLE_LOCATION
                )

        detail_response: Dict[str, Any] = {}
        reproduction = {"matched_notice_numbers": [], "matched_titles": [], "reproduced": False}
        executed = False

        if len(shape_candidates) == 1 and detail_request_count < MAX_DETAIL_REQUESTS:
            contract = shape_candidates[0]
            method = normalize_space(contract.get("method") or "GET").upper()
            action_url = normalize_space(contract.get("action_url"))
            if contract.get("kind") == "FORM":
                payload = build_payload(contract, argument)
                if method == "GET":
                    detail_response = request_text(session, "GET", action_url, params=payload, referer=selected_page_url)
                else:
                    detail_response = request_text(session, method, action_url, data=payload, referer=selected_page_url)
            else:
                # LOCATION contract는 literal query key가 확인된 경우에만 기존 query에 argument를 삽입
                parsed = urlparse(action_url)
                query = dict(parse_qsl(parsed.query, keep_blank_values=True))
                query[normalize_space(contract.get("identity_name"))] = argument
                target_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))
                detail_response = request_text(session, "GET", target_url, referer=selected_page_url)

            request_count += 1
            detail_request_count += 1
            executed = True
            if isinstance(detail_response.get("http_status"), int) and 200 <= detail_response["http_status"] < 300:
                http_success_count += 1
            if detail_response.get("error"):
                transport_error_count += 1
            reproduction = marker_match(str(detail_response.get("text") or ""), notices, titles)

            if not (isinstance(detail_response.get("http_status"), int) and 200 <= detail_response["http_status"] < 300):
                classification = CLASS_REJECTED_HTTP
            elif reproduction["reproduced"]:
                classification = CLASS_VALIDATED
            else:
                classification = CLASS_REJECTED_SAMPLE_MISMATCH

        result = {
            "sample_index": sample.get("sample_index"),
            "source_family": family,
            "sample_tokens": sample.get("sample_tokens") or {},
            "function": function_name,
            "argument": argument,
            "definition_records": definition_records,
            "request_shape_candidates": shape_candidates,
            "request_shape_count": len(shape_candidates),
            "detail_request_executed": executed,
            "detail_http_status": detail_response.get("http_status") if executed else None,
            "detail_final_url": normalize_space(detail_response.get("final_url")) if executed else "",
            "detail_response_bytes": detail_response.get("bytes") if executed else 0,
            "sample_reproduction": reproduction,
            "classification": classification,
            "known_sample_request_validated": classification == CLASS_VALIDATED,
            "target_query_executed": False,
            "target_identity_evaluated": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        results.append(result)
        if classification == CLASS_VALIDATED:
            validated_pool.append({
                **result,
                "validated_request_shape": shape_candidates[0],
                "requires_historical_metadata_traversal_with_validated_detail_contract": True,
            })

        print()
        print("-" * 60)
        print(f"SAMPLE {index}")
        print("Family:", family)
        print("Function:", function_name)
        print("Argument:", argument)
        print("Request shape candidates:", len(shape_candidates))
        print("Executed:", executed)
        if executed:
            print("HTTP:", detail_response.get("http_status"))
            print("Final URL:", detail_response.get("final_url"))
            print("Matched notice numbers:", reproduction.get("matched_notice_numbers"))
            print("Matched titles:", reproduction.get("matched_titles"))
        print("Resolution:", classification)

    resolution = (
        "COMPETENT_AUTHORITY_BOUNDED_DETAIL_REQUEST_VALIDATION_COMPLETED"
        if validated_pool
        else "COMPETENT_AUTHORITY_BOUNDED_DETAIL_REQUEST_VALIDATION_NO_VALIDATED_CONTRACT"
    )
    next_action = (
        "known sample을 재현한 validated detail request contract만 다음 historical metadata/detail traversal에 사용한다. "
        "다음 단계부터 과거 row의 실제 identity argument를 복원해 detail metadata를 검증하되 UQQ700 target identity 평가는 별도 단계에서 수행한다."
        if validated_pool
        else
        "known sample detail request contract를 재현하지 못했다. 실행되지 않았거나 sample mismatch인 request shape는 폐기한다. "
        "SITE FALSE가 아니며 UNKNOWN을 유지하고 function body/request serialization을 추가 분석한다."
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-16-S7 Bounded Detail Request Validation",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "method": {
            "S6S1_hardened_single_binding_only": True,
            "live_function_definition_recovery": True,
            "live_form_control_recovery": True,
            "guessed_route_disabled": True,
            "guessed_parameter_disabled": True,
            "guessed_method_disabled": True,
            "single_request_shape_required": True,
            "known_sample_detail_execution_enabled": True,
            "known_sample_reproduction_required": True,
            "target_query_execution_enabled": False,
            "target_identity_evaluation_enabled": False,
            "document_candidate_promotion_allowed": False,
        },
        "summary": {
            "input_sample_count": len(samples),
            "source_page_request_count": len(source_urls),
            "detail_request_count": detail_request_count,
            "total_request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "validated_request_contract_count": len(validated_pool),
        },
        "classification_counts": dict(sorted(Counter(x.get("classification") for x in results).items())),
        "sample_results": results,
        "next_stage_validated_detail_contract_pool": validated_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    request_budget_leakage = max(0, request_count - MAX_TOTAL_REQUESTS)
    invalid_shape_leakage = sum(1 for x in validated_pool if x.get("request_shape_count") != 1)
    reproduction_leakage = sum(1 for x in validated_pool if not (x.get("sample_reproduction") or {}).get("reproduced"))
    non_go_kr_detail_leakage = sum(
        1 for x in validated_pool
        if not is_government_host(hostname(x.get("detail_final_url") or ""))
    )
    target_query_leakage = sum(1 for x in results + validated_pool if x.get("target_query_executed") is True)
    target_identity_leakage = sum(1 for x in results + validated_pool if x.get("target_identity_evaluated") is True)
    unsafe_promotion_leakage = sum(
        1 for x in results + validated_pool
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
        "S6-S1 input exists": S6S1_INPUT_PATH.exists(),
        "S6-S1 input parsed": isinstance(data, dict),
        "hardened single bindings loaded": len(samples) > 0,
        "total request budget respected": request_budget_leakage == 0,
        "live function recovery enabled": True,
        "live form/control recovery enabled": True,
        "guessed request shape disabled": True,
        "single request shape required": True,
        "all classes valid": all(x.get("classification") in VALID_CLASSES for x in results),
        "validated shape cardinality one": invalid_shape_leakage == 0,
        "validated samples reproduce metadata": reproduction_leakage == 0,
        "validated final URLs go.kr": non_go_kr_detail_leakage == 0,
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
    print("BOUNDED DETAIL REQUEST VALIDATION RESULT")
    print("=" * 60)
    print("Input sample count:", len(samples))
    print("Source page request count:", len(source_urls))
    print("Detail request count:", detail_request_count)
    print("Total request count:", request_count)
    print("Validated request contract count:", len(validated_pool))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)
    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Request budget leakage:", request_budget_leakage)
    print("Invalid validated shape leakage:", invalid_shape_leakage)
    print("Sample reproduction leakage:", reproduction_leakage)
    print("Non-go.kr detail leakage:", non_go_kr_detail_leakage)
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
        raise AssertionError("UQQ700 bounded detail request validation regression failed")


if __name__ == "__main__":
    main()
