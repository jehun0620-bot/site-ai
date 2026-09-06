# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
S221L = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_detail_renderer_delivery_contract_forensic.json"
S221J = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_subject_desc_candidate_identity_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_exact_document_delivery_replay.json"

BASE_URL = "https://www.gwanbo.go.kr/"
TARGET = "개발밀도관리구역"


def get(session: requests.Session, url: str, referer: str | None = None):
    headers = {"Referer": referer} if referer else None
    try:
        r = session.get(url, timeout=60, allow_redirects=True, headers=headers)
        return r, None
    except requests.RequestException as ex:
        return None, f"{type(ex).__name__}: {ex}"


def text(r: requests.Response | None) -> str:
    return r.text if r is not None else ""


def main():
    print("=" * 78)
    print("E-GAZETTE EXACT DOCUMENT DELIVERY REPLAY - S221M")
    print("=" * 78)
    print("Purpose: replay the recovered eZPDF viewer contract only")
    print("No arbitrary .do endpoint guessing")
    print("Document/body hit != official designation identity")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s221l = json.loads(S221L.read_text(encoding="utf-8"))
    s221j = json.loads(S221J.read_text(encoding="utf-8"))

    summary_l = s221l.get("summary") or {}
    gate_l = (
        summary_l.get("uqq700_final_resolution") == "UNKNOWN"
        and summary_l.get("legal_absence_inference_allowed") is False
        and s221l.get("official_designation_identity_verified") is False
    )
    candidates = s221j.get("raw_candidates") or []
    gate_j = len(candidates) == 1
    if not (gate_l and gate_j):
        raise AssertionError("S221M prerequisite gate not satisfied")

    raw = candidates[0].get("raw_item") or {}
    field_url = str(raw.get("stored_field_url") or "")
    toc_id = str(raw.get("stored_toc_seq") or "")
    m = re.search(r"contentId=([^&]+)", field_url)
    content_id = m.group(1) if m else ""
    if not (content_id and toc_id):
        raise AssertionError("S221M recovered content/toc ids missing")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    detail_url = urljoin(BASE_URL, field_url)
    detail, detail_error = get(session, detail_url, BASE_URL)
    detail_html = text(detail)

    # Recover exact viewer.jsp URLs or construction fragments from the live detail HTML.
    viewer_matches = []
    patterns = [
        r"[\"']([^\"']*/ezpdfwebviewer/viewer\.jsp\?[^\"']+)[\"']",
        r"(?:src|href)\s*=\s*[\"']([^\"']*viewer\.jsp[^\"']*)[\"']",
    ]
    for pat in patterns:
        for hit in re.findall(pat, detail_html, flags=re.I):
            hit = hit.replace("&amp;", "&")
            if hit not in viewer_matches:
                viewer_matches.append(hit)

    # Keep only bounded viewer candidates tied to the recovered contract.
    viewer_candidates = []
    for hit in viewer_matches:
        full = urljoin(BASE_URL, hit)
        if "viewer.jsp" in full and full not in viewer_candidates:
            viewer_candidates.append(full)

    # If the detail HTML constructs the URL dynamically, replay only the exact known viewer base
    # with recovered IDs, not guessed backend actions.
    if not viewer_candidates:
        viewer_candidates.append(
            urljoin(
                BASE_URL,
                f"/ezpdfwebviewer/viewer.jsp?optNoUi=true&optLang=ko&timeStampYn=&contentId={content_id}&tocId={toc_id}",
            )
        )

    viewer_candidates = viewer_candidates[:5]
    viewer_attempts = []
    backend_signals = []
    content_signals = []

    for url in viewer_candidates:
        r, err = get(session, url, detail_url)
        body = text(r)
        record = {
            "url": url,
            "http": r.status_code if r is not None else None,
            "final_url": str(r.url) if r is not None else None,
            "content_type": r.headers.get("Content-Type", "") if r is not None else "",
            "body_bytes": len(r.content) if r is not None else 0,
            "error": err,
            "content_id_signal": content_id in body,
            "toc_id_signal": toc_id in body,
            "target_term_hit": TARGET in body,
            "preview": body[:3000],
        }
        viewer_attempts.append(record)

        if r is None or r.status_code != 200:
            continue

        # Recover, but do not invoke, backend/content endpoints exposed by the viewer response.
        for pat in (
            r"[\"']([^\"']*viewer\.yex\.api\.do[^\"']*)[\"']",
            r"[\"']([^\"']*(?:\.pdf|\.png|\.jpg|\.jpeg)(?:\?[^\"']*)?)[\"']",
            r"[\"']([^\"']*(?:text|page|image|download|file)[^\"']*\.do(?:\?[^\"']*)?)[\"']",
        ):
            for hit in re.findall(pat, body, flags=re.I):
                full = urljoin(BASE_URL, hit.replace("&amp;", "&"))
                bucket = backend_signals if ".do" in full else content_signals
                if full not in bucket:
                    bucket.append(full)

    viewer_replay_qualified = any(
        r["http"] == 200 and r["body_bytes"] > 0 for r in viewer_attempts
    )
    backend_contract_recovered = bool(backend_signals)
    content_endpoint_recovered = bool(content_signals)

    if content_endpoint_recovered:
        classification = "DOCUMENT_CONTENT_ENDPOINT_RECOVERED"
    elif backend_contract_recovered:
        classification = "VIEWER_BACKEND_CONTRACT_RECOVERED"
    elif viewer_replay_qualified:
        classification = "VIEWER_REPLAY_QUALIFIED"
    else:
        classification = "TECHNICAL_UNKNOWN"

    semantic = {
        "DOCUMENT_CONTENT_ENDPOINT_RECOVERED": "E_GAZETTE_DOCUMENT_CONTENT_ENDPOINT_RECOVERED_FROM_VIEWER_RESPONSE",
        "VIEWER_BACKEND_CONTRACT_RECOVERED": "E_GAZETTE_VIEWER_BACKEND_CONTRACT_RECOVERED_WITHOUT_INVOCATION",
        "VIEWER_REPLAY_QUALIFIED": "E_GAZETTE_VIEWER_REPLAY_QUALIFIED_BACKEND_PENDING",
        "TECHNICAL_UNKNOWN": "E_GAZETTE_VIEWER_REPLAY_TECHNICAL_UNKNOWN",
    }[classification]

    if classification == "DOCUMENT_CONTENT_ENDPOINT_RECOVERED":
        next_action = "BUILD_S221N_BOUNDED_DOCUMENT_CONTENT_ENDPOINT_REPLAY_FROM_EXACT_RECOVERED_URL"
    elif classification == "VIEWER_BACKEND_CONTRACT_RECOVERED":
        next_action = "BUILD_S221N_EXACT_VIEWER_BACKEND_REQUEST_CONTRACT_FORENSIC_BEFORE_INVOCATION"
    elif classification == "VIEWER_REPLAY_QUALIFIED":
        next_action = "INSPECT_VIEWER_INLINE_SCRIPT_AND_EXTERNAL_JS_FOR_EXACT_BACKEND_REQUEST_PARAMETERS"
    else:
        next_action = "KEEP_TECHNICAL_UNKNOWN_AND_REFINE_VIEWER_URL_CONSTRUCTION_WITHOUT_LEGAL_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-128-S221M",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "input_s221l": str(S221L),
        "input_s221j": str(S221J),
        "candidate": {
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
        },
        "viewer_candidates": viewer_candidates,
        "viewer_attempts": viewer_attempts,
        "backend_signals": backend_signals[:100],
        "content_signals": content_signals[:100],
        "classification": classification,
        "summary": {
            "viewer_replay_qualified": viewer_replay_qualified,
            "viewer_backend_contract_recovered": backend_contract_recovered,
            "document_content_endpoint_recovered": content_endpoint_recovered,
            "semantic_state": semantic,
            "next_action": next_action,
            "arbitrary_do_endpoint_guessing_performed": False,
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

    print("CONTENT ID:", content_id)
    print("TOC ID:", toc_id)
    print("DETAIL HTTP:", out["detail"]["http"])
    print("VIEWER CANDIDATE COUNT:", len(viewer_candidates))
    for i, row in enumerate(viewer_attempts, 1):
        print(
            f"VIEWER[{i}] HTTP={row['http']} type={row['content_type']} "
            f"bytes={row['body_bytes']} contentId={row['content_id_signal']} "
            f"tocId={row['toc_id_signal']} target={row['target_term_hit']} url={row['url']}"
        )
    print("VIEWER REPLAY QUALIFIED:", viewer_replay_qualified)
    print("BACKEND SIGNAL COUNT:", len(backend_signals))
    print("CONTENT ENDPOINT SIGNAL COUNT:", len(content_signals))
    print("CLASSIFICATION:", classification)

    print("\nBACKEND SIGNALS")
    for u in backend_signals[:50]:
        print(u)

    print("\nCONTENT ENDPOINT SIGNALS")
    for u in content_signals[:50]:
        print(u)

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221L safe gate": gate_l,
        "S221J candidate gate": gate_j,
        "content/toc ids recovered": bool(content_id and toc_id),
        "detail replay attempted": out["detail"]["http"] is not None,
        "viewer replay attempted": len(viewer_attempts) > 0,
        "response classified": classification in {"VIEWER_REPLAY_QUALIFIED", "VIEWER_BACKEND_CONTRACT_RECOVERED", "DOCUMENT_CONTENT_ENDPOINT_RECOVERED", "TECHNICAL_UNKNOWN"},
        "arbitrary do guessing disabled": out["summary"]["arbitrary_do_endpoint_guessing_performed"] is False,
        "document hit not designation identity": out["summary"]["document_hit_equals_designation_identity"] is False,
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
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
        raise AssertionError("S221M exact document delivery replay failed")


if __name__ == "__main__":
    main()
