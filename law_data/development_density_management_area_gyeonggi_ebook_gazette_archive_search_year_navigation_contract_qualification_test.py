# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_gyeonggi_ebook_gazette_archive_search_year_navigation_contract_qualification.json"
S230E = OUT_DIR / "development_density_management_area_gyeonggi_historical_local_gazette_notice_archive_alternate_entry_qualification.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_ID = "GG_EBOOK_GAZETTE_ARCHIVE"
ENTRY_URL = "https://ebook.gg.go.kr/home/list.php?code=21"
EXPECTED_HOST = "ebook.gg.go.kr"
TIMEOUT = 20

SAFE_POSITIVE_TERMS = ["경기도보", "도보"]
YEAR_RE = re.compile(r"(?:19|20)\d{2}")
SEARCH_FIELD_HINTS = (
    "search", "keyword", "query", "word", "find", "title", "subject", "sch", "srch", "key", "text", "sword",
)
YEAR_FIELD_HINTS = ("year", "yyyy", "date", "from", "to", "start", "end", "sdate", "edate")
DETAIL_HINTS = ("view", "detail", "book", "viewer", "read", "content", "contents", "idx", "no", "seq", "id")
BINARY_HINTS = ("pdf", "download", "file", "attach", "down")


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def compact_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or " ").strip()


def fetch(session: requests.Session, url: str, method: str = "GET", params=None, data=None):
    try:
        r = session.request(method, url, params=params, data=data, timeout=TIMEOUT, allow_redirects=True)
        return {
            "ok": True,
            "status_code": r.status_code,
            "url": r.url,
            "content_type": r.headers.get("Content-Type", ""),
            "text": r.text,
            "body_size": len(r.content),
        }
    except Exception as e:
        return {"ok": False, "error": repr(e), "status_code": None, "url": url, "text": "", "body_size": 0, "content_type": ""}


def form_contracts(base_url: str, html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for idx, form in enumerate(soup.find_all("form"), 1):
        method = (form.get("method") or "GET").upper()
        action = urljoin(base_url, form.get("action") or base_url)
        fields = []
        for el in form.find_all(["input", "select", "textarea", "button"]):
            name = el.get("name")
            if not name:
                continue
            typ = (el.get("type") or el.name or "").lower()
            val = el.get("value") or ""
            fields.append({"name": name, "type": typ, "value": val})
        search_fields = []
        year_fields = []
        for f in fields:
            low = f["name"].lower()
            if any(h in low for h in SEARCH_FIELD_HINTS):
                search_fields.append(f["name"])
            if any(h in low for h in YEAR_FIELD_HINTS):
                year_fields.append(f["name"])
        out.append({
            "form_index": idx,
            "method": method,
            "action": action,
            "fields": fields,
            "search_field_candidates": sorted(set(search_fields)),
            "year_field_candidates": sorted(set(year_fields)),
            "form_text": compact_text(form.get_text(" ", strip=True))[:500],
        })
    return out


def link_inventory(base_url: str, html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    years = set()
    detail = []
    binary = []
    pagination = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a.get("href"))
        text = compact_text(a.get_text(" ", strip=True))
        raw = (a.get("href") or "")
        row = {"text": text[:200], "href": href}
        rows.append(row)
        for y in YEAR_RE.findall(text + " " + href):
            years.add(y)
        low = (text + " " + href).lower()
        if any(h in low for h in DETAIL_HINTS):
            detail.append(row)
        if any(h in low for h in BINARY_HINTS):
            binary.append(row)
        q = parse_qs(urlparse(href).query)
        if any(k.lower() in {"page", "p", "pg", "page_no", "pageno", "start"} for k in q):
            pagination.append(row)
        elif re.search(r"(?:page|paging|goPage)\s*\(?\s*\d+", raw, re.I):
            pagination.append(row)
    return {
        "link_count": len(rows),
        "year_tokens": sorted(years),
        "detail_link_sample": detail[:30],
        "binary_link_sample": binary[:30],
        "pagination_link_sample": pagination[:30],
        "detail_link_count": len(detail),
        "binary_link_count": len(binary),
        "pagination_link_count": len(pagination),
    }


def infer_list_records(base_url: str, html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    seen = set()
    for a in soup.find_all("a", href=True):
        text = compact_text(a.get_text(" ", strip=True))
        href = urljoin(base_url, a.get("href"))
        low = href.lower()
        if not text:
            continue
        if any(tok in low for tok in ["view", "detail", "book", "viewer", "idx=", "seq=", "no=", "id="]):
            key = (text, href)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({"title": text[:250], "url": href})
    return candidates[:100]


def make_payload(contract: dict, query_field: str, query: str) -> dict:
    payload = {}
    for f in contract.get("fields", []):
        name = f["name"]
        typ = f.get("type", "")
        if typ in {"submit", "button", "image", "reset", "file"}:
            continue
        payload[name] = f.get("value", "")
    payload[query_field] = query
    return payload


def main() -> None:
    print("=" * 78)
    print("GYEONGGI EBOOK GAZETTE SEARCH / YEAR NAVIGATION CONTRACT QUALIFICATION - S230F")
    print("=" * 78)
    print("Purpose: recover ebook.gg.go.kr search/year/detail contract before UQQ700 target search")
    print("UQQ700 target search: DISABLED")
    print("Positive control uses only generic gazette terms")
    print("Search success != designation/current validity/site inclusion")
    print("Search failure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    s230e = load_json(S230E)
    s230e_loaded = isinstance(s230e, dict)

    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Referer": "https://ebook.gg.go.kr/",
    })

    entry = fetch(sess, ENTRY_URL)
    html = entry.get("text", "")
    host_ok = urlparse(entry.get("url", ENTRY_URL)).hostname == EXPECTED_HOST
    http_ok = entry.get("status_code") == 200
    official_signal = any(x in html for x in ["경기도", "경기도보", "Gyeonggi", "경기"])

    forms = form_contracts(entry.get("url", ENTRY_URL), html) if http_ok else []
    links = link_inventory(entry.get("url", ENTRY_URL), html) if http_ok else {
        "link_count": 0, "year_tokens": [], "detail_link_sample": [], "binary_link_sample": [],
        "pagination_link_sample": [], "detail_link_count": 0, "binary_link_count": 0, "pagination_link_count": 0,
    }
    list_records = infer_list_records(entry.get("url", ENTRY_URL), html) if http_ok else []

    candidate_contracts = []
    for f in forms:
        for qf in f.get("search_field_candidates", []):
            candidate_contracts.append({**f, "query_field": qf})

    positive_controls = []
    # Bounded: at most two generic terms per discovered query contract, but cap total requests.
    request_budget = 4
    for c in candidate_contracts[:2]:
        for term in SAFE_POSITIVE_TERMS:
            if request_budget <= 0:
                break
            payload = make_payload(c, c["query_field"], term)
            r = fetch(sess, c["action"], method=c["method"], params=payload if c["method"] == "GET" else None,
                      data=payload if c["method"] != "GET" else None)
            body = r.get("text", "")
            query_echo = term in body
            records = infer_list_records(r.get("url", c["action"]), body) if r.get("status_code") == 200 else []
            result_signal_count = sum(1 for row in records if term in row.get("title", ""))
            positive_controls.append({
                "form_index": c["form_index"],
                "method": c["method"],
                "action": c["action"],
                "query_field": c["query_field"],
                "term": term,
                "status_code": r.get("status_code"),
                "final_url": r.get("url"),
                "query_echo": query_echo,
                "candidate_record_count": len(records),
                "title_result_signal_count": result_signal_count,
                "qualified_positive_control": r.get("status_code") == 200 and (len(records) > 0 or result_signal_count > 0),
            })
            request_budget -= 1

    search_contract_qualified = any(x["qualified_positive_control"] for x in positive_controls)
    discovered_search_surface = len(candidate_contracts) > 0
    year_navigation_signal = bool(links["year_tokens"] or any(f.get("year_field_candidates") for f in forms))
    detail_surface = bool(links["detail_link_count"] or list_records)
    pagination_surface = bool(links["pagination_link_count"])
    binary_surface = bool(links["binary_link_count"])

    contract_qualified = (
        http_ok and host_ok and official_signal and discovered_search_surface
        and (search_contract_qualified or detail_surface)
    )

    if contract_qualified:
        classification = "GYEONGGI_EBOOK_GAZETTE_SEARCH_YEAR_NAVIGATION_CONTRACT_QUALIFIED"
        semantic = "EBOOK_GG_GO_KR_EXPOSES_A_DISTINCT_GAZETTE_ARCHIVE_SEARCH_OR_LIST_CONTRACT_WITH_DETAIL_NAVIGATION_BEFORE_ANY_UQQ700_QUERY"
        next_action = "RUN_BOUNDED_UQQ700_EXACT_VARIANT_WEAK_SEARCH_ONLY_THROUGH_THE_QUALIFIED_EBOOK_ARCHIVE_CONTRACT_AND_HARDEN_QUERY_ECHO_VS_RESULT_ROWS"
    elif http_ok and discovered_search_surface:
        classification = "GYEONGGI_EBOOK_GAZETTE_SEARCH_CONTRACT_PARTIAL_TECHNICAL_UNKNOWN"
        semantic = "SEARCH_SURFACE_WAS_DISCOVERED_BUT_POSITIVE_CONTROL_OR_DETAIL_NAVIGATION_DID_NOT_FULLY_QUALIFY"
        next_action = "HARDEN_THE_DISCOVERED_FORM_OR_LIST_DETAIL_CONTRACT_WITHOUT_RUNNING_UQQ700_AND_WITHOUT_NEGATIVE_INFERENCE"
    else:
        classification = "GYEONGGI_EBOOK_GAZETTE_ENTRY_REACHABLE_SEARCH_CONTRACT_NOT_QUALIFIED"
        semantic = "EBOOK_ENTRY_DID_NOT_YET_EXPOSE_A_QUALIFIED_SEARCH_CONTRACT_IN_THIS_PROBE"
        next_action = "FALL_BACK_TO_THE_OTHER_S230E_QUALIFIED_GYEONGGI_GAZETTE_ENTRY_OR_RECOVER_EBOOK_NAVIGATION_CONTRACT_WITHOUT_UQQ700_QUERY"

    out = {
        "step": "S230F",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_id": SOURCE_ID,
        "entry_url": ENTRY_URL,
        "s230e_loaded": s230e_loaded,
        "uqq700_target_search_executed": False,
        "entry": {
            "http_status": entry.get("status_code"),
            "final_url": entry.get("url"),
            "body_size": entry.get("body_size"),
            "host_ok": host_ok,
            "official_signal": official_signal,
        },
        "forms": forms,
        "candidate_search_contracts": candidate_contracts,
        "positive_controls": positive_controls,
        "link_inventory": links,
        "list_record_sample": list_records[:30],
        "signals": {
            "discovered_search_surface": discovered_search_surface,
            "search_contract_qualified": search_contract_qualified,
            "year_navigation_signal": year_navigation_signal,
            "detail_surface": detail_surface,
            "pagination_surface": pagination_surface,
            "binary_surface": binary_surface,
            "contract_qualified": contract_qualified,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "search_success_equals_designation": False,
            "search_success_equals_current_validity": False,
            "search_success_equals_site_inclusion": False,
            "search_failure_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("CONTRACT DISCOVERY")
    print("=" * 78)
    print(f"ENTRY HTTP: {entry.get('status_code')}")
    print(f"FINAL URL: {entry.get('url')}")
    print(f"FORM COUNT: {len(forms)}")
    print(f"CANDIDATE SEARCH CONTRACT COUNT: {len(candidate_contracts)}")
    print(f"POSITIVE CONTROL REQUEST COUNT: {len(positive_controls)}")
    print(f"QUALIFIED POSITIVE CONTROL COUNT: {sum(1 for x in positive_controls if x['qualified_positive_control'])}")
    print(f"YEAR NAVIGATION SIGNAL: {year_navigation_signal}")
    print(f"DETAIL SURFACE: {detail_surface}")
    print(f"PAGINATION SURFACE: {pagination_surface}")
    print(f"BINARY SURFACE: {binary_surface}")
    print(f"CONTRACT QUALIFIED: {contract_qualified}")
    for c in candidate_contracts[:10]:
        print(json.dumps({
            "form_index": c["form_index"], "method": c["method"], "action": c["action"],
            "query_field": c["query_field"], "year_fields": c.get("year_field_candidates", []),
            "field_names": [x["name"] for x in c.get("fields", [])],
        }, ensure_ascii=False))
    for p in positive_controls:
        print(json.dumps(p, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("UQQ700 target search executed: False")
    print("Search failure == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S230E loaded": s230e_loaded,
        "no UQQ700 target search": out["uqq700_target_search_executed"] is False,
        "entry host is ebook gg": host_ok,
        "generic positive controls only": all(x["term"] in SAFE_POSITIVE_TERMS for x in positive_controls),
        "positive control request bounded": len(positive_controls) <= 4,
        "search success not designation": out["summary"]["search_success_equals_designation"] is False,
        "search success not validity": out["summary"]["search_success_equals_current_validity"] is False,
        "search success not site inclusion": out["summary"]["search_success_equals_site_inclusion"] is False,
        "search failure not legal absence": out["summary"]["search_failure_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": bool(classification),
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for k, v in validation.items():
        print(f"{k}: {v}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")
    if not all(validation.values()):
        raise AssertionError("S230F validation failed")


if __name__ == "__main__":
    main()
