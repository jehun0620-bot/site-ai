# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_S229B = OUT_DIR / "development_density_management_area_national_regional_planning_research_document_positive_control_search_contract_qualification.json"
IN_S229C = OUT_DIR / "development_density_management_area_national_regional_planning_research_document_uqq700_bounded_target_search.json"
OUT = OUT_DIR / "development_density_management_area_national_regional_planning_research_document_uqq700_search_result_semantic_hardening.json"

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

RESULT_HINTS = [
    "result", "search", "list", "report", "research", "resreport", "contents",
    "board", "item", "article", "title", "subject", "book", "project",
]
NON_RESULT_HINTS = [
    "login", "member", "privacy", "sitemap", "main/index", "javascript:", "mailto:", "tel:",
]
NOTICE_IDENTITY_RE = re.compile(
    r"(?:제\s*\d+\s*[-–]\s*\d+\s*호|고시\s*제?\s*\d+\s*[-–]\s*\d+\s*호|공고\s*제?\s*\d+\s*[-–]\s*\d+\s*호)",
    re.I,
)


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


def attr(tag: str, name: str) -> str | None:
    m = re.search(rf'(?is)\b{name}\s*=\s*["\']([^"\']*)["\']', tag)
    if m:
        return html.unescape(m.group(1))
    m = re.search(rf'(?is)\b{name}\s*=\s*([^\s>]+)', tag)
    return html.unescape(m.group(1)) if m else None


def neutral_payload(contract: dict, query: str) -> dict:
    payload = {k: "" for k in (contract.get("payload_keys") or [])}
    payload[contract["query_field"]] = query
    if contract.get("semantic_contract_role") == "RESEARCH_REPORT_SEARCH":
        defaults = {
            "schM": "list", "page": "1", "viewCount": "10", "schPrjType": "ALL",
            "schStartYear": "", "schEndYear": "", "schSubj1": "", "schSubj2": "", "schFld": "ALL",
        }
        payload.update(defaults)
        payload[contract["query_field"]] = query
    return payload


def remove_echo_surfaces(text: str, query: str) -> str:
    # Remove scripts/styles/comments first.
    s = re.sub(r"(?is)<!--.*?-->", " ", text)
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s)
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)

    # Remove inputs/textareas/selects that can replay the submitted query.
    s = re.sub(r"(?is)<input\b[^>]*>", " ", s)
    s = re.sub(r"(?is)<textarea\b.*?</textarea>", " ", s)
    s = re.sub(r"(?is)<select\b.*?</select>", " ", s)

    # Remove form blocks containing the query; these are considered UI echo surfaces.
    def drop_query_form(m: re.Match) -> str:
        block = m.group(0)
        return " " if query in html.unescape(block) else block

    s = re.sub(r"(?is)<form\b.*?</form>", drop_query_form, s)
    return s


def normalize_result_url(base_url: str, href: str, query_field: str, query: str) -> str:
    url = urljoin(base_url, html.unescape(href))
    p = urlparse(url)
    kept = []
    for k, v in parse_qsl(p.query, keep_blank_values=True):
        if k == query_field and v == query:
            continue
        kept.append((k, v))
    q = urlencode(kept, doseq=True)
    return p._replace(query=q, fragment="").geturl()


def link_is_result_like(url: str, label: str) -> bool:
    blob = f"{url} {label}".lower()
    if any(x in blob for x in NON_RESULT_HINTS):
        return False
    if not label.strip():
        return False
    return any(x in blob for x in RESULT_HINTS) or len(label.strip()) >= 8


def extract_result_candidates(base_url: str, cleaned_html: str, query: str, query_field: str) -> list[dict]:
    rows = []
    seen = set()
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", cleaned_html):
        attrs, body = m.group(1), m.group(2)
        href = attr(attrs, "href")
        if not href or href.lower().startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        label = strip_tags(body)
        if not link_is_result_like(href, label):
            continue
        url = normalize_result_url(base_url, href, query_field, query)

        # Result anchors are only promoted when the visible title itself carries
        # the searched literal/weak stem. URL query echo alone is insufficient.
        label_exact = query in label
        label_weak = "개발밀도" in label
        if not label_exact and not label_weak:
            continue

        key = (url, label)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "url": url,
            "title": label,
            "label_exact_match": label_exact,
            "label_weak_match": label_weak,
            "notice_identity_literals": sorted(set(NOTICE_IDENTITY_RE.findall(label))),
        })
    return rows[:100]


def extract_result_text_windows(cleaned_html: str, query: str) -> list[str]:
    plain = strip_tags(cleaned_html)
    windows = []
    pos = 0
    while True:
        i = plain.find(query, pos)
        if i < 0:
            break
        left = max(0, i - 180)
        right = min(len(plain), i + len(query) + 220)
        snippet = plain[left:right].strip()
        if snippet and snippet not in windows:
            windows.append(snippet)
        pos = i + len(query)
        if len(windows) >= 20:
            break
    return windows


def verified_status(query_class: str, query: str, candidates: list[dict], windows: list[str]) -> tuple[str, bool, str]:
    # Primary evidence is a visible result anchor/title. Plain text windows are
    # retained as diagnostics only because the page can echo queries outside a
    # true result item.
    exact_title_hits = [c for c in candidates if c["label_exact_match"]]
    weak_title_hits = [c for c in candidates if c["label_weak_match"]]
    if query_class == "EXACT":
        if exact_title_hits:
            return "EXACT_VERIFIED_RESULT_HIT", True, "VISIBLE_RESULT_TITLE_LITERAL"
        return "EXACT_ECHO_OR_NONRESULT_ONLY", False, "NO_VISIBLE_RESULT_TITLE_LITERAL"
    if query_class == "VARIANT":
        if exact_title_hits:
            return "VARIANT_VERIFIED_RESULT_HIT", True, "VISIBLE_RESULT_TITLE_LITERAL"
        return "VARIANT_ECHO_OR_NONRESULT_ONLY", False, "NO_VISIBLE_RESULT_TITLE_LITERAL"
    if weak_title_hits:
        return "WEAK_VERIFIED_RESULT_HIT", True, "VISIBLE_RESULT_TITLE_WEAK_LITERAL"
    return "WEAK_ECHO_OR_NONRESULT_ONLY", False, "NO_VISIBLE_RESULT_TITLE_WEAK_LITERAL"


def main() -> None:
    print("=" * 78)
    print("NATIONAL / REGIONAL PLANNING RESEARCH DOCUMENT UQQ700 SEARCH RESULT SEMANTIC HARDENING - S229D")
    print("=" * 78)
    print("Purpose: separate search-form/query echo from visible GRI result-item evidence")
    print("No new source family; bounded replay remains 2 canonical contracts x 3 queries = 6")
    print("Visible result title is required for VERIFIED HIT")
    print("Planning/research hit != designation/current validity/site inclusion")
    print("Planning/research no-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    if not IN_S229B.exists():
        raise FileNotFoundError(f"Missing S229B output: {IN_S229B}")
    if not IN_S229C.exists():
        raise FileNotFoundError(f"Missing S229C output: {IN_S229C}")

    s229b = json.loads(IN_S229B.read_text(encoding="utf-8"))
    s229c = json.loads(IN_S229C.read_text(encoding="utf-8"))
    contracts = s229b.get("canonical_qualified_search_contracts") or []
    canonical_keys = {c.get("canonical_contract_key") for c in contracts}
    if canonical_keys != EXPECTED_CANONICAL_KEYS:
        raise AssertionError(f"Unexpected canonical contract set: {sorted(canonical_keys)}")
    if s229c.get("request_count") != 6:
        raise AssertionError("S229D expects completed S229C with exactly six bounded requests")

    rows = []
    for contract in sorted(contracts, key=lambda x: x["canonical_contract_key"]):
        for q in QUERIES:
            query = q["query"]
            payload = neutral_payload(contract, query)
            rr = curl_get(contract["action_url"], payload, contract.get("page_url"))
            text = decode(rr.get("body") or b"")
            cleaned = remove_echo_surfaces(text, query)
            plain_cleaned = strip_tags(cleaned)
            candidates = extract_result_candidates(
                rr.get("final_url") or contract["action_url"],
                cleaned,
                query,
                contract["query_field"],
            )
            windows = extract_result_text_windows(cleaned, query)
            status, verified_hit, evidence_class = verified_status(q["class"], query, candidates, windows)
            technical_unknown = rr.get("http") != "200" or len(rr.get("body") or b"") < 1000
            if technical_unknown:
                status = "TECHNICAL_UNKNOWN"
                verified_hit = False
                evidence_class = "TRANSPORT_OR_BODY_UNRESOLVED"

            notice_ids = sorted({x for c in candidates for x in c["notice_identity_literals"]})
            row = {
                "source_id": contract["source_id"],
                "name": contract["name"],
                "semantic_contract_role": contract["semantic_contract_role"],
                "canonical_contract_key": contract["canonical_contract_key"],
                "query": query,
                "query_class": q["class"],
                "http": rr.get("http"),
                "final_url": rr.get("final_url"),
                "body_size": len(rr.get("body") or b""),
                "raw_query_present": query in text,
                "cleaned_query_present": query in plain_cleaned,
                "cleaned_query_occurrence_count": plain_cleaned.count(query),
                "cleaned_weak_occurrence_count": plain_cleaned.count("개발밀도"),
                "verified_result_hit": verified_hit,
                "verified_status": status,
                "evidence_class": evidence_class,
                "result_candidate_count": len(candidates),
                "result_candidates": candidates,
                "diagnostic_text_window_count": len(windows),
                "diagnostic_text_windows": windows[:10],
                "notice_identity_literal_count": len(notice_ids),
                "notice_identity_literals": notice_ids,
                "technical_unknown": technical_unknown,
                "source_role": "CONTEXT_AND_REVERSE_LOOKUP_ONLY",
                "designation_identity_promoted": False,
                "current_validity_promoted": False,
                "site_inclusion_promoted": False,
            }
            rows.append(row)
            print(json.dumps({
                "contract": row["canonical_contract_key"],
                "query_class": row["query_class"],
                "query": row["query"],
                "http": row["http"],
                "raw_query_present": row["raw_query_present"],
                "cleaned_query_occurrence_count": row["cleaned_query_occurrence_count"],
                "verified_result_hit": row["verified_result_hit"],
                "verified_status": row["verified_status"],
                "result_candidate_count": row["result_candidate_count"],
                "notice_identity_literal_count": row["notice_identity_literal_count"],
            }, ensure_ascii=False))
            for c in candidates:
                print("  CANDIDATE", json.dumps(c, ensure_ascii=False))

    exact_verified = [r for r in rows if r["verified_status"] == "EXACT_VERIFIED_RESULT_HIT"]
    variant_verified = [r for r in rows if r["verified_status"] == "VARIANT_VERIFIED_RESULT_HIT"]
    weak_verified = [r for r in rows if r["verified_status"] == "WEAK_VERIFIED_RESULT_HIT"]
    technical_unknowns = [r for r in rows if r["technical_unknown"]]

    candidate_map = {}
    for r in rows:
        for c in r["result_candidates"]:
            candidate_map[(c["url"], c["title"])] = c
    candidates = list(candidate_map.values())
    notice_ids = sorted({x for c in candidates for x in c["notice_identity_literals"]})

    if exact_verified or variant_verified:
        classification = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_SEARCH_RESULT_SEMANTICALLY_VERIFIED_EXACT_OR_VARIANT_CONTEXT_ANCHOR"
        semantic = "VISIBLE_GRI_RESULT_TITLE_EVIDENCE_VERIFIED_ONE_OR_MORE_EXACT_OR_VARIANT_CONTEXT_ANCHORS_WITHOUT_LEGAL_PROMOTION"
        next_action = "REVIEW_ONLY_VERIFIED_RESULT_DOCUMENTS_FOR_LITERAL_OFFICIAL_DESIGNATION_NOTICE_IDENTITY_AND_TRACE_ANY_LITERAL_IDENTITY_TO_THE_OFFICIAL_NOTICE_SOURCE"
    elif weak_verified:
        classification = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_SEARCH_RESULT_SEMANTICALLY_VERIFIED_WEAK_CONTEXT_ANCHOR_ONLY"
        semantic = "ONLY_VISIBLE_GRI_RESULT_TITLE_WEAK_DEVELOPMENT_DENSITY_CONTEXT_WAS_VERIFIED_AFTER_ECHO_REMOVAL"
        next_action = "REVIEW_ONLY_VERIFIED_WEAK_RESULT_DOCUMENTS_AS_TIMELINE_OR_REVERSE_LOOKUP_KEYS_AND_KEEP_UQQ700_UNKNOWN"
    elif technical_unknowns:
        classification = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_SEARCH_RESULT_SEMANTIC_HARDENING_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_MORE_BOUNDED_SEMANTIC_REPLAYS_REMAIN_TECHNICALLY_UNRESOLVED_WITHOUT_NEGATIVE_INFERENCE"
        next_action = "HARDEN_ONLY_TECHNICALLY_UNRESOLVED_GRI_RESULT_REPLAYS_AND_KEEP_UQQ700_UNKNOWN"
    else:
        classification = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_SEARCH_RESULT_ECHO_ONLY_NO_VERIFIED_RESULT_ANCHOR"
        semantic = "S229C_LITERAL_OCCURRENCES_WERE_NOT_VERIFIED_IN_VISIBLE_RESULT_TITLES_AFTER_ECHO_SURFACE_REMOVAL"
        next_action = "OPERATIONALLY_RECONCILE_THE_SOURCE_FAMILY_NON_NEGATIVELY_AND_KEEP_UQQ700_UNKNOWN"

    out = {
        "step": "STEP 17-21-C-16-8-T-164-S229D",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "input_s229c_raw_exact_hit_count": s229c.get("exact_hit_count"),
        "input_s229c_raw_variant_hit_count": s229c.get("variant_hit_count"),
        "input_s229c_raw_weak_hit_count": s229c.get("weak_hit_count"),
        "canonical_contract_count": len(contracts),
        "request_count": len(rows),
        "results": rows,
        "verified_exact_hit_count": len(exact_verified),
        "verified_variant_hit_count": len(variant_verified),
        "verified_weak_hit_count": len(weak_verified),
        "verified_result_candidate_count": len(candidates),
        "verified_result_candidates": candidates,
        "notice_identity_literal_count": len(notice_ids),
        "notice_identity_literals": notice_ids,
        "technical_unknown_count": len(technical_unknowns),
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "target_search_executed": True,
            "semantic_hardening_executed": True,
            "echo_surfaces_removed": True,
            "visible_result_title_required_for_verified_hit": True,
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
    print(f"S229C RAW EXACT HIT COUNT: {s229c.get('exact_hit_count')}")
    print(f"S229C RAW VARIANT HIT COUNT: {s229c.get('variant_hit_count')}")
    print(f"S229C RAW WEAK HIT COUNT: {s229c.get('weak_hit_count')}")
    print(f"REQUEST COUNT: {len(rows)}")
    print(f"VERIFIED EXACT HIT COUNT: {len(exact_verified)}")
    print(f"VERIFIED VARIANT HIT COUNT: {len(variant_verified)}")
    print(f"VERIFIED WEAK HIT COUNT: {len(weak_verified)}")
    print(f"VERIFIED RESULT CANDIDATE COUNT: {len(candidates)}")
    print(f"NOTICE IDENTITY LITERAL COUNT: {len(notice_ids)}")
    print(f"TECHNICAL UNKNOWN COUNT: {len(technical_unknowns)}")
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
        "S229B loaded": IN_S229B.exists(),
        "S229C loaded": IN_S229C.exists(),
        "canonical contract count two": len(contracts) == 2,
        "request count exactly six": len(rows) == 6,
        "semantic hardening executed": out["summary"]["semantic_hardening_executed"] is True,
        "echo surfaces removed": out["summary"]["echo_surfaces_removed"] is True,
        "visible result title required": out["summary"]["visible_result_title_required_for_verified_hit"] is True,
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
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_SEARCH_RESULT_SEMANTICALLY_VERIFIED_EXACT_OR_VARIANT_CONTEXT_ANCHOR",
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_SEARCH_RESULT_SEMANTICALLY_VERIFIED_WEAK_CONTEXT_ANCHOR_ONLY",
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_SEARCH_RESULT_SEMANTIC_HARDENING_TECHNICAL_UNKNOWN",
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_UQQ700_SEARCH_RESULT_ECHO_ONLY_NO_VERIFIED_RESULT_ANCHOR",
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
        raise AssertionError("S229D validation failed")


if __name__ == "__main__":
    main()
