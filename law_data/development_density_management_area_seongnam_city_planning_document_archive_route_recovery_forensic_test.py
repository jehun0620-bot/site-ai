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
S227A_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_archive_entry_contract_qualification.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_archive_route_recovery_forensic.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
OFFICIAL_HOST = "www.seongnam.go.kr"

# No UQQ700 query in this stage. These are route/attachment positive controls only.
ENTRY_CANDIDATES = [
    "https://www.seongnam.go.kr/ct020100",
    "https://www.seongnam.go.kr/city/1000539/30225/bbsView.do?idx=198961",
    "https://www.seongnam.go.kr/city/1000818/30278/bbsList.do",
    "https://www.seongnam.go.kr/pm010301/151718",
]

PLANNING_TERMS = (
    "도시기본계획", "도시관리계획", "지구단위계획", "도시계획", "계획",
    "도시주택국", "도시계획과", "첨부파일", "다운로드", "바로보기",
)
FILE_EXTS = (".pdf", ".hwp", ".hwpx", ".xls", ".xlsx", ".doc", ".docx")
HREF_RE = re.compile(r'''(?is)<a\b([^>]*?)href\s*=\s*(["'])(.*?)\2([^>]*)>(.*?)</a>''')
FORM_RE = re.compile(r"(?is)<form\b([^>]*)>(.*?)</form>")
SCRIPT_SRC_RE = re.compile(r'''(?is)<script\b[^>]*src\s*=\s*(["'])(.*?)\1''')
URL_LIKE_RE = re.compile(r'''(?i)(?:https?://[^\s"'<>]+|/[A-Za-z0-9_./?=&%-]+)''')
TITLE_RE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")


def curl_request(url: str, *, method: str = "GET", data: str | None = None) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"ok": False, "http": None, "final_url": None, "content_type": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "60",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}",
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
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 2)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
        content_type = parts[2] if len(parts) > 2 else None
    else:
        body, http, final_url, content_type = raw, None, None, None
    return {
        "ok": p.returncode == 0 and bool(http and http != "000"),
        "returncode": p.returncode,
        "http": http,
        "final_url": final_url,
        "content_type": content_type,
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


def same_host(url: str) -> bool:
    try:
        return (urlparse(url).hostname or "").lower() == OFFICIAL_HOST
    except Exception:
        return False


def page_title(html: str) -> str | None:
    m = TITLE_RE.search(html or "")
    return clean_html(m.group(1)) if m else None


def classify_binary(resp: dict) -> dict:
    body = resp.get("body") or b""
    ct = (resp.get("content_type") or "").lower()
    return {
        "pdf_magic": body.startswith(b"%PDF-"),
        "ole_magic": body.startswith(bytes.fromhex("D0CF11E0A1B11AE1")),
        "zip_magic": body.startswith(b"PK\x03\x04"),
        "pdf_content_type": "pdf" in ct,
        "hwp_content_type": "hwp" in ct or "haansofthwp" in ct,
        "zip_content_type": "zip" in ct,
        "html_content_type": "html" in ct,
        "body_size": len(body),
    }


def extract_forms(html: str, base_url: str) -> list[dict]:
    rows = []
    for fm in FORM_RE.finditer(html or ""):
        a = attr_map(fm.group(1))
        inner = fm.group(2)
        inputs = []
        for im in re.finditer(r"(?is)<(?:input|select|button)\b([^>]*)>", inner):
            ia = attr_map(im.group(1))
            if ia.get("name") or ia.get("id"):
                inputs.append({k: ia.get(k) for k in ("name", "id", "type", "value") if ia.get(k) is not None})
        rows.append({
            "id": a.get("id"), "name": a.get("name"), "method": (a.get("method") or "GET").upper(),
            "action": urljoin(base_url, a.get("action") or base_url), "inputs": inputs[:50],
        })
    return rows


def extract_candidates(html: str, base_url: str) -> list[dict]:
    found = {}
    text = clean_html(html)
    for m in HREF_RE.finditer(html or ""):
        attrs = attr_map((m.group(1) or "") + " " + (m.group(4) or ""))
        href = unescape(m.group(3)).strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        url = urljoin(base_url, href)
        if not same_host(url):
            continue
        label = clean_html(m.group(5))
        blob = " ".join([label, attrs.get("title", ""), attrs.get("onclick", ""), url])
        term_hits = [t for t in PLANNING_TERMS if t in blob]
        file_like = any(ext in url.lower() for ext in FILE_EXTS) or any(k in url.lower() for k in ("getfile", "filepreview", "/contents/down/", "download"))
        if term_hits or file_like:
            found.setdefault(url, {"url": url, "label": label[:500], "term_hits": term_hits, "file_like": file_like, "source": "anchor"})

    for sm in SCRIPT_SRC_RE.finditer(html or ""):
        url = urljoin(base_url, unescape(sm.group(2)).strip())
        if same_host(url):
            found.setdefault(url, {"url": url, "label": "", "term_hits": [], "file_like": False, "source": "script_src"})

    for um in URL_LIKE_RE.finditer(html or ""):
        raw = unescape(um.group(0))
        url = urljoin(base_url, raw)
        if not same_host(url):
            continue
        low = url.lower()
        file_like = any(ext in low for ext in FILE_EXTS) or any(k in low for k in ("getfile", "filepreview", "/contents/down/", "download"))
        route_like = any(k in low for k in ("ct020100", "bbsview", "bbslist", "select", "getfile", "filepreview"))
        if file_like or route_like:
            found.setdefault(url, {"url": url, "label": "", "term_hits": [], "file_like": file_like, "source": "html_literal"})
    return list(found.values())


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT ARCHIVE ROUTE RECOVERY FORENSIC - S227A-R")
    print("=" * 78)
    print("Purpose: recover current official planning-document list/detail/attachment routes")
    print("UQQ700 target query: NOT EXECUTED")
    print("No-hit != legal absence")
    print("SITE FALSE inference: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s227a_exists = S227A_OUT.exists()
    s227a = json.loads(S227A_OUT.read_text(encoding="utf-8")) if s227a_exists else {}

    surfaces = []
    all_candidates = {}
    for url in ENTRY_CANDIDATES:
        r = curl_request(url)
        html, enc = decode_body(r.get("body") or b"")
        text = clean_html(html)
        forms = extract_forms(html, r.get("final_url") or url) if r.get("http") == "200" else []
        candidates = extract_candidates(html, r.get("final_url") or url) if r.get("http") == "200" else []
        for c in candidates:
            all_candidates.setdefault(c["url"], c)
        surfaces.append({
            "url": url,
            "http": r.get("http"),
            "final_url": r.get("final_url"),
            "content_type": r.get("content_type"),
            "charset": enc,
            "title": page_title(html),
            "planning_signals": [t for t in PLANNING_TERMS if t in text],
            "form_count": len(forms),
            "forms": forms,
            "candidate_count": len(candidates),
        })

    candidates = list(all_candidates.values())
    candidates.sort(key=lambda x: (not x["file_like"], -len(x["term_hits"]), x["url"]))

    sampled = []
    qualified_attachments = []
    for c in candidates[:60]:
        r = curl_request(c["url"])
        cls = classify_binary(r)
        row = {
            **c,
            "http": r.get("http"),
            "final_url": r.get("final_url"),
            "content_type": r.get("content_type"),
            "content_class": cls,
        }
        if cls["html_content_type"]:
            html, _ = decode_body(r.get("body") or b"")
            row["title"] = page_title(html)
            row["planning_signals"] = [t for t in PLANNING_TERMS if t in clean_html(html)]
        else:
            row["title"] = None
            row["planning_signals"] = []
        sampled.append(row)
        if r.get("http") == "200" and (cls["pdf_magic"] or cls["ole_magic"] or cls["zip_magic"] or cls["pdf_content_type"] or cls["hwp_content_type"]):
            qualified_attachments.append(row)

    current_plan_surface = next((s for s in surfaces if s["url"].endswith("/ct020100") and s["http"] == "200" and any(t in s["planning_signals"] for t in ("도시기본계획", "도시관리계획", "지구단위계획", "도시계획"))), None)
    legacy_detail_surface = next((s for s in surfaces if "198961" in s["url"] and s["http"] == "200"), None)
    attachment_contract_qualified = bool(qualified_attachments)
    route_contract_qualified = bool(current_plan_surface or legacy_detail_surface)

    if route_contract_qualified and attachment_contract_qualified:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_ROUTE_ATTACHMENT_CONTRACT_RECOVERED"
        semantic = "CURRENT_OR_LEGACY_OFFICIAL_PLANNING_SURFACE_AND_AT_LEAST_ONE_REAL_ATTACHMENT_DOWNLOAD_VERIFIED_WITHOUT_UQQ700_QUERY"
        next_action = "QUALIFY_ARCHIVE_COVERAGE_AND_CANONICAL_DOCUMENT_ENUMERATION_BEFORE_UQQ700_CONTENT_SCAN"
    elif route_contract_qualified:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_ROUTE_RECOVERED_ATTACHMENT_TECHNICAL_UNKNOWN"
        semantic = "OFFICIAL_PLANNING_SURFACE_RECOVERED_BUT_BINARY_ATTACHMENT_DOWNLOAD_NOT_YET_VERIFIED"
        next_action = "HARDEN_ATTACHMENT_DOWNLOAD_PARAMETERS_FROM_VERIFIED_PLANNING_DETAIL_WITHOUT_NEGATIVE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_ROUTE_TECHNICAL_UNKNOWN"
        semantic = "PLANNING_ARCHIVE_ROUTE_NOT_YET_TECHNICALLY_QUALIFIED"
        next_action = "CONTINUE_ROUTE_RECOVERY_FROM_OFFICIAL_SEARCH_MENU_OR_SCRIPT_CONTRACT"

    out = {
        "step": "STEP 17-21-C-16-8-T-143-S227A-R",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s227a_input_exists": s227a_exists,
        "target_query_executed": False,
        "entry_candidates": ENTRY_CANDIDATES,
        "surfaces": surfaces,
        "candidate_count": len(candidates),
        "candidates": candidates[:120],
        "sampled_count": len(sampled),
        "sampled": sampled,
        "qualified_attachment_count": len(qualified_attachments),
        "qualified_attachments": qualified_attachments[:30],
        "route_contract_qualified": route_contract_qualified,
        "attachment_contract_qualified": attachment_contract_qualified,
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
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nENTRY SURFACES")
    print("-" * 78)
    for s in surfaces:
        print(f"HTTP={s['http']} | URL={s['url']}")
        print(f"  FINAL={s['final_url']}")
        print(f"  TITLE={s['title']}")
        print(f"  SIGNALS={s['planning_signals']}")
        print(f"  FORMS={s['form_count']} CANDIDATES={s['candidate_count']}")

    print("\nROUTE / ATTACHMENT CANDIDATES")
    print("-" * 78)
    print(f"CANDIDATE COUNT: {len(candidates)}")
    print(f"SAMPLED COUNT: {len(sampled)}")
    print(f"QUALIFIED ATTACHMENT COUNT: {len(qualified_attachments)}")
    for i, x in enumerate(sampled[:30], 1):
        c = x["content_class"]
        print(f"[{i:02d}] HTTP={x['http']} FILELIKE={x['file_like']} PDF={c['pdf_magic']} OLE={c['ole_magic']} ZIP={c['zip_magic']}")
        print(f"     URL={x['url']}")
        print(f"     CT={x['content_type']} TITLE={x.get('title')}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"ROUTE CONTRACT QUALIFIED: {route_contract_qualified}")
    print(f"ATTACHMENT CONTRACT QUALIFIED: {attachment_contract_qualified}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Target query executed: False")
    print("Document no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S227A input exists": s227a_exists,
        "target query not executed": out["target_query_executed"] is False,
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_ROUTE_ATTACHMENT_CONTRACT_RECOVERED",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_ROUTE_RECOVERED_ATTACHMENT_TECHNICAL_UNKNOWN",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ARCHIVE_ROUTE_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S227A-R validation failed")


if __name__ == "__main__":
    main()
