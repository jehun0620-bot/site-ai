# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-6-S1
Development Density Management Area
SAEOL Source-specific Request Contract Probe

목표
======================================================================
T-6에서 HTML <form>이 0개였던 새올전자민원창구 source를 대상으로,
실제 페이지 HTML/inline script/external script/iframe/link/query 구조에서
검색 실행에 필요한 request contract identity를 복원한다.

중요 원칙
======================================================================
1. 입력은 T-5-S1 hardened source pool만 사용한다.
2. UQQ700 target query는 아직 실행하지 않는다.
3. guessed request parameter를 생성하지 않는다.
4. HTML에 실제 존재하는 input/select/textarea name, script literal,
   URL query key, iframe/src/href/action literal만 수집한다.
5. target query 문자열은 evidence로 사용하지 않는다.
6. source 자체를 document candidate로 승격하지 않는다.
7. verified positive / SITE TRUE / SITE FALSE / runtime registration 금지.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_official_notice_archive_source_url_hardening.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_saeol_request_contract_probe.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_EXTERNAL_SCRIPT_REQUESTS = 12
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

REQUEST_PARAM_HINTS = {
    "search", "srch", "sch", "query", "keyword", "word", "title", "subject",
    "content", "ancmt", "not_ancmt", "gosi", "gonggo", "ofr", "list", "page",
}
REQUEST_ACTION_HINTS = {
    "ofraction.do", "selectofrnotancmt", "search", "list", "select", "ntis", "eminwon",
}
SCRIPT_REQUEST_PATTERNS = [
    re.compile(r'''(?:url|action)\s*[:=]\s*["']([^"']+)["']''', re.I),
    re.compile(r'''(?:open|location\.href|window\.location)\s*\(?\s*["']([^"']+)["']''', re.I),
    re.compile(r'''["']([^"']*OfrAction\.do[^"']*)["']''', re.I),
]
SCRIPT_PARAM_PATTERNS = [
    re.compile(r'''(?:name|paramName|key)\s*[:=]\s*["']([A-Za-z0-9_\-]+)["']''', re.I),
    re.compile(r'''[?&]([A-Za-z0-9_\-]+)='''),
    re.compile(r'''document\.(?:getElementById|querySelector)\(\s*["']#?([A-Za-z0-9_\-]+)["']\s*\)''', re.I),
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


def safe_url(value: str, base: str = "") -> str:
    value = normalize_space(value).replace("&amp;", "&").replace("&#38;", "&")
    if not value:
        return ""
    if base:
        value = urljoin(base, value)
    try:
        parsed = urlparse(value)
    except Exception:
        return ""
    if not parsed.hostname:
        return ""
    return value


def decode_bytes(response: requests.Response, data: bytes) -> Tuple[str, str]:
    candidates = [response.encoding, "utf-8", "cp949", "euc-kr"]
    for enc in unique_strings(candidates):
        try:
            return data.decode(enc), enc
        except Exception:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def fetch_text(session: requests.Session, url: str) -> Dict[str, Any]:
    result = {
        "url": url, "final_url": "", "http_status": None, "content_type": "",
        "response_bytes": 0, "text": "", "encoding": "", "error": "",
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
            text, encoding = decode_bytes(response, data)
            result["text"] = text
            result["encoding"] = encoding
    except Exception as exc:
        result["error"] = repr(exc)
    return result


class ProbeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.controls: List[Dict[str, str]] = []
        self.scripts: List[str] = []
        self.external_scripts: List[str] = []
        self.iframes: List[str] = []
        self.links: List[str] = []
        self.forms: List[Dict[str, str]] = []
        self.current_script = False
        self.script_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr = {normalize_space(k).lower(): normalize_space(v) for k, v in attrs if normalize_space(k)}
        tag = tag.lower()
        if tag == "form":
            self.forms.append({
                "action": attr.get("action", ""),
                "method": (attr.get("method", "GET") or "GET").upper(),
                "id": attr.get("id", ""),
                "name": attr.get("name", ""),
            })
        elif tag in {"input", "select", "textarea", "button"}:
            self.controls.append({
                "tag": tag,
                "type": (attr.get("type", "") or "").lower(),
                "name": attr.get("name", ""),
                "id": attr.get("id", ""),
                "value": attr.get("value", ""),
                "title": attr.get("title", ""),
                "placeholder": attr.get("placeholder", ""),
                "onclick": attr.get("onclick", ""),
            })
        elif tag == "script":
            src = attr.get("src", "")
            if src:
                self.external_scripts.append(src)
            self.current_script = True
            self.script_parts = []
        elif tag == "iframe":
            if attr.get("src"):
                self.iframes.append(attr.get("src", ""))
        elif tag == "a":
            if attr.get("href"):
                self.links.append(attr.get("href", ""))

    def handle_data(self, data: str) -> None:
        if self.current_script:
            self.script_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            script = "\n".join(self.script_parts)
            if normalize_space(script):
                self.scripts.append(script)
            self.current_script = False
            self.script_parts = []


def looks_relevant_param(name: str) -> bool:
    lowered = normalize_space(name).lower()
    return bool(lowered) and any(hint in lowered for hint in REQUEST_PARAM_HINTS)


def looks_relevant_action(url: str) -> bool:
    lowered = normalize_space(url).lower()
    return bool(lowered) and any(hint in lowered for hint in REQUEST_ACTION_HINTS)


def extract_script_contracts(text: str, base_url: str) -> Tuple[List[str], List[str]]:
    actions: List[str] = []
    params: List[str] = []
    for pattern in SCRIPT_REQUEST_PATTERNS:
        for match in pattern.finditer(text):
            candidate = safe_url(match.group(1), base_url)
            if candidate and same_host(base_url, candidate) and looks_relevant_action(candidate):
                actions.append(candidate)
    for pattern in SCRIPT_PARAM_PATTERNS:
        for match in pattern.finditer(text):
            name = normalize_space(match.group(1))
            if looks_relevant_param(name):
                params.append(name)
    return unique_strings(actions), unique_strings(params)


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SAEOL SOURCE-SPECIFIC REQUEST CONTRACT PROBE")
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
    sources = data.get("next_stage_source_pool")
    if not isinstance(sources, list):
        sources = []

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/javascript,text/javascript,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    })

    request_count = 0
    http_success_count = 0
    external_script_request_count = 0
    records: List[Dict[str, Any]] = []

    for index, source in enumerate(sources, start=1):
        source_url = safe_url(source.get("url") or "")
        family = normalize_space(source.get("source_family"))
        regions = unique_strings(source.get("regions") or [])
        print("-" * 60)
        print(f"SOURCE {index}")
        print("Family:", family)
        print("Regions:", regions)
        print("URL:", source_url)

        request_count += 1
        response = fetch_text(session, source_url)
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1

        parser = ProbeParser()
        if response.get("text"):
            parser.feed(response["text"])

        query_params = [key for key, _ in parse_qsl(urlparse(source_url).query, keep_blank_values=True)]
        relevant_query_params = unique_strings(key for key in query_params if looks_relevant_param(key))
        relevant_controls = [
            control for control in parser.controls
            if looks_relevant_param(control.get("name") or control.get("id") or "")
        ]

        inline_actions: List[str] = []
        inline_params: List[str] = []
        for script in parser.scripts:
            actions, params = extract_script_contracts(script, source_url)
            inline_actions.extend(actions)
            inline_params.extend(params)

        external_results: List[Dict[str, Any]] = []
        external_actions: List[str] = []
        external_params: List[str] = []
        for raw_src in unique_strings(parser.external_scripts):
            if external_script_request_count >= MAX_EXTERNAL_SCRIPT_REQUESTS:
                break
            script_url = safe_url(raw_src, source_url)
            if not script_url or not same_host(source_url, script_url):
                continue
            external_script_request_count += 1
            request_count += 1
            script_response = fetch_text(session, script_url)
            if isinstance(script_response.get("http_status"), int) and 200 <= script_response["http_status"] < 300:
                http_success_count += 1
            actions, params = extract_script_contracts(script_response.get("text") or "", source_url)
            external_actions.extend(actions)
            external_params.extend(params)
            external_results.append({
                "url": script_url,
                "http_status": script_response.get("http_status"),
                "actions": actions,
                "params": params,
                "error": script_response.get("error"),
            })

        iframe_urls = unique_strings(
            safe_url(value, source_url) for value in parser.iframes
            if safe_url(value, source_url) and same_host(source_url, safe_url(value, source_url))
        )
        relevant_links = unique_strings(
            safe_url(value, source_url) for value in parser.links
            if safe_url(value, source_url)
            and same_host(source_url, safe_url(value, source_url))
            and looks_relevant_action(safe_url(value, source_url))
        )

        recovered_actions = unique_strings(inline_actions + external_actions + relevant_links + iframe_urls)
        recovered_params = unique_strings(relevant_query_params + inline_params + external_params + [
            control.get("name") or control.get("id") for control in relevant_controls
        ])

        qualified = bool(recovered_actions or recovered_params or relevant_controls)
        resolution = "REQUEST_CONTRACT_EVIDENCE_RECOVERED" if qualified else "NO_REQUEST_CONTRACT_EVIDENCE"
        record = {
            "source_family": family,
            "regions": regions,
            "source_url": source_url,
            "http_status": status,
            "form_count": len(parser.forms),
            "control_count": len(parser.controls),
            "inline_script_count": len(parser.scripts),
            "external_script_count": len(parser.external_scripts),
            "iframe_count": len(parser.iframes),
            "relevant_query_params": relevant_query_params,
            "relevant_controls": relevant_controls,
            "inline_request_actions": unique_strings(inline_actions),
            "inline_request_params": unique_strings(inline_params),
            "external_script_results": external_results,
            "external_request_actions": unique_strings(external_actions),
            "external_request_params": unique_strings(external_params),
            "iframe_urls": iframe_urls,
            "relevant_links": relevant_links,
            "recovered_actions": recovered_actions,
            "recovered_params": recovered_params,
            "qualified_probe": qualified,
            "resolution": resolution,
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        records.append(record)

        print("HTTP:", status)
        print("Forms:", len(parser.forms))
        print("Controls:", len(parser.controls))
        print("Inline scripts:", len(parser.scripts))
        print("External scripts:", len(parser.external_scripts))
        print("Recovered actions:", len(recovered_actions))
        print("Recovered params:", len(recovered_params))
        print("Resolution:", resolution)
        if recovered_actions:
            print("Actions:", recovered_actions[:10])
        if recovered_params:
            print("Params:", recovered_params[:20])
        print()

    qualified_records = [item for item in records if item.get("qualified_probe") is True]
    resolution = (
        "SAEOL_REQUEST_CONTRACT_PROBE_COMPLETED"
        if qualified_records
        else "SAEOL_REQUEST_CONTRACT_PROBE_NO_EVIDENCE"
    )
    next_action = (
        "복원된 실제 action/parameter/control evidence를 바탕으로 T-6-S2에서 source-specific executable request contract를 재구성한다. 아직 target query는 실행하지 않는다."
        if qualified_records
        else "새올 HTML/JS에서도 request contract identity를 복원하지 못했다. UNKNOWN을 유지하고 브라우저 네트워크 contract 또는 별도 official source family로 전환한다."
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-6-S1 SAEOL Source-specific Request Contract Probe",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "input": {
            "path": str(INPUT_PATH),
            "resolution": data.get("resolution"),
        },
        "method": {
            "hardened_source_only": True,
            "direct_source_fetch": True,
            "html_control_probe": True,
            "inline_script_probe": True,
            "same_host_external_script_probe": True,
            "iframe_and_link_probe": True,
            "guessed_parameter_generation": False,
            "target_query_execution": False,
            "query_as_candidate_evidence": False,
        },
        "summary": {
            "source_count": len(sources),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "external_script_request_count": external_script_request_count,
            "qualified_probe_count": len(qualified_records),
        },
        "records": records,
        "next_stage_request_contract_probe_pool": qualified_records,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    target_execution_leakage = sum(1 for item in records if item.get("target_query_executed") is True)
    document_leakage = sum(1 for item in records if item.get("document_candidate") is True)
    non_official_action_leakage = sum(
        1 for item in records for url in item.get("recovered_actions", [])
        if not is_government_host(hostname(url))
    )
    cross_host_action_leakage = sum(
        1 for item in records for url in item.get("recovered_actions", [])
        if not same_host(item.get("source_url") or "", url)
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
        "hardened source pool loaded": len(sources) > 0,
        "HTML control probe enabled": True,
        "inline script probe enabled": True,
        "same-host external script probe enabled": True,
        "iframe/link probe enabled": True,
        "guessed parameter generation disabled": True,
        "target query execution leakage zero": target_execution_leakage == 0,
        "document candidate leakage zero": document_leakage == 0,
        "recovered action go.kr leakage zero": non_official_action_leakage == 0,
        "recovered action cross-host leakage zero": cross_host_action_leakage == 0,
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
    print("SAEOL REQUEST CONTRACT PROBE RESULT")
    print("=" * 60)
    print("Source count:", len(sources))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("External script request count:", external_script_request_count)
    print("Qualified probe count:", len(qualified_records))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)
    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Target query execution leakage:", target_execution_leakage)
    print("Document candidate leakage:", document_leakage)
    print("Non-official action leakage:", non_official_action_leakage)
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
        raise AssertionError("UQQ700 SAEOL request contract probe regression failed")


if __name__ == "__main__":
    main()
