# -*- coding: utf-8 -*-
from __future__ import annotations

import json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_detail_session_identity_forensic.json'
LIST='https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp'
DETAIL='https://www.eum.go.kr/web/gs/gv/gvGosiDet.jsp'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
SAMPLES=['638968','117916','117520']
MAX=12*1024*1024


def fetch(s,url,params=None,referer=None):
    try:
        headers={}
        if referer: headers['Referer']=referer
        r=s.get(url,params=params,headers=headers,timeout=25,stream=True,allow_redirects=True)
        b=bytearray(); ov=False
        try:
            for c in r.iter_content(65536):
                if not c: continue
                if len(b)+len(c)>MAX: ov=True; break
                b.extend(c)
        finally:r.close()
        return {'state':'HTTP_RESPONSE_CAPTURED' if not ov else 'TECHNICAL_REQUEST_UNKNOWN','http':r.status_code,'url':str(r.url),'body':bytes(b),'error':'RESPONSE_SIZE_LIMIT_EXCEEDED' if ov else None}
    except requests.RequestException as e:
        return {'state':'TECHNICAL_REQUEST_UNKNOWN','http':None,'url':url,'body':b'','error':f'{type(e).__name__}: {e}'}

def dec(b):
    for enc in ('euc-kr','cp949','utf-8'):
        try:return b.decode(enc),enc
        except UnicodeDecodeError:pass
    return b.decode('euc-kr',errors='ignore'),'euc-kr-ignore'

def inspect(seq,r):
    text,enc=dec(r['body'])
    return {
        'state':r['state'],'http':r['http'],'final_url':r['url'],'encoding':enc,'byte_length':len(r['body']),
        'seq_identity':(f'seq={seq}' in r['url']) or (seq in text),
        'download_marker_count':text.lower().count('download('),
        'download_zip_marker_count':text.lower().count('downloadzip.jsp'),
        'attachment_word_count':sum(text.count(x) for x in ['첨부','다운로드','.pdf','.hwp','.hwpx']),
        'abnormal_access_marker':bool(re.search(r'비정상\s*접근|잘못된\s*접근|접근이\s*제한|alert\s*\(',text,re.I)),
        'form_frm_marker':bool(re.search(r'<form\b[^>]*(?:name|id)=["\']frm["\']',text,re.I)),
        'title_marker':bool(re.search(r'<title[^>]*>[\s\S]*?토지이음',text,re.I)),
        'error':r['error'],
    }

def new_session():
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'});return s

def main():
    print('='*60);print('EUM GOSI DETAIL SESSION/IDENTITY FORENSIC - S183');print('='*60)
    print('Attachment download: DISABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    rows=[]
    for seq in SAMPLES:
        cold_s=new_session(); cold=inspect(seq,fetch(cold_s,DETAIL,{'seq':seq}))
        warm_s=new_session(); pre=fetch(warm_s,LIST); warm=inspect(seq,fetch(warm_s,DETAIL,{'seq':seq},LIST))
        row={'seq':seq,'preflight_http':pre['http'],'preflight_state':pre['state'],'cold':cold,'warm':warm,'warm_cookie_names':sorted(c.name for c in warm_s.cookies)};rows.append(row)
        print('SEQ:',seq)
        print('  COLD | HTTP:',cold['http'],'| BYTES:',cold['byte_length'],'| IDENTITY:',cold['seq_identity'],'| DOWNLOAD:',cold['download_marker_count'],'| ZIP:',cold['download_zip_marker_count'],'| FORM:',cold['form_frm_marker'],'| ABNORMAL:',cold['abnormal_access_marker'])
        print('  WARM | PREFLIGHT:',pre['http'],'| HTTP:',warm['http'],'| BYTES:',warm['byte_length'],'| IDENTITY:',warm['seq_identity'],'| DOWNLOAD:',warm['download_marker_count'],'| ZIP:',warm['download_zip_marker_count'],'| FORM:',warm['form_frm_marker'],'| ABNORMAL:',warm['abnormal_access_marker'],'| COOKIES:',row['warm_cookie_names'])
    tech=sum(1 for x in rows for mode in ('cold','warm') if x[mode]['state']=='TECHNICAL_REQUEST_UNKNOWN')+sum(1 for x in rows if x['preflight_state']=='TECHNICAL_REQUEST_UNKNOWN')
    warm_identity=sum(1 for x in rows if x['warm']['seq_identity'])
    warm_download=sum(1 for x in rows if x['warm']['download_marker_count']>0 or x['warm']['download_zip_marker_count']>0)
    out={'step':'STEP 17-21-C-16-8-T-79-S183','target_name':'개발밀도관리구역','standard_code':'UQQ700','results':rows,'summary':{'sample_count':len(rows),'technical_unknown_count':tech,'warm_identity_qualified_count':warm_identity,'warm_attachment_marker_count':warm_download,'semantic_state':'EUM_DETAIL_SESSION_IDENTITY_FORENSIC_CAPTURED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'attachment_download_executed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'sample exact':len(rows)==len(SAMPLES),'technical unknown zero':tech==0,'attachment download disabled':not out['attachment_download_executed'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()): raise AssertionError('S183 EUM detail session identity forensic failed')
if __name__=='__main__':main()
