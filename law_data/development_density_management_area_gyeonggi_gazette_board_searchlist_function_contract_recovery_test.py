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
IN_PREV = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_javascript_search_submission_contract_recovery.json"
OUT = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_searchlist_function_contract_recovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
ENTRY = "https://www.gg.go.kr/bbs/board.do?bsIdx=769&menuId=1786"
HOST = "www.gg.go.kr"
TIMEOUT = 20
GENERIC_TERMS = ["경기도보", "고시"]
KEYWORD_FIELD = "searchKeyword"
DATE_FIELDS = ["searchStartDate", "searchEndDate"]
POST_ID_KEYS = ["bcIdx", "bIdx", "bbsIdx", "seq", "idx", "articleNo", "boardIdx", "boardSeq"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Referer": ENTRY,
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


def extract_post_identity(href_raw: str, title: str):
    p = urlparse(href_raw)
    qs = parse_qs(p.query)
    ids = []
    for key in POST_ID_KEYS:
        if key in qs and qs[key]:
            ids.append(f"{key}={qs[key][0]}")
    if ids:
        return "|".join(ids)
    m = re.search(r"(?:view|detail|read|goView|boardView)\s*\(([^)]{1,180})\)", href_raw, re.I)
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
        href_signal = bool(re.search(r"(?:bcIdx|bIdx|board|bbs|view|detail|read|seq|idx)", href_raw, re.I))
        title_signal = bool(re.search(r"(?:경기도보|제\s*\d+\s*호|고시|공고|도보)", title))
        if not (href_signal or title_signal):
            continue
        identity = extract_post_identity(href_raw, title)
        key = (identity, title)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"identity": identity, "title": title, "url": urljoin(base_url, href_raw)})
    return rows


def sig(rows):
    return {f"{r['identity']}|{r['title']}" for r in rows}


def overlap(baseline, result):
    b, r = sig(baseline), sig(result)
    return {
        "baseline_count": len(b),
        "result_count": len(r),
        "intersection_count": len(b & r),
        "removed_count": len(b - r),
        "added_count": len(r - b),
        "changed": b != r,
        "strict_subset": bool(r) and r < b,
    }


def form_defaults(soup: BeautifulSoup):
    for form in soup.find_all("form"):
        names = {x.get("name") for x in form.find_all(["input", "select", "textarea"]) if x.get("name")}
        if KEYWORD_FIELD not in names:
            continue
        payload = {}
        for tag in form.find_all(["input", "select", "textarea"]):
            name = tag.get("name")
            if not name:
                continue
            if tag.name == "select":
                selected = tag.find("option", selected=True)
                if selected is None:
                    selected = tag.find("option")
                payload[name] = selected.get("value", "") if selected else ""
            elif tag.name == "input":
                typ = (tag.get("type") or "text").lower()
                if typ in {"submit", "button", "image", "reset"}:
                    continue
                payload[name] = tag.get("value", "") or ""
            else:
                payload[name] = tag.get_text() or ""
        return form, payload
    return None, {}


def fetch_script_sources(session: requests.Session, soup: BeautifulSoup, base_url: str):
    sources = []
    for i, s in enumerate(soup.find_all("script"), 1):
        src = s.get("src")
        if src:
            url = urljoin(base_url, src)
            if urlparse(url).hostname != HOST:
                continue
            r = get(session, url)
            if r is not None and r.status_code == 200:
                sources.append({"source": url, "text": r.text})
        else:
            text = s.get_text("\n", strip=False) or ""
            if text:
                sources.append({"source": f"inline:{i}", "text": text})
    return sources[:80]


def extract_function_blocks(sources):
    hits = []
    patterns = [
        re.compile(r"function\s+searchList\s*\(([^)]*)\)\s*\{", re.I),
        re.compile(r"searchList\s*=\s*function\s*\(([^)]*)\)\s*\{", re.I),
    ]
    for src in sources:
        text = src["text"]
        for pat in patterns:
            for m in pat.finditer(text):
                start = m.start()
                brace = text.find("{", m.end() - 1)
                if brace < 0:
                    continue
                depth = 0
                end = min(len(text), brace + 12000)
                for i in range(brace, min(len(text), brace + 12000)):
                    if text[i] == "{":
                        depth += 1
                    elif text[i] == "}":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                block = text[start:end]
                hits.append({"source": src["source"], "args": norm(m.group(1)), "body": block[:12000]})
    return hits[:20]


def infer_contract(function_blocks, form_action: str):
    candidates = []
    seen = set()
    for block in function_blocks:
        body = block["body"]
        method_hints = []
        if re.search(r"type\s*:\s*['\"]POST['\"]|method\s*:\s*['\"]POST['\"]|\.post\s*\(", body, re.I):
            method_hints.append("POST")
        if re.search(r"type\s*:\s*['\"]GET['\"]|method\s*:\s*['\"]GET['\"]|\.get\s*\(", body, re.I):
            method_hints.append("GET")
        if not method_hints:
            method_hints = ["GET", "POST"]

        url_literals = []
        for m in re.finditer(r"(?:url\s*:\s*|\.load\s*\(|\.get\s*\(|\.post\s*\(|fetch\s*\()\s*['\"]([^'\"]+)['\"]", body, re.I):
            url_literals.append(urljoin(ENTRY, m.group(1)))
        if not url_literals:
            url_literals = [form_action]

        serialize = bool(re.search(r"serialize\s*\(|serializeArray\s*\(", body, re.I))
        ajax = bool(re.search(r"\$\.ajax\s*\(|\.ajax\s*\(|fetch\s*\(|\.load\s*\(|\$\.get\s*\(|\$\.post\s*\(", body, re.I))
        page_reset = bool(re.search(r"page(?:Index|No|Num|Unit|IndexNo)?\s*['\"]?\)?\s*\.?(?:val|value)?\s*\(?\s*['\"]?1['\"]?", body, re.I))

        for url in url_literals:
            if urlparse(url).hostname != HOST:
                continue
            for method in method_hints:
                key = (method, url, serialize, ajax)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append({
                    "method": method,
                    "action": url,
                    "serialize": serialize,
                    "ajax": ajax,
                    "page_reset_signal": page_reset,
                    "source": block["source"],
                    "body_sample": body[:4000],
                })
    return candidates[:8]


def run_candidate(session, candidate, base_payload, term, baseline_rows):
    payload = dict(base_payload)
    for f in DATE_FIELDS:
        payload[f] = ""
    payload[KEYWORD_FIELD] = term
    payload["bsIdx"] = payload.get("bsIdx") or "769"
    payload["menuId"] = payload.get("menuId") or "1786"

    if candidate["method"] == "POST":
        r = post(session, candidate["action"], data=payload)
    else:
        r = get(session, candidate["action"], params=payload)

    if r is None:
        return {"term": term, **{k: candidate[k] for k in ["method", "action", "serialize", "ajax"]}, "http": None, "credible_filtering": False, "technical_unknown": True}

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
        "serialize": candidate["serialize"],
        "ajax": candidate["ajax"],
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
    print("GYEONGGI GAZETTE BOARD searchList() FUNCTION CONTRACT RECOVERY - S230H-JS2")
    print("=" * 78)
    print("Purpose: recover searchList(true) function definition and actual submission contract")
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
    form, base_payload = form_defaults(soup)
    baseline_rows = canonical_posts(entry.text, entry.url)
    scripts = fetch_script_sources(session, soup, entry.url)
    functions = extract_function_blocks(scripts)
    form_action = urljoin(entry.url, form.get("action") or entry.url) if form else ENTRY
    candidates = infer_contract(functions, form_action)

    experiments = []
    for c in candidates:
        for term in GENERIC_TERMS:
            experiments.append(run_candidate(session, c, base_payload, term, baseline_rows))

    grouped = {}
    for e in experiments:
        key = (e["method"], e["action"], e["serialize"], e["ajax"])
        grouped.setdefault(key, []).append(e)

    qualified = []
    for key, rows in grouped.items():
        if len(rows) == len(GENERIC_TERMS) and all(r.get("http") == 200 and r.get("credible_filtering") and not r.get("technical_unknown") for r in rows):
            qualified.append({
                "method": key[0], "action": key[1], "serialize": key[2], "ajax": key[3],
                "runs": len(rows),
                "result_counts": [r.get("result_count") for r in rows],
                "removed_counts": [r.get("removed_count") for r in rows],
                "title_match_counts": [r.get("title_match_count") for r in rows],
            })

    contract_qualified = len(qualified) == 1
    function_recovered = len(functions) > 0

    if contract_qualified:
        classification = "GYEONGGI_GAZETTE_BOARD_SEARCHLIST_FUNCTION_CONTRACT_QUALIFIED"
        semantic = "SEARCHLIST_FUNCTION_WAS_RECOVERED_AND_EXACTLY_ONE_SUBMISSION_PATTERN_FILTERED_CANONICAL_POST_IDENTITIES_FOR_ALL_GENERIC_POSITIVE_CONTROLS"
        next_action = "RUN_ONLY_EXACT_VARIANT_WEAK_UQQ700_BOUNDED_SEARCH_THROUGH_THE_RECOVERED_SEARCHLIST_CONTRACT"
    elif function_recovered:
        classification = "GYEONGGI_GAZETTE_BOARD_SEARCHLIST_FUNCTION_RECOVERED_BUT_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "SEARCHLIST_FUNCTION_BODY_WAS_RECOVERED_BUT_NO_UNIQUE_SERVER_REQUEST_PATTERN_PROVED_FILTERING_WITH_GENERIC_CONTROLS"
        next_action = "HARDEN_ONLY_THE_SERVER_REQUEST_OR_FRAGMENT_REPLACEMENT_PATH_EXPOSED_BY_SEARCHLIST_WITHOUT_UQQ700_QUERY"
    else:
        classification = "GYEONGGI_GAZETTE_BOARD_SEARCHLIST_FUNCTION_NOT_RECOVERED_TECHNICAL_UNKNOWN"
        semantic = "SEARCHLIST_CALL_WAS_OBSERVED_PREVIOUSLY_BUT_ITS_FUNCTION_DEFINITION_WAS_NOT_RECOVERED_FROM_BOUNDED_INLINE_OR_OFFICIAL_EXTERNAL_SCRIPTS"
        next_action = "QUALIFY_ONLY_THE_MISSING_SCRIPT_SOURCE_OR_DYNAMIC_FUNCTION_DEFINITION_WITHOUT_UQQ700_QUERY"

    out = {
        "step": "STEP 17-S230H-JS2",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "entry_url": ENTRY,
        "entry_http": entry.status_code,
        "previous_js_recovery_loaded": True,
        "uqq700_target_search_executed": False,
        "baseline_post_count": len(baseline_rows),
        "script_source_count": len(scripts),
        "searchlist_function_count": len(functions),
        "searchlist_functions": functions,
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
    print("SEARCHLIST FUNCTION RECOVERY")
    print("=" * 78)
    print(f"ENTRY HTTP: {entry.status_code}")
    print(f"BASELINE POST COUNT: {len(baseline_rows)}")
    print(f"SCRIPT SOURCE COUNT: {len(scripts)}")
    print(f"SEARCHLIST FUNCTION COUNT: {len(functions)}")
    print(f"CANDIDATE CONTRACT COUNT: {len(candidates)}")
    print(f"POSITIVE CONTROL EXPERIMENT COUNT: {len(experiments)}")
    print(f"QUALIFIED CONTRACT COUNT: {len(qualified)}")
    print(f"CONTRACT QUALIFIED: {contract_qualified}")

    for f in functions:
        print("SEARCHLIST_FUNCTION:", json.dumps({"source": f["source"], "args": f["args"], "body": f["body"][:5000]}, ensure_ascii=False))
    for c in candidates:
        print("CANDIDATE_CONTRACT:", json.dumps({k: c.get(k) for k in ["method", "action", "serialize", "ajax", "page_reset_signal", "source"]}, ensure_ascii=False))
    for e in experiments:
        print("POSITIVE_CONTROL:", json.dumps({k: e.get(k) for k in [
            "term", "method", "action", "serialize", "ajax", "http", "baseline_count", "result_count",
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
        "previous JS recovery loaded": out["previous_js_recovery_loaded"] is True,
        "entry host gg": urlparse(ENTRY).hostname == HOST,
        "no UQQ700 target search": out["uqq700_target_search_executed"] is False,
        "generic controls only": GENERIC_TERMS == ["경기도보", "고시"],
        "script sources bounded": len(scripts) <= 80,
        "candidate contracts bounded": len(candidates) <= 8,
        "positive controls bounded": len(experiments) <= 16,
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
            "GYEONGGI_GAZETTE_BOARD_SEARCHLIST_FUNCTION_CONTRACT_QUALIFIED",
            "GYEONGGI_GAZETTE_BOARD_SEARCHLIST_FUNCTION_RECOVERED_BUT_CONTRACT_TECHNICAL_UNKNOWN",
            "GYEONGGI_GAZETTE_BOARD_SEARCHLIST_FUNCTION_NOT_RECOVERED_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S230H-JS2 validation failed")


if __name__ == "__main__":
    main()
