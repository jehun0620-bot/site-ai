# -*- coding: utf-8 -*-
"""S95: validate a concrete pre-2010 gazette detail identity and probe deeper list pages.

S94 proved that official /bbs010308 list pages 133-135 contain concrete 2007 gazette
rows. This stage performs one bounded detail request for a known 2007 row to validate
list->detail identity, and probes only pages 140/150/160 to see whether the official
list continues to earlier years.

No UQQ700 target-term search, attachment download, state mutation, negative evidence,
SITE/runtime promotion, or legal absence inference is allowed.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlencode, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "development_density_management_area_seongnam_legacy_gazette_pre2010_detail_and_deeper_boundary.json"

LIST_URL = "https://www.seongnam.go.kr/bbs010308"
HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_REQ = 6
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
KNOWN_2007_GAZETTE = 769
KNOWN_2007_PSTSN = "28918"
PROBE_PAGES = [140, 150, 160]

TR_RE = re.compile(r"<tr\b[^>]*>(?P<b>.*?)</tr>", re.I | re.S)
ANCHOR_RE = re.compile(r"<a\b(?P<a>[^>]*)>(?P<b>.*?)</a>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
TAG_RE = re.compile(r"<[^>]+>", re.S)
GAZ_RE = re.compile(r"성남시보\s*제\s*(\d+)\s*호", re.I)
CALL_RE = re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")


def attrs(raw: str) -> dict[str, str]:
    out = {}
    for m in ATTR_RE.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def rr(r: requests.Response) -> dict:
    return {"http": r.status_code, "url": str(r.url), "host": (urlparse(str(r.url)).hostname or "").lower(), "text": r.text, "bytes": len(r.content)}


def get(session, url, counter):
    if counter[0] >= MAX_REQ: raise AssertionError("request budget exceeded")
    counter[0] += 1
    return rr(session.get(url, timeout=TIMEOUT, allow_redirects=True))


def list_url(page: int) -> str:
    params = {
        "curPage": str(page),
        "cntPerPage": "10",
        "pstSn": "0",
        "srchText": "",
        "srchBgngYmd": "",
        "srchEndYmd": "",
        "sortType": "1",
        "srchTypeCd": "pstTtl",
        "srchDtType": "",
    }
    return LIST_URL + "?" + urlencode(params)


def parse_rows(text: str) -> list[dict]:
    out=[]; seen=set()
    for tm in TR_RE.finditer(text or ""):
        body=tm.group("b"); row_text=clean(body); gaz=None; pst=None
        for am in ANCHOR_RE.finditer(body):
            a=attrs(am.group("a")); label=clean(am.group("b")); gm=GAZ_RE.search(label)
            if not gm: continue
            mm=CALL_RE.search(a.get("href","")+" "+a.get("onclick",""))
            if not mm: continue
            gaz=int(gm.group(1)); pst=mm.group(1); break
        if gaz is None or pst is None: continue
        key=(gaz,pst)
        if key in seen: continue
        seen.add(key)
        years=sorted({int(y) for y in YEAR_RE.findall(row_text)})
        out.append({"gazette_number":gaz,"pstSn":pst,"years":years,"row_text":row_text[:1200]})
    return out


def main():
    print("="*60)
    print("SEONGNAM LEGACY GAZETTE PRE-2010 DETAIL / DEEPER BOUNDARY - S95")
    print("="*60)
    print("Target-term search: DISABLED")
    print("Attachment download: DISABLED")
    print("Negative evidence: DISABLED")

    s=requests.Session(); s.headers.update({"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9"}); c=[0]

    detail_url=f"{LIST_URL}/{KNOWN_2007_PSTSN}"
    detail=get(s,detail_url,c)
    detail_text=clean(detail["text"])
    detail_gazette_match=bool(re.search(rf"성남시보\s*제\s*{KNOWN_2007_GAZETTE}\s*호",detail_text,re.I))
    detail_pstsn_path=urlparse(detail["url"]).path.endswith("/"+KNOWN_2007_PSTSN)
    detail_years=sorted({int(y) for y in YEAR_RE.findall(detail_text)})
    print("DETAIL:",{"http":detail["http"],"official":detail["host"]==HOST,"url":detail["url"],"gazette_identity_match":detail_gazette_match,"pstSn_path_match":detail_pstsn_path,"observed_years":detail_years[:20]})

    pages=[]
    for page in PROBE_PAGES:
        r=get(s,list_url(page),c); rows=parse_rows(r["text"]); years=sorted({y for x in rows for y in x["years"]})
        item={"page":page,"http":r["http"],"official":r["host"]==HOST,"row_count":len(rows),"identities":[(x["gazette_number"],x["pstSn"]) for x in rows],"observed_years":years,"rows":rows}
        pages.append(item); print("PAGE:",{k:item[k] for k in ["page","http","official","row_count","identities","observed_years"]})

    oldest_observed=min([y for p in pages for y in p["observed_years"]]+([min(detail_years)] if detail_years else [9999]))
    any_pre2007=any(y<2007 for p in pages for y in p["observed_years"])
    any_nonempty=any(p["row_count"]>0 for p in pages)

    summary={
        "request_count":c[0],
        "known_2007_detail_identity_validated":detail["http"]==200 and detail["host"]==HOST and detail_gazette_match and detail_pstsn_path,
        "pre2010_source_reachability_verified":detail["http"]==200 and detail["host"]==HOST and detail_gazette_match,
        "deeper_pages_any_nonempty":any_nonempty,
        "oldest_observed_year_across_probe":oldest_observed if oldest_observed!=9999 else None,
        "pre2007_year_observed":any_pre2007,
        "semantic_state":"PRE2010_DETAIL_IDENTITY_VERIFIED_WITH_DEEPER_LIST_REACH" if any_nonempty else "PRE2010_DETAIL_IDENTITY_VERIFIED_DEEPER_BOUNDARY_UNRESOLVED",
        "negative_evidence_allowed":False,
        "uqq700_final_resolution":"UNKNOWN",
    }

    out={
        "step":"STEP 17-21-C-16-8-T-35-S95",
        "target_name":"개발밀도관리구역",
        "standard_code":"UQQ700",
        "resolution_type":"HYBRID_SPATIAL_NOTICE",
        "source_family":"LEGACY_LOCAL_GAZETTE",
        "known_2007_detail":{"gazette_number":KNOWN_2007_GAZETTE,"pstSn":KNOWN_2007_PSTSN,"http":detail["http"],"final_url":detail["url"],"official":detail["host"]==HOST,"gazette_identity_match":detail_gazette_match,"pstSn_path_match":detail_pstsn_path,"observed_years":detail_years[:100]},
        "deeper_page_probes":pages,
        "summary":summary,
        "target_term_search_executed":False,
        "attachment_body_download_executed":False,
        "state_mutation_executed":False,
        "negative_evidence_allowed":False,
        "site_positive_allowed":False,
        "site_negative_allowed":False,
        "runtime_registration_allowed":False,
        "final_positive_promotion_allowed":False,
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")

    vals={
        "detail transport official":detail["http"]==200 and detail["host"]==HOST,
        "detail identity matched":detail_gazette_match and detail_pstsn_path,
        "all page transport official":all(p["http"]==200 and p["official"] for p in pages),
        "request budget respected":c[0]<=MAX_REQ,
        "target-term search disabled":not out["target_term_search_executed"],
        "negative evidence disabled":not out["negative_evidence_allowed"],
        "unsafe promotion leakage zero":not any(out[k] for k in ["site_positive_allowed","site_negative_allowed","runtime_registration_allowed","final_positive_promotion_allowed"]),
        "output written":OUT.exists() and OUT.stat().st_size>0,
    }
    print("\nSUMMARY"); [print(f"{k}: {v}") for k,v in summary.items()]; print("Output:",OUT)
    print("\nVALIDATION"); [print(f"{k}: {v}") for k,v in vals.items()]; print("all_pass:",all(vals.values()))
    if not all(vals.values()): raise AssertionError("S95 pre-2010 detail/deeper boundary validation failed")


if __name__=="__main__": main()
