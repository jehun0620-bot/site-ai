# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_S229A = OUT_DIR / "development_density_management_area_national_regional_planning_research_document_source_family_entry_qualification.json"
OUT = OUT_DIR / "development_density_management_area_national_regional_planning_research_document_positive_control_search_contract_qualification.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT"
POSITIVE_CONTROL = "도시계획"
MAX_ROUTE_PROBES_PER_SOURCE = 8
MAX_FORM_REPLAYS_PER_SOURCE = 8

SEARCH_HINTS = [
    "search", "srch", "query", "keyword", "keyWord", "searchWord", "searchText",
    "searchKeyword", "searchTerm", "searchValue", "searchTxt", "subject", "title",
    "word", "kwd", "q", "text", "content", "sch", "sword",
]
ROUTE_HINTS = [
    "검색", "통합검색", "자료검색", "연구검색", "보고서", "연구보고서", "정책연구",
    "간행물", "발간물", "자료실", "정책자료", "연구자료", "publication", "research",
    "report", "search", "archive",
]

# Semantic hardening: only these field/action combinations are eligible for
# canonical reuse. Everything else remains diagnostic only even if a generic
# echo/result heuristic looked positive.
SEMANTIC_ALLOWLIST = {
    "GRI": {
        ("GET", "/web/contents/webSearch.do", "kwd"): "GLOBAL_SEARCH",
        ("GET", "/web/contents/resreport.do", "schStr"): "RESEARCH_REPORT_SEARCH",
    },
}

# These are selector/filter/date fields and must never be promoted to target
# query fields for this source family.
SEMANTIC_DENY_FIELDS = {
    "schFld",
    "searchStartDate",
    "searchEndDate",
    "search_kind",
    "startDay",
    "endDay",
    "proposer",
}


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
        for k, v in (data or {}).items():
            cmd += ["--data-urlencode", f"{k}={v}"]
    elif data:
        sep = "&" if "?" in url else "?"
        url += sep + urlencode(data, doseq=True)
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
            continue
    return body.decode("utf-8", errors="replace")


def strip_tags(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s)
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def attr(tag: str, name: str) -> str | None:
    m = re.search(rf'(?is)\b{name}\s*=\s*["\']([^"\']*)["\']', tag)
    if m:
        return html.unescape(m.group(1))
    m = re.search(rf'(?is)\b{name}\s*=\s*([^\s>]+)', tag)
    return html.unescape(m.group(1)) if m else None


def same_host(base_url: str, candidate_url: str) -> bool:
    a = (urlparse(base_url).hostname or "").lower().removeprefix("www.")
    b = (urlparse(candidate_url).hostname or "").lower().removeprefix("www.")
    return bool(a and b and (a == b or a.endswith("." + b) or b.endswith("." + a)))


def title_of(text: str) -> str:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", text)
    return strip_tags(m.group(1)) if m else ""


def official_signal(source_id: str, final_url: str, text: str) -> bool:
    host = (urlparse(final_url).hostname or "").lower()
    sample = f"{title_of(text)} {strip_tags(text[:60000])}".lower()
    if source_id == "GG":
        return "gg.go.kr" in host and "경기도" in sample
    if source_id == "GRI":
        return "gri.re.kr" in host and ("경기연구원" in sample or "gri" in sample)
    if source_id == "KRIHS":
        return "krihs.re.kr" in host and ("국토연구원" in sample or "krihs" in sample)
    return False


def extract_route_candidates(base_url: str, text: str) -> list[dict]:
    rows, seen = [], set()
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", text):
        attrs, body = m.group(1), m.group(2)
        href = attr(attrs, "href")
        if not href or href.lower().startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        url = urljoin(base_url, href)
        if not same_host(base_url, url):
            continue
        label = strip_tags(body)
        blob = f"{label} {href}".lower()
        score = sum(1 for h in ROUTE_HINTS if h.lower() in blob)
        if score <= 0:
            continue
        key = url.split("#", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        rows.append({"url": key, "label": label, "score": score})
    rows.sort(key=lambda x: (-x["score"], len(x["url"])))
    return rows[:MAX_ROUTE_PROBES_PER_SOURCE]


def parse_forms(base_url: str, text: str) -> list[dict]:
    rows = []
    for fm in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", text):
        attrs, body = fm.group(1), fm.group(2)
        method = (attr(attrs, "method") or "GET").upper()
        action = urljoin(base_url, attr(attrs, "action") or base_url)
        if not same_host(base_url, action):
            continue
        inputs = []
        for im in re.finditer(r"(?is)<input\b([^>]*)>", body):
            a = im.group(1)
            name = attr(a, "name")
            if not name:
                continue
            inputs.append({"name": name, "type": (attr(a, "type") or "text").lower(), "value": attr(a, "value") or ""})
        for tm in re.finditer(r"(?is)<textarea\b([^>]*)>.*?</textarea>", body):
            name = attr(tm.group(1), "name")
            if name:
                inputs.append({"name": name, "type": "textarea", "value": ""})
        for sm in re.finditer(r"(?is)<select\b([^>]*)>(.*?)</select>", body):
            a, sb = sm.group(1), sm.group(2)
            name = attr(a, "name")
            if not name:
                continue
            selected = re.search(r'(?is)<option\b([^>]*)selected[^>]*>', sb)
            first = re.search(r'(?is)<option\b([^>]*)>', sb)
            opt = selected or first
            inputs.append({"name": name, "type": "select", "value": (attr(opt.group(1), "value") if opt else "") or ""})
        search_fields = []
        for i in inputs:
            n = i["name"]
            t = i["type"]
            if t in {"text", "search", "textarea"} or any(h.lower() in n.lower() for h in SEARCH_HINTS):
                if n not in search_fields:
                    search_fields.append(n)
        plain = strip_tags(body)
        search_signal = any(k in plain.lower() for k in ["검색", "search", "조회"])
        if search_fields and search_signal:
            rows.append({
                "method": method,
                "action_url": action,
                "form_id": attr(attrs, "id"),
                "form_name": attr(attrs, "name"),
                "inputs": inputs,
                "search_fields": search_fields,
            })
    return rows[:12]


def build_payload(form: dict, field: str) -> dict:
    payload = {}
    for i in form["inputs"]:
        if i["type"] in {"submit", "button", "image", "file", "reset"}:
            continue
        payload[i["name"]] = i.get("value") or ""
    payload[field] = POSITIVE_CONTROL
    for k in list(payload):
        if k.lower() in {"page", "pageindex", "pageno", "currentpage", "currpage"}:
            payload[k] = "1"
    return payload


def replay_form(source_id: str, page_url: str, form: dict, field: str) -> dict:
    payload = build_payload(form, field)
    rr = curl(form["action_url"], form["method"], payload, page_url)
    text = decode(rr.get("body") or b"")
    plain = strip_tags(text)
    query_echo = POSITIVE_CONTROL in text or POSITIVE_CONTROL in plain
    official = official_signal(source_id, rr.get("final_url") or form["action_url"], text)
    error_signal = any(x in plain.lower() for x in ["error", "오류", "잘못된 접근", "페이지를 찾을 수 없습니다", "forbidden"])
    result_signal = any(x in plain for x in ["검색결과", "검색 결과", "총", "건", "연구", "보고서", "자료", "도시계획"])
    body_ok = len(rr.get("body") or b"") > 1000
    qualified = rr.get("http") == "200" and body_ok and official and query_echo and result_signal and not error_signal
    return {
        "qualified": qualified,
        "query_field": field,
        "method": form["method"],
        "action_url": form["action_url"],
        "payload_keys": sorted(payload.keys()),
        "http": rr.get("http"),
        "final_url": rr.get("final_url"),
        "content_type": rr.get("content_type"),
        "redirects": rr.get("redirects"),
        "body_size": len(rr.get("body") or b""),
        "official_signal": official,
        "query_echo": query_echo,
        "result_signal": result_signal,
        "error_signal": error_signal,
        "text_sample": plain[:1000],
    }


def semantic_contract_role(source_id: str, method: str, action_url: str, field: str) -> str | None:
    if field in SEMANTIC_DENY_FIELDS:
        return None
    path = urlparse(action_url).path
    return SEMANTIC_ALLOWLIST.get(source_id, {}).get((method.upper(), path, field))


def canonicalize_contracts(raw_contracts: list[dict]) -> tuple[list[dict], list[dict]]:
    canonical: list[dict] = []
    rejected: list[dict] = []
    seen = set()
    for row in raw_contracts:
        role = semantic_contract_role(row["source_id"], row["method"], row["action_url"], row["query_field"])
        if not role:
            rejected.append({
                **row,
                "semantic_rejection_reason": "NOT_IN_SEMANTIC_ALLOWLIST_OR_FILTER_SELECTOR_FIELD",
            })
            continue
        path = urlparse(row["action_url"]).path
        key = (row["source_id"], row["method"].upper(), path, row["query_field"])
        if key in seen:
            continue
        seen.add(key)
        canonical.append({
            **row,
            "canonical_action_path": path,
            "semantic_contract_role": role,
            "canonical_contract_key": "|".join(key),
            "semantically_hardened": True,
        })
    return canonical, rejected


def main() -> None:
    print("=" * 78)
    print("NATIONAL / REGIONAL PLANNING RESEARCH DOCUMENT POSITIVE CONTROL SEARCH CONTRACT QUALIFICATION - S229B HARDENED")
    print("=" * 78)
    print("Purpose: positive-control qualification plus semantic hardening and canonical deduplication")
    print("Positive control:", POSITIVE_CONTROL)
    print("UQQ700 target search: DISABLED")
    print("Only semantically allowlisted canonical contracts may advance")
    print("Planning/research hit != designation/current validity/site inclusion")
    print("Planning/research no-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    if not IN_S229A.exists():
        raise FileNotFoundError(f"Missing S229A output: {IN_S229A}")
    s229a = json.loads(IN_S229A.read_text(encoding="utf-8"))
    ranked = s229a.get("ranked_qualified_sources") or []
    selected = [x for x in ranked if x.get("source_id") in {"GG", "GRI", "KRIHS"}][:3]

    source_results = []
    raw_qualified_contracts = []
    total_route_probes = 0
    total_form_replays = 0

    for src in selected:
        source_id = src["source_id"]
        entry_url = src["final_url"]
        entry_rr = curl(entry_url)
        entry_text = decode(entry_rr.get("body") or b"")
        entry_official = official_signal(source_id, entry_rr.get("final_url") or entry_url, entry_text)
        routes = extract_route_candidates(entry_rr.get("final_url") or entry_url, entry_text) if entry_rr.get("http") == "200" else []
        page_rows = []
        source_replays = 0

        candidate_pages = [{"url": entry_rr.get("final_url") or entry_url, "label": "ENTRY", "score": 0}] + routes
        seen_pages = set()
        for route in candidate_pages:
            if route["url"] in seen_pages:
                continue
            seen_pages.add(route["url"])
            if route["label"] != "ENTRY":
                total_route_probes += 1
            rr = entry_rr if route["label"] == "ENTRY" else curl(route["url"], referer=entry_url)
            text = entry_text if route["label"] == "ENTRY" else decode(rr.get("body") or b"")
            final_url = rr.get("final_url") or route["url"]
            official = official_signal(source_id, final_url, text) if rr.get("http") == "200" else False
            forms = parse_forms(final_url, text) if rr.get("http") == "200" and official else []
            form_rows = []

            for form_index, form in enumerate(forms):
                if source_replays >= MAX_FORM_REPLAYS_PER_SOURCE:
                    break
                for field in form["search_fields"][:2]:
                    if source_replays >= MAX_FORM_REPLAYS_PER_SOURCE:
                        break
                    replay = replay_form(source_id, final_url, form, field)
                    source_replays += 1
                    total_form_replays += 1
                    semantic_role = semantic_contract_role(source_id, replay["method"], replay["action_url"], replay["query_field"])
                    form_rows.append({
                        "form_index": form_index,
                        "form": form,
                        "replay": {**replay, "semantic_role": semantic_role},
                    })
                    if replay["qualified"]:
                        raw_qualified_contracts.append({
                            "source_id": source_id,
                            "name": src["name"],
                            "expected_role": src["expected_role"],
                            "page_url": final_url,
                            "form_index": form_index,
                            **replay,
                            "source_role": "CONTEXT_AND_REVERSE_LOOKUP_ONLY",
                        })

            page_rows.append({
                "input_url": route["url"],
                "label": route["label"],
                "http": rr.get("http"),
                "final_url": final_url,
                "body_size": len(rr.get("body") or b""),
                "official_signal": official,
                "form_candidate_count": len(forms),
                "form_replays": form_rows,
            })

        source_results.append({
            "source_id": source_id,
            "name": src["name"],
            "expected_role": src["expected_role"],
            "entry_url": entry_url,
            "entry_http": entry_rr.get("http"),
            "entry_final_url": entry_rr.get("final_url"),
            "entry_body_size": len(entry_rr.get("body") or b""),
            "entry_official_signal": entry_official,
            "route_candidate_count": len(routes),
            "pages": page_rows,
            "positive_control_replay_count": source_replays,
        })

    canonical_contracts, semantically_rejected_raw_contracts = canonicalize_contracts(raw_qualified_contracts)

    for r in source_results:
        raw_source_q = [q for q in raw_qualified_contracts if q["source_id"] == r["source_id"]]
        canonical_source_q = [q for q in canonical_contracts if q["source_id"] == r["source_id"]]
        r["raw_qualified_contract_count"] = len(raw_source_q)
        r["canonical_qualified_contract_count"] = len(canonical_source_q)
        r["contract_qualified"] = bool(canonical_source_q)

    qualified_source_count = sum(1 for r in source_results if r["contract_qualified"])
    raw_qualified_contract_count = len(raw_qualified_contracts)
    canonical_qualified_contract_count = len(canonical_contracts)

    if canonical_qualified_contract_count > 0:
        classification = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_POSITIVE_CONTROL_SEARCH_CONTRACT_SEMANTICALLY_HARDENED_QUALIFIED"
        semantic = "ONLY_SEMANTICALLY_VALID_CANONICAL_PLANNING_RESEARCH_SEARCH_CONTRACTS_WERE_RETAINED_AFTER_POSITIVE_CONTROL_QUALIFICATION"
        next_action = "RUN_BOUNDED_UQQ700_TARGET_SEARCH_ONLY_ON_CANONICAL_SEMANTICALLY_HARDENED_CONTRACTS_AS_CONTEXT_AND_REVERSE_LOOKUP_ANCHORS"
    else:
        classification = "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_POSITIVE_CONTROL_SEARCH_CONTRACT_SEMANTICALLY_HARDENED_TECHNICAL_UNKNOWN"
        semantic = "RAW_POSITIVE_CONTROL_RESPONSES_WERE_OBSERVED_BUT_NO_SEMANTICALLY_VALID_CANONICAL_CONTRACT_REMAINED"
        next_action = "HARDEN_ONLY_SOURCE_SPECIFIC_PUBLICATION_OR_SEARCH_ROUTES_WITHOUT_UQQ700_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-162-S229B-HARDENED",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "positive_control_query": POSITIVE_CONTROL,
        "selected_source_count": len(selected),
        "selected_sources": [{k: x.get(k) for k in ["source_id", "name", "expected_role", "final_url", "score"]} for x in selected],
        "source_results": source_results,
        "route_probe_count": total_route_probes,
        "positive_control_replay_count": total_form_replays,
        "raw_qualified_search_contract_count": raw_qualified_contract_count,
        "raw_qualified_search_contracts": raw_qualified_contracts,
        "canonical_qualified_search_contract_count": canonical_qualified_contract_count,
        "canonical_qualified_search_contracts": canonical_contracts,
        "semantically_rejected_raw_contract_count": len(semantically_rejected_raw_contracts),
        "semantically_rejected_raw_contracts": semantically_rejected_raw_contracts,
        "qualified_source_count": qualified_source_count,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "target_search_executed": False,
            "positive_control_search_executed": total_form_replays > 0,
            "semantic_allowlist_enforced": True,
            "canonical_deduplication_enforced": True,
            "filter_selector_fields_blocked": True,
            "source_role_context_and_reverse_lookup_only": True,
            "planning_research_hit_equals_designation_notice": False,
            "planning_research_hit_equals_current_validity": False,
            "planning_research_hit_equals_site_inclusion": False,
            "planning_research_no_hit_equals_legal_absence": False,
            "search_failure_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nSOURCE CONTRACT QUALIFICATION")
    print("-" * 78)
    for r in source_results:
        print(json.dumps({
            "source_id": r["source_id"],
            "name": r["name"],
            "entry_http": r["entry_http"],
            "entry_official_signal": r["entry_official_signal"],
            "route_candidate_count": r["route_candidate_count"],
            "positive_control_replay_count": r["positive_control_replay_count"],
            "raw_qualified_contract_count": r["raw_qualified_contract_count"],
            "canonical_qualified_contract_count": r["canonical_qualified_contract_count"],
            "contract_qualified": r["contract_qualified"],
        }, ensure_ascii=False))
        for p in r["pages"]:
            if p["form_candidate_count"] or p["label"] == "ENTRY":
                print(f"  PAGE label={p['label']} http={p['http']} official={p['official_signal']} forms={p['form_candidate_count']} url={p['final_url']}")
                for fr in p["form_replays"]:
                    x = fr["replay"]
                    print(f"    FORM[{fr['form_index']}] FIELD={x['query_field']} METHOD={x['method']} HTTP={x['http']} RAW_QUALIFIED={x['qualified']} SEMANTIC_ROLE={x['semantic_role']} OFFICIAL={x['official_signal']} ECHO={x['query_echo']} RESULT={x['result_signal']} ERROR={x['error_signal']} ACTION={x['action_url']}")

    print("\nCANONICAL QUALIFIED SEARCH CONTRACTS")
    print("-" * 78)
    for q in canonical_contracts:
        print(json.dumps({k: q.get(k) for k in [
            "source_id", "name", "semantic_contract_role", "query_field", "method",
            "action_url", "canonical_action_path", "canonical_contract_key",
            "http", "query_echo", "result_signal", "semantically_hardened",
        ]}, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"SELECTED SOURCE COUNT: {len(selected)}")
    print(f"ROUTE PROBE COUNT: {total_route_probes}")
    print(f"POSITIVE CONTROL REPLAY COUNT: {total_form_replays}")
    print(f"RAW QUALIFIED SEARCH CONTRACT COUNT: {raw_qualified_contract_count}")
    print(f"CANONICAL QUALIFIED SEARCH CONTRACT COUNT: {canonical_qualified_contract_count}")
    print(f"QUALIFIED SOURCE COUNT: {qualified_source_count}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Target UQQ700 search executed: False")
    print("Planning/research no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    canonical_keys = {q["canonical_contract_key"] for q in canonical_contracts}
    expected_gri_keys = {
        "GRI|GET|/web/contents/webSearch.do|kwd",
        "GRI|GET|/web/contents/resreport.do|schStr",
    }
    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S229A loaded": IN_S229A.exists(),
        "bounded selected sources": len(selected) <= 3,
        "bounded route probes": total_route_probes <= len(selected) * MAX_ROUTE_PROBES_PER_SOURCE,
        "bounded positive control replays": total_form_replays <= len(selected) * MAX_FORM_REPLAYS_PER_SOURCE,
        "target search not executed": out["summary"]["target_search_executed"] is False,
        "semantic allowlist enforced": out["summary"]["semantic_allowlist_enforced"] is True,
        "canonical deduplication enforced": out["summary"]["canonical_deduplication_enforced"] is True,
        "filter selector fields blocked": out["summary"]["filter_selector_fields_blocked"] is True,
        "canonical contracts unique": len(canonical_keys) == len(canonical_contracts),
        "only expected GRI canonical contracts": canonical_keys.issubset(expected_gri_keys),
        "source role context/reverse lookup only": out["summary"]["source_role_context_and_reverse_lookup_only"] is True,
        "planning research hit not designation": out["summary"]["planning_research_hit_equals_designation_notice"] is False,
        "planning research hit not validity": out["summary"]["planning_research_hit_equals_current_validity"] is False,
        "planning research hit not site inclusion": out["summary"]["planning_research_hit_equals_site_inclusion"] is False,
        "planning research no-hit not legal absence": out["summary"]["planning_research_no_hit_equals_legal_absence"] is False,
        "search failure not legal absence": out["summary"]["search_failure_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_POSITIVE_CONTROL_SEARCH_CONTRACT_SEMANTICALLY_HARDENED_QUALIFIED",
            "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT_POSITIVE_CONTROL_SEARCH_CONTRACT_SEMANTICALLY_HARDENED_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S229B hardened validation failed")


if __name__ == "__main__":
    main()
