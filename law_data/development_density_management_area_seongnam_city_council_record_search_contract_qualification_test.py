# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode, urljoin

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_council_record_search_contract_qualification.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD"
POSITIVE_CONTROL = "도시계획"

ROUTES = [
    {
        "family": "MINUTES",
        "url": "https://www.sncouncil.go.kr/kr/assembly/details.do",
        "allowed_target_fields": ["keyword"],
    },
    {
        "family": "AGENDA",
        "url": "https://www.sncouncil.go.kr/kr/bill/bill.do",
        "allowed_target_fields": ["subject"],
    },
    {
        "family": "SEARCH",
        "url": "https://www.sncouncil.go.kr/kr/open/search.do",
        "allowed_target_fields": ["keyword"],
    },
]

SEARCH_HINTS = [
    "search", "srch", "query", "keyword", "keyWord", "searchWord", "searchText",
    "sch", "sword", "word", "kwd", "q", "text", "title", "content", "subject",
    "searchKeyword", "searchTerm", "searchValue", "searchTxt",
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


def parse_forms(base_url: str, text: str) -> list[dict]:
    rows = []
    for fm in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", text):
        attrs, body = fm.group(1), fm.group(2)
        method = (attr(attrs, "method") or "GET").upper()
        action = urljoin(base_url, attr(attrs, "action") or base_url)
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
                "id": attr(a, "id"),
            })
        for sm in re.finditer(r"(?is)<select\b([^>]*)>(.*?)</select>", body):
            a, sb = sm.group(1), sm.group(2)
            name = attr(a, "name")
            if not name:
                continue
            selected = re.search(r'(?is)<option\b([^>]*)selected[^>]*>', sb)
            first = re.search(r'(?is)<option\b([^>]*)>', sb)
            opt = selected or first
            value = attr(opt.group(1), "value") if opt else ""
            inputs.append({"name": name, "type": "select", "value": value or "", "id": attr(a, "id")})
        search_fields = []
        for i in inputs:
            n = i["name"]
            t = i["type"]
            if t in {"text", "search", ""} or any(h.lower() in n.lower() for h in SEARCH_HINTS):
                if n not in search_fields:
                    search_fields.append(n)
        body_plain = strip_tags(body)
        search_signal = any(x in body_plain for x in ["검색", "조회"]) or any("search" in (i.get("name") or "").lower() for i in inputs)
        rows.append({
            "method": method,
            "action_url": action,
            "form_id": attr(attrs, "id"),
            "form_name": attr(attrs, "name"),
            "inputs": inputs,
            "search_fields": search_fields,
            "search_signal": search_signal,
        })
    return rows


def build_payload(form: dict, query_field: str) -> dict:
    payload = {}
    for i in form.get("inputs", []):
        if i.get("type") in {"submit", "button", "image", "file", "reset"}:
            continue
        payload[i["name"]] = i.get("value") or ""
    payload[query_field] = POSITIVE_CONTROL
    for k in list(payload):
        if k.lower() in {"page", "pageindex", "pageno", "currentpage", "currpage"}:
            payload[k] = "1"
    return payload


def qualify_form(page_url: str, form: dict, allowed_fields: list[str]) -> list[dict]:
    results = []
    for field in [f for f in form.get("search_fields", []) if f in allowed_fields]:
        payload = build_payload(form, field)
        rr = curl(form["action_url"], method=form["method"], data=payload, referer=page_url)
        text = decode(rr.get("body") or b"")
        plain = strip_tags(text)
        query_echo = POSITIVE_CONTROL in text or POSITIVE_CONTROL in plain
        error_signal = any(x in plain.lower() for x in ["error", "오류", "잘못된 접근", "페이지를 찾을 수 없습니다"])
        result_signal = any(x in plain for x in ["검색결과", "검색 결과", "회의록", "의안", "도시계획", "검색어"])
        body_ok = len(rr.get("body") or b"") > 1000
        semantic_field_allowed = field in allowed_fields
        qualified = (
            semantic_field_allowed
            and rr.get("http") == "200"
            and body_ok
            and not error_signal
            and query_echo
            and result_signal
        )
        results.append({
            "qualified": qualified,
            "semantic_field_allowed": semantic_field_allowed,
            "query_field": field,
            "method": form["method"],
            "action_url": form["action_url"],
            "payload_keys": sorted(payload.keys()),
            "http": rr.get("http"),
            "final_url": rr.get("final_url"),
            "content_type": rr.get("content_type"),
            "redirects": rr.get("redirects"),
            "body_size": len(rr.get("body") or b""),
            "query_echo": query_echo,
            "result_signal": result_signal,
            "error_signal": error_signal,
            "text_sample": plain[:1200],
        })
    return results


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY COUNCIL RECORD SEARCH CONTRACT QUALIFICATION - S228C HARDENED")
    print("=" * 78)
    print("Purpose: qualify only semantically valid target-search fields using positive control")
    print("Positive control:", POSITIVE_CONTROL)
    print("Allowed fields: MINUTES=keyword, AGENDA=subject, SEARCH=keyword")
    print("UQQ700 target search: DISABLED")
    print("Council record hit != designation/current validity/site inclusion")
    print("Council no-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    route_results = []
    qualified_contracts = []

    for route in ROUTES:
        rr = curl(route["url"])
        text = decode(rr.get("body") or b"")
        forms = parse_forms(rr.get("final_url") or route["url"], text) if rr.get("http") == "200" else []
        form_results = []
        for idx, form in enumerate(forms):
            semantic_fields = [f for f in form.get("search_fields", []) if f in route["allowed_target_fields"]]
            if not semantic_fields or not form.get("search_signal"):
                continue
            quals = qualify_form(rr.get("final_url") or route["url"], form, route["allowed_target_fields"])
            form_results.append({
                "form_index": idx,
                "form": form,
                "allowed_target_fields": route["allowed_target_fields"],
                "semantic_fields_present": semantic_fields,
                "qualifications": quals,
            })
            for q in quals:
                if q.get("qualified"):
                    qualified_contracts.append({
                        "family": route["family"],
                        "page_url": rr.get("final_url") or route["url"],
                        "form_index": idx,
                        **q,
                    })
        route_results.append({
            "family": route["family"],
            "url": route["url"],
            "allowed_target_fields": route["allowed_target_fields"],
            "http": rr.get("http"),
            "final_url": rr.get("final_url"),
            "content_type": rr.get("content_type"),
            "redirects": rr.get("redirects"),
            "body_size": len(rr.get("body") or b""),
            "form_count": len(forms),
            "semantic_search_form_candidate_count": len(form_results),
            "search_forms": form_results,
        })

    family_status = {}
    for fam in ["MINUTES", "AGENDA", "SEARCH"]:
        qs = [q for q in qualified_contracts if q["family"] == fam]
        family_status[fam] = {
            "qualified": bool(qs),
            "qualified_contract_count": len(qs),
            "contracts": qs,
        }

    qualified_family_count = sum(1 for v in family_status.values() if v["qualified"])
    qualified_contract_count = len(qualified_contracts)

    if qualified_contract_count > 0:
        classification = "SEONGNAM_CITY_COUNCIL_RECORD_SEARCH_CONTRACT_SEMANTICALLY_HARDENED_QUALIFIED"
        semantic = "ONLY_SEMANTICALLY_VALID_COUNCIL_TARGET_SEARCH_FIELDS_WERE_POSITIVE_CONTROL_QUALIFIED"
        next_action = "RUN_BOUNDED_UQQ700_TARGET_SEARCH_ONLY_ON_MINUTES_KEYWORD_AND_AGENDA_SUBJECT_QUALIFIED_CONTRACTS_AS_HISTORICAL_REVERSE_LOOKUP_ANCHORS"
    else:
        classification = "SEONGNAM_CITY_COUNCIL_RECORD_SEARCH_CONTRACT_SEMANTIC_HARDENING_TECHNICAL_UNKNOWN"
        semantic = "NO_SEMANTICALLY_VALID_COUNCIL_TARGET_SEARCH_FIELD_WAS_POSITIVE_CONTROL_QUALIFIED"
        next_action = "HARDEN_ONLY_SEMANTIC_TARGET_SEARCH_FIELDS_WITHOUT_UQQ700_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-159-S228C-H",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "positive_control_query": POSITIVE_CONTROL,
        "semantic_field_policy": {
            "MINUTES": ["keyword"],
            "AGENDA": ["subject"],
            "SEARCH": ["keyword"],
            "excluded_false_positive_fields": ["startDay", "endDay", "proposer"],
            "query_echo_required": True,
            "result_signal_required": True,
        },
        "routes": route_results,
        "family_status": family_status,
        "qualified_family_count": qualified_family_count,
        "qualified_search_contract_count": qualified_contract_count,
        "qualified_search_contracts": qualified_contracts,
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
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nROUTE QUALIFICATION")
    print("-" * 78)
    for r in route_results:
        print(f"FAMILY={r['family']} URL={r['url']}")
        print(f"  ALLOWED_TARGET_FIELDS={r['allowed_target_fields']}")
        print(f"  HTTP={r['http']} FINAL={r['final_url']} BODY_SIZE={r['body_size']}")
        print(f"  FORM_COUNT={r['form_count']} SEMANTIC_SEARCH_FORM_CANDIDATES={r['semantic_search_form_candidate_count']}")
        for sf in r["search_forms"]:
            f = sf["form"]
            print(f"  FORM[{sf['form_index']}] METHOD={f['method']} ACTION={f['action_url']} SEARCH_FIELDS={f['search_fields']}")
            for q in sf["qualifications"]:
                print(f"    FIELD={q['query_field']} SEMANTIC_ALLOWED={q['semantic_field_allowed']} QUALIFIED={q['qualified']} HTTP={q['http']} BODY={q['body_size']} ECHO={q['query_echo']} RESULT_SIGNAL={q['result_signal']} ERROR={q['error_signal']}")

    print("\nQUALIFIED SEARCH CONTRACTS")
    print("-" * 78)
    for q in qualified_contracts:
        print(json.dumps(q, ensure_ascii=False))

    print("\nFAMILY STATUS")
    print("-" * 78)
    for fam, st in family_status.items():
        print(f"{fam}: QUALIFIED={st['qualified']} CONTRACT_COUNT={st['qualified_contract_count']}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"QUALIFIED FAMILY COUNT: {qualified_family_count}")
    print(f"QUALIFIED SEARCH CONTRACT COUNT: {qualified_contract_count}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Target UQQ700 search executed: False")
    print("Council record no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    expected_fields = {(q["family"], q["query_field"]) for q in qualified_contracts}
    no_forbidden_fields = all(q["query_field"] not in {"startDay", "endDay", "proposer"} for q in qualified_contracts)
    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "exact three recovered routes tested": len(route_results) == 3,
        "forbidden semantic fields excluded": no_forbidden_fields,
        "qualified fields limited to minutes keyword / agenda subject / search keyword": expected_fields.issubset({("MINUTES", "keyword"), ("AGENDA", "subject"), ("SEARCH", "keyword")}),
        "query echo required": out["semantic_field_policy"]["query_echo_required"] is True,
        "target search not executed": out["summary"]["target_search_executed"] is False,
        "positive control only": out["summary"]["positive_control_only"] is True,
        "council hit not designation": out["summary"]["council_record_hit_equals_designation_notice"] is False,
        "council hit not validity": out["summary"]["council_record_hit_equals_current_validity"] is False,
        "council hit not site inclusion": out["summary"]["council_record_hit_equals_site_inclusion"] is False,
        "council no-hit not legal absence": out["summary"]["council_record_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_CITY_COUNCIL_RECORD_SEARCH_CONTRACT_SEMANTICALLY_HARDENED_QUALIFIED",
            "SEONGNAM_CITY_COUNCIL_RECORD_SEARCH_CONTRACT_SEMANTIC_HARDENING_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S228C semantic hardening validation failed")


if __name__ == "__main__":
    main()
