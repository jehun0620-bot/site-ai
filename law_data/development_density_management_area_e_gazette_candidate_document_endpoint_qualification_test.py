# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
S221J = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_subject_desc_candidate_identity_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_candidate_document_endpoint_qualification.json"

BASE_URL = "https://www.gwanbo.go.kr/"
TARGET = "개발밀도관리구역"
EXPECTED_NOTICE = "국무총리실고시제2010-1호"
EXPECTED_TITLE = "사회·행정적 규제 및 추가등록 규제 일몰제 확대 추진계획"


def text_preview(content: bytes, limit: int = 1200) -> str:
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return content.decode(enc, errors="ignore")[:limit]
        except Exception:
            pass
    return ""


def extract_pdf_text(content: bytes):
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        chunks = []
        for page in reader.pages[:30]:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(chunks), None, len(reader.pages)
    except Exception as ex:  # diagnostic stage
        return "", f"{type(ex).__name__}: {ex}", None


def request_record(session: requests.Session, url: str, referer: str | None = None):
    headers = {"Referer": referer} if referer else None
    try:
        r = session.get(url, timeout=60, allow_redirects=True, headers=headers)
        body = r.content
        ctype = r.headers.get("Content-Type", "")
        is_pdf = body.startswith(b"%PDF-") or "application/pdf" in ctype.lower()
        return {
            "url": url,
            "http": r.status_code,
            "final_url": str(r.url),
            "content_type": ctype,
            "body_bytes": len(body),
            "pdf_signature": body.startswith(b"%PDF-"),
            "is_pdf": is_pdf,
            "body": body,
            "text_preview": text_preview(body),
            "error": None,
        }
    except requests.RequestException as ex:
        return {
            "url": url,
            "http": None,
            "final_url": None,
            "content_type": "",
            "body_bytes": 0,
            "pdf_signature": False,
            "is_pdf": False,
            "body": b"",
            "text_preview": "",
            "error": f"{type(ex).__name__}: {ex}",
        }


def main():
    print("=" * 78)
    print("E-GAZETTE CANDIDATE DOCUMENT ENDPOINT QUALIFICATION - S221K")
    print("=" * 78)
    print("Candidate:", EXPECTED_NOTICE, EXPECTED_TITLE)
    print("Target term:", TARGET)
    print("Document/body hit != official designation identity")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution before qualification: UNKNOWN")

    s221j = json.loads(S221J.read_text(encoding="utf-8"))
    summary_j = s221j.get("summary") or {}
    candidates = s221j.get("raw_candidates") or []
    gate_j = (
        s221j.get("classification") == "CANDIDATE_IDENTITY_RECOVERED"
        and len(candidates) == 1
        and summary_j.get("uqq700_final_resolution") == "UNKNOWN"
        and s221j.get("official_designation_identity_verified") is False
    )
    if not gate_j:
        raise AssertionError("S221K prerequisite S221J gate not satisfied")

    raw = candidates[0].get("raw_item") or {}
    subject = str(raw.get("stored_field_subject") or "")
    toc_id = str(raw.get("stored_toc_seq") or "")
    ebook_no = str(raw.get("stored_ebook_no") or raw.get("keyword_ebook_no") or "")
    field_url = str(raw.get("stored_field_url") or "")
    pdf_file_path = str(raw.get("stored_pdf_file_path") or "")
    file_name = str(raw.get("stored_file_name") or "")
    search_key = str(raw.get("search_key") or "")

    m = re.search(r"contentId=([^&]+)", field_url)
    content_id = m.group(1) if m else ""
    m2 = re.search(r"tocId=([^&]+)", field_url)
    url_toc_id = m2.group(1) if m2 else ""

    candidate_identity_matches = EXPECTED_NOTICE in subject and EXPECTED_TITLE in subject
    recovered_ids = bool(content_id and toc_id and (url_toc_id == toc_id))

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    entry = request_record(session, BASE_URL)
    detail_url = urljoin(BASE_URL, field_url)
    detail = request_record(session, detail_url, referer=BASE_URL)

    # Bounded public PDF endpoint candidates derived only from recovered official metadata.
    pdf_candidates = []
    if content_id and toc_id:
        pdf_candidates.extend([
            urljoin(BASE_URL, f"ndata/gwanbo/{content_id}/toc/{toc_id}.pdf"),
            urljoin(BASE_URL, f"/ndata/gwanbo/{content_id}/toc/{toc_id}.pdf"),
        ])
    if pdf_file_path:
        pdf_candidates.append(urljoin(BASE_URL, pdf_file_path.lstrip("/")))
    dedup = []
    for u in pdf_candidates:
        if u not in dedup:
            dedup.append(u)
    pdf_candidates = dedup[:3]

    pdf_attempts = [request_record(session, u, referer=detail_url) for u in pdf_candidates]

    actual_pdf = next((r for r in pdf_attempts if r["http"] == 200 and r["is_pdf"]), None)
    pdf_text = ""
    pdf_text_error = None
    pdf_page_count = None
    if actual_pdf is not None:
        pdf_text, pdf_text_error, pdf_page_count = extract_pdf_text(actual_pdf["body"])

    detail_text = detail.get("text_preview", "")
    detail_identity_signal = EXPECTED_NOTICE in detail_text or EXPECTED_TITLE in detail_text
    pdf_identity_signal = EXPECTED_NOTICE in pdf_text or EXPECTED_TITLE in pdf_text
    document_identity_signal = candidate_identity_matches and (detail_identity_signal or pdf_identity_signal or actual_pdf is not None)
    body_term_hit = TARGET in pdf_text or TARGET in detail_text

    detail_endpoint_qualified = detail.get("http") == 200 and detail.get("body_bytes", 0) > 0
    pdf_endpoint_qualified = actual_pdf is not None
    document_endpoint_qualified = detail_endpoint_qualified or pdf_endpoint_qualified

    if not document_endpoint_qualified:
        classification = "TECHNICAL_UNKNOWN"
    elif body_term_hit:
        classification = "DOCUMENT_BODY_TERM_HIT"
    elif document_identity_signal:
        classification = "DOCUMENT_IDENTITY_QUALIFIED"
    else:
        classification = "DOCUMENT_ENDPOINT_QUALIFIED"

    semantic = {
        "TECHNICAL_UNKNOWN": "E_GAZETTE_CANDIDATE_DOCUMENT_ENDPOINT_TECHNICAL_UNKNOWN",
        "DOCUMENT_ENDPOINT_QUALIFIED": "E_GAZETTE_CANDIDATE_DOCUMENT_ENDPOINT_QUALIFIED_IDENTITY_PENDING",
        "DOCUMENT_IDENTITY_QUALIFIED": "E_GAZETTE_CANDIDATE_DOCUMENT_IDENTITY_QUALIFIED_BODY_TERM_NOT_OBSERVED",
        "DOCUMENT_BODY_TERM_HIT": "E_GAZETTE_CANDIDATE_DOCUMENT_BODY_TERM_HIT_CONTEXT_ONLY",
    }[classification]

    if classification == "DOCUMENT_BODY_TERM_HIT":
        next_action = "INSPECT_TERM_CONTEXT_AND_DETERMINE_WHETHER_CANDIDATE_IS_REGULATORY_CONTEXT_ONLY_NOT_DESIGNATION_NOTICE"
    elif classification == "DOCUMENT_IDENTITY_QUALIFIED":
        next_action = "CLASSIFY_CANDIDATE_AS_DOCUMENT_IDENTITY_WITHOUT_DESIGNATION_PROMOTION_AND_CONTINUE_BOUNDED_TERM_VARIANTS"
    elif classification == "DOCUMENT_ENDPOINT_QUALIFIED":
        next_action = "FORENSIC_E_GAZETTE_DETAIL_RENDERER_OR_PDF_DELIVERY_CONTRACT_FOR_DOCUMENT_IDENTITY"
    else:
        next_action = "KEEP_E_GAZETTE_CANDIDATE_TECHNICAL_UNKNOWN_AND_INSPECT_DOCUMENT_DELIVERY_CONTRACT"

    clean_attempts = []
    for r in pdf_attempts:
        clean_attempts.append({k: v for k, v in r.items() if k != "body"})

    out = {
        "step": "STEP 17-21-C-16-8-T-127-S221K",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "input_s221j": str(S221J),
        "candidate": {
            "subject": subject,
            "content_id": content_id,
            "toc_id": toc_id,
            "url_toc_id": url_toc_id,
            "ebook_no": ebook_no,
            "file_name": file_name,
            "search_key": search_key,
            "stored_field_url": field_url,
            "stored_pdf_file_path": pdf_file_path,
            "candidate_identity_matches_expected": candidate_identity_matches,
            "recovered_ids_consistent": recovered_ids,
        },
        "entry": {k: v for k, v in entry.items() if k != "body"},
        "detail": {k: v for k, v in detail.items() if k != "body"},
        "pdf_attempts": clean_attempts,
        "pdf_text": {
            "available": bool(pdf_text),
            "extract_error": pdf_text_error,
            "page_count": pdf_page_count,
            "length": len(pdf_text),
            "target_term_hit": TARGET in pdf_text,
            "expected_notice_hit": EXPECTED_NOTICE in pdf_text,
            "expected_title_hit": EXPECTED_TITLE in pdf_text,
            "preview": pdf_text[:4000],
        },
        "classification": classification,
        "summary": {
            "detail_endpoint_qualified": detail_endpoint_qualified,
            "pdf_endpoint_qualified": pdf_endpoint_qualified,
            "document_endpoint_qualified": document_endpoint_qualified,
            "document_identity_signal": document_identity_signal,
            "document_body_term_hit": body_term_hit,
            "semantic_state": semantic,
            "next_action": next_action,
            "document_hit_equals_designation_identity": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "legal_absence": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "official_designation_identity_verified": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("CANDIDATE SUBJECT:", subject)
    print("CONTENT ID:", content_id)
    print("TOC ID:", toc_id)
    print("EBOOK NO:", ebook_no)
    print("DETAIL URL:", detail_url)
    print("DETAIL HTTP:", detail.get("http"))
    print("DETAIL CONTENT-TYPE:", detail.get("content_type"))
    print("DETAIL BODY BYTES:", detail.get("body_bytes"))
    print("DETAIL IDENTITY SIGNAL:", detail_identity_signal)
    print("PDF ATTEMPT COUNT:", len(pdf_attempts))
    for i, r in enumerate(pdf_attempts, 1):
        print(f"PDF[{i}] HTTP={r['http']} type={r['content_type']} bytes={r['body_bytes']} signature={r['pdf_signature']} url={r['url']}")
    print("PDF ENDPOINT QUALIFIED:", pdf_endpoint_qualified)
    print("PDF TEXT LENGTH:", len(pdf_text))
    print("PDF TEXT ERROR:", pdf_text_error)
    print("PDF PAGE COUNT:", pdf_page_count)
    print("DOCUMENT IDENTITY SIGNAL:", document_identity_signal)
    print("DOCUMENT BODY TERM HIT:", body_term_hit)
    print("CLASSIFICATION:", classification)

    if pdf_text:
        print("\nPDF TEXT PREVIEW")
        print(pdf_text[:4000])

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221J candidate identity gate": gate_j,
        "candidate subject matches recovered identity": candidate_identity_matches,
        "content/toc ids recovered consistently": recovered_ids,
        "response classified": classification in {"DOCUMENT_ENDPOINT_QUALIFIED", "DOCUMENT_IDENTITY_QUALIFIED", "DOCUMENT_BODY_TERM_HIT", "TECHNICAL_UNKNOWN"},
        "document hit not designation identity": out["summary"]["document_hit_equals_designation_identity"] is False,
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "legal absence false": out["summary"]["legal_absence"] is False,
        "designation identity not promoted": out["official_designation_identity_verified"] is False,
        "current validity not promoted": out["current_validity_verified"] is False,
        "site inclusion not promoted": out["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": not out["site_positive_allowed"] and not out["site_negative_allowed"],
        "runtime registration blocked": not out["runtime_registration_allowed"],
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S221K e-gazette candidate document endpoint qualification failed")


if __name__ == "__main__":
    main()
