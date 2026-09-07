# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_national_regional_planning_research_document_source_family_entry_qualification.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT"

# Entry qualification only. No target-term search is executed in S229A.
ENTRY_CANDIDATES = [
    {
        "source_id": "MOLIT",
        "name": "국토교통부",
        "url": "https://www.molit.go.kr/",
        "expected_role": "NATIONAL_PLANNING_POLICY_AUTHORITY",
    },
    {
        "source_id": "GG",
        "name": "경기도",
        "url": "https://www.gg.go.kr/",
        "expected_role": "REGIONAL_PLANNING_AUTHORITY",
    },
    {
        "source_id": "KRIHS",
        "name": "국토연구원",
        "url": "https://www.krihs.re.kr/",
        "expected_role": "NATIONAL_PLANNING_RESEARCH_INSTITUTE",
    },
    {
        "source_id": "GRI",
        "name": "경기연구원",
        "url": "https://www.gri.re.kr/",
        "expected_role": "REGIONAL_PLANNING_RESEARCH_INSTITUTE",
    },
]

ROLE_KEYWORDS = {
    "PLANNING": ["국토", "도시", "계획", "도시계획", "국토계획", "도시정책", "공간계획"],
    "RESEARCH": ["연구", "연구보고서", "정책연구", "보고서", "연구자료", "정책자료"],
    "PUBLICATION": ["자료", "간행물", "발간", "정책", "정보", "문서"],
    "SEARCH": ["검색", "통합검색", "자료검색", "연구검색", "보고서 검색"],
}


def curl(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {
            "http": None,
            "final_url": None,
            "content_type": None,
            "redirects": None,
            "body": b"",
            "stderr": "curl not found",
        }
    cmd = [
        exe,
        "-L",
        "-sS",
        "--connect-timeout",
        "15",
        "--max-time",
        "120",
        "-A",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H",
        "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w",
        "\n__META__%{http_code}|%{url_effective}|%{content_type}|%{num_redirects}",
        url,
    ]
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


def title_of(text: str) -> str:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", text)
    return strip_tags(m.group(1)) if m else ""


def same_host(base_url: str, candidate_url: str) -> bool:
    a = (urlparse(base_url).hostname or "").lower().removeprefix("www.")
    b = (urlparse(candidate_url).hostname or "").lower().removeprefix("www.")
    return bool(a and b and (a == b or a.endswith("." + b) or b.endswith("." + a)))


def extract_links(base_url: str, text: str) -> list[dict]:
    rows = []
    seen = set()
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", text):
        attrs, body = m.group(1), m.group(2)
        href = attr(attrs, "href")
        if not href or href.lower().startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        url = urljoin(base_url, href)
        if not same_host(base_url, url):
            continue
        label = strip_tags(body)
        blob = f"{label} {href}".lower()
        roles = []
        for role, kws in ROLE_KEYWORDS.items():
            if any(k.lower() in blob for k in kws):
                roles.append(role)
        if not roles:
            continue
        key = (url, label)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"url": url, "label": label, "roles": roles})
    return rows[:120]


def extract_forms(base_url: str, text: str) -> list[dict]:
    rows = []
    for fm in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", text):
        attrs, body = fm.group(1), fm.group(2)
        action = urljoin(base_url, attr(attrs, "action") or base_url)
        method = (attr(attrs, "method") or "GET").upper()
        if not same_host(base_url, action):
            continue
        names = []
        for im in re.finditer(r"(?is)<(?:input|select|textarea)\b([^>]*)>", body):
            name = attr(im.group(1), "name")
            if name and name not in names:
                names.append(name)
        plain = strip_tags(body)
        search_signal = any(k in plain.lower() for k in ["검색", "search", "조회"])
        rows.append({
            "action_url": action,
            "method": method,
            "field_names": names,
            "search_signal": search_signal,
        })
    return rows[:40]


def official_signal(source_id: str, final_url: str, text: str, title: str) -> bool:
    host = (urlparse(final_url).hostname or "").lower()
    sample = f"{title} {strip_tags(text[:50000])}".lower()
    if source_id == "MOLIT":
        return "molit.go.kr" in host and ("국토교통부" in sample or "molit" in sample)
    if source_id == "GG":
        return "gg.go.kr" in host and "경기도" in sample
    if source_id == "KRIHS":
        return "krihs.re.kr" in host and ("국토연구원" in sample or "krihs" in sample)
    if source_id == "GRI":
        return "gri.re.kr" in host and ("경기연구원" in sample or "gri" in sample)
    return False


def classify_entry(entry: dict, rr: dict, text: str) -> dict:
    final_url = rr.get("final_url") or entry["url"]
    title = title_of(text)
    plain = strip_tags(text)
    links = extract_links(final_url, text) if rr.get("http") == "200" else []
    forms = extract_forms(final_url, text) if rr.get("http") == "200" else []
    roles_observed = sorted({role for x in links for role in x["roles"]})
    planning_signal = any(k in plain for k in ROLE_KEYWORDS["PLANNING"])
    research_signal = any(k in plain for k in ROLE_KEYWORDS["RESEARCH"])
    publication_signal = any(k in plain for k in ROLE_KEYWORDS["PUBLICATION"])
    search_signal = any(k in plain for k in ROLE_KEYWORDS["SEARCH"]) or any(f["search_signal"] for f in forms)
    official = official_signal(entry["source_id"], final_url, text, title)
    usable_surface = bool(links) and (planning_signal or research_signal or publication_signal)
    qualified = rr.get("http") == "200" and official and usable_surface
    return {
        "source_id": entry["source_id"],
        "name": entry["name"],
        "expected_role": entry["expected_role"],
        "input_url": entry["url"],
        "http": rr.get("http"),
        "final_url": final_url,
        "content_type": rr.get("content_type"),
        "redirects": rr.get("redirects"),
        "body_size": len(rr.get("body") or b""),
        "title": title,
        "official_signal": official,
        "planning_signal": planning_signal,
        "research_signal": research_signal,
        "publication_signal": publication_signal,
        "search_signal": search_signal,
        "roles_observed": roles_observed,
        "relevant_link_count": len(links),
        "search_form_count": sum(1 for f in forms if f["search_signal"]),
        "relevant_links": links,
        "search_forms": forms,
        "entry_qualified": qualified,
        "source_role": "CONTEXT_AND_REVERSE_LOOKUP_ONLY",
        "target_search_eligible_after_contract_qualification": qualified,
    }


def main() -> None:
    print("=" * 78)
    print("NATIONAL / REGIONAL PLANNING RESEARCH DOCUMENT SOURCE FAMILY ENTRY QUALIFICATION - S229A")
    print("=" * 78)
    print("Purpose: identify official planning/research source entries and roles before any UQQ700 target search")
    print("UQQ700 target search: DISABLED")
    print("Planning/research document hit != designation/current validity/site inclusion")
    print("Planning/research no-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    rows = []
    for entry in ENTRY_CANDIDATES:
        rr = curl(entry["url"])
        text = decode(rr.get("body") or b"")
        row = classify_entry(entry, rr, text)
        rows.append(row)

    qualified = [r for r in rows if r["entry_qualified"]]
    planning_authorities = [r for r in qualified if "AUTHORITY" in r["expected_role"]]
    research_institutes = [r for r in qualified if "RESEARCH_INSTITUTE" in r["expected_role"]]

    ranked = []
    for r in qualified:
        score = 0
        if "AUTHORITY" in r["expected_role"]:
            score += 5
        if r["planning_signal"]:
            score += 4
        if r["research_signal"]:
            score += 3
        if r["publication_signal"]:
            score += 2
        if r["search_signal"]:
            score += 2
        score += min(r["relevant_link_count"], 20) / 20
        ranked.append({
            "source_id": r["source_id"],
            "name": r["name"],
            "expected_role": r["expected_role"],
            "final_url": r["final_url"],
            "score": round(score, 2),
            "recommended_next_stage": "QUALIFY_DOCUMENT_SEARCH_OR_PUBLICATION_ARCHIVE_CONTRACT_WITH_POSITIVE_CONTROL_ONLY",
        })
    ranked.sort(key=lambda x: (-x["score"], x["source_id"]))

    if qualified:
        classification = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_ENTRY_SOURCE_ROLE_QUALIFIED"
        semantic = "ONE_OR_MORE_OFFICIAL_PLANNING_OR_RESEARCH_SOURCE_ENTRIES_WERE_QUALIFIED_FOR_CONTEXT_AND_REVERSE_LOOKUP_ONLY"
        next_action = "QUALIFY_POSITIVE_CONTROL_DOCUMENT_SEARCH_OR_PUBLICATION_ARCHIVE_CONTRACTS_ON_TOP_RANKED_QUALIFIED_SOURCES_BEFORE_UQQ700_TARGET_SEARCH"
    else:
        classification = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_ENTRY_SOURCE_ROLE_TECHNICAL_UNKNOWN"
        semantic = "NO_OFFICIAL_PLANNING_OR_RESEARCH_SOURCE_ENTRY_WAS_QUALIFIED_FROM_THE_BOUNDED_ENTRY_SET"
        next_action = "HARDEN_ONLY_OFFICIAL_ENTRY_ROUTES_OR_RESELECT_OFFICIAL_PLANNING_RESEARCH_SOURCE_FAMILIES_WITHOUT_UQQ700_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-161-S229A",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "entry_candidate_count": len(ENTRY_CANDIDATES),
        "results": rows,
        "qualified_entry_count": len(qualified),
        "qualified_planning_authority_count": len(planning_authorities),
        "qualified_research_institute_count": len(research_institutes),
        "ranked_qualified_sources": ranked,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "target_search_executed": False,
            "positive_control_search_executed": False,
            "source_role_context_and_reverse_lookup_only": True,
            "planning_research_hit_equals_designation_notice": False,
            "planning_research_hit_equals_current_validity": False,
            "planning_research_hit_equals_site_inclusion": False,
            "planning_research_no_hit_equals_legal_absence": False,
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

    print("\nENTRY QUALIFICATION")
    print("-" * 78)
    for r in rows:
        print(json.dumps({
            "source_id": r["source_id"],
            "name": r["name"],
            "http": r["http"],
            "final_url": r["final_url"],
            "body_size": r["body_size"],
            "title": r["title"],
            "official_signal": r["official_signal"],
            "planning_signal": r["planning_signal"],
            "research_signal": r["research_signal"],
            "publication_signal": r["publication_signal"],
            "search_signal": r["search_signal"],
            "relevant_link_count": r["relevant_link_count"],
            "search_form_count": r["search_form_count"],
            "entry_qualified": r["entry_qualified"],
        }, ensure_ascii=False))

    print("\nRANKED QUALIFIED SOURCES")
    print("-" * 78)
    for x in ranked:
        print(json.dumps(x, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"ENTRY CANDIDATE COUNT: {len(ENTRY_CANDIDATES)}")
    print(f"QUALIFIED ENTRY COUNT: {len(qualified)}")
    print(f"QUALIFIED PLANNING AUTHORITY COUNT: {len(planning_authorities)}")
    print(f"QUALIFIED RESEARCH INSTITUTE COUNT: {len(research_institutes)}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Target UQQ700 search executed: False")
    print("Planning/research no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "bounded four entry candidates": out["entry_candidate_count"] == 4,
        "target search not executed": out["summary"]["target_search_executed"] is False,
        "positive control search not executed": out["summary"]["positive_control_search_executed"] is False,
        "source role context/reverse lookup only": out["summary"]["source_role_context_and_reverse_lookup_only"] is True,
        "planning research hit not designation": out["summary"]["planning_research_hit_equals_designation_notice"] is False,
        "planning research hit not validity": out["summary"]["planning_research_hit_equals_current_validity"] is False,
        "planning research hit not site inclusion": out["summary"]["planning_research_hit_equals_site_inclusion"] is False,
        "planning research no-hit not legal absence": out["summary"]["planning_research_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_ENTRY_SOURCE_ROLE_QUALIFIED",
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_ENTRY_SOURCE_ROLE_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S229A validation failed")


if __name__ == "__main__":
    main()
