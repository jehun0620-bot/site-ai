# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
S221C = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_f_searchdetail_form_state_forensic.json"
S221D = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_exact_positive_control_replay.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_live_search_form_response_state_forensic.json"

BASE_URL = "https://www.gwanbo.go.kr/"
ENTRY = urljoin(BASE_URL, "main.do")
SEARCH = urljoin(BASE_URL, "user/search/searchKeyword.do")
TARGET = "개발밀도관리구역"
POSITIVE_CONTROL = "성남시"
MAX_BYTES = 8 * 1024 * 1024


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


def visible_text(s: str) -> str:
    s = re.sub(r"<script\b.*?</script>", " ", s or "", flags=re.I | re.S)
    s = re.sub(r"<style\b.*?</style>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return norm(html.unescape(s))


def extract_scripts(text: str):
    rows = []
    for m in re.finditer(r"<script\b([^>]*)>(.*?)</script>", text or "", re.I | re.S):
        attrs = m.group(1)
        body = m.group(2)
        src_m = re.search(r"src\s*=\s*['\"]([^'\"]+)['\"]", attrs, re.I)
        rows.append({"src": html.unescape(src_m.group(1)) if src_m else None, "body": body[:50000]})
    return rows


def extract_forms(text: str):
    rows = []
    for idx, m in enumerate(re.finditer(r"<form\b([^>]*)>(.*?)</form>", text or "", re.I | re.S), 1):
        attrs = m.group(1)
        body = m.group(2)
        name_m = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", attrs, re.I)
        id_m = re.search(r"id\s*=\s*['\"]([^'\"]+)['\"]", attrs, re.I)
        action_m = re.search(r"action\s*=\s*['\"]([^'\"]*)['\"]", attrs, re.I)
        method_m = re.search(r"method\s*=\s*['\"]([^'\"]*)['\"]", attrs, re.I)
        fields = []
        for im in re.finditer(r"<(input|select|textarea)\b([^>]*)>", body, re.I | re.S):
            tag = im.group(1).lower()
            a = im.group(2)
            nm = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", a, re.I)
            idm = re.search(r"id\s*=\s*['\"]([^'\"]+)['\"]", a, re.I)
            typ = re.search(r"type\s*=\s*['\"]([^'\"]+)['\"]", a, re.I)
            val = re.search(r"value\s*=\s*['\"]([^'\"]*)['\"]", a, re.I)
            fields.append({
                "tag": tag,
                "name": nm.group(1) if nm else None,
                "id": idm.group(1) if idm else None,
                "type": typ.group(1) if typ else None,
                "value": html.unescape(val.group(1)) if val else None,
            })
        rows.append({
            "index": idx,
            "name": name_m.group(1) if name_m else None,
            "id": id_m.group(1) if id_m else None,
            "action": html.unescape(action_m.group(1)) if action_m else None,
            "method": method_m.group(1).upper() if method_m else None,
            "fields": fields,
        })
    return rows


def extract_jsessionid(text: str):
    vals = []
    for m in re.finditer(r"searchKeyword\.do;jsessionid=([A-Za-z0-9._-]+)", text or "", re.I):
        v = m.group(1)
        if v not in vals:
            vals.append(v)
    return vals


def extract_focus_snippets(text: str):
    patterns = [
        r"function\s+f_searchDetail\s*\([^)]*\)\s*\{.{0,8000}?\}",
        r"searchKeyword\.do;jsessionid=[^'\"\s)]+",
        r"insertKeyword\.do.{0,1000}",
        r"getTrsnrOfctt(?:Dtl)?List\.do.{0,1500}",
        r"searchKeyword.{0,1200}",
        r"pKeyword.{0,1200}",
        r"result.{0,1200}",
        r"paging.{0,1200}",
    ]
    rows = []
    for pat in patterns:
        for m in re.finditer(pat, text or "", re.I | re.S):
            s = norm(m.group(0))[:8000]
            if s and s not in rows:
                rows.append(s)
    return rows[:100]


def extract_ajax_endpoints(text: str):
    eps = []
    for m in re.finditer(r"['\"](/user/search/[A-Za-z0-9_./?=&;-]+\.do(?:\?[^'\"]*)?)['\"]", text or "", re.I):
        v = html.unescape(m.group(1))
        if v not in eps:
            eps.append(v)
    return eps[:200]


def detect_result_containers(text: str):
    rows = []
    for m in re.finditer(r"<(div|table|tbody|ul)\b([^>]*)>", text or "", re.I):
        attrs = m.group(2)
        idm = re.search(r"id\s*=\s*['\"]([^'\"]+)['\"]", attrs, re.I)
        clsm = re.search(r"class\s*=\s*['\"]([^'\"]+)['\"]", attrs, re.I)
        blob = " ".join(x for x in [idm.group(1) if idm else "", clsm.group(1) if clsm else ""] if x)
        if re.search(r"result|search|list|paging|content|board|tbl", blob, re.I):
            rows.append({"tag": m.group(1).lower(), "id": idm.group(1) if idm else None, "class": clsm.group(1) if clsm else None})
    uniq = []
    for r in rows:
        if r not in uniq:
            uniq.append(r)
    return uniq[:120]


def main():
    print("=" * 78)
    print("E-GAZETTE LIVE SEARCH FORM/RESPONSE STATE FORENSIC - S221E")
    print("=" * 78)
    print("Target UQQ700 query is NOT replayed")
    print("No positive-control replay is performed in this stage")
    print("Purpose: inspect live form/session/result loading state only")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s221c = json.loads(S221C.read_text(encoding="utf-8"))
    s221d = json.loads(S221D.read_text(encoding="utf-8"))
    gate_c = bool((s221c.get("recovered_form_state") or {}).get("exact_function_state_recovered"))
    gate_d = (s221d.get("summary") or {}).get("semantic_state") == "E_GAZETTE_EXACT_POSITIVE_CONTROL_REPLAY_UNRESOLVED"
    gate_safe = (s221d.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    if not (gate_c and gate_d and gate_safe):
        raise AssertionError("S221E prerequisite gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    entry = fetch(session, ENTRY)
    search = fetch(session, SEARCH, referer=ENTRY)

    cookies = {c.name: c.value for c in session.cookies}
    live_text = search["text"]
    forms = extract_forms(live_text)
    scripts = extract_scripts(live_text)
    inline_js = "\n".join(x["body"] for x in scripts if not x["src"])
    combined = live_text + "\n" + inline_js

    jsessionids = extract_jsessionid(combined)
    jsession_cookie = cookies.get("JSESSIONID")
    cookie_path_match = bool(jsession_cookie and jsessionids and any(jsession_cookie == x for x in jsessionids))
    ajax_endpoints = extract_ajax_endpoints(combined)
    snippets = extract_focus_snippets(combined)
    containers = detect_result_containers(live_text)

    focus_fields = []
    for f in forms:
        for fld in f["fields"]:
            name = fld.get("name") or fld.get("id") or ""
            if name in {"searchKeyword", "pKeyword", "query", "pQuery_tmp", "old_query", "searchGubun", "pageNo", "sort", "category_num", "organ_code", "organ_name"}:
                focus_fields.append({"form_index": f["index"], **fld})

    dynamic_result_endpoints = [x for x in ajax_endpoints if re.search(r"getTrsnrOfctt|List|Dtl|search", x, re.I)]
    shell_paging_only_suspected = bool(
        (s221d.get("summary") or {}).get("pagination_signal_observed")
        and not (s221d.get("summary") or {}).get("result_identity_signal_observed")
    )

    state_recovered = bool(
        search["http"] == 200
        and not search["error"]
        and not search["overflow"]
        and (len(jsessionids) > 0 or len(forms) > 0 or len(dynamic_result_endpoints) > 0)
    )

    semantic = "E_GAZETTE_LIVE_SEARCH_FORM_RESPONSE_STATE_RECOVERED" if state_recovered else "E_GAZETTE_LIVE_SEARCH_FORM_RESPONSE_STATE_UNRESOLVED"
    next_action = "BUILD_S221F_LIVE_SESSION_PATH_OR_RESULT_AJAX_POSITIVE_CONTROL_REPLAY" if state_recovered else "MANUALLY_INSPECT_LIVE_SEARCH_HTML_BEFORE_ANY_REPLAY"

    out = {
        "step": "STEP 17-21-C-16-8-T-121-S221E",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "source_role": "OFFICIAL_NOTICE_IDENTITY_DISCOVERY_CANDIDATE",
        "input_s221c": str(S221C),
        "input_s221d": str(S221D),
        "entry": {k: entry[k] for k in ("http", "final_url", "bytes", "encoding", "overflow", "error")},
        "search_page": {k: search[k] for k in ("http", "final_url", "bytes", "encoding", "overflow", "error")},
        "cookies": cookies,
        "live_jsessionids": jsessionids,
        "jsession_cookie": jsession_cookie,
        "cookie_matches_path_jsessionid": cookie_path_match,
        "forms": forms,
        "focus_fields": focus_fields,
        "ajax_endpoints": ajax_endpoints,
        "dynamic_result_endpoints": dynamic_result_endpoints,
        "result_containers": containers,
        "focus_snippets": snippets,
        "shell_paging_only_suspected": shell_paging_only_suspected,
        "summary": {
            "live_state_recovered": state_recovered,
            "form_count": len(forms),
            "focus_field_count": len(focus_fields),
            "live_jsessionid_count": len(jsessionids),
            "dynamic_result_endpoint_count": len(dynamic_result_endpoints),
            "result_container_count": len(containers),
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
    print("SEARCH FINAL URL:", search["final_url"])
    print("COOKIE NAMES:", sorted(cookies))
    print("JSESSIONID cookie present:", bool(jsession_cookie))
    print("Live path jsessionid count:", len(jsessionids))
    print("Cookie/path jsessionid exact match:", cookie_path_match)
    print("FORM COUNT:", len(forms))
    print("FOCUS FIELD COUNT:", len(focus_fields))
    print("DYNAMIC RESULT ENDPOINT COUNT:", len(dynamic_result_endpoints))
    print("RESULT CONTAINER COUNT:", len(containers))
    print("Shell paging only suspected:", shell_paging_only_suspected)
    print("Live state recovered:", state_recovered)

    print("\nLIVE FORM SUMMARY")
    for f in forms[:20]:
        print(f"form#{f['index']} name={f['name']!r} id={f['id']!r} method={f['method']!r} action={f['action']!r}")

    print("\nFOCUS FIELDS")
    for i, fld in enumerate(focus_fields[:50], 1):
        print(f"[{i:02d}] form={fld['form_index']} tag={fld['tag']} name={fld['name']!r} id={fld['id']!r} type={fld['type']!r} value={fld['value']!r}")

    print("\nLIVE JSESSIONID VALUES")
    for i, v in enumerate(jsessionids[:20], 1):
        print(f"[{i:02d}] {v}")

    print("\nDYNAMIC RESULT ENDPOINTS")
    for i, ep in enumerate(dynamic_result_endpoints[:40], 1):
        print(f"[{i:02d}] {ep}")

    print("\nRESULT CONTAINERS")
    for i, c in enumerate(containers[:40], 1):
        print(f"[{i:02d}] tag={c['tag']} id={c['id']!r} class={c['class']!r}")

    print("\nFOCUS SNIPPETS")
    for i, s in enumerate(snippets[:20], 1):
        print(f"--- snippet {i:02d} ---")
        print(s)

    print("\nSUMMARY")
    print("Live state recovered:", state_recovered)
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221C form-state gate": gate_c,
        "S221D unresolved gate": gate_d,
        "entry GET 200": entry["http"] == 200 and not entry["error"] and not entry["overflow"],
        "search GET 200": search["http"] == 200 and not search["error"] and not search["overflow"],
        "live state recovered": state_recovered,
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
        raise AssertionError("S221E e-gazette live search form response state forensic failed")


if __name__ == "__main__":
    main()
