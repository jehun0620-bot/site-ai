# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
S226J_OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_board_historical_coverage_qualification.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_board_list_contract_hardening.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
OFFICIAL_HOST = "www.seongnam.go.kr"
BOARD_BASE = "https://www.seongnam.go.kr/ct-bbs020102"
VERIFIED_DETAIL = f"{BOARD_BASE}/374215"
MAX_SCRIPT_FETCH = 20
MAX_SAFE_REPLAY = 6

SEARCHISH = re.compile(r"(?i)(query|search|srch|keyword|find|sch)")
PAGEISH = re.compile(r"(?i)(page|paging|currentPage|pageIndex|pageNo|cPage|startCount)")
BOARD_IDISH = re.compile(r"(?i)(pstSn|idx|board|bbs|seq|sn|id)")
PATHISH = re.compile(r"(?:https?://[^\"'\s<>]+|/[A-Za-z0-9_./?=&%{}$:+\-]+)")


def curl_bytes(url: str, *, method: str = "GET", data: str | None = None) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"ok": False, "http": None, "final_url": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "45",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}",
    ]
    if method.upper() == "POST":
        cmd += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded"]
        if data is not None:
            cmd += ["--data", data]
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 1)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
    else:
        body, http, final_url = raw, None, None
    return {
        "ok": p.returncode == 0 and bool(http and http != "000"),
        "returncode": p.returncode,
        "http": http,
        "final_url": final_url,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def decode_body(body: bytes) -> tuple[str, str]:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            text = body.decode(enc)
            if enc == "utf-8" or "성남" in text:
                return text, enc
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace"), "utf-8-replace"


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def extract_title(html: str) -> str | None:
    m = re.search(r"(?is)<title\b[^>]*>(.*?)</title>", html or "")
    return clean_html(m.group(1))[:500] if m else None


def attr_map(attrs: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r'''(?is)([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(["'])(.*?)\2''', attrs or ""):
        out[m.group(1).lower()] = unescape(m.group(3))
    return out


def extract_forms(html: str, base_url: str) -> list[dict]:
    forms = []
    for idx, fm in enumerate(re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html or ""), 1):
        attrs, inner = fm.group(1), fm.group(2)
        amap = attr_map(attrs)
        action = urljoin(base_url, amap.get("action") or base_url)
        method = (amap.get("method") or "GET").upper()
        controls = []
        for cm in re.finditer(r"(?is)<(input|select|textarea|button)\b([^>]*)>(.*?)</(?:select|textarea|button)>|<(input)\b([^>]*)>", inner):
            tag = cm.group(1) or cm.group(4) or "input"
            rawattrs = cm.group(2) or cm.group(5) or ""
            cmap = attr_map(rawattrs)
            if "name" not in cmap and "id" not in cmap:
                continue
            controls.append({
                "tag": tag.lower(),
                "name": cmap.get("name"),
                "id": cmap.get("id"),
                "type": cmap.get("type"),
                "value": cmap.get("value", ""),
                "onclick": cmap.get("onclick"),
                "data": {k: v for k, v in cmap.items() if k.startswith("data-")},
            })
        forms.append({
            "index": idx,
            "id": amap.get("id"),
            "name": amap.get("name"),
            "action": action,
            "method": method,
            "onsubmit": amap.get("onsubmit"),
            "controls": controls,
            "search_controls": [c for c in controls if SEARCHISH.search((c.get("name") or "") + " " + (c.get("id") or ""))],
            "page_controls": [c for c in controls if PAGEISH.search((c.get("name") or "") + " " + (c.get("id") or ""))],
            "board_id_controls": [c for c in controls if BOARD_IDISH.search((c.get("name") or "") + " " + (c.get("id") or ""))],
        })
    return forms


def extract_scripts(html: str, base_url: str) -> tuple[list[str], list[str]]:
    srcs, inline = [], []
    for m in re.finditer(r"(?is)<script\b([^>]*)>(.*?)</script>", html or ""):
        attrs, body = m.group(1), m.group(2)
        amap = attr_map(attrs)
        if amap.get("src"):
            u = urljoin(base_url, amap["src"])
            if urlparse(u).hostname == OFFICIAL_HOST and u not in srcs:
                srcs.append(u)
        elif body.strip():
            inline.append(body)
    return srcs, inline


def extract_js_contracts(text: str, source: str) -> list[dict]:
    contracts, seen = [], set()
    for raw in PATHISH.findall(text or ""):
        raw = raw.rstrip("),;]")
        u = urljoin(BOARD_BASE, raw)
        p = urlparse(u)
        if p.hostname != OFFICIAL_HOST:
            continue
        blob = raw.lower()
        if not any(tok in blob for tok in ("ct-bbs", "bbs", "board", "page", "search", "ajax", "list")):
            continue
        if u in seen:
            continue
        seen.add(u)
        contracts.append({"source": source, "url": u})
    return contracts


def extract_handlers(html: str) -> list[dict]:
    handlers = []
    for m in re.finditer(r"(?is)<(a|button|input)\b([^>]*)>", html or ""):
        tag, attrs = m.group(1), m.group(2)
        amap = attr_map(attrs)
        if not any(k in amap for k in ("onclick", "href")) and not any(k.startswith("data-") for k in amap):
            continue
        item = {
            "tag": tag.lower(),
            "href": amap.get("href"),
            "onclick": amap.get("onclick"),
            "data": {k: v for k, v in amap.items() if k.startswith("data-")},
        }
        blob = json.dumps(item, ensure_ascii=False)
        if any(tok in blob.lower() for tok in ("page", "bbs", "board", "pstsn", "idx", "374215")):
            handlers.append(item)
    return handlers


def safe_replay_candidates(forms: list[dict]) -> list[dict]:
    candidates = []
    for form in forms:
        if urlparse(form["action"]).hostname != OFFICIAL_HOST:
            continue
        payload = {}
        blocked = False
        for c in form["controls"]:
            name = c.get("name")
            if not name:
                continue
            value = c.get("value") or ""
            if SEARCHISH.search(name):
                value = ""
            if TARGET in value or "도시계획위원회" in value:
                blocked = True
                break
            payload[name] = value
        if blocked:
            continue
        candidates.append({"form_index": form["index"], "method": form["method"], "url": form["action"], "payload": payload})
    return candidates[:MAX_SAFE_REPLAY]


def execute_safe_replay(item: dict) -> dict:
    if item["method"] == "POST":
        f = curl_bytes(item["url"], method="POST", data=urlencode(item["payload"], doseq=True))
    else:
        query = urlencode(item["payload"], doseq=True)
        sep = "&" if "?" in item["url"] else "?"
        f = curl_bytes(item["url"] + (sep + query if query else ""))
    html, enc = decode_body(f.pop("body"))
    text = clean_html(html)
    return {
        **item,
        **f,
        "selected_charset": enc,
        "title": extract_title(html),
        "board_identity_signals": [t for t in ("위원회", "도시계획", "도시계획위원회", "도시계획과") if t in text],
        "target_visible": TARGET in text,
        "committee_term_visible": "도시계획위원회" in text,
        "body_prefix": text[:3500],
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE BOARD LIST CONTRACT HARDENING - S226K")
    print("=" * 78)
    print("Purpose: recover ct-bbs020102 form/JS list and pagination contract without semantic search")
    print("Committee search query: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Empty/default list replay only")
    print("2018-07-01 global date: NOT PROMOTED TO POST DATE")
    print("Negative evidence: DISABLED")
    print("Source closure: BLOCKED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    f = curl_bytes(BOARD_BASE)
    html, enc = decode_body(f.pop("body"))
    forms = extract_forms(html, f.get("final_url") or BOARD_BASE)
    srcs, inline = extract_scripts(html, f.get("final_url") or BOARD_BASE)
    handlers = extract_handlers(html)

    script_results = []
    js_contracts = []
    for i, src in enumerate(srcs[:MAX_SCRIPT_FETCH], 1):
        sf = curl_bytes(src)
        stext, senc = decode_body(sf.pop("body"))
        contracts = extract_js_contracts(stext, src)
        js_contracts.extend(contracts)
        script_results.append({
            "index": i,
            "url": src,
            **sf,
            "selected_charset": senc,
            "contract_count": len(contracts),
            "contracts": contracts,
            "page_function_hits": sorted(set(re.findall(r"(?i)\b(?:goPage|fnPage|pageMove|paging|movePage|setPage|doPage)\w*\b", stext)))[:30],
            "search_function_hits": sorted(set(re.findall(r"(?i)\b(?:search|fnSearch|doSearch|goSearch)\w*\b", stext)))[:30],
        })

    inline_contracts = []
    inline_functions = []
    for i, text in enumerate(inline, 1):
        inline_contracts.extend(extract_js_contracts(text, f"inline_{i}"))
        inline_functions.extend(re.findall(r"(?i)function\s+([A-Za-z_$][\w$]*)\s*\(", text))

    all_contracts = []
    seen = set()
    for row in js_contracts + inline_contracts:
        if row["url"] not in seen:
            seen.add(row["url"])
            all_contracts.append(row)

    safe_candidates = safe_replay_candidates(forms)
    safe_results = [execute_safe_replay(x) for x in safe_candidates]

    form_contract_signal = any(
        form["action"].rstrip("/") == BOARD_BASE.rstrip("/")
        and (form["search_controls"] or form["page_controls"] or form["board_id_controls"])
        for form in forms
    )
    js_contract_signal = bool(all_contracts or handlers or inline_functions or any(r["page_function_hits"] for r in script_results))
    safe_replay_ok = any(r.get("http") == "200" and urlparse(r.get("final_url") or "").hostname == OFFICIAL_HOST for r in safe_results)
    target_query_executed = False
    committee_query_executed = False

    if form_contract_signal and safe_replay_ok and js_contract_signal:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOARD_LIST_CONTRACT_QUALIFIED"
        semantic = "CT_BBS020102_FORM_JS_AND_DEFAULT_LIST_REPLAY_CONTRACT_RECOVERED_WITHOUT_SEMANTIC_QUERY"
        next_action = "RECONSTRUCT_BOUNDED_PAGINATION_AND_HISTORICAL_COVERAGE_USING_QUALIFIED_DEFAULT_LIST_CONTRACT_BEFORE_UQQ700_QUERY"
    elif form_contract_signal or js_contract_signal or safe_replay_ok:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOARD_LIST_SURFACE_FOUND_CONTRACT_PARTIAL"
        semantic = "CT_BBS020102_LIST_SURFACE_SIGNALS_RECOVERED_BUT_FULL_LIST_OR_PAGINATION_CONTRACT_REMAINS_PARTIAL"
        next_action = "HARDEN_FORM_SUBMIT_AND_PAGINATION_FUNCTION_ARGUMENT_MAPPING_WITHOUT_UQQ700_QUERY"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOARD_LIST_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "CT_BBS020102_LIST_CONTRACT_NOT_YET_TECHNICALLY_RECOVERED"
        next_action = "RECOVER_CLIENT_SIDE_LIST_CONTRACT_FROM_HTML_JS_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226K",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s226j_input_exists": S226J_OUT.exists(),
        "board_base": BOARD_BASE,
        "verified_detail": VERIFIED_DETAIL,
        "http": f.get("http"),
        "final_url": f.get("final_url"),
        "selected_charset": enc,
        "title": extract_title(html),
        "form_count": len(forms),
        "forms": forms,
        "same_host_script_count": len(srcs),
        "script_fetch_count": len(script_results),
        "script_results": script_results,
        "inline_script_count": len(inline),
        "inline_function_names": sorted(set(inline_functions)),
        "handler_count": len(handlers),
        "handlers": handlers,
        "contract_candidate_count": len(all_contracts),
        "contract_candidates": all_contracts,
        "safe_replay_count": len(safe_results),
        "safe_replay_results": safe_results,
        "form_contract_signal": form_contract_signal,
        "js_contract_signal": js_contract_signal,
        "safe_replay_ok": safe_replay_ok,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "default_list_replay_executed": bool(safe_results),
            "committee_query_executed": committee_query_executed,
            "target_query_executed": target_query_executed,
            "global_2018_date_promoted_to_post_date": False,
            "list_contract_gap_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "source_closure_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nBOARD SURFACE")
    print("-" * 78)
    print(f"HTTP: {f.get('http')}")
    print(f"FINAL URL: {f.get('final_url')}")
    print(f"TITLE: {extract_title(html)}")
    print(f"FORM COUNT: {len(forms)}")
    for form in forms:
        print(f"FORM [{form['index']:02d}] ID={form['id']} NAME={form['name']} METHOD={form['method']} ACTION={form['action']}")
        print(f"  ONSUBMIT: {form['onsubmit']}")
        print(f"  SEARCH CONTROLS: {[(c.get('name'), c.get('value')) for c in form['search_controls']]}")
        print(f"  PAGE CONTROLS: {[(c.get('name'), c.get('value')) for c in form['page_controls']]}")
        print(f"  BOARD-ID CONTROLS: {[(c.get('name'), c.get('value')) for c in form['board_id_controls']]}")

    print("\nSCRIPT / HANDLER CONTRACTS")
    print("-" * 78)
    print(f"SAME-HOST SCRIPT COUNT: {len(srcs)}")
    print(f"SCRIPT FETCH COUNT: {len(script_results)}")
    print(f"INLINE SCRIPT COUNT: {len(inline)}")
    print(f"INLINE FUNCTION NAMES: {sorted(set(inline_functions))}")
    print(f"HANDLER COUNT: {len(handlers)}")
    for i, h in enumerate(handlers[:40], 1):
        print(f"HANDLER [{i:02d}] href={h.get('href')} onclick={h.get('onclick')} data={h.get('data')}")
    print(f"CONTRACT CANDIDATE COUNT: {len(all_contracts)}")
    for i, c in enumerate(all_contracts[:50], 1):
        print(f"CONTRACT [{i:02d}] {c['url']} | SOURCE={c['source']}")
    for s in script_results:
        if s["page_function_hits"] or s["search_function_hits"] or s["contract_count"]:
            print(f"SCRIPT {s['url']} | HTTP={s.get('http')} | PAGE_FUNCS={s['page_function_hits']} | SEARCH_FUNCS={s['search_function_hits']} | CONTRACTS={s['contract_count']}")

    print("\nSAFE DEFAULT-LIST REPLAYS")
    print("-" * 78)
    for i, r in enumerate(safe_results, 1):
        print(f"REPLAY [{i:02d}] FORM={r['form_index']} METHOD={r['method']} URL={r['url']}")
        print(f"  HTTP: {r.get('http')}")
        print(f"  FINAL URL: {r.get('final_url')}")
        print(f"  TITLE: {r.get('title')}")
        print(f"  BOARD IDENTITY SIGNALS: {r.get('board_identity_signals')}")
        print(f"  TARGET VISIBLE: {r.get('target_visible')}")
        print(f"  COMMITTEE TERM VISIBLE: {r.get('committee_term_visible')}")

    print("\n" + "=" * 78)
    print("LIST CONTRACT SUMMARY")
    print("=" * 78)
    print(f"FORM CONTRACT SIGNAL: {form_contract_signal}")
    print(f"JS CONTRACT SIGNAL: {js_contract_signal}")
    print(f"SAFE REPLAY OK: {safe_replay_ok}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Committee query executed: False")
    print("Target query executed: False")
    print("2018 global date promoted to post date: False")
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Source closure allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S226J input exists": out["s226j_input_exists"] is True,
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOARD_LIST_CONTRACT_QUALIFIED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOARD_LIST_SURFACE_FOUND_CONTRACT_PARTIAL",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_BOARD_LIST_CONTRACT_TECHNICAL_UNKNOWN",
        },
        "committee query not executed": out["summary"]["committee_query_executed"] is False,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "global 2018 date not post date": out["summary"]["global_2018_date_promoted_to_post_date"] is False,
        "list contract gap not legal absence": out["summary"]["list_contract_gap_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "source closure blocked": out["summary"]["source_closure_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": out["summary"]["site_positive_allowed"] is False and out["summary"]["site_negative_allowed"] is False,
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
        raise AssertionError("S226K validation failed")


if __name__ == "__main__":
    main()
