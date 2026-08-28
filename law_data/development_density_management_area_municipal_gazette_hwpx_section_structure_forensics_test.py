# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1
Development Density Management Area
Municipal Gazette HWPX Section Structure Forensics

Download exactly one validated representative HWPX and inspect archive member names,
XML roots, namespaces, and text-bearing element tags. No bulk traversal and no legal promotion.
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
OUT=OUT_DIR/"development_density_management_area_municipal_gazette_hwpx_section_structure_forensics.json"
TARGET_NAME="개발밀도관리구역";STANDARD_CODE="UQQ700";MAX_BYTES=8*1024*1024;TIMEOUT=30
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

def n(v:Any)->str:return re.sub(r"\s+"," ",str(v or "")).strip()
def local(tag:str)->str:return tag.rsplit("}",1)[-1] if "}" in tag else tag
def host(u:str)->str:
 try:return (urlparse(u).hostname or "").lower()
 except:return ""
def gov(h:str)->bool:return bool(h) and (h=="go.kr" or h.endswith(".go.kr"))
def main():
 print("="*60);print("DEVELOPMENT DENSITY MANAGEMENT AREA");print("MUNICIPAL GAZETTE HWPX SECTION STRUCTURE FORENSICS");print("="*60)
 print("Target:",TARGET_NAME);print("Standard code:",STANDARD_CODE);print("HWPX download count: 1");print("Bulk traversal: DISABLED");print()
 if not T26.exists():raise FileNotFoundError(T26)
 if not T27.exists():raise FileNotFoundError(T27)
 t26=json.loads(T26.read_text(encoding="utf-8"));t27=json.loads(T27.read_text(encoding="utf-8"))
 hwpx=[x for x in (t26.get("attachment_metadata") or []) if str(x.get("file_ext","")).lower()=="hwpx"]
 contracts=t27.get("next_stage_download_contract_pool") or []
 if len(hwpx)!=1 or len(contracts)!=1:raise AssertionError("representative HWPX/download contract cardinality failure")
 att=hwpx[0];c=contracts[0];pst=str((t26.get("request") or {}).get("params",{}).get("pstSn") or "")
 params={"bbsCrtSn":"16002","pstSn":pst,c["file_no_field"]:str(att.get("file_no") or "")}
 s=requests.Session();s.headers.update({"User-Agent":UA,"Referer":f"https://www.seongnam.go.kr/bbs010308/{pst}"})
 status=None;final_url="";raw=b"";err=""
 try:
  with s.get(c["action"],params=params,timeout=TIMEOUT,allow_redirects=True,stream=True) as r:
   status=r.status_code;final_url=str(r.url);chunks=[];total=0
   for b in r.iter_content(131072):
    if not b:continue
    total+=len(b)
    if total>MAX_BYTES:raise ValueError("download exceeded bounded size")
    chunks.append(b)
   raw=b"".join(chunks)
 except Exception as e:err=repr(e)
 members=[];xml_info=[];zip_ok=False
 if raw:
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   zip_ok=True;members=z.namelist()
   for name in members:
    if not name.lower().endswith(".xml"):continue
    data=z.read(name)
    try:
     root=ET.fromstring(data);counts={};text_samples=[];text_chars=0
     for elem in root.iter():
      tag=local(elem.tag);counts[tag]=counts.get(tag,0)+1
      if elem.text and elem.text.strip():
       txt=n(elem.text);text_chars+=len(txt)
       if len(text_samples)<20:text_samples.append({"tag":tag,"text":txt[:160]})
     xml_info.append({"member":name,"root_tag":local(root.tag),"byte_size":len(data),"text_chars":text_chars,"top_tags":sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:20],"text_samples":text_samples})
    except Exception as e:
     xml_info.append({"member":name,"parse_error":repr(e),"byte_size":len(data)})
 section_info=[x for x in xml_info if "section" in x.get("member","").lower()]
 out={"step":"STEP 17-21-C-16-8-T-28-S1 Municipal Gazette HWPX Section Structure Forensics","target":{"name":TARGET_NAME,"standard_code":STANDARD_CODE},"request":{"count":1,"params":params},"response":{"http_status":status,"final_url":final_url,"response_bytes":len(raw),"error":err},"archive":{"zip_valid":zip_ok,"members":members,"xml_member_count":len(xml_info),"section_member_count":len(section_info)},"xml_info":xml_info,"section_info":section_info,"bulk_traversal_executed":False,"verified_positive":False,"site_positive_allowed":False,"site_negative_allowed":False,"resolution":"MUNICIPAL_GAZETTE_HWPX_SECTION_STRUCTURE_FORENSICS_COMPLETED"}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 vals={"T-26 input exists":T26.exists(),"T-27 input exists":T27.exists(),"single bounded download":out["request"]["count"]==1,"HTTP 200":status==200,"official host":gov(host(final_url)) and host(final_url)==host(c["action"]),"HWPX ZIP valid":zip_ok,"XML members found":len(xml_info)>0,"section members found":len(section_info)>0,"bulk traversal disabled":not out["bulk_traversal_executed"],"unsafe promotion disabled":not any([out["verified_positive"],out["site_positive_allowed"],out["site_negative_allowed"]]),"output written":OUT.exists() and OUT.stat().st_size>0}
 print("HTTP:",status);print("Final URL:",final_url);print("Response bytes:",len(raw));print("ZIP valid:",zip_ok);print("Archive members:",len(members));
 for m in members:print("MEMBER",m)
 print("XML members:",len(xml_info));print("Section members:",len(section_info))
 for x in section_info:
  print("-"*60);print("SECTION",x.get("member"));print("Root:",x.get("root_tag"));print("Bytes:",x.get("byte_size"));print("Text chars:",x.get("text_chars"));print("Top tags:",x.get("top_tags"));print("Text samples:")
  for sm in x.get("text_samples",[])[:20]:print(" ",sm)
 print("Resolution:",out["resolution"]);print("Output:",OUT);print();print("VALIDATION")
 for k,v in vals.items():print(f"{k}: {v}")
 print("all_pass:",all(vals.values()))
 if not all(vals.values()):raise AssertionError("HWPX section structure forensics failed")
if __name__=="__main__":main()
