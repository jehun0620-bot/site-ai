# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
INPUT = BASE / "law_data" / "output" / "development_density_management_area_national_law_seongnam_urban_planning_ordinance_history_positive_control_replay.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_national_law_seongnam_urban_planning_ordinance_historical_body_term_scan.json"
ENTRY = "https://www.law.go.kr/ordinSc.do"
DETAIL = "https://www.law.go.kr/ordinInfoP.do"
TARGET = "성남시 도시계획 조례"
CURRENT_SEQ = "2111431"
UA = "Mozilla/5.0"
MAX = 8 * 1024 * 1024
TERMS = ["개발밀도관리구역", "개발밀도 관리구역", "개발 밀도 관리 구역", "개발밀도"]


def dec(b):
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", errors="ignore"), "utf-8-ignore"


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", html.unescape(s or ""))).strip()


def compact(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", html.unescape(s or "")))


def read_body(r):
    b = bytearray()
    overflow = False
    try:
        for c in r.iter_content(65536):
            if not c:
                continue
            if len(b) + len(c) > MAX:
                overflow = True
                break
            b.extend(c)
    finally:
        r.close()
    t, e = dec(bytes(b))
    return bytes(b), t, e, overflow


class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []
        self.inputs = {}

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = {str(k).lower(): (v or "") for k, v in attrs}
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip += 1
        if tag == "input":
            key = a.get("name") or a.get("id")
            if key:
                self.inputs[key.lower()] = a.get("value", "")
        if tag in {"br", "p", "div", "li", "tr", "td", "th"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data:
            self.parts.append(data)


def parse(text):
    p = Parser()
    try:
        p.feed(text)
    except Exception:
        pass
    return norm(" ".join(p.parts)), p.inputs


def iv(inputs, *names):
    for name in names:
        v = norm(inputs.get(name.lower(), ""))
        if v:
            return v
    return None


def first(patterns, text):
    for pat in patterns:
        m = re.search(pat, text or "", re.I)
        if m:
            return norm(m.group(1))
    return None


def identity(raw, visible, inputs):
    seq = iv(inputs, "ordinSeq") or first([r"ordinSeq[\"']?\s*[:=]\s*[\"']?([0-9]+)", r"ordinSeq=([0-9]+)"], raw)
    oid = iv(inputs, "ordinId") or first([r"ordinId[\"']?\s*[:=]\s*[\"']?([0-9]+)"], raw)
    name = iv(inputs, "ordinNm", "vSct")
    if not name and compact(TARGET) in compact(visible):
        name = TARGET
    anc_yd = iv(inputs, "ancYd") or first([r"ancYd[\"']?\s*[:=]\s*[\"']?([0-9]{8})", r"공포일자\s*[:：]?\s*(20\d{2}[.\-/]\s*\d{1,2}[.\-/]\s*\d{1,2})"], raw + "\n" + visible)
    anc_no = iv(inputs, "ancNo") or first([r"ancNo[\"']?\s*[:=]\s*[\"']?([0-9]+)", r"(?:조례|규칙)?\s*제\s*([0-9]+)\s*호"], raw + "\n" + visible)
    effective = first([r"시행일(?:자)?\s*[:：]?\s*(20\d{2}[.\-/]\s*\d{1,2}[.\-/]\s*\d{1,2})"], visible)
    revision = next((x for x in ("제정", "전부개정", "일부개정", "폐지", "타법개정") if x in visible), None)
    return {
        "ordin_seq": seq,
        "ordin_id": oid,
        "ordin_name": name,
        "anc_yd": anc_yd,
        "anc_no": anc_no,
        "effective_date": effective,
        "revision_type": revision,
        "gubun": iv(inputs, "gubun"),
        "nw_yn": iv(inputs, "nwYn"),
    }


def article_count(text):
    return len(re.findall(r"제\s*\d+\s*조(?:의\s*\d+)?", text or ""))


def term_scan(text):
    c = compact(text)
    matched = [x for x in TERMS if compact(x) in c]
    return {
        "matched_terms": matched,
        "high_signal_uqq700_term_observed": compact("개발밀도관리구역") in c,
        "broad_development_density_term_observed": compact("개발밀도") in c,
    }


def fetch(session, seq, nw_yn):
    params = {
        "ordinSeq": seq,
        "chrClsCd": "010202",
        "gubun": "ELIS",
        "nwYn": nw_yn or "N",
        "conDatGubunCd": "1",
    }
    try:
        r = session.get(DETAIL, params=params, headers={"Referer": ENTRY}, timeout=60, allow_redirects=True, stream=True)
        status = r.status_code
        url = str(r.url)
        ctype = r.headers.get("Content-Type")
        b, t, e, ov = read_body(r)
        return {"params": params, "http": status, "url": url, "content_type": ctype, "body": b, "text": t, "encoding": e, "overflow": ov, "error": None}
    except requests.RequestException as ex:
        return {"params": params, "http": None, "url": None, "content_type": None, "body": b"", "text": "", "encoding": None, "overflow": False, "error": f"{type(ex).__name__}: {ex}"}


def main():
    print("=" * 72)
    print("NATIONAL LAW SEONGNAM URBAN PLANNING ORDINANCE HISTORICAL BODY TERM SCAN - S217")
    print("=" * 72)
    print("UQQ700 resolution: UNKNOWN")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")

    src = json.loads(INPUT.read_text(encoding="utf-8"))
    summary = src.get("summary") or {}
    seqs = [str(x) for x in src.get("unique_ordin_seqs", []) if str(x).strip()]
    rows = src.get("version_rows") or []
    if not summary.get("history_contract_qualified") or not summary.get("history_version_identity_qualified"):
        raise AssertionError("S216 history chain not qualified")
    if summary.get("technical_unknown_count") != 0:
        raise AssertionError("S216 contains technical unknown")
    if len(seqs) != 42 or len(set(seqs)) != 42 or CURRENT_SEQ not in seqs:
        raise AssertionError(f"Expected qualified 42-version chain, got {len(set(seqs))}")

    # Deliberately copy only seq/nwYn; S216 broad-context date/notice/revision hints are non-authoritative.
    row_by_seq = {str(r.get("ordin_seq")): {"nw_yn": r.get("nw_yn")} for r in rows if r.get("ordin_seq")}

    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    try:
        pre = s.get(ENTRY, timeout=30, allow_redirects=True)
        pre_http = pre.status_code
        pre.close()
        pre_error = None
    except requests.RequestException as ex:
        pre_http = None
        pre_error = f"{type(ex).__name__}: {ex}"

    results = []
    for i, seq in enumerate(seqs, 1):
        nw = row_by_seq.get(seq, {}).get("nw_yn") or "N"
        r = fetch(s, seq, nw)
        visible, inputs = parse(r["text"]) if r["text"] else ("", {})
        ident = identity(r["text"], visible, inputs) if r["text"] else {"ordin_seq": None, "ordin_id": None, "ordin_name": None, "anc_yd": None, "anc_no": None, "effective_date": None, "revision_type": None, "gubun": None, "nw_yn": None}
        articles = article_count(visible)
        reasons = []
        if r["error"] or r["http"] != 200 or r["overflow"]:
            reasons.append("transport_or_http_or_overflow")
        if str(ident.get("ordin_seq") or "") != seq:
            reasons.append("version_local_ordin_seq_not_verified")
        if compact(ident.get("ordin_name") or "") != compact(TARGET):
            reasons.append("version_local_ordinance_name_not_verified")
        if articles < 3:
            reasons.append("ordinance_body_article_signal_insufficient")
        scan = term_scan(visible)
        if reasons:
            cls = "TECHNICAL_UNKNOWN"
        elif scan["broad_development_density_term_observed"]:
            cls = "HIT"
        else:
            cls = "NO_HIT"
        item = {
            "scan_index": i,
            "requested_ordin_seq": seq,
            "requested_nw_yn": nw,
            "request": {"method": "GET", "url": DETAIL, "params": r["params"]},
            "response": {"http": r["http"], "final_url": r["url"], "byte_length": len(r["body"]), "encoding": r["encoding"], "overflow": r["overflow"], "error": r["error"], "content_type": r["content_type"]},
            "identity": ident,
            "body_evidence": {"visible_text_length": len(visible), "article_signal_count": articles},
            "term_scan": scan,
            "classification": cls,
            "technical_unknown_reasons": reasons,
            "legal_fact_promoted": False,
            "legal_absence_inferred": False,
            "site_fact_promoted": False,
        }
        results.append(item)
        print(f"[{i:02d}/42] seq={seq} http={r['http']} class={cls} ancYd={ident.get('anc_yd')} ancNo={ident.get('anc_no')} articles={articles} terms={scan['matched_terms']}")

    counts = {k: sum(x["classification"] == k for x in results) for k in ("HIT", "NO_HIT", "TECHNICAL_UNKNOWN")}
    high = [x for x in results if x["classification"] == "HIT" and x["term_scan"]["high_signal_uqq700_term_observed"]]
    broad = [x for x in results if x["classification"] == "HIT" and not x["term_scan"]["high_signal_uqq700_term_observed"]]
    if high:
        semantic = "ORDINANCE_HISTORY_HIGH_SIGNAL_TERM_ANCHOR_OBSERVED"
        next_action = "INSPECT_HIGH_SIGNAL_HIT_AND_ADJACENT_VERSION_CONTEXT;DO_NOT_PROMOTE_TO_DESIGNATION_FACT"
    elif broad:
        semantic = "ORDINANCE_HISTORY_BROAD_TERM_ANCHOR_OBSERVED"
        next_action = "INSPECT_BROAD_TERM_HIT_AND_ADJACENT_VERSION_CONTEXT;DO_NOT_PROMOTE_TO_DESIGNATION_FACT"
    elif counts["TECHNICAL_UNKNOWN"]:
        semantic = "ORDINANCE_HISTORY_BODY_SCAN_TECHNICALLY_INCOMPLETE"
        next_action = "RESOLVE_TECHNICAL_UNKNOWN_DETAIL_REPRESENTATIONS_BEFORE_SOURCE_FAMILY_PROGRESSION"
    else:
        semantic = "ORDINANCE_HISTORY_BODY_SCAN_NO_TERM_ANCHOR_OBSERVED"
        next_action = "KEEP_UQQ700_UNKNOWN;PROCEED_TO_NEXT_RANKED_OFFICIAL_SOURCE_FAMILY_WITHOUT_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-111-S217",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY",
        "source_role": "AUTHORITY_CONTEXT_TIMELINE_ANCHOR_ONLY",
        "input": {"s216_path": str(INPUT), "qualified_unique_ordin_seq_count": len(seqs), "s216_context_hints_authoritative": False},
        "preflight": {"http": pre_http, "error": pre_error},
        "results": results,
        "summary": {
            "version_count": len(results),
            "classification_counts": counts,
            "high_signal_hit_count": len(high),
            "broad_only_hit_count": len(broad),
            "technical_unknown_count": counts["TECHNICAL_UNKNOWN"],
            "semantic_state": semantic,
            "next_action": next_action,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "legal_absence": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    checks = {
        "preflight 200": pre_http == 200,
        "42 results emitted": len(results) == 42,
        "classification total 42": sum(counts.values()) == 42,
        "NO_HIT requires local identity/body": all(x["classification"] != "NO_HIT" or (str(x["identity"].get("ordin_seq") or "") == x["requested_ordin_seq"] and compact(x["identity"].get("ordin_name") or "") == compact(TARGET) and x["body_evidence"]["article_signal_count"] >= 3) for x in results),
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "legal absence false": out["summary"]["legal_absence"] is False,
        "SITE promotion blocked": not out["site_positive_allowed"] and not out["site_negative_allowed"],
        "runtime registration blocked": not out["runtime_registration_allowed"],
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nSUMMARY")
    print("Classification counts:", counts)
    print("High-signal hits:", len(high))
    print("Broad-only hits:", len(broad))
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)
    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S217 historical ordinance body/term scan validation failed")


if __name__ == "__main__":
    main()
