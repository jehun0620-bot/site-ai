# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-9
Development Density Management Area
Current Canonical Query Effectiveness Validation

목표
======================================================================
T-8에서 복원한 current canonical source-local search contract가 실제로
검색 parameter 값에 반응하는지 확인한다.

이번 단계에서는 UQQ700 target query를 실행하지 않는다.
검색 field에 빈값과 법적 의미가 없는 sentinel 값을 각각 넣고 response
fingerprint를 비교한다.

원칙
======================================================================
1. 입력은 T-8 next_stage_search_contract_pool만 사용한다.
2. UQQ700 / 개발밀도관리구역 target query 전송 금지.
3. sentinel은 법적 의미 없는 고유 문자열만 사용한다.
4. live source 재조회로 현재 form contract를 다시 확인한다.
5. 실제 field/action/method/hidden params만 사용한다.
6. empty vs sentinel response fingerprint를 비교한다.
7. response 차이가 확인되면 QUERY_EFFECT_OBSERVED.
8. 동일하면 NO_OBSERVABLE_QUERY_EFFECT이며 SITE FALSE가 아니다.
9. sentinel 자체는 document/legal evidence가 아니다.
10. document candidate / verified positive / runtime registration / SITE TRUE/FALSE 금지.
"""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests


# ============================================================
# PATH / TARGET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_current_canonical_search_contract_recovery.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_current_canonical_query_effectiveness_validation.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

SENTINEL_QUERY = "ZZQX_CURRENT_CANONICAL_NO_MATCH_20260827"
TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 6
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

VOLATILE_QUERY_KEYS = {
    "token", "_csrf", "csrf", "sessionid", "jsessionid", "timestamp",
    "rand", "random", "_",
}
TRACKING_QUERY_KEYS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid",
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


def canonicalize_url(url: str) -> str:
    value = normalize_space(url).replace("&amp;", "&")
    if not value:
        return ""
    try:
        parsed = urlparse(value)
    except Exception:
        return ""
    if not parsed.hostname:
        return ""
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    items: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for key, val in parse_qsl(parsed.query, keep_blank_values=True):
        key = normalize_space(key)
        lowered = key.lower()
        if not key or lowered in VOLATILE_QUERY_KEYS or lowered in TRACKING_QUERY_KEYS or "csrf" in lowered or "session" in lowered:
            continue
        pair = (key, val)
        if pair not in seen:
            seen.add(pair)
            items.append(pair)
    items.sort(key=lambda item: (item[0].lower(), item[1]))
    return urlunparse((scheme, host, path, "", urlencode(items, doseq=True), ""))


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


def attrs_to_dict(attrs: List[Tuple[str, Optional[str]]]) -> Dict[str, str]:
    return {
        normalize_space(k).lower(): normalize_space(v)
        for k, v in attrs
        if normalize_space(k)
    }


# ============================================================
# LIVE FORM RECONFIRMATION
# ============================================================

class LiveFormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: List[Dict[str, Any]] = []
        self.current: Optional[Dict[str, Any]] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attr = attrs_to_dict(attrs)
        if tag == "form":
            if self.current is not None:
                self.forms.append(self.current)
            self.current = {
                "action_raw": attr.get("action", ""),
                "method": (attr.get("method", "GET") or "GET").upper(),
                "controls": [],
            }
            return
        if self.current is None:
            return
        if tag == "input":
            self.current["controls"].append({
                "tag": "input",
                "type": (attr.get("type", "text") or "text").lower(),
                "name": attr.get("name", ""),
                "id": attr.get("id", ""),
                "value": attr.get("value", ""),
            })
        elif tag == "select":
            self.current["controls"].append({
                "tag": "select",
                "type": "select",
                "name": attr.get("name", ""),
                "id": attr.get("id", ""),
                "value": "",
            })

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "form" and self.current is not None:
            self.forms.append(self.current)
            self.current = None

    def close(self) -> None:
        super().close()
        if self.current is not None:
            self.forms.append(self.current)
            self.current = None


def decode_bytes(response: requests.Response, payload: bytes) -> str:
    for encoding in unique_strings([response.encoding, "utf-8", "cp949", "euc-kr"]):
        try:
            return payload.decode(encoding)
        except Exception:
            continue
    return payload.decode("utf-8", errors="replace")


def fetch_html(session: requests.Session, url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "http_status": None,
        "final_url": "",
        "raw_html": "",
        "response_bytes": 0,
        "error": "",
    }
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            result["http_status"] = response.status_code
            result["final_url"] = canonicalize_url(str(response.url))
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
            result["raw_html"] = decode_bytes(response, payload)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def reconfirm_contract(
    session: requests.Session,
    contract: Dict[str, Any],
) -> Dict[str, Any]:
    source_url = canonicalize_url(contract.get("source_url") or "")
    expected_action = canonicalize_url(contract.get("action_url") or "")
    expected_method = normalize_space(contract.get("method")).upper()
    search_field = contract.get("search_field") or {}
    field_name = normalize_space(search_field.get("name") or search_field.get("id"))

    fetched = fetch_html(session, source_url)
    result: Dict[str, Any] = {
        "source_url": source_url,
        "expected_action_url": expected_action,
        "expected_method": expected_method,
        "field_name": field_name,
        "http_status": fetched.get("http_status"),
        "reconfirmed": False,
        "action_url": "",
        "method": "",
        "hidden_params": {},
        "reasons": [],
        "error": fetched.get("error") or "",
    }

    status = fetched.get("http_status")
    if fetched.get("error") or not isinstance(status, int) or not (200 <= status < 300):
        result["reasons"] = ["SOURCE_REQUERY_FAILED"]
        return result

    parser = LiveFormParser()
    parser.feed(str(fetched.get("raw_html") or ""))
    parser.close()

    final_url = fetched.get("final_url") or source_url
    for form in parser.forms:
        action = canonicalize_url(urljoin(final_url, normalize_space(form.get("action_raw")) or final_url))
        method = normalize_space(form.get("method") or "GET").upper()
        controls = form.get("controls") or []
        names = {
            normalize_space(control.get("name") or control.get("id"))
            for control in controls
            if normalize_space(control.get("name") or control.get("id"))
        }
        if action != expected_action or method != expected_method or field_name not in names:
            continue

        hidden: Dict[str, str] = {}
        for control in controls:
            if normalize_space(control.get("type")).lower() != "hidden":
                continue
            name = normalize_space(control.get("name"))
            if name:
                hidden[name] = normalize_space(control.get("value"))

        result["reconfirmed"] = True
        result["action_url"] = action
        result["method"] = method
        result["hidden_params"] = hidden
        result["reasons"] = ["LIVE_FORM_CONTRACT_RECONFIRMED"]
        return result

    result["reasons"] = ["LIVE_FORM_CONTRACT_NOT_RECONFIRMED"]
    return result


# ============================================================
# EFFECTIVENESS EXECUTION
# ============================================================

def execute_query(
    session: requests.Session,
    *,
    method: str,
    action_url: str,
    base_params: Dict[str, str],
    field_name: str,
    field_value: str,
) -> Dict[str, Any]:
    params = dict(base_params)
    params[field_name] = field_value
    result: Dict[str, Any] = {
        "value_kind": "EMPTY" if field_value == "" else "SENTINEL",
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
        elif method == "POST":
            kwargs["data"] = params
        else:
            raise ValueError(f"unsupported method: {method}")

        with session.request(method, action_url, **kwargs) as response:
            result["http_status"] = response.status_code
            result["final_url"] = canonicalize_url(str(response.url))
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


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("CURRENT CANONICAL QUERY EFFECTIVENESS VALIDATION")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Target query execution: DISABLED")
    print()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"T-8 input not found: {INPUT_PATH}")
    data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("T-8 input must be JSON object")

    contracts = data.get("next_stage_search_contract_pool")
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
    refresh_failure_count = 0
    records: List[Dict[str, Any]] = []

    for index, contract in enumerate(contracts, start=1):
        print("-" * 60)
        print(f"CONTRACT {index}")
        print("Family:", contract.get("source_family"))
        print("Source URL:", contract.get("source_url"))
        print("Action URL:", contract.get("action_url"))
        print("Method:", contract.get("method"))
        print("Field:", (contract.get("search_field") or {}).get("name"))

        if request_count + 3 > MAX_TOTAL_REQUESTS:
            break

        refresh = reconfirm_contract(session, contract)
        request_count += 1
        if isinstance(refresh.get("http_status"), int) and 200 <= refresh["http_status"] < 300:
            http_success_count += 1

        if not refresh.get("reconfirmed"):
            refresh_failure_count += 1
            records.append({
                "source_family": contract.get("source_family"),
                "source_url": contract.get("source_url"),
                "action_url": contract.get("action_url"),
                "method": contract.get("method"),
                "search_field": contract.get("search_field") or {},
                "refresh": refresh,
                "query_effectiveness": "UNRESOLVED",
                "target_query_executed": False,
                "sentinel_is_legal_evidence": False,
                "document_candidate": False,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            })
            print("Refresh:", "FAILED")
            continue

        field_name = refresh["field_name"]
        method = refresh["method"]
        action_url = refresh["action_url"]
        base_params = dict(refresh.get("hidden_params") or {})

        empty_result = execute_query(
            session,
            method=method,
            action_url=action_url,
            base_params=base_params,
            field_name=field_name,
            field_value="",
        )
        sentinel_result = execute_query(
            session,
            method=method,
            action_url=action_url,
            base_params=base_params,
            field_name=field_name,
            field_value=SENTINEL_QUERY,
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
            and same_host(contract.get("source_url") or "", empty_result.get("final_url") or "")
            and same_host(contract.get("source_url") or "", sentinel_result.get("final_url") or "")
        )
        same_sha = bool(
            comparable
            and empty_result.get("sha256")
            and empty_result.get("sha256") == sentinel_result.get("sha256")
        )
        same_bytes = bool(
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
            "source_family": contract.get("source_family"),
            "regions": contract.get("regions") or [],
            "source_url": contract.get("source_url"),
            "action_url": action_url,
            "method": method,
            "search_field": contract.get("search_field") or {},
            "field_name": field_name,
            "base_params": base_params,
            "refresh": refresh,
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

        print("Refresh:", "LIVE_FORM_CONTRACT_RECONFIRMED")
        print(
            "Effectiveness:", effectiveness,
            f"empty={empty_result.get('response_bytes')} bytes",
            f"sentinel={sentinel_result.get('response_bytes')} bytes",
            f"same_sha={same_sha}",
            f"sentinel_echo={sentinel_result.get('sentinel_echo')}",
        )

    observed = [item for item in records if item.get("query_effectiveness") == "QUERY_EFFECT_OBSERVED"]
    no_effect = [item for item in records if item.get("query_effectiveness") == "NO_OBSERVABLE_QUERY_EFFECT"]
    unresolved = [item for item in records if item.get("query_effectiveness") == "UNRESOLVED"]

    effective_pool = [
        {
            "source_family": item.get("source_family"),
            "regions": item.get("regions") or [],
            "source_url": item.get("source_url"),
            "action_url": item.get("action_url"),
            "method": item.get("method"),
            "search_field": item.get("search_field") or {},
            "field_name": item.get("field_name"),
            "base_params": item.get("base_params") or {},
            "query_effectiveness": item.get("query_effectiveness"),
            "requires_live_contract_reconfirmation": True,
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in observed
    ]

    if observed:
        resolution = "CURRENT_CANONICAL_QUERY_EFFECTIVENESS_OBSERVED"
        next_action = (
            "response에 실제 query effect가 확인된 current canonical contract만 T-10 bounded exact UQQ700 query execution으로 넘긴다. "
            "T-10에서도 query 문자열 자체는 candidate evidence로 사용하지 않고 result-local document identity만 평가한다."
        )
    elif no_effect and not unresolved:
        resolution = "CURRENT_CANONICAL_QUERY_CONTRACT_NO_OBSERVABLE_EFFECT"
        next_action = (
            "현재 복원된 current canonical contract는 sentinel에 대한 observable response effect가 없다. "
            "문서 부재 또는 SITE FALSE로 해석하지 않고 UNKNOWN을 유지하며 다른 source-specific request contract를 분석한다."
        )
    else:
        resolution = "CURRENT_CANONICAL_QUERY_EFFECTIVENESS_UNRESOLVED"
        next_action = (
            "query effect를 확정하지 못했다. negative evidence로 사용하지 않고 UNKNOWN을 유지한다."
        )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-9 Current Canonical Query Effectiveness Validation",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "input": {"path": str(INPUT_PATH), "resolution": data.get("resolution")},
        "method": {
            "live_contract_reconfirmation": True,
            "fresh_hidden_parameter_recovery": True,
            "target_query_execution": False,
            "empty_vs_sentinel_comparison": True,
            "response_fingerprint_comparison": True,
            "sentinel_as_legal_evidence": False,
            "bounded_requests": True,
        },
        "summary": {
            "contract_count": len(contracts),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "contract_refresh_failure_count": refresh_failure_count,
            "query_effect_observed_count": len(observed),
            "no_observable_effect_count": len(no_effect),
            "unresolved_count": len(unresolved),
            "next_stage_effective_contract_pool_count": len(effective_pool),
        },
        "records": records,
        "effective_search_contract_pool": effective_pool,
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
    non_go_leakage = sum(1 for item in records if not is_government_host(hostname(item.get("action_url") or "")))
    cross_host_leakage = sum(1 for item in records if not same_host(item.get("source_url") or "", item.get("action_url") or ""))
    verified_leakage = sum(1 for item in records if item.get("verified_positive") is True)
    runtime_leakage = sum(1 for item in records if item.get("runtime_registration_allowed") is True)
    site_true_leakage = sum(1 for item in records if item.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for item in records if item.get("site_negative_allowed") is True)
    effective_safety_leakage = sum(
        1 for item in effective_pool
        if item.get("verified_positive") is True
        or item.get("runtime_registration_allowed") is True
        or item.get("site_positive_allowed") is True
        or item.get("site_negative_allowed") is True
        or item.get("final_positive_promotion_allowed") is True
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-8 input exists": INPUT_PATH.exists(),
        "T-8 input parsed": isinstance(data, dict),
        "recovered search contract loaded": len(contracts) > 0,
        "live contract reconfirmation enabled": True,
        "fresh hidden parameter recovery enabled": True,
        "target query execution disabled": target_query_leakage == 0,
        "sentinel legal evidence disabled": sentinel_evidence_leakage == 0,
        "bounded request count respected": request_count <= MAX_TOTAL_REQUESTS,
        "action go.kr leakage zero": non_go_leakage == 0,
        "action cross-host leakage zero": cross_host_leakage == 0,
        "document candidate leakage zero": document_leakage == 0,
        "verified positive leakage zero": verified_leakage == 0,
        "runtime registration leakage zero": runtime_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "next-stage effective pool safety leakage zero": effective_safety_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("CURRENT CANONICAL QUERY EFFECTIVENESS RESULT")
    print("=" * 60)
    print("Contract count:", len(contracts))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Contract refresh failure count:", refresh_failure_count)
    print("Query effect observed count:", len(observed))
    print("No observable effect count:", len(no_effect))
    print("Unresolved count:", len(unresolved))
    print("Next-stage effective contract pool count:", len(effective_pool))
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
    print("Sentinel evidence leakage:", sentinel_evidence_leakage)
    print("Document candidate leakage:", document_leakage)
    print("Non-go.kr action leakage:", non_go_leakage)
    print("Cross-host action leakage:", cross_host_leakage)
    print("Verified positive leakage:", verified_leakage)
    print("Runtime registration leakage:", runtime_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print("Next-stage effective pool safety leakage:", effective_safety_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")
    if not all_pass:
        print("\nFAILED:")
        for name, passed in validations.items():
            if not passed:
                print("-", name)
        raise AssertionError("UQQ700 current canonical query effectiveness regression failed")


if __name__ == "__main__":
    main()
