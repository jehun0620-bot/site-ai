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
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_archive_entry_contract_qualification.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
OFFICIAL_HOST = "www.seongnam.go.kr"
ROOT_URL = "https://www.seongnam.go.kr/"
SITEMAP_URL = "https://www.seongnam.go.kr/sitemap"
POSITIVE_CONTROL_PDF = "https://www.seongnam.go.kr/contents/down/10785_6.pdf"
MAX_DISCOVERED_FETCH = 30

PLANNING_TERMS = (
    "도시계획", "도시기본계획", "도시관리계획", "도시주거", "주거환경정비",
    "정비기본계획", "생활권계획", "도시·주택", "도시주택", "계획자료", "계획문서",
)
DOC_EXT_RE = re.compile(r"\.(?:pdf|hwp|hwpx|xls|xlsx|doc|docx)(?:$|[?#])", re.I)
HREF_RE = re.compile(r'''(?is)<a\b[^>]*href\s*=\s*(["'])(.*?)\1''')
TITLE_RE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")


def curl_request(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"ok": False, "http": None, "final_url": None, "content_type": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "60",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-D", "-",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    header_end = raw.rfind(b"\r\n\r\n")
    if header_end < 0:
        header_end = raw.rfind(b"\n\n")
        sep_len = 2
    else:
        sep_len = 4
    headers_blob = raw[:header_end] if header_end >= 0 else b""
    body = raw[header_end + sep_len:] if header_end >= 0 else raw
    header_text = headers_blob.decode("iso-8859-1", errors="replace")
    status_matches = re.findall(r"HTTP/\S+\s+(\d{3})", header_text)
    http = status_matches[-1] if status_matches else None
    ct_matches = re.findall(r"(?im)^Content-Type:\s*([^\r\n]+)", header_text)
    content_type = ct_matches[-1].strip() if ct_matches else None
    loc_matches = re.findall(r"(?im)^Location:\s*([^\r\n]+)", header_text)
    final_url = loc_matches[-1].strip() if loc_matches else url
    return {
        "ok": p.returncode == 0 and bool(http and http != "000"),
        "returncode": p.returncode,
        "http": http,
        "final_url": final_url,
        "content_type": content_type,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def decode_html(body: bytes) -> tuple[str, str]:
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


def page_title(html: str) -> str | None:
    m = TITLE_RE.search(html or "")
    return clean_html(m.group(1)) if m else None


def same_official_host(url: str) -> bool:
    try:
        return (urlparse(url).hostname or "").lower() == OFFICIAL_HOST
    except Exception:
        return False


def extract_links(html: str, base_url: str) -> list[dict]:
    results = []
    seen = set()
    for m in HREF_RE.finditer(html or ""):
        href = unescape(m.group(2)).strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        url = urljoin(base_url, href)
        if not same_official_host(url) or url in seen:
            continue
        seen.add(url)
        window = html[max(0, m.start() - 250): min(len(html), m.end() + 500)]
        label = clean_html(window)[:600]
        term_hits = [t for t in PLANNING_TERMS if t in label or t in url]
        is_doc = bool(DOC_EXT_RE.search(url)) or "/contents/down/" in url or "/getFile" in url
        if term_hits or is_doc:
            results.append({"url": url, "term_hits": term_hits, "is_document_like": is_doc, "context": label})
    return results


def classify_content(resp: dict) -> dict:
    body = resp.get("body") or b""
    ct = (resp.get("content_type") or "").lower()
    magic = body[:8]
    return {
        "pdf_magic": body.startswith(b"%PDF-"),
        "ole_magic": body.startswith(bytes.fromhex("D0CF11E0A1B11AE1")),
        "zip_magic": body.startswith(b"PK\x03\x04"),
        "pdf_content_type": "pdf" in ct,
        "html_content_type": "html" in ct,
        "body_size": len(body),
        "magic_hex": magic.hex(),
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT ARCHIVE ENTRY CONTRACT QUALIFICATION - S227A")
    print("=" * 78)
    print("Purpose: qualify official planning-document entry/list/detail/attachment surfaces only")
    print("UQQ700 target query: NOT EXECUTED")
    print("Document hit != designation notice")
    print("Document no-hit != legal absence")
    print("Negative evidence: DISABLED")
    print("SITE FALSE inference: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    surfaces = []
    discovered = []
    for label, url in (("ROOT", ROOT_URL), ("SITEMAP", SITEMAP_URL)):
        r = curl_request(url)
        html, enc = decode_html(r.get("body") or b"")
        links = extract_links(html, url) if r.get("http") == "200" else []
        surfaces.append({
            "label": label,
            "url": url,
            "http": r.get("http"),
            "content_type": r.get("content_type"),
            "charset": enc,
            "title": page_title(html),
            "planning_signals": [t for t in PLANNING_TERMS if t in clean_html(html)],
            "candidate_link_count": len(links),
        })
        discovered.extend(links)

    dedup = {}
    for row in discovered:
        dedup.setdefault(row["url"], row)
    discovered = list(dedup.values())
    discovered.sort(key=lambda x: (not x["is_document_like"], -len(x["term_hits"]), x["url"]))

    positive = curl_request(POSITIVE_CONTROL_PDF)
    positive_cls = classify_content(positive)
    positive_ok = positive.get("http") == "200" and (positive_cls["pdf_magic"] or positive_cls["pdf_content_type"])

    sampled = []
    for row in discovered[:MAX_DISCOVERED_FETCH]:
        r = curl_request(row["url"])
        cls = classify_content(r)
        title = None
        planning_signals = []
        if cls["html_content_type"] or (r.get("body") or b"").lstrip().startswith(b"<"):
            html, _ = decode_html(r.get("body") or b"")
            title = page_title(html)
            text = clean_html(html)
            planning_signals = [t for t in PLANNING_TERMS if t in text]
        sampled.append({
            "url": row["url"],
            "source_term_hits": row["term_hits"],
            "is_document_like": row["is_document_like"],
            "http": r.get("http"),
            "content_type": r.get("content_type"),
            "title": title,
            "planning_signals": planning_signals,
            "content_class": cls,
        })

    archive_candidate_count = sum(1 for x in sampled if x.get("http") == "200" and (x["planning_signals"] or x["is_document_like"]))
    document_candidate_count = sum(1 for x in sampled if x.get("http") == "200" and (
        x["content_class"]["pdf_magic"] or x["content_class"]["ole_magic"] or x["content_class"]["zip_magic"] or x["is_document_like"]
    ))
    official_surface_ok = any(s["http"] == "200" for s in surfaces)

    if official_surface_ok and positive_ok:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_ENTRY_ATTACHMENT_CONTRACT_QUALIFIED"
        semantic = "OFFICIAL_SEONGNAM_SURFACE_AND_PLANNING_DOCUMENT_PDF_ATTACHMENT_POSITIVE_CONTROL_VERIFIED_WITHOUT_UQQ700_QUERY"
        next_action = "DISCOVER_AND_BOUND_PLANNING_DOCUMENT_ARCHIVE_COVERAGE_BEFORE_UQQ700_CONTENT_QUERY"
        entry_contract_qualified = True
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_ENTRY_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "OFFICIAL_ENTRY_OR_DOCUMENT_ATTACHMENT_POSITIVE_CONTROL_NOT_YET_FULLY_VERIFIED"
        next_action = "HARDEN_OFFICIAL_PLANNING_DOCUMENT_ENTRY_OR_ATTACHMENT_ROUTE_WITHOUT_NEGATIVE_INFERENCE"
        entry_contract_qualified = False

    out = {
        "step": "STEP 17-21-C-16-8-T-142-S227A",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "target_query_executed": False,
        "official_host": OFFICIAL_HOST,
        "surfaces": surfaces,
        "positive_control": {
            "url": POSITIVE_CONTROL_PDF,
            "http": positive.get("http"),
            "content_type": positive.get("content_type"),
            "content_class": positive_cls,
            "qualified": positive_ok,
        },
        "discovered_candidate_count": len(discovered),
        "discovered_candidates": discovered[:100],
        "sampled_candidate_count": len(sampled),
        "sampled_candidates": sampled,
        "archive_candidate_count": archive_candidate_count,
        "document_candidate_count": document_candidate_count,
        "entry_contract_qualified": entry_contract_qualified,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "document_hit_equals_designation_notice": False,
            "document_hit_equals_current_validity": False,
            "document_hit_equals_site_inclusion": False,
            "document_no_hit_equals_legal_absence": False,
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

    print("\nOFFICIAL ENTRY SURFACES")
    print("-" * 78)
    for s in surfaces:
        print(f"{s['label']} | HTTP={s['http']} | TITLE={s['title']} | CANDIDATE_LINKS={s['candidate_link_count']}")
        print(f"  PLANNING SIGNALS={s['planning_signals']}")

    print("\nPLANNING DOCUMENT POSITIVE CONTROL")
    print("-" * 78)
    print(f"URL: {POSITIVE_CONTROL_PDF}")
    print(f"HTTP: {positive.get('http')}")
    print(f"CONTENT-TYPE: {positive.get('content_type')}")
    print(f"PDF MAGIC: {positive_cls['pdf_magic']}")
    print(f"BODY SIZE: {positive_cls['body_size']}")
    print(f"POSITIVE CONTROL QUALIFIED: {positive_ok}")

    print("\nDISCOVERED ARCHIVE / DOCUMENT CANDIDATES")
    print("-" * 78)
    print(f"DISCOVERED CANDIDATE COUNT: {len(discovered)}")
    print(f"SAMPLED CANDIDATE COUNT: {len(sampled)}")
    print(f"ARCHIVE CANDIDATE COUNT: {archive_candidate_count}")
    print(f"DOCUMENT CANDIDATE COUNT: {document_candidate_count}")
    for i, x in enumerate(sampled[:20], 1):
        print(f"[{i:02d}] HTTP={x['http']} DOC={x['is_document_like']} URL={x['url']}")
        print(f"     TITLE={x['title']} SIGNALS={x['planning_signals']} SOURCE_TERMS={x['source_term_hits']}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"ENTRY CONTRACT QUALIFIED: {entry_contract_qualified}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Target query executed: False")
    print("Document hit == designation notice: False")
    print("Document no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "target query not executed": out["target_query_executed"] is False,
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_ENTRY_ATTACHMENT_CONTRACT_QUALIFIED",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_ENTRY_CONTRACT_TECHNICAL_UNKNOWN",
        },
        "document hit not designation notice": out["summary"]["document_hit_equals_designation_notice"] is False,
        "document hit not current validity": out["summary"]["document_hit_equals_current_validity"] is False,
        "document hit not site inclusion": out["summary"]["document_hit_equals_site_inclusion"] is False,
        "document no-hit not legal absence": out["summary"]["document_no_hit_equals_legal_absence"] is False,
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
        raise AssertionError("S227A validation failed")


if __name__ == "__main__":
    main()
