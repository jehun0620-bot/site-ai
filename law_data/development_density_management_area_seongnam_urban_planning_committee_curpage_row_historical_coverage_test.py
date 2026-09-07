# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
S226L_OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_pagination_historical_coverage_reconstruction.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_curpage_row_historical_coverage.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
BOARD_BASE = "https://www.seongnam.go.kr/ct-bbs020102"
OFFICIAL_HOST = "www.seongnam.go.kr"
TOTAL_PAGE_CONTRACT = 11
MAX_DETAIL_SAMPLE = 24

MOVE_RE = re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
DATE_RE = re.compile(r"\b(20\d{2})[-./](\d{1,2})[-./](\d{1,2})\b")


def curl_bytes(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"ok": False, "http": None, "final_url": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "45",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}",
        url,
    ]
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


def extract_title(html: str) -> str | None:
    m = re.search(r"(?is)<title\b[^>]*>(.*?)</title>", html or "")
    return clean_html(m.group(1))[:500] if m else None


def normalize_date(y: str, m: str, d: str) -> str:
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def extract_rows(html: str) -> list[dict]:
    rows = []
    seen = set()
    # Find each onclick fn_move_form(pstSn), then bind title/date only from a bounded ancestor-like neighborhood.
    for m in MOVE_RE.finditer(html or ""):
        pst_sn = m.group(1)
        if pst_sn in seen:
            continue
        seen.add(pst_sn)
        start = max(0, m.start() - 1800)
        end = min(len(html), m.end() + 1800)
        frag = html[start:end]
        frag_text = clean_html(frag)

        # Prefer anchor/button text nearest to the handler.
        title = None
        local_before = html[max(0, m.start() - 900): min(len(html), m.end() + 900)]
        candidates = []
        for am in re.finditer(r"(?is)<(?:a|button)\b([^>]*)>(.*?)</(?:a|button)>", local_before):
            amap = attr_map(am.group(1))
            blob = (amap.get("onclick") or "") + " " + (amap.get("href") or "")
            if pst_sn in blob or MOVE_RE.search(blob):
                t = clean_html(am.group(2))
                if t:
                    candidates.append(t)
        if candidates:
            title = max(candidates, key=len)[:700]

        dates = []
        for y, mo, d in DATE_RE.findall(frag_text):
            val = normalize_date(y, mo, d)
            if val not in dates:
                dates.append(val)

        rows.append({
            "pstSn": pst_sn,
            "url": f"{BOARD_BASE}/{pst_sn}",
            "title": title,
            "row_dates": dates,
            "context": frag_text[:2600],
        })
    return rows


def fetch_page(page_no: int) -> dict:
    url = f"{BOARD_BASE}?curPage={page_no}"
    f = curl_bytes(url)
    html, enc = decode_body(f.pop("body"))
    rows = extract_rows(html)
    return {
        "page": page_no,
        "url": url,
        **f,
        "selected_charset": enc,
        "title": extract_title(html),
        "row_count": len(rows),
        "rows": rows,
        "fingerprint": [r["pstSn"] for r in rows],
        "target_visible": TARGET in clean_html(html),
    }


def inspect_detail(row: dict) -> dict:
    f = curl_bytes(row["url"])
    html, enc = decode_body(f.pop("body"))
    text = clean_html(html)
    dates = []
    for y, mo, d in DATE_RE.findall(text):
        val = normalize_date(y, mo, d)
        if val not in dates:
            dates.append(val)
    return {
        "pstSn": row["pstSn"],
        "url": row["url"],
        **f,
        "selected_charset": enc,
        "title": extract_title(html),
        "dates": dates[:30],
        "city_planning_signals": [t for t in ("도시계획위원회", "도시계획과") if t in text],
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE CURPAGE / ROW HISTORICAL COVERAGE - S226M")
    print("=" * 78)
    print("Purpose: replay curPage=1..11 and extract actual committee rows without semantic search")
    print("Pagination contract: GET ?curPage=<n>")
    print(f"Total page contract: {TOTAL_PAGE_CONTRACT}")
    print("Committee semantic query: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Committee record != designation notice")
    print("Negative evidence: DISABLED")
    print("Source closure: BLOCKED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    pages = [fetch_page(i) for i in range(1, TOTAL_PAGE_CONTRACT + 1)]
    fingerprints = [tuple(p["fingerprint"]) for p in pages]
    nonempty_pages = [p for p in pages if p["row_count"] > 0]
    distinct_fingerprints = len(set(fingerprints))

    canonical = []
    seen = set()
    for p in pages:
        for row in p["rows"]:
            if row["pstSn"] not in seen:
                seen.add(row["pstSn"])
                canonical.append(row)

    detail_samples = [inspect_detail(row) for row in canonical[:MAX_DETAIL_SAMPLE]]

    # Date evidence: row-bound dates first; detail dates are retained separately because a detail page can contain global dates.
    row_dates = sorted({d for row in canonical for d in row.get("row_dates", [])})
    row_years = sorted({d[:4] for d in row_dates})

    page_http_ok = all(p.get("http") == "200" for p in pages)
    curpage_contract_verified = page_http_ok and len(nonempty_pages) >= 2 and distinct_fingerprints >= 2
    full_11_page_coverage_verified = page_http_ok and len(nonempty_pages) == TOTAL_PAGE_CONTRACT and distinct_fingerprints >= 2
    historical_coverage_observed = curpage_contract_verified and len(canonical) >= 10

    if full_11_page_coverage_verified and historical_coverage_observed:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_CURPAGE_HISTORICAL_COVERAGE_QUALIFIED"
        semantic = "ALL_11_CURPAGE_SURFACES_REPLAYED_WITH_DISTINCT_CANONICAL_COMMITTEE_ROWS_WITHOUT_UQQ700_QUERY"
        next_action = "ASSESS_BOUNDED_UQQ700_HISTORICAL_PRECURSOR_QUERY_ELIGIBILITY_WITHOUT_DESIGNATION_OR_SITE_PROMOTION"
    elif curpage_contract_verified:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_CURPAGE_HISTORICAL_COVERAGE_PARTIAL"
        semantic = "CURPAGE_CONTRACT_VERIFIED_BUT_FULL_11_PAGE_OR_ROW_COVERAGE_REMAINS_PARTIAL"
        next_action = "HARDEN_ROW_EXTRACTION_OR_PAGE_COMPLETENESS_WITHOUT_UQQ700_QUERY"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_CURPAGE_ROW_TECHNICAL_UNKNOWN"
        semantic = "CURPAGE_REPLAY_OR_FN_MOVE_FORM_ROW_EXTRACTION_NOT_YET_TECHNICALLY_VERIFIED"
        next_action = "HARDEN_FN_MOVE_FORM_ROW_CONTAINER_EXTRACTION_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226M",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s226l_input_exists": S226L_OUT.exists(),
        "board_base": BOARD_BASE,
        "pagination_method": "GET",
        "pagination_parameter": "curPage",
        "total_page_contract": TOTAL_PAGE_CONTRACT,
        "pages": pages,
        "page_http_ok": page_http_ok,
        "nonempty_page_count": len(nonempty_pages),
        "distinct_page_fingerprint_count": distinct_fingerprints,
        "canonical_pstsn_count": len(canonical),
        "canonical_rows": canonical,
        "detail_sample_count": len(detail_samples),
        "detail_samples": detail_samples,
        "verified_row_dates": row_dates,
        "observed_years": row_years,
        "oldest_verified_row_date": row_dates[0] if row_dates else None,
        "newest_verified_row_date": row_dates[-1] if row_dates else None,
        "curpage_contract_verified": curpage_contract_verified,
        "full_11_page_coverage_verified": full_11_page_coverage_verified,
        "historical_coverage_observed": historical_coverage_observed,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "committee_semantic_query_executed": False,
            "target_query_executed": False,
            "committee_record_equals_designation_notice": False,
            "coverage_gap_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "source_closure_allowed": False,
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

    print("\nCURPAGE REPLAY")
    print("-" * 78)
    for p in pages:
        print(f"PAGE {p['page']:02d} | HTTP={p.get('http')} | ROWS={p['row_count']} | FINAL={p.get('final_url')}")
        for row in p["rows"][:12]:
            print(f"  {row['pstSn']} | {row.get('title')} | ROW_DATES={row.get('row_dates')}")

    print("\n" + "=" * 78)
    print("HISTORICAL COVERAGE SUMMARY")
    print("=" * 78)
    print(f"TOTAL PAGE CONTRACT: {TOTAL_PAGE_CONTRACT}")
    print(f"CURPAGE CONTRACT VERIFIED: {curpage_contract_verified}")
    print(f"PAGE HTTP OK: {page_http_ok}")
    print(f"NONEMPTY PAGE COUNT: {len(nonempty_pages)}")
    print(f"DISTINCT PAGE FINGERPRINT COUNT: {distinct_fingerprints}")
    print(f"CANONICAL PSTSN COUNT: {len(canonical)}")
    print(f"DETAIL SAMPLE COUNT: {len(detail_samples)}")
    print(f"OBSERVED YEARS: {row_years}")
    print(f"OLDEST VERIFIED ROW DATE: {out['oldest_verified_row_date']}")
    print(f"NEWEST VERIFIED ROW DATE: {out['newest_verified_row_date']}")
    print(f"FULL 11-PAGE COVERAGE VERIFIED: {full_11_page_coverage_verified}")
    print(f"HISTORICAL COVERAGE OBSERVED: {historical_coverage_observed}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Committee semantic query executed: False")
    print("Target query executed: False")
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Source closure allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S226L input exists": out["s226l_input_exists"] is True,
        "pagination parameter fixed to curPage": out["pagination_parameter"] == "curPage",
        "total page contract fixed to 11": out["total_page_contract"] == 11,
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_CURPAGE_HISTORICAL_COVERAGE_QUALIFIED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_CURPAGE_HISTORICAL_COVERAGE_PARTIAL",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_CURPAGE_ROW_TECHNICAL_UNKNOWN",
        },
        "committee semantic query not executed": out["summary"]["committee_semantic_query_executed"] is False,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "committee record not designation notice": out["summary"]["committee_record_equals_designation_notice"] is False,
        "coverage gap not legal absence": out["summary"]["coverage_gap_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "source closure blocked": out["summary"]["source_closure_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": out["summary"]["site_positive_allowed"] is False and out["summary"]["site_negative_allowed"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
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
        raise AssertionError("S226M validation failed")


if __name__ == "__main__":
    main()
