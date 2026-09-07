# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode, urljoin

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
S227H_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_legacy_pdf_attachment_route_recovery.json"
S227B_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_archive_coverage_canonical_enumeration.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_legacy_pdf_storage_reverse_discovery.json"

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

STORAGE_KEY_RE = re.compile(r"(?i)(file|path|save|store|stre|atch|attach|download|url|uri|name|nm|hist|legacy|seq|sn|id)")
URLISH_RE = re.compile(r"(?i)(https?://[^\s\"']+|/[A-Za-z0-9_./?=&%+\-]+)")


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
        "http": http,
        "final_url": final_url,
        "content_type": content_type,
        "redirects": redirects,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def decode_text(body: bytes) -> str:
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
        for i, page in enumerate(reader.pages, 1):
            try:
                chunks.append(page.extract_text() or "")
            except Exception as e:
                return None, f"PAGE_{i}_ERROR:{type(e).__name__}:{e}"
        return "\n".join(chunks), None
    except Exception as e:
        return None, f"PDF_PARSE_ERROR:{type(e).__name__}:{e}"


def normalize_scalar(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def storage_fields(obj: dict) -> dict:
    out = {}
    for k, v in (obj or {}).items():
        if STORAGE_KEY_RE.search(str(k)):
            out[k] = normalize_scalar(v)
    return out


def diff_schema(a: dict, b: dict) -> dict:
    ak, bk = set(a), set(b)
    return {
        "only_target_keys": sorted(ak - bk),
        "only_control_keys": sorted(bk - ak),
        "common_keys": sorted(ak & bk),
        "value_differences": {
            k: {"target": normalize_scalar(a.get(k)), "control": normalize_scalar(b.get(k))}
            for k in sorted(ak & bk)
            if normalize_scalar(a.get(k)) != normalize_scalar(b.get(k))
        },
    }


def load_control_attachment() -> dict | None:
    if not S227B_OUT.exists():
        return None
    try:
        data = json.loads(S227B_OUT.read_text(encoding="utf-8"))
    except Exception:
        return None
    for post in data.get("canonical_posts", []) or data.get("posts", []):
        for a in post.get("attachments", []) or []:
            if str(a.get("fileExtsn") or a.get("extension") or "").lower() == "pdf" and a.get("download_url"):
                rr = curl(a["download_url"])
                if rr.get("http") == "200" and (rr.get("body") or b"").startswith(b"%PDF-"):
                    return {
                        "pstSn": str(post.get("pstSn") or a.get("pstSn")),
                        "fileNo": str(a.get("fileNo")),
                        "name": a.get("orginlFileNm") or a.get("name"),
                        "metadata": a,
                        "download_url": a.get("download_url"),
                    }
    return None


def bounded_identifier_urls(pst_sn: str, file_no: str, metadata: dict, detail_html: str) -> list[dict]:
    candidates = []
    seen = set()

    def add(source: str, url: str):
        if not url or url in seen:
            return
        if not url.startswith(HOST):
            return
        seen.add(url)
        candidates.append({"source": source, "url": url})

    # Direct URL/path-like metadata values only; no arbitrary endpoint fabrication.
    for key, value in (metadata or {}).items():
        if not isinstance(value, str) or not value.strip():
            continue
        v = value.strip().replace("&amp;", "&")
        if v.startswith("http://") or v.startswith("https://"):
            add(f"metadata:{key}", v)
        elif v.startswith("/") and any(tok in v.lower() for tok in ("file", "down", "attach", "atch", "content", "upload")):
            add(f"metadata:{key}", urljoin(HOST, v))

    # URL-like literals around actual identifiers in detail HTML only.
    for m in URLISH_RE.finditer(detail_html or ""):
        raw = m.group(1).replace("&amp;", "&")
        if str(file_no) not in raw and str(pst_sn) not in raw:
            continue
        add("detail_html_identifier_literal", urljoin(HOST, raw))

    # The verified current contract is retained as a diagnostic baseline.
    add("verified_current_contract", f"{HOST}{CURRENT_BOARD}/getFile?{urlencode({'bbsCrtSn': BBS_CRT_SN, 'pstSn': pst_sn, 'fileNo': file_no})}")
    return candidates[:80]


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT LEGACY PDF STORAGE REVERSE DISCOVERY - S227I")
    print("=" * 78)
    print("Purpose: compare actual attachment metadata/schema and replay only identifier-derived official-host routes")
    print("Arbitrary endpoint expansion: DISABLED")
    print("404/metadata-only != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    if not S227H_OUT.exists():
        raise FileNotFoundError(f"Required S227H output not found: {S227H_OUT}")
    prior = json.loads(S227H_OUT.read_text(encoding="utf-8"))
    targets = [r for r in (prior.get("results") or []) if not r.get("recovered_pdf")]
    control = load_control_attachment()

    results = []
    recovered = 0
    remaining = 0
    exact_hits = variant_hits = weak_hits = no_hits = 0
    metadata_present_count = 0
    storage_identity_count = 0
    schema_counter = Counter()

    for idx, t in enumerate(targets, 1):
        pst_sn = str(t.get("pstSn"))
        file_no = str(t.get("fileNo"))
        detail_url = f"{HOST}{CURRENT_BOARD}/{pst_sn}"
        atch_url = f"{HOST}{CURRENT_BOARD}/atchFileDetail?{urlencode({'pstSn': pst_sn})}"
        detail = curl(detail_url)
        atch = curl(atch_url)
        detail_html = decode_text(detail.get("body") or b"") if detail.get("body") else ""
        try:
            atch_json = json.loads(decode_text(atch.get("body") or b"")) if atch.get("body") else {}
        except Exception:
            atch_json = {}
        atch_list = atch_json.get("atchFileVO") if isinstance(atch_json, dict) else []
        if not isinstance(atch_list, list):
            atch_list = []
        matches = [x for x in atch_list if str(x.get("fileNo")) == file_no]
        metadata = matches[0] if matches else (t.get("matching_attachment_metadata") or {})
        metadata_present = bool(metadata)
        if metadata_present:
            metadata_present_count += 1
        storage_meta = storage_fields(metadata)
        for k in storage_meta:
            schema_counter[k] += 1

        control_meta = (control or {}).get("metadata") or {}
        schema_diff = diff_schema(metadata, control_meta) if control else None

        identifiers = {
            "pstSn": pst_sn,
            "fileNo": file_no,
            "bbsCrtSn": str(metadata.get("bbsCrtSn") or BBS_CRT_SN),
        }
        for k, v in storage_meta.items():
            if v not in (None, "", 0, "0"):
                identifiers[k] = v
        if len(identifiers) > 3:
            storage_identity_count += 1

        probes = []
        recovered_body = None
        recovered_url = None
        for cand in bounded_identifier_urls(pst_sn, file_no, metadata, detail_html):
            rr = curl(cand["url"])
            body = rr.get("body") or b""
            is_pdf = rr.get("http") == "200" and body.startswith(b"%PDF-")
            probes.append({
                **cand,
                "http": rr.get("http"),
                "final_url": rr.get("final_url"),
                "content_type": rr.get("content_type"),
                "redirects": rr.get("redirects"),
                "body_size": len(body),
                "prefix_hex": body[:24].hex(),
                "pdf_magic": is_pdf,
            })
            if is_pdf:
                recovered_body = body
                recovered_url = rr.get("final_url") or cand["url"]
                break

        rec = {
            "pstSn": pst_sn,
            "fileNo": file_no,
            "name": t.get("name"),
            "detail_http": detail.get("http"),
            "atch_http": atch.get("http"),
            "metadata_present": metadata_present,
            "metadata": metadata,
            "storage_fields": storage_meta,
            "identifier_snapshot": identifiers,
            "control_attachment": control,
            "schema_diff_vs_control": schema_diff,
            "probe_count": len(probes),
            "probes": probes,
            "recovered_pdf": recovered_body is not None,
            "recovered_url": recovered_url,
            "status": "LEGACY_ATTACHMENT_METADATA_ONLY_TECHNICAL_UNKNOWN",
            "error": None,
            "exact_terms": [],
            "variant_terms": [],
            "weak_terms": [],
        }

        if recovered_body is not None:
            text, err = extract_pdf_text(recovered_body)
            if text is None:
                rec["status"] = "ARCHIVED_BINARY_ACCESS_TECHNICAL_UNKNOWN"
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
            # Distinguish metadata-only from a case where a concrete storage route/key was observed but inaccessible.
            concrete_urlish = any(
                isinstance(v, str) and (v.startswith("http") or v.startswith("/"))
                for v in storage_meta.values()
            )
            if concrete_urlish:
                rec["status"] = "ARCHIVED_BINARY_ACCESS_TECHNICAL_UNKNOWN"
                rec["error"] = "IDENTIFIER_DERIVED_STORAGE_ROUTE_OBSERVED_BUT_NO_PDF_BINARY_RECOVERED"
            else:
                rec["status"] = "LEGACY_ATTACHMENT_METADATA_ONLY_TECHNICAL_UNKNOWN"
                rec["error"] = "METADATA_PRESENT_WITHOUT_RECOVERABLE_STORAGE_ROUTE_OR_BINARY"
            remaining += 1

        results.append(rec)
        print(f"STORAGE DISCOVERY: {idx}/{len(targets)} | PSTSN={pst_sn} | FILENO={file_no} | META={metadata_present} | STORAGE_FIELDS={len(storage_meta)} | PROBES={len(probes)} | STATUS={rec['status']}")

    if exact_hits or variant_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_STORAGE_RECOVERY_UQQ700_CANDIDATE_HIT"
        semantic = "IDENTIFIER_DERIVED_LEGACY_STORAGE_RECOVERY_RETURNED_PDF_WITH_EXACT_OR_VARIANT_UQQ700_TERM"
        next_action = "REVIEW_ONLY_RECOVERED_CANDIDATE_CONTEXT_AND_TRACE_LITERAL_OFFICIAL_NOTICE_IDENTITY_NON_PROMOTIONALLY"
    elif weak_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_STORAGE_RECOVERY_WEAK_HIT"
        semantic = "IDENTIFIER_DERIVED_LEGACY_STORAGE_RECOVERY_RETURNED_PDF_WITH_WEAK_DENSITY_TERM_ONLY"
        next_action = "REVIEW_RECOVERED_WEAK_CONTEXT_NON_PROMOTIONALLY_BEFORE_SOURCE_FAMILY_RECONCILIATION"
    elif remaining == 0:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_STORAGE_RECOVERY_COMPLETE_NO_UQQ700_HIT"
        semantic = "ALL_REMAINING_LEGACY_PDFS_RECOVERED_FROM_IDENTIFIER_DERIVED_STORAGE_ROUTES_AND_SCANNED_WITH_NO_UQQ700_TERM"
        next_action = "RECONCILE_PLANNING_DOCUMENT_SOURCE_FAMILY_OPERATIONALLY_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    else:
        archived_unknown = sum(r["status"] == "ARCHIVED_BINARY_ACCESS_TECHNICAL_UNKNOWN" for r in results)
        metadata_only = sum(r["status"] == "LEGACY_ATTACHMENT_METADATA_ONLY_TECHNICAL_UNKNOWN" for r in results)
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_ATTACHMENT_STORAGE_PROVENANCE_TECHNICAL_UNKNOWN"
        semantic = "LEGACY_ATTACHMENT_METADATA_PRESENCE_RECONCILED_BUT_ONE_OR_MORE_BINARIES_REMAIN_UNRECOVERED_FROM_IDENTIFIER_DERIVED_OFFICIAL_ROUTES"
        next_action = "DECIDE_NON_NEGATIVE_SOURCE_FAMILY_RECONCILIATION_OR_ARCHIVAL_STORAGE_REVERSE_DISCOVERY_WITHOUT_TREATING_UNRECOVERED_BINARIES_AS_LEGAL_ABSENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-155-S227I",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prior_input_exists": S227H_OUT.exists(),
        "control_attachment_found": control is not None,
        "target_count": len(targets),
        "metadata_present_count": metadata_present_count,
        "storage_identity_observed_count": storage_identity_count,
        "storage_field_frequency": dict(schema_counter),
        "recovered_pdf_count": recovered,
        "remaining_technical_unknown_count": remaining,
        "exact_content_hit_count": exact_hits,
        "variant_content_hit_count": variant_hits,
        "weak_content_hit_count": weak_hits,
        "content_no_hit_count": no_hits,
        "results": results,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "metadata_presence_equals_binary_presence": False,
            "metadata_only_equals_legal_absence": False,
            "archived_binary_access_failure_equals_legal_absence": False,
            "storage_recovery_hit_equals_designation_notice": False,
            "storage_recovery_hit_equals_current_validity": False,
            "storage_recovery_hit_equals_site_inclusion": False,
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

    print("\nLEGACY PDF STORAGE REVERSE DISCOVERY SUMMARY")
    print("-" * 78)
    print(f"CONTROL ATTACHMENT FOUND: {control is not None}")
    print(f"TARGET COUNT: {len(targets)}")
    print(f"METADATA PRESENT COUNT: {metadata_present_count}")
    print(f"STORAGE IDENTITY OBSERVED COUNT: {storage_identity_count}")
    print(f"STORAGE FIELD FREQUENCY: {dict(schema_counter)}")
    print(f"RECOVERED PDF COUNT: {recovered}")
    print(f"REMAINING TECHNICAL UNKNOWN COUNT: {remaining}")
    print(f"EXACT CONTENT HIT COUNT: {exact_hits}")
    print(f"VARIANT CONTENT HIT COUNT: {variant_hits}")
    print(f"WEAK CONTENT HIT COUNT: {weak_hits}")
    print(f"CONTENT NO HIT COUNT: {no_hits}")

    print("\nDETAILS")
    print("-" * 78)
    for r in results:
        print(f"PSTSN={r['pstSn']} FILENO={r['fileNo']} NAME={r['name']} STATUS={r['status']}")
        print(f"  DETAIL_HTTP={r['detail_http']} ATCH_HTTP={r['atch_http']} META={r['metadata_present']}")
        print(f"  STORAGE_FIELDS={r['storage_fields']}")
        print(f"  IDENTIFIERS={r['identifier_snapshot']}")
        print(f"  SCHEMA_DIFF={r['schema_diff_vs_control']}")
        print(f"  PROBE_COUNT={r['probe_count']} RECOVERED={r['recovered_pdf']} ERROR={r['error']}")
        for p in r["probes"][:25]:
            print(f"    {p}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Metadata presence == binary presence: False")
    print("Metadata-only == legal absence: False")
    print("Archived binary access failure == legal absence: False")
    print("Storage recovery hit == designation/current validity/site inclusion: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S227H input exists": S227H_OUT.exists(),
        "legacy storage targets present": len(targets) > 0,
        "metadata presence not binary presence": out["summary"]["metadata_presence_equals_binary_presence"] is False,
        "metadata only not legal absence": out["summary"]["metadata_only_equals_legal_absence"] is False,
        "archive access failure not legal absence": out["summary"]["archived_binary_access_failure_equals_legal_absence"] is False,
        "storage hit not designation": out["summary"]["storage_recovery_hit_equals_designation_notice"] is False,
        "storage hit not validity": out["summary"]["storage_recovery_hit_equals_current_validity"] is False,
        "storage hit not site inclusion": out["summary"]["storage_recovery_hit_equals_site_inclusion"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_STORAGE_RECOVERY_UQQ700_CANDIDATE_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_STORAGE_RECOVERY_WEAK_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_STORAGE_RECOVERY_COMPLETE_NO_UQQ700_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_LEGACY_ATTACHMENT_STORAGE_PROVENANCE_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S227I validation failed")


if __name__ == "__main__":
    main()
