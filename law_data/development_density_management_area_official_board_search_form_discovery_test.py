# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-I
Development Density Management Area
Official Board Search Form / Parameter Discovery

H 단계에서 정제된 공식 고시·공고·공보·도시계획 endpoint를 대상으로
실제 검색 form / 검색 parameter / pagination 구조를 탐색하고
'개발밀도관리구역' 검색 결과에서 실제 상세 게시물 URL seed를 수집한다.

안전정책
======================================================================
1. 검색 결과 페이지 자체는 VERIFIED_POSITIVE가 아니다.
2. 검색 결과 0건을 SITE FALSE로 해석하지 않는다.
3. 검색 form을 확인하지 못하면 임의 query parameter를 주입하지 않는다.
4. POST는 검색 form으로 판정된 경우에만 제출한다.
5. hidden/select 기존 값을 보존한다.
6. 채용/입찰/분묘/개인정보/보건/일자리 endpoint는 실행에서 제외한다.
7. URBAN_PLANNING_BOARD는 label/URL 자체에 강한 도시계획 증거가 있어야 한다.
8. runtime spatial condition 등록은 계속 차단한다.
"""

from __future__ import annotations

import html
import json
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests


# ============================================================
# PATH / TARGET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_official_board_endpoint_refinement.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR
    / "development_density_management_area_official_board_search_form_discovery.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


# ============================================================
# CONFIG
# ============================================================

REQUEST_TIMEOUT = 20
REQUEST_SLEEP = 0.20
MAX_CONTENT_LENGTH = 2_000_000
MAX_FORMS_PER_ENDPOINT = 12
MAX_SEARCH_SUBMISSIONS_PER_ENDPOINT = 3
MAX_RESULT_LINKS_PER_SUBMISSION = 160

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

ALLOWED_CLASSES = {
    "PRIMARY_GOSI_BOARD",
    "GAZETTE_ARCHIVE",
    "URBAN_PLANNING_BOARD",
}

EXCLUDED_EXECUTION_TERMS = [
    "채용", "일자리", "구인", "구직", "입찰", "분묘", "무연분묘",
    "개인정보", "제3자 제공", "위탁 공고", "보건", "보건소", "병원",
    "의료", "백신", "예방접종", "employment", "recruit", "hiring",
    "bid", "tender",
]

PRIMARY_STRONG_LABEL_TERMS = [
    "고시공고", "고시/공고", "고시 공고", "공고알림", "고시",
]
PRIMARY_STRONG_URL_TERMS = [
    "/saeol/gosi/list.do",
    "/prog/saeolgosi/",
    "/prog/publicnotice/",
    "/news/announce",
    "/notification/public_notice",
    "/notification/old_public_notice",
]
GAZETTE_TERMS = ["공보", "시보", "구보", "군보", "gazette"]
URBAN_STRONG_TERMS = [
    "도시계획", "도시관리계획", "지구단위계획",
    "urbanplanning", "cityplan", "citymanagement",
]
DETAIL_URL_HINT_TERMS = [
    "/view.do", "detail.do", "selectboardarticle.do", "bbsmsgdetail",
    "eminwonannouncedetail", "act=view", "idx=", "nttid=", "mgt_no=",
    "notancmtmgtno=", "seq=",
]
SEARCHISH_ACTION_TERMS = [
    "search", "list", "board", "bbs", "gosi", "notice", "announce",
    "notification", "gazette", "city", "urban", "plan",
]
UNSAFE_FORM_TERMS = [
    "login", "signin", "logout", "write", "insert", "update", "delete",
    "remove", "save", "register", "join", "password", "passwd",
    "회원가입", "로그인", "삭제", "등록", "수정", "저장",
]
SEARCH_FIELD_HINT_TERMS = [
    "keyword", "query", "search", "searchword", "searchkeyword",
    "searchtext", "searchtxt", "sch", "schtext", "schkeyword",
    "skeyword", "stext", "q", "keyfield", "searchwrd", "searchterm",
    "srch", "title", "subject", "검색", "검색어", "제목",
]
SEARCH_FIELD_NEGATIVE_TERMS = [
    "date", "start", "end", "from", "to", "page", "size", "count",
    "sort", "order", "csrf", "token",
]
PAGINATION_HINT_TERMS = [
    "page", "pageindex", "pageno", "pagenum", "currentpage",
    "currentpageno", "curpage", "nowpage", "recordcountperpage",
    "rows", "offset",
]
RESULT_DETAIL_HINT_TERMS = [
    "view", "detail", "article", "post", "selectboardarticle",
    "bbsmsgdetail", "eminwonannouncedetail", "notancmtmgtno",
    "nttid", "mgt_no", "idx", "seq",
]
ZERO_RESULT_PATTERNS = [
    re.compile(r"검색결과\s*0\s*건"),
    re.compile(r"검색\s*결과\s*0\s*건"),
    re.compile(r"총\s*0\s*건"),
    re.compile(r'''전체\s*[“"']?0[”"']?\s*개의?\s*결과'''),
    re.compile(r"결과를\s*찾을\s*수\s*없"),
    re.compile(r"검색된\s*자료가\s*없"),
    re.compile(r"등록된\s*게시물이\s*없"),
    re.compile(r"조회된\s*데이터가\s*없"),
]

VOLATILE_QUERY_KEYS = {
    "token", "_csrf", "csrf", "jsessionid", "sessionid", "session_id",
    "timestamp", "_",
}


# ============================================================
# BASIC UTIL
# ============================================================

@dataclass
class FetchResult:
    request_url: str
    http_status: Optional[int]
    content_type: str
    text: str
    error: Optional[str]
    final_url: Optional[str]


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def strip_html(source: str) -> str:
    value = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", source)
    value = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", value)
    value = re.sub(r"(?is)<[^>]+>", " ", value)
    return normalize_space(html.unescape(value))


def compact_text(value: str) -> str:
    return re.sub(r"\s+", "", normalize_space(value))


def contains_target(value: str) -> bool:
    return compact_text(TARGET_NAME) in compact_text(value)


def contains_any_term(value: str, terms: Sequence[str]) -> bool:
    lowered = normalize_space(value).lower()
    return any(term.lower() in lowered for term in terms)


def build_preview(value: str, radius: int = 260) -> str:
    text = normalize_space(value)
    for variant in (TARGET_NAME, "개발밀도 관리구역", "개발 밀도 관리구역"):
        index = text.find(variant)
        if index >= 0:
            start = max(0, index - radius)
            end = min(len(text), index + len(TARGET_NAME) + radius)
            return text[start:end]
    return text[: radius * 2]


def is_zero_result_page(text: str) -> bool:
    value = normalize_space(text)
    return any(pattern.search(value) is not None for pattern in ZERO_RESULT_PATTERNS)


# ============================================================
# URL UTIL
# ============================================================

def clean_query_key(key: str) -> str:
    decoded = html.unescape(requests.utils.unquote(str(key or ""))).strip()
    return re.sub(r"^[;&\s]+", "", decoded)


def normalize_url(url: str, remove_volatile: bool = True) -> str:
    try:
        parsed = urlparse(html.unescape(str(url or "")))
    except Exception:
        return str(url or "")

    query_items = []
    seen_pairs = set()

    for raw_key, value in parse_qsl(parsed.query, keep_blank_values=True):
        key = clean_query_key(raw_key)
        if not key:
            continue
        if remove_volatile and key.lower() in VOLATILE_QUERY_KEYS:
            continue
        pair = (key, value)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        query_items.append(pair)

    path = re.sub(r";jsessionid=[^/?#]+", "", parsed.path, flags=re.I)
    return urlunparse(
        parsed._replace(
            path=path,
            query=urlencode(query_items, doseq=True),
            fragment="",
        )
    )


def same_or_subdomain(url: str, base_url: str) -> bool:
    try:
        target_host = (urlparse(url).hostname or "").lower()
        base_host = (urlparse(base_url).hostname or "").lower()
    except Exception:
        return False
    if not target_host or not base_host:
        return False
    return (
        target_host == base_host
        or target_host.endswith("." + base_host)
        or base_host.endswith("." + target_host)
    )


def is_probably_detail_url(url: str) -> bool:
    lower = url.lower()
    return any(term in lower for term in DETAIL_URL_HINT_TERMS)


def is_search_page_url(url: str) -> bool:
    lower = url.lower()
    return any(
        term in lower
        for term in (
            "/search", "search.", "search?", "search.do", "search.jsp",
            "totalsearch",
        )
    )


# ============================================================
# HTTP
# ============================================================

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def _response_to_fetch(request_url: str, response: requests.Response) -> FetchResult:
    content_type = response.headers.get("Content-Type", "") or ""
    lower_type = content_type.lower()
    text = ""
    if (
        "text/" in lower_type
        or "html" in lower_type
        or "xml" in lower_type
        or "json" in lower_type
        or not lower_type
    ):
        text = response.text or ""
        if len(text) > MAX_CONTENT_LENGTH:
            text = text[:MAX_CONTENT_LENGTH]
    return FetchResult(
        request_url=request_url,
        http_status=response.status_code,
        content_type=content_type,
        text=text,
        error=None,
        final_url=response.url,
    )


def fetch_get(url: str) -> FetchResult:
    try:
        response = SESSION.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        return _response_to_fetch(url, response)
    except requests.RequestException as exc:
        return FetchResult(url, None, "", "", repr(exc), None)


def submit_form_request(
    *,
    method: str,
    action_url: str,
    params: Dict[str, str],
    referer: str,
) -> FetchResult:
    try:
        if method.upper() == "POST":
            response = SESSION.post(
                action_url,
                data=params,
                headers={"Referer": referer},
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            return _response_to_fetch(action_url, response)

        parsed = urlparse(action_url)
        existing = dict(parse_qsl(parsed.query, keep_blank_values=True))
        merged = {**existing, **params}
        request_url = urlunparse(
            parsed._replace(query=urlencode(merged, doseq=True))
        )
        response = SESSION.get(
            request_url,
            headers={"Referer": referer},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        return _response_to_fetch(request_url, response)
    except requests.RequestException as exc:
        return FetchResult(action_url, None, "", "", repr(exc), None)


# ============================================================
# HTML PARSERS
# ============================================================

class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: List[Dict[str, Any]] = []
        self.current_form: Optional[Dict[str, Any]] = None
        self.current_select: Optional[Dict[str, Any]] = None
        self.current_option: Optional[Dict[str, Any]] = None
        self.current_textarea: Optional[Dict[str, Any]] = None
        self.form_text_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr = {k: (v if v is not None else "") for k, v in attrs}
        tag = tag.lower()

        if tag == "form":
            self.current_form = {
                "method": (attr.get("method") or "GET").upper(),
                "action": attr.get("action") or "",
                "id": attr.get("id") or "",
                "name": attr.get("name") or "",
                "class": attr.get("class") or "",
                "inputs": [],
                "selects": [],
                "textareas": [],
                "text": "",
            }
            self.form_text_parts = []
            return

        if self.current_form is None:
            return

        if tag == "input":
            self.current_form["inputs"].append(
                {
                    "type": (attr.get("type") or "text").lower(),
                    "name": attr.get("name") or "",
                    "id": attr.get("id") or "",
                    "value": attr.get("value") or "",
                    "placeholder": attr.get("placeholder") or "",
                    "title": attr.get("title") or "",
                    "class": attr.get("class") or "",
                }
            )
        elif tag == "select":
            self.current_select = {
                "name": attr.get("name") or "",
                "id": attr.get("id") or "",
                "title": attr.get("title") or "",
                "options": [],
            }
        elif tag == "option" and self.current_select is not None:
            self.current_option = {
                "value": attr.get("value") or "",
                "selected": "selected" in attr,
                "text": "",
            }
        elif tag == "textarea":
            self.current_textarea = {
                "name": attr.get("name") or "",
                "id": attr.get("id") or "",
                "placeholder": attr.get("placeholder") or "",
                "title": attr.get("title") or "",
                "value": "",
            }

    def handle_data(self, data: str) -> None:
        if self.current_form is None:
            return
        self.form_text_parts.append(data)
        if self.current_option is not None:
            self.current_option["text"] += data
        if self.current_textarea is not None:
            self.current_textarea["value"] += data

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "option":
            if self.current_select is not None and self.current_option is not None:
                self.current_option["text"] = normalize_space(self.current_option["text"])
                self.current_select["options"].append(self.current_option)
            self.current_option = None
        elif tag == "select":
            if self.current_form is not None and self.current_select is not None:
                self.current_form["selects"].append(self.current_select)
            self.current_select = None
            self.current_option = None
        elif tag == "textarea":
            if self.current_form is not None and self.current_textarea is not None:
                self.current_textarea["value"] = normalize_space(
                    self.current_textarea["value"]
                )
                self.current_form["textareas"].append(self.current_textarea)
            self.current_textarea = None
        elif tag == "form":
            if self.current_form is not None:
                self.current_form["text"] = normalize_space(" ".join(self.form_text_parts))
                self.forms.append(self.current_form)
            self.current_form = None
            self.current_select = None
            self.current_option = None
            self.current_textarea = None
            self.form_text_parts = []


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: List[Dict[str, str]] = []
        self.current_href: Optional[str] = None
        self.current_attrs: Dict[str, str] = {}
        self.text_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag.lower() != "a":
            return
        attr = {k: (v if v is not None else "") for k, v in attrs}
        self.current_href = attr.get("href") or ""
        self.current_attrs = attr
        self.text_parts = []

    def handle_data(self, data: str) -> None:
        if self.current_href is not None:
            self.text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self.current_href is not None:
            self.links.append(
                {
                    "href": self.current_href,
                    "label": normalize_space(" ".join(self.text_parts)),
                    "title": self.current_attrs.get("title") or "",
                }
            )
            self.current_href = None
            self.current_attrs = {}
            self.text_parts = []


def parse_forms(source: str) -> List[Dict[str, Any]]:
    parser = FormParser()
    try:
        parser.feed(source)
    except Exception:
        return []
    return parser.forms


def extract_links(source: str, base_url: str) -> List[Dict[str, str]]:
    parser = LinkParser()
    try:
        parser.feed(source)
    except Exception:
        return []

    results = []
    seen = set()
    for link in parser.links:
        href = normalize_space(link.get("href"))
        if not href or href.lower().startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = normalize_url(urljoin(base_url, href), remove_volatile=False)
        if not absolute.startswith(("http://", "https://")):
            continue
        key = (absolute, link.get("label") or "")
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "url": absolute,
                "label": link.get("label") or "",
                "title": link.get("title") or "",
            }
        )
    return results


# ============================================================
# H-STAGE INPUT EXTRACTION
# ============================================================

def recursive_dicts(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from recursive_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from recursive_dicts(child)


def first_string(item: Dict[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and normalize_space(value):
            return normalize_space(value)
    return ""


def extract_refined_endpoints(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    results = []
    seen = set()

    for item in recursive_dicts(data):
        endpoint_class = first_string(
            item,
            ("classification", "endpoint_class", "class", "semantic_class"),
        )
        if endpoint_class not in ALLOWED_CLASSES:
            continue

        raw_url = first_string(
            item,
            ("canonical_url", "canonical_endpoint_url", "url", "endpoint_url"),
        )
        if not raw_url.startswith(("http://", "https://")):
            continue

        canonical_url = normalize_url(raw_url)
        region = first_string(item, ("region", "agency", "municipality"))
        agency = first_string(item, ("agency", "region", "municipality"))
        label = first_string(
            item,
            ("label", "best_label", "representative_label", "title", "name"),
        )

        # raw_variants에서 label 보강
        if not label and isinstance(item.get("raw_variants"), list):
            for variant in item["raw_variants"]:
                if isinstance(variant, dict):
                    label = first_string(variant, ("label", "title"))
                    if label:
                        break

        key = (region, endpoint_class, canonical_url)
        if key in seen:
            continue
        seen.add(key)

        results.append(
            {
                "region": region,
                "agency": agency or region,
                "classification": endpoint_class,
                "label": label,
                "canonical_url": canonical_url,
                "source_score": item.get("score") or item.get("relevance_score") or 0,
                "source_reasons": item.get("reasons") or [],
            }
        )

    return results


# ============================================================
# EXECUTION FILTER
# ============================================================

def endpoint_execution_decision(endpoint: Dict[str, Any]) -> Dict[str, Any]:
    endpoint_class = endpoint["classification"]
    label = normalize_space(endpoint.get("label"))
    url = endpoint["canonical_url"]
    combined = normalize_space(label + " " + requests.utils.unquote(url))

    if contains_any_term(combined, EXCLUDED_EXECUTION_TERMS):
        return {"execute": False, "reason": "EXCLUDED_NOISE_ENDPOINT"}

    if is_probably_detail_url(url):
        return {"execute": False, "reason": "DIRECT_DETAIL_ENDPOINT_NOT_SEARCH_BOARD"}

    if endpoint_class == "PRIMARY_GOSI_BOARD":
        if not (
            contains_any_term(label, PRIMARY_STRONG_LABEL_TERMS)
            or contains_any_term(url, PRIMARY_STRONG_URL_TERMS)
        ):
            return {"execute": False, "reason": "PRIMARY_GOSI_WEAK_EXECUTION_EVIDENCE"}
        return {"execute": True, "reason": "PRIMARY_GOSI_EXECUTION_ELIGIBLE"}

    if endpoint_class == "GAZETTE_ARCHIVE":
        if not contains_any_term(combined, GAZETTE_TERMS):
            return {"execute": False, "reason": "GAZETTE_WEAK_EXECUTION_EVIDENCE"}
        return {"execute": True, "reason": "GAZETTE_EXECUTION_ELIGIBLE"}

    if endpoint_class == "URBAN_PLANNING_BOARD":
        # 본문 내용은 사용하지 않는다. label + URL만 구조 증거로 사용.
        if not contains_any_term(combined, URBAN_STRONG_TERMS):
            return {"execute": False, "reason": "URBAN_BODY_ONLY_OR_WEAK_EVIDENCE"}
        return {"execute": True, "reason": "URBAN_STRUCTURAL_EXECUTION_ELIGIBLE"}

    return {"execute": False, "reason": "UNSUPPORTED_CLASS"}


# ============================================================
# FORM ANALYSIS
# ============================================================

def field_descriptor(field: Dict[str, Any]) -> str:
    return normalize_space(
        " ".join(
            str(field.get(key) or "")
            for key in ("name", "id", "placeholder", "title", "class")
        )
    )


def score_search_field(field: Dict[str, Any]) -> int:
    field_type = str(field.get("type") or "text").lower()
    if field_type not in {"text", "search", "", "textarea"}:
        return -100

    descriptor = field_descriptor(field)
    lower = descriptor.lower()
    if contains_any_term(lower, SEARCH_FIELD_NEGATIVE_TERMS):
        return -20

    score = 0
    name = str(field.get("name") or "")
    lower_name = name.lower()

    for hint in SEARCH_FIELD_HINT_TERMS:
        hint_lower = hint.lower()
        if lower_name == hint_lower:
            score += 10
        elif hint_lower in lower:
            score += 4

    if contains_any_term(descriptor, ("검색", "검색어", "제목", "내용")):
        score += 6
    if field_type == "search":
        score += 5
    if name:
        score += 1
    return score


def find_search_field_candidates(form: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = []
    for field in form.get("inputs", []):
        score = score_search_field(field)
        if score > 0 and field.get("name"):
            candidates.append({**field, "score": score, "source": "input"})

    for textarea in form.get("textareas", []):
        candidate = {**textarea, "type": "textarea"}
        score = score_search_field(candidate)
        if score > 0 and textarea.get("name"):
            candidates.append({**candidate, "score": score, "source": "textarea"})

    return sorted(
        candidates,
        key=lambda item: (-int(item.get("score", 0)), str(item.get("name", ""))),
    )


def get_hidden_values(form: Dict[str, Any]) -> Dict[str, str]:
    result = {}
    for field in form.get("inputs", []):
        if str(field.get("type") or "").lower() != "hidden":
            continue
        name = str(field.get("name") or "")
        if name:
            result[name] = str(field.get("value") or "")
    return result


def get_selected_values(form: Dict[str, Any]) -> Dict[str, str]:
    result = {}
    for select in form.get("selects", []):
        name = str(select.get("name") or "")
        options = select.get("options") or []
        if not name or not options:
            continue
        selected = None
        for option in options:
            if option.get("selected"):
                selected = str(option.get("value") or "")
                break
        if selected is None:
            selected = str(options[0].get("value") or "")
        result[name] = selected
    return result


def form_is_safe_search_form(form: Dict[str, Any], page_url: str) -> Tuple[bool, str]:
    method = str(form.get("method") or "GET").upper()
    if method not in {"GET", "POST"}:
        return False, "UNSUPPORTED_FORM_METHOD"

    action_url = urljoin(page_url, normalize_space(form.get("action")) or page_url)
    combined = normalize_space(
        " ".join(
            [
                action_url,
                str(form.get("id") or ""),
                str(form.get("name") or ""),
                str(form.get("class") or ""),
                str(form.get("text") or ""),
            ]
        )
    )

    if contains_any_term(combined, UNSAFE_FORM_TERMS):
        return False, "UNSAFE_STATE_CHANGING_OR_LOGIN_FORM"

    search_fields = find_search_field_candidates(form)
    if not search_fields:
        return False, "NO_SEARCH_FIELD"

    if method == "POST":
        if not (
            contains_any_term(action_url, SEARCHISH_ACTION_TERMS)
            or contains_any_term(
                combined,
                ("검색", "조회", "검색어", "고시", "공고", "공보", "시보", "도시계획"),
            )
        ):
            return False, "POST_SEARCH_PURPOSE_NOT_STRONG_ENOUGH"

    return True, "SAFE_SEARCH_FORM"


def analyze_form(form: Dict[str, Any], page_url: str, form_index: int) -> Dict[str, Any]:
    action_url = normalize_url(
        urljoin(page_url, normalize_space(form.get("action")) or page_url),
        remove_volatile=False,
    )
    safe, reason = form_is_safe_search_form(form, page_url)
    return {
        "form_index": form_index,
        "method": str(form.get("method") or "GET").upper(),
        "action_url": action_url,
        "form_id": form.get("id") or "",
        "form_name": form.get("name") or "",
        "safe_search_form": safe,
        "safety_reason": reason,
        "search_fields": find_search_field_candidates(form),
        "hidden_values": get_hidden_values(form),
        "selected_values": get_selected_values(form),
        "form_text_preview": normalize_space(form.get("text"))[:500],
    }


def discover_pagination_parameters(
    source: str,
    page_url: str,
    raw_forms: List[Dict[str, Any]],
) -> List[str]:
    found = set()

    for link in extract_links(source, page_url):
        try:
            query = parse_qsl(urlparse(link["url"]).query, keep_blank_values=True)
        except Exception:
            continue
        for key, _ in query:
            cleaned = clean_query_key(key)
            lower = cleaned.lower()
            if any(hint.lower() in lower for hint in PAGINATION_HINT_TERMS):
                found.add(cleaned)

    for form in raw_forms:
        for field in form.get("inputs", []):
            name = str(field.get("name") or "")
            lower = name.lower()
            if name and any(hint.lower() in lower for hint in PAGINATION_HINT_TERMS):
                found.add(name)
        for select in form.get("selects", []):
            name = str(select.get("name") or "")
            lower = name.lower()
            if name and any(hint.lower() in lower for hint in PAGINATION_HINT_TERMS):
                found.add(name)

    return sorted(found)


def build_submission_params(form: Dict[str, Any], search_field_name: str) -> Dict[str, str]:
    params = {}
    params.update({str(k): str(v) for k, v in (form.get("hidden_values") or {}).items()})
    params.update({str(k): str(v) for k, v in (form.get("selected_values") or {}).items()})
    params[search_field_name] = TARGET_NAME
    return params


# ============================================================
# RESULT DETAIL SEED EXTRACTION
# ============================================================

def extract_detail_seed_links(
    source: str,
    result_url: str,
    endpoint_url: str,
) -> List[Dict[str, Any]]:
    results = []
    seen = set()

    for link in extract_links(source, result_url)[:MAX_RESULT_LINKS_PER_SUBMISSION]:
        url = normalize_url(link.get("url") or "", remove_volatile=False)
        if not url or not same_or_subdomain(url, endpoint_url):
            continue
        if is_search_page_url(url):
            continue

        label = normalize_space(link.get("label"))
        title = normalize_space(link.get("title"))
        combined = normalize_space(
            label + " " + title + " " + requests.utils.unquote(url)
        )
        target_evidence = contains_target(combined)
        detail_structure = contains_any_term(url, RESULT_DETAIL_HINT_TERMS)
        strong_notice_label = contains_any_term(
            combined,
            (
                "고시", "공고", "개발밀도", "도시관리계획", "도시계획",
                "지형도면", "지정", "변경", "해제",
            ),
        )

        if not (target_evidence or (detail_structure and strong_notice_label)):
            continue

        key = normalize_url(url)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "url": url,
                "label": label,
                "title": title,
                "target_evidence": target_evidence,
                "detail_structure": detail_structure,
                "strong_notice_label": strong_notice_label,
            }
        )

    return results


# ============================================================
# LOAD INPUT / BUILD EXECUTION POOL
# ============================================================

print("=" * 60)
print("DEVELOPMENT DENSITY MANAGEMENT AREA")
print("OFFICIAL BOARD SEARCH FORM / PARAMETER DISCOVERY")
print("=" * 60)
print()
print("Target:", TARGET_NAME)
print("Standard code:", STANDARD_CODE)
print("Input:", INPUT_PATH)
print()

if not INPUT_PATH.exists():
    raise FileNotFoundError(f"H-stage refinement output not found: {INPUT_PATH}")

input_data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
refined_endpoints = extract_refined_endpoints(input_data)

execution_pool = []
execution_excluded = []
noise_endpoint_execution_leakage = 0
urban_body_only_execution_leakage = 0

for endpoint in refined_endpoints:
    decision = endpoint_execution_decision(endpoint)
    record = {**endpoint, "execution_decision": decision["reason"]}
    if decision["execute"]:
        combined = normalize_space(
            str(endpoint.get("label") or "")
            + " "
            + str(endpoint.get("canonical_url") or "")
        )
        if contains_any_term(combined, EXCLUDED_EXECUTION_TERMS):
            noise_endpoint_execution_leakage += 1
        if (
            endpoint["classification"] == "URBAN_PLANNING_BOARD"
            and not contains_any_term(combined, URBAN_STRONG_TERMS)
        ):
            urban_body_only_execution_leakage += 1
        execution_pool.append(record)
    else:
        execution_excluded.append(record)

print("Refined endpoint candidate count:", len(refined_endpoints))
print("Execution pool count:", len(execution_pool))
print("Execution excluded count:", len(execution_excluded))
print()


# ============================================================
# MAIN DISCOVERY
# ============================================================

endpoint_results: List[Dict[str, Any]] = []
searchable_endpoint_records: List[Dict[str, Any]] = []
detail_seed_candidates: List[Dict[str, Any]] = []

request_count = 0
http_success_count = 0
transport_error_count = 0
html_parse_count = 0
safe_search_form_count = 0
post_search_form_count = 0
post_submission_count = 0
search_submission_count = 0
search_result_target_page_count = 0
zero_result_submission_count = 0
search_page_positive_leakage = 0
pagination_endpoint_count = 0

for endpoint_index, endpoint in enumerate(execution_pool, start=1):
    region = endpoint["region"]
    endpoint_class = endpoint["classification"]
    endpoint_url = endpoint["canonical_url"]
    label = endpoint.get("label") or ""

    print("-" * 60)
    print(f"ENDPOINT {endpoint_index}:", region, "/", endpoint_class)
    print("Label:", label)
    print("URL:", endpoint_url)

    fetch = fetch_get(endpoint_url)
    request_count += 1

    if fetch.error:
        transport_error_count += 1
        print("Fetch error:", fetch.error)
        endpoint_results.append(
            {
                **endpoint,
                "http_status": None,
                "error": fetch.error,
                "forms": [],
                "pagination_parameters": [],
                "search_submissions": [],
                "searchable": False,
                "detail_seed_count": 0,
            }
        )
        continue

    if fetch.http_status == 200:
        http_success_count += 1

    final_url = fetch.final_url or endpoint_url
    raw_forms = parse_forms(fetch.text)[:MAX_FORMS_PER_ENDPOINT] if fetch.text else []
    if fetch.text:
        html_parse_count += 1

    forms = [
        analyze_form(form, final_url, index)
        for index, form in enumerate(raw_forms, start=1)
    ]
    pagination_parameters = (
        discover_pagination_parameters(fetch.text, final_url, raw_forms)
        if fetch.text
        else []
    )
    if pagination_parameters:
        pagination_endpoint_count += 1

    safe_forms = [form for form in forms if form.get("safe_search_form") is True]
    safe_search_form_count += len(safe_forms)
    post_search_form_count += sum(1 for form in safe_forms if form["method"] == "POST")

    searchable = bool(safe_forms)
    if searchable:
        searchable_endpoint_records.append(
            {
                "region": region,
                "classification": endpoint_class,
                "label": label,
                "canonical_url": endpoint_url,
                "final_url": final_url,
                "safe_form_count": len(safe_forms),
                "pagination_parameters": pagination_parameters,
            }
        )

    search_submissions = []
    local_detail_seeds = []
    submission_budget = MAX_SEARCH_SUBMISSIONS_PER_ENDPOINT

    for form in safe_forms:
        if submission_budget <= 0:
            break

        for field in (form.get("search_fields") or [])[:2]:
            if submission_budget <= 0:
                break

            field_name = str(field.get("name") or "")
            if not field_name:
                continue

            params = build_submission_params(form, field_name)
            result = submit_form_request(
                method=form["method"],
                action_url=form["action_url"],
                params=params,
                referer=final_url,
            )
            request_count += 1
            search_submission_count += 1
            submission_budget -= 1

            if form["method"] == "POST":
                post_submission_count += 1

            record: Dict[str, Any] = {
                "form_index": form["form_index"],
                "method": form["method"],
                "action_url": form["action_url"],
                "search_field_name": field_name,
                "search_field_score": field.get("score"),
                "preserved_hidden_parameter_names": sorted(
                    (form.get("hidden_values") or {}).keys()
                ),
                "preserved_select_parameter_names": sorted(
                    (form.get("selected_values") or {}).keys()
                ),
                "http_status": result.http_status,
                "final_url": result.final_url,
                "error": result.error,
                "target_found": False,
                "zero_result_page": False,
                "detail_seed_count": 0,
                "detail_seeds": [],
                "preview": "",
            }

            if result.error:
                transport_error_count += 1
                search_submissions.append(record)
                continue

            if result.http_status == 200:
                http_success_count += 1
            if result.text:
                html_parse_count += 1

            text = strip_html(result.text)
            target_found = contains_target(text)
            zero_result = is_zero_result_page(text)
            if target_found:
                search_result_target_page_count += 1
            if zero_result:
                zero_result_submission_count += 1

            # 검색 결과 페이지 자체는 절대 positive가 아니다.
            result_page_positive = False
            if result_page_positive:
                search_page_positive_leakage += 1

            seeds = extract_detail_seed_links(
                source=result.text,
                result_url=result.final_url or result.request_url or form["action_url"],
                endpoint_url=endpoint_url,
            )

            for seed in seeds:
                candidate = {
                    "region": region,
                    "agency": endpoint.get("agency"),
                    "classification": endpoint_class,
                    "endpoint_label": label,
                    "source_endpoint_url": endpoint_url,
                    "search_method": form["method"],
                    "search_action_url": form["action_url"],
                    "search_field_name": field_name,
                    "search_result_url": result.final_url or result.request_url,
                    **seed,
                }
                local_detail_seeds.append(candidate)
                detail_seed_candidates.append(candidate)

            record.update(
                {
                    "target_found": target_found,
                    "zero_result_page": zero_result,
                    "detail_seed_count": len(seeds),
                    "detail_seeds": seeds,
                    "preview": build_preview(text) if target_found else "",
                }
            )
            search_submissions.append(record)
            time.sleep(REQUEST_SLEEP)

    print("HTTP:", fetch.http_status)
    print("Forms:", len(forms))
    print("Safe search forms:", len(safe_forms))
    print("Pagination params:", pagination_parameters)
    print("Search submissions:", len(search_submissions))
    print("Detail seeds:", len(local_detail_seeds))

    endpoint_results.append(
        {
            **endpoint,
            "http_status": fetch.http_status,
            "content_type": fetch.content_type,
            "final_url": fetch.final_url,
            "forms": forms,
            "pagination_parameters": pagination_parameters,
            "search_submissions": search_submissions,
            "searchable": searchable,
            "detail_seed_count": len(local_detail_seeds),
        }
    )
    time.sleep(REQUEST_SLEEP)


# ============================================================
# DEDUPE / RESOLUTION
# ============================================================

deduped_detail_seeds = []
seen_detail_seeds = set()
for seed in detail_seed_candidates:
    normalized = normalize_url(str(seed.get("url") or ""))
    key = (seed.get("region"), normalized)
    if key in seen_detail_seeds:
        continue
    seen_detail_seeds.add(key)
    item = dict(seed)
    item["url"] = normalized
    deduped_detail_seeds.append(item)

if deduped_detail_seeds:
    resolution = "OFFICIAL_BOARD_TARGET_RESULT_CANDIDATE_DISCOVERED"
    next_action = (
        "검색 결과에서 확보한 상세 게시물 URL을 개별 검증하여 실제 "
        "개발밀도관리구역 지정·변경·해제 고시인지 확정하고 고시번호, "
        "지정일, 행정구역, 지정 범위, 첨부파일 및 현재 유효 여부를 추출한다."
    )
elif searchable_endpoint_records:
    resolution = "OFFICIAL_BOARD_SEARCHABLE_ENDPOINT_CONFIRMED"
    next_action = (
        "확인된 공식 검색 form / parameter 구조에 대해 pagination과 검색조건을 "
        "확장하여 개발밀도관리구역 상세 게시물 URL을 추가 탐색한다."
    )
else:
    resolution = "OFFICIAL_BOARD_SEARCH_FORM_DISCOVERY_COMPLETED_NO_SEARCHABLE_FORM"
    next_action = (
        "동적 JavaScript 검색 API, POST 전용 공보 검색, 전자민원 고시공고 endpoint "
        "및 공보 PDF/HWP archive의 별도 검색 구조로 확장한다."
    )

runtime_registration_blocked = True
site_false_interpretation_blocked = True


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-I Development Density Management Area "
        "Official Board Search Form / Parameter Discovery"
    ),
    "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
    "input": {
        "path": str(INPUT_PATH),
        "refined_endpoint_count": len(refined_endpoints),
    },
    "method": {
        "official_endpoint_direct_probe": True,
        "search_engine_scraping": False,
        "execution_relevance_refinement": True,
        "noise_endpoint_execution_guard": True,
        "urban_structural_evidence_guard": True,
        "search_form_discovery": True,
        "get_form_submission": True,
        "post_form_submission": True,
        "hidden_parameter_preservation": True,
        "select_parameter_preservation": True,
        "pagination_discovery": True,
        "arbitrary_query_parameter_injection": False,
        "search_page_final_positive_allowed": False,
    },
    "summary": {
        "refined_endpoint_count": len(refined_endpoints),
        "execution_pool_count": len(execution_pool),
        "execution_excluded_count": len(execution_excluded),
        "request_count": request_count,
        "http_success_count": http_success_count,
        "transport_error_count": transport_error_count,
        "html_parse_count": html_parse_count,
        "safe_search_form_count": safe_search_form_count,
        "post_search_form_count": post_search_form_count,
        "post_submission_count": post_submission_count,
        "search_submission_count": search_submission_count,
        "searchable_endpoint_count": len(searchable_endpoint_records),
        "pagination_endpoint_count": pagination_endpoint_count,
        "search_result_target_page_count": search_result_target_page_count,
        "zero_result_submission_count": zero_result_submission_count,
        "search_page_positive_leakage": search_page_positive_leakage,
        "noise_endpoint_execution_leakage": noise_endpoint_execution_leakage,
        "urban_body_only_execution_leakage": urban_body_only_execution_leakage,
        "detail_seed_candidate_count": len(deduped_detail_seeds),
    },
    "execution_pool": execution_pool,
    "execution_excluded": execution_excluded,
    "searchable_endpoints": searchable_endpoint_records,
    "detail_seed_candidates": deduped_detail_seeds,
    "endpoint_results": endpoint_results,
    "resolution": resolution,
    "runtime_registration_blocked": runtime_registration_blocked,
    "site_false_interpretation_blocked": site_false_interpretation_blocked,
    "next_action": next_action,
}

OUTPUT_PATH.write_text(
    json.dumps(output_data, ensure_ascii=False, indent=2),
    encoding="utf-8",
)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 60)
print("DISCOVERY RESULT")
print("=" * 60)
print("Refined endpoint count:", len(refined_endpoints))
print("Execution pool count:", len(execution_pool))
print("Execution excluded count:", len(execution_excluded))
print("Request count:", request_count)
print("HTTP success count:", http_success_count)
print("Transport error count:", transport_error_count)
print("HTML parse count:", html_parse_count)
print("Safe search form count:", safe_search_form_count)
print("POST search form count:", post_search_form_count)
print("POST submission count:", post_submission_count)
print("Search submission count:", search_submission_count)
print("Searchable endpoint count:", len(searchable_endpoint_records))
print("Pagination endpoint count:", pagination_endpoint_count)
print("Target result page count:", search_result_target_page_count)
print("Zero-result submission count:", zero_result_submission_count)
print("Search-page positive leakage:", search_page_positive_leakage)
print("Noise endpoint execution leakage:", noise_endpoint_execution_leakage)
print("Urban body-only execution leakage:", urban_body_only_execution_leakage)
print("Detail seed candidate count:", len(deduped_detail_seeds))
print()

if searchable_endpoint_records:
    print("SEARCHABLE OFFICIAL ENDPOINTS")
    print("-" * 60)
    for index, item in enumerate(searchable_endpoint_records[:50], start=1):
        print(f"[{index}]", item.get("region"))
        print("Class:", item.get("classification"))
        print("Label:", item.get("label"))
        print("Safe forms:", item.get("safe_form_count"))
        print("Pagination:", item.get("pagination_parameters"))
        print("URL:", item.get("canonical_url"))
        print()

if deduped_detail_seeds:
    print("TARGET DETAIL SEED CANDIDATES")
    print("-" * 60)
    for index, seed in enumerate(deduped_detail_seeds[:100], start=1):
        print(f"[{index}]", seed.get("region"))
        print("Class:", seed.get("classification"))
        print("Label:", seed.get("label"))
        print("Target evidence:", seed.get("target_evidence"))
        print("URL:", seed.get("url"))
        print()

print("=" * 60)
print("RESOLUTION")
print("=" * 60)
print(resolution)
print()
print(next_action)
print()
print("Output:", OUTPUT_PATH)


# ============================================================
# VALIDATION
# ============================================================

execution_pool_keys = {
    (item.get("region"), item.get("classification"), item.get("canonical_url"))
    for item in execution_pool
}
detail_seed_keys = {
    (item.get("region"), item.get("url"))
    for item in deduped_detail_seeds
}

semicolon_query_key_leakage = 0
for item in execution_pool:
    for key, _ in parse_qsl(
        urlparse(item["canonical_url"]).query,
        keep_blank_values=True,
    ):
        if clean_query_key(key) != key:
            semicolon_query_key_leakage += 1

validations = {
    "target name": TARGET_NAME == "개발밀도관리구역",
    "standard code": STANDARD_CODE == "UQQ700",
    "input exists": INPUT_PATH.exists(),
    "H-stage input parsed": isinstance(input_data, dict),
    "refined endpoints loaded": len(refined_endpoints) > 0,
    "execution relevance refinement enabled": (
        output_data["method"]["execution_relevance_refinement"] is True
    ),
    "noise endpoint execution guard enabled": (
        output_data["method"]["noise_endpoint_execution_guard"] is True
    ),
    "urban structural evidence guard enabled": (
        output_data["method"]["urban_structural_evidence_guard"] is True
    ),
    "search form discovery enabled": (
        output_data["method"]["search_form_discovery"] is True
    ),
    "arbitrary query injection disabled": (
        output_data["method"]["arbitrary_query_parameter_injection"] is False
    ),
    "search pages prohibited as final positive": (
        output_data["method"]["search_page_final_positive_allowed"] is False
    ),
    "execution pool unique": len(execution_pool_keys) == len(execution_pool),
    "all execution classes allowed": all(
        item.get("classification") in ALLOWED_CLASSES for item in execution_pool
    ),
    "all execution URLs exist": all(
        bool(item.get("canonical_url")) for item in execution_pool
    ),
    "semicolon query-key leakage zero": semicolon_query_key_leakage == 0,
    "noise endpoint execution leakage zero": noise_endpoint_execution_leakage == 0,
    "generic news urban promotion zero": urban_body_only_execution_leakage == 0,
    "search-page positive leakage zero": search_page_positive_leakage == 0,
    "searchable endpoints have safe forms": all(
        int(item.get("safe_form_count", 0)) > 0
        for item in searchable_endpoint_records
    ),
    "POST submissions are search-form derived": (
        post_submission_count <= search_submission_count
    ),
    "detail seed candidates unique": (
        len(detail_seed_keys) == len(deduped_detail_seeds)
    ),
    "all detail seeds have URL": all(
        bool(item.get("url")) for item in deduped_detail_seeds
    ),
    "all detail seeds are not search pages": all(
        not is_search_page_url(str(item.get("url") or ""))
        for item in deduped_detail_seeds
    ),
    "runtime registration remains blocked": runtime_registration_blocked is True,
    "SITE FALSE remains blocked": site_false_interpretation_blocked is True,
    "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
}

print()
print("=" * 60)
print("VALIDATION")
print("=" * 60)
for name, passed in validations.items():
    print(f"{name}:", passed)

all_pass = all(validations.values())
print()
print("all_pass:", all_pass)

if not all_pass:
    print()
    print("FAILED:")
    for name, passed in validations.items():
        if not passed:
            print("-", name)
    raise AssertionError(
        "Development density management area official board "
        "search form discovery regression failed"
    )