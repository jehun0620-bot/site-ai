# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent.parent
S221K = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_candidate_document_endpoint_qualification.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_detail_renderer_delivery_contract_forensic.json"

BASE_URL = "https://www.gwanbo.go.kr/"
TARGET = "개발밀도관리구역"

SIGNAL_TERMS = (
    "pdf", "download", "file", "contentId", "tocId", "ebook", "viewer",
    "ezpdf", "DataRestApi", "ajax", "image", "page", "print", "customLayout",
)


def get_text(session: requests.Session, url: str, referer: str | None = None):
    headers = {"Referer": referer} if referer else None
    try:
        r = session.get(url, timeout=60, allow_redirects=True, headers=headers)
        return {
            "url": url,
            "http": r.status_code,
            "final_url": str(r.url),
            "content_type": r.headers.get("Content-Type", ""),
            "body_bytes": len(r.content),
            "text": r.text,
            "error": None,
        }
    except requests.RequestException as ex:
        return {
            "url": url,
            "http": None,
            "final_url": None,
            "content_type": "",
            "body_bytes": 0,
            "text": "",
            "error": f"{type(ex).__name__}: {ex}",
        }


def compact_snippet(text: str, start: int, end: int, radius: int = 350) -> str:
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    return re.sub(r"\s+", " ", text[lo:hi]).strip()


def collect_signal_snippets(text: str):
    snippets = []
    seen = set()
    for term in SIGNAL_TERMS:
        for m in re.finditer(re.escape(term), text, flags=re.I):
            snippet = compact_snippet(text, m.start(), m.end())
            key = snippet[:300]
            if key in seen:
                continue
            seen.add(key)
            snippets.append({"term": term, "snippet": snippet})
            if len(snippets) >= 120:
                return snippets
    return snippets


def extract_urls_and_paths(text: str):
    patterns = [
        r"https?://[^\s\"'<>]+",
        r"/[A-Za-z0-9_./?=&%-]+(?:\.jsp|\.do|\.pdf|\.js|\.json|\.png|\.jpg|\.jpeg|\.gif)(?:\?[^\s\"'<>]*)?",
        r"[A-Za-z0-9_./-]+\.jsp(?:\?[^\s\"'<>]*)?",
        r"[A-Za-z0-9_./-]+\.do(?:\?[^\s\"'<>]*)?",
        r"[A-Za-z0-9_./-]+\.pdf(?:\?[^\s\"'<>]*)?",
    ]
    out = []
    seen = set()
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            raw = m.group(0).replace("&amp;", "&")
            if raw not in seen:
                seen.add(raw)
                out.append(raw)
    return out[:300]


def extract_function_contexts(text: str):
    contexts = []
    patterns = [
        r"function\s+[A-Za-z0-9_$]+\s*\([^)]*\)\s*\{",
        r"(?:var|let|const)\s+[A-Za-z0-9_$]+\s*=\s*function\s*\([^)]*\)\s*\{",
        r"\$\.ajax\s*\(\s*\{",
        r"url\s*:\s*[\"'][^\"']+[\"']",
        r"window\.open\s*\([^)]*\)",
        r"location(?:\.href)?\s*=\s*[^;]+",
    ]
    seen = set()
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            snippet = compact_snippet(text, m.start(), m.end(), radius=500)
            if not any(term.lower() in snippet.lower() for term in SIGNAL_TERMS):
                continue
            key = snippet[:400]
            if key in seen:
                continue
            seen.add(key)
            contexts.append(snippet)
            if len(contexts) >= 100:
                return contexts
    return contexts


def main():
    print("=" * 78)
    print("E-GAZETTE DETAIL RENDERER / DELIVERY CONTRACT FORENSIC - S221L")
    print("=" * 78)
    print("Purpose: recover viewer/PDF/content delivery contract only")
    print("No target-body interpretation in this stage")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s221k = json.loads(S221K.read_text(encoding="utf-8"))
    summary_k = s221k.get("summary") or {}
    candidate = s221k.get("candidate") or {}
    detail_k = s221k.get("detail") or {}

    gate_k = (
        s221k.get("classification") == "DOCUMENT_ENDPOINT_QUALIFIED"
        and detail_k.get("http") == 200
        and summary_k.get("uqq700_final_resolution") == "UNKNOWN"
        and s221k.get("official_designation_identity_verified") is False
    )
    if not gate_k:
        raise AssertionError("S221L prerequisite S221K gate not satisfied")

    detail_url = str(detail_k.get("final_url") or detail_k.get("url") or "")
    content_id = str(candidate.get("content_id") or "")
    toc_id = str(candidate.get("toc_id") or "")
    ebook_no = str(candidate.get("ebook_no") or "")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    detail = get_text(session, detail_url, referer=BASE_URL)
    html = detail.get("text") or ""
    soup = BeautifulSoup(html, "html.parser")

    script_srcs = []
    for tag in soup.find_all("script"):
        src = tag.get("src")
        if src:
            script_srcs.append(urljoin(detail_url, src))

    iframe_srcs = [urljoin(detail_url, x.get("src")) for x in soup.find_all("iframe") if x.get("src")]
    object_data = [urljoin(detail_url, x.get("data")) for x in soup.find_all("object") if x.get("data")]
    embed_srcs = [urljoin(detail_url, x.get("src")) for x in soup.find_all("embed") if x.get("src")]

    inline_scripts = "\n".join(tag.get_text("\n") for tag in soup.find_all("script") if not tag.get("src"))
    html_paths = extract_urls_and_paths(html)
    html_signal_snippets = collect_signal_snippets(html)
    html_function_contexts = extract_function_contexts(inline_scripts + "\n" + html)

    js_results = []
    for src in script_srcs[:30]:
        fetched = get_text(session, src, referer=detail_url)
        text = fetched.get("text") or ""
        relevant = any(term.lower() in text.lower() for term in SIGNAL_TERMS)
        if relevant:
            js_results.append({
                "src": src,
                "http": fetched.get("http"),
                "content_type": fetched.get("content_type"),
                "body_bytes": fetched.get("body_bytes"),
                "error": fetched.get("error"),
                "paths": extract_urls_and_paths(text),
                "signal_snippets": collect_signal_snippets(text),
                "function_contexts": extract_function_contexts(text),
            })

    combined = html + "\n" + inline_scripts + "\n" + "\n".join(
        "\n".join(x.get("function_contexts") or []) + "\n" + "\n".join(y.get("snippet", "") for y in (x.get("signal_snippets") or []))
        for x in js_results
    )

    content_id_signal = content_id in combined if content_id else False
    toc_id_signal = toc_id in combined if toc_id else False
    ebook_signal = ebook_no in combined if ebook_no else False

    all_paths = []
    for raw in html_paths:
        all_paths.append(raw)
    for js in js_results:
        all_paths.extend(js.get("paths") or [])
    for u in iframe_srcs + object_data + embed_srcs:
        all_paths.append(u)

    dedup_paths = []
    for p in all_paths:
        if p not in dedup_paths:
            dedup_paths.append(p)

    pdf_like = [p for p in dedup_paths if ".pdf" in p.lower() or "pdf" in p.lower()]
    viewer_like = [p for p in dedup_paths if any(x in p.lower() for x in ("viewer", "ezpdf", "customlayout"))]
    data_like = [p for p in dedup_paths if any(x in p.lower() for x in ("datarestapi", "ajax", "content", "page", "image"))]

    ajax_signal = bool(re.search(r"\$\.ajax|fetch\s*\(|XMLHttpRequest", combined, flags=re.I))
    window_open_signal = bool(re.search(r"window\.open", combined, flags=re.I))
    download_signal = "download" in combined.lower()
    pdf_signal = "pdf" in combined.lower()
    viewer_signal = any(x in combined.lower() for x in ("viewer", "ezpdf", "customlayout"))

    strong_contract_signal = bool(
        pdf_like
        or (viewer_signal and (content_id_signal or toc_id_signal))
        or (ajax_signal and data_like and (content_id_signal or toc_id_signal or ebook_signal))
    )

    if strong_contract_signal and pdf_like:
        classification = "PDF_DELIVERY_CONTRACT_RECOVERED"
    elif strong_contract_signal:
        classification = "VIEWER_CONTENT_CONTRACT_RECOVERED"
    elif detail.get("http") == 200 and (viewer_signal or ajax_signal or data_like):
        classification = "DETAIL_RENDERER_CONTRACT_PARTIAL"
    else:
        classification = "TECHNICAL_UNKNOWN"

    semantic = {
        "PDF_DELIVERY_CONTRACT_RECOVERED": "E_GAZETTE_PDF_DELIVERY_CONTRACT_RECOVERED_FOR_CANDIDATE",
        "VIEWER_CONTENT_CONTRACT_RECOVERED": "E_GAZETTE_VIEWER_CONTENT_CONTRACT_RECOVERED_FOR_CANDIDATE",
        "DETAIL_RENDERER_CONTRACT_PARTIAL": "E_GAZETTE_DETAIL_RENDERER_CONTRACT_PARTIAL_REQUIRES_NARROW_REPLAY",
        "TECHNICAL_UNKNOWN": "E_GAZETTE_DETAIL_RENDERER_DELIVERY_CONTRACT_TECHNICAL_UNKNOWN",
    }[classification]

    next_action = {
        "PDF_DELIVERY_CONTRACT_RECOVERED": "BUILD_S221M_EXACT_DOCUMENT_DELIVERY_REPLAY_FROM_RECOVERED_CONTRACT",
        "VIEWER_CONTENT_CONTRACT_RECOVERED": "BUILD_S221M_EXACT_VIEWER_CONTENT_REPLAY_FROM_RECOVERED_CONTRACT",
        "DETAIL_RENDERER_CONTRACT_PARTIAL": "INSPECT_NARROW_RELEVANT_JS_FUNCTIONS_BEFORE_DOCUMENT_DELIVERY_REPLAY",
        "TECHNICAL_UNKNOWN": "KEEP_DOCUMENT_DELIVERY_TECHNICAL_UNKNOWN_AND_DO_NOT_INFER_BODY_NO_HIT",
    }[classification]

    out = {
        "step": "STEP 17-21-C-16-8-T-128-S221L",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "input_s221k": str(S221K),
        "candidate": {
            "content_id": content_id,
            "toc_id": toc_id,
            "ebook_no": ebook_no,
            "detail_url": detail_url,
        },
        "detail": {k: v for k, v in detail.items() if k != "text"},
        "script_srcs": script_srcs,
        "iframe_srcs": iframe_srcs,
        "object_data": object_data,
        "embed_srcs": embed_srcs,
        "html_paths": html_paths,
        "html_signal_snippets": html_signal_snippets,
        "html_function_contexts": html_function_contexts,
        "relevant_js": js_results,
        "contract_signals": {
            "content_id_signal": content_id_signal,
            "toc_id_signal": toc_id_signal,
            "ebook_no_signal": ebook_signal,
            "ajax_signal": ajax_signal,
            "window_open_signal": window_open_signal,
            "download_signal": download_signal,
            "pdf_signal": pdf_signal,
            "viewer_signal": viewer_signal,
            "pdf_like_paths": pdf_like,
            "viewer_like_paths": viewer_like,
            "data_like_paths": data_like,
            "strong_contract_signal": strong_contract_signal,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
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

    print("DETAIL HTTP:", detail.get("http"))
    print("DETAIL CONTENT-TYPE:", detail.get("content_type"))
    print("DETAIL BODY BYTES:", detail.get("body_bytes"))
    print("SCRIPT SRC COUNT:", len(script_srcs))
    print("RELEVANT JS COUNT:", len(js_results))
    print("IFRAME SRC COUNT:", len(iframe_srcs))
    print("OBJECT DATA COUNT:", len(object_data))
    print("EMBED SRC COUNT:", len(embed_srcs))
    print("CONTENT ID SIGNAL:", content_id_signal)
    print("TOC ID SIGNAL:", toc_id_signal)
    print("EBOOK NO SIGNAL:", ebook_signal)
    print("AJAX SIGNAL:", ajax_signal)
    print("DOWNLOAD SIGNAL:", download_signal)
    print("PDF SIGNAL:", pdf_signal)
    print("VIEWER SIGNAL:", viewer_signal)
    print("PDF-LIKE PATH COUNT:", len(pdf_like))
    print("VIEWER-LIKE PATH COUNT:", len(viewer_like))
    print("DATA-LIKE PATH COUNT:", len(data_like))
    print("STRONG CONTRACT SIGNAL:", strong_contract_signal)
    print("CLASSIFICATION:", classification)

    print("\nPDF-LIKE PATHS")
    for p in pdf_like[:50]:
        print(p)

    print("\nVIEWER/DATA-LIKE PATHS")
    for p in (viewer_like + data_like)[:100]:
        print(p)

    print("\nRELEVANT JS")
    for i, js in enumerate(js_results, 1):
        print(f"--- JS {i:02d} ---")
        print("SRC:", js["src"])
        print("HTTP:", js["http"], "BYTES:", js["body_bytes"])
        print("PATHS:", json.dumps(js["paths"][:30], ensure_ascii=False, indent=2))
        print("FUNCTION CONTEXTS:")
        for ctx in js["function_contexts"][:20]:
            print(ctx)

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221K document-endpoint gate": gate_k,
        "detail GET 200": detail.get("http") == 200,
        "response classified": classification in {"PDF_DELIVERY_CONTRACT_RECOVERED", "VIEWER_CONTENT_CONTRACT_RECOVERED", "DETAIL_RENDERER_CONTRACT_PARTIAL", "TECHNICAL_UNKNOWN"},
        "document body not interpreted": out["summary"]["document_body_interpreted"] is False,
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
        raise AssertionError("S221L detail renderer/delivery contract forensic failed")


if __name__ == "__main__":
    main()
