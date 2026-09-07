# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
S226I_OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_positive_control_search_qualification.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_board_historical_coverage_qualification.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
OFFICIAL_HOST = "www.seongnam.go.kr"
BOARD_BASE = "https://www.seongnam.go.kr/ct-bbs020102"
VERIFIED_DETAIL = f"{BOARD_BASE}/374215"
VERIFIED_DETAIL_ID = "374215"
POSITIVE_CONTROL_TITLE = "2025년 제6회 성남시 도시계획위원회 개최 결과"
ADJACENT_TITLE_PATTERNS = (
    r"2025년\s*제\s*5\s*회\s*성남시\s*도시계획위원회\s*개최\s*결과",
    r"2025년\s*제\s*6\s*회\s*성남시\s*도시계획위원회\s*개최\s*결과",
    r"2025년\s*제\s*7\s*회\s*성남시\s*도시계획위원회\s*개최\s*결과",
)
MAX_PAGE_PROBES = 12
MAX_DETAIL_SAMPLES = 18


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


def extract_title(html: str) -> str | None:
    m = re.search(r"(?is)<title\b[^>]*>(.*?)</title>", html or "")
    return clean_html(m.group(1))[:500] if m else None


def extract_links(html: str, base_url: str) -> list[dict]:
    out, seen = [], set()
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html or ""):
        attrs, inner = m.group(1), m.group(2)
        hm = re.search(r'''(?is)href\s*=\s*(["'])(.*?)\1''', attrs)
        href = unescape(hm.group(2).strip()) if hm else ""
        if not href or href.lower().startswith(("javascript:", "#", "mailto:", "tel:")):
            continue
        absolute = urljoin(base_url, href)
        if urlparse(absolute).hostname != OFFICIAL_HOST:
            continue
        text = clean_html(inner)[:1200]
        key = (absolute, text)
        if key in seen:
            continue
        seen.add(key)
        out.append({"href": absolute, "text": text})
    return out


def extract_forms(html: str, base_url: str) -> list[dict]:
    forms = []
    for fm in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html or ""):
        attrs, inner = fm.group(1), fm.group(2)
        am = re.search(r'''(?is)action\s*=\s*(["'])(.*?)\1''', attrs)
        mm = re.search(r'''(?is)method\s*=\s*(["'])(.*?)\1''', attrs)
        action = urljoin(base_url, unescape(am.group(2).strip())) if am else base_url
        method = mm.group(2).strip().upper() if mm else "GET"
        inputs = []
        for im in re.finditer(r"(?is)<(?:input|select|textarea)\b([^>]*)>", inner):
            ia = im.group(1)
            nm = re.search(r'''(?is)name\s*=\s*(["'])(.*?)\1''', ia)
            vm = re.search(r'''(?is)value\s*=\s*(["'])(.*?)\1''', ia)
            if nm:
                inputs.append({"name": unescape(nm.group(2).strip()), "value": unescape(vm.group(2)) if vm else ""})
        forms.append({"action": action, "method": method, "inputs": inputs, "text": clean_html(inner)[:2000]})
    return forms


def extract_dates(text: str) -> list[str]:
    dates = []
    for pat in (r"\b(20\d{2})[-./](\d{1,2})[-./](\d{1,2})\b", r"\b(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일\b"):
        for y, m, d in re.findall(pat, text or ""):
            v = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            if v not in dates:
                dates.append(v)
    return dates


def page_number_candidates(html: str, base_url: str) -> list[str]:
    links = extract_links(html, base_url)
    candidates = []
    for row in links:
        u = row["href"]
        q = parse_qs(urlparse(u).query)
        if any(k.lower() in {"page", "currentpage", "pageindex", "pageidx", "pageno", "cpage"} for k in q):
            if u not in candidates:
                candidates.append(u)
    return candidates[:MAX_PAGE_PROBES]


def inspect_page(label: str, url: str) -> dict:
    f = curl_bytes(url)
    html, enc = decode_body(f.pop("body"))
    text = clean_html(html)
    links = extract_links(html, f.get("final_url") or url)
    forms = extract_forms(html, f.get("final_url") or url)
    board_links = []
    for row in links:
        p = urlparse(row["href"]).path
        if re.fullmatch(r"/ct-bbs020102/\d+", p):
            board_links.append(row)
    adjacent_hits = []
    for pat in ADJACENT_TITLE_PATTERNS:
        m = re.search(pat, text)
        if m:
            adjacent_hits.append(" ".join(m.group(0).split()))
    search_input_names = sorted({i["name"] for form in forms for i in form["inputs"] if re.search(r"(?i)(search|srch|query|keyword|text)", i["name"])})
    return {
        "label": label,
        "url": url,
        **f,
        "selected_charset": enc,
        "title": extract_title(html),
        "board_identity_signals": [t for t in ("위원회", "도시계획", "도시계획위원회", "도시계획과") if t in text],
        "positive_control_visible": bool(re.search(ADJACENT_TITLE_PATTERNS[1], text)),
        "adjacent_title_hits": adjacent_hits,
        "board_detail_link_count": len(board_links),
        "board_detail_links": board_links[:100],
        "form_count": len(forms),
        "forms": forms,
        "search_input_names": search_input_names,
        "pagination_candidate_urls": page_number_candidates(html, f.get("final_url") or url),
        "dates": extract_dates(text),
        "body_prefix": text[:5000],
    }


def inspect_detail(url: str) -> dict:
    f = curl_bytes(url)
    html, enc = decode_body(f.pop("body"))
    text = clean_html(html)
    dates = extract_dates(text)
    return {
        "url": url,
        **f,
        "selected_charset": enc,
        "title": extract_title(html),
        "dates": dates,
        "city_planning_signals": [t for t in ("도시계획위원회", "도시계획과") if t in text],
        "body_prefix": text[:3000],
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE BOARD HISTORICAL COVERAGE QUALIFICATION - S226J")
    print("=" * 78)
    print("Purpose: qualify ct-bbs020102 board identity, pagination, and historical coverage before any UQQ700 query")
    print(f"Verified detail: {VERIFIED_DETAIL}")
    print("Committee search query: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Committee record != designation notice")
    print("Negative evidence: DISABLED")
    print("Source closure: BLOCKED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    container = inspect_page("board_container", BOARD_BASE)
    verified_detail = inspect_detail(VERIFIED_DETAIL)

    pagination_urls = list(container.get("pagination_candidate_urls") or [])
    page_probes = []
    for i, u in enumerate(pagination_urls[:MAX_PAGE_PROBES], 1):
        page_probes.append(inspect_page(f"pagination_{i}", u))

    all_board_links = []
    seen = set()
    for page in [container, *page_probes]:
        for row in page.get("board_detail_links") or []:
            if row["href"] not in seen:
                seen.add(row["href"])
                all_board_links.append(row)

    sampled_details = [inspect_detail(row["href"]) for row in all_board_links[:MAX_DETAIL_SAMPLES]]
    all_dates = []
    for row in [verified_detail, *sampled_details]:
        all_dates.extend(row.get("dates") or [])
    all_dates = sorted(set(all_dates))
    years = sorted({d[:4] for d in all_dates})

    adjacent_hits = sorted({hit for page in [container, *page_probes] for hit in (page.get("adjacent_title_hits") or [])})
    board_identity_verified = (
        container.get("http") == "200"
        and urlparse(container.get("final_url") or "").path.rstrip("/") == "/ct-bbs020102"
        and "위원회" in (container.get("board_identity_signals") or [])
        and "도시계획" in (container.get("board_identity_signals") or [])
        and verified_detail.get("http") == "200"
        and "도시계획위원회" in (verified_detail.get("city_planning_signals") or [])
    )
    list_contract_verified = container.get("board_detail_link_count", 0) > 0
    pagination_contract_observed = bool(pagination_urls)
    historical_coverage_observed = len(years) >= 2 or len(all_board_links) >= 10 or bool(adjacent_hits)

    if board_identity_verified and list_contract_verified and historical_coverage_observed:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOARD_HISTORICAL_COVERAGE_QUALIFIED"
        semantic = "CURRENT_COMMITTEE_BOARD_CONTAINER_LIST_CONTRACT_AND_BOUNDED_HISTORICAL_COVERAGE_VERIFIED_WITHOUT_UQQ700_QUERY"
        next_action = "ASSESS_BOUNDED_COMMITTEE_TARGET_QUERY_ELIGIBILITY_AS_HISTORICAL_PRECURSOR_ONLY_WITHOUT_DESIGNATION_PROMOTION"
    elif board_identity_verified and list_contract_verified:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOARD_IDENTIFIED_HISTORICAL_COVERAGE_PARTIAL"
        semantic = "CURRENT_COMMITTEE_BOARD_CONTAINER_AND_LIST_CONTRACT_VERIFIED_BUT_HISTORICAL_COVERAGE_REMAINS_PARTIAL"
        next_action = "EXPAND_BOUNDED_PAGINATION_COVERAGE_WITHOUT_UQQ700_QUERY_OR_NEGATIVE_INFERENCE"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOARD_CONTAINER_TECHNICAL_UNKNOWN"
        semantic = "COMMITTEE_BOARD_CONTAINER_OR_LIST_CONTRACT_NOT_YET_TECHNICALLY_QUALIFIED"
        next_action = "HARDEN_CT_BBS020102_CONTAINER_AND_PAGINATION_CONTRACT_WITHOUT_UQQ700_QUERY"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226J",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s226i_input_exists": S226I_OUT.exists(),
        "board_base": BOARD_BASE,
        "verified_detail": VERIFIED_DETAIL,
        "verified_detail_id": VERIFIED_DETAIL_ID,
        "container": container,
        "verified_detail_result": verified_detail,
        "pagination_probe_count": len(page_probes),
        "pagination_probes": page_probes,
        "canonical_board_detail_count": len(all_board_links),
        "canonical_board_details": all_board_links,
        "sampled_detail_count": len(sampled_details),
        "sampled_details": sampled_details,
        "observed_dates": all_dates,
        "observed_years": years,
        "oldest_observed_date": all_dates[0] if all_dates else None,
        "newest_observed_date": all_dates[-1] if all_dates else None,
        "adjacent_title_hits": adjacent_hits,
        "board_identity_verified": board_identity_verified,
        "list_contract_verified": list_contract_verified,
        "pagination_contract_observed": pagination_contract_observed,
        "historical_coverage_observed": historical_coverage_observed,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "committee_query_executed": False,
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

    print("\nBOARD CONTAINER")
    print("-" * 78)
    print(f"HTTP: {container.get('http')}")
    print(f"FINAL URL: {container.get('final_url')}")
    print(f"TITLE: {container.get('title')}")
    print(f"BOARD IDENTITY SIGNALS: {container.get('board_identity_signals')}")
    print(f"BOARD DETAIL LINK COUNT: {container.get('board_detail_link_count')}")
    print(f"FORM COUNT: {container.get('form_count')}")
    print(f"SEARCH INPUT NAMES: {container.get('search_input_names')}")
    print(f"PAGINATION CANDIDATE COUNT: {len(pagination_urls)}")
    for i, u in enumerate(pagination_urls, 1):
        print(f"PAGINATION [{i:02d}] {u}")

    print("\nVERIFIED DETAIL")
    print("-" * 78)
    print(f"HTTP: {verified_detail.get('http')}")
    print(f"FINAL URL: {verified_detail.get('final_url')}")
    print(f"TITLE: {verified_detail.get('title')}")
    print(f"CITY PLANNING SIGNALS: {verified_detail.get('city_planning_signals')}")
    print(f"DATES: {verified_detail.get('dates')}")

    print("\nPAGINATION PROBES")
    print("-" * 78)
    for page in page_probes:
        print(f"[{page['label']}] {page['url']}")
        print(f"  HTTP: {page.get('http')}")
        print(f"  FINAL URL: {page.get('final_url')}")
        print(f"  DETAIL LINKS: {page.get('board_detail_link_count')}")
        print(f"  ADJACENT TITLE HITS: {page.get('adjacent_title_hits')}")
        print(f"  DATES: {(page.get('dates') or [])[:12]}")

    print("\n" + "=" * 78)
    print("HISTORICAL COVERAGE SUMMARY")
    print("=" * 78)
    print(f"BOARD IDENTITY VERIFIED: {board_identity_verified}")
    print(f"LIST CONTRACT VERIFIED: {list_contract_verified}")
    print(f"PAGINATION CONTRACT OBSERVED: {pagination_contract_observed}")
    print(f"CANONICAL BOARD DETAIL COUNT: {len(all_board_links)}")
    print(f"SAMPLED DETAIL COUNT: {len(sampled_details)}")
    print(f"ADJACENT TITLE HITS: {adjacent_hits}")
    print(f"OBSERVED YEARS: {years}")
    print(f"OLDEST OBSERVED DATE: {out['oldest_observed_date']}")
    print(f"NEWEST OBSERVED DATE: {out['newest_observed_date']}")
    print(f"HISTORICAL COVERAGE OBSERVED: {historical_coverage_observed}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Committee query executed: False")
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
        "S226I input exists": out["s226i_input_exists"] is True,
        "verified detail fixed": out["verified_detail_id"] == VERIFIED_DETAIL_ID,
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOARD_HISTORICAL_COVERAGE_QUALIFIED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOARD_IDENTIFIED_HISTORICAL_COVERAGE_PARTIAL",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOARD_CONTAINER_TECHNICAL_UNKNOWN",
        },
        "committee query not executed": out["summary"]["committee_query_executed"] is False,
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
        raise AssertionError("S226J validation failed")


if __name__ == "__main__":
    main()
