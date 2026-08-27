# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-20
Development Density Management Area
Municipal Gazette Exact Serialization Contract Recovery

Recover the exact fn_move_form serialization contract from the live Seongnam gazette page.
No detail request is executed. No UQQ700 target query or document promotion is allowed.
"""
from __future__ import annotations
import json,re,html
from pathlib import Path
from typing import Any,Dict,List
from urllib.parse import urljoin,urlparse
import requests

BASE_DIR=Path(__file__).resolve().parent.parent
OUT_DIR=BASE_DIR/"law_data"/"output";OUT_DIR.mkdir(parents=True,exist_ok=True)
T19=OUT_DIR/"development_density_management_area_municipal_gazette_interaction_contract_recovery.json"
OUT=OUT_DIR/"development_density_management_area_municipal_gazette_exact_serialization_contract_recovery.json"
TARGET_NAME="개발밀도관리구역";STANDARD_CODE="UQQ700";RESOLUTION_TYPE="HYBRID_SPATIAL_NOTICE"
TIMEOUT=20;MAX_BYTES=12*1024*1024;UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
SCRIPT_RE=re.compile(r"<script\b[^>]*>(.*?)</script>",re.I|re.S)
FORM_RE=re.compile(r"<form\b([^>]*)>(.*?)</form>",re.I|re.S)
INPUT_RE=re.compile(r"<input\b([^>]*)>",re.I|re.S)
ATTR_RE=re.compile(r'''([:\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))''',re.I)
FUNC_RE=re.compile(r"function\s+fn_move_form\s*\(([^)]*)\)\s*\{(.*?)\}",re.S)
ACTION_ASSIGN_RE=re.compile(r'''attr\s*\(\s*["']action["']\s*,\s*([^\)]+)\)''',re.I)
VALUE_ASSIGN_RE=re.compile(r'''(?:#|name=['\"]?)([A-Za-z0-9_]+)[^\n]{0,100}?val\s*\(\s*([A-Za-z0-9_]+)\s*\)''',re.I)
PATH_LITERAL_RE=re.compile(r'''["'](/[^"']+?/)["']''')

def n(v:Any)->str:return re.sub(r"\s+"," ",str(v or "")).strip()
def attrs(raw:str)->Dict[str,str]:
 out={}
 for m in ATTR_RE.finditer(raw or ""):out[m.group(1).lower()]=html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
 return out
def host(u:str)->str:
 try:return (urlparse(u).hostname or "").lower()
 except:return ""
def gov(h:str)->bool:return bool(h) and (h=="go.kr" or h.endswith(".go.kr"))
def fetch(session,url):
 out={"http_status":None,"final_url":"","text":"","error":""}
 try:
  with session.get(url,timeout=TIMEOUT,allow_redirects=True,stream=True) as r:
   out["http_status"]=r.status_code;out["final_url"]=str(r.url);chunks=[];total=0
   for c in r.iter_content(131072):
    if not c:continue
    total+=len(c)
    if total>MAX_BYTES:raise ValueError("response too large")
    chunks.append(c)
   raw=b"".join(chunks)
   for enc in [r.encoding,"utf-8","cp949","euc-kr"]:
    if not enc:continue
    try:out["text"]=raw.decode(enc);break
    except:pass
   if not out["text"]:out["text"]=raw.decode("utf-8",errors="replace")
 except Exception as e:out["error"]=repr(e)
 return out

def main():
 print("="*60);print("DEVELOPMENT DENSITY MANAGEMENT AREA");print("MUNICIPAL GAZETTE EXACT SERIALIZATION CONTRACT RECOVERY");print("="*60)
 print("Target:",TARGET_NAME);print("Standard code:",STANDARD_CODE);print("Detail request execution: DISABLED");print("Target query execution: DISABLED");print()
 if not T19.exists():raise FileNotFoundError(T19)
 data=json.loads(T19.read_text(encoding="utf-8"));pool=data.get("next_stage_contract_pool") or []
 if not pool:raise AssertionError("T-19 contract pool missing")
 source_url=n(pool[0].get("source_url"))
 s=requests.Session();s.headers.update({"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9"})
 r=fetch(s,source_url);raw=r["text"] or "";final_url=r["final_url"] or source_url
 function_defs=[]
 for sm in SCRIPT_RE.finditer(raw):
  fm=FUNC_RE.search(sm.group(1))
  if fm:
   args=[n(x) for x in fm.group(1).split(",") if n(x)];body=n(fm.group(2));function_defs.append({"args":args,"body":body,"action_assignments":[n(x) for x in ACTION_ASSIGN_RE.findall(body)],"path_literals":[n(x) for x in PATH_LITERAL_RE.findall(body)]})
 forms=[]
 for fm in FORM_RE.finditer(raw):
  a=attrs(fm.group(1));inputs=[]
  for im in INPUT_RE.finditer(fm.group(2)):
   ia=attrs(im.group(1));inputs.append({k:ia.get(k,"") for k in ("type","name","id","value")})
  forms.append({"id":a.get("id",""),"name":a.get("name",""),"method":n(a.get("method") or "GET").upper(),"action":urljoin(final_url,a.get("action") or final_url),"inputs":inputs})
 # Structural derivation only from recovered function body.
 contracts=[]
 for fd in function_defs:
  if not fd["args"]:continue
  arg=fd["args"][0];body=fd["body"]
  # common current Seongnam pattern: form action '/bbs010308/' + pstSn, then submit
  base_paths=[p for p in fd["path_literals"] if "bbs010308" in p]
  submit_present="submit" in body.lower()
  if base_paths and submit_present:
   contracts.append({"method":"POST_OR_FORM_METHOD","mode":"PATH_APPEND","base_path":base_paths[0],"argument_name":arg,"function":"fn_move_form","evidence_body":body,"detail_request_executed":False,"target_query_executed":False,"verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False})
 resolution="MUNICIPAL_GAZETTE_EXACT_SERIALIZATION_CONTRACT_RECOVERED" if contracts else "MUNICIPAL_GAZETTE_EXACT_SERIALIZATION_CONTRACT_NO_CONTRACT"
 out={"step":"STEP 17-21-C-16-8-T-20 Municipal Gazette Exact Serialization Contract Recovery","target":{"name":TARGET_NAME,"standard_code":STANDARD_CODE},"resolution_policy":{"resolution_type":RESOLUTION_TYPE,"negative_evidence_allowed":False,"source_failure_site_status":"UNKNOWN"},"source_url":final_url,"http_status":r["http_status"],"function_definitions":function_defs,"forms":forms,"recovered_contracts":contracts,"next_stage_contract_pool":contracts,"resolution":resolution,"verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False,"final_positive_promotion_allowed":False}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 unsafe=sum(1 for x in contracts if x.get("detail_request_executed") or x.get("target_query_executed") or x.get("verified_positive") or x.get("runtime_registration_allowed") or x.get("site_positive_allowed") or x.get("site_negative_allowed"))
 vals={"T-19 input exists":T19.exists(),"T-19 contract pool loaded":bool(pool),"HTTP 200":r["http_status"]==200,"official source host":gov(host(final_url)),"fn_move_form definition recovered":bool(function_defs),"form structures recovered":bool(forms),"exact path evidence recovered":bool(contracts),"detail request execution disabled":True,"target query execution disabled":True,"unsafe promotion leakage zero":unsafe==0,"output written":OUT.exists() and OUT.stat().st_size>0}
 print("HTTP:",r["http_status"]);print("Final URL:",final_url);print("Function definitions:",len(function_defs));print("Forms:",len(forms));print("Recovered contracts:",len(contracts))
 for i,fd in enumerate(function_defs,1):print(f"FUNCTION {i}",fd)
 for i,c in enumerate(contracts,1):print(f"CONTRACT {i}",c)
 print("Resolution:",resolution);print("Output:",OUT);print();print("VALIDATION")
 for k,v in vals.items():print(f"{k}: {v}")
 print("Unsafe promotion leakage:",unsafe);print("all_pass:",all(vals.values()))
 if not all(vals.values()):raise AssertionError("municipal gazette exact serialization contract recovery failed")
if __name__=="__main__":main()
