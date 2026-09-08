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
IN_HARDENED = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_search_contract_semantic_hardening.json"
OUT = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_javascript_search_submission_contract_recovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
ENTRY = "https://www.gg.go.kr/bbs/board.do?bsIdx=769&menuId=1786"
HOST = "www.gg.go.kr"
TIMEOUT = 20
GENERIC_TERMS = ["경기도보", "고시"]
KEYWORD_FIELD = "searchKeyword"
DATE_FIELDS = {"searchStartDate", "searchEndDate"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Referer": ENTRY,
}

POST_ID_KEYS = ["bcIdx", "bIdx", "bbsIdx", "seq", "idx", "articleNo", "boardIdx", "boardSeq"]


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


def form_snapshot(soup: BeautifulSoup, base_url: str):
    forms = []
    for fi, form in enumerate(soup.find_all("form"), 1):
        controls = []
        for tag in form.find_all(["input", "select", "textarea", "button"]):
            name = tag.get("name")
            if not name:
                continue
            item = {
                "tag": tag.name,
                "name": name,
                "id": tag.get("id"),
                "type": tag.get("type"),
                "value": tag.get("value", ""),
                "onclick": tag.get("onclick"),
                "onchange": tag.get("onchange"),
                "options": [],
            }
            if tag.name == "select":
                item["options"] = [
                    {
                        "value": o.get("value", ""),
                        "text": norm(o.get_text(" ", strip=True)),
                        "selected": o.has_attr("selected"),
                    }
                    for o in tag.find_all("option")
                ]
            controls.append(item)
        forms.append({
            "form_index": fi,
            "id": form.get("id"),
            "name": form.get("name"),
            "method": (form.get("method") or "GET").upper(),
            "action": urljoin(base_url, form.get("action") or base_url),
            "onsubmit": form.get("onsubmit"),
            "controls": controls,
            "html": str(form)[:12000],
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
            typ = (c.get("type") or "text").lower()
            if typ in {"submit", "button", "image", "reset"}:
                continue
            payload[name] = c.get("value", "") or ""
        else:
            payload[name] = c.get("value", "") or ""
    return payload


def extract_post_identity(href_raw: str, title: str):
    p = urlparse(href_raw)
    qs = parse_qs(p.query)
    ids = []
    for k in POST_ID_KEYS:
        if k in qs and qs[k]:
            ids.append(f"{k}={qs[k][0]}")
    if ids:
        return "|".join(ids)
    m = re.search(r"(?:view|detail|read|goView|boardView)\s*\(([^)]{1,160})\)", href_raw, re.I)
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
        href_signal = bool(re.search(r"(?:bcIdx|bIdx|board|bbs|view|detail|read|seq|idx)", href_raw, re.I))
        title_signal = bool(re.search(r"(?:경기도보|제\s*\d+\s*호|고시|공고|도보)", title))
        if not (href_signal or title_signal):
            continue
        identity = extract_post_identity(href_raw, title)
        key = (identity, title)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"identity": identity, "title": title, "url": href})
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


def script_evidence(soup: BeautifulSoup, search_form):
    evidence = []
    needles = [KEYWORD_FIELD, "searchStartDate", "searchEndDate", "gubunCk", "submit", "board.do"]
    blocks = []
    for s in soup.find_all("script"):
        text = s.get_text("\n", strip=False) or ""
        src = s.get("src")
        if src:
            blocks.append({"source": urljoin(ENTRY, src), "text": ""})
        if text:
            blocks.append({"source": "inline", "text": text})

    for block in blocks:
        text = block["text"]
        if not text:
            continue
        if not any(n.lower() in text.lower() for n in needles):
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if any(n.lower() in line.lower() for n in needles):
                lo = max(0, i - 3)
                hi = min(len(lines), i + 4)
                snippet = "\n".join(lines[lo:hi])
                evidence.append({"source": block["source"], "snippet": snippet[:3000]})

    if search_form:
        evidence.append({
            "source": "search_form_attributes",
            "snippet": json.dumps({
                "id": search_form.get("id"),
                "name": search_form.get("name"),
                "method": search_form.get("method"),
                "action": search_form.get("action"),
                "onsubmit": search_form.get("onsubmit"),
                "button_controls": [
                    c for c in search_form["controls"]
                    if c.get("tag") == "button" or (c.get("type") or "").lower() in {"submit", "button", "image"}
                ],
            }, ensure_ascii=False),
        })
    return evidence[:80]


def discover_candidate_submission_patterns(search_form, evidence):
    candidates = []
    seen = set()

    if search_form:
        action = search_form["action"]
        declared = search_form["method"]
        for method in [declared, "POST" if declared == "GET" else "GET"]:
            key = (method, action)
            if key not in seen:
                seen.add(key)
                candidates.append({"method": method, "action": action, "reason": "FORM_DECLARED_OR_ALTERNATE_METHOD"})

    text = "\n".join(e.get("snippet", "") for e in evidence)
    for m in re.finditer(r"(?:action\s*=\s*|\.action\s*=\s*)['\"]([^'\"]+)['\"]", text, re.I):
        action = urljoin(ENTRY, m.group(1))
        if urlparse(action).hostname != HOST:
            continue
        for method in ["GET", "POST"]:
            key = (method, action)
            if key not in seen:
                seen.add(key)
                candidates.append({"method": method, "action": action, "reason": "JAVASCRIPT_ACTION_LITERAL"})

    # Keep the experiment bounded.
    return candidates[:6]


def run_candidate(session, candidate, payload, term, baseline_rows):
    p = dict(payload)
    p["searchStartDate"] = ""
    p["searchEndDate"] = ""
    p[KEYWORD_FIELD] = term

    if candidate["method"] == "POST":
        r = post(session, candidate["action"], data=p)
    else:
        r = get(session, candidate["action"], params=p)

    if r is None:
        return {
            "method": candidate["method"],
            "action": candidate["action"],
            "reason": candidate["reason"],
            "term": term,
            "http": None,
            "credible_filtering": False,
            "technical_unknown": True,
        }

    rows = canonical_posts(r.text, r.url)
    stats = overlap(baseline_rows, rows)
    title_match_count = sum(1 for x in rows if term in x["title"])
    credible = (
        r.status_code == 200
        and stats["changed"]
        and (stats["strict_subset"] or stats["removed_count"] > 0)
        and (title_match_count > 0 or stats["result_count"] < stats["baseline_count"])
    )
    return {
        "method": candidate["method"],
        "action": candidate["action"],
        "reason": candidate["reason"],
        "term": term,
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
    print("GYEONGGI GAZETTE BOARD JAVASCRIPT SEARCH SUBMISSION CONTRACT RECOVERY - S230H-JS")
    print("=" * 78)
    print("Purpose: recover real search submission semantics from form/JavaScript using generic controls only")
    print("UQQ700 target search: DISABLED")
    print("Generic positive controls only")
    print("Filtering success != designation/current validity/site inclusion")
    print("Filtering failure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    previous = load_json(IN_HARDENED)
    assert previous.get("contract_qualified") is False
    assert previous.get("uqq700_target_search_executed") is False

    session = requests.Session()
    entry = get(session, ENTRY)
    if entry is None:
        raise RuntimeError("GG gazette board entry request failed")

    soup = BeautifulSoup(entry.text, "html.parser")
    forms = form_snapshot(soup, entry.url)
    search_form = select_search_form(forms)
    baseline_rows = canonical_posts(entry.text, entry.url)
    evidence = script_evidence(soup, search_form)
    candidates = discover_candidate_submission_patterns(search_form, evidence)
    payload = default_payload(search_form) if search_form else {}

    # Preserve official board state observed on the page.
    if search_form:
        payload["bsIdx"] = payload.get("bsIdx") or "769"
        payload["menuId"] = payload.get("menuId") or "1786"
        if "gubunCk" in payload and not payload.get("gubunCk"):
            payload["gubunCk"] = "12"

    experiments = []
    for candidate in candidates:
        for term in GENERIC_TERMS:
            experiments.append(run_candidate(session, candidate, payload, term, baseline_rows))

    grouped = {}
    for e in experiments:
        key = (e["method"], e["action"])
        grouped.setdefault(key, []).append(e)

    qualified = []
    for (method, action), rows in grouped.items():
        if len(rows) != len(GENERIC_TERMS):
            continue
        if all(r.get("http") == 200 and r.get("credible_filtering") and not r.get("technical_unknown") for r in rows):
            qualified.append({
                "method": method,
                "action": action,
                "runs": len(rows),
                "result_counts": [r.get("result_count") for r in rows],
                "removed_counts": [r.get("removed_count") for r in rows],
                "title_match_counts": [r.get("title_match_count") for r in rows],
            })

    contract_qualified = len(qualified) == 1
    if contract_qualified:
        classification = "GYEONGGI_GAZETTE_BOARD_JAVASCRIPT_SUBMISSION_CONTRACT_QUALIFIED"
        semantic = "EXACTLY_ONE_BOUNDED_SUBMISSION_PATTERN_FILTERED_CANONICAL_POST_IDENTITIES_FOR_ALL_GENERIC_POSITIVE_CONTROLS"
        next_action = "RUN_ONLY_EXACT_VARIANT_WEAK_UQQ700_BOUNDED_SEARCH_THROUGH_THE_RECOVERED_SUBMISSION_PATTERN"
    else:
        classification = "GYEONGGI_GAZETTE_BOARD_JAVASCRIPT_SUBMISSION_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "NO_UNIQUE_SUBMISSION_PATTERN_WAS_PROVED_TO_FILTER_CANONICAL_POST_IDENTITIES_FOR_ALL_GENERIC_POSITIVE_CONTROLS"
        next_action = "INSPECT_ONLY_THE_REMAINING_JAVASCRIPT_OR_SERVER_SIDE_SEARCH_TRIGGER_WITHOUT_UQQ700_QUERY_OR_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-S230H-JS",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "entry_url": ENTRY,
        "entry_http": entry.status_code,
        "previous_hardening_loaded": True,
        "uqq700_target_search_executed": False,
        "form_count": len(forms),
        "search_form_found": search_form is not None,
        "search_form": search_form,
        "baseline_post_count": len(baseline_rows),
        "script_evidence_count": len(evidence),
        "script_evidence": evidence,
        "candidate_submission_pattern_count": len(candidates),
        "candidate_submission_patterns": candidates,
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
    print("SUBMISSION CONTRACT RECOVERY")
    print("=" * 78)
    print(f"ENTRY HTTP: {entry.status_code}")
    print(f"FORM COUNT: {len(forms)}")
    print(f"SEARCH FORM FOUND: {search_form is not None}")
    print(f"BASELINE POST COUNT: {len(baseline_rows)}")
    print(f"SCRIPT EVIDENCE COUNT: {len(evidence)}")
    print(f"CANDIDATE SUBMISSION PATTERN COUNT: {len(candidates)}")
    print(f"POSITIVE CONTROL EXPERIMENT COUNT: {len(experiments)}")
    print(f"QUALIFIED CONTRACT COUNT: {len(qualified)}")
    print(f"CONTRACT QUALIFIED: {contract_qualified}")

    for e in evidence[:20]:
        print("SCRIPT_EVIDENCE:", json.dumps(e, ensure_ascii=False))
    for c in candidates:
        print("CANDIDATE_PATTERN:", json.dumps(c, ensure_ascii=False))
    for e in experiments:
        print("POSITIVE_CONTROL:", json.dumps({k: e.get(k) for k in [
            "method", "action", "reason", "term", "http", "baseline_count", "result_count",
            "intersection_count", "removed_count", "added_count", "changed", "strict_subset",
            "title_match_count", "credible_filtering", "technical_unknown", "final_url"
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
        "previous hardening loaded": out["previous_hardening_loaded"] is True,
        "entry host gg": urlparse(ENTRY).hostname == HOST,
        "no UQQ700 target search": out["uqq700_target_search_executed"] is False,
        "generic controls only": GENERIC_TERMS == ["경기도보", "고시"],
        "candidate patterns bounded": len(candidates) <= 6,
        "positive control experiments bounded": len(experiments) <= 12,
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
            "GYEONGGI_GAZETTE_BOARD_JAVASCRIPT_SUBMISSION_CONTRACT_QUALIFIED",
            "GYEONGGI_GAZETTE_BOARD_JAVASCRIPT_SUBMISSION_CONTRACT_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S230H-JS validation failed")


if __name__ == "__main__":
    main()
