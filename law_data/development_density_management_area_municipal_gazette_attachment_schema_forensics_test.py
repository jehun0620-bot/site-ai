# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-26-S1
Development Density Management Area
Municipal Gazette Attachment Schema Forensics

Inspect only the raw attachment metadata already captured by T-26.
No network requests, no file download, no preview, no legal promotion.
"""
from __future__ import annotations
import json,re
from pathlib import Path
from typing import Any,Dict,List

BASE_DIR=Path(__file__).resolve().parent.parent
OUT_DIR=BASE_DIR/"law_data"/"output"
T26=OUT_DIR/"development_density_management_area_municipal_gazette_attachment_metadata_enumeration.json"
OUT=OUT_DIR/"development_density_management_area_municipal_gazette_attachment_schema_forensics.json"
TARGET_NAME="개발밀도관리구역";STANDARD_CODE="UQQ700"

def n(v:Any)->str:return re.sub(r"\s+"," ",str(v or "")).strip()
def main():
 print("="*60);print("DEVELOPMENT DENSITY MANAGEMENT AREA");print("MUNICIPAL GAZETTE ATTACHMENT SCHEMA FORENSICS");print("="*60)
 print("Target:",TARGET_NAME);print("Standard code:",STANDARD_CODE);print("Network requests: DISABLED");print()
 if not T26.exists():raise FileNotFoundError(T26)
 t26=json.loads(T26.read_text(encoding="utf-8"));items=t26.get("attachment_metadata") or []
 if not items:raise AssertionError("T-26 attachment metadata missing")
 forensic=[];all_keys=set();string_fields=[]
 for idx,item in enumerate(items,1):
  raw=item.get("raw") or {};keys=sorted(str(k) for k in raw.keys());all_keys.update(keys)
  vals=[]
  for k,v in raw.items():
   if isinstance(v,(str,int,float,bool)) or v is None:
    sv=n(v)
    vals.append({"key":str(k),"value":sv,"looks_like_filename":bool(re.search(r"\.(pdf|hwp|hwpx|docx?|xlsx?|zip)$",sv,re.I)),"contains_korean":bool(re.search(r"[가-힣]",sv))})
    if sv:string_fields.append((str(k),sv))
  forensic.append({"index":idx,"file_no":item.get("file_no"),"normalized_file_name":item.get("file_name"),"normalized_file_ext":item.get("file_ext"),"raw_keys":keys,"scalar_fields":vals})
 filename_candidates=[]
 for k,v in string_fields:
  score=0;lk=k.lower()
  if any(x in lk for x in ["name","nm","fnm","file"]):score+=1
  if re.search(r"\.(pdf|hwp|hwpx|docx?|xlsx?|zip)$",v,re.I):score+=3
  if re.search(r"[가-힣]",v):score+=1
  if score>=2:filename_candidates.append({"key":k,"value":v,"score":score})
 # de-dup
 seen=set();fc=[]
 for x in sorted(filename_candidates,key=lambda z:(-z["score"],z["key"],z["value"])):
  key=(x["key"],x["value"])
  if key in seen:continue
  seen.add(key);fc.append(x)
 out={"step":"STEP 17-21-C-16-8-T-26-S1 Municipal Gazette Attachment Schema Forensics","target":{"name":TARGET_NAME,"standard_code":STANDARD_CODE},"method":{"network_requests_enabled":False,"input_only":str(T26)},"summary":{"attachment_count":len(items),"raw_key_count":len(all_keys),"filename_candidate_count":len(fc)},"all_raw_keys":sorted(all_keys),"filename_field_candidates":fc,"attachments":forensic,"verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False,"final_positive_promotion_allowed":False,"resolution":"MUNICIPAL_GAZETTE_ATTACHMENT_SCHEMA_FORENSICS_COMPLETED"}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 unsafe=any(out[k] for k in ["verified_positive","runtime_registration_allowed","site_positive_allowed","site_negative_allowed","final_positive_promotion_allowed"])
 vals={"T-26 input exists":T26.exists(),"attachments loaded":len(items)>0,"network requests disabled":True,"raw keys recovered":len(all_keys)>0,"unsafe promotion leakage zero":not unsafe,"output written":OUT.exists() and OUT.stat().st_size>0}
 print("Attachment count:",len(items));print("Raw keys:",sorted(all_keys));print("Filename field candidates:",len(fc))
 for i,x in enumerate(fc[:20],1):print(f"CANDIDATE {i}",x)
 for f in forensic:
  print("-"*60);print("ATTACHMENT",f["index"],"file_no=",f["file_no"],"ext=",f["normalized_file_ext"])
  for sv in f["scalar_fields"]:print(sv["key"],"=",sv["value"])
 print("Resolution:",out["resolution"]);print("Output:",OUT);print();print("VALIDATION")
 for k,v in vals.items():print(f"{k}: {v}")
 print("all_pass:",all(vals.values()))
 if not all(vals.values()):raise AssertionError("attachment schema forensics failed")
if __name__=="__main__":main()
