# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from html import unescape
from pathlib import Path
from urllib.parse import urlencode

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
PRIOR_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_attachment_ajax_schema_binary_replay.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_archive_coverage_canonical_enumeration.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
LIST_URL = "https://www.seongnam.go.kr/ct-bbs020101"
ATCH_URL = "https://www.seongnam.go.kr/ct-bbs020101/atchFileDetail"
BBS_CRT_SN = "19008"
MAX_PAGES_SAFETY = 100

MOVE_RE = re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
DETAIL_HREF_RE = re.compile(r'''(?is)<a\b[^>]*href\s*=\s*(["'])/ct-bbs020101/(\d+)\1[^>]*>(.*?)</a>''')
TOTAL_PAGE_PATTERNS = [
    re.compile(r"(?i)var\s+totalPage\s*=\s*(\d+)"),
    re.compile(r"(?i)totalPage\s*[=:]\s*['\"]?(\d+)"),
]
CURPAGE_RE = re.compile(r"(?i)[?&]curPage=(\d+)")


def curl_request(url: str, *, referer: str | None = None) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "60",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}",
    ]
    if referer:
        cmd += ["-e", referer]
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 2)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
        content_type = parts[2] if len(parts) > 2 else None
    else:
        body, http, final_url, content_type = raw, None, None, None
    return {
        "http": http,
        "final_url": final_url,
        "content_type": content_type,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def decode_text(body: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            t = body.decode(enc)
            if enc == "utf-8" or "성남" in t:
                return t
        except UnicodeDecodeError:
            pass
    return body.decode("utf-8", errors="replace")


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def detect_total_pages(html: str) -> int | None:
    for pat in TOTAL_PAGE_PATTERNS:
        m = pat.search(html or "")
        if m:
            n = int(m.group(1))
            if 1 <= n <= MAX_PAGES_SAFETY:
                return n
    pages = [int(x) for x in CURPAGE_RE.findall(html or "") if int(x) <= MAX_PAGES_SAFETY]
    return max(pages) if pages else None


def extract_posts(html: str, page_no: int) -> list[dict]:
    posts: dict[str, dict] = {}
    for m in DETAIL_HREF_RE.finditer(html or ""):
        pst_sn = m.group(2)
        title = clean_html(m.group(3))
        if pst_sn not in posts:
            posts[pst_sn] = {
                "pstSn": pst_sn,
                "title": title,
                "detail_url": f"{LIST_URL}/{pst_sn}",
                "first_seen_page": page_no,
            }
    for m in MOVE_RE.finditer(html or ""):
        pst_sn = m.group(1)
        posts.setdefault(pst_sn, {
            "pstSn": pst_sn,
            "title": None,
            "detail_url": f"{LIST_URL}/{pst_sn}",
            "first_seen_page": page_no,
        })
    return list(posts.values())


def parse_json(resp: dict) -> tuple[object | None, str | None]:
    text = decode_text(resp.get("body") or b"")
    try:
        return json.loads(text), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def extract_items(data: object) -> list[dict]:
    if isinstance(data, dict) and isinstance(data.get("atchFileVO"), list):
        return [x for x in data["atchFileVO"] if isinstance(x, dict)]
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def file_ext(item: dict) -> str:
    ext = str(item.get("fileExtsn") or "").strip().lower().lstrip(".")
    if ext:
        return ext
    name = str(item.get("orginlFileNm") or item.get("originalFileNm") or "")
    if "." in name:
        return name.rsplit(".", 1)[-1].strip().lower()
    return ""


def canonical_attachment(pst_sn: str, item: dict) -> dict:
    file_no = item.get("fileNo")
    return {
        "bbsCrtSn": BBS_CRT_SN,
        "pstSn": pst_sn,
        "fileNo": str(file_no) if file_no is not None else None,
        "orginlFileNm": item.get("orginlFileNm"),
        "fileExtsn": file_ext(item),
        "fileSize": item.get("fileSize"),
        "download_url": (
            f"{LIST_URL}/getFile?" + urlencode({"bbsCrtSn": BBS_CRT_SN, "pstSn": pst_sn, "fileNo": file_no})
            if file_no not in (None, "") else None
        ),
        "raw": item,
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT ARCHIVE COVERAGE + CANONICAL ENUMERATION - S227B")
    print("=" * 78)
    print("Purpose: qualify current public archive pagination and enumerate canonical posts/attachments")
    print("UQQ700 target query: NOT EXECUTED")
    print("Planning document presence != designation notice")
    print("Planning document no-hit != legal absence")
    print("SITE FALSE inference: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    prior_exists = PRIOR_OUT.exists()
    prior = json.loads(PRIOR_OUT.read_text(encoding="utf-8")) if prior_exists else {}
    prior_binary_verified = bool(prior.get("binary_attachment_verified"))

    first = curl_request(LIST_URL)
    first_html = decode_text(first.get("body") or b"")
    total_pages = detect_total_pages(first_html) or 1

    page_rows = []
    raw_posts = []
    fingerprints = set()
    all_pages_http_200 = True

    for page_no in range(1, total_pages + 1):
        url = LIST_URL if page_no == 1 else f"{LIST_URL}?curPage={page_no}"
        r = first if page_no == 1 else curl_request(url, referer=LIST_URL)
        html = first_html if page_no == 1 else decode_text(r.get("body") or b"")
        posts = extract_posts(html, page_no)
        ids = [p["pstSn"] for p in posts]
        fingerprint = "|".join(ids)
        fingerprints.add(fingerprint)
        all_pages_http_200 = all_pages_http_200 and r.get("http") == "200"
        raw_posts.extend(posts)
        page_rows.append({
            "page": page_no,
            "url": url,
            "http": r.get("http"),
            "post_count": len(posts),
            "pstSns": ids,
            "fingerprint": fingerprint,
        })

    canonical_posts_map: dict[str, dict] = {}
    for p in raw_posts:
        existing = canonical_posts_map.get(p["pstSn"])
        if existing is None:
            canonical_posts_map[p["pstSn"]] = p
        elif not existing.get("title") and p.get("title"):
            existing["title"] = p["title"]
    canonical_posts = list(canonical_posts_map.values())

    attachment_rows = []
    ajax_http_ok_count = 0
    ajax_json_ok_count = 0
    attachment_bearing_posts = 0

    for i, post in enumerate(canonical_posts, 1):
        pst_sn = post["pstSn"]
        url = ATCH_URL + "?" + urlencode({"pstSn": pst_sn})
        r = curl_request(url, referer=post["detail_url"])
        data, err = parse_json(r)
        items = extract_items(data) if data is not None else []
        if r.get("http") == "200":
            ajax_http_ok_count += 1
        if data is not None:
            ajax_json_ok_count += 1
        canonical_items = [canonical_attachment(pst_sn, item) for item in items]
        if canonical_items:
            attachment_bearing_posts += 1
        post["attachment_count"] = len(canonical_items)
        post["attachment_ajax_http"] = r.get("http")
        post["attachment_ajax_json_ok"] = data is not None
        post["attachment_ajax_error"] = err
        attachment_rows.extend(canonical_items)
        if i % 10 == 0 or i == len(canonical_posts):
            print(f"ATTACHMENT ENUMERATION PROGRESS: {i}/{len(canonical_posts)}")

    canonical_attachment_map: dict[tuple[str, str], dict] = {}
    missing_file_no = 0
    for a in attachment_rows:
        if not a.get("fileNo"):
            missing_file_no += 1
            continue
        canonical_attachment_map[(a["pstSn"], a["fileNo"])] = a
    canonical_attachments = list(canonical_attachment_map.values())
    ext_counts = Counter((a.get("fileExtsn") or "") for a in canonical_attachments)

    pagination_qualified = (
        first.get("http") == "200"
        and total_pages >= 1
        and all_pages_http_200
        and len(page_rows) == total_pages
        and len(fingerprints) == total_pages
        and len(canonical_posts) > 0
    )
    attachment_inventory_qualified = (
        prior_binary_verified
        and len(canonical_posts) > 0
        and ajax_http_ok_count == len(canonical_posts)
        and ajax_json_ok_count == len(canonical_posts)
        and missing_file_no == 0
    )
    canonical_inventory_qualified = pagination_qualified and attachment_inventory_qualified

    if canonical_inventory_qualified:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_COVERAGE_AND_CANONICAL_INVENTORY_QUALIFIED"
        semantic = "CURRENT_PUBLIC_PLANNING_ARCHIVE_PAGINATION_AND_CANONICAL_POST_ATTACHMENT_INVENTORY_VERIFIED_WITHOUT_UQQ700_QUERY"
        next_action = "RUN_BOUNDED_UQQ700_METADATA_AND_CONTENT_DISCOVERY_OVER_THE_QUALIFIED_CANONICAL_INVENTORY_NON_NEGATIVELY"
    elif pagination_qualified:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_COVERAGE_QUALIFIED_ATTACHMENT_INVENTORY_TECHNICAL_UNKNOWN"
        semantic = "PUBLIC_ARCHIVE_PAGINATION_VERIFIED_BUT_COMPLETE_ATTACHMENT_METADATA_ENUMERATION_NOT_YET_QUALIFIED"
        next_action = "HARDEN_ONLY_FAILED_ATTACHMENT_METADATA_ROWS_WITHOUT_NEGATIVE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_COVERAGE_TECHNICAL_UNKNOWN"
        semantic = "PUBLIC_ARCHIVE_PAGINATION_OR_ROW_DISTINCTNESS_NOT_YET_QUALIFIED"
        next_action = "HARDEN_PAGINATION_AND_ROW_IDENTITY_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-148-S227B",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prior_input_exists": prior_exists,
        "prior_binary_attachment_verified": prior_binary_verified,
        "target_query_executed": False,
        "total_pages": total_pages,
        "page_rows": page_rows,
        "raw_post_count": len(raw_posts),
        "canonical_post_count": len(canonical_posts),
        "canonical_posts": canonical_posts,
        "attachment_ajax_http_ok_count": ajax_http_ok_count,
        "attachment_ajax_json_ok_count": ajax_json_ok_count,
        "attachment_bearing_post_count": attachment_bearing_posts,
        "raw_attachment_count": len(attachment_rows),
        "canonical_attachment_count": len(canonical_attachments),
        "missing_file_no_count": missing_file_no,
        "attachment_extension_counts": dict(sorted(ext_counts.items())),
        "canonical_attachments": canonical_attachments,
        "pagination_qualified": pagination_qualified,
        "attachment_inventory_qualified": attachment_inventory_qualified,
        "canonical_inventory_qualified": canonical_inventory_qualified,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "planning_document_hit_equals_designation_notice": False,
            "planning_document_hit_equals_current_validity": False,
            "planning_document_hit_equals_site_inclusion": False,
            "planning_document_no_hit_equals_legal_absence": False,
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

    print("\nARCHIVE COVERAGE")
    print("-" * 78)
    print(f"TOTAL PAGES: {total_pages}")
    print(f"RAW POST COUNT: {len(raw_posts)}")
    print(f"CANONICAL POST COUNT: {len(canonical_posts)}")
    print(f"DISTINCT PAGE FINGERPRINT COUNT: {len(fingerprints)}")
    print(f"ALL PAGES HTTP 200: {all_pages_http_200}")
    for p in page_rows:
        print(f"PAGE={p['page']} HTTP={p['http']} POSTS={p['post_count']} PSTSNS={p['pstSns'][:12]}")

    print("\nCANONICAL ATTACHMENT INVENTORY")
    print("-" * 78)
    print(f"ATTACHMENT AJAX HTTP OK COUNT: {ajax_http_ok_count}")
    print(f"ATTACHMENT AJAX JSON OK COUNT: {ajax_json_ok_count}")
    print(f"ATTACHMENT-BEARING POST COUNT: {attachment_bearing_posts}")
    print(f"RAW ATTACHMENT COUNT: {len(attachment_rows)}")
    print(f"CANONICAL ATTACHMENT COUNT: {len(canonical_attachments)}")
    print(f"MISSING FILENO COUNT: {missing_file_no}")
    print(f"EXTENSION COUNTS: {dict(sorted(ext_counts.items()))}")
    print(f"PDF COUNT: {ext_counts.get('pdf', 0)}")
    print(f"HWP COUNT: {ext_counts.get('hwp', 0)}")
    print(f"HWPX COUNT: {ext_counts.get('hwpx', 0)}")
    for a in canonical_attachments[:30]:
        print(f"PSTSN={a['pstSn']} FILENO={a['fileNo']} EXT={a['fileExtsn']} NAME={a['orginlFileNm']}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"PRIOR BINARY ATTACHMENT VERIFIED: {prior_binary_verified}")
    print(f"ARCHIVE COVERAGE QUALIFIED: {pagination_qualified}")
    print(f"ATTACHMENT INVENTORY QUALIFIED: {attachment_inventory_qualified}")
    print(f"CANONICAL DOCUMENT INVENTORY QUALIFIED: {canonical_inventory_qualified}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Target query executed: False")
    print("Planning document no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S227A-P4 input exists": prior_exists,
        "target query not executed": out["target_query_executed"] is False,
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_COVERAGE_AND_CANONICAL_INVENTORY_QUALIFIED",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_COVERAGE_QUALIFIED_ATTACHMENT_INVENTORY_TECHNICAL_UNKNOWN",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_COVERAGE_TECHNICAL_UNKNOWN",
        },
        "planning hit not designation notice": out["summary"]["planning_document_hit_equals_designation_notice"] is False,
        "planning hit not current validity": out["summary"]["planning_document_hit_equals_current_validity"] is False,
        "planning hit not site inclusion": out["summary"]["planning_document_hit_equals_site_inclusion"] is False,
        "planning no-hit not legal absence": out["summary"]["planning_document_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
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
        raise AssertionError("S227B validation failed")


if __name__ == "__main__":
    main()
