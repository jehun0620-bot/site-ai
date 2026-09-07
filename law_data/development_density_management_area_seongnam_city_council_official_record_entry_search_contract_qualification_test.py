# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_council_official_record_entry_search_contract_qualification.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD"

OFFICIAL_ENTRY_CANDIDATES = [
    "https://www.sncouncil.go.kr/",
    "https://sncouncil.go.kr/",
]

POSITIVE_CONTROL_QUERY = "도시계획"
FAMILY_KEYWORDS = {
    "MINUTES": ["회의록", "회의", "본회의", "상임위원회"],
    "AGENDA": ["의안", "안건", "의안정보", "의안검색"],
    "ORDINANCE": ["조례", "규칙", "자치법규"],
    "RECORD_SEARCH": ["통합검색", "자료검색", "검색"],
}
SEARCH_FIELD_HINTS = [
    "search", "srch", "query", "keyword", "keyWord", "searchWord", "searchText",
    "sch", "sword", "word", "kwd", "q", "text", "title", "content", "subject",
]


def curl(url: str, method: str = "GET", data: dict | None = None, referer: str | None = None) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "redirects": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "120",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    ]
    if referer:
        cmd += ["-e", referer]
    if method.upper() == "POST":
        cmd += ["-X", "POST"]
        if data:
            for k, v in data.items():
                cmd += ["--data-urlencode", f"{k}={v}"]
    elif data:
        sep = "&" if "?" in url else "?"
        url = url + sep + urlencode(data, doseq=True)
    cmd += ["-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}|%{num_redirects}", url]
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 3)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
        content_type = parts[2] if len(parts) > 2 else None
        redirects = parts[3] if len(parts) > 3 else None
    else:
        body, http, final_url, content_type, redirects = raw, None, None, None, None
    return {
        "http": http,
        "final_url": final_url,
        "content_type": content_type,
        "redirects": redirects,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def decode(body: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            pass
    return body.decode("utf-8", errors="replace")


def strip_tags(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s)
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def extract_links(base_url: str, text: str) -> list[dict]:
    rows = []
    seen = set()
    pat = re.compile(r'(?is)<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>')
    for href, label_html in pat.findall(text):
        href = html.unescape(href.strip())
        if not href or href.startswith(("javascript:", "#", "mailto:", "tel:")):
            continue
        url = urljoin(base_url, href)
        if url in seen:
            continue
        seen.add(url)
        label = strip_tags(label_html)
        context = f"{label} {url}".lower()
        fam = []
        for name, kws in FAMILY_KEYWORDS.items():
            if any(k.lower() in context for k in kws):
                fam.append(name)
        if fam:
            rows.append({"url": url, "label": label, "families": fam})
    return rows


def attr(tag: str, name: str) -> str | None:
    m = re.search(rf'(?is)\b{name}\s*=\s*["\']([^"\']*)["\']', tag)
    if m:
        return html.unescape(m.group(1))
    m = re.search(rf'(?is)\b{name}\s*=\s*([^\s>]+)', tag)
    return html.unescape(m.group(1)) if m else None


def parse_forms(base_url: str, text: str) -> list[dict]:
    forms = []
    for m in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", text):
        open_attrs, body = m.group(1), m.group(2)
        method = (attr(open_attrs, "method") or "GET").upper()
        action = attr(open_attrs, "action") or base_url
        action_url = urljoin(base_url, action)
        inputs = []
        for im in re.finditer(r"(?is)<input\b([^>]*)>", body):
            a = im.group(1)
            name = attr(a, "name")
            if not name:
                continue
            inputs.append({
                "name": name,
                "type": (attr(a, "type") or "text").lower(),
                "value": attr(a, "value") or "",
            })
        for sm in re.finditer(r"(?is)<select\b([^>]*)>(.*?)</select>", body):
            a, sb = sm.group(1), sm.group(2)
            name = attr(a, "name")
            if not name:
                continue
            opt = re.search(r'(?is)<option\b([^>]*)selected[^>]*>', sb) or re.search(r'(?is)<option\b([^>]*)>', sb)
            value = attr(opt.group(1), "value") if opt else ""
            inputs.append({"name": name, "type": "select", "value": value or ""})
        text_inputs = [i for i in inputs if i["type"] in {"text", "search", ""}]
        hinted = [i for i in inputs if any(h.lower() in i["name"].lower() for h in SEARCH_FIELD_HINTS)]
        search_fields = []
        for i in hinted + text_inputs:
            if i["name"] not in search_fields:
                search_fields.append(i["name"])
        body_text = strip_tags(body)
        likely_search = bool(search_fields) and any(k in body_text.lower() for k in ["검색", "search", "조회"])
        forms.append({
            "method": method,
            "action_url": action_url,
            "inputs": inputs,
            "search_fields": search_fields,
            "likely_search": likely_search,
        })
    return forms


def same_official_host(url: str, official_host: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
        return host == official_host or host.endswith("." + official_host)
    except Exception:
        return False


def qualify_search_form(page_url: str, form: dict, official_host: str) -> dict:
    action_url = form["action_url"]
    if not same_official_host(action_url, official_host):
        return {"qualified": False, "reason": "NON_OFFICIAL_HOST_ACTION"}
    if not form.get("search_fields"):
        return {"qualified": False, "reason": "NO_SEARCH_FIELD"}

    payload = {}
    for i in form.get("inputs", []):
        typ = i.get("type")
        name = i.get("name")
        if typ in {"submit", "button", "image", "file"}:
            continue
        payload[name] = i.get("value") or ""
    query_field = form["search_fields"][0]
    payload[query_field] = POSITIVE_CONTROL_QUERY

    rr = curl(action_url, method=form["method"], data=payload, referer=page_url)
    text = decode(rr.get("body") or b"") if rr.get("body") else ""
    plain = strip_tags(text)
    query_echo = POSITIVE_CONTROL_QUERY in plain or POSITIVE_CONTROL_QUERY in text
    result_signal = any(x in plain for x in ["검색결과", "검색 결과", "총 ", "건", "의안", "회의록", "조례", "도시계획"])
    error_signal = any(x in plain.lower() for x in ["error", "오류", "잘못된 접근", "페이지를 찾을 수 없습니다"])
    http_ok = rr.get("http") == "200"
    qualified = http_ok and not error_signal and (query_echo or result_signal)
    return {
        "qualified": qualified,
        "method": form["method"],
        "action_url": action_url,
        "query_field": query_field,
        "payload_keys": sorted(payload.keys()),
        "http": rr.get("http"),
        "final_url": rr.get("final_url"),
        "content_type": rr.get("content_type"),
        "redirects": rr.get("redirects"),
        "body_size": len(rr.get("body") or b""),
        "query_echo": query_echo,
        "result_signal": result_signal,
        "error_signal": error_signal,
        "title_sample": (re.search(r"(?is)<title[^>]*>(.*?)</title>", text).group(1).strip() if re.search(r"(?is)<title[^>]*>(.*?)</title>", text) else None),
        "text_sample": plain[:1000],
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY COUNCIL OFFICIAL RECORD ENTRY / SEARCH CONTRACT QUALIFICATION - S228A")
    print("=" * 78)
    print("Purpose: qualify official council record entry points and search contracts before UQQ700 target search")
    print("Positive control query:", POSITIVE_CONTROL_QUERY)
    print("Council record hit != designation notice/current validity/site inclusion")
    print("Council record no-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    entry_attempts = []
    selected = None
    for url in OFFICIAL_ENTRY_CANDIDATES:
        rr = curl(url)
        text = decode(rr.get("body") or b"") if rr.get("body") else ""
        plain = strip_tags(text)
        official_signal = any(k in plain for k in ["성남시의회", "성남시 의회", "의회"])
        row = {
            "input_url": url,
            "http": rr.get("http"),
            "final_url": rr.get("final_url"),
            "content_type": rr.get("content_type"),
            "redirects": rr.get("redirects"),
            "body_size": len(rr.get("body") or b""),
            "official_signal": official_signal,
        }
        entry_attempts.append(row)
        if rr.get("http") == "200" and official_signal and selected is None:
            selected = {"url": rr.get("final_url") or url, "html": text}

    result = {
        "step": "STEP 17-21-C-16-8-T-157-S228A",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "entry_attempts": entry_attempts,
        "selected_official_entry": selected["url"] if selected else None,
        "family_entry_candidates": [],
        "page_contracts": [],
        "qualified_search_contracts": [],
    }

    if selected:
        official_host = urlparse(selected["url"]).hostname or ""
        links = extract_links(selected["url"], selected["html"])
        official_links = [x for x in links if same_official_host(x["url"], official_host)]
        # Keep bounded, unique, family-relevant entry pages.
        result["family_entry_candidates"] = official_links[:40]

        pages = [{"url": selected["url"], "families": ["ROOT"]}] + official_links[:24]
        seen_pages = set()
        for p in pages:
            url = p["url"]
            if url in seen_pages:
                continue
            seen_pages.add(url)
            rr = curl(url, referer=selected["url"])
            text = decode(rr.get("body") or b"") if rr.get("body") else ""
            forms = parse_forms(rr.get("final_url") or url, text) if rr.get("http") == "200" else []
            likely_forms = [f for f in forms if f.get("likely_search") or f.get("search_fields")]
            page_rec = {
                "url": url,
                "families": p.get("families", []),
                "http": rr.get("http"),
                "final_url": rr.get("final_url"),
                "body_size": len(rr.get("body") or b""),
                "form_count": len(forms),
                "search_form_candidate_count": len(likely_forms),
                "search_forms": [],
            }
            for f in likely_forms[:8]:
                q = qualify_search_form(rr.get("final_url") or url, f, official_host)
                page_rec["search_forms"].append({"form": f, "qualification": q})
                if q.get("qualified"):
                    result["qualified_search_contracts"].append({
                        "page_url": rr.get("final_url") or url,
                        "families": p.get("families", []),
                        **q,
                    })
            result["page_contracts"].append(page_rec)

    qualified_count = len(result["qualified_search_contracts"])
    family_names = sorted({f for x in result["family_entry_candidates"] for f in x.get("families", [])})

    if qualified_count > 0:
        classification = "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD_SEARCH_CONTRACT_QUALIFIED"
        semantic = "OFFICIAL_COUNCIL_RECORD_ENTRY_AND_AT_LEAST_ONE_POSITIVE_CONTROL_SEARCH_CONTRACT_VERIFIED"
        next_action = "RUN_BOUNDED_UQQ700_COUNCIL_RECORD_TARGET_SEARCH_USING_ONLY_QUALIFIED_CONTRACTS_AS_HISTORICAL_REVERSE_LOOKUP_ANCHORS"
    elif selected:
        classification = "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD_ENTRY_QUALIFIED_SEARCH_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "OFFICIAL_COUNCIL_ENTRY_VERIFIED_BUT_NO_SEARCH_FORM_WAS_POSITIVE_CONTROL_QUALIFIED"
        next_action = "HARDEN_COUNCIL_SEARCH_SUBMIT_CONTRACT_FROM_VERIFIED_OFFICIAL_ENTRY_WITHOUT_UQQ700_NEGATIVE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD_ENTRY_TECHNICAL_UNKNOWN"
        semantic = "OFFICIAL_COUNCIL_ENTRY_WAS_NOT_QUALIFIED_FROM_BOUNDED_ENTRY_CANDIDATES"
        next_action = "RECOVER_OFFICIAL_COUNCIL_ENTRY_ROUTE_WITHOUT_LEGAL_ABSENCE_INFERENCE"

    result.update({
        "record_family_types_observed": family_names,
        "qualified_search_contract_count": qualified_count,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "target_search_executed": False,
            "positive_control_only": True,
            "council_record_hit_equals_designation_notice": False,
            "council_record_hit_equals_current_validity": False,
            "council_record_hit_equals_site_inclusion": False,
            "council_record_no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nENTRY QUALIFICATION")
    print("-" * 78)
    for r in entry_attempts:
        print(json.dumps(r, ensure_ascii=False))
    print(f"SELECTED OFFICIAL ENTRY: {result['selected_official_entry']}")
    print(f"RECORD FAMILY TYPES OBSERVED: {family_names}")
    print(f"FAMILY ENTRY CANDIDATE COUNT: {len(result['family_entry_candidates'])}")
    print(f"PAGE CONTRACT COUNT: {len(result['page_contracts'])}")
    print(f"QUALIFIED SEARCH CONTRACT COUNT: {qualified_count}")

    print("\nQUALIFIED SEARCH CONTRACTS")
    print("-" * 78)
    for q in result["qualified_search_contracts"]:
        print(json.dumps(q, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Target UQQ700 search executed: False")
    print("Council record hit == designation/current validity/site inclusion: False")
    print("Council record no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": result["target_name"] == TARGET,
        "standard code": result["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": result["resolution_type"] == RESOLUTION_TYPE,
        "entry candidates bounded": len(entry_attempts) == len(OFFICIAL_ENTRY_CANDIDATES),
        "target search not executed": result["summary"]["target_search_executed"] is False,
        "positive control only": result["summary"]["positive_control_only"] is True,
        "council hit not designation": result["summary"]["council_record_hit_equals_designation_notice"] is False,
        "council hit not validity": result["summary"]["council_record_hit_equals_current_validity"] is False,
        "council hit not site inclusion": result["summary"]["council_record_hit_equals_site_inclusion"] is False,
        "council no-hit not legal absence": result["summary"]["council_record_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": result["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": result["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": result["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": result["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": result["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": result["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": result["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": result["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD_SEARCH_CONTRACT_QUALIFIED",
            "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD_ENTRY_QUALIFIED_SEARCH_CONTRACT_TECHNICAL_UNKNOWN",
            "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD_ENTRY_TECHNICAL_UNKNOWN",
        },
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for k, v in validation.items():
        print(f"{k}: {v}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")
    if not all(validation.values()):
        raise AssertionError("S228A validation failed")


if __name__ == "__main__":
    main()
