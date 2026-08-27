# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-16-S8-S1
Development Density Management Area
Historical Row Coverage Expansion

S8에서 direct UQQ700 row candidate가 0건이었으나 notice archive의 effective range는
1..199이고 S8은 bounded sparse schedule만 순회했다. 이 단계는 S8에서 이미 조회한 page를
제외하고 미조회 page를 추가로 제한 순회하여 coverage gap을 줄인다.

원칙:
- S8에서 검증된 interaction parser 규칙을 그대로 사용
- S7-S3 validated family gate 유지
- detail request 실행 금지
- row-local direct '개발밀도관리구역' identity만 candidate
- no candidate != SITE FALSE
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
S8_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_competent_authority_historical_row_identity_recovery.json"
T15S2_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_competent_authority_historical_boundary_semantic_hardening.json"
OUT_DIR = BASE_DIR / "law_data" / "output"; OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "development_density_management_area_competent_authority_historical_row_coverage_expansion.json"

TARGET_NAME="개발밀도관리구역"; STANDARD_CODE="UQQ700"; RESOLUTION_TYPE="HYBRID_SPATIAL_NOTICE"
FAMILY_NOTICE="CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"; FAMILY_URBAN="CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"
FUNCTION_BY_FAMILY={FAMILY_NOTICE:"f_view", FAMILY_URBAN:"fn_move_form"}
MAX_TOTAL_REQUESTS=48; MAX_REQUESTS_PER_CONTRACT=24; TIMEOUT=20; MAX_RESPONSE_BYTES=12*1024*1024
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
TR_RE=re.compile(r"<tr\b[^>]*>(.*?)</tr>",re.I|re.S); TAG_RE=re.compile(r"<[^>]+>",re.S); SS_RE=re.compile(r"<(?:script|style)\b.*?</(?:script|style)>",re.I|re.S); COM_RE=re.compile(r"<!--.*?-->",re.S)
TARGET_RE=re.compile(r"개발\s*밀도\s*관리\s*구역",re.I)
DATE_RE=re.compile(r"(?<!\d)((?:19|20)\d{2})[.\-/년\s]+(0?[1-9]|1[0-2])[.\-/월\s]+(0?[1-9]|[12]\d|3[01])(?:일)?(?!\d)")
NOTICE_RE=re.compile(r"(?:고시|공고)\s*(?:제)?\s*\d{4}\s*[-–]\s*\d+\s*호?",re.I)

def norm(v:Any)->str:return re.sub(r"\s+"," ",str(v or "")).strip()
def uniq(vals:Iterable[Any])->List[str]:
    out=[]; seen=set()
    for v in vals:
        t=norm(v)
        if t and t not in seen: seen.add(t); out.append(t)
    return out

def strip_html(raw:str)->str:
    x=COM_RE.sub(" ",raw or ""); x=SS_RE.sub(" ",x); x=TAG_RE.sub(" ",x); return norm(html.unescape(x))
def canon(url:str)->str:
    p=urlparse(norm(url)); params=sorted(parse_qsl(p.query,keep_blank_values=True)); return urlunparse(((p.scheme or "https").lower(),(p.hostname or "").lower(),re.sub(r"/{2,}","/",p.path or "/"),"",urlencode(params),""))
def host(url:str)->str:
    try:return (urlparse(url).hostname or "").lower()
    except:return ""
def gov(h:str)->bool:return bool(h) and (h=="go.kr" or h.endswith(".go.kr"))
def fetch(session,url):
    out={"http_status":None,"final_url":"","text":"","error":""}
    try:
        with session.get(url,timeout=TIMEOUT,allow_redirects=True,stream=True) as r:
            out["http_status"]=r.status_code; out["final_url"]=canon(str(r.url)); chunks=[]; total=0
            for c in r.iter_content(131072):
                if not c: continue
                total+=len(c)
                if total>MAX_RESPONSE_BYTES: raise ValueError("response too large")
                chunks.append(c)
            raw=b"".join(chunks)
            for enc in uniq([r.encoding,"utf-8","cp949","euc-kr"]):
                try: out["text"]=raw.decode(enc); break
                except: pass
            if not out["text"]: out["text"]=raw.decode("utf-8",errors="replace")
    except Exception as e: out["error"]=repr(e)
    return out

def build_url(base,key,page):
    p=urlparse(base); q=dict(parse_qsl(p.query,keep_blank_values=True)); q[key]=str(page); return canon(urlunparse((p.scheme,p.netloc,p.path,"",urlencode(q),"")))
def parse_rows(raw,family,page_url,page):
    fn=FUNCTION_BY_FAMILY[family]; call=re.compile(rf"{re.escape(fn)}\s*\(\s*['\"]?(\d+)['\"]?\s*\)",re.I); rows=[]
    for i,m in enumerate(TR_RE.finditer(raw or ""),1):
        txt=strip_html(m.group(1)); args=uniq(x.group(1) for x in call.finditer(m.group(1)))
        for arg in args:
            mt=TARGET_RE.search(txt)
            rows.append({"source_family":family,"page_number":page,"page_url":page_url,"tr_index":i,"function":fn,"argument":arg,"row_text":txt[:5000],"notice_numbers":uniq(x.group(0) for x in NOTICE_RE.finditer(txt)),"dates":[f"{int(y):04d}-{int(mm):02d}-{int(d):02d}" for y,mm,d in DATE_RE.findall(txt)],"target_identity_direct":bool(mt),"document_candidate_only":bool(mt),"verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False})
    return rows

def main():
    print("="*60); print("DEVELOPMENT DENSITY MANAGEMENT AREA"); print("HISTORICAL ROW COVERAGE EXPANSION"); print("="*60)
    if not S8_PATH.exists() or not T15S2_PATH.exists(): raise FileNotFoundError("input missing")
    s8=json.loads(S8_PATH.read_text(encoding="utf-8")); t15=json.loads(T15S2_PATH.read_text(encoding="utf-8"))
    prior_pages={(norm(x.get("source_family")),int(x.get("page_number") or 0)) for x in s8.get("page_results",[]) if isinstance(x,dict)}
    contracts=[]
    for x in t15.get("next_stage_boundary_pool",[]):
        if not isinstance(x,dict): continue
        fam=norm(x.get("source_family")); base=canon(x.get("primary_base_url") or x.get("base_url") or ""); key=norm(x.get("pagination_key"))
        if fam not in FUNCTION_BY_FAMILY or not base or not key: continue
        contracts.append({"source_family":fam,"base_url":base,"pagination_key":key,"lower":int(x.get("effective_lower_page") or 1),"upper":int(x.get("effective_upper_page") or 0)})
    session=requests.Session(); session.headers.update({"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9"})
    req=0; success=0; errs=0; rows=[]; page_results=[]
    for ci,c in enumerate(contracts,1):
        missing=[p for p in range(c["lower"],c["upper"]+1) if (c["source_family"],p) not in prior_pages]
        selected=missing[:MAX_REQUESTS_PER_CONTRACT]
        print("-"*60); print("CONTRACT",ci); print("Family:",c["source_family"]); print("Missing page count:",len(missing)); print("Selected pages:",selected)
        for p in selected:
            if req>=MAX_TOTAL_REQUESTS: break
            url=build_url(c["base_url"],c["pagination_key"],p); r=fetch(session,url); req+=1
            if isinstance(r["http_status"],int) and 200<=r["http_status"]<300: success+=1
            if r["error"]: errs+=1
            rs=parse_rows(r["text"],c["source_family"],r["final_url"] or url,p) if r["http_status"]==200 else []
            rows.extend(rs); page_results.append({"source_family":c["source_family"],"page_number":p,"page_url":url,"http_status":r["http_status"],"interaction_row_count":len(rs)})
    cmap={}
    for x in rows:
        k=(x["source_family"],x["argument"])
        if k not in cmap: cmap[k]=x
        elif x.get("target_identity_direct"): cmap[k]["target_identity_direct"]=True; cmap[k]["document_candidate_only"]=True
    canonical=list(cmap.values()); candidates=[x for x in canonical if x.get("target_identity_direct")]
    remaining=[]
    for c in contracts:
        covered={p for fam,p in prior_pages if fam==c["source_family"]} | {int(x["page_number"]) for x in page_results if x["source_family"]==c["source_family"]}
        missing=[p for p in range(c["lower"],c["upper"]+1) if p not in covered]
        remaining.append({"source_family":c["source_family"],"remaining_page_count":len(missing),"remaining_pages":missing[:200]})
    out={"step":"STEP 17-21-C-16-8-T-16-S8-S1 Historical Row Coverage Expansion","target":{"name":TARGET_NAME,"standard_code":STANDARD_CODE},"summary":{"request_count":req,"http_success_count":success,"transport_error_count":errs,"raw_interaction_row_count":len(rows),"canonical_row_count":len(canonical),"uqq700_candidate_count":len(candidates),"remaining_contracts":remaining},"page_results":page_results,"canonical_rows":canonical,"uqq700_candidates":candidates,"next_stage_document_candidate_pool":candidates,"resolution":"COMPETENT_AUTHORITY_COVERAGE_EXPANSION_UQQ700_CANDIDATE_RECOVERED" if candidates else "COMPETENT_AUTHORITY_COVERAGE_EXPANSION_NO_UQQ700_ROW","verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False}
    OUT_PATH.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    vals={"inputs exist":S8_PATH.exists() and T15S2_PATH.exists(),"request budget respected":req<=MAX_TOTAL_REQUESTS,"page hosts go.kr":all(gov(host(x["page_url"])) for x in page_results),"unsafe promotion blocked":all(not x.get("verified_positive") and not x.get("runtime_registration_allowed") and not x.get("site_positive_allowed") and not x.get("site_negative_allowed") for x in canonical),"output written":OUT_PATH.exists() and OUT_PATH.stat().st_size>0}
    print(); print("="*60); print("RESULT"); print("="*60); print("Request count:",req); print("Canonical rows:",len(canonical)); print("UQQ700 candidates:",len(candidates)); print("Remaining coverage:",remaining); print("Output:",OUT_PATH); print(); print("VALIDATION")
    for k,v in vals.items(): print(f"{k}: {v}")
    print("all_pass:",all(vals.values()))
    if not all(vals.values()): raise AssertionError("coverage expansion regression failed")
if __name__=="__main__": main()
