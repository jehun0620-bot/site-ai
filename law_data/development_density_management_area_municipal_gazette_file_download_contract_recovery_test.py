# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-27
Development Density Management Area
Municipal Gazette File Download Contract Recovery

Recover exact getFileVO/getFilePreviewVO form serialization from one already-validated
municipal gazette detail page. No attachment download or preview request is executed.
"""
from __future__ import annotations

import html,json,re
from pathlib import Path
from typing import Any,Dict,List
from urllib.parse import urljoin,urlparse
import requests

BASE_DIR=Path(__file__).resolve().parent.parent
OUT_DIR=BASE_DIR/"law_data"/"output";OUT_DIR.mkdir(parents=True,exist_ok=True)
T26=OUT_DIR/"development_density_management_area_municipal_gazette_attachment_metadata_enumeration.json"
OUT=OUT_DIR/"development_density_management_area_municipal_gazette_file_download_contract_recovery.json"
TARGET_NAME="개발밀도관리구역";STANDARD_CODE="UQQ700";RESOLUTION_TYPE="HYBRID_SPATIAL_NOTICE"
TIMEOUT=20;MAX_BYTES=12*1024*1024
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
FORM_RE=re.compile(r"<form\b([^>]*)>(.*?)</form>",re.I|re.S)
INPUT_RE=re.compile(r"<input\b([^>]*)>",re.I|re.S)
ATTR_RE=re.compile(r'''([:\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))''',re.I)
SCRIPT_RE=re.compile(r"<script\b[^>]*>(.*?)</script>",re.I|re.S)
FUNC_RE=re.compile(r"function\s+(fn_get_file|fn_view_file)\s*\(([^)]*)\)\s*\{(.*?)\}",re.I|re.S)

def n(v:Any)->str:return re.sub(r"\s+"," ",str(v or "")).strip()
def attrs(raw:str)->Dict[str,str]:
 d={}
 for m in ATTR_RE.finditer(raw or ""):d[m.group(1).lower()]=html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
 return d
def host(u:str)->str:
 try:return (urlparse(u).hostname or "").lower()
 except:return ""
def gov(h:str)->bool:return bool(h) and (h=="go.kr" or h.endswith(".go.kr"))
def fetch(s,url):
 out={"http_status":None,"final_url":"","text":"","error":"","response_bytes":0}
 try:
  with s.get(url,timeout=TIMEOUT,allow_redirects=True,stream=True) as r:
   out["http_status"]=r.status_code;out["final_url"]=str(r.url);chunks=[];total=0
   for c in r.iter_content(131072):
    if not c:continue
    total+=len(c)
    if total>MAX_BYTES:raise ValueError("response too large")
    chunks.append(c)
   raw=b"".join(chunks);out["response_bytes"]=len(raw)
   for enc in [r.encoding,"utf-8","cp949","euc-kr"]:
    if not enc:continue
    try:out["text"]=raw.decode(enc);break
    except:pass
   if not out["text"]:out["text"]=raw.decode("utf-8",errors="replace")
 except Exception as e:out["error"]=repr(e)
 return out

def main():
 print("="*60);print("DEVELOPMENT DENSITY MANAGEMENT AREA");print("MUNICIPAL GAZETTE FILE DOWNLOAD CONTRACT RECOVERY");print("="*60)
 print("Target:",TARGET_NAME);print("Standard code:",STANDARD_CODE);print("Detail request count: 1");print("File download: DISABLED");print("Preview request: DISABLED");print()
 if not T26.exists():raise FileNotFoundError(T26)
 t26=json.loads(T26.read_text(encoding="utf-8"));detail_url=(t26.get("request") or {}).get("endpoint","").replace("/atchFileDetail","")
 pst=(t26.get("request") or {}).get("params",{}).get("pstSn")
 detail_url=f"{detail_url}/{pst}" if detail_url and pst else "https://www.seongnam.go.kr/bbs010308/404960"
 s=requests.Session();s.headers.update({"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9"})
 r=fetch(s,detail_url);raw=r["text"] or ""
 forms=[]
 for fm in FORM_RE.finditer(raw):
  fa=attrs(fm.group(1));fid=fa.get("id","")
  if fid not in {"getFileVO","getFilePreviewVO"}:continue
  inputs=[]
  for im in INPUT_RE.finditer(fm.group(2)):
   ia=attrs(im.group(1));inputs.append({"name":ia.get("name",""),"id":ia.get("id",""),"type":ia.get("type",""),"value":ia.get("value","")})
  action=fa.get("action","");method=(fa.get("method") or "GET").upper()
  forms.append({"id":fid,"method":method,"action":action,"absolute_action":urljoin(r["final_url"] or detail_url,action),"inputs":inputs})
 functions=[]
 for sm in SCRIPT_RE.finditer(raw):
  for fn in FUNC_RE.finditer(sm.group(1)):
   functions.append({"name":fn.group(1),"args":[n(x) for x in fn.group(2).split(",") if n(x)],"body":n(fn.group(3))[:3000]})
 by_id={f["id"]:f for f in forms}
 download=by_id.get("getFileVO");preview=by_id.get("getFilePreviewVO")
 next_pool=[]
 if download:
  file_inputs=[x for x in download["inputs"] if "fileno" in (x["name"]+x["id"]).lower()]
  if len(file_inputs)==1:
   next_pool.append({"contract_type":"ATTACHMENT_DOWNLOAD_FORM","form_id":"getFileVO","method":download["method"],"action":download["absolute_action"],"file_no_field":file_inputs[0]["name"] or file_inputs[0]["id"],"download_execution_allowed_next_stage":True})
 out={"step":"STEP 17-21-C-16-8-T-27 Municipal Gazette File Download Contract Recovery","target":{"name":TARGET_NAME,"standard_code":STANDARD_CODE},"resolution_policy":{"resolution_type":RESOLUTION_TYPE,"negative_evidence_allowed":False},"request":{"count":1,"detail_url":detail_url},"response":{"http_status":r["http_status"],"final_url":r["final_url"],"response_bytes":r["response_bytes"]},"forms":forms,"functions":functions,"summary":{"qualified_form_count":len(forms),"function_count":len(functions),"next_stage_contract_count":len(next_pool)},"next_stage_download_contract_pool":next_pool,"file_download_executed":False,"preview_request_executed":False,"verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False,"final_positive_promotion_allowed":False,"resolution":"MUNICIPAL_GAZETTE_FILE_DOWNLOAD_CONTRACT_RECOVERED" if len(next_pool)==1 else "MUNICIPAL_GAZETTE_FILE_DOWNLOAD_CONTRACT_UNRESOLVED"}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 unsafe=any(out[k] for k in ["file_download_executed","preview_request_executed","verified_positive","runtime_registration_allowed","site_positive_allowed","site_negative_allowed","final_positive_promotion_allowed"])
 vals={"T-26 input exists":T26.exists(),"HTTP 200":r["http_status"]==200,"official same host":gov(host(r["final_url"])) and host(r["final_url"])==host(detail_url),"getFileVO recovered":download is not None,"getFilePreviewVO recovered":preview is not None,"download function recovered":any(f["name"].lower()=="fn_get_file" for f in functions),"preview function recovered":any(f["name"].lower()=="fn_view_file" for f in functions),"single download contract qualified":len(next_pool)==1,"download execution disabled":not out["file_download_executed"],"preview execution disabled":not out["preview_request_executed"],"unsafe promotion leakage zero":not unsafe,"output written":OUT.exists() and OUT.stat().st_size>0}
 print("HTTP:",r["http_status"]);print("Final URL:",r["final_url"]);print("Recovered forms:",len(forms));print("Recovered functions:",len(functions))
 for f in forms:print("FORM",f)
 for f in functions:print("FUNCTION",f)
 print("Next-stage download contracts:",len(next_pool));
 for c in next_pool:print("CONTRACT",c)
 print("Resolution:",out["resolution"]);print("Output:",OUT);print();print("VALIDATION")
 for k,v in vals.items():print(f"{k}: {v}")
 print("all_pass:",all(vals.values()))
 if not all(vals.values()):raise AssertionError("municipal gazette file download contract recovery failed")
if __name__=="__main__":main()
