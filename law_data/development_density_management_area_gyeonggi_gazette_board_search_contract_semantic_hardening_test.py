# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_S230H = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_uqq700_bounded_search_contract.json"
OUT = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_search_contract_semantic_hardening.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
ENTRY = "https://www.gg.go.kr/bbs/board.do?bsIdx=769&menuId=1786"
HOST = "www.gg.go.kr"
TIMEOUT = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Referer": ENTRY,
}
GENERIC_TERMS = ["경기도보", "고시"]
DATE_FIELDS = {"searchStartDate", "searchEndDate"}
KEYWORD_FIELD = "searchKeyword"

POST_ID_KEYS = ["bcIdx", "bIdx", "bbsIdx", "seq", "idx", "articleNo", "boardIdx"]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def fetch(session: requests.Session, url: str, params=None):
    try:
        return session.get(url, params=params, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException:
        return None


def form_semantics(soup: BeautifulSoup, base_url: str):
    forms = []
    for fi, form in enumerate(soup.find_all("form"), 1):
        controls = []
        for tag in form.find_all(["input", "select", "textarea", "button"]):
            name = tag.get("name")
            if not name:
                continue
            label_text = ""
            elem_id = tag.get("id")
            if elem_id:
                lab = form.find("label", attrs={"for": elem_id})
                if lab:
                    label_text = norm(lab.get_text(" ", strip=True))
            parent_text = norm(tag.parent.get_text(" ", strip=True)) if tag.parent else ""
            item = {
                "tag": tag.name,
                "name": name,
                "type": tag.get("type"),
                "value": tag.get("value", ""),
                "label_text": label_text,
                "parent_text": parent_text[:200],
                "options": [],
            }
            if tag.name == "select":
                item["options"] = [
                    {"value": o.get("value", ""), "text": norm(o.get_text(" ", strip=True)), "selected": o.has_attr("selected")}
                    for o in tag.find_all("option")
                ]
            controls.append(item)
        forms.append({
            "form_index": fi,
            "method": (form.get("method") or "GET").upper(),
            "action": urljoin(base_url, form.get("action") or base_url),
            "controls": controls,
        })
    return forms


def select_search_form(forms):
    for form in forms:
        names = {c["name"] for c in form["controls"]}
        if KEYWORD_FIELD in names and DATE_FIELDS.issubset(names):
            return form
    return None


def default_payload(form):
    payload = {}
    for c in form["controls"]:
        name = c["name"]
        if c["tag"] == "select":
            selected = next((o["value"] for o in c["options"] if o["selected"]), None)
            if selected is None:
                selected = next((o["value"] for o in c["options"] if o["value"] != ""), "")
            payload[name] = selected
        elif c["tag"] == "input":
            t = (c.get("type") or "text").lower()
            if t in {"submit", "button", "image", "reset"}:
                continue
            payload[name] = c.get("value", "") or ""
        else:
            payload[name] = c.get("value", "") or ""
    return payload


def extract_post_identity(href: str, title: str):
    p = urlparse(href)
    qs = parse_qs(p.query)
    ids = []
    for k in POST_ID_KEYS:
        if k in qs and qs[k]:
            ids.append(f"{k}={qs[k][0]}")
    if ids:
        return "|".join(ids)
    m = re.search(r"(?:view|detail|read|boardView|goView)\s*\(([^)]{1,120})\)", href, re.I)
    if m:
        return f"js:{norm(m.group(1))}"
    return f"title:{title}"


def canonical_posts(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    seen = set()
    for a in soup.find_all("a", href=True):
        title = norm(a.get_text(" ", strip=True))
        href_raw = a.get("href") or ""
        if not title:
            continue
        href = urljoin(base_url, href_raw)
        title_signal = bool(re.search(r"(?:경기도보|제\s*\d+\s*호|고시|공고|도보)", title))
        href_signal = bool(re.search(r"(?:board|bbs|view|detail|bcIdx|bIdx|idx|seq)", href_raw, re.I))
        if not (title_signal or href_signal):
            continue
        identity = extract_post_identity(href_raw, title)
        key = (identity, title)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"identity": identity, "title": title, "url": href})
    return rows


def post_signature(rows):
    return sorted({f"{r['identity']}|{r['title']}" for r in rows})


def overlap_stats(baseline, result):
    b = set(post_signature(baseline))
    r = set(post_signature(result))
    return {
        "baseline_count": len(b),
        "result_count": len(r),
        "intersection_count": len(b & r),
        "removed_count": len(b - r),
        "added_count": len(r - b),
        "changed": b != r,
        "strict_subset": bool(r) and r < b,
    }


def field_semantic(form, field_name: str):
    c = next((x for x in form["controls"] if x["name"] == field_name), None)
    if not c:
        return {"field": field_name, "found": False}
    combined = " ".join([field_name, c.get("label_text", ""), c.get("parent_text", "")])
    return {
        "field": field_name,
        "found": True,
        "tag": c["tag"],
        "type": c.get("type"),
        "label_text": c.get("label_text"),
        "parent_text": c.get("parent_text"),
        "date_semantic_signal": bool(re.search(r"날짜|기간|시작|종료|date|start|end", combined, re.I)),
        "keyword_semantic_signal": bool(re.search(r"검색|검색어|키워드|keyword|search", combined, re.I)),
    }


def main():
    print("=" * 78)
    print("GYEONGGI GAZETTE BOARD SEARCH CONTRACT SEMANTIC HARDENING - S230H HARDENED")
    print("=" * 78)
    print("Purpose: exclude date fields semantically and prove searchKeyword filters canonical post identities")
    print("UQQ700 target search: DISABLED")
    print("Generic positive controls only")
    print("Filtering success != designation/current validity/site inclusion")
    print("Filtering failure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    prev = load_json(IN_S230H)
    session = requests.Session()
    entry = fetch(session, ENTRY)
    if entry is None:
        raise RuntimeError("GG gazette board entry request failed")

    soup = BeautifulSoup(entry.text, "html.parser")
    forms = form_semantics(soup, entry.url)
    search_form = select_search_form(forms)
    baseline_rows = canonical_posts(entry.text, entry.url)

    semantics = {
        "searchStartDate": field_semantic(search_form, "searchStartDate") if search_form else {"field": "searchStartDate", "found": False},
        "searchEndDate": field_semantic(search_form, "searchEndDate") if search_form else {"field": "searchEndDate", "found": False},
        "searchKeyword": field_semantic(search_form, "searchKeyword") if search_form else {"field": "searchKeyword", "found": False},
    }

    excluded_fields = []
    for f in sorted(DATE_FIELDS):
        s = semantics[f]
        if s.get("found") and (s.get("date_semantic_signal") or "date" in f.lower() or "start" in f.lower() or "end" in f.lower()):
            excluded_fields.append(f)

    experiments = []
    payload_template = default_payload(search_form) if search_form else {}

    # Preserve official board state observed in S230H, but do not infer legal meaning from it.
    if search_form:
        payload_template["bsIdx"] = payload_template.get("bsIdx") or "769"
        payload_template["menuId"] = payload_template.get("menuId") or "1786"
        if "gubunCk" in payload_template and not payload_template.get("gubunCk"):
            payload_template["gubunCk"] = "12"

    for term in GENERIC_TERMS:
        if not search_form:
            break
        payload = dict(payload_template)
        payload["searchStartDate"] = ""
        payload["searchEndDate"] = ""
        payload[KEYWORD_FIELD] = term
        r = fetch(session, search_form["action"], params=payload)
        if r is None:
            experiments.append({
                "term": term,
                "http": None,
                "result_count": None,
                "changed": False,
                "strict_subset": False,
                "credible_filtering": False,
            })
            continue
        rows = canonical_posts(r.text, r.url)
        stats = overlap_stats(baseline_rows, rows)
        title_match_count = sum(1 for x in rows if term in x["title"])
        credible = (
            r.status_code == 200
            and stats["changed"]
            and (stats["strict_subset"] or stats["removed_count"] > 0)
            and (title_match_count > 0 or stats["result_count"] < stats["baseline_count"])
        )
        experiments.append({
            "term": term,
            "http": r.status_code,
            "final_url": r.url,
            "title_match_count": title_match_count,
            "credible_filtering": credible,
            **stats,
            "sample_rows": rows[:12],
        })

    keyword_semantic_ok = semantics[KEYWORD_FIELD].get("found") and semantics[KEYWORD_FIELD].get("keyword_semantic_signal")
    date_fields_excluded = set(excluded_fields) == DATE_FIELDS
    positive_controls_all_credible = len(experiments) == len(GENERIC_TERMS) and all(x.get("credible_filtering") for x in experiments)
    contract_qualified = bool(search_form and keyword_semantic_ok and date_fields_excluded and positive_controls_all_credible)

    if contract_qualified:
        classification = "GYEONGGI_GAZETTE_BOARD_SEARCHKEYWORD_CONTRACT_SEMANTICALLY_HARDENED_QUALIFIED"
        semantic = "SEARCHKEYWORD_IS_THE_ONLY_SEMANTICALLY_ELIGIBLE_KEYWORD_FIELD_AND_GENERIC_POSITIVE_CONTROLS_PROVED_CANONICAL_POST_FILTERING"
        next_action = "RUN_EXACT_VARIANT_WEAK_UQQ700_BOUNDED_SEARCH_ONLY_THROUGH_SEARCHKEYWORD_WITH_DATE_FIELDS_BLANK_AND_BOARD_STATE_PRESERVED"
    else:
        classification = "GYEONGGI_GAZETTE_BOARD_SEARCH_CONTRACT_SEMANTIC_HARDENING_TECHNICAL_UNKNOWN"
        semantic = "SEARCHKEYWORD_FILTERING_WAS_NOT_FULLY_PROVED_BY_CANONICAL_POST_IDENTITY_CHANGE_AFTER_EXCLUDING_DATE_FIELDS"
        next_action = "RECOVER_BOARD_ROW_IDENTITY_OR_JAVASCRIPT_SEARCH_SUBMISSION_SEMANTICS_WITHOUT_UQQ700_QUERY_OR_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-S230H-HARDENED",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "entry_url": ENTRY,
        "entry_http": entry.status_code,
        "s230h_loaded": True,
        "uqq700_target_search_executed": False,
        "form_count": len(forms),
        "search_form_found": search_form is not None,
        "search_form": search_form,
        "field_semantics": semantics,
        "excluded_date_fields": excluded_fields,
        "baseline_post_count": len(baseline_rows),
        "baseline_posts": baseline_rows[:100],
        "positive_control_experiments": experiments,
        "keyword_field": KEYWORD_FIELD,
        "keyword_semantic_ok": keyword_semantic_ok,
        "date_fields_excluded": date_fields_excluded,
        "positive_controls_all_credible": positive_controls_all_credible,
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
    print(f"SEARCH FORM FOUND: {search_form is not None}")
    print(f"BASELINE POST COUNT: {len(baseline_rows)}")
    print(f"EXCLUDED DATE FIELDS: {excluded_fields}")
    print(f"KEYWORD SEMANTIC OK: {keyword_semantic_ok}")
    print(f"DATE FIELDS EXCLUDED: {date_fields_excluded}")
    print(f"POSITIVE CONTROL COUNT: {len(experiments)}")
    for k, v in semantics.items():
        print("FIELD_SEMANTIC:", json.dumps(v, ensure_ascii=False))
    for e in experiments:
        print("POSITIVE_CONTROL:", json.dumps({k: e.get(k) for k in [
            "term", "http", "baseline_count", "result_count", "intersection_count", "removed_count", "added_count", "changed", "strict_subset", "title_match_count", "credible_filtering", "final_url"
        ]}, ensure_ascii=False))
    print(f"POSITIVE CONTROLS ALL CREDIBLE: {positive_controls_all_credible}")
    print(f"CONTRACT QUALIFIED: {contract_qualified}")

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
        "S230H loaded": IN_S230H.exists(),
        "entry host gg": urlparse(entry.url).hostname == HOST,
        "no UQQ700 target search": out["uqq700_target_search_executed"] is False,
        "generic controls only": all(TARGET not in x for x in GENERIC_TERMS),
        "date fields excluded from keyword qualification": set(excluded_fields).issubset(DATE_FIELDS),
        "positive controls bounded": len(experiments) <= 2,
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
            "GYEONGGI_GAZETTE_BOARD_SEARCHKEYWORD_CONTRACT_SEMANTICALLY_HARDENED_QUALIFIED",
            "GYEONGGI_GAZETTE_BOARD_SEARCH_CONTRACT_SEMANTIC_HARDENING_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S230H hardened validation failed")


if __name__ == "__main__":
    main()
