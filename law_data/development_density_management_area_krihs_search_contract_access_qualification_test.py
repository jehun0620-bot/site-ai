# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_S230J = OUT_DIR / "development_density_management_area_residual_historical_source_family_reranking_after_gyeonggi_closure.json"
OUT = OUT_DIR / "development_density_management_area_krihs_search_contract_access_qualification.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
ENTRY_CANDIDATES = [
    "https://www.krihs.re.kr/",
    "https://library.krihs.re.kr/",
]
TIMEOUT = 20
GENERIC_TERMS = ["국토연구원", "도시계획"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
}

SEARCH_NAME_RE = re.compile(r"(?:search|query|keyword|kwd|sch|find|word|text|title|subject)", re.I)
RESULT_HINT_RE = re.compile(r"(?:search|result|view|detail|board|article|report|publication|library|research)", re.I)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def request(session: requests.Session, method: str, url: str, payload=None):
    try:
        if method == "POST":
            return session.post(url, data=payload or {}, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        return session.get(url, params=payload or {}, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException:
        return None


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def default_payload(form):
    payload = {}
    for tag in form.find_all(["input", "select", "textarea"]):
        name = tag.get("name")
        if not name:
            continue
        if tag.name == "select":
            opt = tag.find("option", selected=True) or tag.find("option")
            payload[name] = opt.get("value", "") if opt else ""
        elif tag.name == "input":
            typ = (tag.get("type") or "text").lower()
            if typ in {"submit", "button", "image", "reset"}:
                continue
            payload[name] = tag.get("value", "") or ""
        else:
            payload[name] = tag.get_text() or ""
    return payload


def canonical_signature(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    seen = set()
    for a in soup.find_all("a", href=True):
        title = norm(a.get_text(" ", strip=True))
        href_raw = a.get("href") or ""
        if not title:
            continue
        if not RESULT_HINT_RE.search(href_raw) and len(title) < 4:
            continue
        href = urljoin(base_url, href_raw)
        key = f"{title}|{href}"
        if key in seen:
            continue
        seen.add(key)
        rows.append(key)
    return set(rows)


def find_candidate_forms(soup: BeautifulSoup, base_url: str):
    out = []
    for fi, form in enumerate(soup.find_all("form"), 1):
        method = (form.get("method") or "GET").upper()
        action = urljoin(base_url, form.get("action") or base_url)
        fields = []
        for tag in form.find_all(["input", "textarea"]):
            name = tag.get("name")
            if name and SEARCH_NAME_RE.search(name):
                fields.append(name)
        if fields:
            out.append({
                "form_index": fi,
                "method": method,
                "action": action,
                "fields": sorted(set(fields)),
                "payload": default_payload(form),
            })
    return out[:20]


def qualify_entry(session: requests.Session, url: str):
    r = request(session, "GET", url)
    if r is None:
        return {"input_url": url, "http": None, "qualified": False, "forms": []}
    soup = BeautifulSoup(r.text, "html.parser")
    forms = find_candidate_forms(soup, r.url)
    official_host = (urlparse(r.url).hostname or "").endswith("krihs.re.kr")
    return {
        "input_url": url,
        "http": r.status_code,
        "final_url": r.url,
        "host": urlparse(r.url).hostname,
        "official_host": official_host,
        "form_count": len(soup.find_all("form")),
        "candidate_search_form_count": len(forms),
        "forms": forms,
        "qualified": r.status_code == 200 and official_host and bool(forms),
    }


def run_positive_control(session: requests.Session, baseline_sig, contract, term: str):
    payload = dict(contract["payload"])
    payload[contract["field"]] = term
    r = request(session, contract["method"], contract["action"], payload)
    if r is None:
        return {"term": term, "http": None, "changed": False, "technical_unknown": True}
    sig = canonical_signature(r.text, r.url)
    return {
        "term": term,
        "http": r.status_code,
        "final_url": r.url,
        "baseline_count": len(baseline_sig),
        "result_count": len(sig),
        "changed": sig != baseline_sig,
        "removed_count": len(baseline_sig - sig),
        "added_count": len(sig - baseline_sig),
        "technical_unknown": r.status_code != 200,
    }


def main():
    print("=" * 78)
    print("KRIHS SEARCH CONTRACT ACCESS QUALIFICATION")
    print("=" * 78)
    print("Purpose: qualify KRIHS entry/search contract with generic controls only")
    print("UQQ700 target search: DISABLED")
    print("Search hit/no-hit != legal fact")
    print("UQQ700 final resolution: UNKNOWN")

    s230j = load_json(IN_S230J)
    selected = s230j.get("selected_next_source_family") or {}
    if isinstance(selected, dict):
        selected_name = selected.get("source_family")
    else:
        selected_name = selected
    assert selected_name == "KRIHS_SEARCH_CONTRACT_ACCESS"

    session = requests.Session()
    entries = [qualify_entry(session, url) for url in ENTRY_CANDIDATES]
    qualified_entries = [e for e in entries if e.get("qualified")]

    experiments = []
    candidate_contracts = []
    for entry in qualified_entries:
        baseline = request(session, "GET", entry["final_url"])
        if baseline is None or baseline.status_code != 200:
            continue
        baseline_sig = canonical_signature(baseline.text, baseline.url)
        for form in entry["forms"]:
            for field in form["fields"][:5]:
                contract = {
                    "entry_url": entry["final_url"],
                    "method": form["method"],
                    "action": form["action"],
                    "field": field,
                    "payload": form["payload"],
                }
                runs = [run_positive_control(session, baseline_sig, contract, term) for term in GENERIC_TERMS]
                experiments.append({"contract": contract, "runs": runs})
                if all(r.get("http") == 200 and r.get("changed") and not r.get("technical_unknown") for r in runs):
                    candidate_contracts.append({
                        "entry_url": entry["final_url"],
                        "method": form["method"],
                        "action": form["action"],
                        "field": field,
                        "runs": runs,
                    })
                if len(experiments) >= 30:
                    break
            if len(experiments) >= 30:
                break
        if len(experiments) >= 30:
            break

    contract_qualified = len(candidate_contracts) == 1
    if contract_qualified:
        classification = "KRIHS_SEARCH_CONTRACT_ACCESS_QUALIFIED"
        semantic = "EXACTLY_ONE_KRIHS_SEARCH_CONTRACT_CHANGED_CANONICAL_RESULT_SIGNATURES_FOR_BOTH_GENERIC_POSITIVE_CONTROLS"
        next_action = "RUN_BOUNDED_UQQ700_EXACT_VARIANT_WEAK_SEARCH_ONLY_THROUGH_THE_QUALIFIED_KRIHS_CONTRACT"
    elif qualified_entries:
        classification = "KRIHS_SEARCH_CONTRACT_ACCESS_TECHNICAL_UNKNOWN"
        semantic = "KRIHS_OFFICIAL_ENTRY_AND_SEARCH_SURFACES_WERE_FOUND_BUT_NO_UNIQUE_FILTERING_CONTRACT_WAS_QUALIFIED"
        next_action = "HARDEN_ONLY_THE_KRIHS_SEARCH_SUBMISSION_OR_RESULT_ROW_SEMANTICS_WITHOUT_UQQ700_QUERY"
    else:
        classification = "KRIHS_ENTRY_OR_SEARCH_SURFACE_NOT_QUALIFIED_TECHNICAL_UNKNOWN"
        semantic = "NO_KRIHS_OFFICIAL_ENTRY_EXPOSED_A_QUALIFIED_SEARCH_FORM_IN_THE_BOUNDED_ENTRY_PROBES"
        next_action = "QUALIFY_ONLY_KRIHS_OFFICIAL_SEARCH_ENTRY_OR_ALTERNATE_OFFICIAL_SUBDOMAIN_WITHOUT_UQQ700_QUERY"

    out = {
        "step": "STEP 17-KRIHS-CONTRACT",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "s230j_loaded": True,
        "uqq700_target_search_executed": False,
        "entry_count": len(entries),
        "entries": entries,
        "qualified_entry_count": len(qualified_entries),
        "positive_control_experiment_count": len(experiments),
        "positive_control_experiments": experiments,
        "qualified_contract_count": len(candidate_contracts),
        "qualified_contracts": candidate_contracts,
        "contract_qualified": contract_qualified,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "search_hit_equals_designation": False,
            "search_hit_equals_current_validity": False,
            "search_hit_equals_site_inclusion": False,
            "no_hit_equals_legal_absence": False,
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
    print("QUALIFICATION")
    print("=" * 78)
    print(f"ENTRY COUNT: {len(entries)}")
    print(f"QUALIFIED ENTRY COUNT: {len(qualified_entries)}")
    print(f"POSITIVE CONTROL EXPERIMENT COUNT: {len(experiments)}")
    print(f"QUALIFIED CONTRACT COUNT: {len(candidate_contracts)}")
    print(f"CONTRACT QUALIFIED: {contract_qualified}")
    for e in entries:
        print("ENTRY:", json.dumps({k: e.get(k) for k in ["input_url", "http", "final_url", "host", "official_host", "form_count", "candidate_search_form_count", "qualified"]}, ensure_ascii=False))
    for x in experiments:
        print("POSITIVE_CONTROL_EXPERIMENT:", json.dumps(x, ensure_ascii=False))
    for c in candidate_contracts:
        print("QUALIFIED_CONTRACT:", json.dumps(c, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("UQQ700 target search executed: False")
    print("No-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S230J loaded": out["s230j_loaded"] is True,
        "no UQQ700 target search": out["uqq700_target_search_executed"] is False,
        "generic controls only": GENERIC_TERMS == ["국토연구원", "도시계획"],
        "entry probes bounded": len(entries) <= 2,
        "positive controls bounded": len(experiments) <= 30,
        "search hit not designation": out["summary"]["search_hit_equals_designation"] is False,
        "search hit not validity": out["summary"]["search_hit_equals_current_validity"] is False,
        "search hit not site inclusion": out["summary"]["search_hit_equals_site_inclusion"] is False,
        "no hit not legal absence": out["summary"]["no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
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
        raise AssertionError("KRIHS search contract qualification validation failed")


if __name__ == "__main__":
    main()
