# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_detail_representation_qualification.json'
DETAIL='https://www.eum.go.kr/web/gs/gv/gvGosiDet.jsp'
HOST='www.eum.go.kr'; UA='Mozilla/5.0'; MAX=12*1024*1024
SAMPLES=[('638968','RECENT_2026'),('117916','LEGACY_1984'),('117520','LEGACY_1980S')]
TARGETS=['개발밀도관리구역','개발밀도 관리구역','개발밀도','UQQ700']

def get(s,seq):
    try:
        r=s.get(DETAIL,params={'seq':seq},timeout=25,stream=True,allow_redirects=True); b=bytearray(); ov=False
        try:
            for c in r.iter_content(65536):
                if not c: continue
                if len(b)+len(c)>MAX: ov=True; break
                b.extend(c)
        finally:r.close()
        return {'state':'HTTP_RESPONSE_CAPTURED' if not ov else 'TECHNICAL_REQUEST_UNKNOWN','http':r.status_code,'url':str(r.url),'body':bytes(b),'error':'RESPONSE_SIZE_LIMIT_EXCEEDED' if ov else None}
    except requests.RequestException as e:return {'state':'TECHNICAL_REQUEST_UNKNOWN','http':None,'url':DETAIL,'body':b'','error':f'{type(e).__name__}: {e}'}

def dec(b):
    for enc in ('euc-kr','cp949','utf-8'):
        try:return b.decode(enc),enc
        except UnicodeDecodeError:pass
    return b.decode('euc-kr',errors='ignore'),'euc-kr-ignore'

def clean(t):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>',' ',t,flags=re.I))).strip()

def links(t,base):
    out=[]
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',t,re.I):
        u=urljoin(base,html.unescape(m.group(1))); label=clean(m.group(2))[:200]
        low=(u+' '+label).lower()
        if any(x in low for x in ['file','down','attach','pdf','.hwp','.hwpx','preview']): out.append({'url':u,'label':label})
    return out[:30]

def main():
    print('='*60);print('EUM GOSI DETAIL REPRESENTATION QUALIFICATION - S177');print('='*60)
    print('Bulk detail crawl: DISABLED');print('OCR: DISABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    rows=[]
    for seq,label in SAMPLES:
        r=get(s,seq); text,enc=dec(r['body']); plain=clean(text); at=links(text,r['url'])
        term={x:plain.count(x) for x in TARGETS}; ident=(f'seq={seq}' in r['url']) or (seq in text)
        row={'seq':seq,'sample_class':label,'state':r['state'],'http':r['http'],'encoding':enc,'identity_ok':ident,'plain_text_length':len(plain),'attachment_like_link_count':len(at),'attachment_like_links':at,'target_counts':term,'error':r['error']}
        rows.append(row);print('SEQ:',seq,'| CLASS:',label,'| STATE:',r['state'],'| HTTP:',r['http'],'| IDENTITY:',ident,'| TEXT_LEN:',len(plain),'| ATTACH_LINKS:',len(at),'| TARGET_COUNTS:',term)
    tech=sum(x['state']=='TECHNICAL_REQUEST_UNKNOWN' for x in rows)
    qualified=sum(x['state']=='HTTP_RESPONSE_CAPTURED' and x['http']==200 and x['identity_ok'] for x in rows)
    text_capable=sum(x['plain_text_length']>=500 for x in rows)
    attach_capable=sum(x['attachment_like_link_count']>0 for x in rows)
    out={'step':'STEP 17-21-C-16-8-T-73-S177','target_name':'개발밀도관리구역','standard_code':'UQQ700','samples':rows,'summary':{'sample_count':len(rows),'detail_identity_qualified_count':qualified,'html_text_capable_count':text_capable,'attachment_surface_observed_count':attach_capable,'technical_unknown_count':tech,'semantic_state':'EUM_GOSI_DETAIL_REPRESENTATION_QUALIFIED' if qualified==len(rows) else 'EUM_GOSI_DETAIL_REPRESENTATION_NOT_YET_QUALIFIED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'bulk_detail_crawl_executed':False,'ocr_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'sample request exact':len(rows)==len(SAMPLES),'technical unknown zero':tech==0,'all detail identities qualified':qualified==len(rows),'bulk detail crawl disabled':not out['bulk_detail_crawl_executed'],'OCR disabled':not out['ocr_allowed'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S177 EUM detail representation qualification failed')
if __name__=='__main__':main()
