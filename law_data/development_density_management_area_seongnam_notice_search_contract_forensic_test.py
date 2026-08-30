# -*- coding: utf-8 -*-
"""S74: forensic recovery of Seongnam official notice search/detail contract.

This stage is discovery-only. It recovers exact GET form controls/options and
resolved detail-link patterns from /pm010301. It may issue bounded search
requests using the official form contract, but it does not download
attachments, mutate cumulative state, or create legal negative evidence.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_notice_search_contract_forensic.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "NOTICE_NUMBER_REVERSE_LOOKUP"

LIST_URL = "https://www.seongnam.go.kr/pm010301/list"
SEARCH_URL = "https://www.seongnam.go.kr/pm010301"
OFFICIAL_HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_TOTAL_REQUESTS = 12
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

FORM_PATTERN = re.compile(r"<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>", re.I | re.S)
SELECT_PATTERN = re.compile(r"<select\b(?P<attrs>[^>]*)>(?P<body>.*?)</select>", re.I | re.S)
OPTION_PATTERN = re.compile(r"<option\b(?P<attrs>[^>]*)>(?P<body>.*?)</option>", re.I | re.S)
INPUT_PATTERN = re.compile(r"<input\b(?P<attrs>[^>]*)>", re.I | re.S)
ANCHOR_PATTERN = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>", re.I | re.S)
ATTR_PATTERN = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
NOTICE_NUMBER_PATTERN = re.compile(r"성남시\s*(?:[가-힣]+구\s*)?(?:고시|공고)\s*제?\s*\d{4}\s*[-－]\s*\d+\s*호")
RESOLVED_DETAIL_PATH = re.compile(r"^/pm010301/(\d+)$")
JS_DETAIL_HINT = re.compile(r"(?:pm010301|fn[A-Za-z_]*view|go[A-Za-z_]*view|detail)[^\n]{0,160}", re.I)

SEARCH_TERMS = [
    "개발밀도관리구역",
    "개발밀도",
    "도시관리계획",
]


def attrs(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in ATTR_PATTERN.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def clean_text(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_PATTERN.sub(" ", raw or ""))).strip()


def fetch(session: requests.Session, url: str, counter: list[int], params: dict | None = None) -> dict:
    if counter[0] >= MAX_TOTAL_REQUESTS:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    r = session.get(url, params=params, timeout=TIMEOUT, allow_redirects=True)
    body = r.content[:MAX_RESPONSE_BYTES]
    text = body.decode(r.encoding or "utf-8", errors="replace")
    return {
        "request_url": str(r.request.url),
        "http_status": r.status_code,
        "final_url": str(r.url),
        "final_host": (urlparse(str(r.url)).hostname or "").lower(),
        "content_type": r.headers.get("Content-Type", ""),
        "body_bytes_read": len(body),
        "text": text,
    }


def parse_get_search_form(text: str, base_url: str) -> dict:
    candidates = []
    for fm in FORM_PATTERN.finditer(text or ""):
        fa = attrs(fm.group("attrs"))
        method = (fa.get("method") or "get").upper()
        action = urljoin(base_url, fa.get("action") or base_url)
        body = fm.group("body")
        inputs = []
        for im in INPUT_PATTERN.finditer(body):
            ia = attrs(im.group("attrs"))
            if ia.get("name"):
                inputs.append({
                    "name": ia.get("name", ""),
                    "type": ia.get("type", ""),
                    "value": ia.get("value", ""),
                })
        selects = []
        for sm in SELECT_PATTERN.finditer(body):
            sa = attrs(sm.group("attrs"))
            name = sa.get("name", "")
            options = []
            for om in OPTION_PATTERN.finditer(sm.group("body")):
                oa = attrs(om.group("attrs"))
                options.append({
                    "value": oa.get("value", ""),
                    "label": clean_text(om.group("body")),
                    "selected": "selected" in oa,
                })
            selects.append({"name": name, "options": options})
        names = {i["name"] for i in inputs} | {s["name"] for s in selects if s["name"]}
        rec = {"method": method, "action_url": action, "inputs": inputs, "selects": selects, "control_names": sorted(names)}
        if method == "GET" and "srchText" in names:
            candidates.append(rec)
    if not candidates:
        raise AssertionError("GET search form with srchText not found")
    return candidates[0]


def resolve_detail_links(text: str, base_url: str) -> list[dict]:
    result = []
    seen = set()
    for am in ANCHOR_PATTERN.finditer(text or ""):
        aa = attrs(am.group("attrs"))
        href = (aa.get("href") or "").strip()
        if not href or href.lower().startswith(("javascript:", "#")):
            continue
        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if parsed.hostname != OFFICIAL_HOST:
            continue
        m = RESOLVED_DETAIL_PATH.match(parsed.path)
        if not m:
            continue
        if url in seen:
            continue
        seen.add(url)
        result.append({
            "document_id": m.group(1),
            "url": url,
            "href_raw": href,
            "anchor_text": clean_text(am.group("body")),
        })
    return result[:50]


def search_key_options(form: dict) -> list[dict]:
    for sel in form.get("selects", []):
        if sel.get("name") == "srchKey":
            return sel.get("options", [])
    return []


def default_params(form: dict) -> dict:
    params = {}
    for item in form.get("inputs", []):
        name = item.get("name")
        if name:
            params[name] = item.get("value", "")
    for sel in form.get("selects", []):
        name = sel.get("name")
        if not name:
            continue
        opts = sel.get("options", [])
        chosen = next((o for o in opts if o.get("selected")), None) or (opts[0] if opts else None)
        if chosen:
            params[name] = chosen.get("value", "")
    return params


def main() -> None:
    print("=" * 60)
    print("SEONGNAM NOTICE SEARCH CONTRACT FORENSIC - S74")
    print("=" * 60)
    print("Attachment download: DISABLED")
    print("State mutation: DISABLED")
    print("Negative evidence: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    counter = [0]

    base = fetch(session, LIST_URL, counter)
    if base["http_status"] != 200 or base["final_host"] != OFFICIAL_HOST:
        raise AssertionError("official list endpoint unavailable")

    form = parse_get_search_form(base["text"], base["final_url"])
    keys = search_key_options(form)
    resolved_links = resolve_detail_links(base["text"], base["final_url"])
    js_hints = sorted(set(clean_text(x) for x in JS_DETAIL_HINT.findall(base["text"])))[:50]

    defaults = default_params(form)
    key_values = [o.get("value", "") for o in keys]
    # Use discovered values only; never guess undocumented srchKey values.
    probe_keys = key_values[:3] if key_values else [defaults.get("srchKey", "")]
    probe_keys = list(dict.fromkeys(probe_keys))

    probes = []
    for term in SEARCH_TERMS:
        for key in probe_keys:
            if counter[0] >= MAX_TOTAL_REQUESTS:
                break
            params = dict(defaults)
            params.update({"curPage": "1", "srchKey": key, "srchText": term})
            rec = fetch(session, form["action_url"], counter, params=params)
            page_text = clean_text(rec["text"])
            links = resolve_detail_links(rec["text"], rec["final_url"])
            notice_numbers = sorted(set(NOTICE_NUMBER_PATTERN.findall(page_text)))
            probes.append({
                "term": term,
                "srchKey": key,
                "request_url": rec["request_url"],
                "http_status": rec["http_status"],
                "final_url": rec["final_url"],
                "official_host": rec["final_host"] == OFFICIAL_HOST,
                "term_visible_in_response_text": term in page_text,
                "notice_number_count": len(notice_numbers),
                "notice_numbers_sample": notice_numbers[:20],
                "resolved_detail_link_count": len(links),
                "resolved_detail_links_sample": links[:10],
            })

    any_probe_ok = any(p["http_status"] == 200 and p["official_host"] for p in probes)
    any_detail_contract = bool(resolved_links) or any(p["resolved_detail_link_count"] > 0 for p in probes)
    summary = {
        "search_form_action": form["action_url"],
        "search_form_method": form["method"],
        "search_control_names": form["control_names"],
        "srchKey_option_count": len(keys),
        "srchKey_options": keys,
        "base_resolved_detail_link_count": len(resolved_links),
        "js_detail_hint_count": len(js_hints),
        "probe_count": len(probes),
        "any_search_probe_http_200": any_probe_ok,
        "detail_contract_discovered": any_detail_contract,
        "request_count": counter[0],
    }

    payload = {
        "step": "STEP 17-21-C-16-8-T-35-S74",
        "target_name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "search_form": form,
        "default_params": defaults,
        "base_resolved_detail_links": resolved_links,
        "js_detail_hints": js_hints,
        "search_probes": probes,
        "summary": summary,
        "attachment_body_download_executed": False,
        "state_mutation_executed": False,
        "negative_evidence_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    validations = {
        "official search form recovered": form["method"] == "GET" and "srchText" in form["control_names"],
        "search probes transport ok": any_probe_ok,
        "request budget respected": counter[0] <= MAX_TOTAL_REQUESTS,
        "attachment download disabled": not payload["attachment_body_download_executed"],
        "state mutation disabled": not payload["state_mutation_executed"],
        "negative evidence disabled": not payload["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not any(payload[k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed", "final_positive_promotion_allowed"]),
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print("\nSEARCH FORM")
    print("method:", form["method"])
    print("action_url:", form["action_url"])
    print("control_names:", form["control_names"])
    print("srchKey options:", keys)
    print("default params:", defaults)

    print("\nDETAIL CONTRACT")
    print("base resolved detail links:", resolved_links[:10])
    print("js detail hints:", js_hints[:10])

    print("\nPROBES")
    for p in probes:
        print({
            "term": p["term"],
            "srchKey": p["srchKey"],
            "http": p["http_status"],
            "term_visible": p["term_visible_in_response_text"],
            "notice_count": p["notice_number_count"],
            "detail_links": p["resolved_detail_link_count"],
        })

    print("\nSUMMARY")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print("Output:", OUTPUT_PATH)

    print("\nVALIDATION")
    for k, v in validations.items():
        print(f"{k}: {v}")
    print("all_pass:", all(validations.values()))
    if not all(validations.values()):
        raise AssertionError("S74 search contract forensic validation failed")


if __name__ == "__main__":
    main()
