# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-6-S4-S1
Development Density Management Area
SAEOL Query Effectiveness Validation

목표
======================================================================
T-6-S4에서 GET/POST × keyword/keyword1 모든 query 실행이 동일한 1368-byte
response를 반환한 상황을 검증한다.

이번 단계에서는 target query를 다시 사용하지 않는다. 대신 이미 검증된
request shape에서 search parameter 값이 response에 실제 영향을 주는지 확인하기 위해
빈값 / 비대상 sentinel 값을 bounded하게 비교한다.

원칙
======================================================================
1. UQQ700 / 개발밀도관리구역 문자열을 전송하지 않는다.
2. sentinel은 법적 의미 없는 고유 문자열만 사용한다.
3. 검색 parameter별로 empty vs sentinel response fingerprint를 비교한다.
4. response가 동일하면 parameter-effectiveness를 FALSE로 확정하지 않고
   NO_OBSERVABLE_QUERY_EFFECT로 분류한다.
5. response가 달라지면 QUERY_EFFECT_OBSERVED로 분류한다.
6. 이 단계는 source/query contract diagnostic일 뿐 SITE evidence가 아니다.
7. document candidate / verified positive / SITE TRUE / SITE FALSE / runtime registration 금지.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import urlencode, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_saeol_request_shape_validation.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_saeol_query_effectiveness_validation.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

SENTINEL_QUERY = "ZZQX_NO_MATCH_20260827"
TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 8
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


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


def decode_bytes(response: requests.Response, payload: bytes) -> str:
    for encoding in unique_strings([response.encoding, "utf-8", "cp949", "euc-kr"]):
        try:
            return payload.decode(encoding)
        except Exception:
            continue
    return payload.decode("utf-8", errors="replace")


def execute(
    session: requests.Session,
    *,
    method: str,
    endpoint_url: str,
    base_params: Dict[str, str],
    search_param: str,
    search_value: str,
) -> Dict[str, Any]:
    params = dict(base_params)
    params[search_param] = search_value
    result: Dict[str, Any] = {
        "method": method,
        "search_param": search_param,
        "search_value_kind": "EMPTY" if search_value == "" else "SENTINEL",
        "http_status": None,
        "final_url": "",
        "content_type": "",
        "response_bytes": 0,
        "sha256": "",
        "sentinel_echo": False,
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
            kwargs["data"] = params

        with session.request(method, endpoint_url, **kwargs) as response:
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
            text = decode_bytes(response, payload)
            result["sentinel_echo"] = SENTINEL_QUERY in text
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SAEOL QUERY EFFECTIVENESS VALIDATION")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Target query execution: DISABLED")
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
        endpoint_url = normalize_space(contract.get("endpoint_url"))
        search_params = unique_strings(contract.get("search_params") or [])
        base_params = dict(contract.get("base_params") or {})
        method_resolution = normalize_space(contract.get("method_resolution"))

        methods = (
            ["GET", "POST"] if method_resolution == "EQUIVALENT"
            else ["GET"] if method_resolution == "PREFERRED_GET"
            else ["POST"] if method_resolution == "PREFERRED_POST"
            else []
        )

        print("-" * 60)
        print(f"CONTRACT {index}")
        print("Endpoint:", endpoint_url)
        print("Methods:", methods)
        print("Search params:", search_params)

        for method in methods:
            for search_param in search_params:
                if request_count + 2 > MAX_TOTAL_REQUESTS:
                    break

                empty_result = execute(
                    session,
                    method=method,
                    endpoint_url=endpoint_url,
                    base_params=base_params,
                    search_param=search_param,
                    search_value="",
                )
                sentinel_result = execute(
                    session,
                    method=method,
                    endpoint_url=endpoint_url,
                    base_params=base_params,
                    search_param=search_param,
                    search_value=SENTINEL_QUERY,
                )
                request_count += 2

                for result in (empty_result, sentinel_result):
                    status = result.get("http_status")
                    if isinstance(status, int) and 200 <= status < 300:
                        http_success_count += 1

                comparable = (
                    not empty_result.get("error")
                    and not sentinel_result.get("error")
                    and isinstance(empty_result.get("http_status"), int)
                    and isinstance(sentinel_result.get("http_status"), int)
                    and 200 <= empty_result["http_status"] < 300
                    and 200 <= sentinel_result["http_status"] < 300
                    and same_host(source_url, empty_result.get("final_url") or "")
                    and same_host(source_url, sentinel_result.get("final_url") or "")
                )

                same_sha = bool(
                    comparable
                    and empty_result.get("sha256")
                    and empty_result.get("sha256") == sentinel_result.get("sha256")
                )
                same_bytes = (
                    comparable
                    and empty_result.get("response_bytes") == sentinel_result.get("response_bytes")
                )

                if not comparable:
                    effectiveness = "UNRESOLVED"
                elif same_sha:
                    effectiveness = "NO_OBSERVABLE_QUERY_EFFECT"
                else:
                    effectiveness = "QUERY_EFFECT_OBSERVED"

                record = {
                    "source_url": source_url,
                    "endpoint_url": endpoint_url,
                    "method": method,
                    "search_param": search_param,
                    "empty_result": empty_result,
                    "sentinel_result": sentinel_result,
                    "same_sha256": same_sha,
                    "same_response_bytes": same_bytes,
                    "query_effectiveness": effectiveness,
                    "target_query_executed": False,
                    "sentinel_is_legal_evidence": False,
                    "document_candidate": False,
                    "verified_positive": False,
                    "runtime_registration_allowed": False,
                    "site_positive_allowed": False,
                    "site_negative_allowed": False,
                    "final_positive_promotion_allowed": False,
                }
                records.append(record)

                print(
                    f"{method} / {search_param}: "
                    f"empty={empty_result.get('response_bytes')} bytes, "
                    f"sentinel={sentinel_result.get('response_bytes')} bytes, "
                    f"same_sha={same_sha}, sentinel_echo={sentinel_result.get('sentinel_echo')}, "
                    f"effect={effectiveness}"
                )

    observed = [item for item in records if item.get("query_effectiveness") == "QUERY_EFFECT_OBSERVED"]
    no_effect = [item for item in records if item.get("query_effectiveness") == "NO_OBSERVABLE_QUERY_EFFECT"]
    unresolved = [item for item in records if item.get("query_effectiveness") == "UNRESOLVED"]

    if observed:
        resolution = "SAEOL_QUERY_EFFECTIVENESS_OBSERVED"
        next_action = (
            "query parameter가 response에 실제 영향을 주는 contract만 후속 bounded target execution 대상으로 유지한다. "
            "T-6-S4 결과와 결합해 candidate absence를 source-local negative search evidence로만 기록하되 SITE FALSE로 승격하지 않는다."
        )
    elif no_effect and not unresolved:
        resolution = "SAEOL_QUERY_CONTRACT_NO_OBSERVABLE_EFFECT"
        next_action = (
            "현재 keyword/keyword1 request shape는 response fingerprint를 변화시키지 않아 실제 검색 contract로 신뢰할 수 없다. "
            "T-6-S4의 0 candidate를 문서 부재 증거로 해석하지 않고 폐기하며, 다른 official archive/source family로 전환한다."
        )
    else:
        resolution = "SAEOL_QUERY_EFFECTIVENESS_UNRESOLVED"
        next_action = (
            "request 효과를 확정하지 못했다. T-6-S4의 0 candidate를 negative evidence로 사용하지 않고 UNKNOWN을 유지한다."
        )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-6-S4-S1 SAEOL Query Effectiveness Validation",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "input": {"path": str(INPUT_PATH), "resolution": data.get("resolution")},
        "method": {
            "target_query_execution": False,
            "empty_vs_sentinel_comparison": True,
            "bounded_requests": True,
            "response_fingerprint_comparison": True,
            "sentinel_as_evidence": False,
        },
        "summary": {
            "contract_count": len(contracts),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "query_effect_observed_count": len(observed),
            "no_observable_effect_count": len(no_effect),
            "unresolved_count": len(unresolved),
        },
        "records": records,
        "effective_request_contract_pool": observed,
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
    sentinel_evidence_leakage = sum(1 for item in records if item.get("sentinel_is_legal_evidence") is True)
    document_leakage = sum(1 for item in records if item.get("document_candidate") is True)
    non_go_leakage = sum(
        1 for item in records
        if not is_government_host(hostname(item.get("endpoint_url") or ""))
    )
    cross_host_leakage = sum(
        1 for item in records
        if not same_host(item.get("source_url") or "", item.get("endpoint_url") or "")
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
        "request shape contract loaded": len(contracts) > 0,
        "target query execution disabled": target_query_leakage == 0,
        "sentinel legal evidence disabled": sentinel_evidence_leakage == 0,
        "bounded request count respected": request_count <= MAX_TOTAL_REQUESTS,
        "endpoint go.kr leakage zero": non_go_leakage == 0,
        "endpoint cross-host leakage zero": cross_host_leakage == 0,
        "document candidate leakage zero": document_leakage == 0,
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

    print()
    print("=" * 60)
    print("SAEOL QUERY EFFECTIVENESS RESULT")
    print("=" * 60)
    print("Contract count:", len(contracts))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Query effect observed count:", len(observed))
    print("No observable effect count:", len(no_effect))
    print("Unresolved count:", len(unresolved))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)

    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Target query leakage:", target_query_leakage)
    print("Sentinel evidence leakage:", sentinel_evidence_leakage)
    print("Document candidate leakage:", document_leakage)
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
        raise AssertionError("UQQ700 SAEOL query effectiveness validation regression failed")


if __name__ == "__main__":
    main()
