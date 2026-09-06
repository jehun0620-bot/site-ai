# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
S221E = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_live_search_form_response_state_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_live_keyword_submit_js_contract_forensic.json"

BASE_URL = "https://www.gwanbo.go.kr/"
ENTRY = urljoin(BASE_URL, "main.do")
SEARCH = urljoin(BASE_URL, "user/search/searchKeyword.do")
TARGET = "개발밀도관리구역"
MAX_BYTES = 8 * 1024 * 1024

FOCUS_FUNCTIONS = (
    "keyword_Submit",
    "search_enter",
    "searchInit",
    "fn_page",
    "goPage",
    "movePage",
)


def decode_bytes(b: bytes):
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", errors="ignore"), "utf-8-ignore"


def fetch(session: requests.Session, url: str, referer: str | None = None):
    headers = {"Referer": referer} if referer else {}
    try:
        r = session.get(url, headers=headers, timeout=60, allow_redirects=True, stream=True)
        status = r.status_code
        final_url = str(r.url)
        data = bytearray()
        overflow = False
        try:
            for chunk in r.iter_content(65536):
                if not chunk:
                    continue
                if len(data) + len(chunk) > MAX_BYTES:
                    overflow = True
                    break
                data.extend(chunk)
        finally:
            r.close()
        text, enc = decode_bytes(bytes(data))
        return {
            "http": status,
            "final_url": final_url,
            "bytes": len(data),
            "encoding": enc,
            "overflow": overflow,
            "error": None,
            "text": text,
        }
    except requests.RequestException as ex:
        return {
            "http": None,
            "final_url": url,
            "bytes": 0,
            "encoding": None,
            "overflow": False,
            "error": f"{type(ex).__name__}: {ex}",
            "text": "",
        }


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def extract_script_srcs(text: str):
    rows = []
    for m in re.finditer(r"<script\b[^>]*src\s*=\s*['\"]([^'\"]+)['\"][^>]*>\s*</script>", text or "", re.I | re.S):
        src = html.unescape(m.group(1))
        if src not in rows:
            rows.append(src)
    return rows


def extract_function(text: str, name: str):
    patterns = (
        re.compile(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", re.I),
        re.compile(rf"(?:var|let|const)\s+{re.escape(name)}\s*=\s*function\s*\([^)]*\)\s*\{{", re.I),
    )
    starts = []
    for rx in patterns:
        m = rx.search(text or "")
        if m:
            starts.append(m)
    if not starts:
        return None
    start = min(starts, key=lambda m: m.start())
    i = start.end() - 1
    depth = 0
    quote = None
    escape = False
    for j in range(i, len(text)):
        ch = text[j]
        if quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start.start():j + 1]
    return text[start.start():start.start() + 20000]


def extract_ajax_calls(text: str):
    rows = []
    patterns = [
        re.compile(r"\$\.ajax\s*\(\s*\{(?P<body>.{0,8000}?)\}\s*\)", re.I | re.S),
        re.compile(r"\$\.post\s*\((?P<body>.{0,4000}?)\)", re.I | re.S),
        re.compile(r"\$\.get\s*\((?P<body>.{0,4000}?)\)", re.I | re.S),
    ]
    for rx in patterns:
        for m in rx.finditer(text or ""):
            body = norm(m.group("body"))
            if body and body not in rows:
                rows.append(body)
    return rows[:100]


def extract_endpoints(text: str):
    rows = []
    for m in re.finditer(r"['\"]([^'\"]+\.do(?:\?[^'\"]*)?)['\"]", text or "", re.I):
        v = html.unescape(m.group(1))
        if v not in rows:
            rows.append(v)
    return rows[:200]


def extract_assignments(text: str):
    rows = []
    patterns = [
        re.compile(r"(?P<lhs>\$\(\s*['\"]#[^'\"]+['\"]\s*\)\.val)\s*\(\s*(?P<rhs>[^;\n]{0,600})\s*\)", re.I),
        re.compile(r"(?P<lhs>document\.getElementById\(\s*['\"][^'\"]+['\"]\s*\)\.value)\s*=\s*(?P<rhs>[^;\n]{0,600})", re.I),
        re.compile(r"(?P<lhs>[A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?P<rhs>\$\(\s*['\"]#[^'\"]+['\"]\s*\)\.val\([^)]*\)|document\.getElementById\([^;]+?\.value)", re.I),
    ]
    for rx in patterns:
        for m in rx.finditer(text or ""):
            row = {"lhs": norm(m.group("lhs")), "rhs": norm(m.group("rhs"))}
            if row not in rows:
                rows.append(row)
    return rows[:200]


def extract_dom_writes(text: str):
    rows = []
    for pat in (
        r"\$\(\s*['\"]#keyword_contents_list['\"]\s*\)\.(?:html|append|empty)\([^;]{0,2000}\)",
        r"\$\(\s*['\"]#keyword_paging['\"]\s*\)\.(?:html|append|empty)\([^;]{0,2000}\)",
        r"document\.getElementById\(\s*['\"]keyword_contents_list['\"]\s*\)[^;]{0,2000}",
        r"document\.getElementById\(\s*['\"]keyword_paging['\"]\s*\)[^;]{0,2000}",
    ):
        for m in re.finditer(pat, text or "", re.I | re.S):
            v = norm(m.group(0))
            if v not in rows:
                rows.append(v)
    return rows[:100]


def extract_selector_contexts(text: str):
    rows = []
    terms = ["txSimpleSearch", "pQuery_tmp", "pKeyword", "selectSearchCondition", "keyword_contents_list", "keyword_paging", "pageNo"]
    for term in terms:
        for m in re.finditer(re.escape(term), text or "", re.I):
            a = max(0, m.start() - 700)
            b = min(len(text), m.end() + 1200)
            v = norm(text[a:b])
            if v not in rows:
                rows.append(v)
    return rows[:120]


def main():
    print("=" * 78)
    print("E-GAZETTE LIVE keyword_Submit JS CONTRACT FORENSIC - S221F")
    print("=" * 78)
    print("Target UQQ700 query is NOT replayed")
    print("No positive-control replay is performed")
    print("Purpose: recover current live keyword_Submit/search AJAX contract")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s221e = json.loads(S221E.read_text(encoding="utf-8"))
    summary_e = s221e.get("summary") or {}
    gate_live = bool(summary_e.get("live_state_recovered"))
    gate_no_replay = summary_e.get("query_replay_performed") is False and summary_e.get("positive_control_replay_performed") is False
    gate_safe = summary_e.get("uqq700_final_resolution") == "UNKNOWN"
    if not (gate_live and gate_no_replay and gate_safe):
        raise AssertionError("S221F prerequisite gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    entry = fetch(session, ENTRY)
    search = fetch(session, SEARCH, referer=ENTRY)
    srcs = extract_script_srcs(search["text"])
    keyword_srcs = [x for x in srcs if "searchKeyword.js" in x]

    js_records = []
    for src in keyword_srcs[:5]:
        url = urljoin(search["final_url"], src)
        res = fetch(session, url, referer=SEARCH)
        js_records.append({"src": src, "url": url, **res})

    js_text = "\n".join(x["text"] for x in js_records if x["http"] == 200 and not x["error"] and not x["overflow"])
    functions = {}
    for name in FOCUS_FUNCTIONS:
        body = extract_function(js_text, name)
        if body:
            functions[name] = body

    keyword_submit = functions.get("keyword_Submit") or ""
    search_enter = functions.get("search_enter") or ""
    endpoints = extract_endpoints(js_text)
    ajax_calls = extract_ajax_calls(js_text)
    assignments = extract_assignments(keyword_submit or js_text)
    dom_writes = extract_dom_writes(js_text)
    selector_contexts = extract_selector_contexts(js_text)

    pquery_signal = "pQuery_tmp" in js_text or "txSimpleSearch" in js_text
    pkeyword_signal = "pKeyword" in js_text
    condition_signal = "selectSearchCondition" in js_text
    contents_signal = "keyword_contents_list" in js_text
    paging_signal = "keyword_paging" in js_text
    submit_function_found = bool(keyword_submit)
    ajax_signal = bool(ajax_calls)

    result_endpoints = [x for x in endpoints if re.search(r"list|keyword|search|ofctt|result|page", x, re.I)]
    contract_recovered = bool(
        js_records
        and all(x["http"] == 200 and not x["error"] and not x["overflow"] for x in js_records)
        and submit_function_found
        and pquery_signal
        and pkeyword_signal
        and (ajax_signal or bool(result_endpoints))
    )

    semantic = "E_GAZETTE_LIVE_KEYWORD_SUBMIT_JS_CONTRACT_RECOVERED" if contract_recovered else "E_GAZETTE_LIVE_KEYWORD_SUBMIT_JS_CONTRACT_UNRESOLVED"
    next_action = "BUILD_S221G_BROWSER_EQUIVALENT_POSITIVE_CONTROL_REPLAY_FROM_LIVE_KEYWORD_SUBMIT" if contract_recovered else "MANUALLY_INSPECT_LIVE_SEARCHKEYWORD_JS_BEFORE_ANY_REPLAY"

    out = {
        "step": "STEP 17-21-C-16-8-T-122-S221F",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "input_s221e": str(S221E),
        "entry": {k: entry[k] for k in ("http", "final_url", "bytes", "encoding", "overflow", "error")},
        "search_page": {k: search[k] for k in ("http", "final_url", "bytes", "encoding", "overflow", "error")},
        "script_srcs": srcs,
        "keyword_script_srcs": keyword_srcs,
        "keyword_script_fetches": [
            {k: x[k] for k in ("src", "url", "http", "final_url", "bytes", "encoding", "overflow", "error")}
            for x in js_records
        ],
        "functions": functions,
        "endpoints": endpoints,
        "result_endpoints": result_endpoints,
        "ajax_calls": ajax_calls,
        "assignments": assignments,
        "dom_writes": dom_writes,
        "selector_contexts": selector_contexts,
        "contract": {
            "keyword_submit_found": submit_function_found,
            "search_enter_found": bool(search_enter),
            "pquery_signal": pquery_signal,
            "pkeyword_signal": pkeyword_signal,
            "select_search_condition_signal": condition_signal,
            "keyword_contents_list_signal": contents_signal,
            "keyword_paging_signal": paging_signal,
            "ajax_signal": ajax_signal,
            "contract_recovered": contract_recovered,
        },
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "query_replay_performed": False,
            "positive_control_replay_performed": False,
            "uqq700_query_replayed": False,
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

    print("ENTRY HTTP:", entry["http"])
    print("SEARCH PAGE HTTP:", search["http"])
    print("SCRIPT SRC COUNT:", len(srcs))
    print("searchKeyword.js SRC COUNT:", len(keyword_srcs))
    for i, x in enumerate(js_records, 1):
        print(f"JS[{i:02d}] http={x['http']} bytes={x['bytes']} url={x['url']}")

    print("keyword_Submit found:", submit_function_found)
    print("search_enter found:", bool(search_enter))
    print("pQuery_tmp/txSimpleSearch signal:", pquery_signal)
    print("pKeyword signal:", pkeyword_signal)
    print("selectSearchCondition signal:", condition_signal)
    print("keyword_contents_list signal:", contents_signal)
    print("keyword_paging signal:", paging_signal)
    print("AJAX signal:", ajax_signal)
    print("Contract recovered:", contract_recovered)

    print("\nFUNCTION keyword_Submit")
    print(keyword_submit if keyword_submit else "<NOT FOUND>")

    print("\nFUNCTION search_enter")
    print(search_enter if search_enter else "<NOT FOUND>")

    print("\nRESULT/SEARCH ENDPOINTS")
    for i, ep in enumerate(result_endpoints[:60], 1):
        print(f"[{i:02d}] {ep}")

    print("\nAJAX CALLS")
    for i, call in enumerate(ajax_calls[:30], 1):
        print(f"[{i:02d}] {call}")

    print("\nASSIGNMENTS")
    for i, a in enumerate(assignments[:50], 1):
        print(f"[{i:02d}] {a['lhs']} <- {a['rhs']}")

    print("\nDOM WRITES")
    for i, row in enumerate(dom_writes[:40], 1):
        print(f"[{i:02d}] {row}")

    print("\nSELECTOR CONTEXTS")
    for i, row in enumerate(selector_contexts[:20], 1):
        print(f"--- context {i:02d} ---")
        print(row)

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221E live-state gate": gate_live,
        "entry GET 200": entry["http"] == 200 and not entry["error"] and not entry["overflow"],
        "search GET 200": search["http"] == 200 and not search["error"] and not search["overflow"],
        "searchKeyword.js discovered": len(keyword_srcs) > 0,
        "searchKeyword.js fetched": len(js_records) > 0 and all(x["http"] == 200 and not x["error"] and not x["overflow"] for x in js_records),
        "keyword_Submit found": submit_function_found,
        "live JS contract recovered": contract_recovered,
        "query replay not performed": out["summary"]["query_replay_performed"] is False,
        "positive control replay not performed": out["summary"]["positive_control_replay_performed"] is False,
        "UQQ700 query not replayed": out["summary"]["uqq700_query_replayed"] is False,
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
        raise AssertionError("S221F e-gazette live keyword submit JS contract forensic failed")


if __name__ == "__main__":
    main()
