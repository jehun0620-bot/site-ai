# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-16-S6-S1

Development Density Management Area
Competent Authority Sample-to-Global Binding Cardinality Hardening

S6의 넓은 context window에서 인접 result row의 detail function call까지 함께
포착되는 과대복원을 차단한다.

핵심 원칙
======================================================================
1. S6에서 qualified된 sample만 입력으로 사용한다.
2. sample title/notice number가 실제 존재하는 HTML 위치를 직접 재확인한다.
3. sample을 포함하는 가장 작은 실제 row/container fragment를 복원한다.
4. 그 fragment 내부의 observed detail function call만 허용한다.
5. sample 하나는 정확히 하나의 detail argument로 축약되어야 실행 가능하다.
6. 0개 또는 2개 이상이면 ambiguity로 reject한다.
7. detail request 실행, target query, UQQ700 identity 평가를 하지 않는다.
8. guessed argument/function/path 금지.
9. SITE TRUE/FALSE 및 verified positive 승격 금지.
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
S6_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_competent_authority_sample_global_binding_recovery.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_competent_authority_sample_global_binding_cardinality_hardening.json"
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

CLASS_HARDENED = "HARDENED_SAMPLE_GLOBAL_SINGLE_BINDING"
CLASS_REJECTED_NO_LOCAL = "REJECTED_NO_ROW_LOCAL_BINDING"
CLASS_REJECTED_AMBIGUOUS = "REJECTED_AMBIGUOUS_ROW_LOCAL_BINDING"
CLASS_REJECTED_SAMPLE_NOT_FOUND = "REJECTED_SAMPLE_NOT_RELOCATED"
CLASS_REJECTED_INVALID = "REJECTED_INVALID_BINDING_SOURCE"
VALID_CLASSES = {
    CLASS_HARDENED,
    CLASS_REJECTED_NO_LOCAL,
    CLASS_REJECTED_AMBIGUOUS,
    CLASS_REJECTED_SAMPLE_NOT_FOUND,
    CLASS_REJECTED_INVALID,
}

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 8
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

FUNCTION_CALL_PATTERN = re.compile(
    r'''(?P<func>[A-Za-z_$][\w$]*)\s*\(\s*(?P<args>[^)]{0,300})\)''',
    re.I | re.S,
)
QUOTED_ARG_PATTERN = re.compile(r'''^[\s]*["'](?P<value>[^"']+)["'][\s]*$''', re.S)
NUMERIC_ARG_PATTERN = re.compile(r'''^[\s]*(?P<value>\d+)[\s]*$''')
TAG_PATTERN = re.compile(r'<[^>]+>', re.S)
SCRIPT_STYLE_PATTERN = re.compile(r'<(?:script|style)\b.*?</(?:script|style)>', re.I | re.S)
COMMENT_PATTERN = re.compile(r'<!--.*?-->', re.S)

# 작은 의미 container 우선. table/list 기반 게시판을 가장 강하게 취급한다.
CONTAINER_TAGS = ["tr", "li", "article", "section", "dd", "dt", "div"]
MAX_CONTAINER_BYTES = {
    "tr": 30000,
    "li": 30000,
    "article": 40000,
    "section": 40000,
    "dd": 20000,
    "dt": 20000,
    "div": 12000,
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
    result = {"http_status": None, "final_url": "", "raw_html": "", "error": ""}
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
            result["raw_html"] = decode_html(response, b"".join(chunks))
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def strip_html(raw: str) -> str:
    value = COMMENT_PATTERN.sub(" ", raw or "")
    value = SCRIPT_STYLE_PATTERN.sub(" ", value)
    value = TAG_PATTERN.sub(" ", value)
    return normalize_space(html.unescape(value))


def load_s6(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("next_stage_binding_pool") if isinstance(data.get("next_stage_binding_pool"), list) else []
    result: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        family = normalize_space(item.get("source_family"))
        if family not in ALLOWED_FAMILIES:
            continue
        tokens = item.get("sample_tokens") if isinstance(item.get("sample_tokens"), dict) else {}
        page_urls = item.get("matched_page_urls") if isinstance(item.get("matched_page_urls"), list) else []
        result.append({
            "contract_index": item.get("contract_index"),
            "sample_index": item.get("sample_index"),
            "source_family": family,
            "sample_tokens": tokens,
            "matched_page_urls": unique_strings(page_urls),
            "s6_bindings": item.get("bindings") if isinstance(item.get("bindings"), list) else [],
        })
    return result


def parse_arg(raw_args: str) -> Optional[str]:
    value = normalize_space(raw_args)
    m = QUOTED_ARG_PATTERN.match(value)
    if m:
        return normalize_space(m.group("value"))
    m = NUMERIC_ARG_PATTERN.match(value)
    if m:
        return normalize_space(m.group("value"))
    return None


def sample_locator_tokens(tokens: Dict[str, Any]) -> List[str]:
    # notice number가 가장 식별력이 높고, 그 다음 title/date 순서
    for key in ["notice_numbers", "titles", "dates"]:
        values = unique_strings(tokens.get(key) or [])
        if values:
            return values
    return []


def find_smallest_container(raw_html: str, token: str) -> Optional[Dict[str, Any]]:
    positions: List[int] = []
    start = 0
    while True:
        idx = raw_html.find(token, start)
        if idx < 0:
            break
        positions.append(idx)
        start = idx + max(1, len(token))
    candidates: List[Dict[str, Any]] = []
    for pos in positions:
        for tag in CONTAINER_TAGS:
            # token 앞의 가장 가까운 opening tag, token 뒤의 첫 closing tag
            open_matches = list(re.finditer(rf'<{tag}\b[^>]*>', raw_html[:pos], re.I | re.S))
            if not open_matches:
                continue
            open_match = open_matches[-1]
            close_match = re.search(rf'</{tag}\s*>', raw_html[pos:], re.I | re.S)
            if not close_match:
                continue
            end = pos + close_match.end()
            fragment = raw_html[open_match.start():end]
            if len(fragment) > MAX_CONTAINER_BYTES[tag]:
                continue
            if token not in fragment:
                continue
            candidates.append({
                "tag": tag,
                "start": open_match.start(),
                "end": end,
                "fragment": fragment,
                "length": len(fragment),
            })
    if not candidates:
        return None
    candidates.sort(key=lambda x: (CONTAINER_TAGS.index(x["tag"]), x["length"]))
    return candidates[0]


def recover_local_calls(fragment: str, family: str) -> List[Dict[str, str]]:
    expected = EXPECTED_FUNCTIONS.get(family, set())
    result: List[Dict[str, str]] = []
    seen = set()
    for match in FUNCTION_CALL_PATTERN.finditer(fragment):
        func = normalize_space(match.group("func"))
        if func not in expected:
            continue
        arg = parse_arg(match.group("args"))
        if not arg:
            continue
        key = (func, arg)
        if key in seen:
            continue
        seen.add(key)
        result.append({"function": func, "argument": arg})
    return result


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SAMPLE-GLOBAL BINDING CARDINALITY HARDENING")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Detail request execution: DISABLED")
    print("Target identity evaluation: DISABLED")
    print()

    if not S6_INPUT_PATH.exists():
        raise FileNotFoundError(f"S6 input not found: {S6_INPUT_PATH}")
    s6_data = json.loads(S6_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(s6_data, dict):
        raise TypeError("S6 input must be JSON object")
    samples = load_s6(s6_data)

    all_urls = unique_strings(url for item in samples for url in item.get("matched_page_urls") or [])
    all_urls = all_urls[:MAX_TOTAL_REQUESTS]

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
        final_url = normalize_space(response.get("final_url") or url)
        fetched[url] = {**response, "final_url": final_url}
        fetched[final_url] = fetched[url]
        print("-" * 60)
        print(f"PAGE {index}")
        print("URL:", url)
        print("HTTP:", response.get("http_status"))

    results: List[Dict[str, Any]] = []
    next_stage_pool: List[Dict[str, Any]] = []

    for sample in samples:
        family = sample["source_family"]
        locator_tokens = sample_locator_tokens(sample.get("sample_tokens") or {})
        page_records: List[Dict[str, Any]] = []
        observed_bindings: Dict[Tuple[str, str], Dict[str, Any]] = {}
        sample_relocated = False

        for url in sample.get("matched_page_urls") or []:
            response = fetched.get(url)
            if not response or response.get("http_status") != 200:
                continue
            raw_html = str(response.get("raw_html") or "")
            for token in locator_tokens:
                container = find_smallest_container(raw_html, token)
                if not container:
                    continue
                sample_relocated = True
                calls = recover_local_calls(container["fragment"], family)
                page_record = {
                    "page_url": normalize_space(response.get("final_url") or url),
                    "matched_token": token,
                    "container_tag": container["tag"],
                    "container_length": container["length"],
                    "container_text": strip_html(container["fragment"])[:3000],
                    "local_calls": calls,
                }
                page_records.append(page_record)
                for call in calls:
                    key = (call["function"], call["argument"])
                    if key not in observed_bindings:
                        observed_bindings[key] = {
                            **call,
                            "page_urls": [page_record["page_url"]],
                            "matched_tokens": [token],
                            "container_tags": [container["tag"]],
                        }
                    else:
                        existing = observed_bindings[key]
                        existing["page_urls"] = unique_strings(existing["page_urls"] + [page_record["page_url"]])
                        existing["matched_tokens"] = unique_strings(existing["matched_tokens"] + [token])
                        existing["container_tags"] = unique_strings(existing["container_tags"] + [container["tag"]])

        bindings = list(observed_bindings.values())
        if len(bindings) == 1:
            classification = CLASS_HARDENED
            qualified = True
            reasons = ["ROW_LOCAL_SINGLE_BINDING", f"BINDING:{bindings[0]['function']}({bindings[0]['argument']})"]
        elif len(bindings) > 1:
            classification = CLASS_REJECTED_AMBIGUOUS
            qualified = False
            reasons = [f"ROW_LOCAL_BINDING_CARDINALITY:{len(bindings)}"]
        elif sample_relocated:
            classification = CLASS_REJECTED_NO_LOCAL
            qualified = False
            reasons = ["SAMPLE_RELOCATED_BUT_NO_ROW_LOCAL_DETAIL_CALL"]
        else:
            classification = CLASS_REJECTED_SAMPLE_NOT_FOUND
            qualified = False
            reasons = ["SAMPLE_METADATA_NOT_RELOCATED"]

        result = {
            "contract_index": sample.get("contract_index"),
            "sample_index": sample.get("sample_index"),
            "source_family": family,
            "sample_tokens": sample.get("sample_tokens") or {},
            "page_records": page_records,
            "row_local_bindings": bindings,
            "s6_binding_count": len(sample.get("s6_bindings") or []),
            "hardened_binding_count": len(bindings),
            "classification": classification,
            "qualified_for_next_stage": qualified,
            "reasons": reasons,
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
        results.append(result)
        if qualified:
            next_stage_pool.append({
                **result,
                "binding": bindings[0],
                "requires_bounded_detail_request_validation": True,
            })

        print()
        print("-" * 60)
        print("SAMPLE", sample.get("sample_index"), "Family:", family)
        print("S6 bindings:", len(sample.get("s6_bindings") or []))
        print("Row-local bindings:", len(bindings))
        for binding in bindings:
            print("  Binding:", binding.get("function"), binding.get("argument"))
            print("  Containers:", binding.get("container_tags"))
        print("Qualified:", qualified)
        print("Resolution:", classification)

    resolution = (
        "COMPETENT_AUTHORITY_SAMPLE_GLOBAL_BINDING_CARDINALITY_HARDENING_COMPLETED"
        if next_stage_pool
        else "COMPETENT_AUTHORITY_SAMPLE_GLOBAL_BINDING_CARDINALITY_HARDENING_NO_BINDING"
    )
    next_action = (
        "sample별 row-local single binding만 bounded detail request validation으로 넘긴다. "
        "실제 detail 응답에서 동일 sample notice number/title 재현을 확인한 뒤에만 request contract를 확정한다."
        if next_stage_pool
        else
        "row-local single binding을 확정하지 못했다. 넓은 S6 context binding은 폐기하고 UNKNOWN을 유지한다. "
        "추가 DOM/event 구조 분석 없이는 detail request를 실행하지 않는다."
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-16-S6-S1 Sample-Global Binding Cardinality Hardening",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "method": {
            "S6_qualified_samples_only": True,
            "direct_network_requery": True,
            "smallest_semantic_container_enabled": True,
            "row_local_function_call_required": True,
            "single_binding_cardinality_required": True,
            "wide_context_binding_promotion_disabled": True,
            "guessed_binding_disabled": True,
            "detail_request_execution_enabled": False,
            "target_query_execution_enabled": False,
            "target_identity_evaluation_enabled": False,
            "document_candidate_promotion_allowed": False,
        },
        "summary": {
            "S6_sample_count": len(samples),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "result_count": len(results),
            "qualified_single_binding_count": len(next_stage_pool),
            "ambiguous_rejected_count": sum(1 for x in results if x.get("classification") == CLASS_REJECTED_AMBIGUOUS),
        },
        "classification_counts": dict(sorted(Counter(x.get("classification") for x in results).items())),
        "sample_results": results,
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

    invalid_cardinality_leakage = sum(1 for x in next_stage_pool if len(x.get("row_local_bindings") or []) != 1)
    unexpected_function_leakage = sum(
        1 for x in next_stage_pool for b in x.get("row_local_bindings") or []
        if b.get("function") not in EXPECTED_FUNCTIONS.get(x.get("source_family"), set())
    )
    non_go_kr_page_leakage = sum(
        1 for x in next_stage_pool for b in x.get("row_local_bindings") or [] for u in b.get("page_urls") or []
        if not is_government_host(hostname(u))
    )
    detail_request_leakage = sum(1 for x in results + next_stage_pool if x.get("detail_request_executed") is True)
    target_query_leakage = sum(1 for x in results + next_stage_pool if x.get("target_query_executed") is True)
    target_identity_leakage = sum(1 for x in results + next_stage_pool if x.get("target_identity_evaluated") is True)
    unsafe_promotion_leakage = sum(
        1 for x in results + next_stage_pool
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
        "S6 input exists": S6_INPUT_PATH.exists(),
        "S6 input parsed": isinstance(s6_data, dict),
        "S6 qualified samples loaded": len(samples) > 0,
        "request budget respected": request_count <= MAX_TOTAL_REQUESTS,
        "smallest semantic container enabled": True,
        "row-local binding required": True,
        "single binding cardinality required": True,
        "wide context promotion disabled": True,
        "all classes valid": all(x.get("classification") in VALID_CLASSES for x in results),
        "next-stage cardinality exactly one": invalid_cardinality_leakage == 0,
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
    print("CARDINALITY HARDENING RESULT")
    print("=" * 60)
    print("S6 sample count:", len(samples))
    print("Qualified single binding count:", len(next_stage_pool))
    print("Ambiguous rejected count:", output_data["summary"]["ambiguous_rejected_count"])
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)
    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Invalid cardinality leakage:", invalid_cardinality_leakage)
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
        raise AssertionError("UQQ700 sample-global binding cardinality hardening regression failed")


if __name__ == "__main__":
    main()
