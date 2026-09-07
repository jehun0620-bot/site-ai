# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
TRANSITION_MANIFEST = BASE / "law_data" / "manifests" / "development_density_management_area_e_gazette_terminal_transition_v1.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_search_contract_forensic.json"

ROOT = "https://www.gg.go.kr/"
SEARCH_URL = "https://www.gg.go.kr/search.do"
POSITIVE_CONTROL = "예산"
TARGET = "개발밀도관리구역"
OFFICIAL_RECORD_LABEL = "고시ㆍ공고/채용"


class SurfaceParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.forms = []
        self.current_form = None
        self.scripts = []
        self.links = []
        self.text_parts = []
        self.select_stack = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self.current_form = {
                "action": a.get("action"),
                "method": (a.get("method") or "GET").upper(),
                "id": a.get("id"),
                "name": a.get("name"),
                "fields": [],
            }
            self.forms.append(self.current_form)
        elif tag in {"input", "button", "textarea"} and self.current_form is not None:
            self.current_form["fields"].append({
                "tag": tag,
                "type": a.get("type"),
                "name": a.get("name"),
                "id": a.get("id"),
                "value": a.get("value"),
            })
        elif tag == "select":
            row = {"tag": "select", "name": a.get("name"), "id": a.get("id"), "options": []}
            if self.current_form is not None:
                self.current_form["fields"].append(row)
            self.select_stack.append(row)
        elif tag == "option" and self.select_stack:
            self.select_stack[-1]["options"].append({"value": a.get("value")})
        elif tag == "script" and a.get("src"):
            self.scripts.append(a.get("src"))
        elif tag == "a" and a.get("href"):
            self.links.append(a.get("href"))

    def handle_endtag(self, tag):
        if tag == "form":
            self.current_form = None
        elif tag == "select" and self.select_stack:
            self.select_stack.pop()

    def handle_data(self, data):
        if data and data.strip():
            self.text_parts.append(data.strip())


def fetch(session: requests.Session, url: str, params=None, referer: str | None = None):
    try:
        headers = {"Referer": referer} if referer else None
        r = session.get(url, params=params, timeout=60, allow_redirects=True, headers=headers)
        return r, None
    except requests.RequestException as ex:
        return None, f"{type(ex).__name__}: {ex}"


def parse_surface(html: str):
    p = SurfaceParser()
    p.feed(html or "")
    return p


def extract_count(text: str, label: str):
    compact = re.sub(r"\s+", " ", text or "")
    for pattern in [
        rf"{re.escape(label)}\s*\(?\s*([0-9,]+)\s*건\s*\)?",
        rf"{re.escape(label)}\s*\(?\s*([0-9,]+)\s*\)?",
    ]:
        m = re.search(pattern, compact)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except Exception:
                pass
    return None


def normalize_form(form: dict, base_url: str):
    action = form.get("action")
    absolute = urljoin(base_url, action) if action else base_url
    fields = form.get("fields") or []
    return {
        "action": action,
        "absolute_action": absolute,
        "method": form.get("method"),
        "id": form.get("id"),
        "name": form.get("name"),
        "fields": fields,
        "field_names": sorted({str(f.get("name")) for f in fields if f.get("name")}),
        "field_ids": sorted({str(f.get("id")) for f in fields if f.get("id")}),
    }


def interesting_link(href: str) -> bool:
    low = (href or "").lower()
    return any(k in low for k in ["search", "notice", "bbs", "board", "announce", "gosi", "gonggo", "category", "page"])


def main():
    print("=" * 78)
    print("GYEONGGI OFFICIAL RECORD SEARCH CONTRACT FORENSIC - S222")
    print("=" * 78)
    print("Purpose: qualify the official Gyeonggi search surface before UQQ700 replay")
    print("Positive control only; target no-hit inference is NOT performed")
    print("Immutable E-Gazette transition manifest prerequisite")
    print("Search hit != legal fact")
    print("Search no-hit != legal absence")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    transition = json.loads(TRANSITION_MANIFEST.read_text(encoding="utf-8"))
    gate_s = (
        transition.get("manifest_version") == 1
        and transition.get("manifest_type") == "IMMUTABLE_SOURCE_FAMILY_TRANSITION"
        and transition.get("target_name") == TARGET
        and transition.get("standard_code") == "UQQ700"
        and transition.get("resolution_type") == "HYBRID_SPATIAL_NOTICE"
        and transition.get("source_family") == "E_GAZETTE"
        and transition.get("classification") == "E_GAZETTE_BOUNDED_DESIGNATION_SEARCH_EXHAUSTED_NO_QUALIFIED_DESIGNATION_DOCUMENT"
        and transition.get("operational_source_family_closure") is True
        and transition.get("legal_absence_inference_allowed") is False
        and transition.get("site_false_inference_allowed") is False
        and transition.get("official_designation_identity_verified") is False
        and transition.get("current_validity_verified") is False
        and transition.get("site_spatial_inclusion_verified") is False
        and transition.get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not gate_s:
        raise AssertionError("S222 immutable E-Gazette transition manifest gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    root, root_error = fetch(session, ROOT)
    search_empty, search_empty_error = fetch(session, SEARCH_URL, params={"category": "", "kwd": ""}, referer=ROOT)
    positive, positive_error = fetch(session, SEARCH_URL, params={"category": "", "kwd": POSITIVE_CONTROL}, referer=ROOT)

    empty_html = search_empty.text if search_empty is not None else ""
    positive_html = positive.text if positive is not None else ""
    empty_surface = parse_surface(empty_html)
    positive_surface = parse_surface(positive_html)

    forms = [normalize_form(f, SEARCH_URL) for f in empty_surface.forms]
    search_forms = []
    for f in forms:
        names = set(f["field_names"])
        ids = set(f["field_ids"])
        action_low = (f.get("absolute_action") or "").lower()
        if "search" in action_low or "kwd" in names or "kwd" in ids or "category" in names:
            search_forms.append(f)

    all_field_names = sorted({name for f in forms for name in f["field_names"]})
    exact_kwd_field = "kwd" in all_field_names
    exact_category_field = "category" in all_field_names
    search_action_signal = any("/search.do" in (f.get("absolute_action") or "") for f in search_forms)

    scripts = sorted({urljoin(SEARCH_URL, s) for s in empty_surface.scripts if s})
    script_candidates = [s for s in scripts if any(k in s.lower() for k in ["search", "common", "main"])]

    link_hints = []
    for href in empty_surface.links + positive_surface.links:
        if interesting_link(href):
            absolute = urljoin(SEARCH_URL, href)
            if absolute not in link_hints:
                link_hints.append(absolute)
        if len(link_hints) >= 80:
            break

    positive_text = " ".join(positive_surface.text_parts)
    positive_term_visible = POSITIVE_CONTROL in positive_text
    official_record_label_visible = OFFICIAL_RECORD_LABEL in positive_text
    total_result_match = re.search(r"검색결과\s*[\"']?([0-9,]+)[\"']?건", positive_text)
    total_result_count = int(total_result_match.group(1).replace(",", "")) if total_result_match else None
    official_record_count = extract_count(positive_text, OFFICIAL_RECORD_LABEL)

    parsed_final = urlparse(positive.url) if positive is not None else None
    final_query = parse_qs(parsed_final.query) if parsed_final else {}
    positive_request_contract = bool(
        positive is not None
        and positive.status_code == 200
        and positive_term_visible
        and official_record_label_visible
    )

    if positive_request_contract and (exact_kwd_field or "kwd" in final_query):
        classification = "GYEONGGI_OFFICIAL_SEARCH_SURFACE_POSITIVE_CONTROL_QUALIFIED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_SEARCH_ENTRY_AND_POSITIVE_CONTROL_SURFACE_QUALIFIED"
        next_action = "BUILD_S223_EXACT_SEARCH_PARAMETER_AND_RESULT_IDENTITY_FORENSIC_BEFORE_UQQ700_TARGET_REPLAY"
    elif positive is not None and positive.status_code == 200:
        classification = "GYEONGGI_OFFICIAL_SEARCH_SURFACE_PARTIALLY_RECOVERED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_SEARCH_SURFACE_PARTIAL_CONTRACT_RECOVERY"
        next_action = "FORENSIC_EXTERNAL_JS_AND_CATEGORY_RESULT_NAVIGATION_WITHOUT_TARGET_NEGATIVE_INFERENCE"
    else:
        classification = "GYEONGGI_OFFICIAL_SEARCH_SURFACE_TECHNICAL_UNKNOWN"
        semantic = "GYEONGGI_OFFICIAL_RECORD_SEARCH_SURFACE_TECHNICAL_UNKNOWN"
        next_action = "RESOLVE_OFFICIAL_SEARCH_ENTRY_TRANSPORT_OR_RENDERING_BEFORE_TARGET_REPLAY"

    out = {
        "step": "STEP 17-21-C-16-8-T-135-S222",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "GYEONGGI_OFFICIAL_RECORD",
        "prerequisite": {
            "type": "IMMUTABLE_SOURCE_FAMILY_TRANSITION",
            "manifest": str(TRANSITION_MANIFEST),
            "gate": gate_s,
        },
        "entrypoints": {"root": ROOT, "search": SEARCH_URL},
        "requests": {
            "root": {"http": root.status_code if root is not None else None, "final_url": root.url if root is not None else None, "error": root_error},
            "search_empty": {"http": search_empty.status_code if search_empty is not None else None, "final_url": search_empty.url if search_empty is not None else None, "error": search_empty_error},
            "positive_control": {
                "term": POSITIVE_CONTROL,
                "params": {"category": "", "kwd": POSITIVE_CONTROL},
                "http": positive.status_code if positive is not None else None,
                "final_url": positive.url if positive is not None else None,
                "content_type": positive.headers.get("Content-Type", "") if positive is not None else "",
                "body_bytes": len(positive.content) if positive is not None else 0,
                "error": positive_error,
            },
        },
        "surface": {
            "form_count": len(forms),
            "search_form_count": len(search_forms),
            "forms": forms,
            "search_forms": search_forms,
            "all_field_names": all_field_names,
            "exact_kwd_field": exact_kwd_field,
            "exact_category_field": exact_category_field,
            "search_action_signal": search_action_signal,
            "script_count": len(scripts),
            "scripts": scripts,
            "script_candidates": script_candidates,
            "interesting_links": link_hints,
        },
        "positive_control": {
            "term_visible": positive_term_visible,
            "official_record_label": OFFICIAL_RECORD_LABEL,
            "official_record_label_visible": official_record_label_visible,
            "total_result_count": total_result_count,
            "official_record_count": official_record_count,
            "request_contract_signal": positive_request_contract,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "positive_control_only": True,
            "target_query_executed": False,
            "search_hit_equals_legal_fact": False,
            "search_no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "official_designation_identity_verified": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("TRANSITION MANIFEST:", TRANSITION_MANIFEST)
    print("TRANSITION MANIFEST GATE:", gate_s)
    print("ROOT HTTP:", out["requests"]["root"]["http"])
    print("SEARCH EMPTY HTTP:", out["requests"]["search_empty"]["http"])
    print("POSITIVE CONTROL HTTP:", out["requests"]["positive_control"]["http"])
    print("POSITIVE CONTROL FINAL URL:", out["requests"]["positive_control"]["final_url"])
    print("FORM COUNT:", len(forms))
    print("SEARCH FORM COUNT:", len(search_forms))
    print("ALL FIELD NAMES:", all_field_names)
    print("EXACT KWD FIELD:", exact_kwd_field)
    print("EXACT CATEGORY FIELD:", exact_category_field)
    print("SEARCH ACTION SIGNAL:", search_action_signal)
    print("SCRIPT COUNT:", len(scripts))
    print("SCRIPT CANDIDATES:", script_candidates[:20])
    print("POSITIVE TERM VISIBLE:", positive_term_visible)
    print("OFFICIAL RECORD LABEL VISIBLE:", official_record_label_visible)
    print("TOTAL RESULT COUNT:", total_result_count)
    print("OFFICIAL RECORD COUNT:", official_record_count)
    print("POSITIVE CONTROL REQUEST CONTRACT:", positive_request_contract)
    print("CLASSIFICATION:", classification)

    print("\nSEARCH FORMS")
    for i, form in enumerate(search_forms, 1):
        print(f"--- FORM {i} ---")
        print(json.dumps(form, ensure_ascii=False, indent=2))

    print("\nINTERESTING LINKS")
    for u in link_hints[:40]:
        print(u)

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Target query executed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "immutable E-Gazette transition gate": gate_s,
        "official root attempted": root is not None,
        "official search empty attempted": search_empty is not None,
        "positive control attempted": positive is not None,
        "positive control uses official gg.go.kr": bool(positive is not None and urlparse(positive.url).netloc.endswith("gg.go.kr")),
        "surface parsed": len(empty_html) > 0,
        "positive surface parsed": len(positive_html) > 0,
        "official-record category label checked": isinstance(official_record_label_visible, bool),
        "response classified": classification in {
            "GYEONGGI_OFFICIAL_SEARCH_SURFACE_POSITIVE_CONTROL_QUALIFIED",
            "GYEONGGI_OFFICIAL_SEARCH_SURFACE_PARTIALLY_RECOVERED",
            "GYEONGGI_OFFICIAL_SEARCH_SURFACE_TECHNICAL_UNKNOWN",
        },
        "positive control only": out["summary"]["positive_control_only"] is True,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "search hit not legal fact": out["summary"]["search_hit_equals_legal_fact"] is False,
        "search no-hit not legal absence": out["summary"]["search_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "SITE FALSE inference disabled": not out["summary"]["site_false_inference_allowed"],
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
        raise AssertionError("S222 Gyeonggi official record search contract forensic failed")


if __name__ == "__main__":
    main()
