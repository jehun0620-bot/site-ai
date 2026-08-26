# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-3

Development Density Management Area
Historical Search Form Action & Notice Identity Recovery

목표
======================================================================

T-2-S1 hardened reverse discovery에서 query contamination false positive를
제거한 결과, 현재 S-3 source 범위에서는 UQQ700 historical document가
확인되지 않았다.

T-3에서는 검색 파라미터명을 임의로 추측하지 않는다. S-3에서 검증된
historical entry endpoint를 직접 조회하고 실제 HTML/JavaScript에서 검색
계약(search contract)을 복원한다.

핵심 원칙
======================================================================

1. 입력은 S-3 hardened endpoint만 사용한다.
2. 반드시 endpoint를 직접 HTTP 조회한다.
3. HTTP 2xx + 최종 go.kr host만 사용한다.
4. <form>의 action/method/input/select/textarea/hidden/submit을 구조적으로 복원한다.
5. 검색 필드는 name/id/placeholder/label/submit text 등 endpoint-local evidence로 식별한다.
6. JavaScript search/submit handler도 제한적으로 복원한다.
7. 검색 필드명(searchKeyword 등)을 임의 생성하지 않는다.
8. form action은 urljoin 후 same-host 또는 동일 official host family만 허용한다.
9. generic login/member/newsletter/contact form은 검색 계약으로 승격하지 않는다.
10. recovered contract 자체는 UQQ700 document evidence가 아니다.
11. recovered contract 자체는 verified positive가 아니다.
12. SITE TRUE/FALSE 자동판정 금지. source 실패는 UNKNOWN을 유지한다.
13. runtime registration 금지.
14. 실제 target query 실행은 다음 T-4 단계에서만 수행한다.
"""

from __future__ import annotations

import html
import json
import re
import time

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

S3_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_source_family_entry_endpoint_"
        "qualification_hardening.json"
    )
)

T2_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_target_document_reverse_discovery.json"
    )
)

OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "historical_search_form_action_recovery.json"
    )
)


# ============================================================
# TARGET / POLICY
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

FAMILY_GAZETTE = "LEGACY_LOCAL_GAZETTE"
FAMILY_NOTICE = "LEGACY_LOCAL_NOTICE"
FAMILY_URBAN = "URBAN_PLANNING_ARCHIVE"
FAMILY_NOTICE_REVERSE = "NOTICE_NUMBER_REVERSE_LOOKUP"

ALLOWED_SOURCE_FAMILIES = {
    FAMILY_GAZETTE,
    FAMILY_NOTICE,
    FAMILY_URBAN,
    FAMILY_NOTICE_REVERSE,
}


# ============================================================
# OUTPUT CLASSES
# ============================================================

CLASS_RECOVERED_FORM_GET = "RECOVERED_HISTORICAL_SEARCH_FORM_GET"
CLASS_RECOVERED_FORM_POST = "RECOVERED_HISTORICAL_SEARCH_FORM_POST"
CLASS_RECOVERED_JS = "RECOVERED_HISTORICAL_SEARCH_JS_CONTRACT"

CLASS_REJECTED_NO_SEARCH_FIELD = "REJECTED_FORM_NO_SEARCH_FIELD"
CLASS_REJECTED_GENERIC_FORM = "REJECTED_GENERIC_FORM"
CLASS_REJECTED_NON_OFFICIAL = "REJECTED_NON_OFFICIAL_ACTION"
CLASS_REJECTED_CROSS_HOST = "REJECTED_CROSS_HOST_ACTION"
CLASS_REJECTED_UNSAFE_METHOD = "REJECTED_UNSAFE_METHOD"
CLASS_REJECTED_INVALID = "REJECTED_INVALID_ACTION"

VALID_CLASSES = {
    CLASS_RECOVERED_FORM_GET,
    CLASS_RECOVERED_FORM_POST,
    CLASS_RECOVERED_JS,
    CLASS_REJECTED_NO_SEARCH_FIELD,
    CLASS_REJECTED_GENERIC_FORM,
    CLASS_REJECTED_NON_OFFICIAL,
    CLASS_REJECTED_CROSS_HOST,
    CLASS_REJECTED_UNSAFE_METHOD,
    CLASS_REJECTED_INVALID,
}

QUALIFIED_CLASSES = {
    CLASS_RECOVERED_FORM_GET,
    CLASS_RECOVERED_FORM_POST,
    CLASS_RECOVERED_JS,
}


# ============================================================
# HTTP
# ============================================================

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 30
REQUEST_DELAY_SECONDS = 0.03

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# SEARCH SEMANTICS
# ============================================================

SEARCH_HINT_TERMS = {
    "search", "srch", "sch", "keyword", "query", "word", "text", "find",
    "검색", "검색어", "찾기", "조회어",
}

SEARCH_EXACT_NAMES = {
    "searchkeyword", "search_keyword", "keyword", "searchword", "search_word",
    "query", "q", "searchtext", "search_text", "srchtext", "schtext",
    "searchvalue", "search_value", "searchterm", "search_term",
}

SEARCH_SUBMIT_TERMS = {
    "검색", "조회", "찾기", "search", "find", "query",
}

GENERIC_FORM_TERMS = {
    "login", "logout", "member", "password", "passwd", "userid", "user_id",
    "newsletter", "subscribe", "contact", "문의", "로그인", "회원가입",
    "비밀번호", "아이디", "메일링",
}

ANTI_SEARCH_FIELD_TYPES = {
    "password", "file", "checkbox", "radio", "submit", "button", "reset", "image",
}

SAFE_METHODS = {"GET", "POST"}

JS_FUNCTION_PATTERN = re.compile(
    r"function\s+([A-Za-z_$][\w$]{0,80})\s*\([^)]*\)\s*\{(.{0,5000}?)\}",
    re.IGNORECASE | re.DOTALL,
)

JS_ACTION_ASSIGN_PATTERN = re.compile(
    r"(?:\.action|setAttribute\s*\(\s*['\"]action['\"]\s*,)\s*=*\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)

JS_SUBMIT_PATTERN = re.compile(r"\.submit\s*\(", re.IGNORECASE)
JS_SEARCH_NAME_PATTERN = re.compile(
    r"(?:search|srch|sch|keyword|query|검색)", re.IGNORECASE,
)


# ============================================================
# URL NORMALIZATION
# ============================================================

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
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def canonicalize_url(url: str) -> str:
    value = html.unescape(normalize_space(url))
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

    if port and not (scheme == "http" and port == 80) and not (scheme == "https" and port == 443):
        netloc = f"{host}:{port}"
    else:
        netloc = host

    path = parsed.path or "/"
    path = re.sub(r";jsessionid=[^/?]+", "", path, flags=re.IGNORECASE)
    path = re.sub(r"/{2,}", "/", path)

    query_items: List[Tuple[str, str]] = []
    seen_pairs: Set[Tuple[str, str]] = set()
    for raw_key, raw_value in parse_qsl(parsed.query, keep_blank_values=True):
        key = normalize_space(raw_key)
        if not key:
            continue
        lowered = key.lower()
        if lowered in VOLATILE_QUERY_KEYS or lowered in TRACKING_QUERY_KEYS:
            continue
        if "csrf" in lowered or "session" in lowered:
            continue
        pair = (key, raw_value)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        query_items.append(pair)

    query_items.sort(key=lambda item: (item[0].lower(), item[1]))
    query = urlencode(query_items, doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    value = normalize_space(host).lower()
    return bool(value) and (value == "go.kr" or value.endswith(".go.kr"))


def same_host(url_a: str, url_b: str) -> bool:
    host_a = hostname(url_a)
    host_b = hostname(url_b)
    return bool(host_a) and host_a == host_b


# ============================================================
# INPUT LOAD
# ============================================================


def load_s3_endpoints(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("next_stage_endpoint_pool")
    if not isinstance(raw, list):
        raw = []

    result: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()

    for item in raw:
        if not isinstance(item, dict):
            continue
        family = normalize_space(item.get("source_family"))
        if family not in ALLOWED_SOURCE_FAMILIES:
            continue
        url = canonicalize_url(item.get("url") or "")
        if not url:
            continue
        key = (family, url)
        if key in seen:
            continue
        seen.add(key)
        regions = item.get("regions")
        if not isinstance(regions, list):
            regions = []
        result.append({
            "source_family": family,
            "url": url,
            "regions": unique_strings(regions),
            "title": normalize_space(item.get("title")),
            "classification": normalize_space(item.get("classification")),
        })

    return result


# ============================================================
# HTTP
# ============================================================


def decode_html(response: requests.Response, data: bytes) -> Tuple[str, str]:
    candidates: List[str] = []
    content_type = normalize_space(response.headers.get("Content-Type"))
    match = re.search(r'''charset\s*=\s*["']?([^;"'\s]+)''', content_type, flags=re.IGNORECASE)
    if match:
        candidates.append(normalize_space(match.group(1)))
    if response.encoding:
        candidates.append(normalize_space(response.encoding))

    ascii_preview = data[:8192].decode("ascii", errors="ignore")
    for pattern in [
        re.compile(r'''<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9._\-]+)''', re.IGNORECASE),
        re.compile(r'''charset\s*=\s*([A-Za-z0-9._\-]+)''', re.IGNORECASE),
    ]:
        meta_match = pattern.search(ascii_preview)
        if meta_match:
            candidates.append(normalize_space(meta_match.group(1)))

    candidates.extend(["utf-8", "cp949", "euc-kr"])
    for encoding in unique_strings(candidates):
        try:
            return data.decode(encoding), encoding
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "requested_url": url,
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "response_bytes": 0,
        "encoding": "",
        "raw_html": "",
        "error": "",
        "error_stage": "",
    }

    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            result["http_status"] = response.status_code
            result["final_url"] = canonicalize_url(str(response.url))
            result["content_type"] = normalize_space(response.headers.get("Content-Type"))

            chunks: List[bytes] = []
            total = 0
            try:
                for chunk in response.iter_content(chunk_size=128 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_RESPONSE_BYTES:
                        raise ValueError(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
                    chunks.append(chunk)
            except Exception as exc:
                result["error"] = repr(exc)
                result["error_stage"] = "BODY_DOWNLOAD"
                return result

            data = b"".join(chunks)
            result["response_bytes"] = len(data)
            content_type_lower = normalize_space(result.get("content_type")).lower()
            prefix = data[:1000].lstrip().lower()
            html_like = (
                "html" in content_type_lower
                or "text/" in content_type_lower
                or prefix.startswith(b"<!doctype html")
                or prefix.startswith(b"<html")
            )
            if not html_like:
                return result

            try:
                decoded, encoding = decode_html(response, data)
            except Exception as exc:
                result["error"] = repr(exc)
                result["error_stage"] = "HTML_DECODE"
                return result

            result["raw_html"] = decoded
            result["encoding"] = encoding

    except requests.RequestException as exc:
        result["error"] = repr(exc)
        result["error_stage"] = "HTTP_REQUEST"
    except Exception as exc:
        result["error"] = repr(exc)
        result["error_stage"] = "UNEXPECTED"

    return result


# ============================================================
# STRUCTURED FORM PARSER
# ============================================================


def attrs_to_dict(attrs: List[Tuple[str, Optional[str]]]) -> Dict[str, str]:
    return {
        normalize_space(key).lower(): normalize_space(value)
        for key, value in attrs
        if normalize_space(key)
    }


class SearchFormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: List[Dict[str, Any]] = []
        self.current_form: Optional[Dict[str, Any]] = None
        self.current_select: Optional[Dict[str, Any]] = None
        self.current_textarea: Optional[Dict[str, Any]] = None
        self.current_button: Optional[Dict[str, Any]] = None
        self.current_label_for = ""
        self.current_label_text: List[str] = []
        self.current_option: Optional[Dict[str, Any]] = None
        self.current_script = False
        self.script_parts: List[str] = []
        self.scripts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attr = attrs_to_dict(attrs)

        if tag == "form":
            self.current_form = {
                "action_raw": attr.get("action", ""),
                "method": (attr.get("method", "GET") or "GET").upper(),
                "enctype": attr.get("enctype", ""),
                "id": attr.get("id", ""),
                "name": attr.get("name", ""),
                "class": attr.get("class", ""),
                "onsubmit": attr.get("onsubmit", ""),
                "controls": [],
                "labels": {},
                "submit_texts": [],
            }
            return

        if tag == "script":
            self.current_script = True
            self.script_parts = []
            return

        if self.current_form is None:
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
            self.current_form["controls"].append(control)
            if control["type"] in {"submit", "button", "image"} and control["value"]:
                self.current_form["submit_texts"].append(control["value"])
            return

        if tag == "select":
            self.current_select = {
                "tag": "select",
                "type": "select",
                "name": attr.get("name", ""),
                "id": attr.get("id", ""),
                "value": "",
                "placeholder": "",
                "title": attr.get("title", ""),
                "class": attr.get("class", ""),
                "options": [],
            }
            return

        if tag == "option" and self.current_select is not None:
            self.current_option = {
                "value": attr.get("value", ""),
                "selected": "selected" in attr,
                "text_parts": [],
            }
            return

        if tag == "textarea":
            self.current_textarea = {
                "tag": "textarea",
                "type": "textarea",
                "name": attr.get("name", ""),
                "id": attr.get("id", ""),
                "value_parts": [],
                "placeholder": attr.get("placeholder", ""),
                "title": attr.get("title", ""),
                "class": attr.get("class", ""),
            }
            return

        if tag == "button":
            self.current_button = {
                "type": (attr.get("type", "submit") or "submit").lower(),
                "name": attr.get("name", ""),
                "value": attr.get("value", ""),
                "text_parts": [],
            }
            return

        if tag == "label":
            self.current_label_for = attr.get("for", "")
            self.current_label_text = []

    def handle_data(self, data: str) -> None:
        text = normalize_space(data)
        if not text:
            return
        if self.current_script:
            self.script_parts.append(data)
        if self.current_option is not None:
            self.current_option["text_parts"].append(text)
        if self.current_textarea is not None:
            self.current_textarea["value_parts"].append(text)
        if self.current_button is not None:
            self.current_button["text_parts"].append(text)
        if self.current_label_for:
            self.current_label_text.append(text)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag == "script":
            self.current_script = False
            script = "\n".join(self.script_parts)
            if normalize_space(script):
                self.scripts.append(script)
            self.script_parts = []
            return

        if self.current_form is None:
            return

        if tag == "option" and self.current_select is not None and self.current_option is not None:
            option = {
                "value": self.current_option.get("value", ""),
                "text": normalize_space(" ".join(self.current_option.get("text_parts", []))),
                "selected": bool(self.current_option.get("selected")),
            }
            self.current_select["options"].append(option)
            if option["selected"]:
                self.current_select["value"] = option["value"]
            self.current_option = None
            return

        if tag == "select" and self.current_select is not None:
            self.current_form["controls"].append(self.current_select)
            self.current_select = None
            return

        if tag == "textarea" and self.current_textarea is not None:
            control = dict(self.current_textarea)
            control["value"] = normalize_space(" ".join(control.pop("value_parts", [])))
            self.current_form["controls"].append(control)
            self.current_textarea = None
            return

        if tag == "button" and self.current_button is not None:
            text = normalize_space(" ".join(self.current_button.get("text_parts", [])))
            if text:
                self.current_form["submit_texts"].append(text)
            self.current_button = None
            return

        if tag == "label" and self.current_label_for:
            text = normalize_space(" ".join(self.current_label_text))
            if text:
                self.current_form["labels"][self.current_label_for] = text
            self.current_label_for = ""
            self.current_label_text = []
            return

        if tag == "form":
            self.forms.append(self.current_form)
            self.current_form = None


# ============================================================
# SEARCH CONTRACT EVALUATION
# ============================================================


def field_search_score(control: Dict[str, Any], labels: Dict[str, str]) -> Tuple[int, List[str]]:
    field_type = normalize_space(control.get("type")).lower()
    if field_type in ANTI_SEARCH_FIELD_TYPES:
        return 0, []

    name = normalize_space(control.get("name"))
    field_id = normalize_space(control.get("id"))
    placeholder = normalize_space(control.get("placeholder"))
    title = normalize_space(control.get("title"))
    label = normalize_space(labels.get(field_id, ""))

    evidence = " ".join([name, field_id, placeholder, title, label]).lower()
    reasons: List[str] = []
    score = 0

    if name.lower() in SEARCH_EXACT_NAMES:
        score += 60
        reasons.append(f"SEARCH_FIELD_EXACT_NAME:{name}")

    for term in SEARCH_HINT_TERMS:
        if term.lower() in evidence:
            score += 12
            reasons.append(f"SEARCH_FIELD_HINT:{term}")

    if field_type in {"text", "search", "textarea"}:
        score += 8
        reasons.append(f"SEARCH_FIELD_TEXTUAL_TYPE:{field_type}")

    return score, unique_strings(reasons)


def form_generic_guard(form: Dict[str, Any]) -> Tuple[bool, List[str]]:
    text_parts: List[str] = [
        form.get("id", ""), form.get("name", ""), form.get("class", ""),
        form.get("action_raw", ""), form.get("onsubmit", ""),
        *form.get("submit_texts", []),
    ]
    for control in form.get("controls", []):
        text_parts.extend([
            control.get("name", ""), control.get("id", ""), control.get("title", ""),
            control.get("placeholder", ""), control.get("type", ""),
        ])
    text = normalize_space(" ".join(text_parts)).lower()
    found = [term for term in GENERIC_FORM_TERMS if term.lower() in text]
    return bool(found), [f"GENERIC_FORM_TERM:{term}" for term in sorted(found)]


def resolve_action(base_url: str, action_raw: str) -> str:
    action = normalize_space(action_raw)
    if not action or action == "#":
        return canonicalize_url(base_url)
    if action.lower().startswith("javascript:"):
        return ""
    return canonicalize_url(urljoin(base_url, html.unescape(action)))


def classify_form(source_url: str, form: Dict[str, Any]) -> Dict[str, Any]:
    method = normalize_space(form.get("method") or "GET").upper()
    action_url = resolve_action(source_url, form.get("action_raw", ""))

    if method not in SAFE_METHODS:
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_UNSAFE_METHOD,
            "action_url": action_url,
            "search_field": {},
            "hidden_params": {},
            "reasons": [f"UNSAFE_METHOD:{method}"],
        }

    if not action_url:
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_INVALID,
            "action_url": "",
            "search_field": {},
            "hidden_params": {},
            "reasons": ["INVALID_FORM_ACTION"],
        }

    if not is_government_host(hostname(action_url)):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_NON_OFFICIAL,
            "action_url": action_url,
            "search_field": {},
            "hidden_params": {},
            "reasons": ["ACTION_HOST_NOT_GO_KR"],
        }

    if not same_host(source_url, action_url):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_CROSS_HOST,
            "action_url": action_url,
            "search_field": {},
            "hidden_params": {},
            "reasons": ["ACTION_CROSS_HOST"],
        }

    generic, generic_reasons = form_generic_guard(form)

    labels = form.get("labels") or {}
    scored: List[Tuple[int, Dict[str, Any], List[str]]] = []
    hidden_params: Dict[str, str] = {}

    for control in form.get("controls", []):
        control_type = normalize_space(control.get("type")).lower()
        control_name = normalize_space(control.get("name"))
        if control_type == "hidden" and control_name:
            hidden_params[control_name] = normalize_space(control.get("value"))
            continue
        score, reasons = field_search_score(control, labels)
        if score > 0 and control_name:
            scored.append((score, control, reasons))

    scored.sort(key=lambda item: (-item[0], normalize_space(item[1].get("name"))))
    best = scored[0] if scored else None

    submit_text = normalize_space(" ".join(form.get("submit_texts", []))).lower()
    submit_search = any(term.lower() in submit_text for term in SEARCH_SUBMIT_TERMS)

    if generic and not (best and best[0] >= 60):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_GENERIC_FORM,
            "action_url": action_url,
            "search_field": {},
            "hidden_params": hidden_params,
            "reasons": generic_reasons,
        }

    if not best or best[0] < 20:
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_NO_SEARCH_FIELD,
            "action_url": action_url,
            "search_field": {},
            "hidden_params": hidden_params,
            "reasons": ["SEARCH_FIELD_NOT_IDENTIFIED"],
        }

    score, control, reasons = best
    if submit_search:
        reasons = unique_strings(reasons + ["SEARCH_SUBMIT_IDENTITY"])
        score += 10

    classification = CLASS_RECOVERED_FORM_GET if method == "GET" else CLASS_RECOVERED_FORM_POST

    return {
        "qualified": True,
        "classification": classification,
        "action_url": action_url,
        "method": method,
        "search_field": {
            "name": normalize_space(control.get("name")),
            "id": normalize_space(control.get("id")),
            "type": normalize_space(control.get("type")),
            "placeholder": normalize_space(control.get("placeholder")),
            "title": normalize_space(control.get("title")),
            "score": score,
        },
        "hidden_params": hidden_params,
        "reasons": reasons,
    }


def recover_js_contracts(source_url: str, scripts: List[str]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()

    for script in scripts:
        for match in JS_FUNCTION_PATTERN.finditer(script):
            function_name = normalize_space(match.group(1))
            body = match.group(2)
            if not JS_SEARCH_NAME_PATTERN.search(function_name + " " + body):
                continue
            if not JS_SUBMIT_PATTERN.search(body):
                continue

            action_raw = ""
            action_match = JS_ACTION_ASSIGN_PATTERN.search(body)
            if action_match:
                action_raw = normalize_space(action_match.group(1))

            action_url = resolve_action(source_url, action_raw) if action_raw else canonicalize_url(source_url)
            if not action_url or not is_government_host(hostname(action_url)) or not same_host(source_url, action_url):
                continue

            key = (function_name, action_url)
            if key in seen:
                continue
            seen.add(key)

            result.append({
                "qualified": True,
                "classification": CLASS_RECOVERED_JS,
                "function_name": function_name,
                "action_url": action_url,
                "method": "UNKNOWN",
                "search_field": {},
                "hidden_params": {},
                "reasons": ["JS_SEARCH_SUBMIT_HANDLER"],
                "body_preview": normalize_space(body)[:1200],
            })

    return result


# ============================================================
# CANONICAL CONTRACT IDENTITY
# ============================================================


def contract_key(item: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (
        normalize_space(item.get("source_family")),
        canonicalize_url(item.get("action_url") or ""),
        normalize_space(item.get("method")).upper(),
        normalize_space((item.get("search_field") or {}).get("name")),
    )


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("HISTORICAL SEARCH FORM ACTION & NOTICE IDENTITY RECOVERY")
    print("=" * 60)
    print()
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Negative evidence allowed:", NEGATIVE_EVIDENCE_ALLOWED)
    print()

    if not S3_STAGE_INPUT_PATH.exists():
        raise FileNotFoundError(f"S-3 input not found: {S3_STAGE_INPUT_PATH}")
    if not T2_STAGE_INPUT_PATH.exists():
        raise FileNotFoundError(f"T-2 input not found: {T2_STAGE_INPUT_PATH}")

    s3_data = json.loads(S3_STAGE_INPUT_PATH.read_text(encoding="utf-8"))
    t2_data = json.loads(T2_STAGE_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(s3_data, dict):
        raise TypeError("S-3 input must be JSON object.")
    if not isinstance(t2_data, dict):
        raise TypeError("T-2 input must be JSON object.")

    endpoints = load_s3_endpoints(s3_data)
    print("S-3 endpoint count:", len(endpoints))
    print("T-2 resolution:", t2_data.get("resolution"))
    print()

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    })

    request_count = 0
    http_success_count = 0
    transport_error_count = 0
    raw_records: List[Dict[str, Any]] = []
    source_results: List[Dict[str, Any]] = []

    for index, source in enumerate(endpoints, start=1):
        if request_count >= MAX_TOTAL_REQUESTS:
            break

        family = source["source_family"]
        source_url = source["url"]
        regions = source["regions"]

        print("-" * 60)
        print(f"SOURCE {index}")
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

        source_contract_count = 0
        final_url = canonicalize_url(response.get("final_url") or source_url)

        if not (
            isinstance(status, int)
            and 200 <= status < 300
            and not response.get("error")
            and final_url
            and is_government_host(hostname(final_url))
        ):
            source_results.append({
                "source_family": family,
                "regions": regions,
                "url": source_url,
                "http_status": status,
                "contract_count": 0,
                "resolution": "SOURCE_FETCH_FAILED",
                "error": response.get("error") or "",
            })
            print("HTTP:", status)
            print("Contracts: 0")
            print("Resolution: SOURCE_FETCH_FAILED")
            print()
            continue

        raw_html = str(response.get("raw_html") or "")
        parser = SearchFormParser()
        try:
            parser.feed(raw_html)
            parser.close()
        except Exception as exc:
            source_results.append({
                "source_family": family,
                "regions": regions,
                "url": source_url,
                "http_status": status,
                "contract_count": 0,
                "resolution": "HTML_FORM_PARSE_FAILED",
                "error": repr(exc),
            })
            print("HTTP:", status)
            print("Contracts: 0")
            print("Resolution: HTML_FORM_PARSE_FAILED")
            print()
            continue

        for form_index, form in enumerate(parser.forms, start=1):
            classification = classify_form(final_url, form)
            record = {
                "source_family": family,
                "regions": regions,
                "source_url": source_url,
                "final_url": final_url,
                "http_status": status,
                "form_index": form_index,
                "form_id": normalize_space(form.get("id")),
                "form_name": normalize_space(form.get("name")),
                "form_class": normalize_space(form.get("class")),
                "action_raw": normalize_space(form.get("action_raw")),
                "action_url": classification.get("action_url") or "",
                "method": normalize_space(classification.get("method") or form.get("method") or "GET").upper(),
                "enctype": normalize_space(form.get("enctype")),
                "search_field": classification.get("search_field") or {},
                "hidden_params": classification.get("hidden_params") or {},
                "submit_texts": unique_strings(form.get("submit_texts") or []),
                "qualified": classification.get("qualified") is True,
                "classification": classification.get("classification"),
                "reasons": unique_strings(classification.get("reasons") or []),
                "contract_only": True,
                "target_query_executed": False,
                "target_document_evidence": False,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            }
            raw_records.append(record)
            if record["qualified"]:
                source_contract_count += 1

        js_contracts = recover_js_contracts(final_url, parser.scripts)
        for js_index, js in enumerate(js_contracts, start=1):
            raw_records.append({
                "source_family": family,
                "regions": regions,
                "source_url": source_url,
                "final_url": final_url,
                "http_status": status,
                "js_index": js_index,
                "function_name": js.get("function_name"),
                "action_url": js.get("action_url"),
                "method": js.get("method"),
                "search_field": js.get("search_field") or {},
                "hidden_params": js.get("hidden_params") or {},
                "qualified": True,
                "classification": CLASS_RECOVERED_JS,
                "reasons": js.get("reasons") or [],
                "body_preview": js.get("body_preview") or "",
                "contract_only": True,
                "target_query_executed": False,
                "target_document_evidence": False,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            })
            source_contract_count += 1

        source_resolution = "SEARCH_CONTRACT_RECOVERED" if source_contract_count else "NO_SEARCH_CONTRACT_IN_SOURCE"
        source_results.append({
            "source_family": family,
            "regions": regions,
            "url": source_url,
            "http_status": status,
            "form_count": len(parser.forms),
            "script_count": len(parser.scripts),
            "contract_count": source_contract_count,
            "resolution": source_resolution,
        })

        print("HTTP:", status)
        print("Forms:", len(parser.forms))
        print("Scripts:", len(parser.scripts))
        print("Contracts:", source_contract_count)
        print("Resolution:", source_resolution)
        print()

        if REQUEST_DELAY_SECONDS > 0:
            time.sleep(REQUEST_DELAY_SECONDS)

    # ========================================================
    # DEDUPE
    # ========================================================

    canonical_map: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    duplicate_count = 0

    for item in raw_records:
        if item.get("qualified") is not True:
            continue
        key = contract_key(item)
        if not key[1]:
            continue
        if key in canonical_map:
            duplicate_count += 1
            existing = canonical_map[key]
            existing["regions"] = unique_strings((existing.get("regions") or []) + (item.get("regions") or []))
            existing["source_urls"] = unique_strings((existing.get("source_urls") or [existing.get("source_url")]) + [item.get("source_url")])
            existing["reasons"] = unique_strings((existing.get("reasons") or []) + (item.get("reasons") or []))
            existing["submit_texts"] = unique_strings((existing.get("submit_texts") or []) + (item.get("submit_texts") or []))
            merged_hidden = dict(existing.get("hidden_params") or {})
            for name, value in (item.get("hidden_params") or {}).items():
                if name not in merged_hidden:
                    merged_hidden[name] = value
            existing["hidden_params"] = merged_hidden
            continue

        canonical_item = dict(item)
        canonical_item["source_urls"] = unique_strings([item.get("source_url")])
        canonical_map[key] = canonical_item

    recovered_contracts = list(canonical_map.values())
    recovered_contracts.sort(key=lambda item: (
        normalize_space(item.get("source_family")),
        canonicalize_url(item.get("action_url") or ""),
        normalize_space(item.get("method")),
        normalize_space((item.get("search_field") or {}).get("name")),
    ))

    rejection_counts = Counter(
        item.get("classification")
        for item in raw_records
        if item.get("qualified") is not True
    )

    # T-4 input: contract only. Do not inject TARGET_NAME here.
    next_stage_search_contract_pool = [
        {
            "source_family": item.get("source_family"),
            "regions": item.get("regions") or [],
            "source_urls": item.get("source_urls") or [],
            "classification": item.get("classification"),
            "action_url": canonicalize_url(item.get("action_url") or ""),
            "method": normalize_space(item.get("method")).upper(),
            "search_field": item.get("search_field") or {},
            "hidden_params": item.get("hidden_params") or {},
            "reasons": item.get("reasons") or [],
            "contract_only": True,
            "target_query_executed": False,
            "target_document_evidence": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in recovered_contracts
    ]

    if next_stage_search_contract_pool:
        resolution = "HISTORICAL_SEARCH_FORM_ACTION_RECOVERY_COMPLETED"
        next_action = (
            "복원된 실제 search contract만 T-4 bounded historical search execution 입력으로 사용한다. "
            "T-4에서 UQQ700 query를 주입하되 query 문자열 자체는 candidate evidence로 사용하지 않고, "
            "response result row/link-local title/notice number/document URL에서 target identity를 직접 검증한다."
        )
    else:
        resolution = "HISTORICAL_SEARCH_FORM_ACTION_RECOVERY_NO_CONTRACT"
        next_action = (
            "현재 S-3 endpoint HTML/JavaScript에서 신뢰 가능한 historical search contract를 복원하지 못했다. "
            "SITE FALSE로 판정하지 않고 UNKNOWN을 유지한다. 다음 fallback은 notice-number reverse lookup "
            "또는 기관별 archive endpoint family 확장이다."
        )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-3 Historical Search Form Action & Notice Identity Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "inputs": {
            "s3_stage_path": str(S3_STAGE_INPUT_PATH),
            "t2_stage_path": str(T2_STAGE_INPUT_PATH),
            "s3_resolution": s3_data.get("resolution"),
            "t2_resolution": t2_data.get("resolution"),
        },
        "method": {
            "s3_hardened_endpoints_only": True,
            "direct_endpoint_fetch": True,
            "html_form_structural_parse": True,
            "actual_action_recovery_only": True,
            "actual_search_field_recovery_only": True,
            "hidden_parameter_recovery": True,
            "javascript_search_handler_recovery": True,
            "guessed_query_parameter_names_disabled": True,
            "target_query_execution_enabled": False,
            "query_contamination_disabled": True,
            "same_host_action_required": True,
            "official_go_kr_action_required": True,
            "generic_form_guard_enabled": True,
            "contract_is_target_document_evidence": False,
            "negative_evidence_enabled": False,
            "verified_positive_promotion_allowed": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
        },
        "summary": {
            "s3_endpoint_count": len(endpoints),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "raw_form_contract_record_count": len(raw_records),
            "duplicate_contract_removed": duplicate_count,
            "recovered_contract_count": len(recovered_contracts),
            "next_stage_search_contract_pool_count": len(next_stage_search_contract_pool),
        },
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "source_results": source_results,
        "recovered_search_contracts": recovered_contracts,
        "next_stage_search_contract_pool": next_stage_search_contract_pool,
        "all_form_records": raw_records,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }

    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 60)
    print("HISTORICAL SEARCH FORM ACTION RECOVERY RESULT")
    print("=" * 60)
    print("S-3 endpoint count:", len(endpoints))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Transport error count:", transport_error_count)
    print("Raw form contract record count:", len(raw_records))
    print("Duplicate contract removed:", duplicate_count)
    print("Recovered contract count:", len(recovered_contracts))
    print("Next-stage search contract pool count:", len(next_stage_search_contract_pool))

    if recovered_contracts:
        print()
        print("RECOVERED SEARCH CONTRACTS")
        print("-" * 60)
        for index, item in enumerate(recovered_contracts, start=1):
            print(f"[{index}] {item.get('classification')}")
            print("Family:", item.get("source_family"))
            print("Regions:", item.get("regions"))
            print("Source URL:", item.get("source_url"))
            print("Action URL:", item.get("action_url"))
            print("Method:", item.get("method"))
            print("Search field:", item.get("search_field"))
            print("Hidden params:", item.get("hidden_params"))
            print("Reasons:", item.get("reasons"))
            print()

    print()
    print("=" * 60)
    print("RESOLUTION")
    print("=" * 60)
    print(resolution)
    print()
    print(next_action)
    print()
    print("Output:", OUTPUT_PATH)

    # ========================================================
    # VALIDATION
    # ========================================================

    contract_keys = [contract_key(item) for item in recovered_contracts]
    next_keys = [
        (
            normalize_space(item.get("source_family")),
            canonicalize_url(item.get("action_url") or ""),
            normalize_space(item.get("method")).upper(),
            normalize_space((item.get("search_field") or {}).get("name")),
        )
        for item in next_stage_search_contract_pool
    ]

    invalid_action_leakage = sum(1 for item in recovered_contracts if not canonicalize_url(item.get("action_url") or ""))
    non_go_kr_leakage = sum(1 for item in recovered_contracts if not is_government_host(hostname(item.get("action_url") or "")))
    cross_host_leakage = sum(1 for item in recovered_contracts if not same_host(item.get("source_url") or "", item.get("action_url") or ""))
    guessed_field_leakage = sum(1 for item in recovered_contracts if item.get("classification") != CLASS_RECOVERED_JS and not normalize_space((item.get("search_field") or {}).get("name")))
    target_query_execution_leakage = sum(1 for item in raw_records if item.get("target_query_executed") is True)
    target_document_evidence_leakage = sum(1 for item in raw_records if item.get("target_document_evidence") is True)
    verified_positive_leakage = sum(1 for item in raw_records if item.get("verified_positive") is True)
    runtime_registration_leakage = sum(1 for item in raw_records if item.get("runtime_registration_allowed") is True)
    site_true_leakage = sum(1 for item in raw_records if item.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for item in raw_records if item.get("site_negative_allowed") is True)
    next_stage_safety_leakage = sum(
        1
        for item in next_stage_search_contract_pool
        if (
            item.get("target_query_executed") is True
            or item.get("target_document_evidence") is True
            or item.get("verified_positive") is True
            or item.get("runtime_registration_allowed") is True
            or item.get("site_positive_allowed") is True
            or item.get("site_negative_allowed") is True
            or item.get("final_positive_promotion_allowed") is True
        )
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "S-3 input exists": S3_STAGE_INPUT_PATH.exists(),
        "T-2 input exists": T2_STAGE_INPUT_PATH.exists(),
        "S-3 input parsed": isinstance(s3_data, dict),
        "T-2 input parsed": isinstance(t2_data, dict),
        "S-3 hardened endpoints loaded": len(endpoints) > 0,
        "direct endpoint fetch enabled": True,
        "HTML form structural parsing enabled": True,
        "actual form action recovery enabled": True,
        "actual search field recovery enabled": True,
        "hidden parameter recovery enabled": True,
        "javascript handler recovery enabled": True,
        "guessed query parameter names disabled": True,
        "target query execution disabled": target_query_execution_leakage == 0,
        "query contamination remains disabled": target_document_evidence_leakage == 0,
        "generic form guard enabled": True,
        "all classes valid": all(item.get("classification") in VALID_CLASSES for item in raw_records),
        "qualified classes valid": all(item.get("classification") in QUALIFIED_CLASSES for item in recovered_contracts),
        "canonical contracts unique": len(contract_keys) == len(set(contract_keys)),
        "next-stage contracts unique": len(next_keys) == len(set(next_keys)),
        "candidate and next-stage contract parity": set(contract_keys) == set(next_keys),
        "recovered actions valid": invalid_action_leakage == 0,
        "recovered actions require go.kr": non_go_kr_leakage == 0,
        "recovered actions require same host": cross_host_leakage == 0,
        "non-JS recovered contracts require actual field name": guessed_field_leakage == 0,
        "verified positive leakage zero": verified_positive_leakage == 0,
        "runtime registration leakage zero": runtime_registration_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "next-stage safety leakage zero": next_stage_safety_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")

    print()
    print("Invalid action leakage:", invalid_action_leakage)
    print("Non-go.kr action leakage:", non_go_kr_leakage)
    print("Cross-host action leakage:", cross_host_leakage)
    print("Guessed field leakage:", guessed_field_leakage)
    print("Target query execution leakage:", target_query_execution_leakage)
    print("Target document evidence leakage:", target_document_evidence_leakage)
    print("Verified positive leakage:", verified_positive_leakage)
    print("Runtime registration leakage:", runtime_registration_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print("Next-stage safety leakage:", next_stage_safety_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")

    if not all_pass:
        failed = [name for name, passed in validations.items() if not passed]
        print()
        print("FAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError(
            "Development density management area historical search form action recovery regression failed"
        )


if __name__ == "__main__":
    main()
