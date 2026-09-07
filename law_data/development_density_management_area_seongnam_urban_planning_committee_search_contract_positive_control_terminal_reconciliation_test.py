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
S226N_OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_bounded_uqq700_historical_precursor_query.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_search_contract_positive_control_terminal_reconciliation.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
BOARD_BASE = "https://www.seongnam.go.kr/ct-bbs020102"
POSITIVE_CONTROL_TITLE = "2025년 제6회 성남시 도시계획위원회 개최 결과"
POSITIVE_CONTROL_PSTSN = "374215"

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
        for im in re.finditer(r"(?is)<input\b([^>]*)>", fm.group(2)):
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
        return payload
    return payload


def extract_pstsns(html: str) -> list[str]:
    out = []
    for m in MOVE_RE.finditer(html or ""):
        sn = m.group(1)
        if sn not in out:
            out.append(sn)
    return out


def search(query: str, base_payload: dict[str, str]) -> dict:
    payload = dict(base_payload)
    payload["pstSn"] = "0"
    payload["srchText"] = query
    f = curl_request(BOARD_BASE, method="POST", data=urlencode(payload, doseq=True))
    html, enc = decode_body(f.pop("body"))
    text = clean_html(html)
    total = TOTAL_PAGE_RE.search(html)
    pstsns = extract_pstsns(html)
    return {
        "query": query,
        "http": f.get("http"),
        "final_url": f.get("final_url"),
        "charset": enc,
        "total_pages": int(total.group(1)) if total else None,
        "pstsns": pstsns,
        "row_count": len(pstsns),
        "exact_query_visible": query in text,
        "positive_control_pstsn_visible": POSITIVE_CONTROL_PSTSN in pstsns or POSITIVE_CONTROL_PSTSN in html,
        "target_visible": TARGET in text,
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE SEARCH CONTRACT POSITIVE CONTROL / TERMINAL RECONCILIATION - S226O")
    print("=" * 78)
    print("Purpose: verify board search filtering with a known positive control and reconcile S226N conservatively")
    print(f"Positive control: {POSITIVE_CONTROL_TITLE}")
    print(f"Positive control pstSn: {POSITIVE_CONTROL_PSTSN}")
    print(f"Target: {TARGET}")
    print("Operational closure != legal absence")
    print("Negative evidence: DISABLED")
    print("SITE FALSE inference: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    m_exists = S226M_OUT.exists()
    n_exists = S226N_OUT.exists()
    m = json.loads(S226M_OUT.read_text(encoding="utf-8")) if m_exists else {}
    n = json.loads(S226N_OUT.read_text(encoding="utf-8")) if n_exists else {}

    base = curl_request(BOARD_BASE)
    base_html, base_enc = decode_body(base.pop("body"))
    base_payload = extract_search_payload(base_html)
    baseline_pstsns = extract_pstsns(base_html)
    baseline_total = TOTAL_PAGE_RE.search(base_html)
    baseline_total_pages = int(baseline_total.group(1)) if baseline_total else None

    positive = search(POSITIVE_CONTROL_TITLE, base_payload)
    target = search(TARGET, base_payload)

    positive_result_differs = positive["pstsns"] != baseline_pstsns or positive["total_pages"] != baseline_total_pages
    target_result_differs = target["pstsns"] != baseline_pstsns or target["total_pages"] != baseline_total_pages
    positive_identity_recovered = positive["positive_control_pstsn_visible"] or positive["exact_query_visible"]
    search_contract_verified = (
        positive.get("http") == "200"
        and positive_identity_recovered
        and positive_result_differs
    )

    s226n_no_candidate = n.get("verified_precursor_candidate_count") == 0
    operational_closure_allowed = bool(search_contract_verified and s226n_no_candidate and m.get("full_11_page_coverage_verified"))

    if operational_closure_allowed:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_SOURCE_FAMILY_OPERATIONALLY_CLOSED_NO_UQQ700_PRECURSOR"
        semantic = "QUALIFIED_ARCHIVE_AND_POSITIVE_CONTROL_SEARCH_CONTRACT_VERIFIED_WITH_NO_UQQ700_PRECURSOR_OBSERVED_NON_NEGATIVE_ONLY"
        next_action = "RESELECT_NEXT_OFFICIAL_HISTORICAL_SOURCE_FAMILY_WHILE_KEEPING_UQQ700_UNKNOWN"
    elif search_contract_verified:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_SEARCH_CONTRACT_VERIFIED_RECONCILIATION_INCOMPLETE"
        semantic = "POSITIVE_CONTROL_SEARCH_FILTER_VERIFIED_BUT_TERMINAL_RECONCILIATION_GATES_NOT_ALL_MET"
        next_action = "HARDEN_S226N_RESULT_RECONCILIATION_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_SEARCH_FILTER_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "POSITIVE_CONTROL_DID_NOT_YET_PROVE_SERVER_SIDE_BOARD_FILTERING"
        next_action = "RECOVER_SRCHTYPECD_OR_SEARCH_SUBMIT_MODE_WITH_POSITIVE_CONTROL_BEFORE_SOURCE_FAMILY_CLOSURE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226O",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s226m_input_exists": m_exists,
        "s226n_input_exists": n_exists,
        "historical_coverage_qualified": bool(m.get("full_11_page_coverage_verified") and m.get("historical_coverage_observed")),
        "baseline": {
            "http": base.get("http"),
            "charset": base_enc,
            "total_pages": baseline_total_pages,
            "first_page_pstsns": baseline_pstsns,
        },
        "positive_control": positive,
        "target_query": target,
        "positive_result_differs_from_baseline": positive_result_differs,
        "target_result_differs_from_baseline": target_result_differs,
        "positive_control_identity_recovered": positive_identity_recovered,
        "search_contract_verified": search_contract_verified,
        "s226n_verified_precursor_candidate_count": n.get("verified_precursor_candidate_count"),
        "operational_closure_allowed": operational_closure_allowed,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "source_family_operationally_closed": operational_closure_allowed,
            "operational_closure_equals_legal_absence": False,
            "query_no_hit_equals_legal_absence": False,
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

    print("\nBASELINE")
    print("-" * 78)
    print(f"HTTP: {base.get('http')}")
    print(f"TOTAL PAGES: {baseline_total_pages}")
    print(f"FIRST PAGE PSTSNS: {baseline_pstsns}")

    print("\nPOSITIVE CONTROL SEARCH")
    print("-" * 78)
    print(f"HTTP: {positive.get('http')}")
    print(f"TOTAL PAGES: {positive.get('total_pages')}")
    print(f"ROWS: {positive.get('row_count')}")
    print(f"PSTSNS: {positive.get('pstsns')}")
    print(f"EXACT QUERY VISIBLE: {positive.get('exact_query_visible')}")
    print(f"POSITIVE CONTROL PSTSN VISIBLE: {positive.get('positive_control_pstsn_visible')}")
    print(f"RESULT DIFFERS FROM BASELINE: {positive_result_differs}")

    print("\nTARGET SEARCH RECONCILIATION")
    print("-" * 78)
    print(f"HTTP: {target.get('http')}")
    print(f"TOTAL PAGES: {target.get('total_pages')}")
    print(f"ROWS: {target.get('row_count')}")
    print(f"PSTSNS: {target.get('pstsns')}")
    print(f"TARGET VISIBLE: {target.get('target_visible')}")
    print(f"RESULT DIFFERS FROM BASELINE: {target_result_differs}")
    print(f"S226N VERIFIED PRECURSOR CANDIDATE COUNT: {n.get('verified_precursor_candidate_count')}")

    print("\n" + "=" * 78)
    print("TERMINAL RECONCILIATION")
    print("=" * 78)
    print(f"SEARCH CONTRACT VERIFIED: {search_contract_verified}")
    print(f"OPERATIONAL CLOSURE ALLOWED: {operational_closure_allowed}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Operational closure == legal absence: False")
    print("Query no-hit == legal absence: False")
    print("Negative evidence allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S226M input exists": m_exists,
        "S226N input exists": n_exists,
        "historical coverage remains qualified": out["historical_coverage_qualified"] is True,
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_SOURCE_FAMILY_OPERATIONALLY_CLOSED_NO_UQQ700_PRECURSOR",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_SEARCH_CONTRACT_VERIFIED_RECONCILIATION_INCOMPLETE",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_SEARCH_FILTER_CONTRACT_TECHNICAL_UNKNOWN",
        },
        "operational closure not legal absence": out["summary"]["operational_closure_equals_legal_absence"] is False,
        "query no-hit not legal absence": out["summary"]["query_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
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
        raise AssertionError("S226O validation failed")


if __name__ == "__main__":
    main()
