# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode, urljoin

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
PRIOR_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_uqq700_technical_unknown_attachment_recovery.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_legacy_pdf_attachment_route_recovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
HOST = "https://www.seongnam.go.kr"
CURRENT_BOARD = "/ct-bbs020101"
BBS_CRT_SN = "19008"

EXACT_TERMS = ["개발밀도관리구역"]
VARIANT_TERMS = ["개발밀도 관리구역"]
WEAK_TERMS = ["개발밀도", "밀도관리구역"]


def curl(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "redirects": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "120",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}|%{num_redirects}",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 3)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
        content_type = parts[2] if len(parts) > 2 else None
        redirects = parts[3] if len(parts) > 3 else None
    else:
        body, http, final_url, content_type, redirects = raw, None, None, None, None
    return {
        "http": http, "final_url": final_url, "content_type": content_type,
        "redirects": redirects, "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def decode_html(body: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            pass
    return body.decode("utf-8", errors="replace")


def scan_terms(text: str) -> dict:
    exact = [t for t in EXACT_TERMS if t in text]
    variant = [t for t in VARIANT_TERMS if t in text]
    weak = [t for t in WEAK_TERMS if t in text]
    if exact:
        status = "EXACT_CONTENT_HIT"
    elif variant:
        status = "VARIANT_CONTENT_HIT"
    elif weak:
        status = "WEAK_CONTENT_HIT"
    else:
        status = "CONTENT_NO_HIT"
    return {"status": status, "exact_terms": exact, "variant_terms": variant, "weak_terms": weak}


def extract_pdf_text(body: bytes) -> tuple[str | None, str | None]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(body))
        chunks = []
        for i, p in enumerate(reader.pages, 1):
            try:
                chunks.append(p.extract_text() or "")
            except Exception as e:
                return None, f"PAGE_{i}_ERROR:{type(e).__name__}:{e}"
        return "\n".join(chunks), None
    except Exception as e:
        return None, f"PDF_PARSE_ERROR:{type(e).__name__}:{e}"


def candidate_urls(pst_sn: str, file_no: str, detail_html: str, atch_obj: dict) -> list[tuple[str, str]]:
    candidates = []
    seen = set()

    def add(label: str, url: str):
        if url and url not in seen:
            seen.add(url)
            candidates.append((label, url))

    params = urlencode({"bbsCrtSn": BBS_CRT_SN, "pstSn": pst_sn, "fileNo": file_no})
    add("CURRENT_GETFILE", f"{HOST}{CURRENT_BOARD}/getFile?{params}")
    add("CURRENT_FILEPREVIEW", f"{HOST}{CURRENT_BOARD}/filePreview?{params}")
    add("CURRENT_ATCHFILEDETAIL", f"{HOST}{CURRENT_BOARD}/atchFileDetail?{urlencode({'pstSn': pst_sn})}")

    legacy_bases = [
        "/city/1000539/30225/getFile.do",
        "/city/1000539/30225/fileDownload.do",
        "/city/1000539/30225/bbsFileDown.do",
        "/city/1000539/30225/bbsDownload.do",
        "/city/1000818/30278/getFile.do",
        "/city/1000818/30278/fileDownload.do",
        "/city/1000818/30278/bbsFileDown.do",
        "/city/1000818/30278/bbsDownload.do",
        "/common/fileDownload.do",
        "/comm/getFile",
        "/comm/fileDownload",
    ]
    legacy_param_sets = [
        {"bbsCrtSn": BBS_CRT_SN, "pstSn": pst_sn, "fileNo": file_no},
        {"pstSn": pst_sn, "fileNo": file_no},
        {"idx": pst_sn, "fileNo": file_no},
        {"bbsCrtSn": BBS_CRT_SN, "idx": pst_sn, "fileNo": file_no},
        {"fileNo": file_no},
    ]
    for base in legacy_bases:
        for ps in legacy_param_sets:
            add("LEGACY_GUESS", HOST + base + "?" + urlencode(ps))

    texts = [detail_html, json.dumps(atch_obj, ensure_ascii=False)]
    patterns = [
        re.compile(r'''(?i)(?:href|src)\s*=\s*["']([^"']*(?:getFile|filePreview|download|fileDown|contents/down)[^"']*)["']'''),
        re.compile(r'''(?i)["']([^"']*(?:getFile|filePreview|download|fileDown|contents/down)[^"']*)["']'''),
    ]
    for text in texts:
        for pat in patterns:
            for m in pat.finditer(text or ""):
                raw = m.group(1).replace("&amp;", "&")
                if raw.startswith("javascript:"):
                    continue
                add("DISCOVERED_MARKUP_OR_JSON", urljoin(HOST, raw))

    # Common explicit fields occasionally exposed by legacy metadata.
    for key in ("fileUrl", "downloadUrl", "filePath", "saveFilePath", "atchFilePath", "streFileNm"):
        value = atch_obj.get(key)
        if isinstance(value, str) and value.strip():
            v = value.strip()
            if v.startswith("http"):
                add(f"ATCH_FIELD_{key}", v)
            elif "/" in v:
                add(f"ATCH_FIELD_{key}", urljoin(HOST, v))

    return candidates[:120]


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT LEGACY PDF ATTACHMENT ROUTE RECOVERY - S227H")
    print("=" * 78)
    print("Purpose: recover only six legacy PDF attachments whose current getFile returns 404")
    print("404 != file absence != legal absence")
    print("OCR: NOT EXECUTED")
    print("UQQ700 final resolution: UNKNOWN")

    if not PRIOR_OUT.exists():
        raise FileNotFoundError(f"Required S227F output not found: {PRIOR_OUT}")
    prior = json.loads(PRIOR_OUT.read_text(encoding="utf-8"))
    targets = [r for r in (prior.get("results") or []) if r.get("extension") == "pdf" and r.get("http") == "404"]

    results = []
    recovered = remaining = exact_hits = variant_hits = weak_hits = no_hits = 0

    for idx, t in enumerate(targets, 1):
        pst_sn = str(t.get("pstSn"))
        file_no = str(t.get("fileNo"))
        detail_url = f"{HOST}{CURRENT_BOARD}/{pst_sn}"
        atch_url = f"{HOST}{CURRENT_BOARD}/atchFileDetail?{urlencode({'pstSn': pst_sn})}"
        detail = curl(detail_url)
        atch = curl(atch_url)
        detail_html = decode_html(detail.get("body") or b"") if detail.get("body") else ""
        try:
            atch_json = json.loads(decode_html(atch.get("body") or b"")) if atch.get("body") else {}
        except Exception:
            atch_json = {}
        atch_list = atch_json.get("atchFileVO") if isinstance(atch_json, dict) else None
        if not isinstance(atch_list, list):
            atch_list = []
        matching = [x for x in atch_list if str(x.get("fileNo")) == file_no]
        atch_obj = matching[0] if matching else {}

        candidate_results = []
        recovered_body = None
        recovered_url = None
        for label, url in candidate_urls(pst_sn, file_no, detail_html, atch_obj):
            rr = curl(url)
            body = rr.get("body") or b""
            is_pdf = rr.get("http") == "200" and body.startswith(b"%PDF-")
            candidate_results.append({
                "label": label, "url": url, "http": rr.get("http"), "final_url": rr.get("final_url"),
                "content_type": rr.get("content_type"), "redirects": rr.get("redirects"),
                "body_size": len(body), "prefix_hex": body[:24].hex(), "pdf_magic": is_pdf,
            })
            if is_pdf:
                recovered_body = body
                recovered_url = rr.get("final_url") or url
                break

        rec = {
            "pstSn": pst_sn, "fileNo": file_no, "name": t.get("name"),
            "detail_http": detail.get("http"), "atch_http": atch.get("http"),
            "atch_json_ok": bool(atch_json), "metadata_file_still_present": bool(matching),
            "matching_attachment_metadata": atch_obj,
            "candidate_probe_count": len(candidate_results), "candidate_results": candidate_results,
            "recovered_pdf": recovered_body is not None, "recovered_url": recovered_url,
            "status": "LEGACY_ATTACHMENT_TRANSPORT_TECHNICAL_UNKNOWN", "error": None,
            "exact_terms": [], "variant_terms": [], "weak_terms": [],
        }

        if recovered_body is not None:
            text, err = extract_pdf_text(recovered_body)
            if text is None:
                rec["error"] = err
                remaining += 1
            else:
                rec.update(scan_terms(text))
                recovered += 1
                if rec["status"] == "EXACT_CONTENT_HIT": exact_hits += 1
                elif rec["status"] == "VARIANT_CONTENT_HIT": variant_hits += 1
                elif rec["status"] == "WEAK_CONTENT_HIT": weak_hits += 1
                elif rec["status"] == "CONTENT_NO_HIT": no_hits += 1
        else:
            rec["error"] = "NO_BOUNDED_ROUTE_RETURNED_PDF_BINARY"
            remaining += 1

        results.append(rec)
        print(f"LEGACY PDF RECOVERY: {idx}/{len(targets)} | PSTSN={pst_sn} | FILENO={file_no} | META={rec['metadata_file_still_present']} | PROBES={rec['candidate_probe_count']} | STATUS={rec['status']}")

    if exact_hits or variant_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_PDF_RECOVERY_UQQ700_CANDIDATE_HIT"
        semantic = "RECOVERED_LEGACY_PDF_CONTENT_CONTAINS_EXACT_OR_VARIANT_UQQ700_TERM_REQUIRING_CONTEXT_AND_OFFICIAL_NOTICE_TRACE"
        next_action = "REVIEW_ONLY_RECOVERED_EXACT_OR_VARIANT_HIT_CONTEXT_AND_TRACE_LITERAL_NOTICE_IDENTITY_NON_PROMOTIONALLY"
    elif weak_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_PDF_RECOVERY_WEAK_HIT"
        semantic = "RECOVERED_LEGACY_PDF_CONTENT_CONTAINS_WEAK_DENSITY_TERM_WITHOUT_DESIGNATION_PROMOTION"
        next_action = "REVIEW_RECOVERED_WEAK_CONTEXT_NON_PROMOTIONALLY_BEFORE_FINAL_SOURCE_FAMILY_RECONCILIATION"
    elif remaining == 0:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_PDF_ATTACHMENTS_FULLY_RECOVERED_NO_UQQ700_HIT"
        semantic = "ALL_SIX_LEGACY_PDF_ATTACHMENTS_RECOVERED_AND_SCANNED_WITH_NO_UQQ700_TERM"
        next_action = "RECONCILE_PLANNING_DOCUMENT_SOURCE_FAMILY_OPERATIONALLY_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_PDF_ATTACHMENT_TRANSPORT_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_MORE_LEGACY_PDF_ATTACHMENTS_REMAIN_UNRECOVERED_AFTER_BOUNDED_CURRENT_AND_LEGACY_ROUTE_PROBES"
        next_action = "RECONCILE_METADATA_PRESENCE_AND_ROUTE_FAILURE_NON_NEGATIVELY_OR_REVERSE_DISCOVER_ARCHIVED_ATTACHMENT_STORAGE_WITHOUT_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-154-S227H",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prior_input_exists": PRIOR_OUT.exists(),
        "target_legacy_pdf_count": len(targets),
        "recovered_pdf_count": recovered,
        "remaining_legacy_pdf_technical_unknown_count": remaining,
        "exact_content_hit_count": exact_hits,
        "variant_content_hit_count": variant_hits,
        "weak_content_hit_count": weak_hits,
        "content_no_hit_count": no_hits,
        "results": results,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "legacy_pdf_hit_equals_designation_notice": False,
            "legacy_pdf_hit_equals_current_validity": False,
            "legacy_pdf_hit_equals_site_inclusion": False,
            "legacy_pdf_no_hit_equals_legal_absence": False,
            "legacy_pdf_404_equals_file_absence": False,
            "remaining_legacy_pdf_unknown_equals_legal_absence": False,
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

    print("\nLEGACY PDF ATTACHMENT RECOVERY SUMMARY")
    print("-" * 78)
    print(f"TARGET LEGACY PDF COUNT: {len(targets)}")
    print(f"RECOVERED PDF COUNT: {recovered}")
    print(f"REMAINING LEGACY PDF TECHNICAL UNKNOWN COUNT: {remaining}")
    print(f"EXACT CONTENT HIT COUNT: {exact_hits}")
    print(f"VARIANT CONTENT HIT COUNT: {variant_hits}")
    print(f"WEAK CONTENT HIT COUNT: {weak_hits}")
    print(f"CONTENT NO HIT COUNT: {no_hits}")

    print("\nDETAILS")
    print("-" * 78)
    for r in results:
        print(f"PSTSN={r['pstSn']} FILENO={r['fileNo']} NAME={r['name']}")
        print(f"  DETAIL_HTTP={r['detail_http']} ATCH_HTTP={r['atch_http']} ATCH_JSON_OK={r['atch_json_ok']} META_PRESENT={r['metadata_file_still_present']}")
        print(f"  PROBE_COUNT={r['candidate_probe_count']} RECOVERED={r['recovered_pdf']} STATUS={r['status']} ERROR={r['error']}")
        for p in r['candidate_results'][:30]:
            print(f"    {p}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Legacy PDF 404 == file absence: False")
    print("Legacy PDF hit == designation/current validity/site inclusion: False")
    print("Legacy PDF no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S227F input exists": PRIOR_OUT.exists(),
        "legacy PDF targets present": len(targets) > 0,
        "404 not file absence": out["summary"]["legacy_pdf_404_equals_file_absence"] is False,
        "legacy hit not designation": out["summary"]["legacy_pdf_hit_equals_designation_notice"] is False,
        "legacy hit not validity": out["summary"]["legacy_pdf_hit_equals_current_validity"] is False,
        "legacy hit not site inclusion": out["summary"]["legacy_pdf_hit_equals_site_inclusion"] is False,
        "legacy no-hit not legal absence": out["summary"]["legacy_pdf_no_hit_equals_legal_absence"] is False,
        "remaining unknown not legal absence": out["summary"]["remaining_legacy_pdf_unknown_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_PDF_RECOVERY_UQQ700_CANDIDATE_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_PDF_RECOVERY_WEAK_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_PDF_ATTACHMENTS_FULLY_RECOVERED_NO_UQQ700_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_PDF_ATTACHMENT_TRANSPORT_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S227H validation failed")


if __name__ == "__main__":
    main()
