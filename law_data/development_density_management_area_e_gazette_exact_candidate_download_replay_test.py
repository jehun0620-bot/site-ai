# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from pypdf import PdfReader

BASE = Path(__file__).resolve().parent.parent
S221N = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_viewer_backend_request_contract_forensic.json"
S221J = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_subject_desc_candidate_identity_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_exact_candidate_download_replay.json"

BASE_URL = "https://www.gwanbo.go.kr/"
TARGET = "개발밀도관리구역"
EXPECTED_NOTICE_PREFIX = "국무총리실고시제2010-1호"
EXPECTED_TITLE_FRAGMENT = "사회·행정적 규제 및 추가등록 규제 일몰제 확대 추진계획"
DOWNLOAD_PATH = "/user/common/ofcttCntntDownload.do"


def safe_get(session: requests.Session, url: str, referer: str | None = None):
    try:
        r = session.get(url, timeout=60, allow_redirects=True, headers={"Referer": referer} if referer else None)
        return r, None
    except requests.RequestException as ex:
        return None, f"{type(ex).__name__}: {ex}"


def safe_post(session: requests.Session, url: str, data: dict[str, str], referer: str):
    try:
        r = session.post(
            url,
            data=data,
            timeout=60,
            allow_redirects=True,
            headers={"Referer": referer, "Content-Type": "application/x-www-form-urlencoded"},
        )
        return r, None
    except requests.RequestException as ex:
        return None, f"{type(ex).__name__}: {ex}"


def extract_pdf_text(data: bytes, max_pages: int = 40):
    try:
        reader = PdfReader(io.BytesIO(data))
        parts = []
        for page in reader.pages[:max_pages]:
            try:
                parts.append(page.extract_text() or "")
            except Exception as ex:
                parts.append(f"\n[PAGE_EXTRACT_ERROR:{type(ex).__name__}]\n")
        return "\n".join(parts), len(reader.pages), None
    except Exception as ex:
        return "", None, f"{type(ex).__name__}: {ex}"


def main():
    print("=" * 78)
    print("E-GAZETTE EXACT CANDIDATE DOWNLOAD REPLAY - S221O")
    print("=" * 78)
    print("Purpose: replay official UI download POST contract for the recovered candidate only")
    print("Download/body signal != official designation identity")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s221n = json.loads(S221N.read_text(encoding="utf-8"))
    s221j = json.loads(S221J.read_text(encoding="utf-8"))

    summary_n = s221n.get("summary") or {}
    gate_n = (
        summary_n.get("uqq700_final_resolution") == "UNKNOWN"
        and summary_n.get("backend_invocation_performed") is False
        and summary_n.get("arbitrary_endpoint_guessing_performed") is False
        and s221n.get("official_designation_identity_verified") is False
    )
    candidates = s221j.get("raw_candidates") or []
    gate_j = len(candidates) == 1
    if not (gate_n and gate_j):
        raise AssertionError("S221O prerequisite gate not satisfied")

    raw = candidates[0].get("raw_item") or {}
    subject = str(raw.get("stored_field_subject") or "")
    field_url = str(raw.get("stored_field_url") or "")
    toc_id = str(raw.get("stored_toc_seq") or "")
    m = re.search(r"contentId=([^&]+)", field_url)
    content_id = m.group(1) if m else ""
    if not (content_id and toc_id):
        raise AssertionError("S221O recovered content/toc ids missing")

    subject_identity_signal = EXPECTED_NOTICE_PREFIX in subject and EXPECTED_TITLE_FRAGMENT in subject
    detail_url = urljoin(BASE_URL, field_url)
    download_url = urljoin(BASE_URL, DOWNLOAD_PATH)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    detail, detail_error = safe_get(session, detail_url, BASE_URL)
    cookies_after_detail = sorted(session.cookies.keys())

    payload = {"cntnt_seq_no": toc_id}
    download, download_error = safe_post(session, download_url, payload, detail_url)

    status = download.status_code if download is not None else None
    ctype = download.headers.get("Content-Type", "") if download is not None else ""
    cdisp = download.headers.get("Content-Disposition", "") if download is not None else ""
    body = download.content if download is not None else b""
    pdf_signature = body.startswith(b"%PDF-")
    pdf_like = pdf_signature or "application/pdf" in ctype.lower()

    pdf_text = ""
    pdf_pages = None
    pdf_error = None
    if pdf_like and body:
        pdf_text, pdf_pages, pdf_error = extract_pdf_text(body)

    normalized_text = re.sub(r"\s+", "", pdf_text)
    expected_notice_in_body = EXPECTED_NOTICE_PREFIX in normalized_text
    expected_title_in_body = EXPECTED_TITLE_FRAGMENT.replace(" ", "") in normalized_text
    document_identity_signal = subject_identity_signal and (expected_notice_in_body or expected_title_in_body)
    target_hit = TARGET in normalized_text

    download_endpoint_qualified = status == 200 and len(body) > 0 and pdf_like

    if not download_endpoint_qualified:
        classification = "TECHNICAL_UNKNOWN"
    elif target_hit:
        classification = "CANDIDATE_DOCUMENT_BODY_TERM_HIT"
    elif document_identity_signal:
        classification = "CANDIDATE_DOCUMENT_BODY_TERM_NOT_OBSERVED"
    else:
        classification = "DOCUMENT_DOWNLOAD_ENDPOINT_QUALIFIED"

    semantic = {
        "TECHNICAL_UNKNOWN": "E_GAZETTE_CANDIDATE_DOWNLOAD_TECHNICAL_UNKNOWN_WITHOUT_NEGATIVE_INFERENCE",
        "DOCUMENT_DOWNLOAD_ENDPOINT_QUALIFIED": "E_GAZETTE_CANDIDATE_DOWNLOAD_ENDPOINT_QUALIFIED_IDENTITY_PENDING",
        "CANDIDATE_DOCUMENT_BODY_TERM_HIT": "E_GAZETTE_CANDIDATE_DOCUMENT_BODY_TERM_HIT_REQUIRES_CONTEXT_CLASSIFICATION",
        "CANDIDATE_DOCUMENT_BODY_TERM_NOT_OBSERVED": "E_GAZETTE_CANDIDATE_DOCUMENT_BODY_TERM_NOT_OBSERVED_WITHOUT_LEGAL_ABSENCE_INFERENCE",
    }[classification]

    if classification == "CANDIDATE_DOCUMENT_BODY_TERM_HIT":
        next_action = "BUILD_S221P_TARGET_TERM_CONTEXT_CLASSIFICATION_WITHOUT_DESIGNATION_PROMOTION"
    elif classification == "CANDIDATE_DOCUMENT_BODY_TERM_NOT_OBSERVED":
        next_action = "COMPARE_SEARCH_INDEX_HIT_WITH_EXTRACTED_PDF_TEXT_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    elif classification == "DOCUMENT_DOWNLOAD_ENDPOINT_QUALIFIED":
        next_action = "QUALIFY_DOWNLOADED_DOCUMENT_IDENTITY_BEFORE_BODY_INTERPRETATION"
    else:
        next_action = "FORENSIC_DOWNLOAD_RESPONSE_OR_SESSION_REWRITE_CONTRACT_WITHOUT_LEGAL_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-130-S221O",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "candidate": {
            "subject": subject,
            "content_id": content_id,
            "toc_id": toc_id,
            "stored_field_url": field_url,
        },
        "detail": {
            "url": detail_url,
            "http": detail.status_code if detail is not None else None,
            "content_type": detail.headers.get("Content-Type", "") if detail is not None else "",
            "body_bytes": len(detail.content) if detail is not None else 0,
            "error": detail_error,
            "cookies_after_detail": cookies_after_detail,
        },
        "download": {
            "url": download_url,
            "method": "POST",
            "payload": payload,
            "http": status,
            "content_type": ctype,
            "content_disposition": cdisp,
            "body_bytes": len(body),
            "pdf_signature": pdf_signature,
            "pdf_like": pdf_like,
            "error": download_error,
        },
        "pdf": {
            "page_count": pdf_pages,
            "text_length": len(pdf_text),
            "text_error": pdf_error,
            "expected_notice_in_body": expected_notice_in_body,
            "expected_title_in_body": expected_title_in_body,
            "document_identity_signal": document_identity_signal,
            "target_term_hit": target_hit,
            "text_preview": pdf_text[:5000],
        },
        "classification": classification,
        "summary": {
            "subject_identity_signal": subject_identity_signal,
            "download_endpoint_qualified": download_endpoint_qualified,
            "document_body_term_hit": target_hit,
            "term_not_observed_is_negative_evidence": False,
            "document_hit_equals_designation_identity": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "legal_absence": False,
            "semantic_state": semantic,
            "next_action": next_action,
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
    print("SUBJECT IDENTITY SIGNAL:", subject_identity_signal)
    print("DETAIL HTTP:", out["detail"]["http"])
    print("SESSION COOKIES:", cookies_after_detail)
    print("DOWNLOAD URL:", download_url)
    print("DOWNLOAD METHOD: POST")
    print("DOWNLOAD PAYLOAD:", payload)
    print("DOWNLOAD HTTP:", status)
    print("DOWNLOAD CONTENT-TYPE:", ctype)
    print("DOWNLOAD CONTENT-DISPOSITION:", cdisp)
    print("DOWNLOAD BODY BYTES:", len(body))
    print("PDF SIGNATURE:", pdf_signature)
    print("DOWNLOAD ENDPOINT QUALIFIED:", download_endpoint_qualified)
    print("PDF PAGE COUNT:", pdf_pages)
    print("PDF TEXT LENGTH:", len(pdf_text))
    print("PDF TEXT ERROR:", pdf_error)
    print("EXPECTED NOTICE IN BODY:", expected_notice_in_body)
    print("EXPECTED TITLE IN BODY:", expected_title_in_body)
    print("DOCUMENT IDENTITY SIGNAL:", document_identity_signal)
    print("DOCUMENT BODY TERM HIT:", target_hit)
    print("CLASSIFICATION:", classification)

    print("\nPDF TEXT PREVIEW")
    print(pdf_text[:5000])

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221N safe gate": gate_n,
        "S221J candidate gate": gate_j,
        "candidate subject matches recovered identity": subject_identity_signal,
        "content/toc ids recovered": bool(content_id and toc_id),
        "detail GET attempted": detail is not None,
        "official UI download path used": download_url.endswith(DOWNLOAD_PATH),
        "download payload uses recovered toc id": payload.get("cntnt_seq_no") == toc_id,
        "response classified": classification in {"TECHNICAL_UNKNOWN", "DOCUMENT_DOWNLOAD_ENDPOINT_QUALIFIED", "CANDIDATE_DOCUMENT_BODY_TERM_HIT", "CANDIDATE_DOCUMENT_BODY_TERM_NOT_OBSERVED"},
        "term-not-observed not negative evidence": out["summary"]["term_not_observed_is_negative_evidence"] is False,
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
        raise AssertionError("S221O exact candidate download replay failed")


if __name__ == "__main__":
    main()
