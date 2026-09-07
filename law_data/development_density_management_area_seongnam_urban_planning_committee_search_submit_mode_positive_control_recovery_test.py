# -*- coding: utf-8 -*-
from __future__ import annotations

import itertools
import json
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path
from urllib.parse import urlencode

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
S226M_OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_curpage_row_historical_coverage.json"
S226O_OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_search_contract_positive_control_terminal_reconciliation.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_search_submit_mode_positive_control_recovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
BOARD_BASE = "https://www.seongnam.go.kr/ct-bbs020102"
POSITIVE_CONTROL_TITLE = "2025년 제6회 성남시 도시계획위원회 개최 결과"
POSITIVE_CONTROL_PSTSN = "374215"
MAX_PROBES = 36

MOVE_RE = re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
TOTAL_PAGE_RE = re.compile(r"var\s+totalPage\s*=\s*(\d+)", re.I)
FUNCTION_NAMES = ["fn_srch_list", "fn_select_change"]


def curl_request(url: str, *, method: str = "GET", data: str | None = None) -> dict:
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


def attr_map(attrs: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in re.finditer(r'''(?is)([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?:(["'])(.*?)\2|([^\s>]+))''', attrs or ""):
        out[m.group(1).lower()] = unescape(m.group(3) if m.group(2) else m.group(4) or "")
    return out


def extract_function_body(html: str, name: str) -> str | None:
    m = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", html or "", re.I)
    if not m:
        return None
    i = m.end()
    depth = 1
    quote = None
    escape = False
    while i < len(html):
        ch = html[i]
        if quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
        else:
            if ch in "'\"`":
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return html[m.start(): i + 1]
        i += 1
    return html[m.start(): min(len(html), m.start() + 8000)]


def extract_form_contract(html: str) -> dict:
    for fm in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html or ""):
        fattrs = attr_map(fm.group(1))
        if (fattrs.get("id") or "") != "searchVO" and (fattrs.get("name") or "") != "searchVO":
            continue
        inner = fm.group(2)
        controls = []
        defaults: dict[str, str] = {}
        option_map: dict[str, list[dict]] = {}
        radio_map: dict[str, list[dict]] = {}

        for im in re.finditer(r"(?is)<input\b([^>]*)>", inner):
            raw = im.group(1)
            a = attr_map(raw)
            name = a.get("name")
            if not name:
                continue
            typ = (a.get("type") or "text").lower()
            value = a.get("value", "")
            checked = bool(re.search(r"(?:^|\s)checked(?:\s|=|$)", raw, re.I))
            controls.append({"tag": "input", "name": name, "type": typ, "value": value, "checked": checked})
            if typ in {"radio", "checkbox"}:
                radio_map.setdefault(name, []).append({"value": value, "checked": checked})
                if checked:
                    defaults[name] = value
            elif typ not in {"submit", "button", "image", "file"}:
                defaults[name] = value

        for sm in re.finditer(r"(?is)<select\b([^>]*)>(.*?)</select>", inner):
            sa = attr_map(sm.group(1))
            name = sa.get("name")
            if not name:
                continue
            opts = []
            selected_value = None
            for om in re.finditer(r"(?is)<option\b([^>]*)>(.*?)</option>", sm.group(2)):
                raw = om.group(1)
                oa = attr_map(raw)
                value = oa.get("value", "")
                label = clean_html(om.group(2))
                selected = bool(re.search(r"(?:^|\s)selected(?:\s|=|$)", raw, re.I))
                opts.append({"value": value, "label": label, "selected": selected})
                if selected:
                    selected_value = value
            if selected_value is None and opts:
                selected_value = opts[0]["value"]
            if selected_value is not None:
                defaults[name] = selected_value
            option_map[name] = opts
            controls.append({"tag": "select", "name": name, "options": opts})

        return {
            "found": True,
            "method": (fattrs.get("method") or "GET").upper(),
            "action": fattrs.get("action") or BOARD_BASE,
            "defaults": defaults,
            "controls": controls,
            "options": option_map,
            "radios": radio_map,
        }
    return {"found": False, "method": None, "action": None, "defaults": {}, "controls": [], "options": {}, "radios": {}}


def extract_pstsns(html: str) -> list[str]:
    out = []
    for m in MOVE_RE.finditer(html or ""):
        sn = m.group(1)
        if sn not in out:
            out.append(sn)
    return out


def surface_signature(html: str) -> dict:
    total = TOTAL_PAGE_RE.search(html or "")
    return {
        "total_pages": int(total.group(1)) if total else None,
        "pstsns": extract_pstsns(html),
        "text": clean_html(html),
    }


def option_values(form: dict, name: str) -> list[str]:
    vals = [str(x.get("value", "")) for x in form.get("options", {}).get(name, [])]
    return list(dict.fromkeys(vals))


def radio_values(form: dict, name: str) -> list[str]:
    vals = [str(x.get("value", "")) for x in form.get("radios", {}).get(name, [])]
    return list(dict.fromkeys(vals))


def infer_js_values(functions: dict[str, str | None], field: str) -> list[str]:
    vals = []
    patterns = [
        rf'''[#\[]?{re.escape(field)}[^\n]{{0,80}}?\.val\(\s*["']([^"']*)["']\s*\)''',
        rf'''getElementById\(\s*["']{re.escape(field)}["']\s*\)[^\n]{{0,80}}?\.value\s*=\s*["']([^"']*)["']''',
    ]
    blob = "\n".join(x for x in functions.values() if x)
    for pat in patterns:
        for m in re.finditer(pat, blob, re.I):
            vals.append(m.group(1))
    return list(dict.fromkeys(vals))


def build_probe_payloads(form: dict, functions: dict[str, str | None]) -> list[dict]:
    defaults = dict(form.get("defaults") or {})
    defaults["pstSn"] = "0"
    defaults["srchText"] = POSITIVE_CONTROL_TITLE

    srch_type_vals = option_values(form, "srchTypeCd") or radio_values(form, "srchTypeCd")
    srch_dt_vals = option_values(form, "srchDtType") or radio_values(form, "srchDtType")
    srch_type_vals += infer_js_values(functions, "srchTypeCd")
    srch_dt_vals += infer_js_values(functions, "srchDtType")
    srch_type_vals = list(dict.fromkeys(srch_type_vals))
    srch_dt_vals = list(dict.fromkeys(srch_dt_vals))

    # Prefer values actually exposed by the form/JS. Empty/default variants are retained as controls.
    type_candidates = [defaults.get("srchTypeCd", "")] + srch_type_vals
    dt_candidates = [defaults.get("srchDtType", "")] + srch_dt_vals
    type_candidates = list(dict.fromkeys(type_candidates)) or [""]
    dt_candidates = list(dict.fromkeys(dt_candidates)) or [""]

    probes = []
    seen = set()
    for typ, dt in itertools.product(type_candidates, dt_candidates):
        p = dict(defaults)
        p["srchTypeCd"] = typ
        p["srchDtType"] = dt
        key = tuple(sorted(p.items()))
        if key in seen:
            continue
        seen.add(key)
        probes.append({"mode": "POST_FORM", "payload": p, "srchTypeCd": typ, "srchDtType": dt})
        if len(probes) >= MAX_PROBES:
            break

    # Also replay browser-style GET query combinations if form action semantics turn out to be GET-sensitive.
    for typ, dt in itertools.product(type_candidates, dt_candidates):
        p = dict(defaults)
        p["srchTypeCd"] = typ
        p["srchDtType"] = dt
        key = ("GET", tuple(sorted(p.items())))
        if key in seen:
            continue
        seen.add(key)
        probes.append({"mode": "GET_QUERY", "payload": p, "srchTypeCd": typ, "srchDtType": dt})
        if len(probes) >= MAX_PROBES:
            break
    return probes[:MAX_PROBES]


def run_probe(probe: dict, baseline: dict) -> dict:
    encoded = urlencode(probe["payload"], doseq=True)
    if probe["mode"] == "GET_QUERY":
        f = curl_request(f"{BOARD_BASE}?{encoded}")
    else:
        f = curl_request(BOARD_BASE, method="POST", data=encoded)
    html, enc = decode_body(f.pop("body"))
    sig = surface_signature(html)
    identity_visible = POSITIVE_CONTROL_PSTSN in sig["pstsns"] or POSITIVE_CONTROL_PSTSN in html
    exact_title_visible = POSITIVE_CONTROL_TITLE in sig["text"]
    differs = sig["pstsns"] != baseline["pstsns"] or sig["total_pages"] != baseline["total_pages"]
    narrowed = (
        (sig["total_pages"] is not None and baseline["total_pages"] is not None and sig["total_pages"] < baseline["total_pages"])
        or len(sig["pstsns"]) < len(baseline["pstsns"])
    )
    qualified = bool(f.get("http") == "200" and differs and narrowed and (identity_visible or exact_title_visible))
    return {
        "mode": probe["mode"],
        "srchTypeCd": probe["srchTypeCd"],
        "srchDtType": probe["srchDtType"],
        "http": f.get("http"),
        "final_url": f.get("final_url"),
        "charset": enc,
        "total_pages": sig["total_pages"],
        "row_count": len(sig["pstsns"]),
        "pstsns": sig["pstsns"],
        "positive_control_pstsn_visible": identity_visible,
        "exact_title_visible": exact_title_visible,
        "differs_from_baseline": differs,
        "narrowed_from_baseline": narrowed,
        "qualified_search_contract": qualified,
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE SEARCH SUBMIT MODE / POSITIVE CONTROL RECOVERY - S226P")
    print("=" * 78)
    print("Purpose: recover the actual search submit mode using only a verified positive control")
    print(f"Positive control title: {POSITIVE_CONTROL_TITLE}")
    print(f"Positive control pstSn: {POSITIVE_CONTROL_PSTSN}")
    print("UQQ700 target query: NOT EXECUTED")
    print("Search contract recovery only")
    print("Negative evidence: DISABLED")
    print("SITE FALSE inference: BLOCKED")
    print("Source closure: BLOCKED until search contract is verified")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    m_exists = S226M_OUT.exists()
    o_exists = S226O_OUT.exists()
    m = json.loads(S226M_OUT.read_text(encoding="utf-8")) if m_exists else {}
    o = json.loads(S226O_OUT.read_text(encoding="utf-8")) if o_exists else {}

    base = curl_request(BOARD_BASE)
    base_html, base_enc = decode_body(base.pop("body"))
    baseline = surface_signature(base_html)
    form = extract_form_contract(base_html)
    functions = {name: extract_function_body(base_html, name) for name in FUNCTION_NAMES}

    print("\nFORM CONTRACT")
    print("-" * 78)
    print(f"SEARCH FORM FOUND: {form.get('found')}")
    print(f"FORM METHOD: {form.get('method')}")
    print(f"FORM ACTION: {form.get('action')}")
    print(f"DEFAULTS: {form.get('defaults')}")
    print(f"SELECT OPTIONS: {json.dumps(form.get('options'), ensure_ascii=False)}")
    print(f"RADIOS: {json.dumps(form.get('radios'), ensure_ascii=False)}")
    for name, body in functions.items():
        print(f"FUNCTION {name}:")
        print(body or "NOT FOUND")

    probes = build_probe_payloads(form, functions) if form.get("found") else []
    results = [run_probe(p, baseline) for p in probes]
    qualified = [r for r in results if r["qualified_search_contract"]]
    best = qualified[0] if qualified else None

    if best:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_POSITIVE_CONTROL_SEARCH_SUBMIT_MODE_QUALIFIED"
        semantic = "FORM_OR_JS_DERIVED_SEARCH_MODE_FILTERED_THE_BOARD_AND_RECOVERED_VERIFIED_POSITIVE_CONTROL_IDENTITY"
        next_action = "REPLAY_UQQ700_ONLY_WITH_THE_QUALIFIED_SEARCH_MODE_AND_RECONCILE_PRECURSOR_RESULT_NON_NEGATIVELY"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_SEARCH_SUBMIT_MODE_TECHNICAL_UNKNOWN"
        semantic = "FORM_SELECT_RADIO_HIDDEN_AND_JS_DERIVED_POSITIVE_CONTROL_REPLAYS_DID_NOT_YET_VERIFY_SERVER_SIDE_FILTERING"
        next_action = "HARDEN_BROWSER_SUBMIT_EVENT_OR_REQUEST_PARAMETER_CAPTURE_WITH_POSITIVE_CONTROL_ONLY"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226P",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s226m_input_exists": m_exists,
        "s226o_input_exists": o_exists,
        "historical_coverage_qualified": bool(m.get("full_11_page_coverage_verified") and m.get("historical_coverage_observed")),
        "prior_search_contract_verified": bool(o.get("search_contract_verified")),
        "baseline": {
            "http": base.get("http"),
            "charset": base_enc,
            "total_pages": baseline["total_pages"],
            "first_page_pstsns": baseline["pstsns"],
        },
        "form_contract": form,
        "function_contracts": functions,
        "probe_count": len(results),
        "probe_results": results,
        "qualified_probe_count": len(qualified),
        "best_qualified_probe": best,
        "search_submit_mode_verified": best is not None,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "positive_control_only": True,
            "target_query_executed": False,
            "source_family_operationally_closed": False,
            "operational_gap_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
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

    print("\nBASELINE")
    print("-" * 78)
    print(f"HTTP: {base.get('http')}")
    print(f"TOTAL PAGES: {baseline['total_pages']}")
    print(f"FIRST PAGE PSTSNS: {baseline['pstsns']}")

    print("\nPOSITIVE-CONTROL PROBES")
    print("-" * 78)
    for i, r in enumerate(results, 1):
        print(
            f"PROBE {i:02d} | MODE={r['mode']} | srchTypeCd={r['srchTypeCd']!r} | "
            f"srchDtType={r['srchDtType']!r} | HTTP={r['http']} | PAGES={r['total_pages']} | "
            f"ROWS={r['row_count']} | CONTROL={r['positive_control_pstsn_visible']} | "
            f"TITLE={r['exact_title_visible']} | DIFF={r['differs_from_baseline']} | "
            f"NARROW={r['narrowed_from_baseline']} | QUALIFIED={r['qualified_search_contract']}"
        )
        if r["pstsns"]:
            print(f"  PSTSNS={r['pstsns']}")

    print("\n" + "=" * 78)
    print("SEARCH SUBMIT MODE RESOLUTION")
    print("=" * 78)
    print(f"PROBE COUNT: {len(results)}")
    print(f"QUALIFIED PROBE COUNT: {len(qualified)}")
    print(f"SEARCH SUBMIT MODE VERIFIED: {best is not None}")
    print(f"BEST QUALIFIED PROBE: {json.dumps(best, ensure_ascii=False) if best else None}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Target query executed: False")
    print("Source family operationally closed: False")
    print("Negative evidence allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S226M input exists": m_exists,
        "S226O input exists": o_exists,
        "historical coverage remains qualified": out["historical_coverage_qualified"] is True,
        "positive control only": out["summary"]["positive_control_only"] is True,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "source family closure blocked": out["summary"]["source_family_operationally_closed"] is False,
        "operational gap not legal absence": out["summary"]["operational_gap_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": out["summary"]["site_positive_allowed"] is False and out["summary"]["site_negative_allowed"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_POSITIVE_CONTROL_SEARCH_SUBMIT_MODE_QUALIFIED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_SEARCH_SUBMIT_MODE_TECHNICAL_UNKNOWN",
        },
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
        raise AssertionError("S226P validation failed")


if __name__ == "__main__":
    main()
