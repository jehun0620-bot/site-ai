# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1-1
Development Density Management Area
Municipal Gazette HWPX Section Parse Diagnostics

Download exactly one validated representative HWPX and diagnose why section*.xml
fails XML parsing. Inspect only byte prefixes, BOM/XML declaration candidates, decoding
attempts, and parse exceptions. No bulk traversal and no legal promotion.
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
OUT=OUT_DIR/"development_density_management_area_municipal_gazette_hwpx_section_parse_diagnostics.json"
TARGET_NAME="개발밀도관리구역";STANDARD_CODE="UQQ700";MAX_BYTES=8*1024*1024;TIMEOUT=30
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
ENCODINGS=["utf-8-sig","utf-8","utf-16","utf-16-le","utf-16-be","cp949","euc-kr"]

def n(v:Any)->str:return re.sub(r"\s+"," ",str(v or "")).strip()
def host(u:str)->str:
 try:return (urlparse(u).hostname or "").lower()
 except:return ""
def gov(h:str)->bool:return bool(h) and (h=="go.kr" or h.endswith(".go.kr"))
def detect_bom(data:bytes)->str:
 if data.startswith(b"\xef\xbb\xbf"):return "UTF-8-BOM"
 if data.startswith(b"\xff\xfe\x00\x00"):return "UTF-32-LE"
 if data.startswith(b"\x00\x00\xfe\xff"):return "UTF-32-BE"
 if data.startswith(b"\xff\xfe"):return "UTF-16-LE"
 if data.startswith(b"\xfe\xff"):return "UTF-16-BE"
 return "NONE"
def printable_prefix(data:bytes,encoding:str)->str:
 try:return data[:512].decode(encoding,errors="replace").replace("\x00","\\0")[:500]
 except Exception as e:return f"<decode-error {e!r}>"
def main():
 print("="*60);print("DEVELOPMENT DENSITY MANAGEMENT AREA");print("MUNICIPAL GAZETTE HWPX SECTION PARSE DIAGNOSTICS");print("="*60)
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
 diagnostics=[];zip_ok=False
 if raw:
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   zip_ok=True
   section_names=[m for m in z.namelist() if re.search(r"(^|/)section\d+\.xml$",m,re.I)]
   for name in section_names:
    data=z.read(name);direct_error="";direct_ok=False
    try:ET.fromstring(data);direct_ok=True
    except Exception as e:direct_error=repr(e)
    decode_attempts=[]
    for enc in ENCODINGS:
     try:
      txt=data.decode(enc);decl=re.search(r"<\?xml[^>]*encoding=[\"']([^\"']+)",txt[:300],re.I)
      parse_ok=False;parse_error=""
      try:ET.fromstring(txt);parse_ok=True
      except Exception as e:parse_error=repr(e)
      decode_attempts.append({"encoding":enc,"decode_ok":True,"xml_decl_encoding":decl.group(1) if decl else "","parse_ok":parse_ok,"parse_error":parse_error,"prefix":txt[:300].replace("\x00","\\0")})
     except Exception as e:
      decode_attempts.append({"encoding":enc,"decode_ok":False,"decode_error":repr(e)})
    diagnostics.append({"member":name,"byte_size":len(data),"bom":detect_bom(data),"hex_prefix":data[:96].hex(" "),"ascii_prefix":printable_prefix(data,"latin1"),"utf8_replace_prefix":printable_prefix(data,"utf-8"),"direct_bytes_parse_ok":direct_ok,"direct_bytes_parse_error":direct_error,"decode_attempts":decode_attempts})
 out={"step":"STEP 17-21-C-16-8-T-28-S1-1 Municipal Gazette HWPX Section Parse Diagnostics","target":{"name":TARGET_NAME,"standard_code":STANDARD_CODE},"request":{"count":1,"params":params},"response":{"http_status":status,"final_url":final_url,"response_bytes":len(raw),"error":err},"archive":{"zip_valid":zip_ok,"section_count":len(diagnostics)},"section_diagnostics":diagnostics,"bulk_traversal_executed":False,"verified_positive":False,"site_positive_allowed":False,"site_negative_allowed":False,"resolution":"MUNICIPAL_GAZETTE_HWPX_SECTION_PARSE_DIAGNOSTICS_COMPLETED"}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 vals={"T-26 input exists":T26.exists(),"T-27 input exists":T27.exists(),"single bounded download":out["request"]["count"]==1,"HTTP 200":status==200,"official host":gov(host(final_url)) and host(final_url)==host(c["action"]),"HWPX ZIP valid":zip_ok,"section diagnostics recovered":len(diagnostics)>0,"bulk traversal disabled":not out["bulk_traversal_executed"],"unsafe promotion disabled":not any([out["verified_positive"],out["site_positive_allowed"],out["site_negative_allowed"]]),"output written":OUT.exists() and OUT.stat().st_size>0}
 print("HTTP:",status);print("Final URL:",final_url);print("Response bytes:",len(raw));print("ZIP valid:",zip_ok);print("Section count:",len(diagnostics))
 for d in diagnostics:
  print("-"*60);print("SECTION",d["member"]);print("Bytes:",d["byte_size"]);print("BOM:",d["bom"]);print("Hex prefix:",d["hex_prefix"]);print("UTF-8 prefix:",d["utf8_replace_prefix"][:300]);print("Direct bytes parse ok:",d["direct_bytes_parse_ok"]);print("Direct parse error:",d["direct_bytes_parse_error"])
  for a in d["decode_attempts"]:
   if a.get("decode_ok"):
    print("DECODE",a["encoding"],"parse_ok=",a["parse_ok"],"decl=",a.get("xml_decl_encoding","") ,"error=",a.get("parse_error","")[:180]);print(" PREFIX",a.get("prefix","")[:220])
   else:print("DECODE",a["encoding"],"FAILED",a.get("decode_error"))
 print("Resolution:",out["resolution"]);print("Output:",OUT);print();print("VALIDATION")
 for k,v in vals.items():print(f"{k}: {v}")
 print("all_pass:",all(vals.values()))
 if not all(vals.values()):raise AssertionError("HWPX section parse diagnostics failed")
if __name__=="__main__":main()
