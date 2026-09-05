# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
SRC=BASE/'law_data'/'output'/'development_density_management_area_national_archives_uqq700_bounded_candidate_search.json'
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_uqq700_related_candidate_detail_reconciliation.json'
SEARCH='https://www.archives.go.kr/next/newsearch/searchTotalUp.do'
DETAIL='https://www.archives.go.kr/next/newsearch/detailInfo.do'
UA='Mozilla/5.0'; MAX=8*1024*1024
DIRECT_TERMS=['개발밀도관리구역','개발밀도 관리구역','UQQ700']
RELATED_TERM='개발밀도'
SEONGNAM_TERMS=['성남시','성남']
NOTICE_TERMS=['고시','지정','도시관리계획','결정','변경','해제']


def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def fetch(s,c):
    data={k:c[k] for k in ['rc_code','rc_rfile_no','rc_ritem_no']}
    try:
        r=s.post(DETAIL,data=data,headers={'Referer':SEARCH,'Origin':'https://www.archives.go.kr'},timeout=25,stream=True,allow_redirects=True);b=bytearray();ov=False
        try:
            for chunk in r.iter_content(65536):
                if not chunk:continue
                if len(b)+len(chunk)>MAX:ov=True;break
                b.extend(chunk)
        finally:r.close()
        text,encoding=dec(bytes(b))
        return {'state':'HTTP_RESPONSE_CAPTURED' if not ov else 'TECHNICAL_REQUEST_UNKNOWN','http':r.status_code,'final_url':str(r.url),'byte_length':len(b),'encoding':encoding,'text':text,'error':'RESPONSE_SIZE_LIMIT_EXCEEDED' if ov else None}
    except requests.RequestException as e:return {'state':'TECHNICAL_REQUEST_UNKNOWN','http':None,'final_url':DETAIL,'byte_length':0,'encoding':None,'text':'','error':f'{type(e).__name__}: {e}'}

def context(text,term,radius=300,limit=8):
    out=[];start=0
    while len(out)<limit:
        i=text.find(term,start)
        if i<0:break
        frag=text[max(0,i-radius):min(len(text),i+len(term)+radius)]
        frag=re.sub(r'\s+',' ',frag).strip()
        if frag not in out:out.append(frag)
        start=i+len(term)
    return out

def main():
    print('='*60);print('NATIONAL ARCHIVES UQQ700 RELATED CANDIDATE DETAIL RECONCILIATION - S195');print('='*60)
    print('Negative evidence: DISABLED');print('Legal absence inference: DISABLED');print('UQQ700 resolution: UNKNOWN')
    src=json.loads(SRC.read_text(encoding='utf-8')); candidates=src.get('candidates',[])
    if len(candidates)!=4: raise AssertionError(f'expected 4 S194 candidates, got {len(candidates)}')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[];tech=0
    for c in candidates:
        r=fetch(s,c);plain=clean(r['text']); direct={t:plain.count(t) for t in DIRECT_TERMS}; related=plain.count(RELATED_TERM); seongnam=sum(plain.count(t) for t in SEONGNAM_TERMS); notice=sum(plain.count(t) for t in NOTICE_TERMS)
        if r['state']=='TECHNICAL_REQUEST_UNKNOWN':
            state='TECHNICAL_REQUEST_UNKNOWN';tech+=1
        elif any(direct.values()): state='DIRECT_CANDIDATE_REQUIRE_REVIEW'
        elif related>0 and seongnam>0 and notice>0: state='RELATED_CANDIDATE_REQUIRE_REVIEW'
        else: state='CONTEXTUAL_NON_UQQ700'
        row={'identity':{k:c[k] for k in ['rc_code','rc_rfile_no','rc_ritem_no']},'title':c.get('title'),'institution':c.get('institution'),'year':c.get('year'),'manage_no':c.get('manage_no'),'state':state,'http':r['http'],'byte_length':r['byte_length'],'encoding':r['encoding'],'direct_counts':direct,'related_count':related,'seongnam_context_count':seongnam,'notice_context_count':notice,'related_contexts':context(plain,RELATED_TERM),'text_sample':plain[:2500],'error':r['error']};results.append(row)
        print('TITLE:',c.get('title'),'| STATE:',state,'| HTTP:',r['http'],'| BYTES:',r['byte_length'],'| DIRECT:',direct,'| RELATED:',related,'| SEONGNAM:',seongnam,'| NOTICE:',notice)
        for x in row['related_contexts'][:4]:print('  CONTEXT:',x)
    review=sum(x['state'] in {'DIRECT_CANDIDATE_REQUIRE_REVIEW','RELATED_CANDIDATE_REQUIRE_REVIEW'} for x in results);non=sum(x['state']=='CONTEXTUAL_NON_UQQ700' for x in results)
    semantic='NATIONAL_ARCHIVES_RELATED_CANDIDATES_CONTEXTUALLY_RECONCILED_NON_UQQ700' if non==len(results) else ('NATIONAL_ARCHIVES_RELATED_CANDIDATE_REVIEW_REQUIRED' if review else 'NATIONAL_ARCHIVES_RELATED_CANDIDATE_TECHNICAL_UNKNOWN')
    out={'step':'STEP 17-21-C-16-8-T-91-S195','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','results':results,'summary':{'candidate_count':len(results),'contextual_non_uqq700_count':non,'review_remaining_count':review,'technical_unknown_count':tech,'semantic_state':semantic,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'candidate exact':len(results)==4,'technical unknown zero':tech==0,'all reconciled non uqq700':non==4,'review remaining zero':review==0,'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S195 National Archives related candidate detail reconciliation failed')
if __name__=='__main__':main()
