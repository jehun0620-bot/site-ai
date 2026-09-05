# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_detail_positive_control.json'
SEARCH='https://www.archives.go.kr/next/newsearch/searchTotalUp.do'
DETAIL='https://www.archives.go.kr/next/newsearch/detailInfo.do'
UA='Mozilla/5.0'
MAX=8*1024*1024
SAMPLES=[
    {'title':'성남시 도로명주소 안내도','rc_code':'1310377','rc_rfile_no':'201909051836','rc_ritem_no':'000000000001'},
    {'title':'성남시 고령친화도시 조성 연구','rc_code':'1310377','rc_rfile_no':'202110509952','rc_ritem_no':'000000000001'},
]

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def fetch_detail(s,sample):
    data={'rc_code':sample['rc_code'],'rc_rfile_no':sample['rc_rfile_no'],'rc_ritem_no':sample['rc_ritem_no']}
    try:
        r=s.post(DETAIL,data=data,headers={'Referer':SEARCH,'Origin':'https://www.archives.go.kr'},timeout=25,stream=True,allow_redirects=True)
        b=bytearray();ov=False
        try:
            for c in r.iter_content(65536):
                if not c:continue
                if len(b)+len(c)>MAX:ov=True;break
                b.extend(c)
        finally:r.close()
        text,encoding=dec(bytes(b))
        return {'state':'HTTP_RESPONSE_CAPTURED' if not ov else 'TECHNICAL_REQUEST_UNKNOWN','http':r.status_code,'final_url':str(r.url),'byte_length':len(b),'encoding':encoding,'text':text,'error':'RESPONSE_SIZE_LIMIT_EXCEEDED' if ov else None}
    except requests.RequestException as e:return {'state':'TECHNICAL_REQUEST_UNKNOWN','http':None,'final_url':DETAIL,'byte_length':0,'encoding':None,'text':'','error':f'{type(e).__name__}: {e}'}

def main():
    print('='*60);print('NATIONAL ARCHIVES DETAIL POSITIVE CONTROL - S193');print('='*60)
    print('Endpoint:',DETAIL);print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    pre=s.get(SEARCH,params={'query_type':'keyword','is_detail':'yes','upside_query':'성남시','keyword':'성남시','srchinit':'ritem'},timeout=25)
    results=[]
    for sample in SAMPLES:
        r=fetch_detail(s,sample);text=r['text'];plain=clean(text)
        identity_hits={k:(v in text or v in plain) for k,v in [('rc_code',sample['rc_code']),('rc_rfile_no',sample['rc_rfile_no']),('rc_ritem_no',sample['rc_ritem_no'])]}
        title_hit=sample['title'] in plain or sample['title'] in text
        info_markers={k:(k in plain) for k in ['생산기관','생산연도','관리번호','기록물','원문']}
        error_marker=bool(re.search(r'상세\s*정보가\s*존재하지|오류|에러|잘못된\s*접근',plain,re.I))
        qualified=r['http']==200 and r['byte_length']>0 and not error_marker and (title_hit or any(identity_hits.values()) or any(info_markers.values()))
        state='DETAIL_POSITIVE_CONTROL_QUALIFIED' if qualified else ('TECHNICAL_REQUEST_UNKNOWN' if r['state']=='TECHNICAL_REQUEST_UNKNOWN' else 'DETAIL_POSITIVE_CONTROL_NOT_RESOLVED')
        row={'title':sample['title'],'identity':{k:sample[k] for k in ['rc_code','rc_rfile_no','rc_ritem_no']},'state':state,'http':r['http'],'final_url':r['final_url'],'byte_length':r['byte_length'],'encoding':r['encoding'],'title_hit':title_hit,'identity_hits':identity_hits,'info_markers':info_markers,'error_marker':error_marker,'text_sample':plain[:2500],'error':r['error']};results.append(row)
        print('TITLE:',sample['title'],'| STATE:',state,'| HTTP:',r['http'],'| BYTES:',r['byte_length'],'| TITLE_HIT:',title_hit,'| IDENTITY_HITS:',identity_hits,'| INFO:',info_markers,'| ERROR_MARKER:',error_marker)
        print('  TEXT_SAMPLE:',plain[:1200])
    q=sum(x['state']=='DETAIL_POSITIVE_CONTROL_QUALIFIED' for x in results);tech=sum(x['state']=='TECHNICAL_REQUEST_UNKNOWN' for x in results)
    out={'step':'STEP 17-21-C-16-8-T-89-S193','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','results':results,'summary':{'sample_count':len(results),'qualified_count':q,'technical_unknown_count':tech,'semantic_state':'NATIONAL_ARCHIVES_DETAIL_CONTRACT_QUALIFIED' if q==len(results) else 'NATIONAL_ARCHIVES_DETAIL_CONTRACT_PARTIAL','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'preflight 200':pre.status_code==200,'sample exact':len(results)==len(SAMPLES),'technical unknown zero':tech==0,'all qualified':q==len(results),'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S193 National Archives detail positive control failed')
if __name__=='__main__':main()
