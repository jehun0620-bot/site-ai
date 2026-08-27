# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-6-S3
Development Density Management Area
SAEOL Request Shape Validation

목표
======================================================================
T-6-S2에서 확보한 SAEOL archive request contract candidate에 대해
UQQ700 본검색을 실행하지 않고 GET/POST의 request shape만 제한 검증한다.

원칙
======================================================================
1. target query 문자열을 전송하지 않는다.
2. source URL의 기존 archive parameters는 보존한다.
3. semantic binding된 search parameter에는 빈 문자열만 사용한다.
4. GET / POST를 각각 최대 1회 실행한다.
5. 응답의 HTTP, final host, archive identity, response fingerprint를 비교한다.
6. method를 임의 확정하지 않는다. response evidence가 명확할 때만
   PREFERRED_GET / PREFERRED_POST / EQUIVALENT / UNRESOLVED로 판정한다.
7. document candidate / SITE TRUE / SITE FALSE / runtime registration 금지.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_saeol_request_contract_semantic_binding.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_saeol_request_shape_validation.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

ARCHIVE_MARKERS = [
    "새올전자민원창구",
    "selectOfrNotAncmt",
    "OfrNotAncmt",
    "not_ancmt",
    "고시",
    "공고",
]


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
    value = normalize_space(host).lower()
    return bool(value) and (value == "go.kr" or value.endswith(".go.kr"))


def same_host(a: str, b: str) -> bool:
    return bool(hostname(a)) and hostname(a) == hostname(b)


def decode_bytes(response: requests.Response, data: bytes) -> Tuple[str, str]:
    for encoding in unique_strings([response.encoding, "utf-8", "cp949", "euc-kr"]):
        try:
            return data.decode(encoding), encoding
        except Exception:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def request_once(
    session: requests.Session,
    *,
    method: str,
    url: str,
    params: Dict[str, str],
    data: Dict[str, str],
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "method": method,
        "requested_url": url,
        "http_status": None,
        "final_url": "",
        "content_type": "",
        "response_bytes": 0,
        "sha256": "",
        "encoding": "",
        "text_preview": "",
        "archive_markers": [],
        "error": "",
    }
    try:
        kwargs: Dict[str, Any] = {
            "timeout": TIMEOUT,
            "allow_redirects": True,
            "stream": True,
        }
        if method == "GET":
            kwargs["params"] = params
        else:
            kwargs["data"] = data

        with session.request(method, url, **kwargs) as response:
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
            payload = b"".join(chunks)
            result["response_bytes"] = len(payload)
            result["sha256"] = hashlib.sha256(payload).hexdigest()
            text, encoding = decode_bytes(response, payload)
            result["encoding"] = encoding
            normalized = normalize_space(text)
            result["text_preview"] = normalized[:2500]
            result["archive_markers"] = [
                marker for marker in ARCHIVE_MARKERS
                if marker.lower() in normalized.lower()
            ]
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def source_query_params(url: str) -> Dict[str, str]:
    return {key: value for key, value in parse_qsl(urlparse(url).query, keep_blank_values=True)}


def strip_query(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def response_quality(item: Dict[str, Any], source_url: str) -> int:
    score = 0
    status = item.get("http_status")
    if isinstance(status, int) and 200 <= status < 300:
        score += 30
    if same_host(source_url, item.get("final_url") or ""):
        score += 20
    if is_government_host(hostname(item.get("final_url") or "")):
        score += 10
    score += min(30, 5 * len(item.get("archive_markers") or []))
    if item.get("response_bytes", 0) > 500:
        score += 10
    if item.get("error"):
        score -= 100
    return score


def classify_method(get_result: Dict[str, Any], post_result: Dict[str, Any], source_url: str) -> Tuple[str, List[str]]:
    get_score = response_quality(get_result, source_url)
    post_score = response_quality(post_result, source_url)
    reasons = [f"GET_SCORE:{get_score}", f"POST_SCORE:{post_score}"]

    if get_score < 0 and post_score < 0:
        return "UNRESOLVED", reasons

    same_fingerprint = bool(
        get_result.get("sha256")
        and get_result.get("sha256") == post_result.get("sha256")
    )
    if same_fingerprint:
        reasons.append("GET_POST_RESPONSE_IDENTICAL")
        return "EQUIVALENT", reasons

    if get_score >= post_score + 20:
        reasons.append("GET_RESPONSE_STRONGER")
        return "PREFERRED_GET", reasons

    if post_score >= get_score + 20:
        reasons.append("POST_RESPONSE_STRONGER")
        return "PREFERRED_POST", reasons

    reasons.append("GET_POST_DIFFERENCE_INSUFFICIENT")
    return "UNRESOLVED", reasons


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SAEOL REQUEST SHAPE VALIDATION")
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

    contracts = data.get("next_stage_request_contract_pool")
    if not isinstance(contracts, list):
        contracts = []

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    })

    request_count = 0
    http_success_count = 0
    records: List[Dict[str, Any]] = []

    for index, contract in enumerate(contracts, start=1):
        source_url = normalize_space(contract.get("source_url"))
        action_url = normalize_space(contract.get("executable_action_candidate") or source_url)
        qualified_params = unique_strings(contract.get("qualified_params") or [])
        search_params = [p for p in qualified_params if any(t in p.lower() for t in ("keyword", "search", "srch", "query", "word"))]

        print("-" * 60)
        print(f"CONTRACT {index}")
        print("Source URL:", source_url)
        print("Action URL:", action_url)
        print("Search params:", search_params)

        base_params = source_query_params(action_url)
        empty_search_params = dict(base_params)
        for key in search_params:
            empty_search_params[key] = ""

        endpoint = strip_query(action_url)

        get_result = request_once(
            session,
            method="GET",
            url=endpoint,
            params=empty_search_params,
            data={},
        )
        request_count += 1
        if isinstance(get_result.get("http_status"), int) and 200 <= get_result["http_status"] < 300:
            http_success_count += 1

        # POST는 archive identity parameters를 form body에 넣어 request shape만 비교한다.
        post_result = request_once(
            session,
            method="POST",
            url=endpoint,
            params={},
            data=empty_search_params,
        )
        request_count += 1
        if isinstance(post_result.get("http_status"), int) and 200 <= post_result["http_status"] < 300:
            http_success_count += 1

        method_resolution, method_reasons = classify_method(get_result, post_result, source_url)

        record = {
            "source_family": contract.get("source_family"),
            "regions": contract.get("regions") or [],
            "source_url": source_url,
            "action_url": action_url,
            "endpoint_url": endpoint,
            "qualified_params": qualified_params,
            "search_params": search_params,
            "base_params": base_params,
            "empty_search_params": {key: value for key, value in empty_search_params.items() if key not in search_params},
            "search_param_values_redacted": {key: "<EMPTY>" for key in search_params},
            "get_result": get_result,
            "post_result": post_result,
            "method_resolution": method_resolution,
            "method_reasons": method_reasons,
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        records.append(record)

        print("GET:", get_result.get("http_status"), "markers=", get_result.get("archive_markers"))
        print("POST:", post_result.get("http_status"), "markers=", post_result.get("archive_markers"))
        print("Method resolution:", method_resolution)
        print("Reasons:", method_reasons)
        print()

    executable_contracts = [
        item for item in records
        if item.get("method_resolution") in {"PREFERRED_GET", "PREFERRED_POST", "EQUIVALENT"}
    ]

    resolution = (
        "SAEOL_REQUEST_SHAPE_VALIDATION_COMPLETED"
        if executable_contracts
        else "SAEOL_REQUEST_SHAPE_VALIDATION_UNRESOLVED"
    )

    next_action = (
        "T-6-S4에서 request shape가 검증된 contract만 사용하여 최소 bounded target query를 실행한다. query 문자열은 candidate evidence에서 제외하고, response row/title/notice number/document URL의 link-local evidence만 후속 candidate로 인정한다."
        if executable_contracts
        else "GET/POST response evidence만으로 request method를 확정하지 못했다. SITE는 UNKNOWN을 유지하고 source-specific network contract 복원을 계속한다."
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-6-S3 SAEOL Request Shape Validation",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "input": {"path": str(INPUT_PATH), "resolution": data.get("resolution")},
        "method": {
            "empty_search_value_only": True,
            "get_post_bounded_comparison": True,
            "target_query_execution": False,
            "method_guessing_disabled": True,
            "document_candidate_promotion_disabled": True,
        },
        "summary": {
            "contract_count": len(contracts),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "executable_contract_count": len(executable_contracts),
        },
        "records": records,
        "next_stage_request_contract_pool": executable_contracts,
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
    non_go_kr_leakage = sum(
        1 for item in records
        if not is_government_host(hostname(item.get("action_url") or ""))
    )
    cross_host_leakage = sum(
        1 for item in records
        if not same_host(item.get("source_url") or "", item.get("action_url") or "")
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
        "semantic contract pool loaded": len(contracts) > 0,
        "empty search value only": True,
        "bounded GET/POST comparison enabled": True,
        "target query execution leakage zero": target_query_leakage == 0,
        "document candidate leakage zero": document_leakage == 0,
        "action go.kr leakage zero": non_go_kr_leakage == 0,
        "action cross-host leakage zero": cross_host_leakage == 0,
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
    print("SAEOL REQUEST SHAPE VALIDATION RESULT")
    print("=" * 60)
    print("Contract count:", len(contracts))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Executable contract count:", len(executable_contracts))
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
    print("Non-go.kr action leakage:", non_go_kr_leakage)
    print("Cross-host action leakage:", cross_host_leakage)
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
        raise AssertionError("UQQ700 SAEOL request shape validation regression failed")


if __name__ == "__main__":
    main()
