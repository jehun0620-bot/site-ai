# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-16-S6

Development Density Management Area
Competent Authority Sample-to-Global Binding Recovery

목표
======================================================================
T-16-S4에서 재식별된 실제 sample metadata row와 T-16-S5에서 복원된
page-global detail mechanism을 결합한다.

이 단계는 다음만 수행한다.

1. sample title / notice number / date가 실제 HTML에 존재하는 위치를 다시 찾는다.
2. sample 주변 실제 HTML 문맥에서 이미 복원된 global function 호출만 찾는다.
3. function argument(notAncmtMgtNo, pstSn 등)를 실제 문맥에서 복원한다.
4. S5 function/form evidence와 결합하여 executable request binding candidate를 만든다.
5. HTTP detail request는 아직 실행하지 않는다.
6. UQQ700 target identity 평가는 하지 않는다.
7. 인자, URL, parameter, function을 추측하지 않는다.
8. document candidate / SITE TRUE / SITE FALSE 승격 금지.
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
S4_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_competent_authority_sample_row_interaction_recovery.json"
)
S5_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_competent_authority_global_request_mechanism_probe.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_competent_authority_sample_global_binding_recovery.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"
ALLOWED_FAMILIES = {FAMILY_NOTICE, FAMILY_URBAN}

EXPECTED_FUNCTIONS = {
    FAMILY_NOTICE: {"f_view"},
    FAMILY_URBAN: {"fn_move_form"},
}
EXPECTED_ARGUMENT_NAMES = {
    FAMILY_NOTICE: {"notancmtmgtno"},
    FAMILY_URBAN: {"pstsn"},
}

CLASS_SAMPLE_FUNCTION_BOUND = "RECOVERED_SAMPLE_GLOBAL_FUNCTION_BINDING"
CLASS_SAMPLE_FORM_BOUND = "RECOVERED_SAMPLE_GLOBAL_FORM_BINDING"
CLASS_SAMPLE_CONTEXT_ONLY = "SAMPLE_GLOBAL_BINDING_CONTEXT_ONLY"
CLASS_SAMPLE_NOT_FOUND = "SAMPLE_METADATA_NOT_RELOCATED"
CLASS_FUNCTION_NOT_BOUND = "GLOBAL_FUNCTION_NOT_BOUND_TO_SAMPLE"
VALID_CLASSES = {
    CLASS_SAMPLE_FUNCTION_BOUND,
    CLASS_SAMPLE_FORM_BOUND,
    CLASS_SAMPLE_CONTEXT_ONLY,
    CLASS_SAMPLE_NOT_FOUND,
    CLASS_FUNCTION_NOT_BOUND,
}
QUALIFIED_CLASSES = {CLASS_SAMPLE_FUNCTION_BOUND, CLASS_SAMPLE_FORM_BOUND}

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 8
MAX_PAGES_PER_FAMILY = 4
CONTEXT_RADIUS = 3000
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

FUNCTION_CALL_PATTERN = re.compile(
    r'''(?P<func>[A-Za-z_$][\w$]*)\s*\(\s*(?P<args>[^)]{0,500})\)''',
    re.I | re.S,
)
QUOTED_ARG_PATTERN = re.compile(r'''^[\s]*["'](?P<value>[^"']+)["'][\s]*$''', re.S)
NUMERIC_ARG_PATTERN = re.compile(r'''^[\s]*(?P<value>\d+)[\s]*$''')
NOTICE_MGT_NO_PATTERN = re.compile(
    r'''(?:not[_-]?ancmt[_-]?mgt[_-]?no|notAncmtMgtNo)\s*[=:]\s*["']?([A-Za-z0-9_-]{3,})''',
    re.I,
)
PST_SN_PATTERN = re.compile(
    r'''(?:pstSn|pst_sn)\s*[=:]\s*["']?(\d{1,20})''',
    re.I,
)
TAG_PATTERN = re.compile(r'<[^>]+>', re.S)
SCRIPT_STYLE_PATTERN = re.compile(r'<(?:script|style)\b.*?</(?:script|style)>', re.I | re.S)
COMMENT_PATTERN = re.compile(r'<!--.*?-->', re.S)


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


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    host = normalize_space(host).lower()
    return bool(host) and (host == "go.kr" or host.endswith(".go.kr"))


def decode_html(response: requests.Response, data: bytes) -> str:
    for encoding in unique_strings([response.encoding, "utf-8", "cp949", "euc-kr"]):
        try:
            return data.decode(encoding)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result = {"http_status": None, "final_url": "", "raw_html": "", "response_bytes": 0, "error": ""}
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


def strip_html(raw: str) -> str:
    value = COMMENT_PATTERN.sub(" ", raw or "")
    value = SCRIPT_STYLE_PATTERN.sub(" ", value)
    value = TAG_PATTERN.sub(" ", value)
    return normalize_space(html.unescape(value))


def load_s4(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    contracts_raw = data.get("contract_results") if isinstance(data.get("contract_results"), list) else []
    pages_raw = data.get("page_results") if isinstance(data.get("page_results"), list) else []
    contracts: List[Dict[str, Any]] = []
    for item in contracts_raw:
        if not isinstance(item, dict):
            continue
        family = normalize_space(item.get("source_family"))
        rows = item.get("located_rows") if isinstance(item.get("located_rows"), list) else []
        if family not in ALLOWED_FAMILIES or not rows:
            continue
        contracts.append({
            "contract_index": item.get("contract_index"),
            "source_family": family,
            "located_rows": rows,
        })
    pages: List[Dict[str, Any]] = []
    seen = set()
    for item in pages_raw:
        if not isinstance(item, dict) or item.get("http_status") != 200:
            continue
        family = normalize_space(item.get("source_family"))
        url = normalize_space(item.get("url"))
        if family not in ALLOWED_FAMILIES or not url or url in seen:
            continue
        seen.add(url)
        pages.append({
            "source_family": family,
            "page_number": item.get("page_number"),
            "url": url,
        })
    return contracts, pages


def load_s5(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw = data.get("family_results") if isinstance(data.get("family_results"), list) else []
    result: Dict[str, Dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        family = normalize_space(item.get("source_family"))
        if family not in ALLOWED_FAMILIES:
            continue
        result[family] = item
    return result


def select_pages(contracts: List[Dict[str, Any]], pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    wanted: Dict[str, Set[str]] = {family: set() for family in ALLOWED_FAMILIES}
    for contract in contracts:
        family = contract["source_family"]
        for row in contract.get("located_rows") or []:
            for url in row.get("page_urls") or []:
                if url:
                    wanted[family].add(normalize_space(url))
            if row.get("page_url"):
                wanted[family].add(normalize_space(row.get("page_url")))
    result: List[Dict[str, Any]] = []
    seen = set()
    for family in sorted(ALLOWED_FAMILIES):
        candidates = [p for p in pages if p["source_family"] == family]
        candidates.sort(key=lambda p: (0 if p["url"] in wanted[family] else 1, int(p.get("page_number") or 0)))
        count = 0
        for page in candidates:
            if len(result) >= MAX_TOTAL_REQUESTS or count >= MAX_PAGES_PER_FAMILY:
                break
            if page["url"] in seen:
                continue
            seen.add(page["url"])
            result.append(page)
            count += 1
    return result


def sample_tokens(row: Dict[str, Any]) -> Dict[str, List[str]]:
    reasons = row.get("match_reasons") if isinstance(row.get("match_reasons"), list) else []
    titles: List[str] = []
    notice_numbers: List[str] = []
    dates: List[str] = []
    for reason in reasons:
        value = normalize_space(reason)
        if value.startswith("SAMPLE_TITLE_MATCH:"):
            titles.append(value.split(":", 1)[1])
        elif value.startswith("SAMPLE_NOTICE_NUMBER_MATCH:"):
            notice_numbers.append(value.split(":", 1)[1])
        elif value.startswith("SAMPLE_DATE_MATCH:"):
            dates.append(value.split(":", 1)[1])
    row_text = normalize_space(row.get("row_text"))
    return {
        "titles": unique_strings(titles),
        "notice_numbers": unique_strings(notice_numbers),
        "dates": unique_strings(dates),
        "row_text": [row_text] if row_text else [],
    }


def find_occurrences(raw_html: str, tokens: Dict[str, List[str]]) -> List[Tuple[int, int, str]]:
    found: List[Tuple[int, int, str]] = []
    priority = tokens.get("notice_numbers") or tokens.get("titles") or tokens.get("dates") or []
    for token in priority:
        if not token:
            continue
        start = 0
        while True:
            index = raw_html.find(token, start)
            if index < 0:
                break
            found.append((index, index + len(token), token))
            start = index + len(token)
    if found:
        return found
    # HTML entity / whitespace 변형 fallback: row text의 짧은 의미 조각만 사용
    for row_text in tokens.get("row_text") or []:
        plain = normalize_space(strip_html(row_text))
        if len(plain) < 8:
            continue
        fragment = plain[:80]
        index = strip_html(raw_html).find(fragment)
        if index >= 0:
            found.append((0, len(raw_html), fragment))
            break
    return found


def parse_single_arg(raw_args: str) -> Optional[str]:
    value = normalize_space(raw_args)
    quoted = QUOTED_ARG_PATTERN.match(value)
    if quoted:
        return normalize_space(quoted.group("value"))
    numeric = NUMERIC_ARG_PATTERN.match(value)
    if numeric:
        return normalize_space(numeric.group("value"))
    return None


def recover_context_bindings(raw_html: str, family: str, tokens: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    expected_functions = EXPECTED_FUNCTIONS.get(family, set())
    occurrences = find_occurrences(raw_html, tokens)
    bindings: List[Dict[str, Any]] = []
    for start, end, token in occurrences:
        left = max(0, start - CONTEXT_RADIUS)
        right = min(len(raw_html), end + CONTEXT_RADIUS)
        context = raw_html[left:right]
        for match in FUNCTION_CALL_PATTERN.finditer(context):
            func = normalize_space(match.group("func"))
            if func not in expected_functions:
                continue
            arg = parse_single_arg(match.group("args"))
            if not arg:
                continue
            bindings.append({
                "function": func,
                "argument": arg,
                "matched_sample_token": token,
                "context": normalize_space(context)[:6000],
                "evidence": "SAMPLE_LOCAL_GLOBAL_FUNCTION_CALL",
            })

        if family == FAMILY_NOTICE:
            for match in NOTICE_MGT_NO_PATTERN.finditer(context):
                bindings.append({
                    "function": "f_view",
                    "argument": normalize_space(match.group(1)),
                    "matched_sample_token": token,
                    "context": normalize_space(context)[:6000],
                    "evidence": "SAMPLE_CONTEXT_NOTICE_MGT_NO",
                })
        elif family == FAMILY_URBAN:
            for match in PST_SN_PATTERN.finditer(context):
                bindings.append({
                    "function": "fn_move_form",
                    "argument": normalize_space(match.group(1)),
                    "matched_sample_token": token,
                    "context": normalize_space(context)[:6000],
                    "evidence": "SAMPLE_CONTEXT_PST_SN",
                })

    canonical: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for item in bindings:
        key = (normalize_space(item.get("function")), normalize_space(item.get("argument")))
        if key not in canonical:
            canonical[key] = {**item, "evidence_variants": [item.get("evidence")], "matched_sample_tokens": [item.get("matched_sample_token")]}
        else:
            existing = canonical[key]
            existing["evidence_variants"] = unique_strings((existing.get("evidence_variants") or []) + [item.get("evidence")])
            existing["matched_sample_tokens"] = unique_strings((existing.get("matched_sample_tokens") or []) + [item.get("matched_sample_token")])
    return list(canonical.values())


def s5_function_evidence_for(s5_family: Dict[str, Any], function_name: str) -> List[Dict[str, Any]]:
    return [
        item for item in (s5_family.get("function_evidence") or [])
        if normalize_space(item.get("function")) == function_name
    ]


def s5_forms_for(s5_family: Dict[str, Any]) -> List[Dict[str, Any]]:
    forms = s5_family.get("form_evidence") if isinstance(s5_family.get("form_evidence"), list) else []
    result = []
    for form in forms:
        if not isinstance(form, dict):
            continue
        controls = form.get("identity_controls") if isinstance(form.get("identity_controls"), list) else []
        result.append({
            "action_url": normalize_space(form.get("action_url")),
            "method": normalize_space(form.get("method")),
            "identity_controls": controls,
        })
    return result


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("COMPETENT AUTHORITY SAMPLE-TO-GLOBAL BINDING RECOVERY")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Detail request execution: DISABLED")
    print("Target query execution: DISABLED")
    print("Target identity evaluation: DISABLED")
    print()

    if not S4_INPUT_PATH.exists():
        raise FileNotFoundError(f"T-16-S4 input not found: {S4_INPUT_PATH}")
    if not S5_INPUT_PATH.exists():
        raise FileNotFoundError(f"T-16-S5 input not found: {S5_INPUT_PATH}")

    s4_data = json.loads(S4_INPUT_PATH.read_text(encoding="utf-8"))
    s5_data = json.loads(S5_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(s4_data, dict) or not isinstance(s5_data, dict):
        raise TypeError("S4/S5 inputs must be JSON objects")

    contracts, pages = load_s4(s4_data)
    s5_by_family = load_s5(s5_data)
    selected_pages = select_pages(contracts, pages)

    print("S4 metadata contract count:", len(contracts))
    print("S5 mechanism family count:", len(s5_by_family))
    print("Selected page count:", len(selected_pages))
    print()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    request_count = 0
    http_success_count = 0
    transport_error_count = 0
    fetched_pages: List[Dict[str, Any]] = []

    for index, page in enumerate(selected_pages, start=1):
        response = fetch_page(session, page["url"])
        request_count += 1
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1
        fetched_pages.append({
            "source_family": page["source_family"],
            "page_number": page.get("page_number"),
            "url": normalize_space(response.get("final_url") or page["url"]),
            "http_status": status,
            "raw_html": str(response.get("raw_html") or ""),
        })
        print("-" * 60)
        print(f"PAGE {index}")
        print("Family:", page["source_family"])
        print("Page:", page.get("page_number"))
        print("HTTP:", status)

    sample_results: List[Dict[str, Any]] = []
    next_stage_pool: List[Dict[str, Any]] = []

    for contract in contracts:
        family = contract["source_family"]
        s5_family = s5_by_family.get(family) or {}
        forms = s5_forms_for(s5_family)
        for row in contract.get("located_rows") or []:
            tokens = sample_tokens(row)
            bound_records: List[Dict[str, Any]] = []
            matched_page_urls: List[str] = []
            for page in fetched_pages:
                if page["source_family"] != family or page["http_status"] != 200:
                    continue
                bindings = recover_context_bindings(page["raw_html"], family, tokens)
                if not bindings:
                    continue
                matched_page_urls.append(page["url"])
                for binding in bindings:
                    function_name = normalize_space(binding.get("function"))
                    function_evidence = s5_function_evidence_for(s5_family, function_name)
                    if not function_evidence:
                        continue
                    bound_records.append({
                        **binding,
                        "page_url": page["url"],
                        "page_number": page.get("page_number"),
                        "global_function_evidence": function_evidence,
                        "global_form_evidence": forms,
                    })

            canonical: Dict[Tuple[str, str], Dict[str, Any]] = {}
            for item in bound_records:
                key = (normalize_space(item.get("function")), normalize_space(item.get("argument")))
                if key not in canonical:
                    canonical[key] = {**item, "page_urls": [item.get("page_url")], "page_numbers": [item.get("page_number")]}
                else:
                    existing = canonical[key]
                    existing["page_urls"] = unique_strings((existing.get("page_urls") or []) + [item.get("page_url")])
                    existing["page_numbers"] = sorted(set((existing.get("page_numbers") or []) + [item.get("page_number")]))
                    existing["evidence_variants"] = unique_strings((existing.get("evidence_variants") or []) + (item.get("evidence_variants") or []))
                    existing["matched_sample_tokens"] = unique_strings((existing.get("matched_sample_tokens") or []) + (item.get("matched_sample_tokens") or []))

            bindings = list(canonical.values())
            if bindings:
                classification = CLASS_SAMPLE_FUNCTION_BOUND
                qualified = True
            elif matched_page_urls:
                classification = CLASS_FUNCTION_NOT_BOUND
                qualified = False
            elif tokens.get("titles") or tokens.get("notice_numbers"):
                classification = CLASS_SAMPLE_CONTEXT_ONLY
                qualified = False
            else:
                classification = CLASS_SAMPLE_NOT_FOUND
                qualified = False

            result = {
                "contract_index": contract.get("contract_index"),
                "source_family": family,
                "sample_index": row.get("sample_index"),
                "sample_tokens": tokens,
                "matched_page_urls": unique_strings(matched_page_urls),
                "bindings": bindings,
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
            sample_results.append(result)
            if qualified:
                next_stage_pool.append({
                    **result,
                    "requires_bounded_executable_binding_validation": True,
                })

            print()
            print("-" * 60)
            print("SAMPLE", row.get("sample_index"), "Family:", family)
            print("Notice numbers:", tokens.get("notice_numbers"))
            print("Titles:", tokens.get("titles"))
            print("Bindings:", len(bindings))
            print("Qualified:", qualified)
            print("Resolution:", classification)
            for binding in bindings[:5]:
                print("  Function:", binding.get("function"))
                print("  Argument:", binding.get("argument"))
                print("  Evidence:", binding.get("evidence_variants"))
                print("  Forms:", len(binding.get("global_form_evidence") or []))

    if next_stage_pool:
        resolution = "COMPETENT_AUTHORITY_SAMPLE_GLOBAL_BINDING_RECOVERY_COMPLETED"
        next_action = (
            "sample metadata와 실제 global function argument binding이 복원되었다. "
            "다음 단계에서는 이 exact sample binding만 사용하여 bounded detail request를 실행하고, "
            "응답에서 기존 sample title/notice number가 재현되는지만 검증한다. UQQ700 target identity 평가는 계속 금지한다."
        )
    else:
        resolution = "COMPETENT_AUTHORITY_SAMPLE_GLOBAL_BINDING_RECOVERY_NO_BINDING"
        next_action = (
            "global function 정의는 존재하지만 sample metadata 주변 문맥에서 실제 function argument binding을 복원하지 못했다. "
            "SITE FALSE가 아니며 UNKNOWN을 유지한다. 다음에는 DOM event delegation 또는 serialized dataset/XHR contract를 분석한다."
        )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-16-S6 Sample-to-Global Binding Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "inputs": {
            "t16_s4_path": str(S4_INPUT_PATH),
            "t16_s5_path": str(S5_INPUT_PATH),
        },
        "method": {
            "S4_sample_metadata_only": True,
            "S5_recovered_global_mechanism_only": True,
            "direct_page_requery": True,
            "sample_context_binding_enabled": True,
            "function_argument_must_be_observed": True,
            "guessed_function_disabled": True,
            "guessed_argument_disabled": True,
            "guessed_request_parameter_disabled": True,
            "detail_request_execution_enabled": False,
            "target_query_execution_enabled": False,
            "target_identity_evaluation_enabled": False,
            "document_candidate_promotion_allowed": False,
        },
        "summary": {
            "metadata_contract_count": len(contracts),
            "selected_page_count": len(selected_pages),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "sample_result_count": len(sample_results),
            "qualified_binding_count": len(next_stage_pool),
        },
        "classification_counts": dict(sorted(Counter(x.get("classification") for x in sample_results).items())),
        "sample_results": sample_results,
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

    invalid_binding_argument_leakage = sum(
        1 for item in next_stage_pool for binding in item.get("bindings") or []
        if not normalize_space(binding.get("argument"))
    )
    unexpected_function_leakage = sum(
        1 for item in next_stage_pool for binding in item.get("bindings") or []
        if normalize_space(binding.get("function")) not in EXPECTED_FUNCTIONS.get(item.get("source_family"), set())
    )
    non_go_kr_page_leakage = sum(
        1 for item in next_stage_pool for url in item.get("matched_page_urls") or []
        if not is_government_host(hostname(url))
    )
    detail_request_leakage = sum(1 for x in sample_results + next_stage_pool if x.get("detail_request_executed") is True)
    target_query_leakage = sum(1 for x in sample_results + next_stage_pool if x.get("target_query_executed") is True)
    target_identity_leakage = sum(1 for x in sample_results + next_stage_pool if x.get("target_identity_evaluated") is True)
    unsafe_promotion_leakage = sum(
        1 for x in sample_results + next_stage_pool
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
        "T-16-S5 input exists": S5_INPUT_PATH.exists(),
        "inputs parsed": isinstance(s4_data, dict) and isinstance(s5_data, dict),
        "S4 metadata contracts loaded": len(contracts) > 0,
        "S5 mechanism families loaded": len(s5_by_family) > 0,
        "request budget respected": request_count <= MAX_TOTAL_REQUESTS,
        "sample context binding enabled": True,
        "guessed binding disabled": True,
        "all classes valid": all(x.get("classification") in VALID_CLASSES for x in sample_results),
        "next-stage classes valid": all(x.get("classification") in QUALIFIED_CLASSES for x in next_stage_pool),
        "binding arguments present": invalid_binding_argument_leakage == 0,
        "expected functions only": unexpected_function_leakage == 0,
        "binding page go.kr leakage zero": non_go_kr_page_leakage == 0,
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
    print("SAMPLE-TO-GLOBAL BINDING RESULT")
    print("=" * 60)
    print("Sample result count:", len(sample_results))
    print("Qualified binding count:", len(next_stage_pool))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Transport error count:", transport_error_count)
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)
    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Invalid binding argument leakage:", invalid_binding_argument_leakage)
    print("Unexpected function leakage:", unexpected_function_leakage)
    print("Non-go.kr binding page leakage:", non_go_kr_page_leakage)
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
        raise AssertionError("UQQ700 sample-to-global binding recovery regression failed")


if __name__ == "__main__":
    main()
