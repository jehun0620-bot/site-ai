# -*- coding: utf-8 -*-
"""S137: bounded structural probe for legacy HWP3 attachments.

Uses the same first/median/last HWP3 samples as S136. The goal is not text extraction yet, but to
identify stable HWP3 header markers, plausible paragraph/text-bearing regions, and record-like length
fields through conservative binary inspection. No target-term scan, no OCR, no decryption, no legal
negative evidence, and no SITE/runtime promotion.
"""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE=Path(__file__).resolve().parent.parent
OUT_DIR=BASE/'law_data'/'output'
S135=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_hwp_extraction_qualification.json'
OUT=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_hwp3_structure_probe.json'
DOWNLOAD='https://www.seongnam.go.kr/bbs010308/getFile'
HOST='www.seongnam.go.kr'
BBS_CRT_SN='16002'
TIMEOUT=45
MAX_BYTES=64*1024*1024
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
MAGIC=b'HWP Document File'


def norm(v): return re.sub(r'\s+',' ',str(v or '')).strip()

def host(url):
    try:return (urlparse(url).hostname or '').lower()
    except Exception:return ''

def download(session,pst,file_no):
    r=session.get(DOWNLOAD,params={'bbsCrtSn':BBS_CRT_SN,'pstSn':pst,'fileNo':file_no},timeout=TIMEOUT,stream=True,allow_redirects=True)
    buf=bytearray(); overflow=False
    try:
        for chunk in r.iter_content(65536):
            if not chunk: continue
            if len(buf)+len(chunk)>MAX_BYTES: overflow=True; break
            buf.extend(chunk)
    finally:r.close()
    return r.status_code,str(r.url),bytes(buf),overflow,r.headers.get('Content-Type','')

def u16(data,off):
    if off+2>len(data): return None
    return struct.unpack_from('<H',data,off)[0]

def u32(data,off):
    if off+4>len(data): return None
    return struct.unpack_from('<I',data,off)[0]

def ascii_runs(data,min_len=6,max_items=80):
    out=[]
    for m in re.finditer(rb'[\x20-\x7e]{%d,}'%min_len,data):
        s=m.group().decode('ascii',errors='ignore')
        out.append({'offset':m.start(),'length':len(s),'text':s[:200]})
        if len(out)>=max_items: break
    return out

def utf16_hangul_runs(data,min_chars=4,max_items=80):
    out=[]
    # test both byte parities and retain runs dominated by Hangul/printable Korean punctuation
    for parity in (0,1):
        start=parity
        usable=data[start:len(data)-((len(data)-start)%2)]
        try:s=usable.decode('utf-16le',errors='ignore')
        except Exception:continue
        for m in re.finditer(r'[가-힣][가-힣0-9A-Za-z\s.,()·ㆍ:;\-]{%d,}'%(min_chars-1),s):
            txt=norm(m.group())
            if len(txt)<min_chars: continue
            # approximate byte offset for forensic localization only
            off=start+m.start()*2
            out.append({'parity':parity,'offset_approx':off,'char_length':len(txt),'text':txt[:200]})
            if len(out)>=max_items: return out
    return out

def length_field_hits(data):
    # Inventory small/medium little-endian lengths whose following bytes show plausible Korean UTF-16LE.
    hits=[]
    limit=min(len(data)-8,2_000_000)
    for off in range(32,limit,2):
        n=u16(data,off)
        if not n or n<4 or n>4096: continue
        byte_len=n*2
        end=off+2+byte_len
        if end>len(data): continue
        block=data[off+2:end]
        try:s=block.decode('utf-16le',errors='ignore')
        except Exception:continue
        hang=sum(1 for ch in s if '\uac00'<=ch<='\ud7a3')
        printable=sum(1 for ch in s if ch.isprintable() or ch in '\r\n\t')
        if hang>=4 and printable/max(1,len(s))>=0.75:
            text=norm(''.join(ch if (ch.isprintable() or ch in '\r\n\t') else ' ' for ch in s))
            hits.append({'offset':off,'u16_length':n,'hangul_count':hang,'printable_ratio':round(printable/max(1,len(s)),4),'text':text[:220]})
            if len(hits)>=60: break
    return hits

def main():
    print('='*60)
    print('SEONGNAM LEGACY GAZETTE PRE-HWP5 HWP3 STRUCTURE PROBE - S137')
    print('='*60)
    print('Scope: 3 bounded HWP3 samples')
    print('Target-term scan: DISABLED')
    print('OCR: DISABLED')
    print('Decryption: DISABLED')
    print('Negative evidence: DISABLED')

    src=json.loads(S135.read_text(encoding='utf-8'))
    rows=[r for r in (src.get('results') or []) if r.get('signature')=='HWP3']
    if len(rows)!=47: raise AssertionError(f'expected 47 HWP3 rows, got {len(rows)}')
    picks=[rows[0],rows[len(rows)//2],rows[-1]]
    session=requests.Session();session.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[]
    for r in picks:
        pst=norm(r.get('pstSn')); no=norm(r.get('fileNo'))
        hs,hu,data,overflow,ct=download(session,pst,no)
        magic_ok=data.startswith(MAGIC)
        header_hex=data[:256].hex()
        ar=ascii_runs(data[:65536])
        ur=utf16_hangul_runs(data,min_chars=5,max_items=40)
        lh=length_field_hits(data)
        state='HWP3_STRUCTURE_PROBE_CAPTURED' if hs==200 and not overflow and magic_ok else 'TECHNICAL_STRUCTURE_UNKNOWN'
        rec={'pstSn':pst,'gazette_number':r.get('gazette_number'),'filename':r.get('filename'),'http':hs,'official_host':host(hu)==HOST,'bytes':len(data),'overflow':overflow,'content_type':ct,'magic_ok':magic_ok,'header_256_hex':header_hex,'header_u16':[u16(data,o) for o in range(16,min(128,len(data)-1),2)],'header_u32':[u32(data,o) for o in range(16,min(128,len(data)-3),4)],'ascii_runs_first64k':ar,'utf16_hangul_runs':ur,'u16_length_field_hits':lh,'state':state}
        results.append(rec)
        print('GAZETTE:',rec['gazette_number'],'| pstSn:',pst,'| MAGIC:',magic_ok,'| UTF16_RUNS:',len(ur),'| LEN_HITS:',len(lh),'| STATE:',state)
        for item in ur[:5]: print(' UTF16_RUN:',item)
        for item in lh[:5]: print(' LEN_HIT:',item)

    out={'step':'STEP 17-21-C-16-8-T-36-S137','target_name':'개발밀도관리구역','standard_code':'UQQ700','summary':{'hwp3_input_count':47,'sample_count':len(results),'structure_probe_success_count':sum(r['state']=='HWP3_STRUCTURE_PROBE_CAPTURED' for r in results),'technical_unknown_count':sum(r['state']!='HWP3_STRUCTURE_PROBE_CAPTURED' for r in results),'semantic_state':'PRE_HWP5_HWP3_STRUCTURE_PROBE_CAPTURED','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'results':results,'target_term_scan_executed':False,'ocr_executed':False,'decryption_executed':False,'candidate_promotion_allowed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'47 HWP3 source rows':len(rows)==47,'sample count exact':len(results)==3,'official hosts only':all(r['official_host'] for r in results),'download ceilings respected':all(not r['overflow'] for r in results),'HWP3 magic exact':all(r['magic_ok'] for r in results),'target-term scan disabled':not out['target_term_scan_executed'],'OCR disabled':not out['ocr_executed'],'decryption disabled':not out['decryption_executed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nSUMMARY')
    for k,v in out['summary'].items(): print(f'{k}: {v}')
    print('Output:',OUT)
    print('\nVALIDATION')
    for k,v in vals.items(): print(f'{k}: {v}')
    print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S137 HWP3 structure probe failed')

if __name__=='__main__': main()
