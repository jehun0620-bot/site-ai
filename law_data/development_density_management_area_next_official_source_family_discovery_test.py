# -*- coding: utf-8 -*-
from __future__ import annotations

import json, re
from pathlib import Path
from urllib.parse import urlparse
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_next_official_source_family_discovery.json'
UA='Mozilla/5.0'

# Discovery only. These are official entry surfaces, not UQQ700 evidence.
SEEDS=[
    {'family':'NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY','name':'국가법령정보센터 자치법규','url':'https://www.law.go.kr/ordinSc.do'},
    {'family':'GYEONGGI_OFFICIAL_RECORD','name':'경기도 공식 홈페이지','url':'https://www.gg.go.kr/'},
    {'family':'E_GAZETTE','name':'대한민국 전자관보','url':'https://gwanbo.go.kr/'},
]
TOKENS=['검색','자치법규','연혁','고시','공고','도보','관보','성남','법규']

def main():
    print('='*60);print('NEXT OFFICIAL HISTORICAL SOURCE FAMILY DISCOVERY - S206');print('='*60)
    print('Discovery only; candidate source != legal fact');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    rec=[]
    for seed in SEEDS:
        r0={'family':seed['family'],'name':seed['name'],'input_url':seed['url'],'official_host':urlparse(seed['url']).hostname,'http':None,'final_url':None,'final_host':None,'byte_length':0,'content_type':None,'title':None,'token_hits':{},'form_count':0,'link_count':0,'endpoint_hints':[],'technical_unknown':False,'error':None}
        try:
            r=s.get(seed['url'],timeout=30,allow_redirects=True)
            b=r.content[:8*1024*1024]; enc=r.encoding or r.apparent_encoding or 'utf-8'; t=b.decode(enc,errors='ignore')
            r0.update(http=r.status_code,final_url=str(r.url),final_host=urlparse(str(r.url)).hostname,byte_length=len(b),content_type=r.headers.get('Content-Type'),title=(re.search(r'<title[^>]*>(.*?)</title>',t,re.I|re.S).group(1).strip() if re.search(r'<title[^>]*>(.*?)</title>',t,re.I|re.S) else None),form_count=len(re.findall(r'<form\b',t,re.I)),link_count=len(re.findall(r'<a\b',t,re.I)))
            r0['token_hits']={x:(x in t) for x in TOKENS}
            hints=[]
            for m in re.finditer(r'(?:href|action)=["\']([^"\']+)["\']',t,re.I):
                u=m.group(1)
                if any(x in u.lower() for x in ['search','srch','ordin','gosi','notice','board','gazette','gwanbo','bbs']):
                    if u not in hints:hints.append(u)
                if len(hints)>=30:break
            r0['endpoint_hints']=hints
            if r.status_code!=200:r0['technical_unknown']=True
        except requests.RequestException as e:
            r0['technical_unknown']=True;r0['error']=f'{type(e).__name__}: {e}'
        rec.append(r0)
        print(f"FAMILY: {r0['family']} | HTTP: {r0['http']} | HOST: {r0['final_host']} | BYTES: {r0['byte_length']} | FORMS: {r0['form_count']} | HINTS: {len(r0['endpoint_hints'])} | UNKNOWN: {r0['technical_unknown']}")
        print('  TITLE:',r0['title']);print('  TOKENS:',r0['token_hits']);print('  ENDPOINT_HINTS:',r0['endpoint_hints'][:10])
    reachable=[x for x in rec if x['http']==200 and not x['technical_unknown']]
    # Qualification is deliberately deferred: reachability alone is insufficient.
    ranked=sorted(reachable,key=lambda x:(sum(x['token_hits'].values()),len(x['endpoint_hints']),x['form_count']),reverse=True)
    next_family=ranked[0]['family'] if ranked else None
    out={'step':'STEP 17-21-C-16-8-T-102-S206','target_name':'개발밀도관리구역','standard_code':'UQQ700','purpose':'NEXT_OFFICIAL_HISTORICAL_SOURCE_FAMILY_DISCOVERY','records':rec,'summary':{'seed_count':len(SEEDS),'http_200_count':len(reachable),'technical_unknown_count':sum(x['technical_unknown'] for x in rec),'ranked_family_order':[x['family'] for x in ranked],'next_family_for_contract_qualification':next_family,'semantic_state':'NEXT_OFFICIAL_HISTORICAL_SOURCE_FAMILY_ENTRY_SURFACES_DISCOVERED' if reachable else 'NEXT_OFFICIAL_HISTORICAL_SOURCE_FAMILY_ENTRY_SURFACES_UNRESOLVED','source_family_qualified':False,'search_contract_qualified':False,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'seed exact':len(rec)==3,'at least one reachable':len(reachable)>0,'source not prematurely qualified':not out['summary']['source_family_qualified'],'search not prematurely qualified':not out['summary']['search_contract_qualified'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S206 next official source-family discovery failed')
if __name__=='__main__':main()
