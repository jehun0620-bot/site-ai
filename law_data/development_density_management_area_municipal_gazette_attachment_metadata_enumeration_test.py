# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-26
Development Density Management Area
Municipal Gazette Attachment Metadata Enumeration

Execute exactly one validated atchFileDetail request for the known gazette sample and
recover attachment metadata only. No file download, no preview request, no UQQ700 promotion.
"""
from __future__ import annotations
import json,re
from pathlib import Path
from typing import Any,Dict,List
from urllib.parse import urljoin,urlparse
import requests

BASE_DIR=Path(__file__).resolve().parent.parent
OUT_DIR=BASE_DIR/"law_data"/"output";OUT_DIR.mkdir(parents=True,exist_ok=True)
T25=OUT_DIR/"development_density_management_area_municipal_gazette_detail_attachment_contract_probe.json"
OUT=OUT_DIR/"development_density_management_area_municipal_gazette_attachment_metadata_enumeration.json"
TARGET_NAME="개발밀도관리구역";STANDARD_CODE="UQQ700";RESOLUTION_TYPE="HYBRID_SPATIAL_NOTICE"
KNOWN_PSTSN="404960";TIMEOUT=20;MAX_BYTES=8*1024*1024
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

def n(v:Any)->str:return re.sub(r"\s+"," ",str(v or "")).strip()
def host(u:str)->str:
 try:return (urlparse(u).hostname or "").lower()
 except:return ""
def gov(h:str)->bool:return bool(h) and (h=="go.kr" or h.endswith(".go.kr"))
def fetch_json(s,url,params):
 out={"http_status":None,"final_url":"","json":None,"text":"","error":"","response_bytes":0}
 try:
  with s.get(url,params=params,timeout=TIMEOUT,allow_redirects=True,stream=True) as r:
   out["http_status"]=r.status_code;out["final_url"]=str(r.url);chunks=[];total=0
   for c in r.iter_content(131072):
    if not c:continue
    total+=len(c)
    if total>MAX_BYTES:raise ValueError("response too large")
    chunks.append(c)
   raw=b"".join(chunks);out["response_bytes"]=len(raw)
   txt=raw.decode(r.encoding or "utf-8",errors="replace");out["text"]=txt
   try:out["json"]=r.json()
   except:
    try:out["json"]=json.loads(txt)
    except:pass
 except Exception as e:out["error"]=repr(e)
 return out

def flatten_items(obj:Any)->List[Dict[str,Any]]:
 found=[]
 def walk(x):
  if isinstance(x,dict):
   keys={str(k).lower() for k in x.keys()}
   if any(k in keys for k in ["fileno","file_no","atchfileno","orgnlfnm","fileNm".lower(),"streflnm"]):found.append(x)
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(obj)
 return found

def main():
 print("="*60);print("DEVELOPMENT DENSITY MANAGEMENT AREA");print("MUNICIPAL GAZETTE ATTACHMENT METADATA ENUMERATION");print("="*60)
 print("Target:",TARGET_NAME);print("Standard code:",STANDARD_CODE);print("Attachment metadata request count: 1");print("File download: DISABLED");print("Preview request: DISABLED");print()
 if not T25.exists():raise FileNotFoundError(T25)
 t25=json.loads(T25.read_text(encoding="utf-8"));detail_url=t25.get("request",{}).get("url") or "https://www.seongnam.go.kr/bbs010308/404960"
 endpoint=urljoin(detail_url,"/bbs010308/atchFileDetail")
 s=requests.Session();s.headers.update({"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9","Referer":detail_url})
 r=fetch_json(s,endpoint,{"pstSn":KNOWN_PSTSN})
 items=flatten_items(r.get("json")) if r.get("json") is not None else []
 normalized=[]
 for item in items:
  lower={str(k).lower():v for k,v in item.items()}
  file_no=lower.get("fileno") or lower.get("file_no") or lower.get("atchfileno") or lower.get("fileid")
  name=lower.get("orgnlfnm") or lower.get("filename") or lower.get("filenm") or lower.get("streflnm") or lower.get("orignlfilenm")
  ext=lower.get("fileextsn") or lower.get("fileext") or ""
  normalized.append({"file_no":str(file_no or ""),"file_name":n(name),"file_ext":n(ext),"raw":item})
 # dedup by file_no + name
 seen=set();dedup=[]
 for x in normalized:
  key=(x["file_no"],x["file_name"])
  if key in seen:continue
  seen.add(key);dedup.append(x)
 out={"step":"STEP 17-21-C-16-8-T-26 Municipal Gazette Attachment Metadata Enumeration","target":{"name":TARGET_NAME,"standard_code":STANDARD_CODE},"resolution_policy":{"resolution_type":RESOLUTION_TYPE,"negative_evidence_allowed":False,"source_failure_site_status":"UNKNOWN"},"request":{"count":1,"method":"GET","endpoint":endpoint,"params":{"pstSn":KNOWN_PSTSN}},"response":{"http_status":r["http_status"],"final_url":r["final_url"],"response_bytes":r["response_bytes"],"json_detected":r["json"] is not None},"attachment_metadata":dedup,"summary":{"attachment_count":len(dedup)},"file_download_executed":False,"preview_request_executed":False,"verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False,"final_positive_promotion_allowed":False,"resolution":"MUNICIPAL_GAZETTE_ATTACHMENT_METADATA_ENUMERATION_COMPLETED"}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 unsafe=any([out["file_download_executed"],out["preview_request_executed"],out["verified_positive"],out["runtime_registration_allowed"],out["site_positive_allowed"],out["site_negative_allowed"],out["final_positive_promotion_allowed"]])
 vals={"T-25 input exists":T25.exists(),"HTTP 200":r["http_status"]==200,"official same host":gov(host(r["final_url"])) and host(r["final_url"])==host(endpoint),"single metadata request only":out["request"]["count"]==1,"JSON response detected":r["json"] is not None,"attachment metadata recovered":len(dedup)>0,"file download disabled":not out["file_download_executed"],"preview request disabled":not out["preview_request_executed"],"unsafe promotion leakage zero":not unsafe,"output written":OUT.exists() and OUT.stat().st_size>0}
 print("HTTP:",r["http_status"]);print("Final URL:",r["final_url"]);print("JSON detected:",r["json"] is not None);print("Attachment count:",len(dedup))
 for i,x in enumerate(dedup[:10],1):print(f"ATTACHMENT {i}",{"file_no":x["file_no"],"file_name":x["file_name"],"file_ext":x["file_ext"]})
 print("Resolution:",out["resolution"]);print("Output:",OUT);print();print("VALIDATION")
 for k,v in vals.items():print(f"{k}: {v}")
 print("all_pass:",all(vals.values()))
 if not all(vals.values()):raise AssertionError("municipal gazette attachment metadata enumeration failed")
if __name__=="__main__":main()
