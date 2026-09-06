# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
S220 = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_designation_notice_search_contract_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_js_submit_contract_forensic.json"

BASE_URL = "https://www.gwanbo.go.kr/"
ENTRY = urljoin(BASE_URL, "main.do")
BASIC = urljoin(BASE_URL, "user/search/searchKeyword.do")
ADVANCED = urljoin(BASE_URL, "user/search/searchDetail.do")
TARGET = "개발밀도관리구역"
UA = "Mozilla/5.0"
MAX = 8 * 1024 * 1024
MAX_JS = 32

INTEREST = (
    "search", "keyword", "query", "word", "text", "title", "content", "ofctt",
    "organ", "category", "laword", "date", "from", "to", "start", "end",
    "page", "sort", "order", "tab", "menu", "gubun", "type", "kind", "year",
)


def dec(b: bytes):
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", errors="ignore"), "utf-8-ignore"


def read_body(r):
    buf = bytearray()
    overflow = False
    try:
        for chunk in r.iter_content(65536):
            if not chunk:
                continue
            if len(buf) + len(chunk) > MAX:
                overflow = True
                break
            buf.extend(chunk)
    finally:
        r.close()
    text, enc = dec(bytes(buf))
    return bytes(buf), text, enc, overflow


def get(session, url, referer=None):
    try:
        r = session.get(
            url,
            headers={"Referer": referer} if referer else {},
            timeout=60,
            allow_redirects=True,
            stream=True,
        )
        status = r.status_code
        final_url = str(r.url)
        ctype = r.headers.get("Content-Type")
        body, text, enc, overflow = read_body(r)
        return {
            "http": status,
            "final_url": final_url,
            "content_type": ctype,
            "body": body,
            "text": text,
            "encoding": enc,
            "overflow": overflow,
            "error": None,
        }
    except requests.RequestException as ex:
        return {
            "http": None,
            "final_url": url,
            "content_type": None,
            "body": b"",
            "text": "",
            "encoding": None,
            "overflow": False,
            "error": f"{type(ex).__name__}: {ex}",
        }


def script_sources(text: str, base: str):
    out = []
    for src in re.findall(r"<script\b[^>]*src=[\"']([^\"']+)[\"']", text or "", re.I):
        u = urljoin(base, html.unescape(src))
        if urlparse(u).netloc.endswith("gwanbo.go.kr") and u not in out:
            out.append(u)
    return out


def inline_scripts(text: str):
    return [m.group(1) for m in re.finditer(r"<script\b[^>]*>(.*?)</script>", text or "", re.I | re.S)]


def function_blocks(text: str):
    out = []
    for m in re.finditer(r"function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{", text or "", re.I):
        name = m.group(1)
        start = m.start()
        i = m.end()
        depth = 1
        quote = None
        esc = False
        while i < len(text) and depth > 0:
            ch = text[i]
            if quote:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == quote:
                    quote = None
            else:
                if ch in ('"', "'"):
                    quote = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
            i += 1
        body = text[start:i] if depth == 0 else text[start:min(len(text), start + 12000)]
        low = body.lower()
        if any(x in name.lower() or x in low for x in ("search", "submit", "keyword", "detail", "page", "go", "move", "ajax")):
            out.append({"name": name, "args": m.group(2), "body": re.sub(r"\s+", " ", body).strip()[:12000]})
        if len(out) >= 150:
            break
    return out


def endpoint_hits(text: str):
    return sorted(set(re.findall(r"(?:/user/)?[A-Za-z0-9_./-]+\.do(?:\?[^\"'<>\s]*)?", text or "", re.I)))


def param_names(text: str):
    names = set()
    patterns = [
        r"(?:name|id)=[\"']([A-Za-z0-9_.$\[\]-]+)[\"']",
        r"[\"']([A-Za-z0-9_.$\[\]-]+)[\"']\s*:\s*",
        r"\.val\s*\([^)]*\)\s*;?",
        r"(?:param|data)\s*\[\s*[\"']([A-Za-z0-9_.$\[\]-]+)[\"']\s*\]",
        r"(?:append|set)\s*\(\s*[\"']([A-Za-z0-9_.$\[\]-]+)[\"']",
        r"[?&]([A-Za-z0-9_.$\[\]-]+)=",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text or "", re.I):
            if m.lastindex:
                names.add(m.group(1))
    return sorted(x for x in names if any(t in x.lower() for t in INTEREST))


def submit_contexts(text: str):
    out = []
    rgx = re.compile(
        r"\.submit\s*\(|\.serialize\s*\(|serializeArray\s*\(|FormData\s*\(|"
        r"\$\.ajax|\$\.post|\$\.get|fetch\s*\(|location\.(?:href|replace)|"
        r"\.attr\s*\(\s*[\"']action|\.prop\s*\(\s*[\"']action|action\s*=|url\s*:",
        re.I,
    )
    for m in rgx.finditer(text or ""):
        ctx = re.sub(r"\s+", " ", (text or "")[max(0, m.start()-1200):min(len(text or ""), m.start()+3600)]).strip()
        if ctx not in out:
            out.append(ctx[:4800])
        if len(out) >= 80:
            break
    return out


def selectors(text: str):
    vals = set()
    for m in re.finditer(r"\$\(\s*[\"']([^\"']+)[\"']\s*\)", text or ""):
        sel = m.group(1)
        if any(t in sel.lower() for t in INTEREST):
            vals.add(sel)
    return sorted(vals)


def inspect_text(text: str):
    return {
        "endpoints": endpoint_hits(text)[:250],
        "parameter_names": param_names(text)[:250],
        "selectors": selectors(text)[:250],
        "submit_contexts": submit_contexts(text),
        "functions": function_blocks(text),
    }


def main():
    print("=" * 76)
    print("E-GAZETTE SEARCH JS SUBMIT CONTRACT FORENSIC - S220A")
    print("=" * 76)
    print("Target:", TARGET)
    print("Purpose: recover JS submit/AJAX/search parameter assembly contract only")
    print("No positive-control query replay in this stage")
    print("Search hit != designation fact")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s220 = json.loads(S220.read_text(encoding="utf-8"))
    s220_summary = s220.get("summary") or {}
    s220_contract = s220.get("contract") or {}
    if s220_summary.get("technical_unknown_count") != 0:
        raise AssertionError("S220 transport contract not clean")
    if not s220_contract.get("contract_signal_observed"):
        raise AssertionError("S220 did not observe search endpoint signals")
    if s220_contract.get("search_contract_qualified_for_positive_control_replay"):
        raise AssertionError("S220A only applies when S220 form contract is unresolved")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})

    pages = {}
    js_urls = []
    for label, url in (("entry", ENTRY), ("basic", BASIC), ("advanced", ADVANCED)):
        r = get(session, url, ENTRY if label != "entry" else None)
        scripts = script_sources(r["text"], r["final_url"] or url)
        for x in scripts:
            if x not in js_urls:
                js_urls.append(x)
        inline = "\n".join(inline_scripts(r["text"]))
        pages[label] = {
            "url": url,
            "response": {
                "http": r["http"], "final_url": r["final_url"], "bytes": len(r["body"]),
                "encoding": r["encoding"], "overflow": r["overflow"], "error": r["error"],
            },
            "script_srcs": scripts,
            "inline_signals": inspect_text(inline),
            "full_html_signals": inspect_text(r["text"]),
        }

    external_js = {}
    for url in js_urls[:MAX_JS]:
        r = get(session, url, referer=ADVANCED)
        external_js[url] = {
            "response": {"http": r["http"], "bytes": len(r["body"]), "overflow": r["overflow"], "error": r["error"]},
            "signals": inspect_text(r["text"]) if r["http"] == 200 and not r["overflow"] else {},
        }

    all_endpoint = set()
    all_params = set()
    all_selectors = set()
    all_contexts = []
    all_functions = []

    def absorb(sig):
        all_endpoint.update(sig.get("endpoints", []))
        all_params.update(sig.get("parameter_names", []))
        all_selectors.update(sig.get("selectors", []))
        for x in sig.get("submit_contexts", []):
            if x not in all_contexts:
                all_contexts.append(x)
        for x in sig.get("functions", []):
            key = (x.get("name"), x.get("body"))
            if not any((y.get("name"), y.get("body")) == key for y in all_functions):
                all_functions.append(x)

    for p in pages.values():
        absorb(p["inline_signals"])
        absorb(p["full_html_signals"])
    for j in external_js.values():
        absorb(j.get("signals", {}))

    search_endpoints = sorted(x for x in all_endpoint if re.search(r"search|ofctt|organ|category|laword|keyword", x, re.I))
    relevant_params = sorted(all_params)
    submit_signal_count = len(all_contexts) + len(all_functions)

    required_endpoint_signal = any("searchKeyword.do" in x or "searchDetail.do" in x for x in search_endpoints)
    parameter_signal = len(relevant_params) > 0
    js_submit_contract_signal = submit_signal_count > 0

    technical_unknown_count = sum(
        1 for p in pages.values()
        if p["response"]["http"] != 200 or p["response"]["error"] or p["response"]["overflow"]
    )

    contract_recovered = (
        technical_unknown_count == 0
        and required_endpoint_signal
        and parameter_signal
        and js_submit_contract_signal
    )

    semantic = (
        "E_GAZETTE_JS_SUBMIT_CONTRACT_SIGNAL_RECOVERED_FOR_POSITIVE_CONTROL_REPLAY"
        if contract_recovered
        else "E_GAZETTE_JS_SUBMIT_CONTRACT_STILL_UNRESOLVED"
    )
    next_action = (
        "BUILD_S221_POSITIVE_CONTROL_REPLAY_FROM_RECOVERED_JS_PARAMETER_CONTRACT"
        if contract_recovered
        else "MANUALLY_NARROW_CAPTURED_JS_FUNCTIONS_AND_PARAMETER_ASSEMBLY_BEFORE_QUERY_REPLAY"
    )

    out = {
        "step": "STEP 17-21-C-16-8-T-115-S220A",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "source_role": "OFFICIAL_NOTICE_IDENTITY_DISCOVERY_CANDIDATE",
        "input_s220": str(S220),
        "pages": pages,
        "external_js": external_js,
        "aggregated_contract": {
            "search_endpoints": search_endpoints[:250],
            "parameter_names": relevant_params[:250],
            "selectors": sorted(all_selectors)[:250],
            "submit_contexts": all_contexts[:100],
            "functions": all_functions[:150],
            "required_search_endpoint_signal": required_endpoint_signal,
            "parameter_signal_observed": parameter_signal,
            "js_submit_signal_observed": js_submit_contract_signal,
            "contract_recovered_for_positive_control_replay": contract_recovered,
        },
        "summary": {
            "technical_unknown_count": technical_unknown_count,
            "semantic_state": semantic,
            "next_action": next_action,
            "query_replay_performed": False,
            "search_hit_equals_designation_fact": False,
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

    print("ENTRY HTTP:", pages["entry"]["response"]["http"])
    print("BASIC HTTP:", pages["basic"]["response"]["http"])
    print("ADVANCED HTTP:", pages["advanced"]["response"]["http"])
    print("EXTERNAL JS COUNT:", len(external_js))
    print("SEARCH ENDPOINTS:", search_endpoints[:80])
    print("PARAMETER NAMES:", relevant_params[:120])
    print("SELECTORS:", sorted(all_selectors)[:120])
    print("SUBMIT CONTEXT COUNT:", len(all_contexts))
    print("FUNCTION COUNT:", len(all_functions))

    print("\nSUMMARY")
    print("Required search endpoint signal:", required_endpoint_signal)
    print("Parameter signal observed:", parameter_signal)
    print("JS submit signal observed:", js_submit_contract_signal)
    print("Contract recovered for positive control replay:", contract_recovered)
    print("Technical unknown count:", technical_unknown_count)
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution:", out["summary"]["uqq700_final_resolution"])
    print("Output:", OUT)

    checks = {
        "S220 unresolved form contract gate": s220_contract.get("search_contract_qualified_for_positive_control_replay") is False,
        "entry 200": pages["entry"]["response"]["http"] == 200,
        "basic 200": pages["basic"]["response"]["http"] == 200,
        "advanced 200": pages["advanced"]["response"]["http"] == 200,
        "technical unknown zero": technical_unknown_count == 0,
        "required search endpoint signal": required_endpoint_signal,
        "parameter signal observed": parameter_signal,
        "JS submit signal observed": js_submit_contract_signal,
        "contract recovered only for positive control replay": contract_recovered,
        "query replay not performed": out["summary"]["query_replay_performed"] is False,
        "search hit not designation fact": out["summary"]["search_hit_equals_designation_fact"] is False,
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
        raise AssertionError("S220A e-gazette JS submit contract forensic failed")


if __name__ == "__main__":
    main()
