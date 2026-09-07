# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path
from urllib.parse import urlencode

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
S226M_OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_curpage_row_historical_coverage.json"
S226P_OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_search_submit_mode_positive_control_recovery.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_qualified_uqq700_title_query_terminal_reconciliation.json"

TARGET = "개발밀도관리구역"
TARGET_VARIANTS = ["개발밀도관리구역", "개발밀도 관리구역"]
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
BOARD_BASE = "https://www.seongnam.go.kr/ct-bbs020102"
QUALIFIED_SEARCH_FIELD = "pstTtl"
MAX_DETAIL_FETCH = 20

MOVE_RE = re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
TOTAL_PAGE_RE = re.compile(r"var\s+totalPage\s*=\s*(\d+)", re.I)


def curl_request(url: str, *, method: str = "GET", data: str | None = None) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"ok": False, "http": None, "final_url": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "45",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}",
    ]
    if method.upper() == "POST":
        cmd += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded"]
        if data is not None:
            cmd += ["--data", data]
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 1)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
    else:
        body, http, final_url = raw, None, None
    return {
        "ok": p.returncode == 0 and bool(http and http != "000"),
        "returncode": p.returncode,
        "http": http,
        "final_url": final_url,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def decode_body(body: bytes) -> tuple[str, str]:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            text = body.decode(enc)
            if enc == "utf-8" or "성남" in text:
                return text, enc
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace"), "utf-8-replace"


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def attr_map(attrs: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r'''(?is)([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(["'])(.*?)\2''', attrs or ""):
        out[m.group(1).lower()] = unescape(m.group(3))
    return out


def extract_search_payload(html: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    for fm in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html or ""):
        amap = attr_map(fm.group(1))
        if (amap.get("id") or "") != "searchVO" and (amap.get("name") or "") != "searchVO":
            continue
        inner = fm.group(2)
        for im in re.finditer(r"(?is)<input\b([^>]*)>", inner):
            raw_attrs = im.group(1)
            i = attr_map(raw_attrs)
            name = i.get("name")
            if not name:
                continue
            typ = (i.get("type") or "text").lower()
            if typ in {"submit", "button", "image", "file"}:
                continue
            if typ in {"checkbox", "radio"} and "checked" not in raw_attrs.lower():
                continue
            payload[name] = i.get("value", "")
        for sm in re.finditer(r"(?is)<select\b([^>]*)>(.*?)</select>", inner):
            sattrs = attr_map(sm.group(1))
            name = sattrs.get("name")
            if not name:
                continue
            selected = None
            first = None
            for om in re.finditer(r"(?is)<option\b([^>]*)>(.*?)</option>", sm.group(2)):
                oattrs = attr_map(om.group(1))
                val = oattrs.get("value", clean_html(om.group(2)))
                if first is None:
                    first = val
                if "selected" in om.group(1).lower():
                    selected = val
                    break
            payload[name] = selected if selected is not None else (first or "")
        return payload
    return payload


def extract_rows(html: str) -> list[dict]:
    rows = []
    seen = set()
    for m in MOVE_RE.finditer(html or ""):
        pst_sn = m.group(1)
        if pst_sn in seen:
            continue
        seen.add(pst_sn)
        start = max(0, m.start() - 1400)
        end = min(len(html), m.end() + 1400)
        frag = html[start:end]
        title = None
        for am in re.finditer(r"(?is)<(?:a|button)\b([^>]*)>(.*?)</(?:a|button)>", frag):
            attrs = attr_map(am.group(1))
            blob = (attrs.get("onclick") or "") + " " + (attrs.get("href") or "")
            if pst_sn in blob:
                t = clean_html(am.group(2))
                if t:
                    title = t[:700]
                    break
        rows.append({"pstSn": pst_sn, "title": title, "url": f"{BOARD_BASE}/{pst_sn}"})
    return rows


def run_title_query(query: str, base_payload: dict[str, str]) -> dict:
    payload = dict(base_payload)
    payload["pstSn"] = "0"
    payload["srchTypeCd"] = QUALIFIED_SEARCH_FIELD
    payload["srchText"] = query
    if "srchDtType" in payload:
        payload["srchDtType"] = ""
    f = curl_request(BOARD_BASE, method="POST", data=urlencode(payload, doseq=True))
    html, enc = decode_body(f.pop("body"))
    text = clean_html(html)
    total = TOTAL_PAGE_RE.search(html)
    rows = extract_rows(html)
    return {
        "query": query,
        "http": f.get("http"),
        "final_url": f.get("final_url"),
        "charset": enc,
        "total_pages": int(total.group(1)) if total else (1 if f.get("http") == "200" else None),
        "row_count": len(rows),
        "rows": rows,
        "query_visible": query in text,
        "target_visible": TARGET in text,
    }


def fetch_detail(row: dict, query: str) -> dict:
    f = curl_request(row["url"])
    html, enc = decode_body(f.pop("body"))
    text = clean_html(html)
    hits = [q for q in TARGET_VARIANTS if q in text]
    snippets = []
    for q in hits:
        idx = text.find(q)
        if idx >= 0:
            snippets.append(text[max(0, idx - 400): idx + len(q) + 700])
    return {
        "pstSn": row["pstSn"],
        "title": row.get("title"),
        "url": row["url"],
        "query": query,
        "http": f.get("http"),
        "final_url": f.get("final_url"),
        "charset": enc,
        "target_hits": hits,
        "snippets": snippets,
        "signals": [x for x in ("도시계획위원회", "도시관리계획", "개발밀도관리구역", "지정", "심의", "고시") if x in text],
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE QUALIFIED UQQ700 TITLE QUERY / TERMINAL RECONCILIATION - S226Q")
    print("=" * 78)
    print("Purpose: replay UQQ700 only with the qualified title-search contract")
    print("Qualified search field: srchTypeCd=pstTtl")
    print(f"Target variants: {TARGET_VARIANTS}")
    print("Search hit != designation notice")
    print("Search no-hit != legal absence")
    print("Operational source-family closure != SITE FALSE")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    m_exists = S226M_OUT.exists()
    p_exists = S226P_OUT.exists()
    m = json.loads(S226M_OUT.read_text(encoding="utf-8")) if m_exists else {}
    p = json.loads(S226P_OUT.read_text(encoding="utf-8")) if p_exists else {}

    historical_coverage_qualified = bool(m.get("full_11_page_coverage_verified") and m.get("historical_coverage_observed"))
    submit_mode_verified = bool(p.get("search_submit_mode_verified"))
    best_probe = p.get("best_qualified_probe") or {}
    qualified_field_verified = best_probe.get("srchTypeCd") == QUALIFIED_SEARCH_FIELD

    base = curl_request(BOARD_BASE)
    base_html, base_enc = decode_body(base.pop("body"))
    base_payload = extract_search_payload(base_html)

    query_results = [run_title_query(q, base_payload) for q in TARGET_VARIANTS]
    candidate_rows = []
    seen = set()
    for qr in query_results:
        for row in qr["rows"]:
            key = row["pstSn"]
            if key not in seen:
                seen.add(key)
                candidate_rows.append({**row, "matched_query": qr["query"]})

    detail_results = [fetch_detail(r, r["matched_query"]) for r in candidate_rows[:MAX_DETAIL_FETCH]]
    verified_precursors = [d for d in detail_results if d.get("target_hits")]

    technical_query_ok = all(qr.get("http") == "200" for qr in query_results)
    any_result_rows = any(qr.get("row_count", 0) > 0 for qr in query_results)

    if verified_precursors:
        operational_closure_allowed = False
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_QUALIFIED_UQQ700_TITLE_PRECURSOR_FOUND"
        semantic = "QUALIFIED_TITLE_SEARCH_RETURNED_AND_DETAIL_VERIFIED_UQQ700_PRECURSOR_EVIDENCE_ONLY"
        next_action = "EXTRACT_REVERSE_LOOKUP_KEYS_AND_TRACE_OFFICIAL_DESIGNATION_NOTICE_WITHOUT_SITE_PROMOTION"
    elif technical_query_ok and submit_mode_verified and qualified_field_verified and historical_coverage_qualified:
        operational_closure_allowed = True
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_SOURCE_FAMILY_OPERATIONALLY_CLOSED_NO_UQQ700_TITLE_PRECURSOR"
        semantic = "QUALIFIED_PSTTTL_SEARCH_EXECUTED_OVER_QUALIFIED_PUBLIC_ARCHIVE_WITH_NO_VERIFIED_UQQ700_TITLE_PRECURSOR_NON_NEGATIVE_ONLY"
        next_action = "RESELECT_NEXT_OFFICIAL_HISTORICAL_SOURCE_FAMILY_WHILE_KEEPING_UQQ700_UNKNOWN"
    else:
        operational_closure_allowed = False
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_QUALIFIED_UQQ700_TITLE_QUERY_TECHNICAL_UNKNOWN"
        semantic = "QUALIFIED_SEARCH_PREREQUISITES_OR_QUERY_TRANSPORT_NOT_ALL_VERIFIED"
        next_action = "HARDEN_QUALIFIED_TITLE_QUERY_EXECUTION_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226Q",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s226m_input_exists": m_exists,
        "s226p_input_exists": p_exists,
        "historical_coverage_qualified": historical_coverage_qualified,
        "search_submit_mode_verified": submit_mode_verified,
        "qualified_field_verified": qualified_field_verified,
        "qualified_search_field": QUALIFIED_SEARCH_FIELD,
        "base_http": base.get("http"),
        "base_charset": base_enc,
        "query_results": query_results,
        "candidate_row_count": len(candidate_rows),
        "candidate_rows": candidate_rows,
        "detail_fetch_count": len(detail_results),
        "detail_results": detail_results,
        "verified_precursor_count": len(verified_precursors),
        "verified_precursors": verified_precursors,
        "technical_query_ok": technical_query_ok,
        "any_result_rows": any_result_rows,
        "operational_closure_allowed": operational_closure_allowed,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "source_family_operationally_closed": operational_closure_allowed,
            "search_hit_equals_designation_notice": False,
            "search_hit_equals_current_validity": False,
            "search_hit_equals_site_inclusion": False,
            "search_no_hit_equals_legal_absence": False,
            "operational_closure_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nQUALIFIED INPUT")
    print("-" * 78)
    print(f"S226M INPUT EXISTS: {m_exists}")
    print(f"S226P INPUT EXISTS: {p_exists}")
    print(f"HISTORICAL COVERAGE QUALIFIED: {historical_coverage_qualified}")
    print(f"SEARCH SUBMIT MODE VERIFIED: {submit_mode_verified}")
    print(f"QUALIFIED FIELD VERIFIED: {qualified_field_verified}")
    print(f"QUALIFIED SEARCH FIELD: {QUALIFIED_SEARCH_FIELD}")

    print("\nQUALIFIED UQQ700 TITLE QUERIES")
    print("-" * 78)
    for qr in query_results:
        print(f"QUERY={qr['query']} | HTTP={qr.get('http')} | PAGES={qr.get('total_pages')} | ROWS={qr.get('row_count')} | TARGET_VISIBLE={qr.get('target_visible')}")
        for row in qr["rows"]:
            print(f"  PSTSN={row['pstSn']} | TITLE={row.get('title')}")

    print("\nDETAIL VERIFICATION")
    print("-" * 78)
    print(f"CANDIDATE ROW COUNT: {len(candidate_rows)}")
    print(f"DETAIL FETCH COUNT: {len(detail_results)}")
    print(f"VERIFIED PRECURSOR COUNT: {len(verified_precursors)}")
    for d in verified_precursors:
        print(f"PSTSN={d['pstSn']} | TITLE={d.get('title')} | HITS={d.get('target_hits')}")
        for s in d.get("snippets") or []:
            print(f"  SNIPPET: {s[:1000]}")

    print("\n" + "=" * 78)
    print("TERMINAL RECONCILIATION")
    print("=" * 78)
    print(f"TECHNICAL QUERY OK: {technical_query_ok}")
    print(f"ANY RESULT ROWS: {any_result_rows}")
    print(f"OPERATIONAL CLOSURE ALLOWED: {operational_closure_allowed}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Search no-hit == legal absence: False")
    print("Operational closure == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S226M input exists": m_exists,
        "S226P input exists": p_exists,
        "historical coverage qualified": historical_coverage_qualified,
        "search submit mode verified": submit_mode_verified,
        "qualified field pstTtl verified": qualified_field_verified,
        "qualified field fixed": out["qualified_search_field"] == "pstTtl",
        "technical query executed": technical_query_ok,
        "search hit not designation notice": out["summary"]["search_hit_equals_designation_notice"] is False,
        "search hit not current validity": out["summary"]["search_hit_equals_current_validity"] is False,
        "search hit not site inclusion": out["summary"]["search_hit_equals_site_inclusion"] is False,
        "search no-hit not legal absence": out["summary"]["search_no_hit_equals_legal_absence"] is False,
        "operational closure not legal absence": out["summary"]["operational_closure_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": out["summary"]["site_positive_allowed"] is False and out["summary"]["site_negative_allowed"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_QUALIFIED_UQQ700_TITLE_PRECURSOR_FOUND",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_SOURCE_FAMILY_OPERATIONALLY_CLOSED_NO_UQQ700_TITLE_PRECURSOR",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_QUALIFIED_UQQ700_TITLE_QUERY_TECHNICAL_UNKNOWN",
        },
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for key, value in validation.items():
        print(f"{key}: {value}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")

    if not all(validation.values()):
        raise AssertionError("S226Q validation failed")


if __name__ == "__main__":
    main()
