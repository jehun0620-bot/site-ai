# -*- coding: utf-8 -*-
"""S93: inspect server-retained search state and pagination serialization for legacy gazette.

S92 proved title POST search is effective while multiple date-filter shapes have no
visible effect on row identities. This stage compares response-side form values and
pagination/search links after a working title control and date probes. It identifies
which submitted parameters the server actually retains/echoes and which parameters
are propagated by pagination.

No UQQ700 target-term search, attachment download, state mutation, negative evidence,
SITE/runtime promotion, or pre-2010 reachability/absence conclusion is allowed.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "development_density_management_area_seongnam_legacy_gazette_date_state_echo_pagination_forensic.json"

URL = "https://www.seongnam.go.kr/bbs010308"
HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_REQ = 6
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

FORM_RE = re.compile(r"<form\b(?P<a>[^>]*)>(?P<b>.*?)</form>", re.I | re.S)
INPUT_RE = re.compile(r"<input\b(?P<a>[^>]*)/?>", re.I | re.S)
SELECT_RE = re.compile(r"<select\b(?P<a>[^>]*)>(?P<b>.*?)</select>", re.I | re.S)
OPTION_RE = re.compile(r"<option\b(?P<a>[^>]*)>(?P<b>.*?)</option>", re.I | re.S)
ANCHOR_RE = re.compile(r"<a\b(?P<a>[^>]*)>(?P<b>.*?)</a>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
TAG_RE = re.compile(r"<[^>]+>", re.S)
GAZ_RE = re.compile(r"성남시보\s*제\s*(\d+)\s*호", re.I)
CALL_RE = re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
PAGINATION_JS_RE = re.compile(r"(?:fn_page|fn_paging|goPage|movePage)\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
STATE_FIELDS = ["srchTypeCd", "srchText", "srchDtType", "srchBgngYmd", "srchEndYmd", "creatrDt", "radio", "curPage", "cntPerPage", "sortType"]


def attrs(raw: str) -> dict[str, str]:
    out = {}
    for m in ATTR_RE.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def rr(r: requests.Response) -> dict:
    return {"http": r.status_code, "url": str(r.url), "host": (urlparse(str(r.url)).hostname or "").lower(), "text": r.text, "bytes": len(r.content)}


def get(session, counter):
    if counter[0] >= MAX_REQ: raise AssertionError("request budget exceeded")
    counter[0] += 1
    return rr(session.get(URL, timeout=TIMEOUT, allow_redirects=True))


def post(session, data, counter):
    if counter[0] >= MAX_REQ: raise AssertionError("request budget exceeded")
    counter[0] += 1
    return rr(session.post(URL, data=data, timeout=TIMEOUT, allow_redirects=True))


def recover_form(text: str) -> dict:
    candidates = []
    for fm in FORM_RE.finditer(text or ""):
        fa = attrs(fm.group("a")); body = fm.group("b"); defaults = {}; controls = []
        for im in INPUT_RE.finditer(body):
            ia = attrs(im.group("a")); name = ia.get("name", ""); typ = ia.get("type", "text").lower(); checked = "checked" in ia
            controls.append({"name": name, "id": ia.get("id", ""), "type": typ, "value": ia.get("value", ""), "checked": checked})
            if name and not (typ in {"radio", "checkbox"} and not checked): defaults[name] = ia.get("value", "")
        for sm in SELECT_RE.finditer(body):
            sa = attrs(sm.group("a")); name = sa.get("name", ""); chosen = ""; opts = []
            for om in OPTION_RE.finditer(sm.group("b")):
                oa = attrs(om.group("a")); value = oa.get("value", ""); selected = "selected" in oa
                opts.append({"value": value, "label": clean(om.group("b")), "selected": selected})
                if selected or chosen == "": chosen = value
            if name: defaults[name] = chosen
        score = sum(k in defaults for k in ["csrfToken", "srchText", "srchTypeCd"])
        candidates.append({"method": fa.get("method", "GET").upper(), "action": urljoin(URL, fa.get("action", "")), "defaults": defaults, "controls": controls, "score": score})
    candidates.sort(key=lambda x: (x["method"] == "POST", x["score"]), reverse=True)
    if not candidates or candidates[0]["method"] != "POST": raise AssertionError("search POST form missing")
    return candidates[0]


def response_state(text: str) -> dict[str, str]:
    state = {}
    for fm in FORM_RE.finditer(text or ""):
        body = fm.group("b")
        local = {}
        for im in INPUT_RE.finditer(body):
            ia = attrs(im.group("a")); name = ia.get("name", "")
            if name in STATE_FIELDS:
                typ = ia.get("type", "text").lower(); checked = "checked" in ia
                if typ in {"radio", "checkbox"} and not checked: continue
                local[name] = ia.get("value", "")
        for sm in SELECT_RE.finditer(body):
            sa = attrs(sm.group("a")); name = sa.get("name", "")
            if name not in STATE_FIELDS: continue
            chosen = ""
            for om in OPTION_RE.finditer(sm.group("b")):
                oa = attrs(om.group("a")); value = oa.get("value", "")
                if "selected" in oa: chosen = value; break
                if chosen == "": chosen = value
            local[name] = chosen
        if any(k in local for k in ["srchText", "srchTypeCd"]):
            state = local; break
    return {k: state.get(k, "") for k in STATE_FIELDS}


def rows(text: str) -> list[tuple[int, str]]:
    out = []; seen = set()
    for am in ANCHOR_RE.finditer(text or ""):
        a = attrs(am.group("a")); label = clean(am.group("b")); gm = GAZ_RE.search(label)
        if not gm: continue
        mm = CALL_RE.search(a.get("href", "") + " " + a.get("onclick", ""))
        if not mm: continue
        key = (int(gm.group(1)), mm.group(1))
        if key not in seen: seen.add(key); out.append(key)
    return out


def pagination_evidence(text: str) -> list[dict]:
    out = []
    for am in ANCHOR_RE.finditer(text or ""):
        a = attrs(am.group("a")); href = html.unescape(a.get("href", "")); onclick = html.unescape(a.get("onclick", "")); label = clean(am.group("b"))
        abs_url = urljoin(URL, href) if href and not href.lower().startswith("javascript:") else ""
        params = dict(parse_qsl(urlparse(abs_url).query, keep_blank_values=True)) if abs_url else {}
        js_page = PAGINATION_JS_RE.search(href + " " + onclick)
        if "curPage" in params or js_page:
            out.append({"text": label, "href": href, "onclick": onclick, "query_params": params, "js_page": js_page.group(1) if js_page else None})
    return out[:30]


def payload(form: dict, extras=None):
    p = dict(form["defaults"]); p["cntPerPage"] = p.get("cntPerPage") or "30"; p["sortType"] = p.get("sortType") or "1"; p["curPage"] = "1"; p["pstSn"] = "0"
    if extras: p.update(extras)
    return p


def run_probe(session, form, counter, label, extras, baseline_ids):
    submitted = payload(form, extras)
    r = post(session, submitted, counter)
    ids = rows(r["text"])
    state = response_state(r["text"])
    pagination = pagination_evidence(r["text"])
    result = {"label": label, "http": r["http"], "official": r["host"] == HOST, "submitted": {k: submitted.get(k, "") for k in STATE_FIELDS}, "response_state": state, "row_count": len(ids), "identities": ids, "same_as_baseline": ids == baseline_ids, "pagination_evidence": pagination}
    print("PROBE:", {k: result[k] for k in ["label", "http", "official", "submitted", "response_state", "row_count", "same_as_baseline"]})
    print("PAGINATION SAMPLE:", pagination[:5])
    return result


def main():
    print("=" * 60); print("SEONGNAM LEGACY GAZETTE DATE STATE ECHO / PAGINATION FORENSIC - S93"); print("=" * 60)
    print("UQQ700 target-term search: DISABLED"); print("Negative evidence: DISABLED"); print("Pre-2010 conclusion: DISABLED")
    s = requests.Session(); s.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"}); c = [0]
    base = get(s, c); form = recover_form(base["text"])
    baseline_r = post(s, payload(form, {"srchTypeCd": "pstTtl", "srchText": ""}), c); baseline_ids = rows(baseline_r["text"])
    print("BASELINE STATE:", response_state(baseline_r["text"])); print("BASELINE ROWS:", baseline_ids)
    probes = []
    probes.append(run_probe(s, form, c, "TITLE_2088_CONTROL", {"srchTypeCd": "pstTtl", "srchText": "2088"}, baseline_ids))
    probes.append(run_probe(s, form, c, "DATE_2099_EMPTY_TYPE", {"srchTypeCd": "pstTtl", "srchText": "", "srchDtType": "", "srchBgngYmd": "2099-01-01", "srchEndYmd": "2099-12-31"}, baseline_ids))
    probes.append(run_probe(s, form, c, "DATE_2099_CREATR_TYPE", {"srchTypeCd": "pstTtl", "srchText": "", "srchDtType": "creatrDt", "creatrDt": "09", "srchBgngYmd": "2099-01-01", "srchEndYmd": "2099-12-31"}, baseline_ids))

    title = probes[0]; date_probes = probes[1:]
    title_echo = title["response_state"].get("srchText") == "2088"
    date_echo_fields = {}
    for field in ["srchDtType", "srchBgngYmd", "srchEndYmd", "creatrDt"]:
        date_echo_fields[field] = [p["response_state"].get(field, "") for p in date_probes]
    retained_date_any = any(any(v for v in values) for values in date_echo_fields.values())
    summary = {
        "request_count": c[0],
        "title_control_effective": not title["same_as_baseline"],
        "title_search_state_echoed": title_echo,
        "date_response_echo_fields": date_echo_fields,
        "date_state_retained_any": retained_date_any,
        "date_filter_effect_observed": any(not p["same_as_baseline"] for p in date_probes),
        "semantic_state": "DATE_STATE_RETAINED_BUT_FILTER_NO_EFFECT" if retained_date_any else "DATE_STATE_NOT_RETAINED_BY_SERVER",
        "negative_evidence_allowed": False,
        "pre2010_reachability_conclusion_allowed": False,
    }
    out = {"step":"STEP 17-21-C-16-8-T-35-S93","target_name":"개발밀도관리구역","standard_code":"UQQ700","resolution_type":"HYBRID_SPATIAL_NOTICE","source_family":"LEGACY_LOCAL_GAZETTE","baseline_identities":baseline_ids,"probes":probes,"summary":summary,"target_term_search_executed":False,"attachment_body_download_executed":False,"state_mutation_executed":False,"negative_evidence_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False,"runtime_registration_allowed":False,"final_positive_promotion_allowed":False}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    vals = {"base transport official":base["http"]==200 and base["host"]==HOST,"search form recovered":form["method"]=="POST","title control effective":summary["title_control_effective"],"request budget respected":c[0]<=MAX_REQ,"UQQ700 target-term search disabled":not out["target_term_search_executed"],"negative evidence disabled":not out["negative_evidence_allowed"],"pre2010 conclusion blocked":not summary["pre2010_reachability_conclusion_allowed"],"unsafe promotion leakage zero":not any(out[k] for k in ["site_positive_allowed","site_negative_allowed","runtime_registration_allowed","final_positive_promotion_allowed"]),"output written":OUT.exists() and OUT.stat().st_size>0}
    print("\nSUMMARY"); [print(f"{k}: {v}") for k,v in summary.items()]; print("Output:", OUT); print("\nVALIDATION"); [print(f"{k}: {v}") for k,v in vals.items()]; print("all_pass:", all(vals.values()))
    if not all(vals.values()): raise AssertionError("S93 date state echo forensic failed")


if __name__ == "__main__": main()
