# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_S230E = OUT_DIR / "development_density_management_area_gyeonggi_historical_local_gazette_notice_archive_alternate_entry_qualification.json"
IN_S230G = OUT_DIR / "development_density_management_area_gyeonggi_ebook_gazette_archive_uqq700_bounded_target_search.json"
OUT = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_uqq700_bounded_search_contract.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
ENTRY = "https://www.gg.go.kr/bbs/board.do?bsIdx=769&menuId=1786"
HOST = "www.gg.go.kr"
TIMEOUT = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Referer": ENTRY,
}

GENERIC_CONTROLS = ["경기도보", "고시"]
QUERIES = [
    ("EXACT", "개발밀도관리구역"),
    ("VARIANT", "개발밀도 관리구역"),
    ("WEAK", "개발밀도"),
]

SEARCH_NAME_RE = re.compile(r"(?:search|srch|query|keyword|key|word|text|title|subject|sch)", re.I)
DETAIL_HINT_RE = re.compile(r"(?:boardView|view|detail|bbs|article|post|idx|seq|no|sn)", re.I)
NOTICE_ID_RE = re.compile(r"(?:고시|공고)\s*제?\s*(\d{4})\s*[-–]\s*(\d{1,5})\s*호")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def fetch(session: requests.Session, url: str, params=None, data=None, method="GET"):
    try:
        if method == "POST":
            return session.post(url, params=params, data=data, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True)
        return session.get(url, params=params, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True)
    except requests.RequestException:
        return None


def decoded_text(r: requests.Response) -> str:
    encs = []
    if r.encoding:
        encs.append(r.encoding)
    encs += ["utf-8", "euc-kr", "cp949"]
    best, best_score = None, -10**9
    for enc in dict.fromkeys(encs):
        try:
            t = r.content.decode(enc, errors="replace")
        except Exception:
            continue
        score = len(re.findall(r"[가-힣]", t)) - (t.count("�") * 10)
        if score > best_score:
            best, best_score = t, score
    return best if best is not None else r.text


def form_descriptors(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for i, form in enumerate(soup.find_all("form"), 1):
        method = (form.get("method") or "GET").upper()
        action = urljoin(base_url, form.get("action") or base_url)
        controls = []
        for tag in form.find_all(["input", "select", "textarea"]):
            name = tag.get("name")
            if not name:
                continue
            item = {"tag": tag.name, "name": name, "type": tag.get("type"), "value": tag.get("value", ""), "options": []}
            if tag.name == "select":
                item["options"] = [
                    {"value": o.get("value", ""), "text": norm(o.get_text(" ", strip=True))}
                    for o in tag.find_all("option")
                ]
            controls.append(item)
        out.append({"form_index": i, "method": method, "action": action, "controls": controls})
    return out


def default_payload(desc: dict):
    payload = {}
    for c in desc["controls"]:
        if c["tag"] == "select":
            selected = next((o["value"] for o in c["options"] if o["value"]), "")
            payload[c["name"]] = selected
        elif c["tag"] == "input":
            typ = (c.get("type") or "text").lower()
            if typ in {"submit", "button", "image", "reset", "file"}:
                continue
            payload[c["name"]] = c.get("value", "") or ""
        else:
            payload[c["name"]] = c.get("value", "") or ""
    return payload


def keyword_fields(desc: dict):
    fields = []
    for c in desc["controls"]:
        typ = (c.get("type") or "text").lower()
        if c["tag"] in {"input", "textarea"} and typ in {"text", "search", "hidden", ""} and SEARCH_NAME_RE.search(c["name"]):
            fields.append(c["name"])
    return sorted(set(fields))


def canonical_rows(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")
    rows, seen = [], set()
    for a in soup.find_all("a", href=True):
        title = norm(a.get_text(" ", strip=True))
        href = urljoin(base_url, a["href"])
        if not title:
            continue
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)
        detailish = DETAIL_HINT_RE.search(href) is not None or any(DETAIL_HINT_RE.search(k or "") for k in qs)
        if not detailish:
            continue
        key = (title, href)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"title": title, "url": href})
    return rows


def sig(rows):
    return sorted({f"{r['title']}|{r['url']}" for r in rows})


def execute_contract(session, desc, field, term):
    payload = default_payload(desc)
    for f in keyword_fields(desc):
        payload[f] = ""
    payload[field] = term
    if desc["method"] == "POST":
        r = fetch(session, desc["action"], data=payload, method="POST")
    else:
        r = fetch(session, desc["action"], params=payload, method="GET")
    return r, payload


def detail_probe(session, row: dict, terms: list[str]):
    r = fetch(session, row["url"])
    if r is None:
        return {"url": row["url"], "http": None, "technical_unknown": True, "target_hit": False, "notice_identities": []}
    text = norm(BeautifulSoup(decoded_text(r), "html.parser").get_text(" ", strip=True))
    hit = any(t in text for t in terms)
    notices = []
    for m in NOTICE_ID_RE.finditer(text):
        notices.append({"literal": norm(m.group(0)), "canonical": f"{int(m.group(1)):04d}-{int(m.group(2))}"})
    return {
        "url": r.url,
        "http": r.status_code,
        "technical_unknown": r.status_code != 200,
        "target_hit": hit,
        "notice_identities": notices[:20],
        "text_sample": text[:1200],
    }


def main():
    print("=" * 78)
    print("GYEONGGI GAZETTE BOARD UQQ700 BOUNDED SEARCH CONTRACT - S230H")
    print("=" * 78)
    print("Purpose: recover board search contract, positive-control it, then run only three bounded UQQ700 queries")
    print("Search hit != designation/current validity/site inclusion")
    print("No-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    s230e = load_json(IN_S230E)
    s230g = load_json(IN_S230G)
    assert s230g.get("classification") == "GYEONGGI_EBOOK_GAZETTE_UQQ700_BOUNDED_SEARCH_NO_VERIFIED_TARGET_RESULT"

    session = requests.Session()
    entry = fetch(session, ENTRY)
    if entry is None:
        raise RuntimeError("GG gazette board entry request failed")
    html = decoded_text(entry)
    forms = form_descriptors(html, entry.url)
    baseline_rows = canonical_rows(html, entry.url)
    baseline_sig = sig(baseline_rows)

    experiments = []
    for desc in forms:
        for field in keyword_fields(desc):
            for term in GENERIC_CONTROLS:
                r, payload = execute_contract(session, desc, field, term)
                if r is None:
                    experiments.append({"form_index": desc["form_index"], "field": field, "term": term, "http": None, "changed": False, "result_count": None})
                    continue
                rows = canonical_rows(decoded_text(r), r.url)
                experiments.append({
                    "form_index": desc["form_index"], "method": desc["method"], "action": desc["action"],
                    "field": field, "term": term, "http": r.status_code, "final_url": r.url,
                    "changed": sig(rows) != baseline_sig, "result_count": len(rows), "payload": payload,
                })

    stats = {}
    for e in experiments:
        key = (e["form_index"], e["field"])
        s = stats.setdefault(key, {"runs": 0, "http_200": 0, "changed": 0})
        s["runs"] += 1
        s["http_200"] += int(e.get("http") == 200)
        s["changed"] += int(e.get("changed") is True)

    qualified = []
    for (form_index, field), s in stats.items():
        if s["runs"] == len(GENERIC_CONTROLS) and s["http_200"] == s["runs"] and s["changed"] == s["runs"]:
            qualified.append({"form_index": form_index, "field": field, **s})

    contract_qualified = len(qualified) == 1
    target_results = []
    total_detail = 0

    if contract_qualified:
        q = qualified[0]
        desc = next(d for d in forms if d["form_index"] == q["form_index"])
        field = q["field"]
        for kind, term in QUERIES:
            r, payload = execute_contract(session, desc, field, term)
            if r is None:
                target_results.append({"query_kind": kind, "query": term, "http": None, "result_row_count": 0, "verified_result_row_hit_count": 0, "detail_probe_count": 0, "detail_target_hit_count": 0, "notice_identity_count": 0, "technical_unknown": True, "status": "TECHNICAL_UNKNOWN", "hit_rows": [], "detail_results": []})
                continue
            page = decoded_text(r)
            rows = canonical_rows(page, r.url)
            terms = [term]
            hit_rows = [row for row in rows if term in norm(row["title"])]
            details = []
            for row in hit_rows[:10]:
                d = detail_probe(session, row, terms)
                d["source_title"] = row["title"]
                details.append(d)
                total_detail += 1
            tech = r.status_code != 200 or any(d["technical_unknown"] for d in details)
            detail_hits = sum(1 for d in details if d["target_hit"])
            notice_count = sum(len(d["notice_identities"]) for d in details if d["target_hit"])
            if tech:
                status = "TECHNICAL_UNKNOWN"
            elif detail_hits:
                status = f"{kind}_VERIFIED_DETAIL_HIT"
            elif hit_rows:
                status = f"{kind}_RESULT_ROW_HIT_UNVERIFIED_DETAIL"
            else:
                status = f"{kind}_NO_VERIFIED_RESULT_HIT"
            target_results.append({
                "query_kind": kind, "query": term, "http": r.status_code, "final_url": r.url,
                "result_row_count": len(rows), "verified_result_row_hit_count": len(hit_rows),
                "detail_probe_count": len(details), "detail_target_hit_count": detail_hits,
                "notice_identity_count": notice_count, "technical_unknown": tech, "status": status,
                "hit_rows": hit_rows[:20], "detail_results": details,
            })

    row_hits = sum(x["verified_result_row_hit_count"] for x in target_results)
    detail_hits = sum(x["detail_target_hit_count"] for x in target_results)
    notice_count = sum(x["notice_identity_count"] for x in target_results)
    tech_count = sum(1 for x in target_results if x["technical_unknown"])

    if not contract_qualified:
        classification = "GYEONGGI_GAZETTE_BOARD_SEARCH_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "A_UNIQUE_FILTERING_SEARCH_CONTRACT_WAS_NOT_QUALIFIED_BY_GENERIC_POSITIVE_CONTROLS"
        next_action = "HARDEN_ONLY_THE_BOARD_SEARCH_CONTRACT_WITHOUT_NEGATIVE_OR_LEGAL_ABSENCE_INFERENCE"
    elif detail_hits > 0:
        classification = "GYEONGGI_GAZETTE_BOARD_UQQ700_BOUNDED_SEARCH_VERIFIED_DETAIL_TARGET_HIT"
        semantic = "ONE_OR_MORE_CANONICAL_BOARD_RESULTS_LED_TO_DETAIL_PAGES_CONTAINING_THE_TARGET_TERM"
        next_action = "VERIFY_GAZETTE_DOCUMENT_IDENTITY_NOTICE_NUMBER_DATE_ATTACHMENT_AND_BODY_BEFORE_ANY_DESIGNATION_PROMOTION"
    elif row_hits > 0:
        classification = "GYEONGGI_GAZETTE_BOARD_UQQ700_BOUNDED_SEARCH_RESULT_ROW_HIT_DETAIL_UNVERIFIED"
        semantic = "TARGET_TERM_APPEARED_IN_CANONICAL_BOARD_ROWS_BUT_DETAIL_CONFIRMATION_IS_NOT_ESTABLISHED"
        next_action = "HARDEN_ONLY_MATCHED_ROWS_AND_DETAIL_OR_ATTACHMENT_PATHS"
    elif tech_count > 0:
        classification = "GYEONGGI_GAZETTE_BOARD_UQQ700_BOUNDED_SEARCH_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_MORE_BOUNDED_TARGET_REQUESTS_OR_MATCHED_DETAILS_REMAIN_TECHNICALLY_UNRESOLVED"
        next_action = "RESOLVE_ONLY_THE_TECHNICAL_UNKNOWN_SURFACE_WITHOUT_TREATING_IT_AS_NO_HIT"
    else:
        classification = "GYEONGGI_GAZETTE_BOARD_UQQ700_BOUNDED_SEARCH_NO_VERIFIED_TARGET_RESULT"
        semantic = "THE_QUALIFIED_GG_GAZETTE_BOARD_SEARCH_CONTRACT_RETURNED_NO_VERIFIED_TARGET_RESULT_FOR_EXACT_VARIANT_OR_WEAK_QUERIES"
        next_action = "TERMINALLY_RECONCILE_THE_GYEONGGI_HISTORICAL_LOCAL_GAZETTE_ALTERNATE_SOURCE_FAMILY_WITHOUT_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP 17-S230H", "target_name": TARGET, "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE, "source_id": "GG_GAZETTE_BOARD", "entry_url": ENTRY,
        "entry_http": entry.status_code, "entry_final_url": entry.url, "s230e_loaded": IN_S230E.exists(),
        "s230g_loaded": IN_S230G.exists(), "form_count": len(forms), "baseline_record_count": len(baseline_rows),
        "positive_control_experiments": experiments, "qualified_contracts": qualified,
        "contract_qualified": contract_qualified, "target_query_count": len(target_results), "target_results": target_results,
        "verified_result_row_hit_count": row_hits, "verified_detail_target_hit_count": detail_hits,
        "notice_identity_count": notice_count, "technical_unknown_query_count": tech_count,
        "detail_probe_count": total_detail, "classification": classification,
        "summary": {
            "semantic_state": semantic, "next_action": next_action,
            "search_hit_equals_designation": False, "document_hit_equals_current_validity": False,
            "document_hit_equals_site_inclusion": False, "no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False, "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False, "official_designation_identity_verified": False,
            "current_validity_verified": False, "site_spatial_inclusion_verified": False,
            "runtime_registration_allowed": False, "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("CONTRACT QUALIFICATION")
    print("=" * 78)
    print(f"ENTRY HTTP: {entry.status_code}")
    print(f"FORM COUNT: {len(forms)}")
    print(f"BASELINE RECORD COUNT: {len(baseline_rows)}")
    print(f"POSITIVE CONTROL EXPERIMENT COUNT: {len(experiments)}")
    print(f"QUALIFIED CONTRACT COUNT: {len(qualified)}")
    print(f"CONTRACT QUALIFIED: {contract_qualified}")
    for q in qualified:
        print("QUALIFIED_CONTRACT:", json.dumps(q, ensure_ascii=False))
    for e in experiments:
        print("POSITIVE_CONTROL:", json.dumps(e, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("BOUNDED TARGET SEARCH")
    print("=" * 78)
    for x in target_results:
        print(json.dumps({k: x[k] for k in ["query_kind", "query", "http", "result_row_count", "verified_result_row_hit_count", "detail_probe_count", "detail_target_hit_count", "notice_identity_count", "technical_unknown", "status"]}, ensure_ascii=False))
        for row in x.get("hit_rows", []):
            print("  HIT_ROW:", json.dumps(row, ensure_ascii=False))
        for d in x.get("detail_results", []):
            print("  DETAIL:", json.dumps({"source_title": d.get("source_title"), "http": d.get("http"), "target_hit": d.get("target_hit"), "notice_identities": d.get("notice_identities"), "url": d.get("url")}, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"TARGET QUERY COUNT: {len(target_results)}")
    print(f"VERIFIED RESULT ROW HIT COUNT: {row_hits}")
    print(f"VERIFIED DETAIL TARGET HIT COUNT: {detail_hits}")
    print(f"NOTICE IDENTITY COUNT: {notice_count}")
    print(f"TECHNICAL UNKNOWN QUERY COUNT: {tech_count}")
    print(f"DETAIL PROBE COUNT: {total_detail}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("No-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S230E loaded": IN_S230E.exists(), "S230G loaded": IN_S230G.exists(),
        "entry host gg": urlparse(entry.url).hostname == HOST,
        "positive controls generic only": all(TARGET not in x for x in GENERIC_CONTROLS),
        "positive controls bounded": len(experiments) <= 40,
        "target queries bounded": len(target_results) in {0, 3},
        "detail probes bounded": total_detail <= 30,
        "search hit not designation": out["summary"]["search_hit_equals_designation"] is False,
        "document hit not validity": out["summary"]["document_hit_equals_current_validity"] is False,
        "document hit not site inclusion": out["summary"]["document_hit_equals_site_inclusion"] is False,
        "no hit not legal absence": out["summary"]["no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": bool(classification), "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for k, v in validation.items():
        print(f"{k}: {v}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")
    if not all(validation.values()):
        raise AssertionError("S230H validation failed")


if __name__ == "__main__":
    main()
