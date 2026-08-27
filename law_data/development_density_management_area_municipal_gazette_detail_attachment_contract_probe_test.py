# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-25
Development Density Management Area
Municipal Gazette Detail / Attachment Contract Probe

Probe exactly one already-validated gazette detail page to recover body and attachment
interaction contracts. No UQQ700 legal identity promotion or bulk traversal.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR=Path(__file__).resolve().parent.parent
OUT_DIR=BASE_DIR/"law_data"/"output";OUT_DIR.mkdir(parents=True,exist_ok=True)
T21=OUT_DIR/"development_density_management_area_municipal_gazette_bounded_detail_validation.json"
OUT=OUT_DIR/"development_density_management_area_municipal_gazette_detail_attachment_contract_probe.json"

TARGET_NAME="개발밀도관리구역";STANDARD_CODE="UQQ700";RESOLUTION_TYPE="HYBRID_SPATIAL_NOTICE"
KNOWN_PSTSN="404960";KNOWN_GAZETTE=2087
TIMEOUT=20;MAX_BYTES=12*1024*1024
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

A_RE=re.compile(r"<a\b([^>]*)>(.*?)</a>",re.I|re.S)
ATTR_RE=re.compile(r'''([:\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))''',re.I)
TAG_RE=re.compile(r"<[^>]+>",re.S)
SCRIPT_RE=re.compile(r"<script\b[^>]*>(.*?)</script>",re.I|re.S)
FUNC_RE=re.compile(r"function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{(.*?)\}",re.S)
FILE_HINTS=("첨부","다운로드","download","file","파일")

def n(v:Any)->str:return re.sub(r"\s+"," ",str(v or "")).strip()
def attrs(raw:str)->Dict[str,str]:
 out={}
 for m in ATTR_RE.finditer(raw or ""):out[m.group(1).lower()]=html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
 return out
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
 print("="*60);print("DEVELOPMENT DENSITY MANAGEMENT AREA");print("MUNICIPAL GAZETTE DETAIL / ATTACHMENT CONTRACT PROBE");print("="*60)
 print("Target:",TARGET_NAME);print("Standard code:",STANDARD_CODE);print("Known detail probe count: 1");print("UQQ700 promotion: DISABLED");print()
 if not T21.exists():raise FileNotFoundError(T21)
 t21=json.loads(T21.read_text(encoding="utf-8"));pool=t21.get("next_stage_contract_pool") or []
 if not pool:raise AssertionError("T-21 validated contract missing")
 detail_url=pool[0]["known_sample"]["detail_url"]
 s=requests.Session();s.headers.update({"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9"})
 r=fetch(s,detail_url);raw=r["text"] or "";plain=n(html.unescape(TAG_RE.sub(" ",raw)))
 anchors=[]
 for m in A_RE.finditer(raw):
  a=attrs(m.group(1));text=n(html.unescape(TAG_RE.sub(" ",m.group(2))));href=n(a.get("href"));onclick=n(a.get("onclick"));absolute=urljoin(r["final_url"] or detail_url,href) if href and not href.lower().startswith("javascript:") else ""
  evidence=(text+" "+href+" "+onclick).lower()
  if any(h.lower() in evidence for h in FILE_HINTS) or any(ext in evidence for ext in [".pdf",".hwp",".hwpx",".zip",".doc",".docx"]):
   anchors.append({"text":text,"href":href,"onclick":onclick,"absolute_url":absolute})
 functions=[]
 for sm in SCRIPT_RE.finditer(raw):
  for fm in FUNC_RE.finditer(sm.group(1)):
   body=n(fm.group(3))
   evidence=(fm.group(1)+" "+body).lower()
   if any(h.lower() in evidence for h in FILE_HINTS):functions.append({"name":fm.group(1),"args":[n(x) for x in fm.group(2).split(",") if n(x)],"body":body[:5000]})
 # record broad content signals without claiming legal target identity
 content_signals={k:(k in plain) for k in ["고시","공고","조례","첨부파일","성남시보"]}
 out={"step":"STEP 17-21-C-16-8-T-25 Municipal Gazette Detail Attachment Contract Probe","target":{"name":TARGET_NAME,"standard_code":STANDARD_CODE},"resolution_policy":{"resolution_type":RESOLUTION_TYPE,"negative_evidence_allowed":False,"source_failure_site_status":"UNKNOWN"},"request":{"count":1,"url":detail_url},"response":{"http_status":r["http_status"],"final_url":r["final_url"],"response_bytes":r["response_bytes"],"known_gazette_reproduced":f"성남시보 제{KNOWN_GAZETTE}호" in plain,"content_signals":content_signals},"attachment_anchors":anchors,"attachment_functions":functions,"summary":{"attachment_anchor_count":len(anchors),"attachment_function_count":len(functions)},"resolution":"MUNICIPAL_GAZETTE_DETAIL_ATTACHMENT_CONTRACT_PROBE_COMPLETED","verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False,"final_positive_promotion_allowed":False}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 unsafe=any([out["verified_positive"],out["runtime_registration_allowed"],out["site_positive_allowed"],out["site_negative_allowed"],out["final_positive_promotion_allowed"]])
 vals={"T-21 input exists":T21.exists(),"HTTP 200":r["http_status"]==200,"official same host":gov(host(r["final_url"])) and host(r["final_url"])==host(detail_url),"known gazette reproduced":out["response"]["known_gazette_reproduced"],"single request only":out["request"]["count"]==1,"unsafe promotion leakage zero":not unsafe,"output written":OUT.exists() and OUT.stat().st_size>0}
 print("HTTP:",r["http_status"]);print("Final URL:",r["final_url"]);print("Content signals:",content_signals);print("Attachment anchors:",len(anchors));print("Attachment functions:",len(functions))
 for i,a in enumerate(anchors[:10],1):print(f"ANCHOR {i}",a)
 for i,f in enumerate(functions[:10],1):print(f"FUNCTION {i}",f)
 print("Resolution:",out["resolution"]);print("Output:",OUT);print();print("VALIDATION")
 for k,v in vals.items():print(f"{k}: {v}")
 print("all_pass:",all(vals.values()))
 if not all(vals.values()):raise AssertionError("municipal gazette detail attachment contract probe failed")
if __name__=="__main__":main()
