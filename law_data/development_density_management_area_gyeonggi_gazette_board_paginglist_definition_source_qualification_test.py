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
IN_PREV = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_searchfields_paginglist_contract_recovery.json"
OUT = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_paginglist_definition_source_qualification.json"

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


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def get(session: requests.Session, url: str):
    try:
        return session.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException:
        return None


def collect_scripts(session: requests.Session, soup: BeautifulSoup, base_url: str):
    out = []
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
                out.append({"source": url, "text": r.text, "external": True})
        else:
            text = script.get_text("\n", strip=False) or ""
            if text:
                out.append({"source": f"inline:{i}", "text": text, "external": False})
    return out[:100]


def context_snippets(text: str, pattern: re.Pattern, radius=1400, limit=12):
    hits = []
    for m in pattern.finditer(text):
        lo = max(0, m.start() - radius)
        hi = min(len(text), m.end() + radius)
        hits.append(text[lo:hi])
        if len(hits) >= limit:
            break
    return hits


def extract_paging_evidence(sources):
    evidence = []
    patterns = [
        ("PAGINGLIST_TOKEN", re.compile(r"\bPagingList\b", re.I)),
        ("SETPAGE_TOKEN", re.compile(r"\bsetPage\s*\(", re.I)),
        ("WINDOW_PAGINGLIST", re.compile(r"window\s*\.\s*PagingList", re.I)),
        ("NEW_PAGING", re.compile(r"new\s+[A-Za-z_$][\w$]*(?:Paging|Page|List)[A-Za-z0-9_$]*\s*\(", re.I)),
        ("PROTOTYPE_SETPAGE", re.compile(r"prototype\s*\.\s*setPage\s*=\s*function", re.I)),
        ("OBJECT_SETPAGE", re.compile(r"setPage\s*:\s*function\s*\(", re.I)),
        ("ASSIGN_SETPAGE", re.compile(r"\.setPage\s*=\s*function\s*\(", re.I)),
        ("AJAX_TOKEN", re.compile(r"\$\.ajax\s*\(|\.ajax\s*\(|fetch\s*\(|\.load\s*\(|\$\.get\s*\(|\$\.post\s*\(", re.I)),
        ("PAGE_PARAM_TOKEN", re.compile(r"(?:pageIndex|pageNo|pageNum|pageUnit|currentPage|page)\b", re.I)),
    ]
    for src in sources:
        text = src["text"]
        source_hits = []
        for kind, pat in patterns:
            snippets = context_snippets(text, pat)
            for snip in snippets:
                source_hits.append({"kind": kind, "snippet": snip[:4000]})
        if source_hits:
            evidence.append({"source": src["source"], "external": src["external"], "hits": source_hits[:40]})
    return evidence[:40]


def score_source(item):
    kinds = {h["kind"] for h in item["hits"]}
    score = 0
    if "PAGINGLIST_TOKEN" in kinds:
        score += 8
    if "SETPAGE_TOKEN" in kinds:
        score += 6
    if "WINDOW_PAGINGLIST" in kinds:
        score += 5
    if "PROTOTYPE_SETPAGE" in kinds or "OBJECT_SETPAGE" in kinds or "ASSIGN_SETPAGE" in kinds:
        score += 10
    if "AJAX_TOKEN" in kinds:
        score += 4
    if "PAGE_PARAM_TOKEN" in kinds:
        score += 2
    return score


def extract_candidate_definitions(evidence):
    candidates = []
    for item in evidence:
        score = score_source(item)
        if score <= 0:
            continue
        combined = "\n".join(h["snippet"] for h in item["hits"])
        endpoint_literals = []
        for m in re.finditer(r"(?:url\s*:\s*|\.load\s*\(|\.get\s*\(|\.post\s*\(|fetch\s*\()\s*['\"]([^'\"]+)['\"]", combined, re.I):
            endpoint_literals.append(urljoin(ENTRY, m.group(1)))
        methods = []
        if re.search(r"type\s*:\s*['\"]POST['\"]|method\s*:\s*['\"]POST['\"]|\.post\s*\(", combined, re.I):
            methods.append("POST")
        if re.search(r"type\s*:\s*['\"]GET['\"]|method\s*:\s*['\"]GET['\"]|\.get\s*\(", combined, re.I):
            methods.append("GET")
        candidates.append({
            "source": item["source"],
            "score": score,
            "endpoint_literals": sorted(set(endpoint_literals))[:20],
            "method_hints": sorted(set(methods)),
            "has_paginglist_token": any(h["kind"] == "PAGINGLIST_TOKEN" for h in item["hits"]),
            "has_setpage_token": any(h["kind"] == "SETPAGE_TOKEN" for h in item["hits"]),
            "has_function_definition_signal": any(h["kind"] in {"PROTOTYPE_SETPAGE", "OBJECT_SETPAGE", "ASSIGN_SETPAGE"} for h in item["hits"]),
            "sample": combined[:9000],
        })
    candidates.sort(key=lambda x: (-x["score"], x["source"]))
    return candidates[:20]


def main():
    print("=" * 78)
    print("GYEONGGI GAZETTE BOARD PagingList DEFINITION SOURCE QUALIFICATION - S230H-JS4")
    print("=" * 78)
    print("Purpose: identify PagingList/setPage definition source and request-shape evidence only")
    print("UQQ700 target search: DISABLED")
    print("Generic filtering requests: DISABLED")
    print("Source recovery failure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    prev = load_json(IN_PREV)
    assert prev.get("contract_qualified") is False
    assert prev.get("uqq700_target_search_executed") is False

    session = requests.Session()
    entry = get(session, ENTRY)
    if entry is None:
        raise RuntimeError("GG gazette board entry request failed")

    soup = BeautifulSoup(entry.text, "html.parser")
    scripts = collect_scripts(session, soup, entry.url)
    evidence = extract_paging_evidence(scripts)
    candidates = extract_candidate_definitions(evidence)

    qualified = [c for c in candidates if c["has_paginglist_token"] and c["has_setpage_token"] and c["has_function_definition_signal"]]
    source_qualified = len(qualified) >= 1

    if source_qualified:
        classification = "GYEONGGI_GAZETTE_BOARD_PAGINGLIST_DEFINITION_SOURCE_QUALIFIED"
        semantic = "ONE_OR_MORE_OFFICIAL_SCRIPT_SOURCES_EXPOSE_PAGINGLIST_SETPAGE_DEFINITION_SIGNALS_WITH_REQUEST_SHAPE_EVIDENCE"
        next_action = "REPLAY_ONLY_THE_EXACT_QUALIFIED_PAGINGLIST_REQUEST_SHAPE_WITH_GENERIC_CONTROLS_BEFORE_ANY_UQQ700_QUERY"
    elif candidates:
        classification = "GYEONGGI_GAZETTE_BOARD_PAGINGLIST_REFERENCE_FOUND_DEFINITION_NOT_QUALIFIED_TECHNICAL_UNKNOWN"
        semantic = "PAGING_RELATED_REFERENCES_WERE_FOUND_BUT_NO_SOURCE_EXPOSED_A_QUALIFIED_SETPAGE_FUNCTION_DEFINITION"
        next_action = "HARDEN_ONLY_THE_TOP_PAGING_SOURCE_OR_ITS_DEPENDENCY_CHAIN_WITHOUT_SEARCH_EXECUTION_OR_NEGATIVE_INFERENCE"
    else:
        classification = "GYEONGGI_GAZETTE_BOARD_PAGINGLIST_DEFINITION_SOURCE_NOT_FOUND_TECHNICAL_UNKNOWN"
        semantic = "NO_QUALIFIED_PAGINGLIST_OR_SETPAGE_DEFINITION_SOURCE_WAS_FOUND_IN_BOUNDED_OFFICIAL_SCRIPT_SOURCES"
        next_action = "QUALIFY_ONLY_DYNAMIC_OR_INDIRECT_SCRIPT_DEPENDENCIES_WITHOUT_SEARCH_EXECUTION_OR_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-S230H-JS4",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "entry_url": ENTRY,
        "entry_http": entry.status_code,
        "previous_js3_loaded": True,
        "uqq700_target_search_executed": False,
        "generic_filtering_request_executed": False,
        "script_source_count": len(scripts),
        "paging_evidence_source_count": len(evidence),
        "paging_evidence": evidence,
        "candidate_definition_source_count": len(candidates),
        "candidate_definition_sources": candidates,
        "qualified_definition_source_count": len(qualified),
        "qualified_definition_sources": qualified,
        "source_qualified": source_qualified,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
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
    print("PAGINGLIST SOURCE QUALIFICATION")
    print("=" * 78)
    print(f"ENTRY HTTP: {entry.status_code}")
    print(f"SCRIPT SOURCE COUNT: {len(scripts)}")
    print(f"PAGING EVIDENCE SOURCE COUNT: {len(evidence)}")
    print(f"CANDIDATE DEFINITION SOURCE COUNT: {len(candidates)}")
    print(f"QUALIFIED DEFINITION SOURCE COUNT: {len(qualified)}")
    print(f"SOURCE QUALIFIED: {source_qualified}")

    for item in evidence:
        print("PAGING_EVIDENCE_SOURCE:", json.dumps({"source": item["source"], "kinds": sorted({h["kind"] for h in item["hits"]}), "hit_count": len(item["hits"])}, ensure_ascii=False))
    for c in candidates:
        print("CANDIDATE_DEFINITION_SOURCE:", json.dumps({k: c.get(k) for k in ["source", "score", "endpoint_literals", "method_hints", "has_paginglist_token", "has_setpage_token", "has_function_definition_signal"]}, ensure_ascii=False))
        print("CANDIDATE_DEFINITION_SAMPLE:", json.dumps({"source": c["source"], "sample": c["sample"][:7000]}, ensure_ascii=False))
    for q in qualified:
        print("QUALIFIED_DEFINITION_SOURCE:", json.dumps({k: q.get(k) for k in ["source", "score", "endpoint_literals", "method_hints"]}, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("UQQ700 target search executed: False")
    print("Generic filtering request executed: False")
    print("Search/source recovery failure == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "previous JS3 loaded": out["previous_js3_loaded"] is True,
        "entry host gg": urlparse(ENTRY).hostname == HOST,
        "no UQQ700 target search": out["uqq700_target_search_executed"] is False,
        "no generic filtering request": out["generic_filtering_request_executed"] is False,
        "script sources bounded": len(scripts) <= 100,
        "candidate sources bounded": len(candidates) <= 20,
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
            "GYEONGGI_GAZETTE_BOARD_PAGINGLIST_DEFINITION_SOURCE_QUALIFIED",
            "GYEONGGI_GAZETTE_BOARD_PAGINGLIST_REFERENCE_FOUND_DEFINITION_NOT_QUALIFIED_TECHNICAL_UNKNOWN",
            "GYEONGGI_GAZETTE_BOARD_PAGINGLIST_DEFINITION_SOURCE_NOT_FOUND_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S230H-JS4 validation failed")


if __name__ == "__main__":
    main()
