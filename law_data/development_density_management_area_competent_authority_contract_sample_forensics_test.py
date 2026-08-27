# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-16-S3
Development Density Management Area
Competent Authority Contract Sample Forensics & Global Script/Form Binding Recovery

S1의 detail contract sample을 기준으로 bounded historical page의 실제 inline JS/form
구조를 교차검증한다. 새로운 함수명/파라미터/detail URL은 추측하지 않는다.
UQQ700 target query/identity 평가 및 SITE 승격은 수행하지 않는다.
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
S1_INPUT_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_competent_authority_detail_contract_probe.json"
T16_INPUT_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_competent_authority_bounded_historical_range_traversal.json"
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_competent_authority_contract_sample_forensics.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

CLASS_EXECUTABLE_JS_FORM_BINDING = "RECOVERED_EXECUTABLE_JS_FORM_DETAIL_BINDING"
CLASS_STATIC_DETAIL_RECONFIRMED = "RECONFIRMED_STATIC_DETAIL_PATH_BINDING"
CLASS_FUNCTION_DEFINITION_ONLY = "RECOVERED_JS_FUNCTION_DEFINITION_ONLY"
CLASS_CONTRACT_SAMPLE_ONLY = "CONTRACT_SAMPLE_FORENSIC_EVIDENCE_ONLY"
CLASS_UNRESOLVED = "UNRESOLVED_GLOBAL_DETAIL_BINDING"
VALID_CLASSES = {
    CLASS_EXECUTABLE_JS_FORM_BINDING,
    CLASS_STATIC_DETAIL_RECONFIRMED,
    CLASS_FUNCTION_DEFINITION_ONLY,
    CLASS_CONTRACT_SAMPLE_ONLY,
    CLASS_UNRESOLVED,
}
EXECUTABLE_CLASSES = {CLASS_EXECUTABLE_JS_FORM_BINDING, CLASS_STATIC_DETAIL_RECONFIRMED}

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 12
MAX_PAGES_PER_FAMILY = 6
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

SCRIPT_BLOCK_PATTERN = re.compile(r"<script\b(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.I | re.S)
FORM_PATTERN = re.compile(r"<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>", re.I | re.S)
INPUT_PATTERN = re.compile(r"<input\b(?P<attrs>[^>]*)>", re.I | re.S)
SELECT_PATTERN = re.compile(r"<select\b(?P<attrs>[^>]*)>", re.I | re.S)
TEXTAREA_PATTERN = re.compile(r"<textarea\b(?P<attrs>[^>]*)>", re.I | re.S)
ANCHOR_PATTERN = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>", re.I | re.S)
ATTR_PATTERN = re.compile(r'''([:\w-]+)\s*=\s*(?:["']([^"']*)["']|([^\s>]+))''', re.I | re.S)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)
SCRIPT_STYLE_PATTERN = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
QUOTED_LITERAL_PATTERN = re.compile(r'''["']([^"'<>]{1,500})["']''')
FORM_ACTION_ASSIGNMENT_PATTERN = re.compile(r'''(?P<form>[A-Za-z_$][\w$.\[\]'\"]*)\.action\s*=\s*["'](?P<value>[^"']+)["']''', re.I)
LOCATION_ASSIGNMENT_PATTERN = re.compile(r'''(?:location(?:\.href)?|window\.location(?:\.href)?)\s*=\s*["'](?P<value>[^"']+)["']''', re.I)
VALUE_ASSIGNMENT_PATTERN = re.compile(r'''(?P<field>[A-Za-z_$][\w$.\[\]'\"]*)\.value\s*=\s*(?P<value>[A-Za-z_$][\w$]*)''', re.I)
GET_ELEMENT_VALUE_PATTERN = re.compile(r'''getElementById\(\s*["'](?P<field>[^"']+)["']\s*\)\.value\s*=\s*(?P<value>[A-Za-z_$][\w$]*)''', re.I)
SUBMIT_PATTERN = re.compile(r'''(?P<form>[A-Za-z_$][\w$.\[\]'\"]*)\.submit\s*\(\s*\)''', re.I)
FUNCTION_DECLARATION_PREFIX = r"function\s+{name}\s*\((?P<params>[^)]*)\)\s*\{{"
FUNCTION_ASSIGNMENT_PREFIX = r"(?:var|let|const)?\s*{name}\s*=\s*function\s*\((?P<params>[^)]*)\)\s*\{{"
DETAIL_PATH_HINTS = ("/view", "/detail", "/read", "/select", "/bbs/", "/board/", "/notice/", "/post/")
GENERIC_ACTION_PATH_HINTS = ("/login", "/member", "/satisfaction", "/search", "/main", "/index")


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
    value = normalize_space(host).lower()
    return bool(value) and (value == "go.kr" or value.endswith(".go.kr"))


def same_host(a: str, b: str) -> bool:
    return bool(hostname(a)) and hostname(a) == hostname(b)


def normalize_path(value: Any) -> str:
    text = normalize_space(value)
    if not text:
        return ""
    try:
        parsed = urlparse(text)
        if parsed.scheme or parsed.netloc:
            return normalize_space(parsed.path or "/")
    except Exception:
        pass
    return text.split("?", 1)[0].split("#", 1)[0]


def detail_like_path(path: str) -> bool:
    lowered = normalize_space(path).lower()
    if not lowered or any(noise in lowered for noise in GENERIC_ACTION_PATH_HINTS):
        return False
    return any(hint in lowered for hint in DETAIL_PATH_HINTS)


def extract_name_tail(expression: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9_:\-]+", normalize_space(expression))
    return tokens[-1] if tokens else ""


def load_contracts(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("next_stage_contract_pool")
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        family = normalize_space(item.get("source_family"))
        if not family:
            continue
        pages: List[int] = []
        for value in item.get("page_numbers") or []:
            try:
                page = int(value)
            except Exception:
                continue
            if page >= 1:
                pages.append(page)
        out.append({
            **item,
            "source_family": family,
            "static_detail_paths": unique_strings(normalize_path(v) for v in (item.get("static_detail_paths") or [])),
            "javascript_functions": unique_strings(item.get("javascript_functions") or []),
            "identity_keys": unique_strings(normalize_space(v).lower() for v in (item.get("identity_keys") or [])),
            "sample_rows": item.get("sample_rows") if isinstance(item.get("sample_rows"), list) else [],
            "page_numbers": sorted(set(pages)),
        })
    return out


def load_t16_pages(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("page_records")
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict) or item.get("http_status") != 200:
            continue
        family = normalize_space(item.get("source_family"))
        url = normalize_space(item.get("final_url") or item.get("requested_url"))
        if not family or not url or not is_government_host(hostname(url)):
            continue
        try:
            page_number = int(item.get("page_number") or 0)
        except Exception:
            page_number = 0
        out.append({"source_family": family, "page_number": page_number, "url": url})
    return out


def select_probe_pages(contracts: List[Dict[str, Any]], pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_family: Dict[str, List[Dict[str, Any]]] = {}
    for page in pages:
        by_family.setdefault(page["source_family"], []).append(page)
    selected: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for family in sorted(by_family):
        wanted: Set[int] = set()
        for contract in contracts:
            if contract.get("source_family") == family:
                wanted.update(contract.get("page_numbers") or [])
        ranked = sorted(by_family[family], key=lambda x: (0 if x.get("page_number") in wanted else 1, int(x.get("page_number") or 0)))
        count = 0
        for item in ranked:
            if count >= MAX_PAGES_PER_FAMILY or len(selected) >= MAX_TOTAL_REQUESTS:
                break
            url = item["url"]
            if url in seen:
                continue
            seen.add(url)
            selected.append(item)
            count += 1
    return selected


def decode_html(response: requests.Response, data: bytes) -> str:
    for encoding in unique_strings([response.encoding, "utf-8", "cp949", "euc-kr"]):
        try:
            return data.decode(encoding)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"http_status": None, "final_url": "", "raw_html": "", "response_bytes": 0, "error": ""}
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
            result["response_bytes"] = len(data)
            result["raw_html"] = decode_html(response, data)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def extract_forms(raw_html: str, page_url: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for index, match in enumerate(FORM_PATTERN.finditer(raw_html or ""), start=1):
        attrs = parse_attrs(match.group("attrs"))
        body = match.group("body")
        action_raw = normalize_space(attrs.get("action"))
        action_url = urljoin(page_url, action_raw) if action_raw else page_url
        fields: List[str] = []
        for pattern in (INPUT_PATTERN, SELECT_PATTERN, TEXTAREA_PATTERN):
            for field_match in pattern.finditer(body):
                fattrs = parse_attrs(field_match.group("attrs"))
                fields.extend([fattrs.get("name", ""), fattrs.get("id", "")])
        out.append({
            "form_index": index,
            "id": normalize_space(attrs.get("id")),
            "name": normalize_space(attrs.get("name")),
            "method": normalize_space(attrs.get("method")).upper() or "GET",
            "action_url": action_url,
            "action_path": normalize_path(action_url),
            "fields": unique_strings(fields),
        })
    return out


def extract_static_anchor_paths(raw_html: str, page_url: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for match in ANCHOR_PATTERN.finditer(raw_html or ""):
        attrs = parse_attrs(match.group("attrs"))
        href = normalize_space(attrs.get("href"))
        if not href or href.lower().startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        absolute = urljoin(page_url, href)
        if not is_government_host(hostname(absolute)) or not same_host(page_url, absolute):
            continue
        path = normalize_path(absolute)
        if detail_like_path(path):
            out.append({"url": absolute, "path": path, "text": strip_html(match.group("body"))})
    return out


def find_balanced_block(source: str, open_index: int) -> Optional[str]:
    if open_index < 0 or open_index >= len(source) or source[open_index] != "{":
        return None
    depth = 0
    quote: Optional[str] = None
    escaped = False
    for index in range(open_index, len(source)):
        ch = source[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"', "`"):
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[open_index + 1:index]
    return None


def extract_function_definitions(script: str, function_name: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    name = re.escape(function_name)
    patterns = [FUNCTION_DECLARATION_PREFIX.format(name=name), FUNCTION_ASSIGNMENT_PREFIX.format(name=name)]
    seen: Set[Tuple[Tuple[str, ...], str]] = set()
    for prefix in patterns:
        for match in re.compile(prefix, re.I).finditer(script or ""):
            body = find_balanced_block(script, match.end() - 1)
            if body is None:
                continue
            params = unique_strings(part.strip() for part in (match.group("params") or "").split(","))
            key = (tuple(params), normalize_space(body)[:800])
            if key in seen:
                continue
            seen.add(key)
            out.append({"function": function_name, "params": params, "body": body})
    return out


def analyze_function_body(definition: Dict[str, Any], page_url: str, forms: List[Dict[str, Any]], static_paths: List[str], identity_keys: List[str]) -> Dict[str, Any]:
    body = str(definition.get("body") or "")
    params = unique_strings(definition.get("params") or [])
    param_set = {p.lower() for p in params}
    paths: List[str] = []
    for literal in QUOTED_LITERAL_PATTERN.findall(body):
        value = normalize_space(literal)
        if not value.startswith(("/", "./", "../", "http://", "https://")):
            continue
        candidate = urljoin(page_url, value)
        if is_government_host(hostname(candidate)) and same_host(page_url, candidate):
            paths.append(normalize_path(candidate))
    for pattern in (FORM_ACTION_ASSIGNMENT_PATTERN, LOCATION_ASSIGNMENT_PATTERN):
        for match in pattern.finditer(body):
            candidate = urljoin(page_url, normalize_space(match.group("value")))
            if is_government_host(hostname(candidate)) and same_host(page_url, candidate):
                paths.append(normalize_path(candidate))
    assignments: List[Dict[str, str]] = []
    for pattern in (VALUE_ASSIGNMENT_PATTERN, GET_ELEMENT_VALUE_PATTERN):
        for match in pattern.finditer(body):
            arg = normalize_space(match.group("value"))
            if arg.lower() not in param_set:
                continue
            field_expr = normalize_space(match.group("field"))
            assignments.append({"field_expression": field_expr, "field_name": extract_name_tail(field_expr), "argument": arg})
    path_set = {normalize_path(x) for x in static_paths}
    static_matches = unique_strings(p for p in paths if normalize_path(p) in path_set)
    detail_literals = unique_strings(p for p in paths if detail_like_path(p))
    identity_set = {normalize_space(x).lower() for x in identity_keys}
    identity_matches = unique_strings(a.get("field_name") for a in assignments if normalize_space(a.get("field_name")).lower() in identity_set)
    matched_forms: List[Dict[str, Any]] = []
    assignment_fields = {normalize_space(a.get("field_name")).lower() for a in assignments if normalize_space(a.get("field_name"))}
    for form in forms:
        form_fields = {normalize_space(v).lower() for v in (form.get("fields") or [])}
        overlap = sorted(form_fields & assignment_fields)
        action_path = normalize_path(form.get("action_path"))
        action_contract = action_path in path_set
        action_detail = detail_like_path(action_path)
        if overlap or action_contract or action_detail:
            matched_forms.append({
                "form_index": form.get("form_index"), "id": form.get("id"), "name": form.get("name"),
                "method": form.get("method"), "action_url": form.get("action_url"), "action_path": action_path,
                "field_overlap": overlap, "action_matches_contract": action_contract, "action_detail_like": action_detail,
            })
    executable_form = any(x.get("field_overlap") and (x.get("action_matches_contract") or x.get("action_detail_like")) for x in matched_forms)
    executable_literal = bool(assignments and (static_matches or detail_literals))
    executable = executable_form or executable_literal
    reasons = ["JS_FUNCTION_DEFINITION_PRESENT"]
    if assignments: reasons.append("FUNCTION_ARGUMENT_TO_FIELD_BINDING")
    if static_matches: reasons.append("CONTRACT_STATIC_DETAIL_PATH_LITERAL_MATCH")
    if detail_literals: reasons.append("SAME_HOST_DETAIL_LITERAL_PRESENT")
    if matched_forms: reasons.append("GLOBAL_FORM_CONTEXT_MATCHED")
    if executable_form: reasons.append("EXECUTABLE_FORM_ACTION_FIELD_BINDING")
    if executable_literal: reasons.append("EXECUTABLE_LITERAL_DETAIL_BINDING")
    return {
        "function": definition.get("function"), "params": params, "assignments": assignments,
        "submitted_forms": unique_strings(m.group("form") for m in SUBMIT_PATTERN.finditer(body)),
        "literal_paths": unique_strings(paths), "static_path_matches": static_matches,
        "detail_literal_paths": detail_literals, "identity_key_matches": identity_matches,
        "matched_forms": matched_forms, "executable": executable, "reasons": unique_strings(reasons),
    }


def summarize_sample_rows(contract: Dict[str, Any]) -> Dict[str, Any]:
    rows = contract.get("sample_rows") or []
    anchors: List[str] = []; hrefs: List[str] = []; onclicks: List[str] = []; calls: List[str] = []
    data_keys: List[str] = []; hidden_keys: List[str] = []; row_texts: List[str] = []
    for row in rows:
        if not isinstance(row, dict): continue
        text = normalize_space(row.get("row_text"))
        if text: row_texts.append(text[:1000])
        anchors.extend(row.get("meaningful_anchor_texts") or [])
        for anchor in row.get("anchors") or []:
            if not isinstance(anchor, dict): continue
            anchors.append(anchor.get("text", "")); hrefs.append(anchor.get("href", "")); onclicks.append(anchor.get("onclick", ""))
            data_keys.extend((anchor.get("data_attrs") or {}).keys())
        for js in row.get("javascript_contracts") or []:
            if isinstance(js, dict) and normalize_space(js.get("function")):
                calls.append(f"{normalize_space(js.get('function'))}({normalize_space(js.get('args'))})")
        for item in row.get("data_identity") or []:
            if isinstance(item, dict): data_keys.append(item.get("name", ""))
        for item in row.get("hidden_identity") or []:
            if isinstance(item, dict): hidden_keys.append(item.get("name") or item.get("id") or "")
    return {
        "sample_row_count": len(rows), "row_texts": unique_strings(row_texts), "anchor_texts": unique_strings(anchors),
        "raw_hrefs": unique_strings(hrefs), "onclicks": unique_strings(onclicks), "javascript_calls": unique_strings(calls),
        "data_keys": unique_strings(data_keys), "hidden_keys": unique_strings(hidden_keys),
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("CONTRACT SAMPLE FORENSICS & GLOBAL SCRIPT/FORM BINDING")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Target query execution: DISABLED")
    print("Target identity evaluation: DISABLED")
    print("Document candidate promotion: DISABLED")
    print()

    if not S1_INPUT_PATH.exists(): raise FileNotFoundError(f"T-16-S1 input not found: {S1_INPUT_PATH}")
    if not T16_INPUT_PATH.exists(): raise FileNotFoundError(f"T-16 input not found: {T16_INPUT_PATH}")
    s1_data = json.loads(S1_INPUT_PATH.read_text(encoding="utf-8"))
    t16_data = json.loads(T16_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(s1_data, dict) or not isinstance(t16_data, dict): raise TypeError("stage input must be JSON object")
    contracts = load_contracts(s1_data)
    pages = load_t16_pages(t16_data)
    selected = select_probe_pages(contracts, pages)
    print("Detail contract count:", len(contracts))
    print("T-16 bounded page count:", len(pages))
    print("Selected forensic page count:", len(selected)); print()

    session = requests.Session(); session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    request_count = 0; http_success_count = 0; transport_error_count = 0
    page_forensics: List[Dict[str, Any]] = []
    for index, page in enumerate(selected, start=1):
        response = fetch_page(session, page["url"]); request_count += 1
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300: http_success_count += 1
        if response.get("error"): transport_error_count += 1
        final_url = normalize_space(response.get("final_url") or page["url"])
        raw_html = str(response.get("raw_html") or "")
        forms = extract_forms(raw_html, final_url) if status == 200 else []
        static_anchors = extract_static_anchor_paths(raw_html, final_url) if status == 200 else []
        scripts: List[str] = []
        if status == 200:
            for match in SCRIPT_BLOCK_PATTERN.finditer(raw_html):
                attrs = parse_attrs(match.group("attrs"))
                if normalize_space(attrs.get("src")): continue
                body = str(match.group("body") or "")
                if normalize_space(body): scripts.append(body)
        page_forensics.append({"source_family": page["source_family"], "page_number": page["page_number"], "url": final_url, "http_status": status, "forms": forms, "static_detail_anchors": static_anchors, "inline_scripts": scripts, "inline_script_count": len(scripts), "error": response.get("error")})
        print("-" * 60); print(f"PAGE {index}"); print("Family:", page["source_family"]); print("Page number:", page["page_number"]); print("HTTP:", status); print("Forms:", len(forms)); print("Static detail anchors:", len(static_anchors)); print("Inline scripts:", len(scripts))

    contract_results: List[Dict[str, Any]] = []; next_pool: List[Dict[str, Any]] = []
    for index, contract in enumerate(contracts, start=1):
        family = contract["source_family"]; static_paths = contract.get("static_detail_paths") or []; functions = contract.get("javascript_functions") or []; identity_keys = contract.get("identity_keys") or []
        sample_summary = summarize_sample_rows(contract); function_bindings: List[Dict[str, Any]] = []; static_reconfirmed: List[Dict[str, Any]] = []
        for page in [p for p in page_forensics if p.get("source_family") == family and p.get("http_status") == 200]:
            page_url = page["url"]
            path_set = {normalize_path(x) for x in static_paths}
            for anchor in page.get("static_detail_anchors") or []:
                if normalize_path(anchor.get("path")) in path_set:
                    static_reconfirmed.append({"page_url": page_url, "page_number": page.get("page_number"), **anchor})
            for function_name in functions:
                for script_index, script in enumerate(page.get("inline_scripts") or [], start=1):
                    for definition in extract_function_definitions(script, function_name):
                        function_bindings.append({"page_url": page_url, "page_number": page.get("page_number"), "script_index": script_index, **analyze_function_body(definition, page_url, page.get("forms") or [], static_paths, identity_keys)})
        executable_js = [x for x in function_bindings if x.get("executable") is True]
        if executable_js:
            classification = CLASS_EXECUTABLE_JS_FORM_BINDING; qualified = True
        elif static_reconfirmed:
            classification = CLASS_STATIC_DETAIL_RECONFIRMED; qualified = True
        elif function_bindings:
            classification = CLASS_FUNCTION_DEFINITION_ONLY; qualified = False
        elif sample_summary["sample_row_count"] > 0:
            classification = CLASS_CONTRACT_SAMPLE_ONLY; qualified = False
        else:
            classification = CLASS_UNRESOLVED; qualified = False
        reasons = []
        if sample_summary["sample_row_count"]: reasons.append("S1_SAMPLE_ROWS_PRESENT")
        if functions: reasons.append("S1_JAVASCRIPT_FUNCTION_SIGNATURE_PRESENT")
        if static_paths: reasons.append("S1_STATIC_DETAIL_PATH_SIGNATURE_PRESENT")
        if identity_keys: reasons.append("S1_IDENTITY_KEY_SIGNATURE_PRESENT")
        if function_bindings: reasons.append("GLOBAL_JS_FUNCTION_DEFINITION_RECOVERED")
        if executable_js: reasons.append("EXECUTABLE_JS_FORM_BINDING_RECOVERED")
        if static_reconfirmed: reasons.append("STATIC_DETAIL_PATH_RECONFIRMED")
        record = {"source_family": family, "static_detail_paths": static_paths, "javascript_functions": functions, "identity_keys": identity_keys, "page_numbers": contract.get("page_numbers") or [], "sample_summary": sample_summary, "function_bindings": function_bindings, "static_path_reconfirmed": static_reconfirmed, "qualified_for_next_stage": qualified, "classification": classification, "reasons": unique_strings(reasons), "target_query_executed": False, "target_identity_evaluated": False, "document_candidate": False, "verified_positive": False, "runtime_registration_allowed": False, "site_positive_allowed": False, "site_negative_allowed": False, "final_positive_promotion_allowed": False}
        contract_results.append(record)
        if qualified:
            next_pool.append({"source_family": family, "classification": classification, "static_detail_paths": static_paths, "javascript_functions": functions, "identity_keys": identity_keys, "function_bindings": executable_js, "static_path_reconfirmed": static_reconfirmed, "requires_source_specific_execution_recovery": True, "target_query_executed": False, "target_identity_evaluated": False, "document_candidate": False, "verified_positive": False, "runtime_registration_allowed": False, "site_positive_allowed": False, "site_negative_allowed": False, "final_positive_promotion_allowed": False})
        print(); print("-" * 60); print(f"CONTRACT {index}"); print("Family:", family); print("Static paths:", static_paths); print("JS functions:", functions); print("Identity keys:", identity_keys); print("Sample rows:", sample_summary["sample_row_count"]); print("Function definitions:", len(function_bindings)); print("Executable JS bindings:", len(executable_js)); print("Static path reconfirmations:", len(static_reconfirmed)); print("Qualified for next stage:", qualified); print("Resolution:", classification)

    if next_pool:
        resolution = "COMPETENT_AUTHORITY_GLOBAL_DETAIL_BINDING_RECOVERY_COMPLETED"
        next_action = "T-16-S3에서 실제 HTML 구조로 재확인된 detail binding만 T-16-S4 source-specific executable detail identity recovery에 사용한다. S4에서도 UQQ700 target identity는 평가하지 않는다."
    else:
        resolution = "COMPETENT_AUTHORITY_GLOBAL_DETAIL_BINDING_RECOVERY_NO_EXECUTABLE_BINDING"
        next_action = "S1 sample contract는 존재하지만 실제 inline JS/form executable binding이 확인되지 않았다. SITE FALSE로 판정하지 않고 UNKNOWN을 유지하며 external script/source-specific request mechanism을 별도 probe한다."

    output_data = {
        "step": "STEP 17-21-C-16-8-T-16-S3 Contract Sample Forensics & Global Script/Form Binding Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {"resolution_type": RESOLUTION_TYPE, "negative_evidence_allowed": False, "source_failure_site_status": "UNKNOWN"},
        "inputs": {"t16_s1_path": str(S1_INPUT_PATH), "t16_path": str(T16_INPUT_PATH)},
        "method": {"s1_contract_pool_only": True, "t16_bounded_pages_only": True, "direct_network_requery": True, "inline_script_analysis_enabled": True, "same_page_form_analysis_enabled": True, "external_script_fetch_enabled": False, "new_function_guessing_enabled": False, "new_parameter_guessing_enabled": False, "new_detail_url_guessing_enabled": False, "function_definition_required_for_js_binding": True, "argument_to_field_binding_required_for_executable_js": True, "same_host_official_action_required": True, "target_query_execution_enabled": False, "target_identity_evaluation_enabled": False, "document_candidate_promotion_allowed": False, "verified_positive_promotion_allowed": False, "runtime_registration_allowed": False, "site_positive_allowed": False, "site_negative_allowed": False},
        "summary": {"detail_contract_count": len(contracts), "t16_bounded_page_count": len(pages), "selected_forensic_page_count": len(selected), "request_count": request_count, "http_success_count": http_success_count, "transport_error_count": transport_error_count, "contract_result_count": len(contract_results), "next_stage_binding_count": len(next_pool)},
        "classification_counts": dict(sorted(Counter(x.get("classification") for x in contract_results).items())),
        "page_forensics": [{**p, "inline_scripts": []} for p in page_forensics],
        "contract_results": contract_results,
        "next_stage_binding_pool": next_pool,
        "resolution": resolution, "next_action": next_action,
        "verified_positive": False, "runtime_registration_allowed": False, "site_positive_allowed": False, "site_negative_allowed": False, "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    all_classes_valid = all(x.get("classification") in VALID_CLASSES for x in contract_results)
    next_classes_valid = all(x.get("classification") in EXECUTABLE_CLASSES for x in next_pool)
    guessed_function_leakage = sum(1 for item in contract_results for binding in (item.get("function_bindings") or []) if normalize_space(binding.get("function")) not in set(item.get("javascript_functions") or []))
    guessed_static_path_leakage = sum(1 for item in contract_results for row in (item.get("static_path_reconfirmed") or []) if normalize_path(row.get("path")) not in {normalize_path(p) for p in (item.get("static_detail_paths") or [])})
    cross_host_executable_leakage = 0
    for item in next_pool:
        for binding in item.get("function_bindings") or []:
            page_url = normalize_space(binding.get("page_url"))
            for form in binding.get("matched_forms") or []:
                action_url = normalize_space(form.get("action_url"))
                if action_url and (not is_government_host(hostname(action_url)) or not same_host(page_url, action_url)):
                    cross_host_executable_leakage += 1
    unsafe_promotion_leakage = sum(1 for item in contract_results + next_pool if item.get("document_candidate") is True or item.get("verified_positive") is True or item.get("runtime_registration_allowed") is True or item.get("site_positive_allowed") is True or item.get("site_negative_allowed") is True or item.get("final_positive_promotion_allowed") is True)
    target_query_leakage = sum(1 for item in contract_results + next_pool if item.get("target_query_executed") is True)
    target_identity_leakage = sum(1 for item in contract_results + next_pool if item.get("target_identity_evaluated") is True)
    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역", "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE", "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-16-S1 input exists": S1_INPUT_PATH.exists(), "T-16 input exists": T16_INPUT_PATH.exists(), "S1 contracts loaded": len(contracts) > 0,
        "T-16 bounded pages loaded": len(pages) > 0, "forensic request budget respected": request_count <= MAX_TOTAL_REQUESTS,
        "external script fetch disabled": True, "new function guessing disabled": guessed_function_leakage == 0,
        "new static path guessing disabled": guessed_static_path_leakage == 0, "all classes valid": all_classes_valid, "next-stage classes valid": next_classes_valid,
        "cross-host executable leakage zero": cross_host_executable_leakage == 0, "target query execution leakage zero": target_query_leakage == 0,
        "target identity evaluation leakage zero": target_identity_leakage == 0, "unsafe promotion leakage zero": unsafe_promotion_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False, "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False, "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }
    print(); print("=" * 60); print("CONTRACT SAMPLE FORENSICS RESULT"); print("=" * 60)
    print("Detail contract count:", len(contracts)); print("Selected forensic page count:", len(selected)); print("Request count:", request_count); print("HTTP success count:", http_success_count); print("Transport error count:", transport_error_count); print("Next-stage binding count:", len(next_pool)); print("Resolution:", resolution); print("Output:", OUTPUT_PATH)
    print(); print("=" * 60); print("VALIDATION"); print("=" * 60)
    for name, passed in validations.items(): print(f"{name}: {passed}")
    print(); print("Guessed function leakage:", guessed_function_leakage); print("Guessed static path leakage:", guessed_static_path_leakage); print("Cross-host executable leakage:", cross_host_executable_leakage); print("Target query leakage:", target_query_leakage); print("Target identity leakage:", target_identity_leakage); print("Unsafe promotion leakage:", unsafe_promotion_leakage)
    print(); all_pass = all(validations.values()); print(f"all_pass: {all_pass}")
    if not all_pass:
        print(); print("FAILED:")
        for name, passed in validations.items():
            if not passed: print("-", name)
        raise AssertionError("UQQ700 contract sample forensics and global detail binding recovery regression failed")


if __name__ == "__main__":
    main()
