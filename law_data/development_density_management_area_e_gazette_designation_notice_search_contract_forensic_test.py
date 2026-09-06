# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_designation_notice_search_contract_forensic.json"

BASE_URL = "https://www.gwanbo.go.kr/"
ENTRY = urljoin(BASE_URL, "main.do")
BASIC = urljoin(BASE_URL, "user/search/searchKeyword.do")
ADVANCED = urljoin(BASE_URL, "user/search/searchDetail.do")
TARGET = "개발밀도관리구역"
POSITIVE_CONTROL = "성남시"
UA = "Mozilla/5.0"
MAX = 8 * 1024 * 1024


def dec(b: bytes):
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", errors="ignore"), "utf-8-ignore"


def clean(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<script\b[^>]*>.*?</script>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<style\b[^>]*>.*?</style>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def read_body(r):
    b = bytearray()
    overflow = False
    try:
        for chunk in r.iter_content(65536):
            if not chunk:
                continue
            if len(b) + len(chunk) > MAX:
                overflow = True
                break
            b.extend(chunk)
    finally:
        r.close()
    text, enc = dec(bytes(b))
    return bytes(b), text, enc, overflow


def get(session, url, *, params=None, referer=None):
    headers = {"Referer": referer} if referer else {}
    try:
        r = session.get(url, params=params, headers=headers, timeout=60, allow_redirects=True, stream=True)
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


def form_contracts(text: str, base_url: str):
    out = []
    for fm in re.finditer(r"<form\b([^>]*)>(.*?)</form>", text or "", re.I | re.S):
        attrs = fm.group(1)
        body = fm.group(2)
        action_m = re.search(r"\baction=[\"']([^\"']*)", attrs, re.I)
        method_m = re.search(r"\bmethod=[\"']([^\"']*)", attrs, re.I)
        id_m = re.search(r"\b(?:id|name)=[\"']([^\"']+)", attrs, re.I)
        action = urljoin(base_url, html.unescape(action_m.group(1))) if action_m else None
        method = (method_m.group(1).upper() if method_m else "GET")
        fields = []
        for m in re.finditer(r"<(input|select|textarea)\b([^>]*)>", body, re.I | re.S):
            tag = m.group(1).lower()
            a = m.group(2)
            name_m = re.search(r"\bname=[\"']([^\"']+)", a, re.I)
            id2_m = re.search(r"\bid=[\"']([^\"']+)", a, re.I)
            type_m = re.search(r"\btype=[\"']([^\"']+)", a, re.I)
            value_m = re.search(r"\bvalue=[\"']([^\"']*)", a, re.I)
            fields.append({
                "tag": tag,
                "name": name_m.group(1) if name_m else None,
                "id": id2_m.group(1) if id2_m else None,
                "type": type_m.group(1) if type_m else None,
                "value": html.unescape(value_m.group(1)) if value_m else None,
            })
        out.append({
            "form_id_or_name": id_m.group(1) if id_m else None,
            "action": action,
            "method": method,
            "fields": fields,
        })
    return out


def extract_submit_signals(text: str):
    endpoints = sorted(set(re.findall(r"[A-Za-z0-9_./-]+\.do(?:\?[^\"'<>\s]*)?", text or "", re.I)))
    contexts = []
    patterns = [
        r"\.submit\s*\(",
        r"action\s*=",
        r"location\.href",
        r"location\.replace",
        r"\$\.ajax",
        r"\$\.post",
        r"\$\.get",
        r"url\s*:",
    ]
    joined = re.compile("|".join(patterns), re.I)
    for m in joined.finditer(text or ""):
        ctx = re.sub(r"\s+", " ", (text or "")[max(0, m.start()-900):min(len(text or ""), m.start()+2600)]).strip()
        if ctx not in contexts:
            contexts.append(ctx[:3500])
        if len(contexts) >= 50:
            break
    return {"endpoints": endpoints[:200], "submit_contexts": contexts}


def script_sources(text: str):
    return [html.unescape(x) for x in re.findall(r"<script\b[^>]*src=[\"']([^\"']+)[\"']", text or "", re.I)]


def likely_search_fields(forms):
    tokens = ("search", "query", "keyword", "word", "text", "title", "contents", "org", "dept", "from", "to", "date", "page", "sort", "gubun", "type", "category", "kind")
    found = []
    for form in forms:
        for field in form["fields"]:
            key = " ".join(str(field.get(k) or "") for k in ("name", "id")).lower()
            if any(t in key for t in tokens):
                found.append(field)
    return found


def main():
    print("=" * 76)
    print("E-GAZETTE UQQ700 DESIGNATION NOTICE SEARCH CONTRACT FORENSIC - S220")
    print("=" * 76)
    print("Target:", TARGET)
    print("Source family: E_GAZETTE")
    print("Purpose: recover official search form/action/parameter contract only")
    print("Search hit != designation fact")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})

    entry = get(s, ENTRY)
    basic = get(s, BASIC, referer=ENTRY)
    advanced = get(s, ADVANCED, referer=ENTRY)

    pages = {
        "entry": {"url": ENTRY, "resp": entry},
        "basic": {"url": BASIC, "resp": basic},
        "advanced": {"url": ADVANCED, "resp": advanced},
    }

    captures = {}
    external_js = {}
    for name, obj in pages.items():
        r = obj["resp"]
        forms = form_contracts(r["text"], r["final_url"] or obj["url"])
        signals = extract_submit_signals(r["text"])
        scripts = script_sources(r["text"])
        captures[name] = {
            "response": {
                "http": r["http"],
                "final_url": r["final_url"],
                "bytes": len(r["body"]),
                "encoding": r["encoding"],
                "overflow": r["overflow"],
                "error": r["error"],
                "content_type": r["content_type"],
            },
            "forms": forms,
            "likely_search_fields": likely_search_fields(forms),
            "submit_signals": signals,
            "script_srcs": scripts[:100],
            "visible_contains_advanced_search": "고급 검색" in clean(r["text"]) or "고급검색" in clean(r["text"]),
            "visible_contains_basic_search": "기본 검색" in clean(r["text"]) or "기본검색" in clean(r["text"]),
        }

        for src in scripts:
            abs_url = urljoin(r["final_url"] or obj["url"], src)
            if abs_url in external_js:
                continue
            if not re.search(r"search|gwanbo|common|main|user", abs_url, re.I):
                continue
            er = get(s, abs_url, referer=r["final_url"] or obj["url"])
            external_js[abs_url] = {
                "http": er["http"],
                "bytes": len(er["body"]),
                "error": er["error"],
                "overflow": er["overflow"],
                "signals": extract_submit_signals(er["text"]) if er["http"] == 200 else {},
            }
            if len(external_js) >= 24:
                break

    all_forms = captures["basic"]["forms"] + captures["advanced"]["forms"]
    nonempty_actions = [f for f in all_forms if f.get("action")]
    candidate_actions = sorted(set(f["action"] for f in nonempty_actions if "search" in (f["action"] or "").lower()))
    field_names = sorted(set(
        field.get("name")
        for form in all_forms
        for field in form.get("fields", [])
        if field.get("name")
    ))

    endpoint_hints = sorted(set(
        captures["basic"]["submit_signals"]["endpoints"]
        + captures["advanced"]["submit_signals"]["endpoints"]
        + [ep for x in external_js.values() for ep in x.get("signals", {}).get("endpoints", [])]
    ))
    search_endpoint_hints = [x for x in endpoint_hints if re.search(r"search|list|result|keyword|detail", x, re.I)]

    technical_unknown_count = sum(
        1 for r in (entry, basic, advanced)
        if r["http"] != 200 or r["error"] or r["overflow"]
    )

    contract_signal_observed = bool(candidate_actions or search_endpoint_hints or field_names)
    contract_qualified = (
        technical_unknown_count == 0
        and captures["basic"]["response"]["http"] == 200
        and captures["advanced"]["response"]["http"] == 200
        and contract_signal_observed
        and len(field_names) > 0
    )

    semantic = (
        "E_GAZETTE_SEARCH_CONTRACT_FORENSIC_CAPTURED"
        if contract_qualified
        else "E_GAZETTE_SEARCH_CONTRACT_FORENSIC_UNRESOLVED"
    )
    next_action = (
        "BUILD_S221_BOUNDED_POSITIVE_CONTROL_REPLAY_USING_CAPTURED_SEARCH_CONTRACT"
        if contract_qualified
        else "INSPECT_FORM_ACTION_AND_JS_SUBMIT_CONTRACT_BEFORE_QUERY_REPLAY"
    )

    out = {
        "step": "STEP 17-21-C-16-8-T-114-S220",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "source_role": "OFFICIAL_NOTICE_IDENTITY_DISCOVERY_CANDIDATE",
        "official_source": {
            "base": BASE_URL,
            "entry": ENTRY,
            "basic_search": BASIC,
            "advanced_search": ADVANCED,
        },
        "positive_control_term_reserved_for_next_stage": POSITIVE_CONTROL,
        "pages": captures,
        "external_js": external_js,
        "contract": {
            "candidate_form_actions": candidate_actions,
            "all_field_names": field_names,
            "search_endpoint_hints": search_endpoint_hints[:100],
            "contract_signal_observed": contract_signal_observed,
            "search_contract_qualified_for_positive_control_replay": contract_qualified,
        },
        "summary": {
            "technical_unknown_count": technical_unknown_count,
            "semantic_state": semantic,
            "next_action": next_action,
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

    print("ENTRY HTTP:", entry["http"], "ERROR:", entry["error"])
    print("BASIC HTTP:", basic["http"], "FORMS:", len(captures["basic"]["forms"]))
    print("ADVANCED HTTP:", advanced["http"], "FORMS:", len(captures["advanced"]["forms"]))
    print("CANDIDATE FORM ACTIONS:", candidate_actions)
    print("FIELD NAMES:", field_names)
    print("SEARCH ENDPOINT HINTS:", search_endpoint_hints[:50])

    print("\nSUMMARY")
    print("Search contract signal observed:", contract_signal_observed)
    print("Search contract qualified for positive control replay:", contract_qualified)
    print("Technical unknown count:", technical_unknown_count)
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution:", out["summary"]["uqq700_final_resolution"])
    print("Output:", OUT)

    checks = {
        "entry 200": entry["http"] == 200,
        "basic search 200": basic["http"] == 200,
        "advanced search 200": advanced["http"] == 200,
        "technical unknown zero": technical_unknown_count == 0,
        "search contract signal observed": contract_signal_observed,
        "search contract qualified only for positive control": contract_qualified,
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
        raise AssertionError("S220 e-gazette search contract forensic failed")


if __name__ == "__main__":
    main()
