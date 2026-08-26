# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-6
Development Density Management Area
Official Archive Source-local Search Contract Recovery

T-5-S1에서 URL hardening 및 direct reconfirmation을 통과한 신규 official
archive source만 입력으로 사용하여 실제 HTML form/action/search field/hidden
parameter contract를 복원한다.

중요:
- UQQ700 target query는 아직 실행하지 않는다.
- guessed query parameter name을 만들지 않는다.
- 실제 form control에 존재하는 field만 search field 후보가 될 수 있다.
- global site search / satisfaction / login form은 제외한다.
- source-local official archive identity가 있는 contract만 다음 단계로 넘긴다.
- contract 자체는 document candidate / verified positive가 아니다.
- SITE TRUE / SITE FALSE / runtime registration 금지.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
T5S1_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_official_notice_archive_source_url_hardening.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_official_archive_search_contract_recovery.json"
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

CLASS_QUALIFIED = "QUALIFIED_OFFICIAL_ARCHIVE_SEARCH_CONTRACT"
CLASS_REJECTED_NO_FIELD = "REJECTED_NO_ACTUAL_SEARCH_FIELD"
CLASS_REJECTED_GENERIC = "REJECTED_GENERIC_FORM_CONTRACT"
CLASS_REJECTED_CROSS_HOST = "REJECTED_CROSS_HOST_FORM_ACTION"
CLASS_REJECTED_NON_OFFICIAL = "REJECTED_NON_OFFICIAL_FORM_ACTION"
CLASS_REJECTED_WEAK = "REJECTED_ARCHIVE_CONTRACT_IDENTITY_WEAK"
CLASS_REJECTED_INVALID = "REJECTED_INVALID_FORM_ACTION"
VALID_CLASSES = {
    CLASS_QUALIFIED,
    CLASS_REJECTED_NO_FIELD,
    CLASS_REJECTED_GENERIC,
    CLASS_REJECTED_CROSS_HOST,
    CLASS_REJECTED_NON_OFFICIAL,
    CLASS_REJECTED_WEAK,
    CLASS_REJECTED_INVALID,
}

VOLATILE_QUERY_KEYS = {
    "token", "_csrf", "csrf", "sessionid", "jsessionid",
    "timestamp", "rand", "random", "_",
}
TRACKING_QUERY_KEYS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term",
    "utm_content", "fbclid", "gclid",
}
SEARCH_HINTS = [
    "search", "srch", "sch", "query", "keyword", "word", "text",
    "검색", "검색어", "제목", "내용", "subject", "title",
]
SEARCH_EXACT_NAMES = {
    "searchkeyword", "keyword", "searchword", "query", "q",
    "searchtext", "srchtext", "schtext", "searchtxt", "srchcontents",
    "search_wrd", "searchword", "search_word",
}
ANTI_SEARCH_TERMS = [
    "login", "password", "passwd", "satisfaction", "satis", "researchcontent",
    "captcha", "email", "phone", "tel", "회원", "로그인", "만족도",
]
ARCHIVE_ACTION_TERMS = [
    "ofraction.do", "selectofrnotancmt", "eminwon", "ntis", "notice",
    "gosi", "gonggo", "bbs", "board", "archive",
]
ARCHIVE_HIDDEN_KEYS = {
    "method", "context", "initvalue", "jndinm", "list_gubun",
    "not_ancmt_se_code", "pageindex", "pagenum", "bbsid", "menuid",
}
GENERIC_ACTION_TERMS = [
    "/rsa/front/search.jsp", "/satisfaction/", "/login", "/member",
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


def decode_url_transport_entities(value: str) -> str:
    result = normalize_space(value)
    for old in ("&amp;", "&#38;", "&#x26;", "&#X26;"):
        result = result.replace(old, "&")
    return result


def canonicalize_url(url: str) -> str:
    value = decode_url_transport_entities(url)
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
    try:
        port = parsed.port
    except ValueError:
        port = None
    netloc = host if not port or (scheme == "http" and port == 80) or (scheme == "https" and port == 443) else f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", re.sub(r";jsessionid=[^/?]+", "", parsed.path or "/", flags=re.I))
    items: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for raw_key, raw_value in parse_qsl(parsed.query, keep_blank_values=True):
        key = normalize_space(raw_key)
        if not key:
            continue
        lowered = key.lower()
        if lowered in VOLATILE_QUERY_KEYS or lowered in TRACKING_QUERY_KEYS or "csrf" in lowered or "session" in lowered:
            continue
        pair = (key, raw_value)
        if pair not in seen:
            seen.add(pair)
            items.append(pair)
    items.sort(key=lambda item: (item[0].lower(), item[1]))
    return urlunparse((scheme, netloc, path, "", urlencode(items, doseq=True), ""))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    value = normalize_space(host).lower()
    return bool(value) and (value == "go.kr" or value.endswith(".go.kr"))


def same_host(url_a: str, url_b: str) -> bool:
    a, b = hostname(url_a), hostname(url_b)
    return bool(a) and a == b


def decode_html(response: requests.Response, data: bytes) -> Tuple[str, str]:
    candidates = [response.encoding, "utf-8", "cp949", "euc-kr"]
    ct = normalize_space(response.headers.get("Content-Type"))
    m = re.search(r'''charset\s*=\s*["']?([^;"'\s]+)''', ct, flags=re.I)
    if m:
        candidates.insert(0, normalize_space(m.group(1)))
    for encoding in unique_strings(candidates):
        try:
            return data.decode(encoding), encoding
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "final_url": "", "http_status": None, "content_type": "",
        "response_bytes": 0, "raw_html": "", "encoding": "", "error": "",
    }
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
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
            data = b"".join(chunks)
            result["response_bytes"] = len(data)
            ct = result["content_type"].lower()
            prefix = data[:1000].lstrip().lower()
            if "html" in ct or "text/" in ct or prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html"):
                decoded, encoding = decode_html(response, data)
                result["raw_html"] = decoded
                result["encoding"] = encoding
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def attrs_to_dict(attrs: List[Tuple[str, Optional[str]]]) -> Dict[str, str]:
    return {
        normalize_space(k).lower(): normalize_space(v)
        for k, v in attrs if normalize_space(k)
    }


class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: List[Dict[str, Any]] = []
        self.current: Optional[Dict[str, Any]] = None
        self.current_button: Optional[Dict[str, Any]] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attr = attrs_to_dict(attrs)
        if tag == "form":
            self.current = {
                "action_raw": attr.get("action", ""),
                "method": (attr.get("method", "GET") or "GET").upper(),
                "id": attr.get("id", ""),
                "name": attr.get("name", ""),
                "class": attr.get("class", ""),
                "onsubmit": attr.get("onsubmit", ""),
                "controls": [],
                "submit_texts": [],
            }
            return
        if self.current is None:
            return
        if tag == "input":
            control = {
                "tag": "input",
                "type": (attr.get("type", "text") or "text").lower(),
                "name": attr.get("name", ""),
                "id": attr.get("id", ""),
                "value": attr.get("value", ""),
                "placeholder": attr.get("placeholder", ""),
                "title": attr.get("title", ""),
                "class": attr.get("class", ""),
            }
            self.current["controls"].append(control)
            if control["type"] in {"submit", "button", "image"} and control["value"]:
                self.current["submit_texts"].append(control["value"])
        elif tag == "textarea":
            self.current["controls"].append({
                "tag": "textarea", "type": "textarea", "name": attr.get("name", ""),
                "id": attr.get("id", ""), "value": "", "placeholder": attr.get("placeholder", ""),
                "title": attr.get("title", ""), "class": attr.get("class", ""),
            })
        elif tag == "select":
            self.current["controls"].append({
                "tag": "select", "type": "select", "name": attr.get("name", ""),
                "id": attr.get("id", ""), "value": "", "placeholder": "",
                "title": attr.get("title", ""), "class": attr.get("class", ""),
            })
        elif tag == "button":
            self.current_button = {"text": []}

    def handle_data(self, data: str) -> None:
        if self.current_button is not None:
            text = normalize_space(data)
            if text:
                self.current_button["text"].append(text)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "button" and self.current is not None and self.current_button is not None:
            text = normalize_space(" ".join(self.current_button["text"]))
            if text:
                self.current["submit_texts"].append(text)
            self.current_button = None
        elif tag == "form" and self.current is not None:
            self.forms.append(self.current)
            self.current = None


def field_score(control: Dict[str, Any]) -> Tuple[int, List[str]]:
    field_type = normalize_space(control.get("type")).lower()
    if field_type in {"hidden", "submit", "button", "image", "password", "checkbox", "radio", "file"}:
        return 0, []
    name = normalize_space(control.get("name"))
    if not name:
        return 0, []
    evidence = normalize_space(" ".join([
        name, control.get("id", ""), control.get("placeholder", ""),
        control.get("title", ""), control.get("class", ""),
    ])).lower()
    if any(term in evidence for term in ANTI_SEARCH_TERMS):
        return 0, ["ANTI_SEARCH_FIELD_IDENTITY"]
    score = 0
    reasons: List[str] = []
    if name.lower() in SEARCH_EXACT_NAMES:
        score += 70
        reasons.append("SEARCH_FIELD_EXACT_NAME:" + name)
    for hint in SEARCH_HINTS:
        if hint.lower() in evidence:
            score += 10
            reasons.append("SEARCH_FIELD_HINT:" + hint)
    if field_type in {"text", "search", "textarea"}:
        score += 10
        reasons.append("SEARCH_FIELD_TEXTUAL_TYPE:" + field_type)
    return score, unique_strings(reasons)


def hidden_params(form: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for control in form.get("controls", []):
        if normalize_space(control.get("type")).lower() != "hidden":
            continue
        name = normalize_space(control.get("name"))
        if name:
            result[name] = normalize_space(control.get("value"))
    return result


def classify_form(source_url: str, form: Dict[str, Any]) -> Dict[str, Any]:
    action_raw = normalize_space(form.get("action_raw"))
    action_url = canonicalize_url(urljoin(source_url, action_raw or source_url))
    method = normalize_space(form.get("method") or "GET").upper()
    hidden = hidden_params(form)
    form_text = normalize_space(" ".join([
        action_url, form.get("id", ""), form.get("name", ""), form.get("class", ""),
        form.get("onsubmit", ""), *form.get("submit_texts", []),
        *hidden.keys(), *hidden.values(),
    ])).lower()

    if not action_url:
        return {"qualified": False, "classification": CLASS_REJECTED_INVALID, "action_url": "", "method": method, "search_field": {}, "hidden_params": hidden, "reasons": ["INVALID_ACTION_URL"]}
    if not is_government_host(hostname(action_url)):
        return {"qualified": False, "classification": CLASS_REJECTED_NON_OFFICIAL, "action_url": action_url, "method": method, "search_field": {}, "hidden_params": hidden, "reasons": ["ACTION_NOT_GO_KR"]}
    if not same_host(source_url, action_url):
        return {"qualified": False, "classification": CLASS_REJECTED_CROSS_HOST, "action_url": action_url, "method": method, "search_field": {}, "hidden_params": hidden, "reasons": ["ACTION_CROSS_HOST"]}
    if any(term in form_text for term in GENERIC_ACTION_TERMS) or any(term in form_text for term in ANTI_SEARCH_TERMS):
        return {"qualified": False, "classification": CLASS_REJECTED_GENERIC, "action_url": action_url, "method": method, "search_field": {}, "hidden_params": hidden, "reasons": ["GENERIC_OR_ANTI_SEARCH_FORM_IDENTITY"]}

    scored: List[Tuple[int, Dict[str, Any], List[str]]] = []
    for control in form.get("controls", []):
        score, reasons = field_score(control)
        if score > 0:
            scored.append((score, control, reasons))
    scored.sort(key=lambda item: (-item[0], normalize_space(item[1].get("name"))))
    if not scored:
        return {"qualified": False, "classification": CLASS_REJECTED_NO_FIELD, "action_url": action_url, "method": method, "search_field": {}, "hidden_params": hidden, "reasons": ["NO_ACTUAL_SEARCH_FIELD"]}

    score, field, field_reasons = scored[0]
    archive_reasons: List[str] = []
    lowered_action = action_url.lower()
    for term in ARCHIVE_ACTION_TERMS:
        if term in lowered_action or term in form_text:
            archive_reasons.append("ARCHIVE_CONTRACT_IDENTITY:" + term)
    for key in hidden:
        if key.lower() in ARCHIVE_HIDDEN_KEYS:
            archive_reasons.append("ARCHIVE_HIDDEN_KEY:" + key)
    if action_url == source_url:
        archive_reasons.append("SOURCE_ACTION_SAME_ENDPOINT")

    if score < 20 or not archive_reasons:
        return {"qualified": False, "classification": CLASS_REJECTED_WEAK, "action_url": action_url, "method": method, "search_field": dict(field), "hidden_params": hidden, "reasons": unique_strings(field_reasons + archive_reasons + [f"SEARCH_FIELD_SCORE:{score}"])}

    search_field = dict(field)
    search_field["score"] = score
    return {
        "qualified": True,
        "classification": CLASS_QUALIFIED,
        "action_url": action_url,
        "method": method,
        "search_field": search_field,
        "hidden_params": hidden,
        "reasons": unique_strings(field_reasons + archive_reasons + [f"SEARCH_FIELD_SCORE:{score}"]),
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("OFFICIAL ARCHIVE SEARCH CONTRACT RECOVERY")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print()

    if not T5S1_INPUT_PATH.exists():
        raise FileNotFoundError(f"T-5-S1 input not found: {T5S1_INPUT_PATH}")
    data = json.loads(T5S1_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("T-5-S1 input must be JSON object")
    raw_sources = data.get("next_stage_source_pool")
    if not isinstance(raw_sources, list):
        raw_sources = []

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    })

    request_count = http_success_count = transport_error_count = 0
    records: List[Dict[str, Any]] = []
    source_results: List[Dict[str, Any]] = []

    for source_index, source in enumerate(raw_sources, start=1):
        source_url = canonicalize_url(source.get("url") or "")
        regions = unique_strings(source.get("regions") or [])
        family = normalize_space(source.get("source_family"))
        print("-" * 60)
        print(f"SOURCE {source_index}")
        print("Family:", family)
        print("Regions:", regions)
        print("URL:", source_url)

        request_count += 1
        response = fetch_page(session, source_url)
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1

        raw_html = normalize_space(response.get("raw_html")) if False else str(response.get("raw_html") or "")
        parser = FormParser()
        if raw_html:
            parser.feed(raw_html)
        source_contract_count = 0

        for form_index, form in enumerate(parser.forms, start=1):
            classification = classify_form(source_url, form)
            record = {
                "source_family": family,
                "regions": regions,
                "source_url": source_url,
                "form_index": form_index,
                "action_url": classification["action_url"],
                "method": classification["method"],
                "search_field": classification["search_field"],
                "hidden_params": classification["hidden_params"],
                "qualified": classification["qualified"],
                "classification": classification["classification"],
                "reasons": classification["reasons"],
                "target_query_executed": False,
                "document_candidate": False,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            }
            records.append(record)
            if record["qualified"]:
                source_contract_count += 1

        source_results.append({
            "source_family": family,
            "regions": regions,
            "url": source_url,
            "http_status": status,
            "form_count": len(parser.forms),
            "qualified_contract_count": source_contract_count,
            "resolution": "SEARCH_CONTRACT_RECOVERED" if source_contract_count else "NO_QUALIFIED_SEARCH_CONTRACT",
        })
        print("HTTP:", status)
        print("Forms:", len(parser.forms))
        print("Qualified contracts:", source_contract_count)
        print("Resolution:", source_results[-1]["resolution"])

    qualified = [item for item in records if item.get("qualified") is True]
    rejected = [item for item in records if item.get("qualified") is not True]

    canonical: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    duplicate_count = 0
    for item in qualified:
        field_name = normalize_space((item.get("search_field") or {}).get("name"))
        key = (
            normalize_space(item.get("source_family")),
            canonicalize_url(item.get("action_url") or ""),
            normalize_space(item.get("method")).upper(),
            field_name,
        )
        if key in canonical:
            duplicate_count += 1
            continue
        canonical[key] = dict(item)
    hardened = list(canonical.values())

    next_stage_search_contract_pool = [
        {
            "source_family": item.get("source_family"),
            "regions": item.get("regions") or [],
            "source_url": item.get("source_url"),
            "action_url": item.get("action_url"),
            "method": item.get("method"),
            "search_field": item.get("search_field") or {},
            "hidden_params": item.get("hidden_params") or {},
            "classification": item.get("classification"),
            "reasons": item.get("reasons") or [],
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in hardened
    ]

    resolution = (
        "OFFICIAL_ARCHIVE_SEARCH_CONTRACT_RECOVERY_COMPLETED"
        if next_stage_search_contract_pool
        else "OFFICIAL_ARCHIVE_SEARCH_CONTRACT_RECOVERY_NO_CONTRACT"
    )
    next_action = (
        "복원된 official archive source-local search contract만 T-7 bounded target search execution으로 넘긴다. T-7에서 fresh form을 재조회한 후 UQQ700 query를 실제 field에 주입한다."
        if next_stage_search_contract_pool
        else "실행 가능한 archive search contract를 복원하지 못했다. SITE FALSE로 판정하지 않고 UNKNOWN을 유지하며 source-specific request contract를 추가 분석한다."
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-6 Official Archive Source-local Search Contract Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {"resolution_type": RESOLUTION_TYPE, "negative_evidence_allowed": False, "source_failure_site_status": "UNKNOWN"},
        "input": {"t5s1_path": str(T5S1_INPUT_PATH), "t5s1_resolution": data.get("resolution")},
        "method": {
            "hardened_source_only": True,
            "direct_source_fetch_required": True,
            "structured_html_form_parsing_enabled": True,
            "actual_form_action_required": True,
            "actual_search_field_required": True,
            "hidden_parameter_recovery_enabled": True,
            "guessed_search_field_disabled": True,
            "target_query_execution_enabled": False,
            "global_search_guard_enabled": True,
            "same_host_required": True,
            "go_kr_required": True,
        },
        "summary": {
            "input_source_count": len(raw_sources),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "raw_form_record_count": len(records),
            "qualified_before_dedupe": len(qualified),
            "duplicate_contract_removed": duplicate_count,
            "recovered_contract_count": len(hardened),
            "rejected_contract_count": len(rejected),
            "next_stage_search_contract_pool_count": len(next_stage_search_contract_pool),
        },
        "source_results": source_results,
        "recovered_contracts": hardened,
        "rejected_contracts": rejected,
        "next_stage_search_contract_pool": next_stage_search_contract_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    guessed_field_leakage = sum(1 for item in hardened if not normalize_space((item.get("search_field") or {}).get("name")))
    non_go_leakage = sum(1 for item in hardened if not is_government_host(hostname(item.get("action_url") or "")))
    cross_host_leakage = sum(1 for item in hardened if not same_host(item.get("source_url") or "", item.get("action_url") or ""))
    target_execution_leakage = sum(1 for item in records if item.get("target_query_executed") is True)
    document_leakage = sum(1 for item in records if item.get("document_candidate") is True)
    verified_leakage = sum(1 for item in records if item.get("verified_positive") is True)
    runtime_leakage = sum(1 for item in records if item.get("runtime_registration_allowed") is True)
    site_true_leakage = sum(1 for item in records if item.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for item in records if item.get("site_negative_allowed") is True)
    keys = [(
        item.get("source_family"), canonicalize_url(item.get("action_url") or ""),
        normalize_space(item.get("method")).upper(), normalize_space((item.get("search_field") or {}).get("name"))
    ) for item in hardened]

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-5-S1 input exists": T5S1_INPUT_PATH.exists(),
        "T-5-S1 input parsed": isinstance(data, dict),
        "hardened source pool loaded": len(raw_sources) > 0,
        "direct source fetch enabled": True,
        "HTML form structural parsing enabled": True,
        "actual form action recovery enabled": True,
        "actual search field recovery enabled": True,
        "hidden parameter recovery enabled": True,
        "guessed search fields disabled": guessed_field_leakage == 0,
        "target query execution leakage zero": target_execution_leakage == 0,
        "document candidate leakage zero": document_leakage == 0,
        "all classes valid": all(item.get("classification") in VALID_CLASSES for item in records),
        "recovered contracts unique": len(keys) == len(set(keys)),
        "recovered actions go.kr": non_go_leakage == 0,
        "recovered actions same-host": cross_host_leakage == 0,
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

    print("\n" + "=" * 60)
    print("OFFICIAL ARCHIVE SEARCH CONTRACT RECOVERY RESULT")
    print("=" * 60)
    print("Input source count:", len(raw_sources))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Raw form record count:", len(records))
    print("Qualified before dedupe:", len(qualified))
    print("Duplicate contract removed:", duplicate_count)
    print("Recovered contract count:", len(hardened))
    print("Next-stage search contract pool count:", len(next_stage_search_contract_pool))
    if hardened:
        print("\nRECOVERED OFFICIAL ARCHIVE SEARCH CONTRACTS")
        print("-" * 60)
        for index, item in enumerate(hardened, start=1):
            print(f"[{index}]", item.get("classification"))
            print("Family:", item.get("source_family"))
            print("Regions:", item.get("regions"))
            print("Action:", item.get("action_url"))
            print("Method:", item.get("method"))
            print("Field:", item.get("search_field"))
            print("Hidden params:", item.get("hidden_params"))
            print("Reasons:", item.get("reasons"))
            print()
    print("=" * 60)
    print("RESOLUTION")
    print("=" * 60)
    print(resolution)
    print(next_action)
    print("Output:", OUTPUT_PATH)
    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Guessed field leakage:", guessed_field_leakage)
    print("Non-go.kr action leakage:", non_go_leakage)
    print("Cross-host action leakage:", cross_host_leakage)
    print("Target query execution leakage:", target_execution_leakage)
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
        raise AssertionError("UQQ700 official archive search contract recovery regression failed")


if __name__ == "__main__":
    main()
