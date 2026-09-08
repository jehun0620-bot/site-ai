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
IN_HARDENED = OUT_DIR / "development_density_management_area_gyeonggi_ebook_gazette_archive_search_contract_semantic_hardening.json"
OUT = OUT_DIR / "development_density_management_area_gyeonggi_ebook_gazette_archive_uqq700_bounded_target_search.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
ENTRY = "https://ebook.gg.go.kr/home/list.php"
HOST = "ebook.gg.go.kr"
TIMEOUT = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Referer": "https://ebook.gg.go.kr/home/list.php?code=21",
}

QUERIES = [
    ("EXACT", "개발밀도관리구역"),
    ("VARIANT", "개발밀도 관리구역"),
    ("WEAK", "개발밀도"),
]

DETAIL_HINT_RE = re.compile(r"(?:view|detail|book|ebook|contents|content|reader|viewer|idx|no|seq|uid|serial)", re.I)
NOTICE_ID_RE = re.compile(r"(?:고시|공고)\s*제?\s*(\d{4})\s*[-–]\s*(\d{1,5})\s*호")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def decode_response(r: requests.Response) -> str:
    # The archive serves legacy Korean pages. Prefer declared charset, then EUC-KR/CP949,
    # while avoiding mojibake seen in S230F-HARDENED.
    content = r.content
    declared = r.encoding
    candidates = []
    if declared:
        candidates.append(declared)
    candidates += ["euc-kr", "cp949", "utf-8"]
    seen = set()
    best = None
    best_score = -10**9
    for enc in candidates:
        if not enc or enc.lower() in seen:
            continue
        seen.add(enc.lower())
        try:
            text = content.decode(enc, errors="replace")
        except Exception:
            continue
        replacement_penalty = text.count("�") * 10
        korean_score = len(re.findall(r"[가-힣]", text))
        mojibake_penalty = sum(text.count(x) for x in ["º", "À", "Æ", "¼", "»"]) * 2
        score = korean_score - replacement_penalty - mojibake_penalty
        if score > best_score:
            best_score = score
            best = text
    return best if best is not None else r.text


def fetch(session: requests.Session, url: str, params=None):
    try:
        return session.get(url, params=params, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True)
    except requests.RequestException:
        return None


def canonical_result_rows(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    seen = set()
    for a in soup.find_all("a", href=True):
        title = normalize_space(a.get_text(" ", strip=True))
        href = urljoin(base_url, a.get("href"))
        if not title:
            continue
        # Require archive/detail-looking anchors or clearly gazette-like title/date text.
        detailish = DETAIL_HINT_RE.search(href) is not None
        gazetteish = "경기도보" in title or bool(re.search(r"20\d{2}[.\-/년]", title))
        if not (detailish or gazetteish):
            continue
        key = (title, href)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"title": title, "url": href})
    return rows


def strip_echo_surfaces(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style", "input", "textarea", "option", "select", "form"]):
        tag.decompose()
    return normalize_space(soup.get_text(" ", strip=True))


def query_terms(kind: str):
    if kind == "EXACT":
        return ["개발밀도관리구역"]
    if kind == "VARIANT":
        return ["개발밀도 관리구역"]
    return ["개발밀도"]


def row_hit(kind: str, row: dict):
    text = normalize_space(row["title"])
    return any(t in text for t in query_terms(kind))


def detail_probe(session: requests.Session, row: dict, kind: str):
    r = fetch(session, row["url"])
    if r is None:
        return {
            "url": row["url"], "http": None, "technical_unknown": True,
            "target_hit": False, "notice_identities": [], "text_sample": "",
        }
    text = decode_response(r)
    cleaned = strip_echo_surfaces(text)
    hit = any(t in cleaned for t in query_terms(kind))
    notices = []
    for m in NOTICE_ID_RE.finditer(cleaned):
        notices.append({"literal": normalize_space(m.group(0)), "canonical": f"{int(m.group(1)):04d}-{int(m.group(2))}"})
    return {
        "url": r.url,
        "http": r.status_code,
        "technical_unknown": r.status_code != 200,
        "target_hit": hit,
        "notice_identities": notices[:20],
        "text_sample": cleaned[:1200],
    }


def main():
    print("=" * 78)
    print("GYEONGGI EBOOK GAZETTE UQQ700 BOUNDED TARGET SEARCH - S230G")
    print("=" * 78)
    print("Purpose: bounded exact/variant/weak target search through hardened searchval contract")
    print("Query echo, result-row hit, and detail-document hit are separated")
    print("Search hit != designation/current validity/site inclusion")
    print("No-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    hard = load_json(IN_HARDENED)
    assert hard.get("contract_qualified") is True
    assert hard.get("likely_keyword_fields") == ["searchval"]

    session = requests.Session()
    results = []
    total_detail_probes = 0

    for kind, term in QUERIES:
        params = {"dummy": "", "searchcode": "24", "searchkey": "all", "searchval": term}
        r = fetch(session, ENTRY, params=params)
        if r is None:
            results.append({
                "query_kind": kind, "query": term, "http": None,
                "query_echo": False, "cleaned_occurrence_count": 0,
                "result_row_count": 0, "verified_result_row_hit_count": 0,
                "detail_probe_count": 0, "detail_target_hit_count": 0,
                "notice_identity_count": 0, "technical_unknown": True,
                "status": "TECHNICAL_UNKNOWN", "rows": [], "detail_results": [],
            })
            continue

        html = decode_response(r)
        cleaned = strip_echo_surfaces(html)
        rows = canonical_result_rows(html, r.url)
        hit_rows = [row for row in rows if row_hit(kind, row)]

        detail_results = []
        # Probe only bounded candidate rows. If no row-title hit, do not crawl arbitrary rows.
        for row in hit_rows[:10]:
            d = detail_probe(session, row, kind)
            d["source_title"] = row["title"]
            detail_results.append(d)
            total_detail_probes += 1

        notice_count = sum(len(d["notice_identities"]) for d in detail_results if d.get("target_hit"))
        detail_hit_count = sum(1 for d in detail_results if d.get("target_hit"))
        technical_unknown = r.status_code != 200 or any(d.get("technical_unknown") for d in detail_results)
        occurrence = sum(cleaned.count(t) for t in query_terms(kind))
        query_echo = term in r.url or term in normalize_space(str(params))

        if technical_unknown:
            status = "TECHNICAL_UNKNOWN"
        elif detail_hit_count > 0:
            status = f"{kind}_VERIFIED_DETAIL_HIT"
        elif len(hit_rows) > 0:
            status = f"{kind}_RESULT_ROW_HIT_UNVERIFIED_DETAIL"
        else:
            status = f"{kind}_NO_VERIFIED_RESULT_HIT"

        results.append({
            "query_kind": kind,
            "query": term,
            "http": r.status_code,
            "final_url": r.url,
            "query_echo": query_echo,
            "cleaned_occurrence_count": occurrence,
            "result_row_count": len(rows),
            "verified_result_row_hit_count": len(hit_rows),
            "detail_probe_count": len(detail_results),
            "detail_target_hit_count": detail_hit_count,
            "notice_identity_count": notice_count,
            "technical_unknown": technical_unknown,
            "status": status,
            "rows": rows[:100],
            "hit_rows": hit_rows[:20],
            "detail_results": detail_results,
        })

    verified_row_hits = sum(x["verified_result_row_hit_count"] for x in results)
    verified_detail_hits = sum(x["detail_target_hit_count"] for x in results)
    notice_identity_count = sum(x["notice_identity_count"] for x in results)
    technical_unknown_count = sum(1 for x in results if x["technical_unknown"])

    if verified_detail_hits > 0:
        classification = "GYEONGGI_EBOOK_GAZETTE_UQQ700_BOUNDED_SEARCH_VERIFIED_DETAIL_TARGET_HIT"
        semantic = "ONE_OR_MORE_RESULT_ROWS_LED_TO_DETAIL_DOCUMENTS_CONTAINING_THE_TARGET_TERM"
        next_action = "VERIFY_DOCUMENT_IDENTITY_GAZETTE_ISSUE_DATE_NOTICE_NUMBER_AND_ATTACHMENT_BODY_WITHOUT_PROMOTING_CURRENT_VALIDITY_OR_SITE_INCLUSION"
    elif verified_row_hits > 0:
        classification = "GYEONGGI_EBOOK_GAZETTE_UQQ700_BOUNDED_SEARCH_RESULT_ROW_HIT_DETAIL_UNVERIFIED"
        semantic = "TARGET_TERM_APPEARED_IN_ONE_OR_MORE_CANONICAL_RESULT_ROWS_BUT_DETAIL_DOCUMENT_CONFIRMATION_IS_NOT_YET_ESTABLISHED"
        next_action = "HARDEN_ONLY_THE_MATCHED_RESULT_ROWS_AND_DETAIL_VIEWER_PATHS_BEFORE_ANY_DESIGNATION_INFERENCE"
    elif technical_unknown_count > 0:
        classification = "GYEONGGI_EBOOK_GAZETTE_UQQ700_BOUNDED_SEARCH_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_MORE_BOUNDED_TARGET_REQUESTS_OR_MATCHED_DETAIL_PROBES_REMAIN_TECHNICALLY_UNRESOLVED"
        next_action = "RESOLVE_ONLY_THE_TECHNICAL_UNKNOWN_SURFACE_WITHOUT_TREATING_IT_AS_NO_HIT_OR_LEGAL_ABSENCE"
    else:
        classification = "GYEONGGI_EBOOK_GAZETTE_UQQ700_BOUNDED_SEARCH_NO_VERIFIED_TARGET_RESULT"
        semantic = "THE_HARDENED_EBOOK_SEARCH_CONTRACT_RETURNED_NO_VERIFIED_TARGET_RESULT_ROW_OR_DETAIL_DOCUMENT_FOR_THE_BOUNDED_QUERIES"
        next_action = "RUN_THE_SAME_BOUNDED_TARGET_SCOPE_ON_THE_OTHER_S230E_QUALIFIED_GG_GAZETTE_BOARD_ENTRY_BEFORE_SOURCE_FAMILY_TERMINAL_RECONCILIATION"

    out = {
        "step": "STEP 17-S230G",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_OR_NOTICE_ARCHIVE_ALTERNATE_ENTRY",
        "source_id": "GG_EBOOK_GAZETTE_ARCHIVE",
        "hardened_contract_loaded": True,
        "query_field": "searchval",
        "fixed_payload": {"dummy": "", "searchcode": "24", "searchkey": "all"},
        "request_count": len(results),
        "queries": results,
        "verified_result_row_hit_count": verified_row_hits,
        "verified_detail_target_hit_count": verified_detail_hits,
        "notice_identity_count": notice_identity_count,
        "technical_unknown_query_count": technical_unknown_count,
        "detail_probe_count": total_detail_probes,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "search_hit_equals_designation": False,
            "document_hit_equals_current_validity": False,
            "document_hit_equals_site_inclusion": False,
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
    print("BOUNDED SEARCH")
    print("=" * 78)
    for x in results:
        print(json.dumps({
            "query_kind": x["query_kind"],
            "query": x["query"],
            "http": x["http"],
            "cleaned_occurrence_count": x["cleaned_occurrence_count"],
            "result_row_count": x["result_row_count"],
            "verified_result_row_hit_count": x["verified_result_row_hit_count"],
            "detail_probe_count": x["detail_probe_count"],
            "detail_target_hit_count": x["detail_target_hit_count"],
            "notice_identity_count": x["notice_identity_count"],
            "technical_unknown": x["technical_unknown"],
            "status": x["status"],
        }, ensure_ascii=False))
        for row in x.get("hit_rows", []):
            print("  HIT_ROW:", json.dumps(row, ensure_ascii=False))
        for d in x.get("detail_results", []):
            print("  DETAIL:", json.dumps({
                "source_title": d.get("source_title"),
                "http": d.get("http"),
                "target_hit": d.get("target_hit"),
                "notice_identities": d.get("notice_identities"),
                "url": d.get("url"),
            }, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"REQUEST COUNT: {len(results)}")
    print(f"VERIFIED RESULT ROW HIT COUNT: {verified_row_hits}")
    print(f"VERIFIED DETAIL TARGET HIT COUNT: {verified_detail_hits}")
    print(f"NOTICE IDENTITY COUNT: {notice_identity_count}")
    print(f"TECHNICAL UNKNOWN QUERY COUNT: {technical_unknown_count}")
    print(f"DETAIL PROBE COUNT: {total_detail_probes}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Search hit == designation identity: False")
    print("No-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "hardened contract loaded": IN_HARDENED.exists() and out["hardened_contract_loaded"] is True,
        "host contract fixed": urlparse(ENTRY).hostname == HOST and out["query_field"] == "searchval",
        "exactly three bounded queries": out["request_count"] == 3,
        "query set exact variant weak": [x["query_kind"] for x in results] == ["EXACT", "VARIANT", "WEAK"],
        "detail probes bounded": total_detail_probes <= 30,
        "search hit not designation": out["summary"]["search_hit_equals_designation"] is False,
        "document hit not validity": out["summary"]["document_hit_equals_current_validity"] is False,
        "document hit not site inclusion": out["summary"]["document_hit_equals_site_inclusion"] is False,
        "no hit not legal absence": out["summary"]["no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "GYEONGGI_EBOOK_GAZETTE_UQQ700_BOUNDED_SEARCH_VERIFIED_DETAIL_TARGET_HIT",
            "GYEONGGI_EBOOK_GAZETTE_UQQ700_BOUNDED_SEARCH_RESULT_ROW_HIT_DETAIL_UNVERIFIED",
            "GYEONGGI_EBOOK_GAZETTE_UQQ700_BOUNDED_SEARCH_TECHNICAL_UNKNOWN",
            "GYEONGGI_EBOOK_GAZETTE_UQQ700_BOUNDED_SEARCH_NO_VERIFIED_TARGET_RESULT",
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
        raise AssertionError("S230G validation failed")


if __name__ == "__main__":
    main()
