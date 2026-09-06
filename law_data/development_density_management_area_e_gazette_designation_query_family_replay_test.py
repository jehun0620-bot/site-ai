# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from collections import OrderedDict
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
S221Q = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_pdf_term_context_classification.json"
S221G = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_rest_api_positive_control_replay.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_designation_query_family_replay.json"

BASE_URL = "https://www.gwanbo.go.kr"
ENTRY_URL = BASE_URL + "/"
SEARCH_PAGE_URL = BASE_URL + "/user/search/searchKeyword.do"
SEARCH_API_URL = BASE_URL + "/SearchRestApi.jsp"
TARGET = "개발밀도관리구역"

QUERY_TERMS = [
    "개발밀도관리구역 성남",
    "개발밀도관리구역 성남시",
    "개발밀도관리구역 지정",
    "개발밀도관리구역 결정",
    "개발밀도관리구역 지형도면",
]


def search_trim(s: str) -> str:
    return " ".join((s or "").strip().split())


def remove_special(s: str) -> str:
    # Live JS removes special characters before replacing spaces with AND.
    # Keep Korean/ASCII word content and spaces; this query family contains no punctuation.
    return re.sub(r"[^0-9A-Za-z가-힣\s]", " ", s or "")


def build_subject_desc_query(term: str) -> str:
    p = search_trim(remove_special(term))
    p = " AND ".join(p.split())
    return (
        f"(unstored_field_subject:({p}) OR unstored_field_desc:({p})) "
        "AND keyword_category_order:(@@ORDER_NUM)"
    )


def safe_get(session: requests.Session, url: str):
    try:
        r = session.get(url, timeout=60, allow_redirects=True)
        return r, None
    except requests.RequestException as ex:
        return None, f"{type(ex).__name__}: {ex}"


def safe_post(session: requests.Session, payload: dict[str, str]):
    try:
        r = session.post(
            SEARCH_API_URL,
            data=payload,
            timeout=60,
            allow_redirects=True,
            headers={
                "Referer": SEARCH_PAGE_URL,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )
        return r, None
    except requests.RequestException as ex:
        return None, f"{type(ex).__name__}: {ex}"


def parse_json(response):
    if response is None:
        return None, "no response"
    try:
        return response.json(), None
    except Exception as ex:
        return None, f"{type(ex).__name__}: {ex}"


def iter_category_items(data_obj):
    if not isinstance(data_obj, dict):
        return []
    data = data_obj.get("data")
    if not isinstance(data, list):
        return []
    rows = []
    for cat_idx, category in enumerate(data):
        if not isinstance(category, dict):
            continue
        items = category.get("list")
        if not isinstance(items, list):
            items = []
        count_raw = category.get("count", 0)
        try:
            count = int(str(count_raw).replace(",", ""))
        except Exception:
            count = 0
        for item_idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            rows.append({
                "category_index": cat_idx,
                "category_name": category.get("category_name"),
                "category_order": category.get("category_order"),
                "category_count": count,
                "page_list": category.get("pageList"),
                "item_index": item_idx,
                "item": item,
            })
    return rows


def identity_key(item: dict) -> str:
    toc = str(item.get("stored_toc_seq") or "").strip()
    url = str(item.get("stored_field_url") or "").strip()
    ebook = str(item.get("stored_ebook_no") or item.get("keyword_ebook_no") or "").strip()
    subject = re.sub(r"\s+", "", str(item.get("stored_field_subject") or ""))
    day = "".join(str(item.get(k) or "") for k in ["stored_field_year", "stored_field_month", "stored_field_day"])
    if toc:
        return "toc:" + toc
    if url:
        return "url:" + url
    if ebook:
        return "ebook:" + ebook
    return "fallback:" + subject + ":" + day


def candidate_projection(item: dict) -> dict:
    return {
        "stored_field_subject": item.get("stored_field_subject"),
        "stored_organ_nm": item.get("stored_organ_nm"),
        "stored_category_name": item.get("stored_category_name"),
        "stored_field_year": item.get("stored_field_year"),
        "stored_field_month": item.get("stored_field_month"),
        "stored_field_day": item.get("stored_field_day"),
        "stored_field_url": item.get("stored_field_url"),
        "stored_toc_seq": item.get("stored_toc_seq"),
        "stored_ebook_no": item.get("stored_ebook_no"),
        "stored_pdf_file_path": item.get("stored_pdf_file_path"),
    }


def main():
    print("=" * 78)
    print("E-GAZETTE DESIGNATION QUERY FAMILY REPLAY - S221R")
    print("=" * 78)
    print("Purpose: bounded subjectDesc expansion for designation-document discovery")
    print("Search hit != designation identity")
    print("Search no-hit != legal absence")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s221q = json.loads(S221Q.read_text(encoding="utf-8"))
    s221g = json.loads(S221G.read_text(encoding="utf-8"))

    gate_q = (
        s221q.get("classification") == "NATIONAL_REGULATORY_POLICY_LIST_CONTEXT"
        and (s221q.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
        and s221q.get("official_designation_identity_verified") is False
    )
    gate_g = (
        (s221g.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
        and (s221g.get("summary") or {}).get("positive_control_replay_qualified") is True
    )
    if not (gate_q and gate_g):
        raise AssertionError("S221R prerequisite gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "X-Requested-With": "XMLHttpRequest",
    })
    entry, entry_error = safe_get(session, ENTRY_URL)
    search_page, search_page_error = safe_get(session, SEARCH_PAGE_URL)

    query_results = []
    canonical = OrderedDict()
    request_count = 0
    http_success_count = 0
    technical_unknown_count = 0
    raw_candidate_count = 0

    for idx, term in enumerate(QUERY_TERMS, 1):
        query = build_subject_desc_query(term)
        payload = {
            "mode": "keyword",
            "index": "gwanbo",
            "query": query,
            "pQuery_tmp": term,
            "pageNo": "1",
            "listSize": "50",
            "sort": "",
        }
        response, transport_error = safe_post(session, payload)
        request_count += 1
        if response is not None and response.status_code == 200:
            http_success_count += 1
        parsed, json_error = parse_json(response)
        data_list = parsed.get("data") if isinstance(parsed, dict) else None
        response_contract = isinstance(data_list, list)
        if transport_error or json_error or not response_contract:
            technical_unknown_count += 1

        category_summaries = []
        total_count_sum = 0
        if isinstance(data_list, list):
            for cat_idx, cat in enumerate(data_list):
                if not isinstance(cat, dict):
                    continue
                try:
                    count = int(str(cat.get("count", 0)).replace(",", ""))
                except Exception:
                    count = 0
                total_count_sum += count
                if count > 0:
                    items = cat.get("list") if isinstance(cat.get("list"), list) else []
                    category_summaries.append({
                        "category_index": cat_idx,
                        "category_name": cat.get("category_name"),
                        "category_order": cat.get("category_order"),
                        "count": count,
                        "returned_item_count": len(items),
                        "page_list_present": bool(cat.get("pageList")),
                    })

        rows = iter_category_items(parsed)
        raw_candidate_count += len(rows)
        projected = []
        for row in rows:
            item = row["item"]
            key = identity_key(item)
            rec = canonical.setdefault(key, {
                "identity_key": key,
                "item": candidate_projection(item),
                "matched_queries": [],
                "category_names": [],
            })
            if term not in rec["matched_queries"]:
                rec["matched_queries"].append(term)
            if row.get("category_name") and row.get("category_name") not in rec["category_names"]:
                rec["category_names"].append(row.get("category_name"))
            projected.append({
                "identity_key": key,
                "category_name": row.get("category_name"),
                "category_order": row.get("category_order"),
                "category_count": row.get("category_count"),
                "item": candidate_projection(item),
            })

        classification = "TECHNICAL_UNKNOWN" if (transport_error or json_error or not response_contract) else ("QUERY_HIT" if total_count_sum > 0 else "QUERY_NO_HIT")
        query_results.append({
            "query_index": idx,
            "term": term,
            "compiled_query": query,
            "payload": payload,
            "http": response.status_code if response is not None else None,
            "content_type": response.headers.get("Content-Type", "") if response is not None else "",
            "body_bytes": len(response.content) if response is not None else 0,
            "transport_error": transport_error,
            "json_error": json_error,
            "response_contract": response_contract,
            "category_total_count_sum": total_count_sum,
            "nonzero_categories": category_summaries,
            "returned_candidate_count": len(rows),
            "candidates": projected,
            "classification": classification,
        })
        print(f"[{idx:02d}/{len(QUERY_TERMS):02d}] {term} http={query_results[-1]['http']} total={total_count_sum} returned={len(rows)} class={classification}")

    canonical_candidates = list(canonical.values())
    duplicate_removed = raw_candidate_count - len(canonical_candidates)

    designation_signal_terms = ["지정", "결정", "지형도면", "도시관리계획", "성남", "성남시"]
    ranked_candidates = []
    for rec in canonical_candidates:
        item = rec["item"]
        blob = " ".join(str(v or "") for v in item.values()) + " " + " ".join(rec["matched_queries"])
        signal_hits = [s for s in designation_signal_terms if s in blob]
        target_visible = TARGET in blob
        score = len(signal_hits) + (2 if target_visible else 0)
        ranked_candidates.append({**rec, "designation_signal_hits": signal_hits, "target_visible_in_returned_identity": target_visible, "discovery_score": score})
    ranked_candidates.sort(key=lambda r: (-r["discovery_score"], r["identity_key"]))

    any_query_hit = any(q["classification"] == "QUERY_HIT" for q in query_results)
    if technical_unknown_count > 0:
        classification = "QUERY_FAMILY_PARTIAL_TECHNICAL_UNKNOWN" if any_query_hit else "QUERY_FAMILY_TECHNICAL_UNKNOWN"
    elif ranked_candidates:
        classification = "DESIGNATION_QUERY_FAMILY_CANDIDATES_DISCOVERED"
    else:
        classification = "DESIGNATION_QUERY_FAMILY_NO_HIT"

    semantic = {
        "DESIGNATION_QUERY_FAMILY_CANDIDATES_DISCOVERED": "E_GAZETTE_UQQ700_DESIGNATION_QUERY_FAMILY_CANDIDATES_DISCOVERED_IDENTITY_UNQUALIFIED",
        "DESIGNATION_QUERY_FAMILY_NO_HIT": "E_GAZETTE_UQQ700_DESIGNATION_QUERY_FAMILY_NO_HIT_WITHOUT_LEGAL_ABSENCE_INFERENCE",
        "QUERY_FAMILY_PARTIAL_TECHNICAL_UNKNOWN": "E_GAZETTE_UQQ700_DESIGNATION_QUERY_FAMILY_PARTIAL_TECHNICAL_UNKNOWN",
        "QUERY_FAMILY_TECHNICAL_UNKNOWN": "E_GAZETTE_UQQ700_DESIGNATION_QUERY_FAMILY_TECHNICAL_UNKNOWN",
    }[classification]

    if classification == "DESIGNATION_QUERY_FAMILY_CANDIDATES_DISCOVERED":
        next_action = "QUALIFY_DISCOVERED_E_GAZETTE_CANDIDATE_DOCUMENT_IDENTITIES_BEFORE_DESIGNATION_PROMOTION"
    elif classification == "DESIGNATION_QUERY_FAMILY_NO_HIT":
        next_action = "REVIEW_E_GAZETTE_SOURCE_FAMILY_COVERAGE_THEN_PROCEED_TO_GYEONGGI_OFFICIAL_RECORD_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    else:
        next_action = "RESOLVE_QUERY_FAMILY_TECHNICAL_UNKNOWN_BEFORE_SOURCE_FAMILY_CLOSURE"

    out = {
        "step": "STEP 17-21-C-16-8-T-133-S221R",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "query_mode": "subjectDesc",
        "query_terms": QUERY_TERMS,
        "entry": {
            "http": entry.status_code if entry is not None else None,
            "error": entry_error,
        },
        "search_page": {
            "http": search_page.status_code if search_page is not None else None,
            "error": search_page_error,
        },
        "query_results": query_results,
        "raw_candidate_count": raw_candidate_count,
        "duplicate_candidate_removed": duplicate_removed,
        "canonical_candidate_count": len(canonical_candidates),
        "ranked_candidates": ranked_candidates,
        "classification": classification,
        "summary": {
            "request_count": request_count,
            "http_success_count": http_success_count,
            "technical_unknown_count": technical_unknown_count,
            "any_query_hit": any_query_hit,
            "semantic_state": semantic,
            "next_action": next_action,
            "search_hit_equals_designation_identity": False,
            "search_no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "official_designation_identity_verified": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nSUMMARY")
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Technical unknown count:", technical_unknown_count)
    print("Raw candidate count:", raw_candidate_count)
    print("Duplicate candidate removed:", duplicate_removed)
    print("Canonical candidate count:", len(canonical_candidates))
    print("CLASSIFICATION:", classification)

    print("\nRANKED CANDIDATES")
    for i, rec in enumerate(ranked_candidates, 1):
        print(f"--- CANDIDATE {i} ---")
        print("IDENTITY KEY:", rec["identity_key"])
        print("MATCHED QUERIES:", rec["matched_queries"])
        print("CATEGORY NAMES:", rec["category_names"])
        print("DESIGNATION SIGNAL HITS:", rec["designation_signal_hits"])
        print("TARGET VISIBLE IN RETURNED IDENTITY:", rec["target_visible_in_returned_identity"])
        print("DISCOVERY SCORE:", rec["discovery_score"])
        print(json.dumps(rec["item"], ensure_ascii=False, indent=2))

    print("\nSEMANTIC")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221Q context gate": gate_q,
        "S221G search contract gate": gate_g,
        "entry attempted": entry is not None,
        "search page attempted": search_page is not None,
        "bounded query family exact": QUERY_TERMS == [
            "개발밀도관리구역 성남",
            "개발밀도관리구역 성남시",
            "개발밀도관리구역 지정",
            "개발밀도관리구역 결정",
            "개발밀도관리구역 지형도면",
        ],
        "request count bounded": request_count == len(QUERY_TERMS),
        "all results classified": len(query_results) == len(QUERY_TERMS),
        "candidate dedupe coherent": raw_candidate_count >= len(canonical_candidates),
        "response classified": classification in {
            "DESIGNATION_QUERY_FAMILY_CANDIDATES_DISCOVERED",
            "DESIGNATION_QUERY_FAMILY_NO_HIT",
            "QUERY_FAMILY_PARTIAL_TECHNICAL_UNKNOWN",
            "QUERY_FAMILY_TECHNICAL_UNKNOWN",
        },
        "search hit not designation identity": out["summary"]["search_hit_equals_designation_identity"] is False,
        "search no-hit not legal absence": out["summary"]["search_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "SITE FALSE inference disabled": not out["summary"]["site_false_inference_allowed"],
        "designation identity not promoted": out["official_designation_identity_verified"] is False,
        "current validity not promoted": out["current_validity_verified"] is False,
        "site inclusion not promoted": out["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": not out["site_positive_allowed"] and not out["site_negative_allowed"],
        "runtime registration blocked": not out["runtime_registration_allowed"],
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S221R designation query family replay failed")


if __name__ == "__main__":
    main()
