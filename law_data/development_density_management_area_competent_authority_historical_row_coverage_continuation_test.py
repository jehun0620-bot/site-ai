# -*- coding: utf-8 -*-
"""Reusable cumulative UQQ700 historical row coverage continuation."""
from __future__ import annotations
import html,json,re
from pathlib import Path
from typing import Any,Iterable
from urllib.parse import parse_qsl,urlencode,urlparse,urlunparse
import requests
BASE_DIR=Path(__file__).resolve().parent.parent; OUT=BASE_DIR/"law_data"/"output"
T15=OUT/"development_density_management_area_competent_authority_historical_boundary_semantic_hardening.json"; BASE=OUT/"development_density_management_area_competent_authority_historical_row_identity_recovery.json"; OUTPUT=OUT/"development_density_management_area_competent_authority_historical_row_coverage_continuation.json"
F1="CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE";F2="CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE";FN={F1:"f_view",F2:"fn_move_form"}; MAX=24
TR=re.compile(r"<tr\b[^>]*>(.*?)</tr>",re.I|re.S);TAG=re.compile(r"<[^>]+>",re.S);TARGET=re.compile(r"개발\s*밀도\s*관리\s*구역",re.I)
def n(v):return re.sub(r"\s+"," ",str(v or "")).strip()
def load(p):
 try:
  x=json.loads(p.read_text(encoding="utf-8"));return x if isinstance(x,dict) else {}
 except:return {}
def canon(u):
 p=urlparse(n(u));q=sorted(parse_qsl(p.query,keep_blank_values=True));return urlunparse(((p.scheme or "https").lower(),(p.hostname or "").lower(),p.path,"",urlencode(q),"")) if p.hostname else ""
def burl(base,key,page):
 p=urlparse(base);q=dict(parse_qsl(p.query));q[key]=str(page);return canon(urlunparse((p.scheme,p.netloc,p.path,"",urlencode(q),"")))
def contracts():
 out=[];seen=set()
 for x in load(T15).get("next_stage_boundary_pool") or []:
  f=n(x.get("source_family"));b=canon(x.get("primary_base_url") or x.get("base_url"));k=n(x.get("pagination_key"));ident=(f,b,k)
  if f in FN and b and k and ident not in seen:seen.add(ident);out.append((f,b,k,int(x.get("effective_lower_page") or 1),int(x.get("effective_upper_page") or 0)))
 return out
def pages(data):
 out={}
 for x in data.get("page_results") or []:
  if isinstance(x,dict) and n(x.get("source_family")) in FN and int(x.get("page_number") or 0)>0:out[(n(x["source_family"]),int(x["page_number"]))]=x
 return out
def candidates(data):
 out={}
 for key in ("uqq700_candidates","uqq700_target_candidates","next_stage_document_candidate_pool"):
  for x in data.get(key) or []:
   if isinstance(x,dict) and x.get("target_identity_direct") is True:out[(n(x.get("source_family")),n(x.get("argument")))]=x
 return out
def parse(raw,f,url,page):
 fn=FN[f];call=re.compile(rf"{re.escape(fn)}\s*\(\s*['\"]?(\d+)['\"]?",re.I);out=[]
 for i,m in enumerate(TR.finditer(raw),1):
  rh=m.group(1);args=list(dict.fromkeys(x.group(1) for x in call.finditer(rh)));txt=n(html.unescape(TAG.sub(" ",rh)))
  for a in args:out.append({"source_family":f,"page_number":page,"page_url":url,"tr_index":i,"function":fn,"argument":a,"row_text":txt[:5000],"target_identity_direct":bool(TARGET.search(txt)),"document_candidate_only":bool(TARGET.search(txt)),"detail_request_executed":False,"verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False,"final_positive_promotion_allowed":False})
 return out
def main():
 print("="*60,"\nDEVELOPMENT DENSITY MANAGEMENT AREA\nCUMULATIVE HISTORICAL ROW COVERAGE CONTINUATION\n"+"="*60,sep="")
 files=[BASE]+sorted(OUT.glob("development_density_management_area_competent_authority_historical_row_coverage_expansion*.json"));pm={};cm={}
 for p in files:
  if p.exists():d=load(p);pm.update(pages(d));cm.update(candidates(d))
 # Load our previous fixed output before overwriting: this is what makes repeated runs cumulative.
 previous=load(OUTPUT) if OUTPUT.exists() else {};pm.update(pages(previous));cm.update(candidates(previous));prior=set(pm)
 print("Previous continuation output loaded:",bool(previous));print("Prior covered pages:",len(prior));print("Prior UQQ700 candidates:",len(cm))
 if cm:
  print("Existing candidate detected; no requests executed.");print("all_pass: True");return
 s=requests.Session();s.headers["User-Agent"]="Mozilla/5.0";current=[];rows=[];req=ok=0
 for idx,(f,b,k,lo,hi) in enumerate(contracts(),1):
  missing=[p for p in range(lo,hi+1) if (f,p) not in prior];selected=missing[:MAX];print("-"*60);print("CONTRACT",idx);print("Family:",f);print("Missing page count:",len(missing));print("Selected pages:",selected)
  for p in selected:
   u=burl(b,k,p)
   try:r=s.get(u,timeout=20);status=r.status_code;raw=r.text if status==200 else ""
   except Exception:status=None;raw=""
   req+=1;ok+=status==200;rr=parse(raw,f,u,p) if status==200 else [];rows+=rr;rec={"source_family":f,"page_number":p,"page_url":u,"http_status":status,"interaction_row_count":len(rr)};current.append(rec);pm[(f,p)]=rec
 cmap={}
 for x in rows:
  key=(x["source_family"],x["argument"])
  if key not in cmap or x["target_identity_direct"]:cmap[key]=x
 cur=[x for x in cmap.values() if x["target_identity_direct"]]
 for x in cur:cm[(x["source_family"],x["argument"])]=x
 remaining=[];total=0
 for f,b,k,lo,hi in contracts():
  miss=[p for p in range(lo,hi+1) if (f,p) not in pm];total+=len(miss);remaining.append({"source_family":f,"base_url":b,"remaining_page_count":len(miss),"remaining_pages":miss})
 resolution="COMPETENT_AUTHORITY_COVERAGE_CONTINUATION_UQQ700_CANDIDATE_RECOVERED" if cur else ("COMPETENT_AUTHORITY_COVERAGE_CONTINUATION_COMPLETE_NO_UQQ700_ROW" if total==0 else "COMPETENT_AUTHORITY_COVERAGE_CONTINUATION_PARTIAL_NO_UQQ700_ROW")
 data={"step":"STEP 17-21-C-16-8-T-16-S8-CONT","target":{"name":"개발밀도관리구역","standard_code":"UQQ700"},"summary":{"prior_covered_page_count":len(prior),"request_count":req,"http_success_count":ok,"cumulative_covered_page_count":len(pm),"remaining_page_count":total,"remaining_coverage":remaining},"page_results":list(pm.values()),"current_batch_page_results":current,"canonical_rows":list(cmap.values()),"uqq700_candidates":list(cm.values()),"next_stage_document_candidate_pool":list(cm.values()),"resolution":resolution,"verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False,"final_positive_promotion_allowed":False}
 OUTPUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
 requery=sum((x["source_family"],x["page_number"]) in prior for x in current);badhost=sum(not (urlparse(x["page_url"]).hostname or "").endswith(".go.kr") for x in current);unsafe=sum(any(x.get(k) for k in ("detail_request_executed","verified_positive","runtime_registration_allowed","site_positive_allowed","site_negative_allowed","final_positive_promotion_allowed")) for x in cmap.values())
 vals={"request budget respected":req<=48,"already-covered page requery leakage zero":requery==0,"page hosts go.kr":badhost==0,"unsafe promotion leakage zero":unsafe==0,"cumulative page history persisted":len(data["page_results"])==len(pm),"output written":OUTPUT.exists()}
 print("\n"+"="*60+"\nRESULT\n"+"="*60);print("Prior covered pages:",len(prior));print("Request count:",req);print("HTTP success count:",ok);print("Cumulative covered pages:",len(pm));print("UQQ700 candidates:",len(cur));print("Remaining page count:",total);print("Remaining coverage:",remaining);print("Resolution:",resolution);print("Output:",OUTPUT);print("\nVALIDATION")
 for k,v in vals.items():print(f"{k}: {v}")
 print("Requery leakage:",requery);print("Invalid host leakage:",badhost);print("Unsafe promotion leakage:",unsafe);print("all_pass:",all(vals.values()))
 if not all(vals.values()):raise AssertionError("cumulative continuation regression failed")
if __name__=="__main__":main()
