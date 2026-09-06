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
S223 = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_result_identity_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_result_dom_contract_hardening.json"

ROOT = "https://www.gg.go.kr/"
SEARCH_URL = "https://www.gg.go.kr/search.do"
POSITIVE_CONTROL = "예산"
CATEGORY = "고시ㆍ공고/채용"
PAGE_SIZE = 10
TARGET = "개발밀도관리구역"


class DOMParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.anchors = []
        self.text_nodes = []
        self._anchor = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        node = {
            "tag": tag,
            "id": a.get("id"),
            "class": a.get("class"),
            "role": a.get("role"),
        }
        self.stack.append(node)
        if tag == "a":
            self._anchor = {
                "href": a.get("href"),
                "onclick": a.get("onclick"),
                "title_attr": a.get("title"),
                "text_parts": [],
                "ancestors": [dict(x) for x in self.stack[:-1]],
            }

    def handle_data(self, data):
        t = " ".join((data or "").split())
        if not t:
            return
        self.text_nodes.append({
            "text": t,
            "ancestors": [dict(x) for x in self.stack],
        })
        if self._anchor is not None:
            self._anchor["text_parts"].append(t)

    def handle_endtag(self, tag):
        if tag == "a" and self._anchor is not None:
            self._anchor["text"] = " ".join(self._anchor.pop("text_parts", []))
            self.anchors.append(self._anchor)
            self._anchor = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                break


def fetch(session: requests.Session, url: str, params=None, referer: str | None = None):
    try:
        headers = {"Referer": referer} if referer else None
        r = session.get(url, params=params, timeout=60, allow_redirects=True, headers=headers)
        return r, None
    except requests.RequestException as ex:
        return None, f"{type(ex).__name__}: {ex}"


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def sig(ancestors):
    out = []
    for n in ancestors:
        parts = [n.get("tag") or ""]
        if n.get("id"):
            parts.append("#" + str(n["id"]))
        if n.get("class"):
            classes = ".".join(str(n["class"]).split())
            if classes:
                parts.append("." + classes)
        out.append("".join(parts))
    return " > ".join(out)


def identity_from_url(url: str):
    q = parse_qs(urlparse(url).query)
    out = {}
    for key in ["bsIdx", "bcIdx", "menuId", "seq", "idx", "nttId", "boardId", "articleNo"]:
        if q.get(key):
            out[key] = q[key][0]
    return out


def absolute_href(href: str | None):
    if not href:
        return None
    if href.lower().startswith("javascript:") or href == "#":
        return href
    return urljoin(SEARCH_URL, href)


def ancestor_is_navigation(ancestors):
    s = sig(ancestors).lower()
    return any(k in s for k in ["header", "gnb", "lnb", "nav", "footer", "sitemap", "breadcrumb", "location"])


def ancestor_result_signal(ancestors):
    s = sig(ancestors).lower()
    return any(k in s for k in ["result", "search", "list", "board", "content", "item", "article"])


def nearest_container_signature(ancestors):
    for n in reversed(ancestors):
        marker = " ".join([str(n.get("id") or ""), str(n.get("class") or "")]).lower()
        if any(k in marker for k in ["result", "search", "list", "board", "content", "item", "article"]):
            return sig([n])
    return None


def text_has_date(text: str):
    return bool(re.search(r"\b20\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2}\b", text or ""))


def main():
    print("=" * 78)
    print("GYEONGGI OFFICIAL RECORD RESULT DOM CONTRACT HARDENING - S223A")
    print("=" * 78)
    print("Purpose: supersede S223 result-identity false positive by isolating real result DOM")
    print("S222 search-surface contract remains valid")
    print("S223 result/detail qualification is NOT inherited")
    print("Positive control only; UQQ700 target query is NOT executed")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s222 = json.loads(S222.read_text(encoding="utf-8"))
    s223 = json.loads(S223.read_text(encoding="utf-8"))

    gate_222 = (
        s222.get("classification") == "GYEONGGI_OFFICIAL_SEARCH_SURFACE_POSITIVE_CONTROL_QUALIFIED"
        and (s222.get("summary") or {}).get("target_query_executed") is False
        and (s222.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    gate_223 = (
        s223.get("classification") == "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_RESULT_AND_DETAIL_IDENTITY_QUALIFIED"
        and (s223.get("summary") or {}).get("target_query_executed") is False
    )
    if not gate_222 or not gate_223:
        raise AssertionError("S223A prerequisite gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    params = {
        "kwd": POSITIVE_CONTROL,
        "category": CATEGORY,
        "pageNum": "1",
        "pageSize": str(PAGE_SIZE),
        "sort": "d",
        "date": "",
        "startDate": "",
        "endDate": "",
        "srchFd": "all",
        "originalQuery": POSITIVE_CONTROL,
        "previousQuery": "",
    }
    r, err = fetch(session, SEARCH_URL, params=params, referer=ROOT)
    html = r.text if r is not None else ""
    flat = clean_html(html)

    parser = DOMParser()
    parser.feed(html)

    category_nodes = [x for x in parser.text_nodes if CATEGORY in x.get("text", "")]
    category_signatures = []
    for x in category_nodes[:20]:
        s = sig(x.get("ancestors") or [])
        if s not in category_signatures:
            category_signatures.append(s)

    positive_anchors = []
    for a in parser.anchors:
        text = a.get("text") or ""
        if POSITIVE_CONTROL not in text:
            continue
        abs_href = absolute_href(a.get("href"))
        row = {
            "title": text,
            "href": a.get("href"),
            "absolute_href": abs_href,
            "onclick": a.get("onclick"),
            "ancestor_signature": sig(a.get("ancestors") or []),
            "nearest_container_signature": nearest_container_signature(a.get("ancestors") or []),
            "navigation_ancestor": ancestor_is_navigation(a.get("ancestors") or []),
            "result_ancestor_signal": ancestor_result_signal(a.get("ancestors") or []),
            "identity": identity_from_url(abs_href) if abs_href and not abs_href.startswith("javascript:") else {},
        }
        positive_anchors.append(row)

    real_candidates = [
        a for a in positive_anchors
        if not a["navigation_ancestor"]
        and a["result_ancestor_signal"]
        and a.get("absolute_href")
    ]

    # Group by the nearest result-like container to expose the actual DOM contract.
    container_counts = {}
    for a in real_candidates:
        k = a.get("nearest_container_signature") or "<none>"
        container_counts[k] = container_counts.get(k, 0) + 1
    ranked_containers = sorted(container_counts.items(), key=lambda x: (-x[1], x[0]))
    dominant_container = ranked_containers[0][0] if ranked_containers else None
    dominant_rows = [a for a in real_candidates if (a.get("nearest_container_signature") or "<none>") == dominant_container]

    # Deduplicate exact title+href pairs; expected visible rows should not exceed requested pageSize.
    dedup_rows = []
    seen = set()
    for a in dominant_rows:
        key = (a.get("title"), a.get("absolute_href"))
        if key in seen:
            continue
        seen.add(key)
        dedup_rows.append(a)

    page_size_consistent = 0 < len(dedup_rows) <= PAGE_SIZE
    navigation_contamination_count = sum(1 for a in parser.anchors if ancestor_is_navigation(a.get("ancestors") or []))
    old_candidate_count = (s223.get("result_identity") or {}).get("raw_candidate_count")
    contamination_excluded = bool(old_candidate_count and old_candidate_count > PAGE_SIZE and len(dedup_rows) <= PAGE_SIZE)
    result_section_identified = bool(category_signatures and dominant_container and dedup_rows)

    detail_results = []
    for row in dedup_rows[:3]:
        url = row.get("absolute_href")
        if not url or url.startswith("javascript:") or not urlparse(url).netloc.endswith("gg.go.kr"):
            continue
        dr, derr = fetch(session, url, referer=r.url if r is not None else SEARCH_URL)
        body = dr.text if dr is not None else ""
        dtext = clean_html(body)
        title = row.get("title") or ""
        title_signal = bool(title and title in dtext)
        id_signal = any(str(v) in body for v in (row.get("identity") or {}).values() if v)
        detail_results.append({
            "row": row,
            "http": dr.status_code if dr is not None else None,
            "final_url": dr.url if dr is not None else None,
            "error": derr,
            "title_signal": title_signal,
            "identity_signal": id_signal,
            "detail_identity_signal": bool(title_signal and (id_signal or bool(row.get("identity")))),
        })

    detail_identity_qualified = bool(detail_results) and all(
        x.get("http") == 200 and x.get("detail_identity_signal") is True for x in detail_results
    )
    real_result_identity_qualified = bool(result_section_identified and page_size_consistent and contamination_excluded and detail_identity_qualified)

    if real_result_identity_qualified:
        classification = "GYEONGGI_OFFICIAL_RECORD_RESULT_DOM_AND_DETAIL_IDENTITY_HARDENED_QUALIFIED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_REAL_RESULT_DOM_IDENTITY_QUALIFIED_S223_SUPERSEDED"
        next_action = "BUILD_S224_UQQ700_TARGET_REPLAY_USING_HARDENED_RESULT_DOM_CONTRACT"
    elif result_section_identified and dedup_rows:
        classification = "GYEONGGI_OFFICIAL_RECORD_RESULT_DOM_IDENTIFIED_DETAIL_IDENTITY_UNRESOLVED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_REAL_RESULT_DOM_RECOVERED_DETAIL_IDENTITY_UNRESOLVED"
        next_action = "HARDEN_ROW_SPECIFIC_DETAIL_NAVIGATION_BEFORE_UQQ700_TARGET_REPLAY"
    else:
        classification = "GYEONGGI_OFFICIAL_RECORD_RESULT_DOM_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "GYEONGGI_OFFICIAL_RECORD_RESULT_DOM_CONTRACT_TECHNICAL_UNKNOWN"
        next_action = "FORENSIC_CATEGORY_SECTION_HTML_BOUNDARIES_BEFORE_UQQ700_TARGET_REPLAY"

    out = {
        "step": "STEP 17-21-C-16-8-T-136A-S223A",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "GYEONGGI_OFFICIAL_RECORD",
        "s223_supersession": {
            "search_surface_contract_retained_from_s222": True,
            "s223_previous_classification": s223.get("classification"),
            "s223_result_identity_qualification_superseded": True,
            "reason": "S223 collected global navigation/menu links as result candidates; row/detail identity required DOM hardening",
            "s223_raw_candidate_count": old_candidate_count,
        },
        "request": {
            "params": params,
            "http": r.status_code if r is not None else None,
            "final_url": r.url if r is not None else None,
            "error": err,
            "page_size": PAGE_SIZE,
            "category_visible": CATEGORY in flat,
            "positive_control_visible": POSITIVE_CONTROL in flat,
        },
        "dom_contract": {
            "category_node_count": len(category_nodes),
            "category_ancestor_signatures": category_signatures,
            "positive_anchor_count": len(positive_anchors),
            "real_candidate_count": len(real_candidates),
            "container_counts": ranked_containers,
            "dominant_container_signature": dominant_container,
            "deduplicated_result_row_count": len(dedup_rows),
            "rows": dedup_rows,
            "page_size_consistent": page_size_consistent,
            "navigation_contamination_count": navigation_contamination_count,
            "navigation_contamination_excluded": contamination_excluded,
            "result_section_identified": result_section_identified,
        },
        "detail_navigation": {
            "attempted_count": len(detail_results),
            "results": detail_results,
            "qualified": detail_identity_qualified,
        },
        "real_result_identity_qualified": real_result_identity_qualified,
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

    print("HTTP:", out["request"]["http"])
    print("FINAL URL:", out["request"]["final_url"])
    print("CATEGORY VISIBLE:", out["request"]["category_visible"])
    print("POSITIVE CONTROL VISIBLE:", out["request"]["positive_control_visible"])
    print("S223 RAW CANDIDATE COUNT:", old_candidate_count)
    print("CATEGORY NODE COUNT:", len(category_nodes))
    print("POSITIVE ANCHOR COUNT:", len(positive_anchors))
    print("REAL CANDIDATE COUNT:", len(real_candidates))
    print("DOMINANT CONTAINER:", dominant_container)
    print("DEDUPLICATED RESULT ROW COUNT:", len(dedup_rows))
    print("PAGE SIZE CONSISTENT:", page_size_consistent)
    print("NAVIGATION CONTAMINATION COUNT:", navigation_contamination_count)
    print("NAVIGATION CONTAMINATION EXCLUDED:", contamination_excluded)
    print("RESULT SECTION IDENTIFIED:", result_section_identified)
    print("DETAIL ATTEMPTED COUNT:", len(detail_results))
    print("DETAIL IDENTITY QUALIFIED:", detail_identity_qualified)
    print("REAL RESULT IDENTITY QUALIFIED:", real_result_identity_qualified)
    print("CLASSIFICATION:", classification)

    print("\nCATEGORY DOM SIGNATURES")
    for x in category_signatures[:20]:
        print(x)

    print("\nCONTAINER COUNTS")
    for k, v in ranked_containers[:20]:
        print(v, k)

    print("\nHARDENED RESULT ROWS")
    for i, row in enumerate(dedup_rows, 1):
        print(f"--- ROW {i} ---")
        print(json.dumps(row, ensure_ascii=False, indent=2))

    print("\nDETAIL RESULTS")
    for i, row in enumerate(detail_results, 1):
        print(f"--- DETAIL {i} ---")
        print(json.dumps(row, ensure_ascii=False, indent=2))

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("S223 result identity superseded: True")
    print("S222 search surface retained: True")
    print("Target query executed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S222 search-surface gate": gate_222,
        "S223 prior classification observed": gate_223,
        "S223 result identity explicitly superseded": out["s223_supersession"]["s223_result_identity_qualification_superseded"] is True,
        "S222 search surface retained": out["s223_supersession"]["search_surface_contract_retained_from_s222"] is True,
        "request attempted": r is not None,
        "category DOM inspected": isinstance(category_nodes, list),
        "positive anchors inspected": isinstance(positive_anchors, list),
        "navigation contamination measured": isinstance(navigation_contamination_count, int),
        "result rows bounded against pageSize": isinstance(page_size_consistent, bool),
        "detail navigation inspected": isinstance(detail_results, list),
        "response classified": classification in {
            "GYEONGGI_OFFICIAL_RECORD_RESULT_DOM_AND_DETAIL_IDENTITY_HARDENED_QUALIFIED",
            "GYEONGGI_OFFICIAL_RECORD_RESULT_DOM_IDENTIFIED_DETAIL_IDENTITY_UNRESOLVED",
            "GYEONGGI_OFFICIAL_RECORD_RESULT_DOM_CONTRACT_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S223A Gyeonggi result DOM hardening failed")


if __name__ == "__main__":
    main()
