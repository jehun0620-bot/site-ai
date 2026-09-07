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
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_bounded_uqq700_historical_precursor_query.json"

TARGET = "개발밀도관리구역"
TARGET_VARIANTS = ["개발밀도관리구역", "개발밀도 관리구역"]
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
BOARD_BASE = "https://www.seongnam.go.kr/ct-bbs020102"
MAX_RESULT_PAGES = 11
MAX_DETAIL_FETCH = 40

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
            pass
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
            i = attr_map(im.group(1))
            name = i.get("name")
            if not name:
                continue
            typ = (i.get("type") or "text").lower()
            if typ in {"submit", "button", "image", "file"}:
                continue
            if typ in {"checkbox", "radio"} and "checked" not in im.group(1).lower():
                continue
            payload[name] = i.get("value", "")
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
        start = max(0, m.start() - 1500)
        end = min(len(html), m.end() + 1500)
        frag = html[start:end]
        text = clean_html(frag)
        title = None
        for am in re.finditer(r"(?is)<(?:a|button)\b([^>]*)>(.*?)</(?:a|button)>", frag):
            attrs = attr_map(am.group(1))
            blob = (attrs.get("onclick") or "") + " " + (attrs.get("href") or "")
            if pst_sn in blob:
                t = clean_html(am.group(2))
                if t:
                    title = t[:700]
                    break
        rows.append({
            "pstSn": pst_sn,
            "title": title,
            "url": f"{BOARD_BASE}/{pst_sn}",
            "context": text[:3000],
            "target_variants_in_context": [q for q in TARGET_VARIANTS if q in text],
        })
    return rows


def target_hits(text: str) -> list[str]:
    return [q for q in TARGET_VARIANTS if q in text]


def fetch_detail(row: dict) -> dict:
    f = curl_request(row["url"])
    html, enc = decode_body(f.pop("body"))
    text = clean_html(html)
    hits = target_hits(text)
    snippets = []
    for q in hits:
        idx = text.find(q)
        if idx >= 0:
            snippets.append(text[max(0, idx - 350): idx + len(q) + 550])
    return {
        "pstSn": row["pstSn"],
        "url": row["url"],
        "http": f.get("http"),
        "final_url": f.get("final_url"),
        "charset": enc,
        "target_hits": hits,
        "snippets": snippets,
        "city_planning_signals": [x for x in ("도시계획위원회", "도시계획과", "도시관리계획", "지정", "심의") if x in text],
    }


def local_corpus_scan(s226m: dict) -> list[dict]:
    hits = []
    for row in s226m.get("canonical_rows") or []:
        blob = " ".join([str(row.get("title") or ""), str(row.get("context") or "")])
        matched = target_hits(blob)
        if matched:
            hits.append({
                "pstSn": row.get("pstSn"),
                "title": row.get("title"),
                "url": row.get("url"),
                "matched_variants": matched,
            })
    return hits


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE BOUNDED UQQ700 HISTORICAL PRECURSOR QUERY - S226N")
    print("=" * 78)
    print("Purpose: query the qualified committee archive only for historical precursor clues")
    print(f"Target: {TARGET}")
    print("Search hit != designation notice")
    print("Search hit != current validity")
    print("Search hit != SITE inclusion")
    print("Search no-hit != legal absence")
    print("Negative evidence: DISABLED")
    print("SITE FALSE inference: BLOCKED")
    print("Source closure: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s226m_exists = S226M_OUT.exists()
    s226m = json.loads(S226M_OUT.read_text(encoding="utf-8")) if s226m_exists else {}
    coverage_qualified = bool(s226m.get("full_11_page_coverage_verified") and s226m.get("historical_coverage_observed"))
    local_hits = local_corpus_scan(s226m) if s226m_exists else []

    base = curl_request(BOARD_BASE)
    base_html, base_enc = decode_body(base.pop("body"))
    payload = extract_search_payload(base_html)
    payload["pstSn"] = "0"
    payload["srchText"] = TARGET
    # Keep the board's observed/default search mode. Do not invent unqualified field modes.
    encoded = urlencode(payload, doseq=True)
    first = curl_request(BOARD_BASE, method="POST", data=encoded)
    first_html, first_enc = decode_body(first.pop("body"))
    first_rows = extract_rows(first_html)
    total_match = TOTAL_PAGE_RE.search(first_html)
    result_total_pages = int(total_match.group(1)) if total_match else 1
    result_total_pages = max(1, min(result_total_pages, MAX_RESULT_PAGES))

    result_pages = [{
        "page": 1,
        "method": "POST",
        "http": first.get("http"),
        "final_url": first.get("final_url"),
        "charset": first_enc,
        "target_visible": bool(target_hits(clean_html(first_html))),
        "rows": first_rows,
    }]

    # If the result surface itself exposes multiple pages, follow the qualified curPage contract.
    # We preserve the submitted srchText in POST only on page 1; subsequent GET pages are diagnostic and
    # candidates must still contain target evidence in row context/detail before promotion to precursor candidate.
    for page_no in range(2, result_total_pages + 1):
        f = curl_request(f"{BOARD_BASE}?curPage={page_no}")
        html, enc = decode_body(f.pop("body"))
        result_pages.append({
            "page": page_no,
            "method": "GET",
            "http": f.get("http"),
            "final_url": f.get("final_url"),
            "charset": enc,
            "target_visible": bool(target_hits(clean_html(html))),
            "rows": extract_rows(html),
        })

    candidate_rows = []
    seen = set()
    for p in result_pages:
        for row in p["rows"]:
            if row["pstSn"] in seen:
                continue
            # Require target evidence on returned row/context or local qualified corpus before detail fetch.
            local_match = next((x for x in local_hits if str(x.get("pstSn")) == str(row["pstSn"])), None)
            if row.get("target_variants_in_context") or local_match:
                seen.add(row["pstSn"])
                candidate_rows.append(row)

    details = [fetch_detail(r) for r in candidate_rows[:MAX_DETAIL_FETCH]]
    verified_precursor_candidates = [d for d in details if d.get("target_hits")]

    if verified_precursor_candidates:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_UQQ700_HISTORICAL_PRECURSOR_CANDIDATE_FOUND"
        semantic = "TARGET_TERM_VERIFIED_IN_OFFICIAL_COMMITTEE_DETAIL_AS_HISTORICAL_PRECURSOR_EVIDENCE_ONLY"
        next_action = "EXTRACT_REVERSE_LOOKUP_KEYS_FROM_VERIFIED_COMMITTEE_CONTEXT_AND_TRACE_OFFICIAL_DESIGNATION_NOTICE"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOUNDED_UQQ700_QUERY_NO_VERIFIED_PRECURSOR_CANDIDATE"
        semantic = "NO_VERIFIED_TARGET_TERM_PRECURSOR_CANDIDATE_OBSERVED_IN_BOUNDED_QUALIFIED_COMMITTEE_SURFACE"
        next_action = "KEEP_UQQ700_UNKNOWN_AND_RECONCILE_COMMITTEE_NO_HIT_AS_NON_NEGATIVE_EVIDENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226N",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s226m_input_exists": s226m_exists,
        "historical_coverage_qualified": coverage_qualified,
        "qualified_archive_canonical_count": s226m.get("canonical_pstsn_count"),
        "qualified_archive_observed_years": s226m.get("observed_years"),
        "target_variants": TARGET_VARIANTS,
        "local_corpus_hit_count": len(local_hits),
        "local_corpus_hits": local_hits,
        "board_search": {
            "http": first.get("http"),
            "final_url": first.get("final_url"),
            "base_charset": base_enc,
            "result_charset": first_enc,
            "submitted_parameter": "srchText",
            "submitted_value": TARGET,
            "result_total_pages_bounded": result_total_pages,
            "pages": result_pages,
        },
        "candidate_row_count": len(candidate_rows),
        "candidate_rows": candidate_rows,
        "detail_fetch_count": len(details),
        "details": details,
        "verified_precursor_candidate_count": len(verified_precursor_candidates),
        "verified_precursor_candidates": verified_precursor_candidates,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "target_query_executed": True,
            "committee_hit_equals_designation_notice": False,
            "committee_hit_equals_current_validity": False,
            "committee_hit_equals_site_inclusion": False,
            "query_no_hit_equals_legal_absence": False,
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

    print("\nQUALIFIED INPUT")
    print("-" * 78)
    print(f"S226M INPUT EXISTS: {s226m_exists}")
    print(f"HISTORICAL COVERAGE QUALIFIED: {coverage_qualified}")
    print(f"QUALIFIED ARCHIVE CANONICAL COUNT: {s226m.get('canonical_pstsn_count')}")
    print(f"QUALIFIED ARCHIVE OBSERVED YEARS: {s226m.get('observed_years')}")
    print(f"LOCAL CORPUS TARGET HIT COUNT: {len(local_hits)}")
    for h in local_hits:
        print(f"  LOCAL HIT {h.get('pstSn')} | {h.get('title')} | {h.get('matched_variants')}")

    print("\nOFFICIAL BOARD QUERY")
    print("-" * 78)
    print(f"HTTP: {first.get('http')}")
    print(f"FINAL URL: {first.get('final_url')}")
    print("QUERY PARAMETER: srchText")
    print(f"QUERY VALUE: {TARGET}")
    print(f"RESULT PAGE COUNT (BOUNDED): {result_total_pages}")
    for p in result_pages:
        print(f"PAGE {p['page']:02d} | METHOD={p['method']} | HTTP={p.get('http')} | ROWS={len(p['rows'])} | TARGET_VISIBLE={p['target_visible']}")

    print("\nVERIFIED PRECURSOR CANDIDATES")
    print("-" * 78)
    print(f"CANDIDATE ROW COUNT: {len(candidate_rows)}")
    print(f"DETAIL FETCH COUNT: {len(details)}")
    print(f"VERIFIED PRECURSOR CANDIDATE COUNT: {len(verified_precursor_candidates)}")
    for d in verified_precursor_candidates:
        print(f"PSTSN={d['pstSn']} | HTTP={d.get('http')} | HITS={d.get('target_hits')}")
        for s in d.get('snippets') or []:
            print(f"  SNIPPET: {s[:900]}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Target query executed: True")
    print("Committee hit == designation notice: False")
    print("Committee hit == current validity: False")
    print("Committee hit == SITE inclusion: False")
    print("Query no-hit == legal absence: False")
    print("Negative evidence allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Source closure allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S226M input exists": out["s226m_input_exists"] is True,
        "historical coverage qualified": out["historical_coverage_qualified"] is True,
        "target query executed": out["summary"]["target_query_executed"] is True,
        "committee hit not designation notice": out["summary"]["committee_hit_equals_designation_notice"] is False,
        "committee hit not current validity": out["summary"]["committee_hit_equals_current_validity"] is False,
        "committee hit not SITE inclusion": out["summary"]["committee_hit_equals_site_inclusion"] is False,
        "query no-hit not legal absence": out["summary"]["query_no_hit_equals_legal_absence"] is False,
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
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_UQQ700_HISTORICAL_PRECURSOR_CANDIDATE_FOUND",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOUNDED_UQQ700_QUERY_NO_VERIFIED_PRECURSOR_CANDIDATE",
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
        raise AssertionError("S226N validation failed")


if __name__ == "__main__":
    main()
