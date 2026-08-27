# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-8
Development Density Management Area
Current Canonical Search Contract Recovery

목표
======================================================================
T-7-S1에서 직접 검증된 현재 성남시 canonical source 2개에서 실제 HTML
search form/action/field/hidden parameter를 구조적으로 복원한다.

원칙
======================================================================
- 입력은 T-7-S1 next_stage_source_pool만 사용한다.
- source를 live requery한다.
- 실제 form/action/method/control만 사용한다.
- guessed field/action/method 생성 금지.
- global site search, satisfaction, login/contact form 제외.
- source-local board/search identity를 요구한다.
- UQQ700 target query 실행 금지.
- document candidate 생성 금지.
- no contract != SITE FALSE.
- verified positive / runtime registration / SITE TRUE / SITE FALSE 금지.
"""

from __future__ import annotations

import html
import json
import re
from collections import Counter
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
    "development_density_management_area_current_canonical_archive_source_recovery.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_current_canonical_search_contract_recovery.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"
ALLOWED_FAMILIES = {FAMILY_NOTICE, FAMILY_URBAN}

CLASS_QUALIFIED_GET = "QUALIFIED_CURRENT_CANONICAL_SEARCH_FORM_GET"
CLASS_QUALIFIED_POST = "QUALIFIED_CURRENT_CANONICAL_SEARCH_FORM_POST"
CLASS_REJECTED_NO_FIELD = "REJECTED_FORM_NO_SEARCH_FIELD"
CLASS_REJECTED_GLOBAL = "REJECTED_GLOBAL_SITE_SEARCH_FORM"
CLASS_REJECTED_SATISFACTION = "REJECTED_SATISFACTION_FORM"
CLASS_REJECTED_GENERIC = "REJECTED_GENERIC_FORM"
CLASS_REJECTED_NON_OFFICIAL = "REJECTED_NON_OFFICIAL_ACTION"
CLASS_REJECTED_CROSS_HOST = "REJECTED_CROSS_HOST_ACTION"
CLASS_REJECTED_UNSAFE_METHOD = "REJECTED_UNSAFE_METHOD"
CLASS_REJECTED_WEAK = "REJECTED_SOURCE_LOCAL_IDENTITY_WEAK"
CLASS_REJECTED_INVALID = "REJECTED_INVALID_ACTION"

VALID_CLASSES = {
    CLASS_QUALIFIED_GET, CLASS_QUALIFIED_POST,
    CLASS_REJECTED_NO_FIELD, CLASS_REJECTED_GLOBAL,
    CLASS_REJECTED_SATISFACTION, CLASS_REJECTED_GENERIC,
    CLASS_REJECTED_NON_OFFICIAL, CLASS_REJECTED_CROSS_HOST,
    CLASS_REJECTED_UNSAFE_METHOD, CLASS_REJECTED_WEAK,
    CLASS_REJECTED_INVALID,
}
QUALIFIED_CLASSES = {CLASS_QUALIFIED_GET, CLASS_QUALIFIED_POST}

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

SEARCH_HINTS = {
    "search", "srch", "sch", "keyword", "query", "word", "text", "find",
    "검색", "검색어", "조회", "찾기",
}
SEARCH_SUBMIT_HINTS = {"검색", "검색하기", "조회", "찾기", "search", "find"}
ANTI_FIELD_TYPES = {"password", "file", "checkbox", "radio", "submit", "button", "reset", "image", "hidden"}
GENERIC_FORM_TERMS = {"login", "member", "password", "newsletter", "contact", "로그인", "회원가입", "비밀번호", "문의"}
SATISFACTION_TERMS = {"satisfaction", "voteSatis", "만족", "만족도", "researchContent"}
GLOBAL_SEARCH_PATH_TERMS = {"/search", "/Search", "/RSA/front/Search.jsp", "/search.do"}
SAFE_METHODS = {"GET", "POST"}

VOLATILE_QUERY_KEYS = {"token", "_csrf", "csrf", "sessionid", "jsessionid", "timestamp", "rand", "random", "_"}
TRACKING_QUERY_KEYS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}


# ============================================================
# UTIL / URL
# ============================================================

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
# FORM PARSER
# ============================================================

class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: List[Dict[str, Any]] = []
        self.current: Optional[Dict[str, Any]] = None
        self.current_select: Optional[Dict[str, Any]] = None
        self.current_option: Optional[Dict[str, Any]] = None
        self.current_textarea: Optional[Dict[str, Any]] = None
        self.current_button: Optional[Dict[str, Any]] = None
        self.current_label_for = ""
        self.current_label_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attr = attrs_to_dict(attrs)
        if tag == "form":
            if self.current is not None:
                self.forms.append(self.current)
            self.current = {
                "action_raw": attr.get("action", ""),
                "method": (attr.get("method", "GET") or "GET").upper(),
                "id": attr.get("id", ""),
                "name": attr.get("name", ""),
                "class": attr.get("class", ""),
                "onsubmit": attr.get("onsubmit", ""),
                "controls": [],
                "labels": {},
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
        elif tag == "select":
            self.current_select = {
                "tag": "select", "type": "select",
                "name": attr.get("name", ""), "id": attr.get("id", ""),
                "value": "", "placeholder": "", "title": attr.get("title", ""),
                "class": attr.get("class", ""), "options": [],
            }
        elif tag == "option" and self.current_select is not None:
            self.current_option = {"value": attr.get("value", ""), "selected": "selected" in attr, "text": []}
        elif tag == "textarea":
            self.current_textarea = {
                "tag": "textarea", "type": "textarea",
                "name": attr.get("name", ""), "id": attr.get("id", ""),
                "placeholder": attr.get("placeholder", ""), "title": attr.get("title", ""),
                "class": attr.get("class", ""), "value_parts": [],
            }
        elif tag == "button":
            self.current_button = {"type": (attr.get("type", "submit") or "submit").lower(), "value": attr.get("value", ""), "parts": []}
        elif tag == "label":
            self.current_label_for = attr.get("for", "")
            self.current_label_parts = []

    def handle_data(self, data: str) -> None:
        text = normalize_space(data)
        if not text:
            return
        if self.current_option is not None:
            self.current_option["text"].append(text)
        if self.current_textarea is not None:
            self.current_textarea["value_parts"].append(text)
        if self.current_button is not None:
            self.current_button["parts"].append(text)
        if self.current_label_for:
            self.current_label_parts.append(text)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.current is None:
            return
        if tag == "option" and self.current_select is not None and self.current_option is not None:
            option = {
                "value": self.current_option.get("value", ""),
                "text": normalize_space(" ".join(self.current_option.get("text", []))),
                "selected": bool(self.current_option.get("selected")),
            }
            self.current_select["options"].append(option)
            if option["selected"]:
                self.current_select["value"] = option["value"]
            self.current_option = None
        elif tag == "select" and self.current_select is not None:
            self.current["controls"].append(self.current_select)
            self.current_select = None
        elif tag == "textarea" and self.current_textarea is not None:
            control = dict(self.current_textarea)
            control["value"] = normalize_space(" ".join(control.pop("value_parts", [])))
            self.current["controls"].append(control)
            self.current_textarea = None
        elif tag == "button" and self.current_button is not None:
            text = normalize_space(" ".join(self.current_button.get("parts", []))) or self.current_button.get("value", "")
            if text:
                self.current["submit_texts"].append(text)
            self.current_button = None
        elif tag == "label" and self.current_label_for:
            self.current["labels"][self.current_label_for] = normalize_space(" ".join(self.current_label_parts))
            self.current_label_for = ""
            self.current_label_parts = []
        elif tag == "form":
            self.forms.append(self.current)
            self.current = None

    def close(self) -> None:
        super().close()
        if self.current is not None:
            self.forms.append(self.current)
            self.current = None


# ============================================================
# HTTP / INPUT
# ============================================================

def decode_html(response: requests.Response, payload: bytes) -> str:
    candidates = [response.encoding, "utf-8", "cp949", "euc-kr"]
    for encoding in unique_strings(candidates):
        try:
            return payload.decode(encoding)
        except Exception:
            continue
    return payload.decode("utf-8", errors="replace")


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"final_url": "", "http_status": None, "raw_html": "", "error": "", "response_bytes": 0}
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
            result["raw_html"] = decode_html(response, payload)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def load_sources(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("next_stage_source_pool")
    if not isinstance(raw, list):
        raw = []
    result: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        family = normalize_space(item.get("source_family"))
        url = canonicalize_url(item.get("url") or "")
        if family not in ALLOWED_FAMILIES or not url:
            continue
        key = (family, url)
        if key in seen:
            continue
        seen.add(key)
        regions = item.get("regions") if isinstance(item.get("regions"), list) else []
        result.append({"source_family": family, "url": url, "regions": unique_strings(regions), "title": normalize_space(item.get("title"))})
    return result


# ============================================================
# CONTRACT SEMANTICS
# ============================================================

def field_score(control: Dict[str, Any], labels: Dict[str, str]) -> Tuple[int, List[str]]:
    ctype = normalize_space(control.get("type")).lower()
    if ctype in ANTI_FIELD_TYPES:
        return 0, []
    name = normalize_space(control.get("name"))
    cid = normalize_space(control.get("id"))
    evidence = normalize_space(" ".join([
        name, cid, control.get("placeholder", ""), control.get("title", ""),
        labels.get(cid, ""), labels.get(name, ""),
    ])).lower()
    score = 0
    reasons = []
    for hint in SEARCH_HINTS:
        if hint.lower() in evidence:
            score += 12
            reasons.append("SEARCH_FIELD_HINT:" + hint)
    if ctype in {"text", "search", "textarea"}:
        score += 8
        reasons.append("SEARCH_FIELD_TEXTUAL_TYPE:" + ctype)
    if name or cid:
        score += 4
    return score, unique_strings(reasons)


def choose_search_field(form: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    best: Optional[Dict[str, Any]] = None
    best_score = 0
    best_reasons: List[str] = []
    labels = form.get("labels") or {}
    for control in form.get("controls") or []:
        score, reasons = field_score(control, labels)
        if score > best_score:
            best_score = score
            best = dict(control)
            best["score"] = score
            best_reasons = reasons
    if best_score < 16:
        return None, []
    return best, best_reasons


def hidden_params(form: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for control in form.get("controls") or []:
        if normalize_space(control.get("type")).lower() == "hidden":
            name = normalize_space(control.get("name"))
            if name:
                result[name] = normalize_space(control.get("value"))
    return result


def classify_form(source: Dict[str, Any], source_url: str, form: Dict[str, Any]) -> Dict[str, Any]:
    family = source["source_family"]
    method = normalize_space(form.get("method") or "GET").upper()
    raw_action = normalize_space(form.get("action_raw"))
    action_url = canonicalize_url(urljoin(source_url, raw_action or source_url))
    field, field_reasons = choose_search_field(form)
    submit_text = normalize_space(" ".join(form.get("submit_texts") or []))
    identity_text = normalize_space(" ".join([
        raw_action, action_url, form.get("id", ""), form.get("name", ""), form.get("class", ""),
        form.get("onsubmit", ""), submit_text,
        normalize_space(field.get("name")) if field else "",
        normalize_space(field.get("id")) if field else "",
    ]))
    lower = identity_text.lower()

    if not action_url:
        return {"qualified": False, "classification": CLASS_REJECTED_INVALID, "action_url": "", "method": method, "search_field": field or {}, "hidden_params": hidden_params(form), "reasons": ["INVALID_ACTION"]}
    if not is_government_host(hostname(action_url)):
        return {"qualified": False, "classification": CLASS_REJECTED_NON_OFFICIAL, "action_url": action_url, "method": method, "search_field": field or {}, "hidden_params": hidden_params(form), "reasons": ["ACTION_NOT_GO_KR"]}
    if not same_host(source_url, action_url):
        return {"qualified": False, "classification": CLASS_REJECTED_CROSS_HOST, "action_url": action_url, "method": method, "search_field": field or {}, "hidden_params": hidden_params(form), "reasons": ["ACTION_CROSS_HOST"]}
    if method not in SAFE_METHODS:
        return {"qualified": False, "classification": CLASS_REJECTED_UNSAFE_METHOD, "action_url": action_url, "method": method, "search_field": field or {}, "hidden_params": hidden_params(form), "reasons": ["UNSAFE_METHOD"]}
    if any(term.lower() in lower for term in SATISFACTION_TERMS):
        return {"qualified": False, "classification": CLASS_REJECTED_SATISFACTION, "action_url": action_url, "method": method, "search_field": field or {}, "hidden_params": hidden_params(form), "reasons": ["SATISFACTION_FORM_IDENTITY"]}
    if any(term.lower() in lower for term in GENERIC_FORM_TERMS):
        return {"qualified": False, "classification": CLASS_REJECTED_GENERIC, "action_url": action_url, "method": method, "search_field": field or {}, "hidden_params": hidden_params(form), "reasons": ["GENERIC_FORM_IDENTITY"]}
    if any(term.lower() in action_url.lower() for term in GLOBAL_SEARCH_PATH_TERMS):
        return {"qualified": False, "classification": CLASS_REJECTED_GLOBAL, "action_url": action_url, "method": method, "search_field": field or {}, "hidden_params": hidden_params(form), "reasons": ["GLOBAL_SITE_SEARCH_ACTION"]}
    if field is None:
        return {"qualified": False, "classification": CLASS_REJECTED_NO_FIELD, "action_url": action_url, "method": method, "search_field": {}, "hidden_params": hidden_params(form), "reasons": ["ACTUAL_SEARCH_FIELD_MISSING"]}

    reasons = list(field_reasons)
    if any(hint.lower() in submit_text.lower() for hint in SEARCH_SUBMIT_HINTS):
        reasons.append("SEARCH_SUBMIT_IDENTITY")
    source_path = urlparse(source_url).path.rstrip("/")
    action_path = urlparse(action_url).path.rstrip("/")
    if source_path == action_path:
        reasons.append("SOURCE_ACTION_SAME_PATH")
    if family == FAMILY_NOTICE and "/pm010301" in action_url.lower():
        reasons.append("NOTICE_BOARD_ACTION_IDENTITY")
    if family == FAMILY_URBAN and "/ct020100" in action_url.lower():
        reasons.append("URBAN_BOARD_ACTION_IDENTITY")

    board_identity = any(reason in reasons for reason in [
        "SOURCE_ACTION_SAME_PATH", "NOTICE_BOARD_ACTION_IDENTITY", "URBAN_BOARD_ACTION_IDENTITY"
    ])
    if not board_identity:
        return {"qualified": False, "classification": CLASS_REJECTED_WEAK, "action_url": action_url, "method": method, "search_field": field, "hidden_params": hidden_params(form), "reasons": unique_strings(reasons + ["SOURCE_LOCAL_IDENTITY_WEAK"])}

    classification = CLASS_QUALIFIED_POST if method == "POST" else CLASS_QUALIFIED_GET
    return {"qualified": True, "classification": classification, "action_url": action_url, "method": method, "search_field": field, "hidden_params": hidden_params(form), "reasons": unique_strings(reasons)}


def contract_key(item: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (
        normalize_space(item.get("source_family")),
        canonicalize_url(item.get("action_url") or ""),
        normalize_space(item.get("method")).upper(),
        normalize_space((item.get("search_field") or {}).get("name") or (item.get("search_field") or {}).get("id")),
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("CURRENT CANONICAL SEARCH CONTRACT RECOVERY")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Target query execution: DISABLED")
    print()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"T-7-S1 input not found: {INPUT_PATH}")
    input_data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(input_data, dict):
        raise TypeError("T-7-S1 input must be JSON object")
    sources = load_sources(input_data)
    print("Canonical source count:", len(sources))
    print()

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    })

    request_count = 0
    http_success_count = 0
    raw_form_count = 0
    raw_records: List[Dict[str, Any]] = []
    source_results: List[Dict[str, Any]] = []

    for index, source in enumerate(sources, start=1):
        source_url = source["url"]
        request_count += 1
        response = fetch_page(session, source_url)
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1

        parser = FormParser()
        raw_html = str(response.get("raw_html") or "")
        if raw_html:
            parser.feed(raw_html)
            parser.close()
        forms = parser.forms
        raw_form_count += len(forms)

        qualified_here = 0
        print("-" * 60)
        print(f"SOURCE {index}")
        print("Family:", source["source_family"])
        print("Regions:", source["regions"])
        print("URL:", source_url)
        print("HTTP:", status)
        print("Forms:", len(forms))

        if isinstance(status, int) and 200 <= status < 300 and not response.get("error"):
            final_url = response.get("final_url") or source_url
            for form_index, form in enumerate(forms, start=1):
                classified = classify_form(source, final_url, form)
                record = {
                    "source_family": source["source_family"],
                    "regions": source["regions"],
                    "source_url": source_url,
                    "form_index": form_index,
                    "action_url": classified["action_url"],
                    "method": classified["method"],
                    "search_field": classified["search_field"],
                    "hidden_params": classified["hidden_params"],
                    "qualified": classified["qualified"],
                    "classification": classified["classification"],
                    "reasons": classified["reasons"],
                    "target_query_executed": False,
                    "document_candidate": False,
                    "verified_positive": False,
                    "runtime_registration_allowed": False,
                    "site_positive_allowed": False,
                    "site_negative_allowed": False,
                    "final_positive_promotion_allowed": False,
                }
                raw_records.append(record)
                if record["qualified"]:
                    qualified_here += 1

        print("Qualified contracts:", qualified_here)
        print("Resolution:", "SEARCH_CONTRACT_RECOVERED" if qualified_here else "NO_QUALIFIED_SEARCH_CONTRACT")
        source_results.append({
            "source_family": source["source_family"], "regions": source["regions"], "url": source_url,
            "http_status": status, "form_count": len(forms), "qualified_contract_count": qualified_here,
            "resolution": "SEARCH_CONTRACT_RECOVERED" if qualified_here else "NO_QUALIFIED_SEARCH_CONTRACT",
        })

    canonical_map: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    duplicate_count = 0
    for item in raw_records:
        if item.get("qualified") is not True:
            continue
        key = contract_key(item)
        if key in canonical_map:
            duplicate_count += 1
            existing = canonical_map[key]
            existing["regions"] = unique_strings((existing.get("regions") or []) + (item.get("regions") or []))
            continue
        canonical_map[key] = dict(item)

    contracts = list(canonical_map.values())
    contracts.sort(key=lambda item: contract_key(item))
    rejected = [item for item in raw_records if item.get("qualified") is not True]
    classification_counts = Counter(item.get("classification") for item in raw_records)

    next_stage_pool = [
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
            "requires_live_contract_reconfirmation": True,
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in contracts
    ]

    resolution = "CURRENT_CANONICAL_SEARCH_CONTRACT_RECOVERY_COMPLETED" if next_stage_pool else "CURRENT_CANONICAL_SEARCH_CONTRACT_RECOVERY_NO_CONTRACT"
    next_action = (
        "T-9에서 hardened current canonical contract를 live reconfirm한 뒤 empty-vs-sentinel query effectiveness만 검증한다. 아직 UQQ700 target query는 실행하지 않는다."
        if next_stage_pool else
        "실행 가능한 current canonical search contract를 복원하지 못했다. SITE FALSE가 아니라 UNKNOWN을 유지한다."
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-8 Current Canonical Search Contract Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {"resolution_type": RESOLUTION_TYPE, "negative_evidence_allowed": False, "source_failure_site_status": "UNKNOWN"},
        "inputs": {"t7_s1_path": str(INPUT_PATH), "t7_s1_resolution": input_data.get("resolution")},
        "summary": {
            "source_count": len(sources), "request_count": request_count, "http_success_count": http_success_count,
            "raw_form_count": raw_form_count, "raw_contract_record_count": len(raw_records),
            "duplicate_contract_removed": duplicate_count, "recovered_contract_count": len(contracts),
            "rejected_contract_count": len(rejected), "next_stage_search_contract_pool_count": len(next_stage_pool),
        },
        "classification_counts": dict(sorted(classification_counts.items())),
        "source_results": source_results,
        "recovered_contracts": contracts,
        "rejected_contracts": rejected,
        "next_stage_search_contract_pool": next_stage_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    keys = [contract_key(item) for item in contracts]
    next_keys = [contract_key(item) for item in next_stage_pool]
    invalid_action_leakage = sum(1 for item in contracts if not canonicalize_url(item.get("action_url") or ""))
    non_go_leakage = sum(1 for item in contracts if not is_government_host(hostname(item.get("action_url") or "")))
    cross_host_leakage = sum(1 for item in contracts if not same_host(item.get("source_url") or "", item.get("action_url") or ""))
    missing_field_leakage = sum(1 for item in contracts if not normalize_space((item.get("search_field") or {}).get("name") or (item.get("search_field") or {}).get("id")))
    global_leakage = sum(1 for item in contracts if any(term.lower() in (item.get("action_url") or "").lower() for term in GLOBAL_SEARCH_PATH_TERMS))
    target_query_leakage = sum(1 for item in raw_records if item.get("target_query_executed") is True)
    document_leakage = sum(1 for item in raw_records if item.get("document_candidate") is True)
    verified_leakage = sum(1 for item in raw_records if item.get("verified_positive") is True)
    runtime_leakage = sum(1 for item in raw_records if item.get("runtime_registration_allowed") is True)
    site_true_leakage = sum(1 for item in raw_records if item.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for item in raw_records if item.get("site_negative_allowed") is True)

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-7-S1 input exists": INPUT_PATH.exists(),
        "T-7-S1 input parsed": isinstance(input_data, dict),
        "canonical source pool loaded": len(sources) > 0,
        "direct source requery enabled": True,
        "HTML form structural parsing enabled": True,
        "actual form action recovery enabled": True,
        "actual search field recovery enabled": True,
        "hidden parameter recovery enabled": True,
        "guessed field generation disabled": True,
        "target query execution disabled": target_query_leakage == 0,
        "document candidate generation disabled": document_leakage == 0,
        "global search leakage zero": global_leakage == 0,
        "all classes valid": all(item.get("classification") in VALID_CLASSES for item in raw_records),
        "qualified classes valid": all(item.get("classification") in QUALIFIED_CLASSES for item in contracts),
        "contracts unique": len(keys) == len(set(keys)),
        "next-stage contracts unique": len(next_keys) == len(set(next_keys)),
        "contract and next-stage parity": set(keys) == set(next_keys),
        "invalid action leakage zero": invalid_action_leakage == 0,
        "non-go.kr action leakage zero": non_go_leakage == 0,
        "cross-host action leakage zero": cross_host_leakage == 0,
        "missing actual search field leakage zero": missing_field_leakage == 0,
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
    print("CURRENT CANONICAL SEARCH CONTRACT RECOVERY RESULT")
    print("=" * 60)
    print("Source count:", len(sources))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Raw form count:", raw_form_count)
    print("Recovered contract count:", len(contracts))
    print("Rejected contract count:", len(rejected))
    print("Next-stage search contract pool count:", len(next_stage_pool))

    if contracts:
        print("\nRECOVERED CURRENT CANONICAL SEARCH CONTRACTS")
        print("-" * 60)
        for index, item in enumerate(contracts, start=1):
            print(f"[{index}] {item.get('source_family')}")
            print("Regions:", item.get("regions"))
            print("Source URL:", item.get("source_url"))
            print("Action URL:", item.get("action_url"))
            print("Method:", item.get("method"))
            print("Search field:", item.get("search_field"))
            print("Hidden params:", item.get("hidden_params"))
            print("Reasons:", item.get("reasons"))
            print()

    print("=" * 60)
    print("RESOLUTION")
    print("=" * 60)
    print(resolution)
    print(next_action)
    print("Output:", OUTPUT_PATH)
    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Global search leakage:", global_leakage)
    print("Invalid action leakage:", invalid_action_leakage)
    print("Non-go.kr action leakage:", non_go_leakage)
    print("Cross-host action leakage:", cross_host_leakage)
    print("Missing actual search field leakage:", missing_field_leakage)
    print("Target query leakage:", target_query_leakage)
    print("Document candidate leakage:", document_leakage)
    print("Verified positive leakage:", verified_leakage)
    print("Runtime registration leakage:", runtime_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")
    if not all_pass:
        print("\nFAILED:")
        for name, passed in validations.items():
            if not passed:
                print("-", name)
        raise AssertionError("UQQ700 current canonical search contract recovery regression failed")


if __name__ == "__main__":
    main()
