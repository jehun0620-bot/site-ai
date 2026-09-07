# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
PRIOR_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_canonical_attachment_uqq700_content_scan.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_uqq700_weak_hit_context_identity_review.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
WEAK_TERM = "개발밀도"
CONTEXT_RADIUS = 220
MAX_CONTEXTS_PER_DOC = 30

NOTICE_PATTERNS = [
    re.compile(r"(?:성남시|경기도|국토교통부|건설교통부|국토해양부|국토건설청)?\s*고시\s*제?\s*\d{4}\s*[-–—]\s*\d+\s*호?"),
    re.compile(r"(?:성남시|경기도|국토교통부|건설교통부|국토해양부|국토건설청)?\s*공고\s*제?\s*\d{4}\s*[-–—]\s*\d+\s*호?"),
]
DESIGNATION_TERMS = ["지정", "지정ㆍ변경", "지정·변경", "변경지정", "고시", "개발밀도관리구역"]
LAW_TERMS = ["국토의 계획 및 이용에 관한 법률", "국토계획법", "제66조", "66조"]


def curl_bytes(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "content_type": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "120",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{content_type}",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 1)
        http = parts[0] if parts else None
        content_type = parts[1] if len(parts) > 1 else None
    else:
        body, http, content_type = raw, None, None
    return {
        "http": http,
        "content_type": content_type,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def extract_pdf_pages(body: bytes) -> tuple[list[str] | None, str | None]:
    try:
        from pypdf import PdfReader
    except Exception as e:
        return None, f"IMPORT_ERROR: {type(e).__name__}: {e}"
    try:
        reader = PdfReader(io.BytesIO(body))
        pages = []
        for i, page in enumerate(reader.pages):
            try:
                pages.append(page.extract_text() or "")
            except Exception as e:
                return None, f"PAGE_{i+1}_EXTRACTION_ERROR: {type(e).__name__}: {e}"
        return pages, None
    except Exception as e:
        return None, f"PDF_PARSE_ERROR: {type(e).__name__}: {e}"


def compact(text: str) -> str:
    return " ".join((text or "").split())


def find_notice_candidates(text: str) -> list[str]:
    hits = []
    seen = set()
    for pat in NOTICE_PATTERNS:
        for m in pat.finditer(text or ""):
            v = compact(m.group(0))
            if v and v not in seen:
                seen.add(v)
                hits.append(v)
    return hits


def classify_context(context: str, notice_candidates: list[str]) -> tuple[str, dict]:
    exact_target = TARGET in context
    designation_hits = [t for t in DESIGNATION_TERMS if t in context]
    law_hits = [t for t in LAW_TERMS if t in context]
    has_notice = bool(notice_candidates)
    has_designation_word = any(t in context for t in ["지정", "지정ㆍ변경", "지정·변경", "변경지정"])
    has_gosi = "고시" in context

    if has_notice and (exact_target or (has_designation_word and WEAK_TERM in context)):
        cls = "POSSIBLE_NOTICE_IDENTITY_CONTEXT"
    elif exact_target and (has_designation_word or has_gosi):
        cls = "POSSIBLE_DESIGNATION_CONTEXT"
    elif exact_target or law_hits:
        cls = "DEVELOPMENT_DENSITY_MANAGEMENT_SYSTEM_CONTEXT"
    else:
        cls = "GENERAL_DENSITY_POLICY_CONTEXT"
    return cls, {
        "exact_target_visible": exact_target,
        "designation_terms": designation_hits,
        "law_terms": law_hits,
        "notice_candidates": notice_candidates,
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT UQQ700 WEAK-HIT CONTEXT + NOTICE IDENTITY REVIEW - S227E")
    print("=" * 78)
    print("Purpose: review only S227D weak-hit PDFs and extract context/notice candidates")
    print("Technical unknown attachments: PRESERVED, NOT RESOLVED HERE")
    print("OCR: NOT EXECUTED")
    print("Context/notice candidate != designation/current validity/site inclusion")
    print("UQQ700 final resolution: UNKNOWN")

    if not PRIOR_OUT.exists():
        raise FileNotFoundError(f"Required S227D output not found: {PRIOR_OUT}")
    prior = json.loads(PRIOR_OUT.read_text(encoding="utf-8"))
    weak_rows = [r for r in (prior.get("results") or []) if r.get("status") == "WEAK_CONTENT_HIT" and r.get("extension") == "pdf"]
    prior_technical_unknown = int(prior.get("technical_unknown_count") or 0)

    reviews = []
    context_class_counts = Counter()
    review_technical_unknown = 0
    total_contexts = 0
    possible_notice_contexts = []
    possible_designation_contexts = []

    for idx, row in enumerate(weak_rows, 1):
        url = row.get("download_url")
        dl = curl_bytes(url) if url else {"http": None, "body": b"", "content_type": None, "stderr": "missing url"}
        review = {
            "pstSn": row.get("pstSn"),
            "fileNo": row.get("fileNo"),
            "name": row.get("name"),
            "download_url": url,
            "download_http": dl.get("http"),
            "content_type": dl.get("content_type"),
            "page_count": 0,
            "context_count": 0,
            "contexts": [],
            "review_status": None,
            "error": None,
        }
        if dl.get("http") != "200" or not dl.get("body"):
            review["review_status"] = "TECHNICAL_UNKNOWN"
            review["error"] = "DOWNLOAD_FAILED"
            review_technical_unknown += 1
            reviews.append(review)
            continue

        pages, err = extract_pdf_pages(dl["body"])
        if pages is None:
            review["review_status"] = "TECHNICAL_UNKNOWN"
            review["error"] = err
            review_technical_unknown += 1
            reviews.append(review)
            continue

        review["page_count"] = len(pages)
        contexts = []
        for page_no, text in enumerate(pages, 1):
            start = 0
            while True:
                pos = text.find(WEAK_TERM, start)
                if pos < 0:
                    break
                left = max(0, pos - CONTEXT_RADIUS)
                right = min(len(text), pos + len(WEAK_TERM) + CONTEXT_RADIUS)
                raw_context = text[left:right]
                context = compact(raw_context)
                notices = find_notice_candidates(context)
                cls, signals = classify_context(context, notices)
                item = {
                    "page": page_no,
                    "match_term": WEAK_TERM,
                    "context": context,
                    "context_class": cls,
                    **signals,
                }
                contexts.append(item)
                context_class_counts[cls] += 1
                total_contexts += 1
                if cls == "POSSIBLE_NOTICE_IDENTITY_CONTEXT":
                    possible_notice_contexts.append({"pstSn": row.get("pstSn"), "fileNo": row.get("fileNo"), "name": row.get("name"), **item})
                elif cls == "POSSIBLE_DESIGNATION_CONTEXT":
                    possible_designation_contexts.append({"pstSn": row.get("pstSn"), "fileNo": row.get("fileNo"), "name": row.get("name"), **item})
                if len(contexts) >= MAX_CONTEXTS_PER_DOC:
                    break
                start = pos + len(WEAK_TERM)
            if len(contexts) >= MAX_CONTEXTS_PER_DOC:
                break

        review["contexts"] = contexts
        review["context_count"] = len(contexts)
        review["review_status"] = "REVIEWED" if contexts else "TECHNICAL_UNKNOWN"
        if not contexts:
            review["error"] = "WEAK_TERM_NOT_REPRODUCED_ON_RESCAN"
            review_technical_unknown += 1
        reviews.append(review)
        print(f"REVIEW PROGRESS: {idx}/{len(weak_rows)} | PSTSN={row.get('pstSn')} | CONTEXTS={len(contexts)}")

    notice_identity_candidate_count = len(possible_notice_contexts)
    designation_context_candidate_count = len(possible_designation_contexts)
    review_complete = len(weak_rows) > 0 and review_technical_unknown == 0 and all(r.get("review_status") == "REVIEWED" for r in reviews)

    if notice_identity_candidate_count > 0:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_WEAK_HIT_POSSIBLE_NOTICE_IDENTITY_CONTEXT_OBSERVED"
        semantic = "ONE_OR_MORE_WEAK_HIT_CONTEXTS_CONTAIN_NOTICE_IDENTITY_LIKE_AND_DESIGNATION_RELATED_SIGNALS_REQUIRING_OFFICIAL_NOTICE_TRACE"
        next_action = "TRACE_ONLY_EXTRACTED_NOTICE_IDENTITY_CANDIDATES_TO_OFFICIAL_NOTICE_SURFACE_WITHOUT_PROMOTING_PLANNING_DOCUMENT_CONTEXT"
    elif designation_context_candidate_count > 0:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_WEAK_HIT_POSSIBLE_DESIGNATION_CONTEXT_OBSERVED"
        semantic = "DESIGNATION_RELATED_CONTEXT_OBSERVED_WITHOUT_QUALIFIED_NOTICE_IDENTITY"
        next_action = "REVIEW_DESIGNATION_CONTEXT_FOR_LITERAL_NOTICE_NUMBER_OR_REVERSE_LOOKUP_KEYS_NON_PROMOTIONALLY"
    elif review_complete:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_WEAK_HIT_CONTEXT_REVIEWED_NO_NOTICE_IDENTITY_CANDIDATE"
        semantic = "ALL_WEAK_HIT_CONTEXTS_REVIEWED_AS_GENERAL_OR_SYSTEM_CONTEXT_WITH_NO_NOTICE_IDENTITY_CANDIDATE"
        next_action = "RETURN_TO_S227D_TECHNICAL_UNKNOWN_ATTACHMENT_HARDENING_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_WEAK_HIT_CONTEXT_REVIEW_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_MORE_WEAK_HIT_DOCUMENTS_COULD_NOT_BE_REVIEWED_RELIABLY"
        next_action = "HARDEN_ONLY_WEAK_HIT_REVIEW_FAILURES_BEFORE_ANY_SOURCE_FAMILY_RECONCILIATION"

    out = {
        "step": "STEP 17-21-C-16-8-T-151-S227E",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prior_input_exists": PRIOR_OUT.exists(),
        "weak_hit_document_count": len(weak_rows),
        "prior_technical_unknown_count": prior_technical_unknown,
        "review_technical_unknown_count": review_technical_unknown,
        "total_context_count": total_contexts,
        "context_class_counts": dict(context_class_counts),
        "possible_notice_identity_context_count": notice_identity_candidate_count,
        "possible_designation_context_count": designation_context_candidate_count,
        "review_complete": review_complete,
        "reviews": reviews,
        "possible_notice_identity_contexts": possible_notice_contexts,
        "possible_designation_contexts": possible_designation_contexts,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "weak_context_hit_equals_designation_notice": False,
            "notice_candidate_equals_verified_notice_identity": False,
            "weak_context_hit_equals_current_validity": False,
            "weak_context_hit_equals_site_inclusion": False,
            "weak_context_no_notice_equals_legal_absence": False,
            "prior_technical_unknown_preserved": prior_technical_unknown,
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

    print("\nWEAK-HIT CONTEXT REVIEW SUMMARY")
    print("-" * 78)
    print(f"WEAK HIT DOCUMENT COUNT: {len(weak_rows)}")
    print(f"TOTAL CONTEXT COUNT: {total_contexts}")
    print(f"CONTEXT CLASS COUNTS: {dict(context_class_counts)}")
    print(f"POSSIBLE NOTICE IDENTITY CONTEXT COUNT: {notice_identity_candidate_count}")
    print(f"POSSIBLE DESIGNATION CONTEXT COUNT: {designation_context_candidate_count}")
    print(f"REVIEW TECHNICAL UNKNOWN COUNT: {review_technical_unknown}")
    print(f"PRIOR S227D TECHNICAL UNKNOWN PRESERVED: {prior_technical_unknown}")

    print("\nCONTEXTS")
    print("-" * 78)
    for review in reviews:
        print(f"PSTSN={review['pstSn']} FILENO={review['fileNo']} NAME={review['name']} STATUS={review['review_status']}")
        for ctx in review.get("contexts", [])[:10]:
            print(f"  PAGE={ctx['page']} CLASS={ctx['context_class']}")
            print(f"  NOTICE={ctx['notice_candidates']}")
            print(f"  DESIGNATION={ctx['designation_terms']} LAW={ctx['law_terms']} EXACT={ctx['exact_target_visible']}")
            print(f"  CONTEXT={ctx['context']}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"REVIEW COMPLETE: {review_complete}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Weak context hit == designation/current validity/site inclusion: False")
    print("Notice candidate == verified notice identity: False")
    print("Weak context no-notice == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S227D input exists": PRIOR_OUT.exists(),
        "weak-hit documents present": len(weak_rows) > 0,
        "weak context not designation": out["summary"]["weak_context_hit_equals_designation_notice"] is False,
        "notice candidate not verified identity": out["summary"]["notice_candidate_equals_verified_notice_identity"] is False,
        "weak context not validity": out["summary"]["weak_context_hit_equals_current_validity"] is False,
        "weak context not site inclusion": out["summary"]["weak_context_hit_equals_site_inclusion"] is False,
        "weak no-notice not legal absence": out["summary"]["weak_context_no_notice_equals_legal_absence"] is False,
        "prior technical unknown preserved": out["summary"]["prior_technical_unknown_preserved"] == prior_technical_unknown,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_WEAK_HIT_POSSIBLE_NOTICE_IDENTITY_CONTEXT_OBSERVED",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_WEAK_HIT_POSSIBLE_DESIGNATION_CONTEXT_OBSERVED",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_WEAK_HIT_CONTEXT_REVIEWED_NO_NOTICE_IDENTITY_CANDIDATE",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_WEAK_HIT_CONTEXT_REVIEW_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S227E validation failed")


if __name__ == "__main__":
    main()
