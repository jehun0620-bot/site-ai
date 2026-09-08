# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT_PATH = OUT_DIR / "development_density_management_area_molit_i0204_search_submit_semantics_hardening_test.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
LIST_URL = "https://www.molit.go.kr/USR/I0204/m_45/lst.jsp"
OFFICIAL_HOSTS = {"www.molit.go.kr", "molit.go.kr"}

# UQQ700 is deliberately NOT queried in this step.
UQQ700_QUERY_EXECUTED = False

# Baseline first-page size and bounded historical probe depth.
PSIZE = "10"
POSITIVE_CONTROL_PAGE = "2"


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def strip_tags(value: str | None) -> str:
    return normalize_space(re.sub(r"<[^>]+>", " ", value or ""))


def page_title(html: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", html or "", flags=re.I | re.S)
    return strip_tags(m.group(1)) if m else None


def parse_attrs(raw: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for m in re.finditer(
        r"([:\w-]+)(?:\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+)))?",
        raw or "",
        flags=re.I | re.S,
    ):
        name = (m.group(1) or "").lower()
        if not name:
            continue
        value = next((g for g in m.groups()[1:] if g is not None), "")
        attrs[name] = unescape(value)
    return attrs


def extract_detail_rows(html: str) -> list[dict]:
    rows: list[dict] = []
    seen = set()
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html or "", flags=re.I | re.S):
        attrs = parse_attrs(m.group(1))
        href = unescape(attrs.get("href", ""))
        text = strip_tags(m.group(2))
        if not href or "dtl.jsp" not in href:
            continue
        absolute = urljoin(LIST_URL, href)
        parsed = urlparse(absolute)
        qs = parse_qs(parsed.query)
        idx = (qs.get("idx") or [None])[0]
        key = (idx, text)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "title": text,
                "idx": idx,
                "href": href,
                "absolute_url": absolute,
                "host": parsed.netloc,
            }
        )
    return rows


def extract_form_diagnostics(html: str) -> list[dict]:
    forms = []
    for fm in re.finditer(r"<form\b([^>]*)>(.*?)</form>", html or "", flags=re.I | re.S):
        fattrs = parse_attrs(fm.group(1))
        body = fm.group(2)
        controls = []

        for im in re.finditer(r"<input\b([^>]*)>", body, flags=re.I | re.S):
            attrs = parse_attrs(im.group(1))
            controls.append(
                {
                    "tag": "input",
                    "type": (attrs.get("type") or "text").lower(),
                    "name": attrs.get("name"),
                    "value": attrs.get("value", ""),
                    "checked": "checked" in attrs,
                    "onclick": attrs.get("onclick"),
                    "id": attrs.get("id"),
                    "class": attrs.get("class"),
                }
            )

        for bm in re.finditer(r"<button\b([^>]*)>(.*?)</button>", body, flags=re.I | re.S):
            attrs = parse_attrs(bm.group(1))
            controls.append(
                {
                    "tag": "button",
                    "type": (attrs.get("type") or "submit").lower(),
                    "name": attrs.get("name"),
                    "value": attrs.get("value", ""),
                    "text": strip_tags(bm.group(2)),
                    "checked": False,
                    "onclick": attrs.get("onclick"),
                    "id": attrs.get("id"),
                    "class": attrs.get("class"),
                }
            )

        select_names = []
        for sm in re.finditer(r"<select\b([^>]*)>(.*?)</select>", body, flags=re.I | re.S):
            attrs = parse_attrs(sm.group(1))
            name = attrs.get("name")
            options = []
            for om in re.finditer(r"<option\b([^>]*)>(.*?)</option>", sm.group(2), flags=re.I | re.S):
                oattrs = parse_attrs(om.group(1))
                options.append(
                    {
                        "value": oattrs.get("value", ""),
                        "selected": "selected" in oattrs,
                        "text": strip_tags(om.group(2)),
                    }
                )
            if name:
                select_names.append(name)
            controls.append(
                {
                    "tag": "select",
                    "name": name,
                    "options": options,
                    "id": attrs.get("id"),
                    "class": attrs.get("class"),
                }
            )

        action = urljoin(LIST_URL, fattrs.get("action") or LIST_URL)
        method = (fattrs.get("method") or "GET").upper()
        signal = sum(
            1
            for c in controls
            if c.get("name") in {"srch_usr_titl", "srch_usr_nm", "srch_usr_ctnt", "flag", "search", "lcmspage"}
        )
        forms.append(
            {
                "method": method,
                "action": action,
                "onsubmit": fattrs.get("onsubmit"),
                "id": fattrs.get("id"),
                "name": fattrs.get("name"),
                "class": fattrs.get("class"),
                "signal": signal,
                "controls": controls,
                "select_names": select_names,
            }
        )
    forms.sort(key=lambda x: x["signal"], reverse=True)
    return forms


def extract_js_clues(html: str) -> list[str]:
    patterns = [
        r"function\s+[\w$]+\s*\([^)]*\)\s*\{.*?\}",
        r"onsubmit\s*=\s*[\"'][^\"']+[\"']",
        r"onclick\s*=\s*[\"'][^\"']+[\"']",
        r"document\.[\w$.\[\]'\"]+\.(?:submit|value)\s*\([^;]*\)?;?",
    ]
    out = []
    for pat in patterns:
        for m in re.finditer(pat, html or "", flags=re.I | re.S):
            snippet = normalize_space(m.group(0))
            if any(token in snippet for token in ["srch_usr", "search", "submit", "lcmspage", "flag"]):
                out.append(snippet[:1200])
    dedup = []
    seen = set()
    for item in out:
        if item not in seen:
            seen.add(item)
            dedup.append(item)
    return dedup[:80]


def fetch(session: requests.Session, params: dict[str, str]) -> dict:
    out = {
        "params": params,
        "http": None,
        "final_url": None,
        "official_final_host": False,
        "page_title": None,
        "technical_unknown": True,
        "rows": [],
        "error": None,
    }
    try:
        r = session.get(LIST_URL, params=params, timeout=30, allow_redirects=True)
        out["http"] = r.status_code
        out["final_url"] = r.url
        out["official_final_host"] = urlparse(r.url).netloc in OFFICIAL_HOSTS
        out["page_title"] = page_title(r.text)
        r.raise_for_status()
        out["rows"] = extract_detail_rows(r.text)
        out["technical_unknown"] = False
        out["html"] = r.text
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def baseline_params(page: str = "1") -> dict[str, str]:
    return {
        "gubun": "",
        "flag": "I",
        "r_id": "",
        "lcmspage": page,
        "search_dept_id": "",
        "search_dept_nm": "",
        "search_regdate_s": "",
        "search_regdate_e": "",
        "srch_usr_year": "",
        "srch_usr_num": "",
        "srch_usr_nm": "Y",
        "srch_usr_titl": "",
        "srch_usr_ctnt": "Y",
        "search": "",
        "psize": PSIZE,
    }


def title_search_params(title: str) -> dict[str, str]:
    params = baseline_params("1")
    params["srch_usr_titl"] = title
    return params


def idx_set(rows: list[dict]) -> set[str]:
    return {str(row.get("idx")) for row in rows if row.get("idx") is not None}


def main() -> None:
    print("=" * 78)
    print("MOLIT I0204 SEARCH SUBMIT SEMANTICS HARDENING TEST")
    print("=" * 78)
    print("Purpose: prove actual MOLIT search semantics against baseline before any further UQQ700 query")
    print("UQQ700 term is NOT queried in this step")
    print("Search replay != designation/current validity/site inclusion")
    print("Search failure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; site-ai STEP17 MOLIT submit semantics hardening)",
            "Referer": "https://www.molit.go.kr/",
        }
    )

    base1 = fetch(session, baseline_params("1"))
    base2 = fetch(session, baseline_params(POSITIVE_CONTROL_PAGE))

    form_diagnostics = []
    js_clues = []
    if not base1["technical_unknown"]:
        form_diagnostics = extract_form_diagnostics(base1.pop("html", ""))
        # fetch again only from the already captured HTML source is not possible after pop; preserve via base1_html below.
    # Re-fetch bounded baseline page 1 only for structure diagnostics if needed.
    structure = fetch(session, baseline_params("1"))
    structure_html = structure.pop("html", "") if not structure["technical_unknown"] else ""
    if structure_html:
        form_diagnostics = extract_form_diagnostics(structure_html)
        js_clues = extract_js_clues(structure_html)

    base1_ids = idx_set(base1["rows"])
    base2_candidates = [row for row in base2["rows"] if str(row.get("idx")) not in base1_ids and row.get("title")]
    positive_control = base2_candidates[0] if base2_candidates else None

    positive_search = None
    if positive_control:
        positive_search = fetch(session, title_search_params(str(positive_control["title"])))
        positive_search.pop("html", None)

    base1.pop("html", None)
    base2.pop("html", None)

    positive_verified = False
    search_changed_baseline = False
    positive_idx_match = False
    positive_title_match = False

    if positive_control and positive_search and not positive_search["technical_unknown"]:
        search_ids = idx_set(positive_search["rows"])
        positive_idx_match = str(positive_control["idx"]) in search_ids
        expected_title = normalize_space(str(positive_control["title"]))
        positive_title_match = any(normalize_space(row.get("title")) == expected_title for row in positive_search["rows"])
        search_changed_baseline = search_ids != base1_ids
        positive_verified = bool(
            positive_search["http"] == 200
            and positive_search["official_final_host"]
            and positive_idx_match
            and positive_title_match
            and search_changed_baseline
        )

    relevant_controls = []
    if form_diagnostics:
        for c in form_diagnostics[0].get("controls", []):
            if c.get("name") in {"flag", "lcmspage", "srch_usr_nm", "srch_usr_titl", "srch_usr_ctnt", "search"} \
                or c.get("type") in {"submit", "button", "checkbox", "radio", "hidden"}:
                relevant_controls.append(c)

    any_technical_unknown = any(
        x.get("technical_unknown")
        for x in [base1, base2, structure, positive_search or {"technical_unknown": False}]
    )

    if any_technical_unknown:
        classification = "MOLIT_I0204_SEARCH_SUBMIT_SEMANTICS_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_ONLY_TRANSPORT_OR_STRUCTURE_CAPTURE_WITHOUT_LEGAL_INFERENCE"
    elif positive_control is None:
        classification = "MOLIT_I0204_NO_OUTSIDE_FIRST_PAGE_POSITIVE_CONTROL_RECOVERED"
        next_action = "RECOVER_A_BOUNDED_OFF_FIRST_PAGE_OFFICIAL_DOCUMENT_IDENTITY_BEFORE_SEARCH_QUALIFICATION"
    elif positive_verified:
        classification = "MOLIT_I0204_TITLE_SEARCH_SEMANTICS_POSITIVE_CONTROL_VERIFIED"
        next_action = "REQUALIFY_BOUNDED_UQQ700_TITLE_SEARCH_USING_THE_VERIFIED_SUBMIT_SEMANTICS_ONLY"
    else:
        classification = "MOLIT_I0204_TITLE_SEARCH_SEMANTICS_NOT_VERIFIED_BASELINE_CONTAMINATION_PERSISTS"
        next_action = "RECOVER_REQUIRED_SUBMIT_CONTROL_OR_SERVER_SIDE_FIELD_SEMANTICS_BEFORE_ANY_UQQ700_QUERY"

    out = {
        "step": "STEP17-MOLIT-I0204-SEARCH-SUBMIT-SEMANTICS-HARDENING",
        "target_name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "list_url": LIST_URL,
        "uqq700_query_executed": UQQ700_QUERY_EXECUTED,
        "baseline_page_1": base1,
        "baseline_page_2": base2,
        "structure_probe": structure,
        "form_diagnostics": form_diagnostics,
        "relevant_controls": relevant_controls,
        "js_clues": js_clues,
        "positive_control": positive_control,
        "positive_search": positive_search,
        "positive_idx_match": positive_idx_match,
        "positive_title_match": positive_title_match,
        "search_changed_baseline": search_changed_baseline,
        "positive_verified": positive_verified,
        "classification": classification,
        "summary": {
            "next_action": next_action,
            "prior_positive_control_qualification_reliable": False if not positive_verified else True,
            "prior_uqq700_candidate_classification_reliable": False,
            "search_replay_equals_designation": False,
            "search_replay_equals_current_validity": False,
            "search_replay_equals_site_inclusion": False,
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
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("BASELINE / POSITIVE CONTROL")
    print("=" * 78)
    print(f"BASELINE PAGE 1: http={base1['http']} rows={len(base1['rows'])} ids={sorted(base1_ids)}")
    print(f"BASELINE PAGE 2: http={base2['http']} rows={len(base2['rows'])}")
    if positive_control:
        print(f"POSITIVE CONTROL: idx={positive_control['idx']} title={positive_control['title']}")
    else:
        print("POSITIVE CONTROL: None")

    print("\n" + "=" * 78)
    print("FORM / SUBMIT DIAGNOSTICS")
    print("=" * 78)
    if form_diagnostics:
        form = form_diagnostics[0]
        print(f"FORM method={form['method']} action={form['action']} onsubmit={form['onsubmit']!r}")
        for control in relevant_controls:
            print(f"CONTROL {control}")
    else:
        print("FORM: not captured")
    print(f"JS CLUES: {len(js_clues)}")
    for clue in js_clues[:30]:
        print(f"  {clue}")

    print("\n" + "=" * 78)
    print("POSITIVE SEARCH REPLAY")
    print("=" * 78)
    if positive_search:
        print(
            f"http={positive_search['http']} rows={len(positive_search['rows'])} "
            f"idx_match={positive_idx_match} title_match={positive_title_match} "
            f"changed_vs_baseline={search_changed_baseline} verified={positive_verified}"
        )
        print(f"final={positive_search['final_url']}")
        for row in positive_search["rows"][:20]:
            print(f"  RESULT idx={row['idx']} title={row['title']}")
    else:
        print("positive search not executed")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"Positive control verified: {positive_verified}")
    print("Prior UQQ700 candidate classification reliable: False")
    print("UQQ700 query executed: False")
    print("Search replay == designation: False")
    print("Search replay == current validity: False")
    print("Search replay == site inclusion: False")
    print("Search failure == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET_NAME,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "official list URL fixed": out["list_url"] == LIST_URL,
        "UQQ700 not queried": out["uqq700_query_executed"] is False,
        "technical state explicit": isinstance(any_technical_unknown, bool),
        "prior UQQ700 candidate classification blocked": out["summary"]["prior_uqq700_candidate_classification_reliable"] is False,
        "search replay not designation": out["summary"]["search_replay_equals_designation"] is False,
        "search replay not validity": out["summary"]["search_replay_equals_current_validity"] is False,
        "search replay not site inclusion": out["summary"]["search_replay_equals_site_inclusion"] is False,
        "search failure not legal absence": out["summary"]["search_failure_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT_PATH.exists() and OUT_PATH.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for key, value in validation.items():
        print(f"{key}: {value}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT_PATH}")
    if not all(validation.values()):
        raise AssertionError("MOLIT I0204 search submit semantics hardening validation failed")


if __name__ == "__main__":
    main()
