# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_krihs_library_detail_identity_verification.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
LIBRARY_HOST = "library.krihs.re.kr"

DOCUMENTS = [
    {
        "key": "REPORT_2001",
        "url": "https://library.krihs.re.kr/library/10120/contents/6157059",
        "expected_title": "도시성장관리를 위한 개발밀도에 관한 연구",
        "expected_author_tokens": ["박재길", "김의식", "김상조", "문홍길"],
        "expected_date_tokens": ["2001-12-31", "2001.12.31", "2001/12/31"],
    },
    {
        "key": "ARTICLE_2005",
        "url": "https://library.krihs.re.kr/library/10120/contents/5869852?checkinId=2147473&articleId=1400649",
        "expected_title": "주거환경을 고려한 개발밀도론 제시",
        "expected_author_tokens": ["남진"],
        "expected_date_tokens": ["2005-11-15", "2005.11.15", "2005/11/15"],
    },
    {
        "key": "BRIEF_842",
        "url": "https://library.krihs.re.kr/library/10120/contents/6585922",
        "expected_title": "도시개발밀도 관리를 위한 공간 관리방안",
        "expected_author_tokens": [],
        "expected_date_tokens": ["2024-06-03", "2024.06.03", "2024/06/03"],
    },
]


def normalize_space(value: str):
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def strip_tags(value: str):
    return normalize_space(re.sub(r"<[^>]+>", " ", value or ""))


def extract_page_title(html: str):
    m = re.search(r'<title[^>]*>(.*?)</title>', html or "", flags=re.I | re.S)
    return strip_tags(m.group(1))[:1000] if m else None


def extract_meta(html: str):
    rows = []
    for m in re.finditer(r'<meta\b([^>]*)>', html or "", flags=re.I | re.S):
        tag = m.group(1)
        name = None
        content = None
        for am in re.finditer(r'([:\w-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', tag, flags=re.I | re.S):
            attr_name = am.group(1).lower()
            attr_value = next((g for g in am.groups()[1:] if g is not None), "")
            attr_value = unescape(attr_value)
            if attr_name in {"name", "property"}:
                name = attr_value
            elif attr_name == "content":
                content = attr_value
        if name or content:
            rows.append({"name": name, "content": content})
    return rows[:200]


def compact_text(html: str):
    text = re.sub(r'<script\b.*?</script>', ' ', html or '', flags=re.I | re.S)
    text = re.sub(r'<style\b.*?</style>', ' ', text, flags=re.I | re.S)
    return strip_tags(text)


def contains_any(text: str, tokens: list[str]):
    return any(token and token in text for token in tokens)


def verify_document(session: requests.Session, doc: dict):
    row = {
        "key": doc["key"],
        "requested_url": doc["url"],
        "requested_host": urlparse(doc["url"]).netloc,
        "http": None,
        "final_url": None,
        "final_host": None,
        "content_type": None,
        "page_title": None,
        "expected_title": doc["expected_title"],
        "title_present": False,
        "author_tokens": doc["expected_author_tokens"],
        "author_signal_present": False,
        "date_tokens": doc["expected_date_tokens"],
        "date_signal_present": False,
        "identity_signal_count": 0,
        "document_identity_verified": False,
        "meta": [],
        "text_preview": None,
        "technical_unknown": True,
        "error": None,
    }

    if row["requested_host"] != LIBRARY_HOST:
        row["error"] = f"Unexpected requested host: {row['requested_host']}"
        return row

    try:
        response = session.get(doc["url"], timeout=30, allow_redirects=True)
        response.raise_for_status()
        html = response.text or ""
        text = compact_text(html)
        page_title = extract_page_title(html)
        final_host = urlparse(response.url).netloc

        title_present = doc["expected_title"] in text or (page_title and doc["expected_title"] in page_title)
        author_present = True if not doc["expected_author_tokens"] else contains_any(text, doc["expected_author_tokens"])
        date_present = contains_any(text, doc["expected_date_tokens"])
        signal_count = sum([bool(title_present), bool(author_present), bool(date_present)])
        identity_verified = bool(
            response.status_code == 200
            and final_host == LIBRARY_HOST
            and title_present
            and signal_count >= 2
        )

        row.update({
            "http": response.status_code,
            "final_url": response.url,
            "final_host": final_host,
            "content_type": response.headers.get("Content-Type"),
            "page_title": page_title,
            "title_present": bool(title_present),
            "author_signal_present": bool(author_present),
            "date_signal_present": bool(date_present),
            "identity_signal_count": signal_count,
            "document_identity_verified": identity_verified,
            "meta": extract_meta(html),
            "text_preview": text[:5000],
            "technical_unknown": False,
        })
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def main():
    print("=" * 78)
    print("KRIHS LIBRARY DETAIL IDENTITY VERIFICATION")
    print("=" * 78)
    print("Purpose: verify three recovered library.krihs.re.kr detail URLs against observed publication identities")
    print("Publication document identity != designation/current validity/site inclusion")
    print("Failed publication identity != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; site-ai STEP17 KRIHS library detail identity verification)",
        "Referer": "https://www.krihs.re.kr/",
    })

    rows = [verify_document(session, doc) for doc in DOCUMENTS]
    technical_unknown_count = sum(1 for row in rows if row["technical_unknown"] is True)
    verified_count = sum(1 for row in rows if row["document_identity_verified"] is True)

    if technical_unknown_count:
        classification = "KRIHS_LIBRARY_DETAIL_IDENTITY_VERIFICATION_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_ONLY_KRIHS_LIBRARY_DETAIL_TRANSPORT_OR_PARSING_WITHOUT_LEGAL_INFERENCE"
    elif verified_count == len(rows):
        classification = "KRIHS_LIBRARY_THREE_PUBLICATION_IDENTITIES_VERIFIED"
        next_action = "USE_ONLY_AS_NON_DISPOSITIVE_CONTEXT_LEADS_AND_RETURN_TO_OFFICIAL_DESIGNATION_SOURCE_DISCOVERY"
    elif verified_count > 0:
        classification = "KRIHS_LIBRARY_PARTIAL_PUBLICATION_IDENTITY_VERIFICATION"
        next_action = "REVIEW_ONLY_UNVERIFIED_LIBRARY_DETAIL_IDENTITIES_WITHOUT_PROMOTION_OR_NEGATIVE_EVIDENCE"
    else:
        classification = "KRIHS_LIBRARY_PUBLICATION_IDENTITY_NOT_VERIFIED"
        next_action = "INSPECT_LIBRARY_DETAIL_RENDERING_OR_METADATA_WITHOUT_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP 17-KRIHS-LIBRARY-DETAIL-IDENTITY-VERIFICATION",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "library_host": LIBRARY_HOST,
        "document_count": len(rows),
        "verified_document_identity_count": verified_count,
        "technical_unknown_count": technical_unknown_count,
        "documents": rows,
        "classification": classification,
        "summary": {
            "next_action": next_action,
            "publication_identity_equals_designation": False,
            "publication_identity_equals_current_validity": False,
            "publication_identity_equals_site_inclusion": False,
            "failed_publication_identity_equals_legal_absence": False,
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

    print("\n" + "=" * 78)
    print("DETAIL IDENTITY RESULT")
    print("=" * 78)
    for row in rows:
        print(
            f'{row["key"]}: http={row["http"]} final_host={row["final_host"]!r} '
            f'title_present={row["title_present"]} author={row["author_signal_present"]} '
            f'date={row["date_signal_present"]} signals={row["identity_signal_count"]} '
            f'identity_verified={row["document_identity_verified"]} technical_unknown={row["technical_unknown"]}'
        )
        print(f'    final={row["final_url"]}')
        print(f'    page_title={row["page_title"]!r}')
        if row["error"]:
            print(f'    error={row["error"]}')

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print("Publication identity == designation: False")
    print("Publication identity == current validity: False")
    print("Publication identity == site inclusion: False")
    print("Failed publication identity == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "library host fixed": out["library_host"] == LIBRARY_HOST,
        "three recovered detail URLs fixed": out["document_count"] == 3,
        "technical state explicit": all("technical_unknown" in row for row in out["documents"]),
        "publication identity not designation": out["summary"]["publication_identity_equals_designation"] is False,
        "publication identity not validity": out["summary"]["publication_identity_equals_current_validity"] is False,
        "publication identity not site inclusion": out["summary"]["publication_identity_equals_site_inclusion"] is False,
        "failed identity not legal absence": out["summary"]["failed_publication_identity_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "validity not promoted": out["summary"]["current_validity_verified"] is False,
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
        raise AssertionError("KRIHS library detail identity verification validation failed")


if __name__ == "__main__":
    main()
