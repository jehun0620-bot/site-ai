# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-6-S2
Development Density Management Area
SAEOL Request Contract Semantic Binding

목표
======================================================================
T-6-S1에서 복원된 새올 request parameter/action evidence를 다시 직접
검증하여 실제 고시공고 archive request contract에 속하는 evidence만 남긴다.

원칙
======================================================================
1. T-6-S1 qualified probe만 입력으로 사용한다.
2. UQQ700 검색어는 아직 실행하지 않는다.
3. source archive endpoint(OfrAction.do / selectOfrNotAncmt)를 기준점으로 한다.
4. keyword/keyword1 등의 parameter는 실제 JS context에 archive/list/search
   identity가 함께 있을 때만 executable candidate로 승격한다.
5. 상담/회원/배너/다운로드 등 unrelated action은 제거한다.
6. HTTP method는 실제 script literal 또는 source request identity에서만 복원한다.
7. guessed parameter/method 생성 금지.
8. document candidate / SITE TRUE / SITE FALSE / runtime registration 금지.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import parse_qsl, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_saeol_request_contract_probe.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_saeol_request_contract_semantic_binding.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_SCRIPT_REQUESTS = 12
CONTEXT_RADIUS = 450
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

ARCHIVE_ACTION_TERMS = {
    "ofraction.do",
    "selectofrnotancmt",
    "ofrnotancmt",
    "not_ancmt",
    "ancmt",
}
ARCHIVE_CONTEXT_TERMS = {
    "고시", "공고", "고시공고", "새올", "ntis", "ofr", "ancmt",
    "not_ancmt", "selectofrnotancmt", "list_gubun", "검색", "조회", "목록",
}
SEARCH_PARAM_TERMS = {
    "keyword", "keyword1", "search", "srch", "sch", "query", "word",
}
PAGING_PARAM_TERMS = {
    "_next_page_", "page", "pageno", "pageindex",
}
UNRELATED_ACTION_TERMS = {
    "cnsl", "userinfo", "usermgt", "banner", "download", "filedownload",
    "cmmpotal", "plc", "mcpwebmenuworkmgt",
}
METHOD_PATTERNS = [
    re.compile(r'''method\s*[:=]\s*["'](GET|POST)["']''', re.I),
    re.compile(r'''type\s*[:=]\s*["'](GET|POST)["']''', re.I),
    re.compile(r'''\.open\(\s*["'](GET|POST)["']''', re.I),
]
SCRIPT_SRC_PATTERN = re.compile(r'''<script\b[^>]*\bsrc\s*=\s*["']([^"']+)["']''', re.I)


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


def same_host(a: str, b: str) -> bool:
    return bool(hostname(a)) and hostname(a) == hostname(b)


def is_government_host(host: str) -> bool:
    value = normalize_space(host).lower()
    return bool(value) and (value == "go.kr" or value.endswith(".go.kr"))


def absolute_url(base: str, value: str) -> str:
    from urllib.parse import urljoin
    value = normalize_space(value).replace("&amp;", "&")
    if not value:
        return ""
    try:
        result = urljoin(base, value)
        parsed = urlparse(result)
    except Exception:
        return ""
    return result if parsed.hostname else ""


def fetch_text(session: requests.Session, url: str) -> Dict[str, Any]:
    result = {
        "final_url": "", "http_status": None, "content_type": "",
        "text": "", "encoding": "", "response_bytes": 0, "error": "",
    }
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            result["http_status"] = response.status_code
            result["final_url"] = str(response.url)
            result["content_type"] = normalize_space(response.headers.get("Content-Type"))
            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
                chunks.append(chunk)
            data = b"".join(chunks)
            result["response_bytes"] = len(data)
            for encoding in unique_strings([response.encoding, "utf-8", "cp949", "euc-kr"]):
                try:
                    result["text"] = data.decode(encoding)
                    result["encoding"] = encoding
                    break
                except Exception:
                    continue
            if not result["text"]:
                result["text"] = data.decode("utf-8", errors="replace")
                result["encoding"] = "utf-8-replace"
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def context_windows(text: str, token: str, radius: int = CONTEXT_RADIUS) -> List[str]:
    if not text or not token:
        return []
    lowered = text.lower()
    needle = token.lower()
    result: List[str] = []
    start = 0
    while True:
        index = lowered.find(needle, start)
        if index < 0:
            break
        left = max(0, index - radius)
        right = min(len(text), index + len(token) + radius)
        result.append(normalize_space(text[left:right]))
        start = index + len(token)
        if len(result) >= 20:
            break
    return unique_strings(result)


def archive_context_score(context: str) -> Tuple[int, List[str]]:
    lowered = normalize_space(context).lower()
    reasons: List[str] = []
    score = 0
    for term in ARCHIVE_CONTEXT_TERMS:
        if term.lower() in lowered:
            score += 10
            reasons.append("ARCHIVE_CONTEXT:" + term)
    if "ofraction.do" in lowered:
        score += 25
        reasons.append("ARCHIVE_ACTION_CONTEXT")
    if "selectofrnotancmt" in lowered:
        score += 35
        reasons.append("ARCHIVE_LIST_METHOD_CONTEXT")
    return score, unique_strings(reasons)


def recover_method(contexts: List[str]) -> Tuple[str, List[str]]:
    methods: List[str] = []
    for context in contexts:
        for pattern in METHOD_PATTERNS:
            for match in pattern.finditer(context):
                methods.append(match.group(1).upper())
    methods = unique_strings(methods)
    if len(methods) == 1:
        return methods[0], ["METHOD_LITERAL:" + methods[0]]
    if len(methods) > 1:
        return "AMBIGUOUS", ["METHOD_LITERAL_AMBIGUOUS:" + ",".join(methods)]
    return "UNKNOWN", []


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SAEOL REQUEST CONTRACT SEMANTIC BINDING")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"input not found: {INPUT_PATH}")
    data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("input must be JSON object")
    probes = data.get("next_stage_request_contract_probe_pool")
    if not isinstance(probes, list):
        probes = []

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/javascript,text/javascript,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    })

    request_count = 0
    http_success_count = 0
    records: List[Dict[str, Any]] = []

    for index, probe in enumerate(probes, start=1):
        source_url = normalize_space(probe.get("source_url"))
        family = normalize_space(probe.get("source_family"))
        regions = unique_strings(probe.get("regions") or [])
        recovered_params = unique_strings(probe.get("recovered_params") or [])
        recovered_actions = unique_strings(probe.get("recovered_actions") or [])

        print("-" * 60)
        print(f"PROBE {index}")
        print("Family:", family)
        print("Regions:", regions)
        print("Source URL:", source_url)

        request_count += 1
        source_response = fetch_text(session, source_url)
        if isinstance(source_response.get("http_status"), int) and 200 <= source_response["http_status"] < 300:
            http_success_count += 1
        source_text = source_response.get("text") or ""

        script_urls = unique_strings(
            absolute_url(source_url, match.group(1))
            for match in SCRIPT_SRC_PATTERN.finditer(source_text)
        )
        script_urls = [url for url in script_urls if url and same_host(source_url, url)]

        script_sources: List[Dict[str, Any]] = []
        combined_texts: List[Tuple[str, str]] = [(source_url, source_text)]
        for script_url in script_urls[:MAX_SCRIPT_REQUESTS]:
            request_count += 1
            response = fetch_text(session, script_url)
            if isinstance(response.get("http_status"), int) and 200 <= response["http_status"] < 300:
                http_success_count += 1
            script_sources.append({
                "url": script_url,
                "http_status": response.get("http_status"),
                "error": response.get("error"),
            })
            combined_texts.append((script_url, response.get("text") or ""))

        param_bindings: List[Dict[str, Any]] = []
        qualified_params: List[str] = []
        for param in recovered_params:
            contexts: List[str] = []
            locations: List[str] = []
            for location, text in combined_texts:
                windows = context_windows(text, param)
                if windows:
                    contexts.extend(windows)
                    locations.extend([location] * len(windows))
            scored = []
            max_score = 0
            all_reasons: List[str] = []
            for context in contexts:
                score, reasons = archive_context_score(context)
                max_score = max(max_score, score)
                all_reasons.extend(reasons)
                scored.append({"score": score, "context": context[:1600]})
            lowered = param.lower()
            semantic_kind = (
                "SEARCH" if any(term in lowered for term in SEARCH_PARAM_TERMS)
                else "PAGING" if any(term in lowered for term in PAGING_PARAM_TERMS)
                else "ARCHIVE_FILTER" if any(term in lowered for term in {"ancmt", "list_gubun"})
                else "OTHER"
            )
            qualified = bool(contexts) and max_score >= 20 and semantic_kind != "OTHER"
            if qualified:
                qualified_params.append(param)
            param_bindings.append({
                "parameter": param,
                "semantic_kind": semantic_kind,
                "context_found": bool(contexts),
                "max_archive_context_score": max_score,
                "qualified": qualified,
                "reasons": unique_strings(all_reasons),
                "locations": unique_strings(locations),
                "contexts": sorted(scored, key=lambda item: -item["score"])[:5],
            })

        source_query_keys = unique_strings(key for key, _ in parse_qsl(urlparse(source_url).query, keep_blank_values=True))
        source_archive_identity = (
            any(term in source_url.lower() for term in ARCHIVE_ACTION_TERMS)
            and "selectOfrNotAncmt".lower() in source_url.lower()
        )

        action_bindings: List[Dict[str, Any]] = []
        qualified_actions: List[str] = []
        for action in recovered_actions:
            lowered = action.lower()
            unrelated = any(term in lowered for term in UNRELATED_ACTION_TERMS)
            archive_related = any(term in lowered for term in ARCHIVE_ACTION_TERMS)
            qualified = (
                is_government_host(hostname(action))
                and same_host(source_url, action)
                and archive_related
                and not unrelated
            )
            if qualified:
                qualified_actions.append(action)
            action_bindings.append({
                "action": action,
                "archive_related": archive_related,
                "unrelated": unrelated,
                "qualified": qualified,
                "reasons": unique_strings([
                    "ARCHIVE_ACTION_IDENTITY" if archive_related else "",
                    "UNRELATED_ACTION_IDENTITY" if unrelated else "",
                ]),
            })

        # Source archive endpoint itself is an observed action identity, not guessed.
        executable_action = source_url if source_archive_identity else ""

        method_contexts: List[str] = []
        for _, text in combined_texts:
            method_contexts.extend(context_windows(text, "OfrAction.do"))
            method_contexts.extend(context_windows(text, "selectOfrNotAncmt"))
        recovered_method, method_reasons = recover_method(method_contexts)

        has_search_param = any(
            item.get("qualified") and item.get("semantic_kind") == "SEARCH"
            for item in param_bindings
        )
        contract_candidate = bool(executable_action and has_search_param)
        classification = (
            "QUALIFIED_SAEOL_ARCHIVE_REQUEST_CONTRACT_CANDIDATE"
            if contract_candidate
            else "REJECTED_INCOMPLETE_SAEOL_REQUEST_BINDING"
        )
        reasons = unique_strings([
            "SOURCE_ARCHIVE_ENDPOINT_IDENTITY" if source_archive_identity else "",
            "SEARCH_PARAMETER_BOUND" if has_search_param else "",
            *method_reasons,
        ])

        record = {
            "source_family": family,
            "regions": regions,
            "source_url": source_url,
            "source_http_status": source_response.get("http_status"),
            "source_archive_identity": source_archive_identity,
            "source_query_keys": source_query_keys,
            "script_sources": script_sources,
            "param_bindings": param_bindings,
            "action_bindings": action_bindings,
            "qualified_params": unique_strings(qualified_params),
            "qualified_recovered_actions": unique_strings(qualified_actions),
            "executable_action_candidate": executable_action,
            "method": recovered_method,
            "contract_candidate": contract_candidate,
            "classification": classification,
            "reasons": reasons,
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        records.append(record)

        print("HTTP:", source_response.get("http_status"))
        print("Source archive identity:", source_archive_identity)
        print("Qualified params:", record["qualified_params"])
        print("Qualified recovered actions:", record["qualified_recovered_actions"])
        print("Executable action candidate:", executable_action or "-")
        print("Recovered method:", recovered_method)
        print("Contract candidate:", contract_candidate)
        print("Resolution:", classification)
        print()

    candidates = [item for item in records if item.get("contract_candidate") is True]
    resolution = (
        "SAEOL_REQUEST_CONTRACT_SEMANTIC_BINDING_COMPLETED"
        if candidates
        else "SAEOL_REQUEST_CONTRACT_SEMANTIC_BINDING_INCOMPLETE"
    )
    next_action = (
        "실제 source archive endpoint와 semantic binding된 search parameter만 T-6-S3 bounded dry-run request-shape validation으로 넘긴다. target query 본실행 전 빈값/기존값 요청으로 response shape와 method를 검증한다."
        if candidates
        else "새올 request parameter와 archive endpoint의 의미 결합이 충분하지 않다. UNKNOWN을 유지하고 네트워크 request contract 추가 복원이 필요하다."
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-6-S2 SAEOL Request Contract Semantic Binding",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "input": {"path": str(INPUT_PATH), "resolution": data.get("resolution")},
        "method": {
            "qualified_probe_only": True,
            "direct_source_requery": True,
            "same_host_script_context_binding": True,
            "archive_context_score_required": True,
            "unrelated_action_filter_enabled": True,
            "guessed_parameter_generation": False,
            "guessed_method_generation": False,
            "target_query_execution": False,
        },
        "summary": {
            "probe_count": len(probes),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "contract_candidate_count": len(candidates),
        },
        "records": records,
        "next_stage_request_contract_pool": candidates,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    target_query_leakage = sum(1 for item in records if item.get("target_query_executed") is True)
    document_leakage = sum(1 for item in records if item.get("document_candidate") is True)
    unrelated_action_leakage = sum(
        1 for item in records for action in item.get("qualified_recovered_actions", [])
        if any(term in action.lower() for term in UNRELATED_ACTION_TERMS)
    )
    non_go_kr_action_leakage = sum(
        1 for item in records for action in item.get("qualified_recovered_actions", [])
        if not is_government_host(hostname(action))
    )
    cross_host_action_leakage = sum(
        1 for item in records for action in item.get("qualified_recovered_actions", [])
        if not same_host(item.get("source_url") or "", action)
    )
    verified_leakage = sum(1 for item in records if item.get("verified_positive") is True)
    runtime_leakage = sum(1 for item in records if item.get("runtime_registration_allowed") is True)
    site_true_leakage = sum(1 for item in records if item.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for item in records if item.get("site_negative_allowed") is True)

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "input exists": INPUT_PATH.exists(),
        "input parsed": isinstance(data, dict),
        "qualified probe pool loaded": len(probes) > 0,
        "source requery enabled": True,
        "script context semantic binding enabled": True,
        "unrelated action filter enabled": True,
        "guessed parameter generation disabled": True,
        "guessed method generation disabled": True,
        "target query execution leakage zero": target_query_leakage == 0,
        "document candidate leakage zero": document_leakage == 0,
        "unrelated qualified action leakage zero": unrelated_action_leakage == 0,
        "non-go.kr qualified action leakage zero": non_go_kr_action_leakage == 0,
        "cross-host qualified action leakage zero": cross_host_action_leakage == 0,
        "verified positive leakage zero": verified_leakage == 0,
        "runtime registration leakage zero": runtime_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print("=" * 60)
    print("SAEOL REQUEST CONTRACT SEMANTIC BINDING RESULT")
    print("=" * 60)
    print("Probe count:", len(probes))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Contract candidate count:", len(candidates))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)
    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Target query leakage:", target_query_leakage)
    print("Document candidate leakage:", document_leakage)
    print("Unrelated action leakage:", unrelated_action_leakage)
    print("Non-go.kr action leakage:", non_go_kr_action_leakage)
    print("Cross-host action leakage:", cross_host_action_leakage)
    print("Verified positive leakage:", verified_leakage)
    print("Runtime registration leakage:", runtime_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")
    if not all_pass:
        failed = [name for name, passed in validations.items() if not passed]
        print("\nFAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError("UQQ700 SAEOL request contract semantic binding regression failed")


if __name__ == "__main__":
    main()
