# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_PREV = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_searchlist_function_contract_recovery.json"
OUT = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_searchfields_paginglist_contract_recovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
ENTRY = "https://www.gg.go.kr/bbs/board.do?bsIdx=769&menuId=1786"
HOST = "www.gg.go.kr"
TIMEOUT = 20
GENERIC_TERMS = ["경기도보", "고시"]
POST_ID_KEYS = ["bcIdx", "bIdx", "bbsIdx", "seq", "idx", "articleNo", "boardIdx", "boardSeq"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Referer": ENTRY,
    "X-Requested-With": "XMLHttpRequest",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def get(session: requests.Session, url: str, params=None):
    try:
        return session.get(url, params=params, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException:
        return None


def post(session: requests.Session, url: str, data=None):
    try:
        return session.post(url, data=data, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException:
        return None


def canonical_posts(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    seen = set()
    for a in soup.find_all("a", href=True):
        title = norm(a.get_text(" ", strip=True))
        href_raw = a.get("href") or ""
        if not title:
            continue
        href_signal = bool(re.search(r"(?:bcIdx|bIdx|board|bbs|view|detail|read|seq|idx)", href_raw, re.I))
        title_signal = bool(re.search(r"(?:경기도보|제\s*\d+\s*호|고시|공고|도보)", title))
        if not (href_signal or title_signal):
            continue
        p = urlparse(href_raw)
        qs = parse_qs(p.query)
        ids = []
        for key in POST_ID_KEYS:
            if key in qs and qs[key]:
                ids.append(f"{key}={qs[key][0]}")
        identity = "|".join(ids) if ids else f"title:{title}"
        key = (identity, title)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"identity": identity, "title": title, "url": urljoin(base_url, href_raw)})
    return rows


def signature(rows):
    return {f"{r['identity']}|{r['title']}" for r in rows}


def overlap(baseline, result):
    b = signature(baseline)
    r = signature(result)
    return {
        "baseline_count": len(b),
        "result_count": len(r),
        "intersection_count": len(b & r),
        "removed_count": len(b - r),
        "added_count": len(r - b),
        "changed": b != r,
        "strict_subset": bool(r) and r < b,
    }


def collect_scripts(session: requests.Session, soup: BeautifulSoup, base_url: str):
    sources = []
    seen = set()
    for i, script in enumerate(soup.find_all("script"), 1):
        src = script.get("src")
        if src:
            url = urljoin(base_url, src)
            if urlparse(url).hostname != HOST or url in seen:
                continue
            seen.add(url)
            r = get(session, url)
            if r is not None and r.status_code == 200:
                sources.append({"source": url, "text": r.text})
        else:
            text = script.get_text("\n", strip=False) or ""
            if text:
                sources.append({"source": f"inline:{i}", "text": text})
    return sources[:80]


def extract_balanced_block(text: str, start: int, max_len=16000):
    brace = text.find("{", start)
    if brace < 0:
        return text[start:start + max_len]
    depth = 0
    end = min(len(text), brace + max_len)
    for i in range(brace, min(len(text), brace + max_len)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return text[start:end]


def extract_searchfields(sources):
    hits = []
    patterns = [
        re.compile(r"(?:var|let|const)\s+SearchFields\s*=\s*\{", re.I),
        re.compile(r"SearchFields\s*=\s*\{", re.I),
    ]
    for src in sources:
        text = src["text"]
        for pat in patterns:
            for m in pat.finditer(text):
                block = extract_balanced_block(text, m.start())
                mappings = {}
                for mm in re.finditer(r"([A-Za-z0-9_]+)\s*:\s*\$\(\s*['\"]([^'\"]+)['\"]\s*\)", block):
                    mappings[mm.group(1)] = mm.group(2)
                hits.append({"source": src["source"], "body": block[:12000], "mappings": mappings})
    return hits[:20]


def extract_paginglist_blocks(sources):
    hits = []
    patterns = [
        re.compile(r"(?:var|let|const)\s+PagingList\s*=\s*\{", re.I),
        re.compile(r"PagingList\s*=\s*\{", re.I),
        re.compile(r"PagingList\.setPage\s*=\s*function\s*\(", re.I),
        re.compile(r"setPage\s*:\s*function\s*\(", re.I),
    ]
    for src in sources:
        text = src["text"]
        for pat in patterns:
            for m in pat.finditer(text):
                block = extract_balanced_block(text, m.start())
                if "setPage" not in block and "PagingList" not in block:
                    continue
                hits.append({"source": src["source"], "body": block[:16000]})
    dedup = []
    seen = set()
    for h in hits:
        key = (h["source"], h["body"][:500])
        if key not in seen:
            seen.add(key)
            dedup.append(h)
    return dedup[:20]


def infer_request_contracts(searchfields_hits, paging_hits, entry_url):
    candidates = []
    seen = set()
    text_blocks = [h["body"] for h in paging_hits]
    for body in text_blocks:
        methods = []
        if re.search(r"type\s*:\s*['\"]POST['\"]|method\s*:\s*['\"]POST['\"]|\.post\s*\(", body, re.I):
            methods.append("POST")
        if re.search(r"type\s*:\s*['\"]GET['\"]|method\s*:\s*['\"]GET['\"]|\.get\s*\(", body, re.I):
            methods.append("GET")
        if not methods:
            methods = ["GET", "POST"]

        urls = []
        for m in re.finditer(r"(?:url\s*:\s*|\.load\s*\(|\.get\s*\(|\.post\s*\(|fetch\s*\()\s*['\"]([^'\"]+)['\"]", body, re.I):
            urls.append(urljoin(entry_url, m.group(1)))
        if not urls:
            urls = [entry_url]

        nested_data = bool(re.search(r"params\s*\[\s*['\"]data['\"]\s*\]|params\.data|data\s*:\s*params", body, re.I))
        json_stringify = bool(re.search(r"JSON\.stringify\s*\(", body, re.I))
        ajax = bool(re.search(r"\$\.ajax\s*\(|\.ajax\s*\(|fetch\s*\(|\.load\s*\(|\$\.get\s*\(|\$\.post\s*\(", body, re.I))

        for method in methods:
            for url in urls:
                if urlparse(url).hostname != HOST:
                    continue
                key = (method, url, nested_data, json_stringify, ajax)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append({
                    "method": method,
                    "action": url,
                    "nested_data": nested_data,
                    "json_stringify": json_stringify,
                    "ajax": ajax,
                    "body_sample": body[:5000],
                })

    mappings = {}
    for h in searchfields_hits:
        mappings.update(h.get("mappings") or {})
    return candidates[:8], mappings


def checkbox_state(soup: BeautifulSoup):
    state = {}
    for tag in soup.select('input[type="checkbox"][name="gubunCk"]'):
        tid = tag.get("id")
        if not tid:
            continue
        state[tid] = {
            "value": tag.get("value", ""),
            "checked": tag.has_attr("checked"),
        }
    return state


def selector_value(soup: BeautifulSoup, selector: str):
    try:
        tag = soup.select_one(selector)
    except Exception:
        return ""
    if not tag:
        return ""
    if tag.name == "select":
        opt = tag.find("option", selected=True) or tag.find("option")
        return opt.get("value", "") if opt else ""
    return tag.get("value", "") or ""


def build_browser_payload(soup, mappings, term, checkbox_map):
    data = {}
    for key, selector in mappings.items():
        val = selector_value(soup, selector)
        if key.lower() in {"keyword", "searchkeyword"} or "keyword" in selector.lower():
            val = term
        data[key] = val

    for cid, meta in checkbox_map.items():
        data[cid] = meta["value"] if meta["checked"] else ""

    if checkbox_map and not any(meta["checked"] for meta in checkbox_map.values()):
        if "ck00" in checkbox_map:
            data["ck00"] = "1"

    if "keyword" in data and data.get("keyword") == "":
        data["keyfield"] = ""

    return data


def flatten_variants(data):
    variants = []
    variants.append(("FLAT", dict(data)))
    variants.append(("DATA_PREFIX", {f"data[{k}]": v for k, v in data.items()}))
    variants.append(("DATA_DOT", {f"data.{k}": v for k, v in data.items()}))
    return variants


def execute_candidate(session, candidate, payload_mode, payload, term, baseline_rows):
    if candidate["method"] == "POST":
        r = post(session, candidate["action"], data=payload)
    else:
        r = get(session, candidate["action"], params=payload)

    if r is None:
        return {
            "term": term,
            "method": candidate["method"],
            "action": candidate["action"],
            "payload_mode": payload_mode,
            "http": None,
            "credible_filtering": False,
            "technical_unknown": True,
        }

    rows = canonical_posts(r.text, r.url)
    stats = overlap(baseline_rows, rows)
    title_match_count = sum(1 for row in rows if term in row["title"])
    credible = (
        r.status_code == 200
        and stats["changed"]
        and (stats["strict_subset"] or stats["removed_count"] > 0)
        and (title_match_count > 0 or stats["result_count"] < stats["baseline_count"])
    )
    return {
        "term": term,
        "method": candidate["method"],
        "action": candidate["action"],
        "payload_mode": payload_mode,
        "nested_data_signal": candidate["nested_data"],
        "json_stringify_signal": candidate["json_stringify"],
        "ajax_signal": candidate["ajax"],
        "http": r.status_code,
        "final_url": r.url,
        "title_match_count": title_match_count,
        "credible_filtering": credible,
        "technical_unknown": r.status_code != 200,
        **stats,
        "sample_rows": rows[:12],
    }


def main():
    print("=" * 78)
    print("GYEONGGI GAZETTE BOARD SearchFields + PagingList CONTRACT RECOVERY - S230H-JS3")
    print("=" * 78)
    print("Purpose: recover SearchFields mapping and PagingList.setPage server request structure")
    print("UQQ700 target search: DISABLED")
    print("Generic positive controls only")
    print("Filtering success != designation/current validity/site inclusion")
    print("Filtering failure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    prev = load_json(IN_PREV)
    assert prev.get("contract_qualified") is False
    assert prev.get("uqq700_target_search_executed") is False

    session = requests.Session()
    entry = get(session, ENTRY)
    if entry is None:
        raise RuntimeError("GG gazette board entry request failed")

    soup = BeautifulSoup(entry.text, "html.parser")
    baseline_rows = canonical_posts(entry.text, entry.url)
    scripts = collect_scripts(session, soup, entry.url)
    searchfields_hits = extract_searchfields(scripts)
    paging_hits = extract_paginglist_blocks(scripts)
    candidates, mappings = infer_request_contracts(searchfields_hits, paging_hits, entry.url)
    checkboxes = checkbox_state(soup)

    experiments = []
    for term in GENERIC_TERMS:
        browser_data = build_browser_payload(soup, mappings, term, checkboxes)
        for payload_mode, payload in flatten_variants(browser_data):
            for candidate in candidates:
                experiments.append(execute_candidate(session, candidate, payload_mode, payload, term, baseline_rows))
                if len(experiments) >= 48:
                    break
            if len(experiments) >= 48:
                break
        if len(experiments) >= 48:
            break

    grouped = {}
    for e in experiments:
        key = (e["method"], e["action"], e["payload_mode"])
        grouped.setdefault(key, []).append(e)

    qualified = []
    for key, rows in grouped.items():
        terms = {r["term"] for r in rows}
        if terms != set(GENERIC_TERMS):
            continue
        selected = []
        for term in GENERIC_TERMS:
            term_rows = [r for r in rows if r["term"] == term]
            if len(term_rows) != 1:
                break
            selected.append(term_rows[0])
        if len(selected) != len(GENERIC_TERMS):
            continue
        if all(r.get("http") == 200 and r.get("credible_filtering") and not r.get("technical_unknown") for r in selected):
            qualified.append({
                "method": key[0],
                "action": key[1],
                "payload_mode": key[2],
                "runs": len(selected),
                "result_counts": [r.get("result_count") for r in selected],
                "removed_counts": [r.get("removed_count") for r in selected],
                "title_match_counts": [r.get("title_match_count") for r in selected],
            })

    contract_qualified = len(qualified) == 1
    searchfields_recovered = bool(mappings)
    paginglist_recovered = bool(paging_hits)

    if contract_qualified:
        classification = "GYEONGGI_GAZETTE_BOARD_SEARCHFIELDS_PAGINGLIST_CONTRACT_QUALIFIED"
        semantic = "SEARCHFIELDS_AND_PAGINGLIST_WERE_RECOVERED_AND_EXACTLY_ONE_BROWSER_STYLE_REQUEST_PATTERN_FILTERED_CANONICAL_POST_IDENTITIES_FOR_ALL_GENERIC_POSITIVE_CONTROLS"
        next_action = "RUN_ONLY_EXACT_VARIANT_WEAK_UQQ700_BOUNDED_SEARCH_THROUGH_THE_QUALIFIED_BROWSER_STYLE_CONTRACT"
    elif searchfields_recovered and paginglist_recovered:
        classification = "GYEONGGI_GAZETTE_BOARD_SEARCHFIELDS_PAGINGLIST_RECOVERED_BUT_REQUEST_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "SEARCHFIELDS_MAPPING_AND_PAGINGLIST_LOGIC_WERE_RECOVERED_BUT_NO_UNIQUE_BROWSER_STYLE_SERVER_REQUEST_FILTERED_CANONICAL_POST_IDENTITIES"
        next_action = "HARDEN_ONLY_THE_EXACT_PAGINGLIST_SERVER_ENDPOINT_OR_PAYLOAD_SERIALIZATION_EXPOSED_BY_THE_RECOVERED_CODE_WITHOUT_UQQ700_QUERY"
    else:
        classification = "GYEONGGI_GAZETTE_BOARD_SEARCHFIELDS_OR_PAGINGLIST_NOT_FULLY_RECOVERED_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_BOTH_REQUIRED_JAVASCRIPT_CONTRACT_COMPONENTS_WERE_NOT_RECOVERED_FROM_BOUNDED_OFFICIAL_SCRIPT_SOURCES"
        next_action = "QUALIFY_ONLY_THE_MISSING_SEARCHFIELDS_OR_PAGINGLIST_COMPONENT_WITHOUT_UQQ700_QUERY"

    out = {
        "step": "STEP 17-S230H-JS3",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "entry_url": ENTRY,
        "entry_http": entry.status_code,
        "previous_js2_loaded": True,
        "uqq700_target_search_executed": False,
        "baseline_post_count": len(baseline_rows),
        "script_source_count": len(scripts),
        "searchfields_definition_count": len(searchfields_hits),
        "searchfields_definitions": searchfields_hits,
        "searchfields_mapping": mappings,
        "paginglist_definition_count": len(paging_hits),
        "paginglist_definitions": paging_hits,
        "checkbox_state": checkboxes,
        "candidate_contract_count": len(candidates),
        "candidate_contracts": candidates,
        "positive_control_experiment_count": len(experiments),
        "positive_control_experiments": experiments,
        "qualified_contract_count": len(qualified),
        "qualified_contracts": qualified,
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
    print("CONTRACT COMPONENT RECOVERY")
    print("=" * 78)
    print(f"ENTRY HTTP: {entry.status_code}")
    print(f"BASELINE POST COUNT: {len(baseline_rows)}")
    print(f"SCRIPT SOURCE COUNT: {len(scripts)}")
    print(f"SEARCHFIELDS DEFINITION COUNT: {len(searchfields_hits)}")
    print(f"SEARCHFIELDS MAPPING COUNT: {len(mappings)}")
    print(f"PAGINGLIST DEFINITION COUNT: {len(paging_hits)}")
    print(f"CHECKBOX KEY COUNT: {len(checkboxes)}")
    print(f"CANDIDATE CONTRACT COUNT: {len(candidates)}")
    print(f"POSITIVE CONTROL EXPERIMENT COUNT: {len(experiments)}")
    print(f"QUALIFIED CONTRACT COUNT: {len(qualified)}")
    print(f"CONTRACT QUALIFIED: {contract_qualified}")

    print("SEARCHFIELDS_MAPPING:", json.dumps(mappings, ensure_ascii=False))
    print("CHECKBOX_STATE:", json.dumps(checkboxes, ensure_ascii=False))
    for h in searchfields_hits:
        print("SEARCHFIELDS_DEFINITION:", json.dumps({"source": h["source"], "body": h["body"][:5000], "mappings": h["mappings"]}, ensure_ascii=False))
    for h in paging_hits:
        print("PAGINGLIST_DEFINITION:", json.dumps({"source": h["source"], "body": h["body"][:7000]}, ensure_ascii=False))
    for c in candidates:
        print("CANDIDATE_CONTRACT:", json.dumps({k: c.get(k) for k in ["method", "action", "nested_data", "json_stringify", "ajax"]}, ensure_ascii=False))
    for e in experiments:
        print("POSITIVE_CONTROL:", json.dumps({k: e.get(k) for k in [
            "term", "method", "action", "payload_mode", "http", "baseline_count", "result_count",
            "intersection_count", "removed_count", "added_count", "changed", "strict_subset", "title_match_count",
            "credible_filtering", "technical_unknown", "final_url"
        ]}, ensure_ascii=False))
    for q in qualified:
        print("QUALIFIED_CONTRACT:", json.dumps(q, ensure_ascii=False))

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
        "previous JS2 loaded": out["previous_js2_loaded"] is True,
        "entry host gg": urlparse(ENTRY).hostname == HOST,
        "no UQQ700 target search": out["uqq700_target_search_executed"] is False,
        "generic controls only": GENERIC_TERMS == ["경기도보", "고시"],
        "script sources bounded": len(scripts) <= 80,
        "candidate contracts bounded": len(candidates) <= 8,
        "positive controls bounded": len(experiments) <= 48,
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
            "GYEONGGI_GAZETTE_BOARD_SEARCHFIELDS_PAGINGLIST_CONTRACT_QUALIFIED",
            "GYEONGGI_GAZETTE_BOARD_SEARCHFIELDS_PAGINGLIST_RECOVERED_BUT_REQUEST_CONTRACT_TECHNICAL_UNKNOWN",
            "GYEONGGI_GAZETTE_BOARD_SEARCHFIELDS_OR_PAGINGLIST_NOT_FULLY_RECOVERED_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S230H-JS3 validation failed")


if __name__ == "__main__":
    main()
