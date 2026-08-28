# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1-2
Development Density Management Area
Municipal Gazette HWPX Package Entry Forensics

Inspect the single bounded representative HWPX already persisted by S1-1.
NETWORK IS DISABLED. This test classifies every ZIP member by compression metadata,
byte signature, XML parseability, text-likeness and entropy. It does not decrypt,
does not brute-force encodings, does not traverse gazette issues, and never promotes
retrieval evidence to legal/site TRUE or FALSE.
"""
from __future__ import annotations
import json,math,re,zipfile
from collections import Counter
from pathlib import Path
from typing import Any,Dict,List
import xml.etree.ElementTree as ET

BASE_DIR=Path(__file__).resolve().parent.parent
OUT_DIR=BASE_DIR/"law_data"/"output";OUT_DIR.mkdir(parents=True,exist_ok=True)
S1=OUT_DIR/"development_density_management_area_municipal_gazette_hwpx_section_parse_diagnostics.json"
SAMPLE=OUT_DIR/"development_density_management_area_municipal_gazette_representative_sample.hwpx"
OUT=OUT_DIR/"development_density_management_area_municipal_gazette_hwpx_package_entry_forensics.json"
TARGET_NAME="개발밀도관리구역";STANDARD_CODE="UQQ700";MAX_MEMBER_BYTES=16*1024*1024

COMP={zipfile.ZIP_STORED:"STORED",zipfile.ZIP_DEFLATED:"DEFLATED",zipfile.ZIP_BZIP2:"BZIP2",zipfile.ZIP_LZMA:"LZMA"}

def entropy(data:bytes)->float:
 if not data:return 0.0
 c=Counter(data);ln=len(data)
 return round(-sum((v/ln)*math.log2(v/ln) for v in c.values()),4)
def xml_candidate(name:str,data:bytes)->bool:
 return name.lower().endswith((".xml",".hpf",".opf")) or data.lstrip()[:5].lower().startswith(b"<?xml") or data.lstrip().startswith(b"<")
def text_ratio(data:bytes)->float:
 if not data:return 1.0
 sample=data[:8192]
 printable=sum(1 for b in sample if b in (9,10,13) or 32<=b<=126 or b>=128)
 return round(printable/len(sample),4)
def signature(data:bytes)->str:
 d=data[:16]
 if data.startswith(b"PK\x03\x04"):return "ZIP_LOCAL_HEADER"
 if data.startswith(b"%PDF-"):return "PDF"
 if data.startswith(b"\x89PNG\r\n\x1a\n"):return "PNG"
 if data.startswith(b"\xff\xd8\xff"):return "JPEG"
 if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):return "GIF"
 if data.startswith(b"\xef\xbb\xbf"):return "UTF8_BOM"
 if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):return "UTF16_BOM"
 if data.lstrip().startswith(b"<"):return "ANGLE_TEXT"
 if data.startswith(b"application/hwp+zip"):return "HWPX_MIMETYPE"
 return "UNKNOWN_BINARY_OR_TEXT"
def section_no(name:str)->int:
 m=re.search(r"section(\d+)\.xml$",name,re.I);return int(m.group(1)) if m else 10**9

def main():
 print("="*60);print("DEVELOPMENT DENSITY MANAGEMENT AREA");print("MUNICIPAL GAZETTE HWPX PACKAGE ENTRY FORENSICS");print("="*60)
 print("Target:",TARGET_NAME);print("Standard code:",STANDARD_CODE);print("Network requests: 0");print("Bulk traversal: DISABLED");print()
 if not S1.exists():raise FileNotFoundError(f"Run S1-1 first: {S1}")
 if not SAMPLE.exists():raise FileNotFoundError(f"Run updated S1-1 first to persist sample: {SAMPLE}")
 s1=json.loads(S1.read_text(encoding="utf-8"))
 entries:List[Dict[str,Any]]=[];zip_ok=False;bad_member=[]
 with zipfile.ZipFile(SAMPLE) as z:
  zip_ok=True
  bad=z.testzip()
  if bad:bad_member.append(bad)
  for info in z.infolist():
   if info.is_dir():continue
   if info.file_size>MAX_MEMBER_BYTES:
    entries.append({"member":info.filename,"skipped":True,"reason":"member exceeds forensic size bound","file_size":info.file_size,"compress_size":info.compress_size})
    continue
   data=z.read(info.filename)
   candidate=xml_candidate(info.filename,data);parse_ok=False;parse_error="";root_tag=""
   if candidate:
    try:
     root=ET.fromstring(data);parse_ok=True;root_tag=root.tag.rsplit("}",1)[-1]
    except Exception as e:parse_error=repr(e)
   ratio=round(info.compress_size/info.file_size,4) if info.file_size else 0.0
   entries.append({"member":info.filename,"file_size":info.file_size,"compress_size":info.compress_size,"compression":COMP.get(info.compress_type,str(info.compress_type)),"compression_ratio":ratio,"crc32":f"{info.CRC:08x}","flag_bits":info.flag_bits,"encrypted_zip_flag":bool(info.flag_bits&0x1),"signature":signature(data),"hex_prefix":data[:48].hex(" "),"entropy":entropy(data[:65536]),"text_like_ratio":text_ratio(data),"xml_candidate":candidate,"xml_parse_ok":parse_ok,"xml_root":root_tag,"xml_parse_error":parse_error[:300]})
 sections=sorted([e for e in entries if re.search(r"(^|/)section\d+\.xml$",e.get("member",""),re.I)],key=lambda x:section_no(x["member"]))
 xml_entries=[e for e in entries if e.get("xml_candidate")]
 xml_ok=[e for e in xml_entries if e.get("xml_parse_ok")]
 xml_fail=[e for e in xml_entries if not e.get("xml_parse_ok")]
 section_ok=[e for e in sections if e.get("xml_parse_ok")]
 section_fail=[e for e in sections if not e.get("xml_parse_ok")]
 key_names=["mimetype","META-INF/manifest.xml","Contents/content.hpf","Contents/header.xml"]
 key_entries=[]
 for k in key_names:
  match=next((e for e in entries if e.get("member","").lower()==k.lower()),None)
  key_entries.append({"expected":k,"entry":match})
 all_sections_fail=bool(sections) and len(section_fail)==len(sections)
 package_xml_mixed=bool(xml_ok) and bool(xml_fail)
 encrypted_flags=sum(1 for e in entries if e.get("encrypted_zip_flag"))
 high_entropy_failed_xml=sum(1 for e in xml_fail if (e.get("entropy") or 0)>=7.5)
 if all_sections_fail and package_xml_mixed:
  structural="SECTION_PAYLOADS_NON_XML_WHILE_OTHER_PACKAGE_XML_PARSEABLE"
 elif all_sections_fail:
  structural="ALL_SECTION_PAYLOADS_NON_XML_OR_UNPARSEABLE"
 elif section_fail and section_ok:
  structural="MIXED_SECTION_XML_PARSEABILITY"
 elif section_ok and not section_fail:
  structural="ALL_SECTION_XML_PARSEABLE"
 else:
  structural="SECTION_STRUCTURE_UNRESOLVED"
 out={"step":"STEP 17-21-C-16-8-T-28-S1-2 Municipal Gazette HWPX Package Entry Forensics","target":{"name":TARGET_NAME,"standard_code":STANDARD_CODE},"input":{"sample":str(SAMPLE),"sample_bytes":SAMPLE.stat().st_size,"prior_response_bytes":((s1.get("response") or {}).get("response_bytes"))},"network":{"request_count":0,"network_enabled":False},"archive":{"zip_valid":zip_ok,"zip_integrity_bad_member":bad_member,"entry_count":len(entries),"encrypted_zip_flag_count":encrypted_flags,"xml_candidate_count":len(xml_entries),"xml_parse_ok_count":len(xml_ok),"xml_parse_fail_count":len(xml_fail),"section_count":len(sections),"section_parse_ok_count":len(section_ok),"section_parse_fail_count":len(section_fail),"high_entropy_failed_xml_count":high_entropy_failed_xml},"key_entries":key_entries,"section_entries":sections,"entries":entries,"structural_classification":structural,"interpretation_guard":{"encryption_proven":False,"drm_proven":False,"nonstandard_payload_proven":all_sections_fail,"legal_target_evidence_proven":False,"note":"High entropy or failed XML parsing is structural evidence only; it does not by itself prove encryption or DRM."},"bulk_traversal_executed":False,"verified_positive":False,"site_positive_allowed":False,"site_negative_allowed":False,"resolution":"MUNICIPAL_GAZETTE_HWPX_PACKAGE_ENTRY_FORENSICS_COMPLETED"}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 vals={"S1-1 input exists":S1.exists(),"persisted sample exists":SAMPLE.exists() and SAMPLE.stat().st_size>0,"network request count zero":out["network"]["request_count"]==0 and not out["network"]["network_enabled"],"HWPX ZIP valid":zip_ok,"ZIP integrity clean":not bad_member,"entries recovered":len(entries)>0,"section entries recovered":len(sections)>0,"bulk traversal disabled":not out["bulk_traversal_executed"],"encryption not overclaimed":not out["interpretation_guard"]["encryption_proven"] and not out["interpretation_guard"]["drm_proven"],"unsafe promotion disabled":not any([out["verified_positive"],out["site_positive_allowed"],out["site_negative_allowed"]]),"output written":OUT.exists() and OUT.stat().st_size>0}
 print("Sample:",SAMPLE);print("Sample bytes:",SAMPLE.stat().st_size);print("ZIP valid:",zip_ok);print("Entries:",len(entries));print("XML candidates:",len(xml_entries),"parse OK:",len(xml_ok),"fail:",len(xml_fail));print("Sections:",len(sections),"parse OK:",len(section_ok),"fail:",len(section_fail));print("ZIP encrypted flags:",encrypted_flags);print("High-entropy failed XML:",high_entropy_failed_xml);print("Structural classification:",structural)
 print();print("KEY ENTRIES")
 for x in key_entries:
  e=x.get("entry");print(x["expected"],"=>",("MISSING" if not e else {k:e.get(k) for k in ["file_size","compression","signature","entropy","xml_candidate","xml_parse_ok","xml_root"]}))
 print();print("SECTIONS")
 for e in sections:
  print(e["member"],"size=",e["file_size"],"compressed=",e["compress_size"],"method=",e["compression"],"entropy=",e["entropy"],"signature=",e["signature"],"xml_ok=",e["xml_parse_ok"],"hex=",e["hex_prefix"][:95])
 print();print("Resolution:",out["resolution"]);print("Output:",OUT);print();print("VALIDATION")
 for k,v in vals.items():print(f"{k}: {v}")
 print("all_pass:",all(vals.values()))
 if not all(vals.values()):raise AssertionError("HWPX package entry forensics failed")
if __name__=="__main__":main()
