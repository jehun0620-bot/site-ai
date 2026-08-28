# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28
Development Density Management Area
Municipal Gazette Bounded HWPX Text Extraction Probe

Download exactly one already-enumerated HWPX attachment using the validated T-27 form
contract, inspect its ZIP/XML structure, and extract plain text for technical feasibility.
No bulk traversal, no legal validity/spatial inference, no SITE/runtime promotion.
"""
from __future__ import annotations

import io,json,re,zipfile
from pathlib import Path
from typing import Any,Dict,List
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import requests

BASE_DIR=Path(__file__).resolve().parent.parent
OUT_DIR=BASE_DIR/"law_data"/"output";OUT_DIR.mkdir(parents=True,exist_ok=True)
T26=OUT_DIR/"development_density_management_area_municipal_gazette_attachment_metadata_enumeration.json"
T27=OUT_DIR/"development_density_management_area_municipal_gazette_file_download_contract_recovery.json"
OUT=OUT_DIR/"development_density_management_area_municipal_gazette_hwpx_bounded_text_extraction.json"
TARGET_NAME="개발밀도관리구역";STANDARD_CODE="UQQ700";RESOLUTION_TYPE="HYBRID_SPATIAL_NOTICE"
MAX_BYTES=8*1024*1024;TIMEOUT=30
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
DIRECT_TERMS=["개발밀도관리구역","개발 밀도 관리 구역"]
RELATED_TERMS=["개발밀도","밀도관리","기반시설부담","기반시설 용량","기반시설용량"]

def n(v:Any)->str:return re.sub(r"\s+"," ",str(v or "")).strip()
def host(u:str)->str:
 try:return (urlparse(u).hostname or "").lower()
 except:return ""
def gov(h:str)->bool:return bool(h) and (h=="go.kr" or h.endswith(".go.kr"))
def extract_xml_text(data:bytes)->str:
 try:
  root=ET.fromstring(data)
  vals=[]
  for elem in root.iter():
   if elem.text and elem.text.strip():vals.append(elem.text.strip())
  return n(" ".join(vals))
 except Exception:
  try:return n(data.decode("utf-8",errors="ignore"))
  except:return ""
def main():
 print("="*60);print("DEVELOPMENT DENSITY MANAGEMENT AREA");print("MUNICIPAL GAZETTE BOUNDED HWPX TEXT EXTRACTION PROBE");print("="*60)
 print("Target:",TARGET_NAME);print("Standard code:",STANDARD_CODE);print("Attachment download count: 1");print("Bulk traversal: DISABLED");print("Legal promotion: DISABLED");print()
 if not T26.exists():raise FileNotFoundError(T26)
 if not T27.exists():raise FileNotFoundError(T27)
 t26=json.loads(T26.read_text(encoding="utf-8"));t27=json.loads(T27.read_text(encoding="utf-8"))
 atts=t26.get("attachment_metadata") or []
 hwpx=[x for x in atts if str(x.get("file_ext","")).lower()=="hwpx"]
 contracts=t27.get("next_stage_download_contract_pool") or []
 if len(hwpx)!=1:raise AssertionError(f"expected exactly one representative HWPX, got {len(hwpx)}")
 if len(contracts)!=1:raise AssertionError(f"expected exactly one download contract, got {len(contracts)}")
 att=hwpx[0];contract=contracts[0]
 endpoint=contract["action"];pstSn=str((t26.get("request") or {}).get("params",{}).get("pstSn") or "")
 params={"bbsCrtSn":"16002","pstSn":pstSn,contract["file_no_field"]:str(att.get("file_no") or "")}
 s=requests.Session();s.headers.update({"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9","Referer":f"https://www.seongnam.go.kr/bbs010308/{pstSn}"})
 status=None;final_url="";ctype="";raw=b"";error=""
 try:
  with s.get(endpoint,params=params,timeout=TIMEOUT,allow_redirects=True,stream=True) as r:
   status=r.status_code;final_url=str(r.url);ctype=r.headers.get("Content-Type","");chunks=[];total=0
   for c in r.iter_content(131072):
    if not c:continue
    total+=len(c)
    if total>MAX_BYTES:raise ValueError("download exceeded bounded size")
    chunks.append(c)
   raw=b"".join(chunks)
 except Exception as e:error=repr(e)
 zip_ok=False;members=[];xml_members=[];texts=[]
 if raw:
  try:
   with zipfile.ZipFile(io.BytesIO(raw)) as z:
    zip_ok=True;members=z.namelist();xml_members=[m for m in members if m.lower().endswith(".xml")]
    for name in xml_members:
     if name.lower().startswith(("contents/","content/","sections/")) or "section" in name.lower():
      try:
       txt=extract_xml_text(z.read(name))
       if txt:texts.append({"member":name,"text":txt})
      except:pass
    if not texts:
     for name in xml_members[:20]:
      try:
       txt=extract_xml_text(z.read(name))
       if txt:texts.append({"member":name,"text":txt})
      except:pass
  except Exception as e:
   error=(error+"; " if error else "")+repr(e)
 full=n(" ".join(x["text"] for x in texts));direct=[t for t in DIRECT_TERMS if t in full];related=[t for t in RELATED_TERMS if t in full]
 samples=[]
 for term in direct+related:
  i=full.find(term)
  if i>=0:samples.append({"term":term,"context":full[max(0,i-100):i+len(term)+180]})
 out={"step":"STEP 17-21-C-16-8-T-28 Municipal Gazette Bounded HWPX Text Extraction Probe","target":{"name":TARGET_NAME,"standard_code":STANDARD_CODE},"resolution_policy":{"resolution_type":RESOLUTION_TYPE,"negative_evidence_allowed":False,"no_match_site_status":"UNKNOWN"},"request":{"count":1,"method":"GET","endpoint":endpoint,"params":params},"response":{"http_status":status,"final_url":final_url,"content_type":ctype,"response_bytes":len(raw),"error":error},"attachment":{"file_no":att.get("file_no"),"file_name":att.get("file_name"),"file_ext":att.get("file_ext")},"archive":{"zip_valid":zip_ok,"member_count":len(members),"xml_member_count":len(xml_members),"sample_members":members[:30]},"text_extraction":{"text_member_count":len(texts),"text_length":len(full),"direct_terms_found":direct,"related_terms_found":related,"match_samples":samples,"text_preview":full[:1000]},"bulk_traversal_executed":False,"document_identity_verified":False,"validity_verified":False,"spatial_inclusion_verified":False,"verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False,"final_positive_promotion_allowed":False,"resolution":"MUNICIPAL_GAZETTE_HWPX_TEXT_EXTRACTION_FEASIBLE" if zip_ok and len(full)>0 else "MUNICIPAL_GAZETTE_HWPX_TEXT_EXTRACTION_UNRESOLVED"}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 unsafe=any(out[k] for k in ["bulk_traversal_executed","document_identity_verified","validity_verified","spatial_inclusion_verified","verified_positive","runtime_registration_allowed","site_positive_allowed","site_negative_allowed","final_positive_promotion_allowed"])
 vals={"T-26 input exists":T26.exists(),"T-27 input exists":T27.exists(),"single HWPX selected":len(hwpx)==1,"single bounded download":out["request"]["count"]==1,"HTTP 200":status==200,"official host":gov(host(final_url)) and host(final_url)==host(endpoint),"HWPX ZIP valid":zip_ok,"XML members recovered":len(xml_members)>0,"plain text extracted":len(full)>0,"bulk traversal disabled":not out["bulk_traversal_executed"],"unsafe promotion leakage zero":not unsafe,"output written":OUT.exists() and OUT.stat().st_size>0}
 print("HTTP:",status);print("Final URL:",final_url);print("Content-Type:",ctype);print("Response bytes:",len(raw));print("ZIP valid:",zip_ok);print("Archive members:",len(members));print("XML members:",len(xml_members));print("Text members:",len(texts));print("Extracted text length:",len(full));print("Direct terms found:",direct);print("Related terms found:",related);print("Text preview:",full[:800]);print("Resolution:",out["resolution"]);print("Output:",OUT);print();print("VALIDATION")
 for k,v in vals.items():print(f"{k}: {v}")
 print("all_pass:",all(vals.values()))
 if not all(vals.values()):raise AssertionError("bounded HWPX text extraction probe failed")
if __name__=="__main__":main()
