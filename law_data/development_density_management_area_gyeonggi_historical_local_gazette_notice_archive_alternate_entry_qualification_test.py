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
OUT = OUT_DIR / "development_density_management_area_gyeonggi_historical_local_gazette_notice_archive_alternate_entry_qualification.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_OR_NOTICE_ARCHIVE_ALTERNATE_ENTRY"

# Qualification only. No UQQ700 query is issued in S230E.
ENTRIES = [
    {
        "source_id": "GG_GAZETTE_BOARD",
        "url": "https://www.gg.go.kr/bbs/board.do?bsIdx=769&menuId=1786",
        "expected_host": "www.gg.go.kr",
        "expected_role": "GYEONGGI_OFFICIAL_GAZETTE_BOARD",
    },
    {
        "source_id": "GG_EBOOK_GAZETTE_ARCHIVE",
        "url": "https://ebook.gg.go.kr/home/list.php?code=21",
        "expected_host": "ebook.gg.go.kr",
        "expected_role": "GYEONGGI_HISTORICAL_GAZETTE_EBOOK_ARCHIVE",
    },
]

CLOSED_BACKEND_HOSTS = {
    "local.gosi.go.kr",
    "www.seongnam.go.kr",
    "seongnam.go.kr",
}

OFFICIAL_SIGNALS = ["경기도", "경기도청", "GYEONGGI", "경기도보", "도보"]
ARCHIVE_SIGNALS = ["경기도보", "도보", "전자책", "등록된 자료", "페이지", "일제강점기", "게시판 검색"]
HISTORICAL_SIGNALS = ["1944", "1943", "1942", "1941", "일제강점기", "검색기간", "등록일"]
SEARCH_SIGNALS = ["검색", "search", "keyword", "sch", "query", "검색어"]
DETAIL_ATTACHMENT_SIGNALS = ["view", "detail", "boardView", "download", "file", "첨부", "바로보기", "책자", "페이지"]


def curl_text(url: str, max_time: int = 60) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "body": "", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", str(max_time),
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body_b, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 2)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
        content_type = parts[2] if len(parts) > 2 else None
    else:
        body_b, http, final_url, content_type = raw, None, None, None
    body = body_b.decode("utf-8", errors="replace")
    if body.count("�") > max(20, len(body) // 1000):
        try:
            body = body_b.decode("euc-kr", errors="replace")
        except Exception:
            pass
    return {
        "http": http,
        "final_url": final_url,
        "content_type": content_type,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def strip_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s)
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?is)<!--.*?-->", " ", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", unescape(s)).strip()


def extract_links(html: str, base_url: str) -> list[dict]:
    rows = []
    for m in re.finditer(r'''(?is)<a\b[^>]*?href\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>''', html):
        href = unescape(m.group(1).strip())
        label = strip_html(m.group(2))[:300]
        if not href or href.lower().startswith(("javascript:", "mailto:", "#")):
            continue
        rows.append({"url": urljoin(base_url, href), "label": label})
    return rows


def extract_forms(html: str, base_url: str) -> list[dict]:
    forms = []
    for fm in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html):
        attrs, inner = fm.group(1), fm.group(2)
        method_m = re.search(r'''(?is)method\s*=\s*["']?([^\s"'>]+)''', attrs)
        action_m = re.search(r'''(?is)action\s*=\s*["']([^"']*)["']''', attrs)
        method = (method_m.group(1) if method_m else "GET").upper()
        action = urljoin(base_url, action_m.group(1) if action_m else base_url)
        fields = []
        for im in re.finditer(r'''(?is)<(?:input|select|textarea)\b([^>]*)>''', inner):
            name_m = re.search(r'''(?is)name\s*=\s*["']([^"']+)["']''', im.group(1))
            if name_m:
                fields.append(name_m.group(1))
        forms.append({"method": method, "action": action, "fields": sorted(set(fields))})
    return forms


def classify_route(url: str, label: str) -> list[str]:
    low = (url + " " + label).lower()
    roles = []
    if any(x in low for x in ["search", "sch", "list", "board.do", "검색"]):
        roles.append("SEARCH_OR_LIST")
    if any(x in low for x in ["view", "detail", "boardview", "book", "viewer", "contents"]):
        roles.append("DETAIL_OR_VIEWER")
    if any(x in low for x in ["download", "file", ".pdf", ".hwp", ".hwpx"]):
        roles.append("ATTACHMENT_OR_BINARY")
    return roles


def qualify_entry(entry: dict) -> dict:
    rr = curl_text(entry["url"])
    body = rr["body"]
    plain = strip_html(body)
    final_url = rr["final_url"] or entry["url"]
    host = (urlparse(final_url).hostname or "").lower()
    links = extract_links(body, final_url)
    forms = extract_forms(body, final_url)

    official_hits = sorted({s for s in OFFICIAL_SIGNALS if s.lower() in plain.lower()})
    archive_hits = sorted({s for s in ARCHIVE_SIGNALS if s.lower() in plain.lower()})
    historical_hits = sorted({s for s in HISTORICAL_SIGNALS if s.lower() in plain.lower()})
    search_hits = sorted({s for s in SEARCH_SIGNALS if s.lower() in (body + " " + plain).lower()})
    detail_hits = sorted({s for s in DETAIL_ATTACHMENT_SIGNALS if s.lower() in (body + " " + plain).lower()})

    route_candidates = []
    for link in links:
        roles = classify_route(link["url"], link["label"])
        if roles:
            route_candidates.append({**link, "roles": roles})

    unique_routes = []
    seen = set()
    for r in route_candidates:
        key = (r["url"], tuple(r["roles"]))
        if key not in seen:
            seen.add(key)
            unique_routes.append(r)

    backend_distinct_from_closed = host not in CLOSED_BACKEND_HOSTS
    host_expected = host == entry["expected_host"]
    http_ok = rr["http"] == "200"
    official = len(official_hits) >= 1 and host_expected
    archive_role = len(archive_hits) >= 1
    historical_navigation = len(historical_hits) >= 1 or any(
        re.search(r"(?:19|20)\d{2}", (x.get("label") or "")) for x in links
    )
    search_surface = bool(forms) or len(search_hits) >= 1 or any("SEARCH_OR_LIST" in x["roles"] for x in unique_routes)
    detail_or_attachment_surface = len(detail_hits) >= 1 or any(
        set(x["roles"]) & {"DETAIL_OR_VIEWER", "ATTACHMENT_OR_BINARY"} for x in unique_routes
    )

    score = sum([
        3 if http_ok else 0,
        4 if official else 0,
        4 if archive_role else 0,
        3 if historical_navigation else 0,
        2 if search_surface else 0,
        2 if detail_or_attachment_surface else 0,
        3 if backend_distinct_from_closed else 0,
    ])
    qualified = (
        http_ok
        and official
        and archive_role
        and backend_distinct_from_closed
        and (historical_navigation or entry["source_id"] == "GG_GAZETTE_BOARD")
        and search_surface
    )

    return {
        "source_id": entry["source_id"],
        "expected_role": entry["expected_role"],
        "input_url": entry["url"],
        "http": rr["http"],
        "final_url": final_url,
        "host": host,
        "content_type": rr["content_type"],
        "body_size": len(body.encode("utf-8", errors="replace")),
        "official_signal_hits": official_hits,
        "archive_signal_hits": archive_hits,
        "historical_signal_hits": historical_hits,
        "search_signal_hits": search_hits,
        "detail_attachment_signal_hits": detail_hits,
        "form_count": len(forms),
        "forms": forms[:20],
        "route_candidate_count": len(unique_routes),
        "route_candidates": unique_routes[:50],
        "http_ok": http_ok,
        "host_expected": host_expected,
        "official_source": official,
        "archive_role_verified": archive_role,
        "historical_navigation_verified": historical_navigation,
        "search_surface_observed": search_surface,
        "detail_or_attachment_surface_observed": detail_or_attachment_surface,
        "backend_distinct_from_closed_sources": backend_distinct_from_closed,
        "qualification_score": score,
        "entry_qualified": qualified,
        "target_uqq700_search_executed": False,
        "designation_identity_promoted": False,
        "current_validity_promoted": False,
        "site_inclusion_promoted": False,
        "legal_absence_inferred": False,
        "stderr": rr["stderr"],
    }


def main() -> None:
    print("=" * 78)
    print("GYEONGGI HISTORICAL LOCAL GAZETTE / NOTICE ARCHIVE ALTERNATE ENTRY QUALIFICATION - S230E")
    print("=" * 78)
    print("Purpose: qualify alternate official historical gazette/archive entries before target search")
    print("UQQ700 target search: DISABLED")
    print("Archive entry found != designation identity/current validity/site inclusion")
    print("Archive entry failure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    results = []
    for entry in ENTRIES:
        row = qualify_entry(entry)
        results.append(row)
        print(json.dumps({
            "source_id": row["source_id"],
            "http": row["http"],
            "final_url": row["final_url"],
            "host": row["host"],
            "score": row["qualification_score"],
            "official": row["official_source"],
            "archive_role": row["archive_role_verified"],
            "historical_navigation": row["historical_navigation_verified"],
            "search_surface": row["search_surface_observed"],
            "detail_or_attachment_surface": row["detail_or_attachment_surface_observed"],
            "distinct_backend": row["backend_distinct_from_closed_sources"],
            "entry_qualified": row["entry_qualified"],
        }, ensure_ascii=False))

    qualified = [r for r in results if r["entry_qualified"]]
    historical_qualified = [r for r in qualified if r["historical_navigation_verified"]]
    distinct_host_count = len({r["host"] for r in qualified})

    if historical_qualified:
        classification = "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_NOTICE_ARCHIVE_ALTERNATE_ENTRY_QUALIFIED"
        semantic = "ONE_OR_MORE_DISTINCT_OFFICIAL_GYEONGGI_GAZETTE_ARCHIVE_ENTRIES_EXPOSE_HISTORICAL_NAVIGATION_AND_SEARCH_SURFACES_WITHOUT_TARGET_SEARCH"
        next_action = "QUALIFY_SEARCH_OR_YEAR_NAVIGATION_CONTRACT_ON_THE_HIGHEST_VALUE_HISTORICAL_ENTRY_BEFORE_ANY_UQQ700_QUERY"
    elif qualified:
        classification = "GYEONGGI_GAZETTE_ALTERNATE_ENTRY_QUALIFIED_HISTORICAL_NAVIGATION_REQUIRES_REVIEW"
        semantic = "OFFICIAL_DISTINCT_GAZETTE_ENTRY_EXISTS_BUT_HISTORICAL_NAVIGATION_WAS_NOT_STRONGLY_VERIFIED"
        next_action = "RECOVER_HISTORICAL_NAVIGATION_CONTRACT_WITHOUT_TARGET_SEARCH"
    else:
        classification = "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_NOTICE_ARCHIVE_ALTERNATE_ENTRY_NOT_QUALIFIED"
        semantic = "NO_DISTINCT_OFFICIAL_HISTORICAL_GAZETTE_ARCHIVE_ENTRY_SURVIVED_ENTRY_QUALIFICATION"
        next_action = "RETURN_TO_SOURCE_FAMILY_RERANKING_WITHOUT_NEGATIVE_LEGAL_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-169-S230E",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "entry_count": len(results),
        "qualified_entry_count": len(qualified),
        "historical_qualified_entry_count": len(historical_qualified),
        "qualified_distinct_host_count": distinct_host_count,
        "results": results,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "target_uqq700_search_executed": False,
            "closed_source_contract_reused_for_target_search": False,
            "archive_entry_found_equals_designation_identity": False,
            "archive_entry_found_equals_current_validity": False,
            "archive_entry_found_equals_site_inclusion": False,
            "archive_entry_failure_equals_legal_absence": False,
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
    print("RESOLUTION")
    print("=" * 78)
    print(f"ENTRY COUNT: {len(results)}")
    print(f"QUALIFIED ENTRY COUNT: {len(qualified)}")
    print(f"HISTORICAL QUALIFIED ENTRY COUNT: {len(historical_qualified)}")
    print(f"QUALIFIED DISTINCT HOST COUNT: {distinct_host_count}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("UQQ700 target search executed: False")
    print("Archive entry failure == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "two candidate entries tested": len(results) == 2,
        "no UQQ700 target search": out["summary"]["target_uqq700_search_executed"] is False,
        "closed source contract not reused for target search": out["summary"]["closed_source_contract_reused_for_target_search"] is False,
        "qualified entries use distinct backend": all(r["backend_distinct_from_closed_sources"] for r in qualified),
        "entry found not designation": out["summary"]["archive_entry_found_equals_designation_identity"] is False,
        "entry found not validity": out["summary"]["archive_entry_found_equals_current_validity"] is False,
        "entry found not site inclusion": out["summary"]["archive_entry_found_equals_site_inclusion"] is False,
        "entry failure not legal absence": out["summary"]["archive_entry_failure_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_NOTICE_ARCHIVE_ALTERNATE_ENTRY_QUALIFIED",
            "GYEONGGI_GAZETTE_ALTERNATE_ENTRY_QUALIFIED_HISTORICAL_NAVIGATION_REQUIRES_REVIEW",
            "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_NOTICE_ARCHIVE_ALTERNATE_ENTRY_NOT_QUALIFIED",
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
        raise AssertionError("S230E validation failed")


if __name__ == "__main__":
    main()
