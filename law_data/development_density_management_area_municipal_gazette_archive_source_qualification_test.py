# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-18
Development Density Management Area
Municipal Gazette Archive Source Qualification

Qualify current Seongnam municipal gazette archive (bbs010308) as a competent-authority
historical source family. Do not execute UQQ700 query or promote any document.
"""
from __future__ import annotations

import json,re
from pathlib import Path
from typing import Any,Dict,List
from urllib.parse import urlparse
import requests

BASE_DIR=Path(__file__).resolve().parent.parent
OUT_DIR=BASE_DIR/"law_data"/"output";OUT_DIR.mkdir(parents=True,exist_ok=True)
OUT=OUT_DIR/"development_density_management_area_municipal_gazette_archive_source_qualification.json"

TARGET_NAME="개발밀도관리구역";STANDARD_CODE="UQQ700";RESOLUTION_TYPE="HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY="CURRENT_MUNICIPAL_GAZETTE_ARCHIVE";AUTHORITY="성남시장";REGIONS=["경기도 성남시"]
SEED_URL="https://www.seongnam.go.kr/bbs010308?curPage=1"
TIMEOUT=20;MAX_BYTES=12*1024*1024
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
TITLE_RE=re.compile(r"<title\b[^>]*>(.*?)</title>",re.I|re.S);TAG_RE=re.compile(r"<[^>]+>",re.S)
GAZETTE_NO_RE=re.compile(r"성남시보\s*제\s*\d+\s*호",re.I);DATE_RE=re.compile(r"(?:19|20)\d{2}[-./년\s]+\d{1,2}[-./월\s]+\d{1,2}")
DETAIL_RE=re.compile(r'''href\s*=\s*["'](?P<href>/bbs010308/\d+[^"']*)["']''',re.I)

def n(v:Any)->str:return re.sub(r"\s+"," ",str(v or "")).strip()
def host(u):
 try:return (urlparse(u).hostname or "").lower()
 except:return ""
def gov(h):return bool(h) and (h=="go.kr" or h.endswith(".go.kr"))
def fetch(session,url):
 out={"http_status":None,"final_url":"","text":"","error":"","bytes":0}
 try:
  with session.get(url,timeout=TIMEOUT,allow_redirects=True,stream=True) as r:
   out["http_status"]=r.status_code;out["final_url"]=str(r.url);chunks=[];total=0
   for c in r.iter_content(131072):
    if not c:continue
    total+=len(c)
    if total>MAX_BYTES:raise ValueError("response too large")
    chunks.append(c)
   raw=b"".join(chunks);out["bytes"]=len(raw)
   for enc in [r.encoding,"utf-8","cp949","euc-kr"]:
    if not enc:continue
    try:out["text"]=raw.decode(enc);break
    except:pass
   if not out["text"]:out["text"]=raw.decode("utf-8",errors="replace")
 except Exception as e:out["error"]=repr(e)
 return out

def main():
 print("="*60);print("DEVELOPMENT DENSITY MANAGEMENT AREA");print("MUNICIPAL GAZETTE ARCHIVE SOURCE QUALIFICATION");print("="*60)
 print("Target:",TARGET_NAME);print("Standard code:",STANDARD_CODE);print("Target query execution: DISABLED");print()
 s=requests.Session();s.headers.update({"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9"})
 r=fetch(s,SEED_URL);raw=r["text"] or "";plain=n(TAG_RE.sub(" ",raw));tm=TITLE_RE.search(raw);title=n(TAG_RE.sub(" ",tm.group(1))) if tm else ""
 gazettes=sorted(set(n(x.group(0)) for x in GAZETTE_NO_RE.finditer(plain)))
 detail_paths=sorted(set(n(x.group("href")) for x in DETAIL_RE.finditer(raw)))
 qualified=bool(r["http_status"]==200 and gov(host(r["final_url"])) and "성남 시보" in plain and gazettes)
 classification="QUALIFIED_CURRENT_MUNICIPAL_GAZETTE_ARCHIVE" if qualified else "REJECTED_CURRENT_MUNICIPAL_GAZETTE_ARCHIVE"
 next_pool=[]
 if qualified:
  next_pool=[{"source_family":SOURCE_FAMILY,"authority":AUTHORITY,"regions":REGIONS,"url":r["final_url"],"title":title,"gazette_samples":gazettes[:10],"detail_path_samples":detail_paths[:10],"requires_pagination_detail_contract_recovery":True,"target_query_executed":False,"document_candidate_generated":False,"verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False}]
 data={"step":"STEP 17-21-C-16-8-T-18 Municipal Gazette Archive Source Qualification","target":{"name":TARGET_NAME,"standard_code":STANDARD_CODE},"resolution_policy":{"resolution_type":RESOLUTION_TYPE,"negative_evidence_allowed":False,"source_failure_site_status":"UNKNOWN"},"source":{"source_family":SOURCE_FAMILY,"authority":AUTHORITY,"regions":REGIONS,"seed_url":SEED_URL,"http_status":r["http_status"],"final_url":r["final_url"],"title":title,"gazette_samples":gazettes[:20],"detail_path_samples":detail_paths[:20],"qualified":qualified,"classification":classification},"next_stage_source_pool":next_pool,"resolution":"MUNICIPAL_GAZETTE_ARCHIVE_SOURCE_QUALIFIED" if qualified else "MUNICIPAL_GAZETTE_ARCHIVE_SOURCE_NOT_QUALIFIED","verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False,"final_positive_promotion_allowed":False}
 OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
 vals={"HTTP 200":r["http_status"]==200,"official go.kr host":gov(host(r["final_url"])),"gazette identity present":bool(gazettes),"target query disabled":True,"document promotion disabled":True,"output written":OUT.exists() and OUT.stat().st_size>0}
 print("HTTP:",r["http_status"]);print("Final URL:",r["final_url"]);print("Title:",title);print("Gazette samples:",gazettes[:5]);print("Detail path samples:",detail_paths[:5]);print("Qualified:",qualified);print("Resolution:",classification);print("Output:",OUT);print();print("VALIDATION")
 for k,v in vals.items():print(f"{k}: {v}")
 print("all_pass:",all(vals.values()))
 if not all(vals.values()):raise AssertionError("municipal gazette archive source qualification failed")
if __name__=="__main__":main()
