# -*- coding: utf-8 -*-
"""T-28-S1-5: decrypt and search all section*.xml entries of ONE persisted HWPX.

Offline-only. Uses the previously validated public Hancom distribution-password
compatibility constant. Verifies each section against manifest SHA256-1K, parses XML,
extracts paragraph text, merges the representative gazette issue, and searches only
for UQQ700-related terms. No network, no archive traversal, no legal/SITE promotion.
"""
from __future__ import annotations

import base64, hashlib, json, re, zlib, zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
from Crypto.Cipher import AES

BASE_DIR=Path(__file__).resolve().parent.parent
OUT_DIR=BASE_DIR/"law_data"/"output"
SAMPLE=OUT_DIR/"development_density_management_area_municipal_gazette_representative_sample.hwpx"
PRIOR=OUT_DIR/"development_density_management_area_municipal_gazette_hwpx_bounded_section_decryption_text_extraction.json"
OUT=OUT_DIR/"development_density_management_area_municipal_gazette_hwpx_full_section_offline_text_search.json"
PASSWORD=bytes([0x22,0x59,0x61,0x6e,0x67,0x20,0x57,0x61,0x6e,0x67,0x53,0x75,0x6e,0x76,0x21,0x21,0x22])
DIRECT=["개발밀도관리구역","개발밀도 관리구역"]
RELATED=["개발밀도","밀도관리","관리구역"]

def ln(s): return s.rsplit("}",1)[-1] if "}" in s else s

def attr(e,name):
    for k,v in e.attrib.items():
        if ln(k)==name:return str(v)
    return ""

def manifest_entries(root):
    out={}
    for e in root.iter():
        if ln(e.tag)!="file-entry":continue
        path=attr(e,"full-path")
        if not re.search(r"(^|/)section\d+\.xml$",path,re.I):continue
        d={"path":path,"plain_size":int(attr(e,"size") or 0)}
        for c in e.iter():
            n=ln(c.tag)
            if n=="encryption-data":d.update(checksum=attr(c,"checksum"),checksum_type=attr(c,"checksum-type"))
            elif n=="algorithm":d.update(iv=attr(c,"initialisation-vector"),algorithm=attr(c,"algorithm-name"))
            elif n=="key-derivation":d.update(salt=attr(c,"salt"),iterations=int(attr(c,"iteration-count") or 0),key_size=int(attr(c,"key-size") or 0))
            elif n=="start-key-generation":d.update(start_key=attr(c,"start-key-generation-name"))
        out[path]=d
    return out

def decrypt(ciphertext,d):
    start=hashlib.sha256(PASSWORD).digest()
    key=hashlib.pbkdf2_hmac("sha1",start,base64.b64decode(d["salt"]),d["iterations"],dklen=d["key_size"])
    raw=AES.new(key,AES.MODE_CBC,base64.b64decode(d["iv"])).decrypt(ciphertext)
    return zlib.decompress(raw,-zlib.MAX_WBITS)

def text_from_root(root):
    paragraphs=[]
    for p in root.iter():
        if ln(p.tag)!="p":continue
        t="".join((x.text or "") for x in p.iter() if ln(x.tag)=="t").strip()
        if t:paragraphs.append(t)
    return "\n".join(paragraphs),paragraphs

def main():
    print("="*60);print("DEVELOPMENT DENSITY MANAGEMENT AREA");print("MUNICIPAL GAZETTE HWPX FULL SECTION OFFLINE TEXT SEARCH");print("="*60)
    print("Target: 개발밀도관리구역");print("Standard code: UQQ700");print("Network requests: 0");print("Representative HWPX issues: 1");print("Bulk archive traversal: DISABLED\n")
    if not SAMPLE.exists():raise FileNotFoundError(SAMPLE)
    if not PRIOR.exists():raise FileNotFoundError(PRIOR)
    prior=json.loads(PRIOR.read_text(encoding="utf-8"))
    prior_ok=prior.get("classification")=="SECTION_DECRYPTION_VALIDATED_TEXT_EXTRACTED"
    sections=[];merged=[]
    with zipfile.ZipFile(SAMPLE) as z:
        mr=ET.fromstring(z.read("META-INF/manifest.xml"));contracts=manifest_entries(mr)
        names=sorted(contracts,key=lambda x:int(re.search(r"section(\d+)",x,re.I).group(1)))
        for name in names:
            d=contracts[name];rec={"member":name,"xml_ok":False,"checksum_ok":False}
            try:
                plain=decrypt(z.read(name),d)
                rec["plain_bytes"]=len(plain);rec["manifest_plain_size"]=d["plain_size"]
                rec["plain_size_matches"]=len(plain)==d["plain_size"]
                rec["checksum_ok"]=hashlib.sha256(plain[:1024]).digest()==base64.b64decode(d["checksum"])
                root=ET.fromstring(plain);rec["xml_ok"]=True;rec["root"]=ln(root.tag)
                text,pars=text_from_root(root);merged.append(text)
                rec.update(text_chars=len(text),paragraph_count=len(pars),hangul_chars=len(re.findall(r"[가-힣]",text)),direct_matches={t:text.count(t) for t in DIRECT},related_matches={t:text.count(t) for t in RELATED})
            except Exception as e:rec["error"]=repr(e)
            sections.append(rec)
    full="\n".join(x for x in merged if x)
    direct={t:full.count(t) for t in DIRECT};related={t:full.count(t) for t in RELATED}
    contexts=[]
    for term in DIRECT+RELATED:
        start=0
        while True:
            i=full.find(term,start)
            if i<0:break
            contexts.append({"term":term,"index":i,"context":full[max(0,i-180):i+len(term)+260]})
            start=i+len(term)
            if len(contexts)>=50:break
    all_valid=bool(sections) and all(x.get("xml_ok") and x.get("checksum_ok") and x.get("plain_size_matches") for x in sections)
    if all_valid and any(direct.values()):classification="REPRESENTATIVE_GAZETTE_FULL_TEXT_DIRECT_UQQ700_TERM_FOUND"
    elif all_valid and any(related.values()):classification="REPRESENTATIVE_GAZETTE_FULL_TEXT_RELATED_TERM_FOUND"
    elif all_valid:classification="REPRESENTATIVE_GAZETTE_FULL_TEXT_NO_UQQ700_TERM"
    else:classification="REPRESENTATIVE_GAZETTE_SECTION_RECOVERY_INCOMPLETE"
    out={"step":"STEP 17-21-C-16-8-T-28-S1-5","target":{"name":"개발밀도관리구역","standard_code":"UQQ700"},"network_request_count":0,"representative_issue_count":1,"bulk_archive_traversal_executed":False,"prior_single_section_validation":prior_ok,"section_count":len(sections),"all_sections_validated":all_valid,"sections":sections,"merged_text_chars":len(full),"merged_hangul_chars":len(re.findall(r"[가-힣]",full)),"direct_matches":direct,"related_matches":related,"match_contexts":contexts,"classification":classification,"semantic_note":"This searches one representative gazette issue only. No-match is not historical negative evidence and cannot produce UQQ700 FALSE.","verified_positive":False,"site_positive_allowed":False,"site_negative_allowed":False,"resolution":"MUNICIPAL_GAZETTE_HWPX_FULL_SECTION_OFFLINE_TEXT_SEARCH_COMPLETED"}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Sections:",len(sections));print("All sections validated:",all_valid);print("Merged text chars:",len(full));print("Merged Hangul chars:",out["merged_hangul_chars"]);print("Direct matches:",direct);print("Related matches:",related);print("Classification:",classification)
    print("\nSECTION SUMMARY")
    for x in sections:print("-",x["member"],"bytes=",x.get("plain_bytes"),"size_ok=",x.get("plain_size_matches"),"checksum_ok=",x.get("checksum_ok"),"xml_ok=",x.get("xml_ok"),"text=",x.get("text_chars"),"direct=",x.get("direct_matches"),"related=",x.get("related_matches"))
    print("\nMATCH CONTEXTS")
    for c in contexts:print("-",c["term"],repr(c["context"]))
    vals={"persisted sample exists":SAMPLE.exists(),"prior single-section validation exists":prior_ok,"network request count zero":True,"representative issue count one":True,"section entries recovered":len(sections)>0,"all sections cryptographically and structurally validated":all_valid,"bulk archive traversal disabled":not out["bulk_archive_traversal_executed"],"unsafe promotion disabled":not any([out["verified_positive"],out["site_positive_allowed"],out["site_negative_allowed"]]),"output written":OUT.exists()}
    print("\nResolution:",out["resolution"]);print("Output:",OUT);print("\nVALIDATION")
    for k,v in vals.items():print(f"{k}: {v}")
    print("all_pass:",all(vals.values()))
    if not all(vals.values()):raise AssertionError("full section offline text search validation failed")
if __name__=="__main__":main()
