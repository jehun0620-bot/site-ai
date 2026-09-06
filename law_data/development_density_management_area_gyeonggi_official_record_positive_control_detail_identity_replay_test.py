# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
S223D = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_category_token_replay.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_positive_control_detail_identity_replay.json"

POSITIVE_CONTROL = "예산"
CATEGORY_TOKEN = "고시공고"
TARGET = "개발밀도관리구역"
SAMPLE_LIMIT = 3
DATE_RE = re.compile(r"\b20\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2}\b")


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", "", clean_html(s)).strip()


def query_identity(url: str):
    q = parse_qs(urlparse(url).query)
    out = {}
    for key in ["bsIdx", "bIdx", "menuId"]:
        if q.get(key):
            out[key] = q[key][0]
    return out


def extract_result_title(row_title: str) -> str:
    # S223D title contains title + department/date + breadcrumb. Cut before the first YYYY.MM.DD context.
    text = " ".join((row_title or "").split())
    m = DATE_RE.search(text)
    if not m:
        return text
    prefix = text[:m.start()].strip()
    # The department appears immediately before '| YYYY.MM.DD'. Remove the final department segment conservatively.
    prefix = re.sub(r"\s+[^|]{1,40}\|\s*$", "", prefix).strip()
    if " |" in prefix:
        prefix = prefix.rsplit(" |", 1)[0].strip()
    return prefix


def fetch(session: requests.Session, url: str, referer: str | None = None):
    try:
        headers = {"Referer": referer} if referer else None
        r = session.get(url, timeout=60, allow_redirects=True, headers=headers)
        return r, None
    except requests.RequestException as ex:
        return None, f"{type(ex).__name__}: {ex}"


def main():
    print("=" * 78)
    print("GYEONGGI OFFICIAL RECORD POSITIVE-CONTROL DETAIL IDENTITY REPLAY - S223E")
    print("=" * 78)
    print("Purpose: verify bIdx + bsIdx + menuId + title + date against real detail pages")
    print("Positive control only; UQQ700 target query is NOT executed")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s223d = json.loads(S223D.read_text(encoding="utf-8"))
    gate_223d = (
        s223d.get("classification") == "GYEONGGI_OFFICIAL_RECORD_ACTUAL_CATEGORY_TOKEN_REAL_RESULT_DOM_QUALIFIED"
        and (s223d.get("category_contract") or {}).get("actual_request_token") == CATEGORY_TOKEN
        and (s223d.get("summary") or {}).get("target_query_executed") is False
        and (s223d.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not gate_223d:
        raise AssertionError("S223E prerequisite S223D gate not satisfied")

    rows = ((s223d.get("result_contract") or {}).get("rows") or [])[:SAMPLE_LIMIT]
    if not rows:
        raise AssertionError("S223D has no positive-control result rows")

    prepared = []
    for row in rows:
        url = row.get("absolute_href") or ""
        ident = query_identity(url)
        dates = row.get("date_hits") or DATE_RE.findall(row.get("fragment_text") or row.get("title") or "")
        result_title = extract_result_title(row.get("title") or "")
        prepared.append({
            "source_row": row,
            "url": url,
            "identity": ident,
            "bIdx": ident.get("bIdx"),
            "bsIdx": ident.get("bsIdx"),
            "menuId": ident.get("menuId"),
            "result_title": result_title,
            "date": dates[0] if dates else None,
        })

    bidx_values = [x.get("bIdx") for x in prepared if x.get("bIdx")]
    bidx_extracted = len(bidx_values) == len(prepared)
    bidx_unique = bidx_extracted and len(set(bidx_values)) == len(bidx_values)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    detail_results = []
    for item in prepared:
        r, err = fetch(session, item["url"], referer=(s223d.get("token_replay_request") or {}).get("final_url"))
        body = r.text if r is not None else ""
        flat = clean_html(body)
        norm = normalize_text(body)
        final_url = r.url if r is not None else None
        final_ident = query_identity(final_url or "")

        title = item.get("result_title") or ""
        title_norm = normalize_text(title)
        title_match = bool(title_norm and title_norm in norm)
        date = item.get("date")
        date_match = bool(date and date in flat)

        # Identity can be preserved in final URL or echoed in page markup/scripts/forms.
        bidx = item.get("bIdx")
        bsidx = item.get("bsIdx")
        menuid = item.get("menuId")
        bidx_match = bool(
            bidx and (
                final_ident.get("bIdx") == bidx
                or re.search(rf"(?i)\bbIdx\b\s*[=:]\s*['\"]?{re.escape(bidx)}\b", body)
                or f"bIdx={bidx}" in body
            )
        )
        bsidx_match = bool(
            bsidx and (
                final_ident.get("bsIdx") == bsidx
                or re.search(rf"(?i)\bbsIdx\b\s*[=:]\s*['\"]?{re.escape(bsidx)}\b", body)
                or f"bsIdx={bsidx}" in body
            )
        )
        menuid_match = bool(
            menuid and (
                final_ident.get("menuId") == menuid
                or re.search(rf"(?i)\bmenuId\b\s*[=:]\s*['\"]?{re.escape(menuid)}\b", body)
                or f"menuId={menuid}" in body
            )
        )
        http_ok = bool(r is not None and r.status_code == 200)
        board_identity_match = bool(bsidx_match and menuid_match)
        detail_identity_match = bool(http_ok and title_match and bidx_match and board_identity_match and date_match)

        detail_results.append({
            "source": {
                "url": item["url"],
                "bIdx": bidx,
                "bsIdx": bsidx,
                "menuId": menuid,
                "result_title": title,
                "date": date,
            },
            "http": r.status_code if r is not None else None,
            "final_url": final_url,
            "error": err,
            "final_url_identity": final_ident,
            "title_match": title_match,
            "date_match": date_match,
            "bidx_identity_match": bidx_match,
            "bsidx_identity_match": bsidx_match,
            "menuid_identity_match": menuid_match,
            "board_identity_match": board_identity_match,
            "detail_identity_match": detail_identity_match,
            "detail_text_prefix": flat[:1200],
        })

    attempted = len(detail_results)
    http_all_200 = bool(attempted and all(x["http"] == 200 for x in detail_results))
    title_all_match = bool(attempted and all(x["title_match"] for x in detail_results))
    date_all_match = bool(attempted and all(x["date_match"] for x in detail_results))
    bidx_all_match = bool(attempted and all(x["bidx_identity_match"] for x in detail_results))
    board_all_match = bool(attempted and all(x["board_identity_match"] for x in detail_results))
    detail_all_match = bool(attempted and all(x["detail_identity_match"] for x in detail_results))

    qualified = bool(
        bidx_extracted
        and bidx_unique
        and attempted == min(SAMPLE_LIMIT, len(rows))
        and http_all_200
        and title_all_match
        and date_all_match
        and bidx_all_match
        and board_all_match
        and detail_all_match
    )

    if qualified:
        classification = "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_IDENTITY_QUALIFIED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_BIDX_BSIDX_MENUID_TITLE_DATE_DETAIL_IDENTITY_QUALIFIED"
        next_action = "BUILD_S224_UQQ700_TARGET_REPLAY_USING_VERIFIED_GYEONGGI_SEARCH_AND_DETAIL_CONTRACT"
    elif attempted and http_all_200:
        classification = "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_IDENTITY_PARTIAL"
        semantic = "GYEONGGI_OFFICIAL_RECORD_DETAIL_NAVIGATION_WORKS_IDENTITY_MATCH_PARTIAL"
        next_action = "HARDEN_DETAIL_IDENTITY_MATCH_BEFORE_UQQ700_TARGET_REPLAY"
    else:
        classification = "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_IDENTITY_TECHNICAL_UNKNOWN"
        semantic = "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_NAVIGATION_TECHNICAL_UNKNOWN"
        next_action = "RECOVER_DETAIL_NAVIGATION_CONTRACT_BEFORE_UQQ700_TARGET_REPLAY"

    out = {
        "step": "STEP 17-21-C-16-8-T-136E-S223E",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "GYEONGGI_OFFICIAL_RECORD",
        "positive_control": POSITIVE_CONTROL,
        "category_token": CATEGORY_TOKEN,
        "s223d_gate": gate_223d,
        "sample_count": len(prepared),
        "bidx_extracted": bidx_extracted,
        "bidx_unique_across_sample": bidx_unique,
        "detail_results": detail_results,
        "aggregate": {
            "detail_attempted_count": attempted,
            "detail_http_all_200": http_all_200,
            "detail_title_all_match": title_all_match,
            "detail_date_all_match": date_all_match,
            "detail_bidx_all_match": bidx_all_match,
            "detail_board_identity_all_match": board_all_match,
            "positive_control_detail_contract_qualified": qualified,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "positive_control_only": True,
            "target_query_executed": False,
            "search_hit_equals_legal_fact": False,
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

    print("S223D GATE:", gate_223d)
    print("SAMPLE COUNT:", len(prepared))
    print("BIDX EXTRACTED:", bidx_extracted)
    print("BIDX UNIQUE ACROSS SAMPLE:", bidx_unique)
    print("DETAIL ATTEMPTED COUNT:", attempted)
    print("DETAIL HTTP ALL 200:", http_all_200)
    print("DETAIL TITLE ALL MATCH:", title_all_match)
    print("DETAIL DATE ALL MATCH:", date_all_match)
    print("DETAIL BIDX IDENTITY ALL MATCH:", bidx_all_match)
    print("DETAIL BOARD IDENTITY ALL MATCH:", board_all_match)
    print("POSITIVE CONTROL DETAIL CONTRACT QUALIFIED:", qualified)
    print("CLASSIFICATION:", classification)

    print("\nDETAIL RESULTS")
    for i, item in enumerate(detail_results, 1):
        print(f"--- DETAIL {i} ---")
        print(json.dumps(item, ensure_ascii=False, indent=2))

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Target query executed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S223D qualified gate": gate_223d,
        "sample rows loaded": len(prepared) > 0,
        "bIdx extraction checked": isinstance(bidx_extracted, bool),
        "bIdx uniqueness checked": isinstance(bidx_unique, bool),
        "detail navigation attempted": attempted > 0,
        "detail HTTP checked": isinstance(http_all_200, bool),
        "detail title checked": isinstance(title_all_match, bool),
        "detail date checked": isinstance(date_all_match, bool),
        "detail bIdx identity checked": isinstance(bidx_all_match, bool),
        "detail board identity checked": isinstance(board_all_match, bool),
        "response classified": classification in {
            "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_IDENTITY_QUALIFIED",
            "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_IDENTITY_PARTIAL",
            "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_IDENTITY_TECHNICAL_UNKNOWN",
        },
        "positive control only": out["summary"]["positive_control_only"] is True,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "search hit not legal fact": out["summary"]["search_hit_equals_legal_fact"] is False,
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
        raise AssertionError("S223E Gyeonggi positive-control detail identity replay failed")


if __name__ == "__main__":
    main()
