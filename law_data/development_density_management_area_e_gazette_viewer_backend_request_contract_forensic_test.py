# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
S221M = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_exact_document_delivery_replay.json"
S221J = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_subject_desc_candidate_identity_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_viewer_backend_request_contract_forensic.json"

BASE_URL = "https://www.gwanbo.go.kr/"
TARGET = "개발밀도관리구역"


def fetch(session: requests.Session, url: str, referer: str | None = None):
    headers = {"Referer": referer} if referer else None
    try:
        r = session.get(url, timeout=60, allow_redirects=True, headers=headers)
        return r, None
    except requests.RequestException as ex:
        return None, f"{type(ex).__name__}: {ex}"


def extract_scripts(html: str, base_url: str):
    srcs = []
    for hit in re.findall(r"<script[^>]+src=[\"']([^\"']+)[\"']", html, flags=re.I):
        full = urljoin(base_url, hit.replace("&amp;", "&"))
        if full not in srcs:
            srcs.append(full)
    return srcs


def contexts(blob: str, needle: str, radius: int = 500, limit: int = 20):
    out = []
    low = blob.lower()
    nlow = needle.lower()
    pos = 0
    while True:
        i = low.find(nlow, pos)
        if i < 0:
            break
        start = max(0, i - radius)
        end = min(len(blob), i + len(needle) + radius)
        frag = blob[start:end]
        if frag not in out:
            out.append(frag)
        if len(out) >= limit:
            break
        pos = i + len(needle)
    return out


def extract_ajax_contracts(blob: str):
    records = []
    for m in re.finditer(r"\$\.ajax\s*\(\s*\{", blob):
        start = m.start()
        end = min(len(blob), start + 3000)
        frag = blob[start:end]
        url_m = re.search(r"url\s*:\s*[\"']([^\"']+)[\"']", frag, flags=re.I)
        type_m = re.search(r"(?:type|method)\s*:\s*[\"']([^\"']+)[\"']", frag, flags=re.I)
        data_m = re.search(r"data\s*:\s*\{([^}]+)\}", frag, flags=re.I | re.S)
        if not url_m:
            continue
        url = url_m.group(1)
        if not any(k in url.lower() for k in ("viewer", "yex", "ezpdf", "download", "file", "page", "text", "image")):
            continue
        params = []
        if data_m:
            for pm in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([^,\n}]+)", data_m.group(1)):
                params.append({"name": pm.group(1), "expr": pm.group(2).strip()[:300]})
        rec = {
            "url": url,
            "method": (type_m.group(1).upper() if type_m else "UNKNOWN"),
            "params": params,
            "context": frag[:2000],
        }
        if rec not in records:
            records.append(rec)
    return records


def extract_url_builders(blob: str):
    patterns = [
        r"viewer\.jsp[^\n;]{0,1000}",
        r"viewer\.yex\.api\.do[^\n;]{0,1000}",
        r"contentId[^\n;]{0,800}",
        r"tocId[^\n;]{0,800}",
        r"reqType[^\n;]{0,800}",
    ]
    out = []
    for pat in patterns:
        for m in re.finditer(pat, blob, flags=re.I):
            frag = blob[max(0, m.start() - 350): min(len(blob), m.end() + 350)]
            if frag not in out:
                out.append(frag)
            if len(out) >= 80:
                return out
    return out


def main():
    print("=" * 78)
    print("E-GAZETTE VIEWER BACKEND REQUEST CONTRACT FORENSIC - S221N")
    print("=" * 78)
    print("Purpose: recover exact viewer/document binding and backend request contract")
    print("Backend invocation: DISABLED")
    print("Arbitrary endpoint guessing: DISABLED")
    print("Document/body hit != official designation identity")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s221m = json.loads(S221M.read_text(encoding="utf-8"))
    s221j = json.loads(S221J.read_text(encoding="utf-8"))

    summary_m = s221m.get("summary") or {}
    gate_m = (
        summary_m.get("uqq700_final_resolution") == "UNKNOWN"
        and summary_m.get("arbitrary_do_endpoint_guessing_performed") is False
        and s221m.get("official_designation_identity_verified") is False
    )
    candidates = s221j.get("raw_candidates") or []
    gate_j = len(candidates) == 1
    if not (gate_m and gate_j):
        raise AssertionError("S221N prerequisite gate not satisfied")

    raw = candidates[0].get("raw_item") or {}
    field_url = str(raw.get("stored_field_url") or "")
    toc_id = str(raw.get("stored_toc_seq") or "")
    m = re.search(r"contentId=([^&]+)", field_url)
    content_id = m.group(1) if m else ""
    if not (content_id and toc_id):
        raise AssertionError("Recovered content/toc ids missing")

    detail_url = urljoin(BASE_URL, field_url)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    detail, detail_error = fetch(session, detail_url, BASE_URL)
    detail_html = detail.text if detail is not None else ""

    # Use only viewer URLs observed in S221M, then inspect their inline/external scripts.
    viewer_urls = []
    for u in s221m.get("viewer_candidates") or []:
        if "viewer.jsp" in str(u) and str(u) not in viewer_urls:
            viewer_urls.append(str(u))
    viewer_urls = viewer_urls[:5]

    sources = [{
        "kind": "detail",
        "url": detail_url,
        "http": detail.status_code if detail is not None else None,
        "error": detail_error,
        "body": detail_html,
    }]

    for u in viewer_urls:
        r, err = fetch(session, u, detail_url)
        sources.append({
            "kind": "viewer",
            "url": u,
            "http": r.status_code if r is not None else None,
            "error": err,
            "body": r.text if r is not None else "",
        })

    js_records = []
    seen_js = set()
    for src in sources:
        for js_url in extract_scripts(src["body"], src["url"]):
            if js_url in seen_js:
                continue
            seen_js.add(js_url)
            jr, jerr = fetch(session, js_url, src["url"])
            body = jr.text if jr is not None else ""
            relevant = any(k.lower() in body.lower() for k in (
                "contentId", "tocId", "viewer.yex.api.do", "viewer.jsp", "reqType", "download"
            ))
            if relevant:
                js_records.append({
                    "url": js_url,
                    "http": jr.status_code if jr is not None else None,
                    "error": jerr,
                    "body": body,
                })

    corpus_records = []
    for src in sources:
        corpus_records.append({"source": src["url"], "kind": src["kind"], "body": src["body"]})
    for js in js_records:
        corpus_records.append({"source": js["url"], "kind": "js", "body": js["body"]})

    binding_contexts = []
    backend_contexts = []
    ajax_contracts = []
    url_builders = []

    for rec in corpus_records:
        body = rec["body"]
        for needle in ("contentId", "tocId", "viewer.jsp", "reqType"):
            for frag in contexts(body, needle, radius=500, limit=12):
                binding_contexts.append({"source": rec["source"], "needle": needle, "context": frag})
        for needle in ("viewer.yex.api.do", "download", "fileDownload"):
            for frag in contexts(body, needle, radius=600, limit=12):
                backend_contexts.append({"source": rec["source"], "needle": needle, "context": frag})
        for c in extract_ajax_contracts(body):
            c["source"] = rec["source"]
            ajax_contracts.append(c)
        for frag in extract_url_builders(body):
            url_builders.append({"source": rec["source"], "context": frag})

    binding_blob = "\n".join(x["context"] for x in binding_contexts)
    backend_blob = "\n".join(x["context"] for x in backend_contexts) + "\n" + "\n".join(x["context"] for x in url_builders)

    content_id_binding_signal = "contentid" in binding_blob.lower()
    toc_id_binding_signal = "tocid" in binding_blob.lower()
    viewer_builder_signal = "viewer.jsp" in binding_blob.lower() or "viewer.jsp" in backend_blob.lower()
    req_type_signal = "reqtype" in binding_blob.lower() or "reqtype" in backend_blob.lower()
    viewer_backend_signal = "viewer.yex.api.do" in backend_blob.lower() or any("viewer.yex.api.do" in c["url"] for c in ajax_contracts)
    method_signal = any(c.get("method") in {"GET", "POST"} for c in ajax_contracts)
    param_names = sorted({p["name"] for c in ajax_contracts for p in c.get("params", [])})
    exact_candidate_id_literal_signal = content_id in "\n".join(r["body"] for r in corpus_records)
    exact_toc_id_literal_signal = toc_id in "\n".join(r["body"] for r in corpus_records)

    document_binding_contract_recovered = content_id_binding_signal and viewer_builder_signal
    backend_request_contract_recovered = viewer_backend_signal and method_signal and bool(param_names)

    if document_binding_contract_recovered and backend_request_contract_recovered:
        classification = "VIEWER_BACKEND_REQUEST_CONTRACT_RECOVERED"
    elif document_binding_contract_recovered:
        classification = "VIEWER_DOCUMENT_BINDING_CONTRACT_RECOVERED"
    elif viewer_builder_signal or viewer_backend_signal or req_type_signal:
        classification = "VIEWER_CONTRACT_PARTIAL"
    else:
        classification = "TECHNICAL_UNKNOWN"

    semantic = {
        "VIEWER_BACKEND_REQUEST_CONTRACT_RECOVERED": "E_GAZETTE_VIEWER_BACKEND_REQUEST_CONTRACT_RECOVERED_FORENSIC_ONLY",
        "VIEWER_DOCUMENT_BINDING_CONTRACT_RECOVERED": "E_GAZETTE_VIEWER_DOCUMENT_BINDING_CONTRACT_RECOVERED_BACKEND_PENDING",
        "VIEWER_CONTRACT_PARTIAL": "E_GAZETTE_VIEWER_CONTRACT_PARTIAL_REQUIRES_NARROWER_JS_FUNCTION_FORENSIC",
        "TECHNICAL_UNKNOWN": "E_GAZETTE_VIEWER_BACKEND_REQUEST_CONTRACT_TECHNICAL_UNKNOWN",
    }[classification]

    if classification == "VIEWER_BACKEND_REQUEST_CONTRACT_RECOVERED":
        next_action = "BUILD_S221O_EXACT_BACKEND_POSITIVE_DOCUMENT_REPLAY_FROM_RECOVERED_METHOD_AND_PARAMETERS"
    elif classification == "VIEWER_DOCUMENT_BINDING_CONTRACT_RECOVERED":
        next_action = "INSPECT_EXACT_VIEWER_BACKEND_FUNCTION_FOR_METHOD_AND_PAYLOAD_BEFORE_INVOCATION"
    elif classification == "VIEWER_CONTRACT_PARTIAL":
        next_action = "NARROW_TO_RELEVANT_VIEWER_JS_FUNCTIONS_AND_URL_CONSTRUCTION_ONLY"
    else:
        next_action = "KEEP_TECHNICAL_UNKNOWN_AND_DO_NOT_INFER_DOCUMENT_BODY_OR_LEGAL_ABSENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-129-S221N",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "candidate": {
            "content_id": content_id,
            "toc_id": toc_id,
            "stored_field_url": field_url,
        },
        "sources": [
            {k: v for k, v in s.items() if k != "body"} | {"body_bytes": len(s["body"].encode("utf-8", errors="ignore"))}
            for s in sources
        ],
        "relevant_js": [
            {"url": r["url"], "http": r["http"], "error": r["error"], "body_bytes": len(r["body"].encode("utf-8", errors="ignore"))}
            for r in js_records
        ],
        "binding_contexts": binding_contexts[:120],
        "backend_contexts": backend_contexts[:120],
        "ajax_contracts": ajax_contracts[:80],
        "url_builders": url_builders[:120],
        "signals": {
            "content_id_binding_signal": content_id_binding_signal,
            "toc_id_binding_signal": toc_id_binding_signal,
            "viewer_builder_signal": viewer_builder_signal,
            "req_type_signal": req_type_signal,
            "viewer_backend_signal": viewer_backend_signal,
            "method_signal": method_signal,
            "parameter_names": param_names,
            "exact_candidate_content_id_literal_signal": exact_candidate_id_literal_signal,
            "exact_candidate_toc_id_literal_signal": exact_toc_id_literal_signal,
            "document_binding_contract_recovered": document_binding_contract_recovered,
            "backend_request_contract_recovered": backend_request_contract_recovered,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "backend_invocation_performed": False,
            "arbitrary_endpoint_guessing_performed": False,
            "document_body_interpreted": False,
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
    print("SOURCE COUNT:", len(sources))
    print("RELEVANT JS COUNT:", len(js_records))
    print("BINDING CONTEXT COUNT:", len(binding_contexts))
    print("BACKEND CONTEXT COUNT:", len(backend_contexts))
    print("AJAX CONTRACT COUNT:", len(ajax_contracts))
    print("URL BUILDER COUNT:", len(url_builders))
    print("CONTENT ID BINDING SIGNAL:", content_id_binding_signal)
    print("TOC ID BINDING SIGNAL:", toc_id_binding_signal)
    print("VIEWER BUILDER SIGNAL:", viewer_builder_signal)
    print("REQTYPE SIGNAL:", req_type_signal)
    print("VIEWER BACKEND SIGNAL:", viewer_backend_signal)
    print("METHOD SIGNAL:", method_signal)
    print("PARAMETER NAMES:", param_names)
    print("EXACT CONTENT ID LITERAL SIGNAL:", exact_candidate_id_literal_signal)
    print("EXACT TOC ID LITERAL SIGNAL:", exact_toc_id_literal_signal)
    print("DOCUMENT BINDING CONTRACT RECOVERED:", document_binding_contract_recovered)
    print("BACKEND REQUEST CONTRACT RECOVERED:", backend_request_contract_recovered)
    print("CLASSIFICATION:", classification)

    print("\nAJAX CONTRACTS")
    for i, c in enumerate(ajax_contracts[:20], 1):
        print(f"[{i}] source={c['source']}")
        print("    url:", c["url"])
        print("    method:", c["method"])
        print("    params:", c["params"])

    print("\nDOCUMENT BINDING CONTEXTS")
    for i, c in enumerate(binding_contexts[:20], 1):
        print(f"--- {i} {c['needle']} {c['source']} ---")
        print(c["context"])

    print("\nBACKEND CONTEXTS")
    for i, c in enumerate(backend_contexts[:20], 1):
        print(f"--- {i} {c['needle']} {c['source']} ---")
        print(c["context"])

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221M safe gate": gate_m,
        "S221J candidate gate": gate_j,
        "content/toc ids recovered": bool(content_id and toc_id),
        "detail forensic attempted": detail is not None,
        "backend invocation disabled": out["summary"]["backend_invocation_performed"] is False,
        "arbitrary endpoint guessing disabled": out["summary"]["arbitrary_endpoint_guessing_performed"] is False,
        "document body not interpreted": out["summary"]["document_body_interpreted"] is False,
        "response classified": classification in {"VIEWER_DOCUMENT_BINDING_CONTRACT_RECOVERED", "VIEWER_BACKEND_REQUEST_CONTRACT_RECOVERED", "VIEWER_CONTRACT_PARTIAL", "TECHNICAL_UNKNOWN"},
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
        raise AssertionError("S221N viewer backend request contract forensic failed")


if __name__ == "__main__":
    main()
