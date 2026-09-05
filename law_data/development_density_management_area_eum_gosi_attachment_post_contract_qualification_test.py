# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_attachment_post_contract_qualification.json'
DETAIL='https://www.eum.go.kr/web/gs/gv/gvGosiDet.jsp'
UA='Mozilla/5.0'; MAX=32*1024*1024
SAMPLES=['638968','117916','117520']

DL_RE=re.compile(r"javascript:download\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)",re.I)
FORM_RE=re.compile(r'<form\b([^>]*)name=["\']frm["\']([^>]*)>([\s\S]*?)</form>',re.I)
INPUT_RE=re.compile(r'<input\b([^>]*)>',re.I)
ATTR_RE=re.compile(r'([\w:-]+)\s*=\s*["\']([^"\']*)["\']',re.I)

def attrs(tag): return {k.lower():html.unescape(v) for k,v in ATTR_RE.findall(tag)}

def decode_bytes(raw: bytes) -> str:
    for enc in ('euc-kr','cp949','utf-8'):
        try:return raw.decode(enc)
        except UnicodeDecodeError:pass
    return raw.decode('euc-kr',errors='ignore')

def get_text(s,seq):
    r=s.get(DETAIL,params={'seq':seq},timeout=25); r.raise_for_status(); return decode_bytes(r.content),str(r.url)

def post_file(s,url,data,referer):
    try:
        r=s.post(url,data=data,headers={'Referer':referer,'Origin':'https://www.eum.go.kr'},timeout=30,stream=True,allow_redirects=True)
        b=bytearray(); ov=False
        try:
            for c in r.iter_content(65536):
                if not c: continue
                if len(b)+len(c)>MAX: ov=True; break
                b.extend(c)
        finally:r.close()
        raw=bytes(b); ct=r.headers.get('Content-Type') or ''; cd=r.headers.get('Content-Disposition') or ''
        return {'transport_state':'HTTP_RESPONSE_CAPTURED' if not ov else 'TECHNICAL_REQUEST_UNKNOWN','http':r.status_code,'final_url':str(r.url),'content_type':ct,'content_disposition':cd,'content_length':len(raw),'signature_hex':raw[:16].hex(),'response_text_preview':decode_bytes(raw)[:300] if ('text/' in ct.lower() or len(raw)<2048) else None,'error':'RESPONSE_SIZE_LIMIT_EXCEEDED' if ov else None}
    except requests.RequestException as e:return {'transport_state':'TECHNICAL_REQUEST_UNKNOWN','http':None,'final_url':url,'content_type':None,'content_disposition':None,'content_length':0,'signature_hex':'','response_text_preview':None,'error':f'{type(e).__name__}: {e}'}

def main():
    print('='*60);print('EUM GOSI ATTACHMENT POST CONTRACT QUALIFICATION - S181-R1');print('='*60)
    print('Binary delivery requires non-HTML response');print('Text extraction: DISABLED');print('OCR: DISABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    results=[]
    for seq in SAMPLES:
        s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
        text,detail_url=get_text(s,seq); dls=DL_RE.findall(text); fm=FORM_RE.search(text); hidden={}
        if fm:
            for tag in INPUT_RE.findall(fm.group(3)):
                a=attrs(tag); name=a.get('name'); typ=a.get('type','').lower()
                if name and typ=='hidden': hidden[name]=a.get('value','')
        if not dls:
            row={'seq':seq,'qualification_state':'ATTACHMENT_DOWNLOAD_CALL_NOT_FOUND','download_call_count':0,'hidden_fields':hidden}; results.append(row); print('SEQ:',seq,'| STATE:',row['qualification_state']); continue
        dl_url,file_id=dls[0]; target=urljoin(detail_url,html.unescape(dl_url)); payload=dict(hidden); payload['file']=html.unescape(file_id)
        r=post_file(s,target,payload,detail_url); official=(urlparse(r['final_url']).hostname or '').endswith('eum.go.kr')
        is_html='text/html' in (r['content_type'] or '').lower() or (r['signature_hex'] or '').startswith('3c68746d6c') or (r['signature_hex'] or '').startswith('3c736372697074')
        delivered=r['transport_state']=='HTTP_RESPONSE_CAPTURED' and r['http']==200 and r['content_length']>0 and official and not is_html
        state='ATTACHMENT_POST_DELIVERY_QUALIFIED' if delivered else ('TECHNICAL_REQUEST_UNKNOWN' if r['transport_state']=='TECHNICAL_REQUEST_UNKNOWN' else 'ATTACHMENT_POST_DELIVERY_NOT_RESOLVED')
        row={'seq':seq,'qualification_state':state,'download_call_count':len(dls),'download_url':target,'file_id':file_id,'hidden_fields':hidden,'official_host':official,'html_response_rejected':is_html,**r}; results.append(row)
        print('SEQ:',seq,'| STATE:',state,'| HTTP:',r['http'],'| TYPE:',r['content_type'],'| BYTES:',r['content_length'],'| SIG:',r['signature_hex']); print('  RESPONSE:',r['response_text_preview'])
    q=sum(x.get('qualification_state')=='ATTACHMENT_POST_DELIVERY_QUALIFIED' for x in results); tech=sum(x.get('qualification_state')=='TECHNICAL_REQUEST_UNKNOWN' for x in results); unresolved=len(results)-q-tech
    out={'step':'STEP 17-21-C-16-8-T-77-S181-R1','target_name':'개발밀도관리구역','standard_code':'UQQ700','results':results,'summary':{'sample_count':len(results),'qualified_count':q,'technical_unknown_count':tech,'unresolved_count':unresolved,'semantic_state':'EUM_ATTACHMENT_POST_CONTRACT_QUALIFIED' if q==len(results) else 'EUM_ATTACHMENT_POST_CONTRACT_NOT_YET_QUALIFIED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'attachment_text_extraction_executed':False,'ocr_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'sample exact':len(results)==len(SAMPLES),'technical unknown zero':tech==0,'text extraction disabled':not out['attachment_text_extraction_executed'],'OCR disabled':not out['ocr_allowed'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()): raise AssertionError('S181-R1 EUM attachment POST contract technical validation failed')
if __name__=='__main__':main()
