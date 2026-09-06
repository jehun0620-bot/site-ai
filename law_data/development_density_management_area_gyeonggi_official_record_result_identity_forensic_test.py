# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
S222 = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_search_contract_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_result_identity_forensic.json"

ROOT = "https://www.gg.go.kr/"
SEARCH_URL = "https://www.gg.go.kr/search.do"
POSITIVE_CONTROL = "예산"
CATEGORY = "고시ㆍ공고/채용"
LOCAL_GOSI_URL = "https://local.gosi.go.kr/klid/main/main.do"
TARGET = "개발밀도관리구역"


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            a = dict(attrs)
            self._current = {
                "href": a.get("href"),
                "onclick": a.get("onclick"),
                "title": a.get("title"),
                "class": a.get("class"),
                "id": a.get("id"),
                "text_parts": [],
            }

    def handle_data(self, data):
        if self._current is not None and data:
            self._current["text_parts"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._current is not None:
            self._current["text"] = " ".join(" ".join(self._current.pop("text_parts", [])).split())
            self.links.append(self._current)
            self._current = None


def fetch(session: requests.Session, url: str, params=None, referer: str | None = None):
    try:
        headers = {"Referer": referer} if referer else None
        r = session.get(url, params=params, timeout=60, allow_redirects=True, headers=headers)
        return r, None
    except requests.RequestException as ex:
        return None, f"{type(ex).__name__}: {ex}"


def parse_links(html: str):
    p = LinkParser()
    p.feed(html or "")
    return p.links


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def extract_category_count(text: str, label: str):
    flat = " ".join((text or "").split())
    for pat in [
        rf"{re.escape(label)}\s*\(?\s*([0-9,]+)\s*건\s*\)?",
        rf"{re.escape(label)}\s*\(?\s*([0-9,]+)\s*\)?",
    ]:
        m = re.search(pat, flat)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except Exception:
                pass
    return None


def is_resultish(link: dict) -> bool:
    href = str(link.get("href") or "")
    onclick = str(link.get("onclick") or "")
    text = str(link.get("text") or "")
    blob = (href + " " + onclick).lower()
    return bool(text and (
        "bbs/board.do" in blob
        or "bcidx" in blob
        or "bsidx" in blob
        or "menuid" in blob
        or "view" in blob
        or "detail" in blob
        or "javascript:" in blob
    ))


def identity_from_url(url: str):
    q = parse_qs(urlparse(url).query)
    out = {}
    for key in ["bsIdx", "bcIdx", "menuId", "seq", "idx", "page", "pageIndex", "nttId", "boardId"]:
        vals = q.get(key)
        if vals:
            out[key] = vals[0]
    return out


def absolutize(href: str):
    if not href:
        return None
    if href.lower().startswith("javascript:") or href == "#":
        return href
    return urljoin(SEARCH_URL, href)


def detail_identity_signal(html: str, candidate: dict):
    text = clean_html(html)
    title = candidate.get("title") or ""
    title_token = " ".join(title.split())[:40]
    title_signal = bool(title_token and title_token in text)
    identity = candidate.get("identity") or {}
    identity_signal = False
    for val in identity.values():
        if val and str(val) in (html or ""):
            identity_signal = True
            break
    return title_signal or identity_signal, title_signal, identity_signal


def main():
    print("=" * 78)
    print("GYEONGGI OFFICIAL RECORD RESULT IDENTITY FORENSIC - S223")
    print("=" * 78)
    print("Purpose: qualify positive-control category/result/detail identity before UQQ700 replay")
    print("Positive control only; target query is NOT executed")
    print("Search hit != legal fact")
    print("Search no-hit != legal absence")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s222 = json.loads(S222.read_text(encoding="utf-8"))
    gate_222 = (
        s222.get("classification") == "GYEONGGI_OFFICIAL_SEARCH_SURFACE_POSITIVE_CONTROL_QUALIFIED"
        and (s222.get("summary") or {}).get("target_query_executed") is False
        and (s222.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not gate_222:
        raise AssertionError("S223 prerequisite S222 gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    payload = {
        "kwd": POSITIVE_CONTROL,
        "category": CATEGORY,
        "pageNum": "1",
        "pageSize": "10",
        "sort": "d",
        "date": "",
        "startDate": "",
        "endDate": "",
        "srchFd": "all",
        "originalQuery": POSITIVE_CONTROL,
        "previousQuery": "",
    }
    result, result_error = fetch(session, SEARCH_URL, params=payload, referer=ROOT)
    html = result.text if result is not None else ""
    text = clean_html(html)
    links = parse_links(html)

    category_label_visible = CATEGORY in text
    positive_visible = POSITIVE_CONTROL in text
    category_count = extract_category_count(text, CATEGORY)
    exact_params_visible = bool(result is not None and all(k in result.url for k in ["kwd=", "category=", "pageNum=", "pageSize=", "sort=", "srchFd="]))

    raw_candidates = []
    seen = set()
    for link in links:
        if not is_resultish(link):
            continue
        href = str(link.get("href") or "")
        abs_href = absolutize(href)
        onclick = str(link.get("onclick") or "")
        title = str(link.get("text") or "").strip()
        if not title:
            continue
        # Keep only likely search-result links. Positive-control result pages contain many global nav links,
        # so require query/result identity hints in href/onclick or positive term in visible title.
        blob = (href + " " + onclick)
        if POSITIVE_CONTROL not in title and not any(k in blob for k in ["bcIdx", "bsIdx", "menuId", "search", "view", "detail"]):
            continue
        identity = identity_from_url(abs_href) if abs_href and not abs_href.startswith("javascript:") else {}
        key = json.dumps({"href": abs_href, "onclick": onclick, "title": title}, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        raw_candidates.append({
            "title": title,
            "href": href,
            "absolute_href": abs_href,
            "onclick": onclick,
            "identity": identity,
        })

    # Prefer concrete GET-able gg.go.kr detail rows with board/detail identity.
    gettable = [
        c for c in raw_candidates
        if c.get("absolute_href")
        and not str(c.get("absolute_href")).startswith("javascript:")
        and urlparse(str(c.get("absolute_href"))).netloc.endswith("gg.go.kr")
        and (c.get("identity") or {})
    ]
    detail_candidates = gettable[:5]
    detail_results = []
    for c in detail_candidates:
        r, err = fetch(session, str(c["absolute_href"]), referer=result.url if result is not None else SEARCH_URL)
        body = r.text if r is not None else ""
        signal, title_signal, identity_signal = detail_identity_signal(body, c)
        detail_results.append({
            "candidate": c,
            "http": r.status_code if r is not None else None,
            "final_url": r.url if r is not None else None,
            "error": err,
            "title_signal": title_signal,
            "identity_signal": identity_signal,
            "detail_identity_signal": signal,
        })

    detail_navigation_qualified = any(
        d.get("http") == 200 and d.get("detail_identity_signal") is True
        for d in detail_results
    )
    result_identity_signal = len(raw_candidates) > 0
    category_replay_qualified = bool(
        result is not None
        and result.status_code == 200
        and positive_visible
        and category_label_visible
        and exact_params_visible
    )

    local_gosi_recorded = LOCAL_GOSI_URL in (s222.get("surface") or {}).get("interesting_links", [])

    if category_replay_qualified and result_identity_signal and detail_navigation_qualified:
        classification = "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_RESULT_AND_DETAIL_IDENTITY_QUALIFIED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_CATEGORY_RESULT_DETAIL_IDENTITY_QUALIFIED"
        next_action = "BUILD_S224_UQQ700_TARGET_REPLAY_WITHOUT_NEGATIVE_OR_SITE_INFERENCE"
    elif category_replay_qualified and result_identity_signal:
        classification = "GYEONGGI_OFFICIAL_RECORD_RESULT_IDENTITY_PARTIAL_DETAIL_UNRESOLVED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_RESULT_IDENTITY_RECOVERED_DETAIL_NAVIGATION_UNRESOLVED"
        next_action = "FORENSIC_RESULT_LINK_JS_OR_DETAIL_CONTRACT_BEFORE_UQQ700_TARGET_REPLAY"
    elif category_replay_qualified:
        classification = "GYEONGGI_OFFICIAL_RECORD_CATEGORY_REPLAY_QUALIFIED_RESULT_IDENTITY_UNRESOLVED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_CATEGORY_REPLAY_QUALIFIED_RESULT_IDENTITY_UNRESOLVED"
        next_action = "FORENSIC_RESULT_ROW_HTML_STRUCTURE_BEFORE_UQQ700_TARGET_REPLAY"
    else:
        classification = "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_CATEGORY_REPLAY_TECHNICAL_UNKNOWN"
        semantic = "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_CATEGORY_REPLAY_TECHNICAL_UNKNOWN"
        next_action = "RESOLVE_CATEGORY_PARAMETER_CONTRACT_BEFORE_UQQ700_TARGET_REPLAY"

    out = {
        "step": "STEP 17-21-C-16-8-T-136-S223",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "GYEONGGI_OFFICIAL_RECORD",
        "positive_control": {
            "term": POSITIVE_CONTROL,
            "category": CATEGORY,
            "request_params": payload,
            "http": result.status_code if result is not None else None,
            "final_url": result.url if result is not None else None,
            "error": result_error,
            "term_visible": positive_visible,
            "category_label_visible": category_label_visible,
            "category_count": category_count,
            "exact_params_visible": exact_params_visible,
            "category_replay_qualified": category_replay_qualified,
        },
        "result_identity": {
            "raw_candidate_count": len(raw_candidates),
            "raw_candidates": raw_candidates,
            "result_identity_signal": result_identity_signal,
        },
        "detail_navigation": {
            "attempted_count": len(detail_results),
            "results": detail_results,
            "qualified": detail_navigation_qualified,
        },
        "downstream_official_source_candidate": {
            "url": LOCAL_GOSI_URL,
            "recorded_from_s222": local_gosi_recorded,
            "target_query_executed": False,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "positive_control_only": True,
            "target_query_executed": False,
            "search_hit_equals_legal_fact": False,
            "search_no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "official_designation_identity_verified": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("POSITIVE CONTROL HTTP:", out["positive_control"]["http"])
    print("POSITIVE CONTROL FINAL URL:", out["positive_control"]["final_url"])
    print("CATEGORY:", CATEGORY)
    print("CATEGORY LABEL VISIBLE:", category_label_visible)
    print("POSITIVE TERM VISIBLE:", positive_visible)
    print("CATEGORY COUNT:", category_count)
    print("EXACT PARAMS VISIBLE:", exact_params_visible)
    print("CATEGORY REPLAY QUALIFIED:", category_replay_qualified)
    print("RAW RESULT CANDIDATE COUNT:", len(raw_candidates))
    print("RESULT IDENTITY SIGNAL:", result_identity_signal)
    print("DETAIL ATTEMPTED COUNT:", len(detail_results))
    print("DETAIL NAVIGATION QUALIFIED:", detail_navigation_qualified)
    print("LOCAL.GOSI RECORDED:", local_gosi_recorded)
    print("CLASSIFICATION:", classification)

    print("\nRESULT CANDIDATES")
    for i, c in enumerate(raw_candidates[:20], 1):
        print(f"--- RESULT {i} ---")
        print(json.dumps(c, ensure_ascii=False, indent=2))

    print("\nDETAIL RESULTS")
    for i, d in enumerate(detail_results, 1):
        print(f"--- DETAIL {i} ---")
        print(json.dumps(d, ensure_ascii=False, indent=2))

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Target query executed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S222 positive-control gate": gate_222,
        "positive-control category request attempted": result is not None,
        "category label checked": isinstance(category_label_visible, bool),
        "positive term checked": isinstance(positive_visible, bool),
        "exact parameter contract checked": isinstance(exact_params_visible, bool),
        "result identity inspected": isinstance(raw_candidates, list),
        "detail navigation inspected": isinstance(detail_results, list),
        "local.gosi downstream candidate recorded state checked": isinstance(local_gosi_recorded, bool),
        "response classified": classification in {
            "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_RESULT_AND_DETAIL_IDENTITY_QUALIFIED",
            "GYEONGGI_OFFICIAL_RECORD_RESULT_IDENTITY_PARTIAL_DETAIL_UNRESOLVED",
            "GYEONGGI_OFFICIAL_RECORD_CATEGORY_REPLAY_QUALIFIED_RESULT_IDENTITY_UNRESOLVED",
            "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_CATEGORY_REPLAY_TECHNICAL_UNKNOWN",
        },
        "positive control only": out["summary"]["positive_control_only"] is True,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "search hit not legal fact": out["summary"]["search_hit_equals_legal_fact"] is False,
        "search no-hit not legal absence": out["summary"]["search_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "SITE FALSE inference disabled": not out["summary"]["site_false_inference_allowed"],
        "designation identity not promoted": out["official_designation_identity_verified"] is False,
        "current validity not promoted": out["current_validity_verified"] is False,
        "site inclusion not promoted": out["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": not out["site_positive_allowed"] and not out["site_negative_allowed"],
        "runtime registration blocked": not out["runtime_registration_allowed"],
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S223 Gyeonggi official record result identity forensic failed")


if __name__ == "__main__":
    main()
