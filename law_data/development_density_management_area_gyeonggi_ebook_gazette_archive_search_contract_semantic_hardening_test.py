# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_S230F = OUT_DIR / "development_density_management_area_gyeonggi_ebook_gazette_archive_search_year_navigation_contract_qualification.json"
OUT = OUT_DIR / "development_density_management_area_gyeonggi_ebook_gazette_archive_search_contract_semantic_hardening.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
ENTRY = "https://ebook.gg.go.kr/home/list.php?code=21"
HOST = "ebook.gg.go.kr"

GENERIC_TERMS = ["경기도보", "도보"]
TIMEOUT = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Referer": ENTRY,
}

DETAIL_HINT_RE = re.compile(r"(?:view|detail|book|ebook|contents|content|reader|viewer|idx|no|seq|uid|serial)", re.I)
PAGE_HINT_RE = re.compile(r"(?:page|pageno|page_no|nowpage|curpage|pg|start)", re.I)
BINARY_HINT_RE = re.compile(r"(?:\.pdf(?:$|\?)|download|file|attach|ebook|viewer)", re.I)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def fetch(session: requests.Session, url: str, params=None):
    try:
        r = session.get(url, params=params, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True)
        return r
    except requests.RequestException:
        return None


def form_descriptor(form, base_url: str):
    method = (form.get("method") or "GET").upper()
    action = urljoin(base_url, form.get("action") or base_url)
    controls = []
    for tag in form.find_all(["input", "select", "textarea", "button"]):
        name = tag.get("name")
        if not name:
            continue
        item = {
            "tag": tag.name,
            "name": name,
            "type": tag.get("type"),
            "value": tag.get("value", ""),
            "options": [],
        }
        if tag.name == "select":
            item["options"] = [
                {"value": o.get("value", ""), "text": normalize_space(o.get_text(" ", strip=True))}
                for o in tag.find_all("option")
            ]
        controls.append(item)
    return {"method": method, "action": action, "controls": controls}


def likely_keyword_fields(desc: dict):
    out = []
    for c in desc["controls"]:
        n = c["name"].lower()
        if c["tag"] == "input" and (c.get("type") or "text").lower() in {"text", "search", ""}:
            if any(k in n for k in ["search", "query", "keyword", "key", "word", "val"]):
                out.append(c["name"])
    return sorted(set(out))


def default_payload(desc: dict):
    payload = {}
    for c in desc["controls"]:
        name = c["name"]
        if c["tag"] == "select":
            selected = None
            for o in c["options"]:
                if o["value"]:
                    selected = o["value"]
                    break
            payload[name] = selected or ""
        elif c["tag"] == "input":
            t = (c.get("type") or "text").lower()
            if t in {"submit", "button", "image", "reset"}:
                continue
            payload[name] = c.get("value", "") or ""
        else:
            payload[name] = c.get("value", "") or ""
    return payload


def canonical_rows(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    seen = set()
    for a in soup.find_all("a", href=True):
        text = normalize_space(a.get_text(" ", strip=True))
        href = urljoin(base_url, a.get("href"))
        if not text:
            continue
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)
        detailish = (
            DETAIL_HINT_RE.search(href) is not None
            or any(DETAIL_HINT_RE.search(k or "") for k in qs.keys())
            or "경기도보" in text
            or re.search(r"\b20\d{2}\b", text) is not None
        )
        if not detailish:
            continue
        key = (text, href)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"title": text, "url": href})
    return rows


def signature(rows):
    return sorted({f"{r['title']}|{r['url']}" for r in rows})


def discover_pagination(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")
    vals = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        q = parse_qs(urlparse(href).query)
        for k, v in q.items():
            if PAGE_HINT_RE.search(k):
                vals.append({"parameter": k, "values": v[:3], "url": href})
    for tag in soup.find_all(attrs={"onclick": True}):
        onclick = tag.get("onclick") or ""
        if re.search(r"page|paging|movePage|goPage", onclick, re.I):
            vals.append({"onclick": onclick[:300]})
    return vals[:50]


def discover_detail_and_binary(session, rows):
    detail_samples = []
    binary_samples = []
    for row in rows[:8]:
        r = fetch(session, row["url"])
        if not r or r.status_code != 200:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = urljoin(r.url, a["href"])
            text = normalize_space(a.get_text(" ", strip=True))
            if BINARY_HINT_RE.search(href) or BINARY_HINT_RE.search(text):
                links.append({"text": text, "url": href})
        detail_samples.append({
            "source_title": row["title"],
            "detail_url": r.url,
            "http": r.status_code,
            "link_count": len(links),
            "links": links[:15],
        })
        for x in links:
            if x not in binary_samples:
                binary_samples.append(x)
    return detail_samples, binary_samples[:50]


def main():
    print("=" * 78)
    print("GYEONGGI EBOOK GAZETTE SEARCH CONTRACT SEMANTIC HARDENING - S230F HARDENED")
    print("=" * 78)
    print("Purpose: verify field semantics and real result-set changes before any UQQ700 query")
    print("UQQ700 target search: DISABLED")
    print("Generic positive controls only")
    print("Search result change != designation/current validity/site inclusion")
    print("Search failure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    prev = load_json(IN_S230F)
    session = requests.Session()
    entry = fetch(session, ENTRY)
    if entry is None:
        raise RuntimeError("ebook entry request failed")

    soup = BeautifulSoup(entry.text, "html.parser")
    forms = soup.find_all("form")
    descriptors = [form_descriptor(f, entry.url) for f in forms]

    baseline_rows = canonical_rows(entry.text, entry.url)
    baseline_sig = signature(baseline_rows)

    experiments = []
    candidate_contracts = []

    for idx, desc in enumerate(descriptors, 1):
        if desc["method"] != "GET":
            continue
        fields = likely_keyword_fields(desc)
        base_payload = default_payload(desc)
        for field in fields:
            for term in GENERIC_TERMS:
                payload = dict(base_payload)
                # Blank only candidate text/search fields, then populate exactly one.
                for f in fields:
                    payload[f] = ""
                payload[field] = term
                r = fetch(session, desc["action"], params=payload)
                if r is None:
                    experiments.append({
                        "form_index": idx, "query_field": field, "term": term,
                        "http": None, "result_count": None, "changed_from_baseline": False,
                    })
                    continue
                rows = canonical_rows(r.text, r.url)
                sig = signature(rows)
                changed = sig != baseline_sig
                query_echo = term in normalize_space(BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True))
                experiments.append({
                    "form_index": idx,
                    "method": desc["method"],
                    "action": desc["action"],
                    "query_field": field,
                    "term": term,
                    "http": r.status_code,
                    "final_url": r.url,
                    "query_echo": query_echo,
                    "result_count": len(rows),
                    "baseline_count": len(baseline_rows),
                    "changed_from_baseline": changed,
                    "same_as_baseline": not changed,
                    "sample_titles": [x["title"] for x in rows[:8]],
                })

    by_field = {}
    for e in experiments:
        f = e["query_field"]
        b = by_field.setdefault(f, {"runs": 0, "http_200": 0, "changed": 0, "counts": []})
        b["runs"] += 1
        b["http_200"] += int(e.get("http") == 200)
        b["changed"] += int(e.get("changed_from_baseline") is True)
        if isinstance(e.get("result_count"), int):
            b["counts"].append(e["result_count"])

    for field, stats in sorted(by_field.items()):
        role = "UNKNOWN"
        if stats["runs"] and stats["http_200"] == stats["runs"] and stats["changed"] == stats["runs"]:
            role = "LIKELY_KEYWORD_FIELD"
        elif stats["runs"] and stats["changed"] == 0:
            role = "LIKELY_CONTROL_OR_INERT_FIELD"
        candidate_contracts.append({
            "query_field": field,
            "runs": stats["runs"],
            "http_200_count": stats["http_200"],
            "changed_result_set_count": stats["changed"],
            "result_counts": stats["counts"],
            "semantic_role": role,
        })

    likely_fields = [x["query_field"] for x in candidate_contracts if x["semantic_role"] == "LIKELY_KEYWORD_FIELD"]

    pagination = discover_pagination(entry.text, entry.url)
    detail_samples, binary_samples = discover_detail_and_binary(session, baseline_rows)

    contract_qualified = len(likely_fields) == 1
    if contract_qualified:
        classification = "GYEONGGI_EBOOK_GAZETTE_SEARCH_CONTRACT_SEMANTICALLY_HARDENED_QUALIFIED"
        semantic = "EXACTLY_ONE_SEARCH_FIELD_CHANGED_CANONICAL_RESULT_SETS_FOR_ALL_GENERIC_POSITIVE_CONTROLS"
        next_action = "RUN_BOUNDED_UQQ700_TARGET_SEARCH_ONLY_THROUGH_THE_HARDENED_QUERY_FIELD_WITH_ECHO_AND_RESULT_ROW_SEPARATION"
    else:
        classification = "GYEONGGI_EBOOK_GAZETTE_SEARCH_CONTRACT_SEMANTIC_HARDENING_TECHNICAL_UNKNOWN"
        semantic = "FIELD_ROLE_REMAINS_AMBIGUOUS_OR_GENERIC_POSITIVE_CONTROLS_DID_NOT_PROVE_A_UNIQUE_FILTERING_FIELD"
        next_action = "RECOVER_JAVASCRIPT_OR_SERVER_SIDE_SEARCH_PARAMETER_SEMANTICS_WITHOUT_UQQ700_QUERY_OR_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-S230F-HARDENED",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "entry_url": ENTRY,
        "entry_http": entry.status_code,
        "entry_final_url": entry.url,
        "s230f_loaded": True,
        "uqq700_target_search_executed": False,
        "generic_positive_control_terms": GENERIC_TERMS,
        "form_count": len(forms),
        "form_descriptors": descriptors,
        "baseline_record_count": len(baseline_rows),
        "baseline_records": baseline_rows[:100],
        "experiments": experiments,
        "candidate_contracts": candidate_contracts,
        "likely_keyword_fields": likely_fields,
        "pagination_surface_count": len(pagination),
        "pagination_surfaces": pagination,
        "detail_sample_count": len(detail_samples),
        "detail_samples": detail_samples,
        "binary_surface_count": len(binary_samples),
        "binary_surfaces": binary_samples,
        "contract_qualified": contract_qualified,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "search_success_equals_designation": False,
            "search_success_equals_validity": False,
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
    print("SEMANTIC HARDENING")
    print("=" * 78)
    print(f"ENTRY HTTP: {entry.status_code}")
    print(f"FORM COUNT: {len(forms)}")
    print(f"BASELINE RECORD COUNT: {len(baseline_rows)}")
    print(f"FIELD EXPERIMENT COUNT: {len(experiments)}")
    print(f"LIKELY KEYWORD FIELD COUNT: {len(likely_fields)}")
    print(f"LIKELY KEYWORD FIELDS: {likely_fields}")
    print(f"PAGINATION SURFACE COUNT: {len(pagination)}")
    print(f"DETAIL SAMPLE COUNT: {len(detail_samples)}")
    print(f"BINARY SURFACE COUNT: {len(binary_samples)}")
    print(f"CONTRACT QUALIFIED: {contract_qualified}")
    for c in candidate_contracts:
        print(json.dumps(c, ensure_ascii=False))
    for e in experiments:
        print(json.dumps(e, ensure_ascii=False))

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
        "S230F loaded": IN_S230F.exists(),
        "ebook host": urlparse(entry.url).hostname == HOST,
        "no UQQ700 target search": out["uqq700_target_search_executed"] is False,
        "generic controls only": all(TARGET not in t for t in GENERIC_TERMS),
        "experiments bounded": len(experiments) <= 20,
        "search success not designation": out["summary"]["search_success_equals_designation"] is False,
        "search success not validity": out["summary"]["search_success_equals_validity"] is False,
        "search success not site inclusion": out["summary"]["search_success_equals_site_inclusion"] is False,
        "search failure not legal absence": out["summary"]["search_failure_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "GYEONGGI_EBOOK_GAZETTE_SEARCH_CONTRACT_SEMANTICALLY_HARDENED_QUALIFIED",
            "GYEONGGI_EBOOK_GAZETTE_SEARCH_CONTRACT_SEMANTIC_HARDENING_TECHNICAL_UNKNOWN",
        },
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
        raise AssertionError("S230F hardened validation failed")


if __name__ == "__main__":
    main()
