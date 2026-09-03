# -*- coding: utf-8 -*-
"""S135: bounded HWP extraction qualification for the 48 PRE-HWP5 current-snapshot rows.

Input is S134-R1. Download exactly one official HWP attachment per row, classify HWP generation,
read HWP5 flags when applicable, and attempt ordinary text extraction using a local no-Crypto HWP5
parser. HWP3 is classified but not parsed in this stage. Distribution/password-protected HWP5 is left
technical unknown. No OCR, no target-term scan, no negative evidence, and no SITE/runtime promotion.
"""
from __future__ import annotations

import io
import json
import re
import struct
import zlib
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import olefile
import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'law_data' / 'output'
S134 = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_attachment_format_inventory.json'
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_hwp_extraction_qualification.json'

EXPECTED = 48
DOWNLOAD = 'https://www.seongnam.go.kr/bbs010308/getFile'
HOST = 'www.seongnam.go.kr'
BBS_CRT_SN = '16002'
TIMEOUT = 45
MAX_BYTES = 64 * 1024 * 1024
RECORD_LIMIT = 2_000_000
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
OLE_SIG = bytes.fromhex('D0CF11E0A1B11AE1')


def norm(v): return re.sub(r'\s+', ' ', str(v or '')).strip()

def host(url):
    try: return (urlparse(url).hostname or '').lower()
    except Exception: return ''

def bounded_download(session, params):
    r=session.get(DOWNLOAD,params=params,timeout=TIMEOUT,stream=True,allow_redirects=True)
    buf=bytearray(); overflow=False
    try:
        for chunk in r.iter_content(65536):
            if not chunk: continue
            if len(buf)+len(chunk)>MAX_BYTES: overflow=True; break
            buf.extend(chunk)
    finally: r.close()
    return r.status_code,str(r.url),bytes(buf),overflow,r.headers.get('Content-Type','')

def classify_signature(data):
    if data.startswith(OLE_SIG): return 'HWP5'
    if data.startswith(b'HWP Document File'): return 'HWP3'
    return 'UNKNOWN'

def parse_record_header(buf,pos):
    if pos+4>len(buf): return None
    v=struct.unpack_from('<I',buf,pos)[0]
    tag=v & 0x3FF; level=(v>>10)&0x3FF; size=(v>>20)&0xFFF; head=4
    if size==0xFFF:
        if pos+8>len(buf): return None
        size=struct.unpack_from('<I',buf,pos+4)[0]; head=8
    return tag,level,size,head

def sanitize_para_text(payload):
    if len(payload)<2: return ''
    try: s=payload.decode('utf-16le',errors='ignore')
    except Exception: return ''
    out=[]
    for ch in s:
        o=ord(ch)
        if ch in '\r\n\t': out.append(' ')
        elif o>=32 and o not in range(0x7F,0xA0): out.append(ch)
    return re.sub(r'\s+',' ',''.join(out)).strip()

def parse_records_text(data):
    pos=0; count=0; parts=[]
    while pos < len(data):
        h=parse_record_header(data,pos)
        if h is None: break
        tag,level,size,head=h
        end=pos+head+size
        if end>len(data): break
        count+=1
        if count>RECORD_LIMIT: raise RuntimeError(f'HWP5 record ceiling exceeded: {RECORD_LIMIT}')
        if tag==67:
            t=sanitize_para_text(data[pos+head:end])
            if t: parts.append(t)
        pos=end
    return '\n'.join(parts),count

def extract_hwp5(data):
    ole=olefile.OleFileIO(io.BytesIO(data))
    try:
        if not ole.exists('FileHeader'): raise RuntimeError('FileHeader missing')
        fh=ole.openstream('FileHeader').read()
        if len(fh)<40: raise RuntimeError('FileHeader too short')
        flags=struct.unpack_from('<I',fh,36)[0]
        compressed=bool(flags & 0x01); password=bool(flags & 0x02); distribution=bool(flags & 0x04)
        meta={'compressed':compressed,'password':password,'distribution':distribution,'flags':flags}
        if password: return False,'',0,0,meta,'password protected HWP5'
        if distribution: return False,'',0,0,meta,'distribution HWP5 requires optional decryption path'
        sections=[]
        for entry in ole.listdir(streams=True,storages=False):
            if len(entry)==2 and entry[0]=='BodyText' and re.fullmatch(r'Section\d+',entry[1] or ''):
                sections.append((int(entry[1][7:]),entry))
        sections.sort()
        texts=[]; records=0
        for _,entry in sections:
            raw=ole.openstream(entry).read()
            if compressed:
                try: raw=zlib.decompress(raw,-15)
                except Exception as exc: raise RuntimeError(f'raw-deflate decompress failed: {exc!r}')
            txt,cnt=parse_records_text(raw); records+=cnt
            if txt: texts.append(txt)
        return True,'\n'.join(texts),len(sections),records,meta,''
    finally: ole.close()

def main():
    print('='*60)
    print('SEONGNAM LEGACY GAZETTE PRE-HWP5 HWP EXTRACTION QUALIFICATION - S135')
    print('='*60)
    print('Crypto dependency: NOT REQUIRED FOR ORDINARY HWP5')
    print('HWP3 parsing: DISABLED IN THIS STAGE')
    print('Distribution/password decryption: DISABLED')
    print('OCR: DISABLED')
    print('Target-term scan: DISABLED')
    print('Negative evidence: DISABLED')

    src=json.loads(S134.read_text(encoding='utf-8'))
    rows=src.get('results') or []
    if len(rows)!=EXPECTED: raise AssertionError(f'S134 row count mismatch: {len(rows)}')
    if any(len(r.get('attachments') or [])!=1 or (r['attachments'][0].get('extension') or '').lower()!='hwp' for r in rows):
        raise AssertionError('S134 expected exactly one HWP attachment per row')

    session=requests.Session(); session.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[]; request_count=0; total_bytes=0; total_text=0
    for r in rows:
        pst=norm(r.get('pstSn')); a=r['attachments'][0]
        hs,hu,data,overflow,ct=bounded_download(session,{'bbsCrtSn':BBS_CRT_SN,'pstSn':pst,'fileNo':norm(a.get('fileNo'))}); request_count+=1; total_bytes+=len(data)
        sig=classify_signature(data) if hs==200 and not overflow else 'UNKNOWN'
        extract_ok=False; text_len=0; sections=0; records=0; flags={}; error=''; parser='NONE'
        if hs!=200: error=f'HTTP {hs}'
        elif overflow: error='download byte ceiling exceeded'
        elif sig=='HWP5':
            parser='HWP5_ORDINARY_INTERNAL_NO_CRYPTO_HIGH_LIMIT_2000000'
            try:
                extract_ok,text,sections,records,flags,error=extract_hwp5(data); text_len=len(text); total_text+=text_len
            except Exception as exc: error=repr(exc)
        elif sig=='HWP3':
            parser='HWP3_NOT_PARSED_IN_S135'; error='HWP3 parser qualification required'
        else: error='unknown HWP signature'

        if extract_ok and text_len>0: state='HWP_TEXT_EXTRACTION_QUALIFIED'
        elif sig=='HWP3': state='HWP3_EXTRACTION_FALLBACK_REQUIRED'
        elif sig=='HWP5' and flags.get('distribution'): state='DISTRIBUTION_HWP5_TECHNICAL_UNKNOWN'
        elif sig=='HWP5' and flags.get('password'): state='PASSWORD_PROTECTED_HWP5_TECHNICAL_UNKNOWN'
        else: state='EXTRACTION_OR_REQUEST_UNKNOWN'
        rec={'pstSn':pst,'gazette_number':r.get('gazette_number'),'date':r.get('date'),'filename':a.get('filename'),'fileNo':a.get('fileNo'),'http':hs,'download_url':hu,'official_host':host(hu)==HOST,'bytes':len(data),'overflow':overflow,'content_type':ct,'signature':sig,'parser':parser,'flags':flags,'section_count':sections,'record_count':records,'extract_ok':extract_ok,'text_length':text_len,'error':error,'state':state}
        results.append(rec)
        print('GAZETTE:',rec['gazette_number'],'| pstSn:',pst,'| HTTP:',hs,'| BYTES:',len(data),'| SIG:',sig,'| STATE:',state,'| TEXT_LEN:',text_len)

    sig_counts=Counter(r['signature'] for r in results); state_counts=Counter(r['state'] for r in results)
    out={'step':'STEP 17-21-C-16-8-T-36-S135','target_name':'개발밀도관리구역','standard_code':'UQQ700','summary':{'input_row_count':len(results),'request_count':request_count,'signature_counts':dict(sig_counts),'state_counts':dict(state_counts),'qualified_text_extraction_count':state_counts.get('HWP_TEXT_EXTRACTION_QUALIFIED',0),'hwp3_fallback_required_count':state_counts.get('HWP3_EXTRACTION_FALLBACK_REQUIRED',0),'distribution_hwp5_technical_unknown_count':state_counts.get('DISTRIBUTION_HWP5_TECHNICAL_UNKNOWN',0),'password_hwp5_technical_unknown_count':state_counts.get('PASSWORD_PROTECTED_HWP5_TECHNICAL_UNKNOWN',0),'other_technical_unknown_count':state_counts.get('EXTRACTION_OR_REQUEST_UNKNOWN',0),'total_downloaded_bytes':total_bytes,'total_extracted_text_length':total_text,'semantic_state':'PRE_HWP5_HWP_EXTRACTION_QUALIFICATION_CAPTURED','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'results':results,'hwp3_parsing_executed':False,'distribution_decryption_executed':False,'password_decryption_executed':False,'ocr_executed':False,'target_term_scan_executed':False,'candidate_promotion_allowed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'input row count exact':len(results)==EXPECTED,'request budget exact':request_count==EXPECTED,'official hosts only':all(r['official_host'] for r in results),'download ceilings respected':all(not r['overflow'] for r in results),'HWP3 parsing disabled':not out['hwp3_parsing_executed'],'distribution decryption disabled':not out['distribution_decryption_executed'],'password decryption disabled':not out['password_decryption_executed'],'OCR disabled':not out['ocr_executed'],'target-term scan disabled':not out['target_term_scan_executed'],'candidate promotion disabled':not out['candidate_promotion_allowed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nSUMMARY')
    for k,v in out['summary'].items(): print(f'{k}: {v}')
    print('Output:',OUT)
    print('\nVALIDATION')
    for k,v in vals.items(): print(f'{k}: {v}')
    print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S135 PRE-HWP5 HWP extraction qualification failed')

if __name__=='__main__': main()
