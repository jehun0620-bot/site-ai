# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_S229B = OUT_DIR / "development_density_management_area_national_regional_planning_research_document_positive_control_search_contract_qualification.json"
OUT = OUT_DIR / "development_density_management_area_national_regional_planning_research_document_uqq700_bounded_target_search.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT"

QUERIES = [
    {"query": "개발밀도관리구역", "class": "EXACT"},
    {"query": "개발밀도 관리구역", "class": "VARIANT"},
    {"query": "개발밀도", "class": "WEAK"},
]

EXPECTED_CANONICAL_KEYS = {
    "GRI|GET|/web/contents/webSearch.do|kwd",
    "GRI|GET|/web/contents/resreport.do|schStr",
}


def curl_get(url: str, params: dict, referer: str | None = None) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "redirects": None, "body": b"", "stderr": "curl not found"}
    sep = "&" if "?" in url else "?"
    full_url = url + sep + urlencode(params, doseq=True)
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "120",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    ]
    if referer:
        cmd += ["-e", referer]
    cmd += ["-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}|%{num_redirects}", full_url]
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 3)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
        content_type = parts[2] if len(parts) > 2 else None
        redirects = parts[3] if len(parts) > 3 else None
    else:
        body, http, final_url, content_type, redirects = raw, None, None, None, None
    return {
        "http": http,
        "final_url": final_url,
        "content_type": content_type,
        "redirects": redirects,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def decode(body: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace")


def strip_tags(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s)
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def count_occurrences(text: str, query: str) -> int:
    if not query:
        return 0
    return text.count(query)


def extract_candidate_links(base_url: str, text: str, query: str) -> list[dict]:
    rows = []
    seen = set()
    for m in re.finditer(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text):
        href = html.unescape(m.group(1))
        label = strip_tags(m.group(2))
        blob = f"{label} {href}"
        if query not in blob and "개발밀도" not in blob:
            continue
        if href.startswith("javascript:") or href.startswith("#"):
            continue
        if href.startswith("http://") or href.startswith("https://"):
            url = href
        else:
            p = urlparse(base_url)
            if href.startswith("/"):
                url = f"{p.scheme}://{p.netloc}{href}"
            else:
                base_dir = base_url.rsplit("/", 1)[0] + "/"
                url = base_dir + href
        key = (url, label)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"url": url, "label": label})
    return rows[:50]


def make_payload(contract: dict, query: str) -> dict:
    payload = {}
    # Start from the positive-control payload shape when available, but only use
    # fields that were observed in the qualified contract. Values other than
    # the target query field stay neutral/blank to avoid inventing filters.
    for k in contract.get("payload_keys") or []:
        payload[k] = ""
    payload[contract["query_field"]] = query

    # Source-specific neutral pagination defaults observed on GRI surfaces.
    if contract.get("semantic_contract_role") == "RESEARCH_REPORT_SEARCH":
        defaults = {
            "schM": "list",
            "page": "1",
            "viewCount": "10",
            "schPrjType": "ALL",
            "schStartYear": "",
            "schEndYear": "",
            "schSubj1": "",
            "schSubj2": "",
            "schFld": "ALL",
        }
        for k, v in defaults.items():
            if k in payload or k in {"schM", "page", "viewCount", "schPrjType", "schStartYear", "schEndYear", "schSubj1", "schSubj2", "schFld"}:
                payload[k] = v
        payload[contract["query_field"]] = query
    return payload


def classify_response(contract: dict, query_row: dict, rr: dict) -> dict:
    text = decode(rr.get("body") or b"")
    plain = strip_tags(text)
    query = query_row["query"]
    query_occurrence_count = count_occurrences(text, query) + count_occurrences(plain, query)
    weak_occurrence_count = count_occurrences(text, "개발밀도") + count_occurrences(plain, "개발밀도")
    query_echo = query in text or query in plain
    body_ok = len(rr.get("body") or b"") > 1000
    http_ok = rr.get("http") == "200"
    error_signal = any(x in plain.lower() for x in ["forbidden", "잘못된 접근", "페이지를 찾을 수 없습니다", "오류가 발생", "access denied"])
    technical_unknown = not http_ok or not body_ok or error_signal
    candidate_links = extract_candidate_links(rr.get("final_url") or contract["action_url"], text, query)

    if technical_unknown:
        status = "TECHNICAL_UNKNOWN"
        content_hit = False
    else:
        if query_row["class"] == "EXACT":
            content_hit = query_occurrence_count > 0
            status = "EXACT_HIT" if content_hit else "EXACT_NO_HIT"
        elif query_row["class"] == "VARIANT":
            content_hit = query_occurrence_count > 0
            status = "VARIANT_HIT" if content_hit else "VARIANT_NO_HIT"
        else:
            content_hit = weak_occurrence_count > 0
            status = "WEAK_HIT" if content_hit else "WEAK_NO_HIT"

    return {
        "source_id": contract["source_id"],
        "name": contract["name"],
        "semantic_contract_role": contract["semantic_contract_role"],
        "canonical_contract_key": contract["canonical_contract_key"],
        "query": query,
        "query_class": query_row["class"],
        "method": contract["method"],
        "action_url": contract["action_url"],
        "query_field": contract["query_field"],
        "http": rr.get("http"),
        "final_url": rr.get("final_url"),
        "content_type": rr.get("content_type"),
        "redirects": rr.get("redirects"),
        "body_size": len(rr.get("body") or b""),
        "query_echo": query_echo,
        "query_occurrence_count": query_occurrence_count,
        "weak_occurrence_count": weak_occurrence_count,
        "content_hit": content_hit,
        "status": status,
        "technical_unknown": technical_unknown,
        "candidate_link_count": len(candidate_links),
        "candidate_links": candidate_links,
        "text_sample": plain[:1500],
        "source_role": "CONTEXT_AND_REVERSE_LOOKUP_ONLY",
        "designation_identity_promoted": False,
        "current_validity_promoted": False,
        "site_inclusion_promoted": False,
    }


def main() -> None:
    print("=" * 78)
    print("NATIONAL / REGIONAL PLANNING RESEARCH DOCUMENT UQQ700 BOUNDED TARGET SEARCH - S229C")
    print("=" * 78)
    print("Purpose: bounded UQQ700 search on semantically hardened canonical GRI contracts")
    print("Request budget: 2 canonical contracts x 3 queries = 6")
    print("Planning/research hit != designation/current validity/site inclusion")
    print("Planning/research no-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    if not IN_S229B.exists():
        raise FileNotFoundError(f"Missing hardened S229B output: {IN_S229B}")
    s229b = json.loads(IN_S229B.read_text(encoding="utf-8"))
    contracts = s229b.get("canonical_qualified_search_contracts") or []

    canonical_keys = {c.get("canonical_contract_key") for c in contracts}
    if canonical_keys != EXPECTED_CANONICAL_KEYS:
        raise AssertionError(f"Unexpected canonical contract set: {sorted(canonical_keys)}")
    if any(c.get("source_id") != "GRI" for c in contracts):
        raise AssertionError("S229C may use only GRI canonical contracts")
    if any(c.get("method") != "GET" for c in contracts):
        raise AssertionError("S229C bounded runner supports only the qualified GRI GET contracts")

    rows = []
    for contract in sorted(contracts, key=lambda x: x["canonical_contract_key"]):
        for q in QUERIES:
            payload = make_payload(contract, q["query"])
            rr = curl_get(contract["action_url"], payload, contract.get("page_url"))
            row = classify_response(contract, q, rr)
            row["request_payload_keys"] = sorted(payload.keys())
            rows.append(row)
            print(json.dumps({
                "contract": row["canonical_contract_key"],
                "query_class": row["query_class"],
                "query": row["query"],
                "http": row["http"],
                "query_echo": row["query_echo"],
                "query_occurrence_count": row["query_occurrence_count"],
                "weak_occurrence_count": row["weak_occurrence_count"],
                "content_hit": row["content_hit"],
                "status": row["status"],
                "candidate_link_count": row["candidate_link_count"],
            }, ensure_ascii=False))

    request_count = len(rows)
    exact_hits = [r for r in rows if r["status"] == "EXACT_HIT"]
    variant_hits = [r for r in rows if r["status"] == "VARIANT_HIT"]
    weak_hits = [r for r in rows if r["status"] == "WEAK_HIT"]
    no_hits = [r for r in rows if r["status"].endswith("NO_HIT")]
    technical_unknowns = [r for r in rows if r["status"] == "TECHNICAL_UNKNOWN"]

    candidate_map = {}
    for r in rows:
        for c in r["candidate_links"]:
            key = (c["url"], c["label"])
            candidate_map[key] = c
    candidates = list(candidate_map.values())

    if exact_hits or variant_hits:
        classification = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_BOUNDED_TARGET_SEARCH_EXACT_OR_VARIANT_CONTEXT_ANCHOR_OBSERVED"
        semantic = "ONE_OR_MORE_GRI_CONTEXT_OR_REVERSE_LOOKUP_EXACT_OR_VARIANT_UQQ700_ANCHORS_WERE_OBSERVED_WITHOUT_LEGAL_PROMOTION"
        next_action = "REVIEW_OBSERVED_CONTEXT_ANCHORS_FOR_LITERAL_OFFICIAL_DESIGNATION_NOTICE_IDENTITY_AND_ONLY_THEN_TRACE_ANY_IDENTITY_TO_OFFICIAL_NOTICE_SOURCE"
    elif weak_hits:
        classification = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_BOUNDED_TARGET_SEARCH_WEAK_CONTEXT_ANCHOR_ONLY"
        semantic = "ONLY_WEAK_DEVELOPMENT_DENSITY_CONTEXT_WAS_OBSERVED_ON_GRI_SEARCH_SURFACES_WITHOUT_DESIGNATION_IDENTITY_PROMOTION"
        next_action = "REVIEW_WEAK_CONTEXT_ANCHORS_ONLY_AS_TIMELINE_OR_REVERSE_LOOKUP_KEYS_AND_KEEP_UQQ700_UNKNOWN"
    elif technical_unknowns:
        classification = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_BOUNDED_TARGET_SEARCH_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_MORE_BOUNDED_GRI_TARGET_REQUESTS_REMAIN_TECHNICALLY_UNRESOLVED_SO_NO_NEGATIVE_INFERENCE_IS_ALLOWED"
        next_action = "HARDEN_ONLY_THE_TECHNICALLY_UNRESOLVED_GRI_REQUESTS_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    else:
        classification = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_BOUNDED_TARGET_SEARCH_NO_TARGET_ANCHOR_OBSERVED"
        semantic = "QUALIFIED_GRI_GLOBAL_AND_RESEARCH_REPORT_SEARCHES_COMPLETED_WITHOUT_EXACT_VARIANT_OR_WEAK_UQQ700_CONTEXT_ANCHORS"
        next_action = "OPERATIONALLY_RECONCILE_NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_SOURCE_FAMILY_NON_NEGATIVELY_AND_KEEP_UQQ700_UNKNOWN"

    out = {
        "step": "STEP 17-21-C-16-8-T-163-S229C",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "query_set": QUERIES,
        "canonical_contract_count": len(contracts),
        "canonical_contract_keys": sorted(canonical_keys),
        "request_count": request_count,
        "results": rows,
        "exact_hit_count": len(exact_hits),
        "variant_hit_count": len(variant_hits),
        "weak_hit_count": len(weak_hits),
        "no_hit_count": len(no_hits),
        "technical_unknown_count": len(technical_unknowns),
        "context_anchor_candidate_count": len(candidates),
        "context_anchor_candidates": candidates,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "target_search_executed": True,
            "bounded_request_budget": 6,
            "source_role_context_and_reverse_lookup_only": True,
            "planning_research_hit_equals_designation_notice": False,
            "planning_research_hit_equals_current_validity": False,
            "planning_research_hit_equals_site_inclusion": False,
            "planning_research_no_hit_equals_legal_absence": False,
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
    print("RESOLUTION")
    print("=" * 78)
    print(f"CANONICAL CONTRACT COUNT: {len(contracts)}")
    print(f"REQUEST COUNT: {request_count}")
    print(f"EXACT HIT COUNT: {len(exact_hits)}")
    print(f"VARIANT HIT COUNT: {len(variant_hits)}")
    print(f"WEAK HIT COUNT: {len(weak_hits)}")
    print(f"NO HIT COUNT: {len(no_hits)}")
    print(f"TECHNICAL UNKNOWN COUNT: {len(technical_unknowns)}")
    print(f"CONTEXT ANCHOR CANDIDATE COUNT: {len(candidates)}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Planning/research hit == designation notice: False")
    print("Planning/research hit == current validity: False")
    print("Planning/research hit == site inclusion: False")
    print("Planning/research no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "hardened S229B loaded": IN_S229B.exists(),
        "exact canonical contract set": canonical_keys == EXPECTED_CANONICAL_KEYS,
        "canonical contract count two": len(contracts) == 2,
        "bounded query count three": len(QUERIES) == 3,
        "request count exactly six": request_count == 6,
        "target search executed": out["summary"]["target_search_executed"] is True,
        "source role context/reverse lookup only": out["summary"]["source_role_context_and_reverse_lookup_only"] is True,
        "planning research hit not designation": out["summary"]["planning_research_hit_equals_designation_notice"] is False,
        "planning research hit not validity": out["summary"]["planning_research_hit_equals_current_validity"] is False,
        "planning research hit not site inclusion": out["summary"]["planning_research_hit_equals_site_inclusion"] is False,
        "planning research no-hit not legal absence": out["summary"]["planning_research_no_hit_equals_legal_absence"] is False,
        "search failure not legal absence": out["summary"]["search_failure_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_BOUNDED_TARGET_SEARCH_EXACT_OR_VARIANT_CONTEXT_ANCHOR_OBSERVED",
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_BOUNDED_TARGET_SEARCH_WEAK_CONTEXT_ANCHOR_ONLY",
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_BOUNDED_TARGET_SEARCH_TECHNICAL_UNKNOWN",
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_BOUNDED_TARGET_SEARCH_NO_TARGET_ANCHOR_OBSERVED",
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
        raise AssertionError("S229C validation failed")


if __name__ == "__main__":
    main()
