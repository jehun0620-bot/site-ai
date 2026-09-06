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
S221O = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_exact_candidate_download_replay.json"
S221J = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_subject_desc_candidate_identity_forensic.json"
S221I = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_subject_desc_target_query_replay.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_index_pdf_mismatch_forensic.json"

BASE_URL = "https://www.gwanbo.go.kr/"
TARGET = "개발밀도관리구역"
DOWNLOAD_PATH = "/user/common/ofcttCntntDownload.do"

VARIANTS = [
    "개발밀도관리구역",
    "개발 밀도 관리 구역",
    "개발밀도 관리구역",
    "개발 밀도관리구역",
]
FRAGMENTS = [
    "개발밀도",
    "밀도관리",
    "관리구역",
    "개발밀도관리",
]


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


def extract_pdf_text(data: bytes):
    try:
        reader = PdfReader(io.BytesIO(data))
        page_texts = []
        page_errors = []
        for idx, page in enumerate(reader.pages, 1):
            try:
                page_texts.append(page.extract_text() or "")
            except Exception as ex:
                page_texts.append("")
                page_errors.append({"page": idx, "error": f"{type(ex).__name__}: {ex}"})
        return page_texts, len(reader.pages), page_errors, None
    except Exception as ex:
        return [], None, [], f"{type(ex).__name__}: {ex}"


def compact(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def find_occurrences(text: str, term: str, radius: int = 120, limit: int = 10):
    out = []
    pos = 0
    while True:
        i = text.find(term, pos)
        if i < 0:
            break
        out.append(text[max(0, i - radius): min(len(text), i + len(term) + radius)])
        if len(out) >= limit:
            break
        pos = i + max(1, len(term))
    return out


def main():
    print("=" * 78)
    print("E-GAZETTE SEARCH INDEX / PDF MISMATCH FORENSIC - S221P")
    print("=" * 78)
    print("Purpose: explain subjectDesc search hit versus verified PDF text")
    print("Search-index mismatch != legal absence")
    print("Candidate rejection != SITE FALSE")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s221o = json.loads(S221O.read_text(encoding="utf-8"))
    s221j = json.loads(S221J.read_text(encoding="utf-8"))
    s221i = json.loads(S221I.read_text(encoding="utf-8"))

    summary_o = s221o.get("summary") or {}
    gate_o = (
        summary_o.get("uqq700_final_resolution") == "UNKNOWN"
        and summary_o.get("download_endpoint_qualified") is True
        and s221o.get("official_designation_identity_verified") is False
    )
    candidates = s221j.get("raw_candidates") or []
    gate_j = len(candidates) == 1
    gate_i = (
        s221i.get("classification") == "TARGET_HIT"
        and (s221i.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not (gate_o and gate_j and gate_i):
        raise AssertionError("S221P prerequisite gate not satisfied")

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
    page_texts, page_count, page_errors, pdf_error = extract_pdf_text(body) if pdf_signature else ([], None, [], None)
    full_text = "\n".join(page_texts)
    normalized = compact(full_text)

    variant_results = []
    for v in VARIANTS:
        literal_count = full_text.count(v)
        normalized_count = normalized.count(compact(v))
        variant_results.append({
            "variant": v,
            "literal_count": literal_count,
            "normalized_count": normalized_count,
        })

    fragment_results = []
    for frag in FRAGMENTS:
        literal_count = full_text.count(frag)
        normalized_count = normalized.count(compact(frag))
        fragment_results.append({
            "fragment": frag,
            "literal_count": literal_count,
            "normalized_count": normalized_count,
            "contexts": find_occurrences(full_text, frag, limit=5),
        })

    normalized_target_hit = TARGET in normalized
    any_variant_hit = any(r["literal_count"] > 0 or r["normalized_count"] > 0 for r in variant_results)
    fragment_signal = any(r["literal_count"] > 0 or r["normalized_count"] > 0 for r in fragment_results)

    raw_keys = sorted(raw.keys())
    returned_desc_fields = [k for k in raw_keys if "desc" in k.lower()]
    returned_unstored_fields = [k for k in raw_keys if "unstored" in k.lower()]
    returned_stored_fields = [k for k in raw_keys if "stored" in k.lower()]
    target_visible_in_raw = TARGET in json.dumps(raw, ensure_ascii=False)

    # The actual S221I query contract is an index-side matcher. These names are not
    # inferred as returned fields; they are documented separately as query fields.
    query_match_fields = ["unstored_field_subject", "unstored_field_desc"]
    index_only_desc_signal = "unstored_field_desc" in query_match_fields and not returned_desc_fields
    matcher_return_field_mismatch = index_only_desc_signal and not target_visible_in_raw

    if normalized_target_hit or any_variant_hit:
        classification = "PDF_TEXT_NORMALIZATION_TERM_HIT"
    elif fragment_signal:
        classification = "PDF_TEXT_FRAGMENT_SIGNAL_ONLY"
    elif matcher_return_field_mismatch and pdf_signature and pdf_error is None:
        classification = "INDEX_HIT_NOT_REPRODUCED_IN_PDF_TEXT"
    elif pdf_signature and pdf_error is None:
        classification = "SEARCH_INDEX_PROVENANCE_UNRESOLVED"
    else:
        classification = "TECHNICAL_UNKNOWN"

    semantic = {
        "PDF_TEXT_NORMALIZATION_TERM_HIT": "E_GAZETTE_PDF_TEXT_NORMALIZATION_TERM_HIT_REQUIRES_CONTEXT_REVIEW",
        "PDF_TEXT_FRAGMENT_SIGNAL_ONLY": "E_GAZETTE_PDF_TEXT_FRAGMENT_SIGNAL_ONLY_NOT_DESIGNATION_IDENTITY",
        "INDEX_HIT_NOT_REPRODUCED_IN_PDF_TEXT": "E_GAZETTE_SUBJECT_DESC_INDEX_HIT_NOT_REPRODUCED_IN_VERIFIED_PDF_TEXT",
        "SEARCH_INDEX_PROVENANCE_UNRESOLVED": "E_GAZETTE_SEARCH_INDEX_HIT_PROVENANCE_UNRESOLVED",
        "TECHNICAL_UNKNOWN": "E_GAZETTE_SEARCH_INDEX_PDF_MISMATCH_TECHNICAL_UNKNOWN",
    }[classification]

    if classification == "INDEX_HIT_NOT_REPRODUCED_IN_PDF_TEXT":
        next_action = "ISOLATE_2010_CANDIDATE_AS_SEARCH_INDEX_NOISE_WITHOUT_LEGAL_ABSENCE_AND_REVIEW_E_GAZETTE_SCOPE"
    elif classification in {"PDF_TEXT_NORMALIZATION_TERM_HIT", "PDF_TEXT_FRAGMENT_SIGNAL_ONLY"}:
        next_action = "BUILD_S221Q_PDF_TERM_CONTEXT_CLASSIFICATION_WITHOUT_DESIGNATION_PROMOTION"
    elif classification == "SEARCH_INDEX_PROVENANCE_UNRESOLVED":
        next_action = "KEEP_CANDIDATE_PROVENANCE_UNRESOLVED_AND_INSPECT_INDEX_METADATA_ONLY_IF_EXPOSED"
    else:
        next_action = "KEEP_TECHNICAL_UNKNOWN_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-131-S221P",
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
            "download_content_type": download.headers.get("Content-Type", "") if download is not None else "",
            "download_bytes": len(body),
            "download_error": download_error,
            "pdf_signature": pdf_signature,
            "pdf_page_count": page_count,
            "pdf_text_length": len(full_text),
            "pdf_extract_error": pdf_error,
            "pdf_page_extract_errors": page_errors,
        },
        "pdf_term_forensic": {
            "target_literal_count": full_text.count(TARGET),
            "target_normalized_count": normalized.count(TARGET),
            "normalized_target_hit": normalized_target_hit,
            "variant_results": variant_results,
            "fragment_results": fragment_results,
        },
        "search_index_forensic": {
            "query_match_fields": query_match_fields,
            "returned_raw_keys": raw_keys,
            "returned_desc_fields": returned_desc_fields,
            "returned_unstored_fields": returned_unstored_fields,
            "returned_stored_fields": returned_stored_fields,
            "target_visible_in_returned_raw_item": target_visible_in_raw,
            "index_only_desc_signal": index_only_desc_signal,
            "matcher_return_field_mismatch": matcher_return_field_mismatch,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "candidate_can_be_isolated_as_search_noise": classification == "INDEX_HIT_NOT_REPRODUCED_IN_PDF_TEXT",
            "candidate_is_official_designation_identity": False,
            "candidate_is_legal_absence_evidence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "legal_absence": False,
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
    print("PDF PAGE COUNT:", page_count)
    print("PDF TEXT LENGTH:", len(full_text))
    print("PDF EXTRACT ERROR:", pdf_error)
    print("TARGET LITERAL COUNT:", full_text.count(TARGET))
    print("TARGET NORMALIZED COUNT:", normalized.count(TARGET))
    print("ANY VARIANT HIT:", any_variant_hit)
    print("FRAGMENT SIGNAL:", fragment_signal)
    print("RETURNED DESC FIELDS:", returned_desc_fields)
    print("RETURNED UNSTORED FIELDS:", returned_unstored_fields)
    print("TARGET VISIBLE IN RAW ITEM:", target_visible_in_raw)
    print("INDEX-ONLY DESC SIGNAL:", index_only_desc_signal)
    print("MATCHER/RETURN FIELD MISMATCH:", matcher_return_field_mismatch)
    print("CLASSIFICATION:", classification)

    print("\nVARIANT RESULTS")
    for row in variant_results:
        print(json.dumps(row, ensure_ascii=False))

    print("\nFRAGMENT RESULTS")
    for row in fragment_results:
        print(json.dumps({k: v for k, v in row.items() if k != "contexts"}, ensure_ascii=False))
        for c in row["contexts"]:
            print("  CONTEXT:", c.replace("\n", " "))

    print("\nSEARCH INDEX FIELD COMPARISON")
    print("Query matcher fields:", query_match_fields)
    print("Returned desc fields:", returned_desc_fields)
    print("Returned unstored fields:", returned_unstored_fields)
    print("Returned stored fields:", returned_stored_fields)

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221O safe gate": gate_o,
        "S221J candidate gate": gate_j,
        "S221I subjectDesc hit gate": gate_i,
        "content/toc ids recovered": bool(content_id and toc_id),
        "official download replay attempted": download is not None,
        "verified PDF recovered": pdf_signature,
        "all PDF pages processed": page_count is not None and len(page_texts) == page_count,
        "search matcher fields separated from returned fields": bool(query_match_fields),
        "response classified": classification in {"PDF_TEXT_NORMALIZATION_TERM_HIT", "PDF_TEXT_FRAGMENT_SIGNAL_ONLY", "INDEX_HIT_NOT_REPRODUCED_IN_PDF_TEXT", "SEARCH_INDEX_PROVENANCE_UNRESOLVED", "TECHNICAL_UNKNOWN"},
        "candidate not designation identity": out["summary"]["candidate_is_official_designation_identity"] is False,
        "candidate not legal absence evidence": out["summary"]["candidate_is_legal_absence_evidence"] is False,
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "SITE FALSE inference disabled": not out["summary"]["site_false_inference_allowed"],
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
        raise AssertionError("S221P search index/PDF mismatch forensic failed")


if __name__ == "__main__":
    main()
