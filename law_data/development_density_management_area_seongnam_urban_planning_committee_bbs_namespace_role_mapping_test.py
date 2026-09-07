# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
S226E_OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_script_menu_route_discovery.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_bbs_namespace_role_mapping.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
OFFICIAL_HOST = "www.seongnam.go.kr"
MAX_BOARDS = 24

HIGH_SIGNAL_TERMS = ("도시계획위원회", "도시계획 위원회")
LOW_SIGNAL_TERMS = ("위원회", "도시계획")
EXCLUDE_TERMS = ("신청", "접수", "예방접종", "복지", "강좌", "시설", "대관")


def curl_bytes(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"ok": False, "http": None, "final_url": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS",
        "--connect-timeout", "15", "--max-time", "45",
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


def extract_first(html: str, tag: str) -> str | None:
    m = re.search(fr"(?is)<{tag}\b[^>]*>(.*?)</{tag}>", html or "")
    return clean_html(m.group(1))[:500] if m else None


def extract_title(html: str) -> str | None:
    return extract_first(html, "title")


def extract_breadcrumb_like(html: str) -> list[str]:
    rows = []
    for pat in (
        r'(?is)<[^>]+class=["\'][^"\']*(?:breadcrumb|location|path)[^"\']*["\'][^>]*>(.*?)</[^>]+>',
        r'(?is)<nav\b[^>]*>(.*?)</nav>',
    ):
        for m in re.finditer(pat, html or ""):
            text = clean_html(m.group(1))
            if text:
                rows.append(text[:1000])
    return rows[:10]


def extract_department_like(text: str) -> list[str]:
    hits = []
    patterns = [
        r"담당부서\s*[:：]?\s*([^|·\n]{2,80})",
        r"부서명\s*[:：]?\s*([^|·\n]{2,80})",
        r"담당자\s*[:：]?\s*([^|·\n]{2,80})",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            val = " ".join(m.group(1).split())
            if val and val not in hits:
                hits.append(val)
    return hits[:10]


def canonical_bbs(url: str) -> str | None:
    p = urlparse(url)
    if p.hostname != OFFICIAL_HOST:
        return None
    m = re.match(r"^/(bbs\d+)(?:/\d+)?/?$", p.path)
    if not m:
        return None
    return f"https://{OFFICIAL_HOST}/{m.group(1)}"


def load_candidates() -> list[str]:
    if not S226E_OUT.exists():
        return []
    data = json.loads(S226E_OUT.read_text(encoding="utf-8"))
    raw = []
    raw.extend(data.get("committee_signal_candidates") or [])
    raw.extend(data.get("real_route_candidates") or [])
    root = data.get("root") or {}
    for row in root.get("menu_links") or []:
        if row.get("href_absolute"):
            raw.append(row["href_absolute"])
    out = []
    seen = set()
    for u in raw:
        c = canonical_bbs(str(u))
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out[:MAX_BOARDS]


def inspect_board(url: str) -> dict:
    f = curl_bytes(url)
    html, enc = decode_body(f.pop("body"))
    text = clean_html(html)
    title = extract_title(html)
    h1 = extract_first(html, "h1")
    h2 = extract_first(html, "h2")
    breadcrumbs = extract_breadcrumb_like(html)
    dept = extract_department_like(text)
    evidence_blob = " | ".join(x for x in [title, h1, h2, *breadcrumbs, *dept, text[:4000]] if x)
    high = [t for t in HIGH_SIGNAL_TERMS if t in evidence_blob]
    low = [t for t in LOW_SIGNAL_TERMS if t in evidence_blob]
    excludes = [t for t in EXCLUDE_TERMS if t in evidence_blob]
    return {
        "url": url,
        **f,
        "selected_charset": enc,
        "same_official_host": bool(f.get("final_url") and urlparse(f["final_url"]).hostname == OFFICIAL_HOST),
        "title": title,
        "h1": h1,
        "h2": h2,
        "breadcrumbs": breadcrumbs,
        "department_like": dept,
        "high_signal_terms": high,
        "low_signal_terms": low,
        "exclude_terms": excludes,
        "body_prefix": text[:2500],
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE BBS NAMESPACE ROLE MAPPING - S226F")
    print("=" * 78)
    print("Purpose: map current /bbs namespace roles without submitting any search")
    print("Search request: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Generic '위원회' signal is NOT sufficient")
    print("Committee board discovery != designation notice")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    candidates = load_candidates()
    inspected = [inspect_board(u) for u in candidates]

    high_signal = [r for r in inspected if r.get("ok") and r.get("high_signal_terms")]
    low_only = [r for r in inspected if r.get("ok") and not r.get("high_signal_terms") and r.get("low_signal_terms")]
    excluded = [r for r in inspected if r.get("exclude_terms") and not r.get("high_signal_terms")]

    if high_signal:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_BBS_NAMESPACE_IDENTIFIED"
        semantic = "SEONGNAM_URBAN_PLANNING_COMMITTEE_CURRENT_BBS_NAMESPACE_IDENTIFIED_WITH_DIRECT_BOARD_ROLE_SIGNAL"
        next_action = "QUALIFY_IDENTIFIED_COMMITTEE_BOARD_WITH_POSITIVE_CONTROL_AND_HISTORICAL_COVERAGE_BEFORE_UQQ700_QUERY"
    elif inspected and any(r.get("ok") for r in inspected):
        classification = "SEONGNAM_BBS_NAMESPACE_MAPPED_COMMITTEE_BOARD_UNRESOLVED"
        semantic = "SEONGNAM_CURRENT_BBS_NAMESPACE_ROLE_MAPPING_COMPLETED_BUT_COMMITTEE_BOARD_REMAINS_UNRESOLVED"
        next_action = "EXPAND_BBS_NAMESPACE_DISCOVERY_FROM_MENU_LABELS_OR_SITE_SEARCH_INDEX_WITHOUT_UQQ700_QUERY"
    else:
        classification = "SEONGNAM_BBS_NAMESPACE_MAPPING_TECHNICAL_UNKNOWN"
        semantic = "SEONGNAM_BBS_NAMESPACE_ROLE_MAPPING_NOT_TECHNICALLY_QUALIFIED"
        next_action = "RECHECK_BBS_NAMESPACE_TRANSPORT_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226F",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s226e_input_exists": S226E_OUT.exists(),
        "canonical_candidate_count": len(candidates),
        "canonical_candidates": candidates,
        "inspected_count": len(inspected),
        "inspected": inspected,
        "direct_high_signal_count": len(high_signal),
        "direct_high_signal_boards": [r["url"] for r in high_signal],
        "low_signal_only_count": len(low_only),
        "excluded_non_committee_context_count": len(excluded),
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "search_request_executed": False,
            "target_query_executed": False,
            "generic_committee_term_sufficient": False,
            "committee_board_discovery_equals_designation_notice": False,
            "namespace_no_hit_equals_legal_absence": False,
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

    print(f"S226E INPUT EXISTS: {S226E_OUT.exists()}")
    print(f"CANONICAL BBS CANDIDATE COUNT: {len(candidates)}")
    print(f"INSPECTED COUNT: {len(inspected)}")
    for i, r in enumerate(inspected, 1):
        print("-" * 78)
        print(f"[{i:02d}] {r['url']}")
        print(f"HTTP: {r.get('http')}")
        print(f"FINAL URL: {r.get('final_url')}")
        print(f"TITLE: {r.get('title')}")
        print(f"H1: {r.get('h1')}")
        print(f"H2: {r.get('h2')}")
        print(f"BREADCRUMBS: {r.get('breadcrumbs')}")
        print(f"DEPARTMENT LIKE: {r.get('department_like')}")
        print(f"HIGH SIGNAL: {r.get('high_signal_terms')}")
        print(f"LOW SIGNAL: {r.get('low_signal_terms')}")
        print(f"EXCLUDE TERMS: {r.get('exclude_terms')}")

    print("\n" + "=" * 78)
    print("ROLE MAPPING SUMMARY")
    print("=" * 78)
    print(f"DIRECT HIGH-SIGNAL BOARD COUNT: {len(high_signal)}")
    for i, r in enumerate(high_signal, 1):
        print(f"HIGH SIGNAL [{i:02d}] {r['url']} | {r.get('title')} | {r.get('high_signal_terms')}")
    print(f"LOW-SIGNAL-ONLY COUNT: {len(low_only)}")
    print(f"EXCLUDED NON-COMMITTEE CONTEXT COUNT: {len(excluded)}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Search request executed: False")
    print("Target query executed: False")
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S226E input exists": out["s226e_input_exists"] is True,
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_BBS_NAMESPACE_IDENTIFIED",
            "SEONGNAM_BBS_NAMESPACE_MAPPED_COMMITTEE_BOARD_UNRESOLVED",
            "SEONGNAM_BBS_NAMESPACE_MAPPING_TECHNICAL_UNKNOWN",
        },
        "search request not executed": out["summary"]["search_request_executed"] is False,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "generic committee term insufficient": out["summary"]["generic_committee_term_sufficient"] is False,
        "committee discovery not designation notice": out["summary"]["committee_board_discovery_equals_designation_notice"] is False,
        "namespace no-hit not legal absence": out["summary"]["namespace_no_hit_equals_legal_absence"] is False,
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
        raise AssertionError("S226F validation failed")


if __name__ == "__main__":
    main()
