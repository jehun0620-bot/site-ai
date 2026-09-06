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
S221P = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_index_pdf_mismatch_forensic.json"
S221J = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_subject_desc_candidate_identity_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_pdf_term_context_classification.json"

BASE_URL = "https://www.gwanbo.go.kr/"
TARGET = "개발밀도관리구역"
DOWNLOAD_PATH = "/user/common/ofcttCntntDownload.do"

POLICY_SIGNALS = ["규제일몰", "재검토형", "효력상실형", "규제명", "규제내용", "주기", "국토해양부"]
LEGAL_SIGNALS = ["국토의계획및이용에관한법률", "제66조", "제62조", "제63조"]
DESIGNATION_SIGNALS = ["지정", "도시관리계획", "지형도면", "성남시", "경계", "면적", "위치", "고시번호"]


def compact(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


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


def extract_pdf_pages(data: bytes):
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = []
        errors = []
        for i, page in enumerate(reader.pages, 1):
            try:
                pages.append(page.extract_text() or "")
            except Exception as ex:
                pages.append("")
                errors.append({"page": i, "error": f"{type(ex).__name__}: {ex}"})
        return pages, errors, None
    except Exception as ex:
        return [], [], f"{type(ex).__name__}: {ex}"


def contexts_for_page(text: str, term: str, radius: int = 350):
    out = []
    start = 0
    while True:
        idx = text.find(term, start)
        if idx < 0:
            break
        out.append(text[max(0, idx - radius): min(len(text), idx + len(term) + radius)])
        start = idx + len(term)
    return out


def main():
    print("=" * 78)
    print("E-GAZETTE PDF TERM CONTEXT CLASSIFICATION - S221Q")
    print("=" * 78)
    print("Purpose: classify the verified UQQ700 term context in the recovered PDF")
    print("Term/context hit != official designation identity")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s221p = json.loads(S221P.read_text(encoding="utf-8"))
    s221j = json.loads(S221J.read_text(encoding="utf-8"))

    gate_p = (
        s221p.get("classification") == "PDF_TEXT_NORMALIZATION_TERM_HIT"
        and (s221p.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
        and s221p.get("official_designation_identity_verified") is False
    )
    candidates = s221j.get("raw_candidates") or []
    gate_j = len(candidates) == 1
    if not (gate_p and gate_j):
        raise AssertionError("S221Q prerequisite gate not satisfied")

    raw = candidates[0].get("raw_item") or {}
    field_url = str(raw.get("stored_field_url") or "")
    toc_id = str(raw.get("stored_toc_seq") or "")
    m = re.search(r"contentId=([^&]+)", field_url)
    content_id = m.group(1) if m else ""
    if not (content_id and toc_id):
        raise AssertionError("Recovered content/toc ids missing")

    detail_url = urljoin(BASE_URL, field_url)
    download_url = urljoin(BASE_URL, DOWNLOAD_PATH)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    detail, detail_error = safe_get(session, detail_url, BASE_URL)
    download, download_error = safe_post(session, download_url, {"cntnt_seq_no": toc_id}, detail_url)
    body = download.content if download is not None else b""
    pdf_signature = body.startswith(b"%PDF-")
    pages, page_errors, pdf_error = extract_pdf_pages(body) if pdf_signature else ([], [], None)

    occurrences = []
    for page_no, text in enumerate(pages, 1):
        for ctx in contexts_for_page(text, TARGET):
            compact_ctx = compact(ctx)
            policy_hits = [s for s in POLICY_SIGNALS if compact(s) in compact_ctx]
            legal_hits = [s for s in LEGAL_SIGNALS if compact(s) in compact_ctx]
            designation_hits = [s for s in DESIGNATION_SIGNALS if compact(s) in compact_ctx]
            occurrences.append({
                "page": page_no,
                "context": ctx,
                "policy_hits": policy_hits,
                "legal_hits": legal_hits,
                "designation_hits": designation_hits,
            })

    occurrence_count = len(occurrences)
    strong_policy_context = any(len(o["policy_hits"]) >= 2 and len(o["legal_hits"]) >= 1 for o in occurrences)
    local_designation_signal = any(
        "성남시" in o["designation_hits"] and any(x in o["designation_hits"] for x in ["지정", "도시관리계획", "지형도면", "경계", "면적", "위치"])
        for o in occurrences
    )
    generic_designation_word_only = any(o["designation_hits"] for o in occurrences) and not local_designation_signal

    if occurrence_count == 0:
        classification = "TECHNICAL_UNKNOWN"
    elif local_designation_signal:
        classification = "DESIGNATION_CONTEXT_SIGNAL"
    elif strong_policy_context:
        classification = "NATIONAL_REGULATORY_POLICY_LIST_CONTEXT"
    elif generic_designation_word_only:
        classification = "AMBIGUOUS_LEGAL_CONTEXT"
    else:
        classification = "AMBIGUOUS_LEGAL_CONTEXT"

    semantic = {
        "NATIONAL_REGULATORY_POLICY_LIST_CONTEXT": "E_GAZETTE_UQQ700_TERM_VERIFIED_AS_NATIONAL_REGULATORY_POLICY_LIST_CONTEXT_NOT_LOCAL_DESIGNATION",
        "DESIGNATION_CONTEXT_SIGNAL": "E_GAZETTE_UQQ700_TERM_HAS_DESIGNATION_CONTEXT_SIGNAL_REQUIRES_SEPARATE_IDENTITY_QUALIFICATION",
        "AMBIGUOUS_LEGAL_CONTEXT": "E_GAZETTE_UQQ700_TERM_CONTEXT_AMBIGUOUS_WITHOUT_DESIGNATION_PROMOTION",
        "TECHNICAL_UNKNOWN": "E_GAZETTE_UQQ700_TERM_CONTEXT_TECHNICAL_UNKNOWN",
    }[classification]

    if classification == "NATIONAL_REGULATORY_POLICY_LIST_CONTEXT":
        next_action = "RETAIN_AS_HISTORICAL_LEGAL_CONTEXT_EXCLUDE_FROM_DESIGNATION_CANDIDATES_AND_REVIEW_E_GAZETTE_QUERY_SCOPE"
    elif classification == "DESIGNATION_CONTEXT_SIGNAL":
        next_action = "QUALIFY_DESIGNATION_DOCUMENT_IDENTITY_BEFORE_ANY_LEGAL_OR_SITE_PROMOTION"
    elif classification == "AMBIGUOUS_LEGAL_CONTEXT":
        next_action = "NARROW_TERM_CONTEXT_WITH_ADJACENT_ROWS_AND_DOCUMENT_STRUCTURE_ONLY"
    else:
        next_action = "KEEP_TECHNICAL_UNKNOWN_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-132-S221Q",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "candidate": {
            "subject": raw.get("stored_field_subject"),
            "content_id": content_id,
            "toc_id": toc_id,
        },
        "replay": {
            "detail_http": detail.status_code if detail is not None else None,
            "detail_error": detail_error,
            "download_http": download.status_code if download is not None else None,
            "download_error": download_error,
            "pdf_signature": pdf_signature,
            "pdf_page_count": len(pages),
            "page_extract_errors": page_errors,
            "pdf_error": pdf_error,
        },
        "occurrence_count": occurrence_count,
        "occurrences": occurrences,
        "signals": {
            "strong_policy_context": strong_policy_context,
            "local_designation_signal": local_designation_signal,
            "generic_designation_word_only": generic_designation_word_only,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "term_identity_verified": occurrence_count > 0,
            "document_identity_verified": True,
            "historical_legal_context_verified": classification == "NATIONAL_REGULATORY_POLICY_LIST_CONTEXT",
            "designation_candidate_excluded": classification == "NATIONAL_REGULATORY_POLICY_LIST_CONTEXT",
            "official_designation_identity_verified": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
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

    print("CONTENT ID:", content_id)
    print("TOC ID:", toc_id)
    print("DETAIL HTTP:", out["replay"]["detail_http"])
    print("DOWNLOAD HTTP:", out["replay"]["download_http"])
    print("PDF SIGNATURE:", pdf_signature)
    print("PDF PAGE COUNT:", len(pages))
    print("PDF ERROR:", pdf_error)
    print("TERM OCCURRENCE COUNT:", occurrence_count)
    print("STRONG POLICY CONTEXT:", strong_policy_context)
    print("LOCAL DESIGNATION SIGNAL:", local_designation_signal)
    print("GENERIC DESIGNATION WORD ONLY:", generic_designation_word_only)
    print("CLASSIFICATION:", classification)

    print("\nTERM CONTEXTS")
    for i, occ in enumerate(occurrences, 1):
        print(f"--- OCCURRENCE {i} / PAGE {occ['page']} ---")
        print("POLICY HITS:", occ["policy_hits"])
        print("LEGAL HITS:", occ["legal_hits"])
        print("DESIGNATION HITS:", occ["designation_hits"])
        print(occ["context"])

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221P term-hit gate": gate_p,
        "S221J candidate gate": gate_j,
        "content/toc ids recovered": bool(content_id and toc_id),
        "official PDF replay attempted": download is not None,
        "verified PDF recovered": pdf_signature,
        "all PDF pages processed": len(pages) > 0 and not pdf_error,
        "term occurrence recovered": occurrence_count > 0,
        "response classified": classification in {"NATIONAL_REGULATORY_POLICY_LIST_CONTEXT", "DESIGNATION_CONTEXT_SIGNAL", "AMBIGUOUS_LEGAL_CONTEXT", "TECHNICAL_UNKNOWN"},
        "designation identity not promoted": out["official_designation_identity_verified"] is False,
        "current validity not promoted": out["current_validity_verified"] is False,
        "site inclusion not promoted": out["site_spatial_inclusion_verified"] is False,
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "SITE FALSE inference disabled": not out["summary"]["site_false_inference_allowed"],
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
        raise AssertionError("S221Q PDF term context classification failed")


if __name__ == "__main__":
    main()
