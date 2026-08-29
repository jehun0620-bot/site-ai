# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-32
Development Density Management Area
Municipal Gazette HWP3 UQQ700 Bounded Batch Search

Actual candidate search begins here.

Scope
-----
- HWP3 era only: canonical rows from archive start through Gazette 524 / 2003-12-29
- first bounded batch: exactly 10 rows
- per row: attachment metadata + one HWP download
- parse HWP3 searchable paragraph text with the validated structural contract
- search direct and related UQQ700 terms
- persist cumulative batch state for later continuation

Safety
------
- no OCR
- no PDF search
- no HWP5/HWPX rows
- no legal/SITE promotion
- zero matches => UNKNOWN, never FALSE
"""
from __future__ import annotations

import json
import re
import struct
import zlib
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
T23 = OUT_DIR / "development_density_management_area_municipal_gazette_historical_row_registry_recovery.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp3_uqq700_bounded_batch_search.json"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp3_uqq700_cumulative_state.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
DIRECT = ["개발밀도관리구역", "개발밀도 관리구역"]
RELATED = ["개발밀도", "밀도관리", "관리구역"]

HWP3_LAST_PST = "28673"  # Gazette 524, 2003-12-29
BATCH_SIZE = 10
MAX_REQUESTS = 20
TIMEOUT = 30
MAX_META_BYTES = 8 * 1024 * 1024
MAX_FILE_BYTES = 12 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
ATTACHMENT_ENDPOINT = "https://www.seongnam.go.kr/bbs010308/atchFileDetail"
DOWNLOAD_ENDPOINT = "https://www.seongnam.go.kr/bbs010308/getFile"
BASE_DETAIL = "https://www.seongnam.go.kr/bbs010308/"
BBS_CRT_SN = "16002"
HWP3_SIG = b"HWP Document File V3.00"

PARA_SHAPE_SIZE = 187
LINE_INFO_SIZE = 14
INLINE_CHAR_SHAPE_SIZE = 31
STYLE_RECORD_SIZE = 238
MAX_RECURSION = 32
MAX_PARAGRAPHS = 200_000
MAX_CELL_COUNT = 20_000

CHO_MAP = [-1, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18] + [-1] * 11
JUNG_MAP = [-1, -1, -1, 0, 1, 2, 3, 4, -1, -1, 5, 6, 7, 8, 9, 10, -1, -1, 11, 12, 13, 14, 15, 16, -1, -1, 17, 18, 19, 20, -1, -1]
JONG_MAP = [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, -1, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, -1, -1]
EXTRA_MAP = {0x0081: "“", 0x0082: "”", 0x301C: "━", 0x303D: "■", 0x3366: "□", 0x3404: "․", 0x3441: "■", 0x3446: "→", 0x35E1: "─", 0x3479: "▷", 0x347A: "▶", 0x2F67: "▸"}
SIMPLE_CTRL = {9:(6,3,"\t"),18:(6,3," "),19:(6,3," "),20:(6,3," "),21:(6,3," "),22:(22,11," "),23:(8,4," "),24:(4,2,"-"),25:(4,2,""),26:(244,122," "),28:(62,31," "),30:(2,1," "),31:(2,1," ")}


class Reader:
    def __init__(self, data: bytes): self.data, self.pos = data, 0
    def remaining(self): return len(self.data) - self.pos
    def eof(self): return self.pos >= len(self.data)
    def ensure(self, n):
        if n < 0 or self.pos + n > len(self.data): raise ValueError(f"insufficient data need={n} remaining={self.remaining()}")
    def skip(self, n): self.ensure(n); self.pos += n
    def read_u8(self): self.ensure(1); v=self.data[self.pos]; self.pos+=1; return v
    def read_u16(self): self.ensure(2); v=struct.unpack_from("<H",self.data,self.pos)[0]; self.pos+=2; return v
    def read_u32(self): self.ensure(4); v=struct.unpack_from("<I",self.data,self.pos)[0]; self.pos+=4; return v
    def read_bytes(self,n): self.ensure(n); b=self.data[self.pos:self.pos+n]; self.pos+=n; return b


def norm(v: Any) -> str: return re.sub(r"\s+", " ", str(v or "")).strip()
def parse_date(v: Any) -> Optional[date]:
    try:
        y,m,d=[int(x) for x in norm(v).split("-")]; return date(y,m,d)
    except Exception: return None

def host(url: str) -> str:
    try: return (urlparse(url).hostname or "").lower()
    except Exception: return ""

def decode_hchar(ch: int) -> str:
    if ch < 0x80: return chr(ch)
    if 0x3590 <= ch <= 0x3599: return chr(0x2160 + ch - 0x3590)
    if 0x36E7 <= ch <= 0x36F0: return chr(0x2460 + ch - 0x36E7)
    if 0x37C0 <= ch <= 0x37C5: return "한글과컴퓨터"[ch - 0x37C0]
    if ch in EXTRA_MAP: return EXTRA_MAP[ch]
    if ch >= 0x8000:
        cho,jung,jong=CHO_MAP[(ch>>10)&31],JUNG_MAP[(ch>>5)&31],JONG_MAP[ch&31]
        if cho>=0 and jung>=0 and jong>=0: return chr(0xAC00 + cho*588 + jung*28 + jong)
        try: return ch.to_bytes(2,"big").decode("johab")
        except Exception: return ""
    return ""

def skip_fonts_styles(r: Reader):
    for _ in range(7): r.skip(r.read_u16()*40)
    r.skip(r.read_u16()*STYLE_RECORD_SIZE)

def parse_picture(r,ctx,depth):
    info=r.read_bytes(348); n=struct.unpack_from("<I",info,0)[0]
    if n>100*1024*1024 or n>r.remaining(): raise ValueError("invalid picture extension")
    r.skip(n); parse_paragraph_list(r,ctx,depth+1)

def parse_table(r,ctx,depth):
    info=r.read_bytes(84); cells=struct.unpack_from("<H",info,80)[0] or 1
    if cells>MAX_CELL_COUNT or cells*27>r.remaining(): raise ValueError("invalid table")
    r.skip(cells*27)
    for _ in range(cells): parse_paragraph_list(r,ctx,depth+1)
    parse_paragraph_list(r,ctx,depth+1)

def parse_char_stream(r,char_count,ctx,depth):
    out=[]; i=0
    while i<char_count:
        ch=r.read_u16(); i+=1
        if ch==13: out.append("\n"); continue
        if ch==0: continue
        if ch>=32: out.append(decode_hchar(ch)); continue
        simple=SIMPLE_CTRL.get(ch)
        if simple:
            eb,eh,emit=simple; r.skip(eb); i+=eh
            if emit: out.append(emit)
            continue
        hv=r.read_u32(); r.read_u16(); i+=3
        if ch==10: parse_table(r,ctx,depth)
        elif ch==11: parse_picture(r,ctx,depth)
        elif ch==14: r.skip(84)
        elif ch==15: r.skip(8); parse_paragraph_list(r,ctx,depth+1)
        elif ch==16: r.skip(10); parse_paragraph_list(r,ctx,depth+1)
        elif ch==17: r.skip(14); parse_paragraph_list(r,ctx,depth+1)
        elif ch==5:
            if 0<hv<1_000_000: r.skip(hv)
        elif ch==6: r.skip(34)
        elif ch==7: r.skip(76)
        elif ch==8: r.skip(88)
        elif ch==29:
            if hv<1_000_000: r.skip(hv)
    return re.sub(r"[ \t]+"," ","".join(out)).strip()

def parse_paragraph_list(r,ctx,depth=0):
    if depth>MAX_RECURSION: raise ValueError("recursion limit")
    while not r.eof():
        if ctx["headers"]>=MAX_PARAGRAPHS: raise ValueError("paragraph limit")
        follow=r.read_u8(); chars=r.read_u16(); ctx["headers"]+=1
        if chars==0: r.skip(40); return
        lines=r.read_u16()
        if chars>60000 or lines>4096: raise ValueError("abnormal paragraph header")
        include=r.read_u8(); r.skip(1+4+1+31)
        if follow==0: r.skip(PARA_SHAPE_SIZE)
        r.skip(lines*LINE_INFO_SIZE)
        if include:
            for _ in range(chars):
                flag=r.read_u8()
                if flag!=1: r.skip(INLINE_CHAR_SHAPE_SIZE)
        text=parse_char_stream(r,chars,ctx,depth)
        if text: ctx["paragraphs"].append(text)

def extract_hwp3(raw: bytes) -> Dict[str, Any]:
    if not raw.startswith(HWP3_SIG): return {"ok":False,"error":"not HWP3 signature","text":""}
    if len(raw)<1166: return {"ok":False,"error":"too short","text":""}
    compressed=raw[30+124]
    info_len=struct.unpack_from("<H",raw,30+126)[0]
    offset=30+128+1008+info_len
    try:
        if compressed:
            dec=zlib.decompressobj(-zlib.MAX_WBITS); body=dec.decompress(raw[offset:])+dec.flush()
            if not dec.eof: return {"ok":False,"error":"deflate EOF not reached","text":""}
        else: body=raw[offset:]
        r=Reader(body); skip_fonts_styles(r); ctx={"headers":0,"paragraphs":[]}; parse_paragraph_list(r,ctx,0)
        text="\n".join(ctx["paragraphs"])
        return {"ok":len(text)>0,"error":"","text":text,"paragraphs":len(ctx["paragraphs"]),"headers":ctx["headers"],"consumed":r.pos,"body_bytes":len(body)}
    except Exception as exc:
        return {"ok":False,"error":repr(exc),"text":""}

def flatten_items(obj: Any) -> List[Dict[str, Any]]:
    found=[]
    def walk(x):
        if isinstance(x,dict):
            keys={str(k).lower() for k in x}
            if any(k in keys for k in ["fileno","file_no","atchfileno","orginlfilenm","orignlfilenm","strefilenm"]): found.append(x)
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(obj); return found

def hwp_attachment(obj: Any) -> Optional[Dict[str,str]]:
    for item in flatten_items(obj):
        lower={str(k).lower():v for k,v in item.items()}; no=lower.get("fileno") or lower.get("file_no") or lower.get("atchfileno") or lower.get("fileid")
        name=norm(lower.get("orginlfilenm") or lower.get("orignlfilenm") or lower.get("filename") or lower.get("filenm") or lower.get("strefilenm"))
        if name.lower().endswith(".hwp") and norm(no): return {"file_no":norm(no),"file_name":name}
    return None

def get_json(session,pst):
    detail=urljoin(BASE_DETAIL,pst)
    with session.get(ATTACHMENT_ENDPOINT,params={"pstSn":pst},headers={"Referer":detail},timeout=TIMEOUT,allow_redirects=True,stream=True) as r:
        chunks=[]; total=0
        for c in r.iter_content(128*1024):
            if not c: continue
            total+=len(c)
            if total>MAX_META_BYTES: raise ValueError("metadata too large")
            chunks.append(c)
        raw=b"".join(chunks)
        try: obj=r.json()
        except Exception: obj=json.loads(raw.decode(r.encoding or "utf-8",errors="replace"))
        return r.status_code,str(r.url),obj

def get_file(session,pst,file_no):
    detail=urljoin(BASE_DETAIL,pst); params={"bbsCrtSn":BBS_CRT_SN,"pstSn":pst,"fileNo":file_no}
    with session.get(DOWNLOAD_ENDPOINT,params=params,headers={"Referer":detail},timeout=TIMEOUT,allow_redirects=True,stream=True) as r:
        chunks=[]; total=0
        for c in r.iter_content(128*1024):
            if not c: continue
            total+=len(c)
            if total>MAX_FILE_BYTES: raise ValueError("file too large")
            chunks.append(c)
        return r.status_code,str(r.url),b"".join(chunks)


def main():
    print("="*60); print("DEVELOPMENT DENSITY MANAGEMENT AREA"); print("MUNICIPAL GAZETTE HWP3 UQQ700 BOUNDED BATCH SEARCH"); print("="*60)
    print("Target:",TARGET_NAME); print("Standard code:",STANDARD_CODE); print("Batch size:",BATCH_SIZE); print("Max requests:",MAX_REQUESTS); print("OCR: DISABLED"); print()
    if not T23.exists(): raise FileNotFoundError(T23)
    reg=json.loads(T23.read_text(encoding="utf-8")); rows=[r for r in (reg.get("canonical_gazette_rows") or []) if parse_date(r.get("date")) and norm(r.get("pstSn"))]
    rows.sort(key=lambda r:(parse_date(r.get("date")),int(r.get("gazette_number") or 0),norm(r.get("pstSn"))))
    end=next(i for i,r in enumerate(rows) if norm(r.get("pstSn"))==HWP3_LAST_PST)
    era=rows[:end+1]
    state={"processed_pstSn":[],"results":[]} if not STATE.exists() else json.loads(STATE.read_text(encoding="utf-8"))
    done=set(state.get("processed_pstSn") or [])
    selected=[r for r in era if norm(r.get("pstSn")) not in done][:BATCH_SIZE]
    if not selected:
        print("No remaining HWP3 rows."); return
    session=requests.Session(); session.headers.update({"User-Agent":USER_AGENT,"Accept-Language":"ko-KR,ko;q=0.9"})
    req=0; batch=[]
    for row in selected:
        pst=norm(row.get("pstSn")); rec={"date":norm(row.get("date")),"gazette_number":row.get("gazette_number"),"pstSn":pst,"status":"UNKNOWN","direct_matches":{},"related_matches":{},"error":""}
        try:
            hs,mu,obj=get_json(session,pst); req+=1; att=hwp_attachment(obj)
            rec["metadata_http"]=hs; rec["metadata_url"]=mu; rec["attachment"]=att
            if not att: raise ValueError("HWP attachment not found")
            ds,du,raw=get_file(session,pst,att["file_no"]); req+=1
            rec["download_http"]=ds; rec["download_url"]=du; rec["download_bytes"]=len(raw)
            ext=extract_hwp3(raw); rec["extract_ok"]=ext.get("ok"); rec["extract_error"]=ext.get("error"); rec["text_chars"]=len(ext.get("text","") or ""); rec["paragraphs"]=ext.get("paragraphs",0)
            if not ext.get("ok"): raise ValueError(ext.get("error") or "HWP3 extraction failed")
            text=ext["text"]; rec["direct_matches"]={t:text.count(t) for t in DIRECT}; rec["related_matches"]={t:text.count(t) for t in RELATED}
            if any(rec["direct_matches"].values()): rec["status"]="DIRECT_CANDIDATE"
            elif any(rec["related_matches"].values()): rec["status"]="RELATED_CANDIDATE"
            else: rec["status"]="NO_TERM_IN_EXTRACTED_SAMPLE"
        except Exception as exc:
            rec["error"]=repr(exc); rec["status"]="EXTRACTION_OR_REQUEST_UNKNOWN"
        batch.append(rec); print("ROW:",{k:rec.get(k) for k in ["gazette_number","date","pstSn","status","text_chars","direct_matches","related_matches","error"]})
    merged_results=(state.get("results") or [])+batch; processed=list(dict.fromkeys((state.get("processed_pstSn") or [])+[r["pstSn"] for r in batch]))
    candidates=[r for r in merged_results if r.get("status") in {"DIRECT_CANDIDATE","RELATED_CANDIDATE"}]
    unresolved=[r for r in merged_results if r.get("status")=="EXTRACTION_OR_REQUEST_UNKNOWN"]
    new_state={"era":"HWP3","era_row_count":len(era),"processed_count":len(processed),"remaining_count":len(era)-len(processed),"processed_pstSn":processed,"candidate_count":len(candidates),"unresolved_count":len(unresolved),"results":merged_results,"negative_evidence_allowed":False}
    STATE.write_text(json.dumps(new_state,ensure_ascii=False,indent=2),encoding="utf-8")
    output={"step":"STEP 17-21-C-16-8-T-32 Municipal Gazette HWP3 UQQ700 Bounded Batch Search","target":{"name":TARGET_NAME,"standard_code":STANDARD_CODE},"network_request_count":req,"batch_size":len(batch),"era_row_count":len(era),"batch":batch,"cumulative_summary":{k:new_state[k] for k in ["processed_count","remaining_count","candidate_count","unresolved_count"]},"negative_evidence_allowed":False,"verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False,"final_positive_promotion_allowed":False,"resolution":"MUNICIPAL_GAZETTE_HWP3_UQQ700_BOUNDED_BATCH_SEARCH_COMPLETED"}
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print(); print("SUMMARY"); print("HWP3 era rows:",len(era)); print("Batch processed:",len(batch)); print("Cumulative processed:",new_state["processed_count"]); print("Remaining:",new_state["remaining_count"]); print("Candidates:",new_state["candidate_count"]); print("Unresolved:",new_state["unresolved_count"]); print("Network requests:",req); print("State:",STATE); print("Output:",OUT)
    unsafe=any([output["verified_positive"],output["runtime_registration_allowed"],output["site_positive_allowed"],output["site_negative_allowed"],output["final_positive_promotion_allowed"]])
    vals={"T-23 registry exists":T23.exists(),"batch bounded":len(batch)<=BATCH_SIZE,"request budget respected":req<=MAX_REQUESTS,"all response hosts official":all((not r.get("metadata_url") or host(r.get("metadata_url"))=="www.seongnam.go.kr") and (not r.get("download_url") or host(r.get("download_url"))=="www.seongnam.go.kr") for r in batch),"no non-HWP3 signature rows silently accepted":all(r.get("status")=="EXTRACTION_OR_REQUEST_UNKNOWN" or r.get("extract_ok") for r in batch),"negative evidence disabled":not output["negative_evidence_allowed"],"unsafe promotion leakage zero":not unsafe,"state written":STATE.exists() and STATE.stat().st_size>0,"output written":OUT.exists() and OUT.stat().st_size>0}
    print(); print("VALIDATION")
    for k,v in vals.items(): print(f"{k}: {v}")
    print("all_pass:",all(vals.values()))
    if not all(vals.values()): raise AssertionError("HWP3 UQQ700 bounded batch search failed")


if __name__=="__main__": main()
