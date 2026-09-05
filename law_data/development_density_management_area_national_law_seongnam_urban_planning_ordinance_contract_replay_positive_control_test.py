# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_law_seongnam_urban_planning_ordinance_contract_replay_positive_control.json'
BASE_URL='https://www.law.go.kr/ordinSc.do'
LIST_URL='https://www.law.go.kr/ordinScListR.do'
UA='Mozilla/5.0'
TARGET='성남시 도시계획 조례'
MAX=8*1024*1024

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()

def fetch(s,params):
    try:
        r=s.get(LIST_URL,params=params,headers={'Referer':BASE_URL,'X-Requested-With':'XMLHttpRequest'},timeout=30,allow_redirects=True,stream=True)
        b=bytearray();ov=False
        try:
            for c in r.iter_content(65536):
                if not c:continue
                if len(b)+len(c)>MAX:ov=True;break
                b.extend(c)
        finally:r.close()
        t,e=dec(bytes(b));return {'http':r.status_code,'url':str(r.url),'body':bytes(b),'text':t,'encoding':e,'overflow':ov,'error':None,'content_type':r.headers.get('Content-Type')}
    except requests.RequestException as ex:return {'http':None,'url':LIST_URL,'body':b'','text':'','encoding':None,'overflow':False,'error':f'{type(ex).__name__}: {ex}','content_type':None}

def parse_rows(text):
    rows=[]
    # Prefer actual fOrdinListView(...) result anchors/blocks.
    for m in re.finditer(r'fOrdinListView\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']?([^,"\')]+)["\']?\s*,\s*["\']?([^,"\')]+)["\']?\s*,\s*["\']?([^,"\')]+)["\']?\s*,\s*["\']?([^,"\')]+)["\']?\s*\)',text,re.I):
        frag=text[max(0,m.start()-1200):min(len(text),m.end()+1800)]
        plain=clean(frag)
        titles=[]
        for pat in [r'<a[^>]*fOrdinListView[^>]*>([\s\S]{0,500}?)</a>',r'<span[^>]*class=["\'][^"\']*(?:title|tit)[^"\']*["\'][^>]*>([\s\S]{0,500}?)</span>',r'<strong[^>]*>([\s\S]{0,500}?)</strong>']:
            tm=re.search(pat,frag,re.I)
            if tm:
                x=clean(tm.group(1))
                if x and x not in titles:titles.append(x)
        row={'chk_id':m.group(1),'ordin_seq':m.group(2),'nw_yn':m.group(3),'mode':m.group(4),'gubun':m.group(5),'titles':titles[:5],'context':plain[:2400]}
        row['target_seen']=TARGET in plain or any(TARGET in x for x in titles)
        row['seongnam_seen']='성남시' in plain
        row['urban_planning_seen']='도시계획' in plain
        rows.append(row)
    # Deduplicate identities.
    out=[];seen=set()
    for r in rows:
        k=(r['chk_id'],r['ordin_seq'],r['nw_yn'],r['gubun'])
        if k in seen:continue
        seen.add(k);out.append(r)
    return out

def main():
    print('='*60);print('NATIONAL LAW SEONGNAM URBAN PLANNING ORDINANCE CONTRACT REPLAY POSITIVE CONTROL - S210');print('='*60)
    print('Known positive control:',TARGET);print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    pre_err=None
    try:
        pr=s.get(BASE_URL,timeout=30,allow_redirects=True);pre_http=pr.status_code
    except requests.RequestException as ex:
        pre_http=None;pre_err=f'{type(ex).__name__}: {ex}'
    # JS contract from S209: q, section=ordinNm, idxList=LsKwdNm_idx,OrdinNm_idx, p3=current(3), pg, outmax.
    cases=[
      ('CURRENT_NAME_GLOBAL',{'q':TARGET,'section':'ordinNm','idxList':'LsKwdNm_idx,OrdinNm_idx','p3':'3','p1':'','p4':'','p5':'','p6':'','p7':'','pg':'1','outmax':'50','dtlYn':'N'}),
      ('CURRENT_NAME_GLOBAL_WITH_DEFAULT_SORT',{'q':TARGET,'section':'ordinNm','idxList':'LsKwdNm_idx,OrdinNm_idx','p3':'3','p1':'','p4':'','p5':'','p6':'','p7':'','pg':'1','outmax':'50','dtlYn':'N','fsort':'21,10,31'}),
    ]
    results=[]
    for name,params in cases:
        rr=fetch(s,params);rows=parse_rows(rr['text']);pos=[x for x in rows if x['target_seen'] or (x['seongnam_seen'] and x['urban_planning_seen'])]
        rec={'case':name,'params':params,'http':rr['http'],'final_url':rr['url'],'byte_length':len(rr['body']),'encoding':rr['encoding'],'content_type':rr['content_type'],'overflow':rr['overflow'],'error':rr['error'],'row_count':len(rows),'positive_row_count':len(pos),'positive_rows':pos[:10],'rows':rows[:20]}
        results.append(rec)
        print(f"CASE: {name} | HTTP: {rr['http']} | BYTES: {len(rr['body'])} | ROWS: {len(rows)} | POSITIVE_ROWS: {len(pos)}")
        for x in pos[:5]:print('  POSITIVE:',x)
    qualified=[x for x in results if x['http']==200 and not x['overflow'] and x['error'] is None and x['positive_row_count']>0]
    best=qualified[0]['case'] if qualified else None
    technical=sum(1 for x in results if x['http']!=200 or x['overflow'] or x['error']) + (1 if pre_http!=200 else 0)
    semantic='NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_SEARCH_CONTRACT_QUALIFIED' if qualified else 'NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_SEARCH_CONTRACT_UNRESOLVED'
    out={'step':'STEP 17-21-C-16-8-T-105-S210','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY','positive_control':TARGET,'base_preflight':{'http':pre_http,'error':pre_err},'cases':results,'summary':{'case_count':len(results),'qualified_positive_control_case_count':len(qualified),'best_positive_control_case':best,'technical_unknown_count':technical,'semantic_state':semantic,'search_contract_qualified':bool(qualified),'result_identity_qualified':bool(qualified),'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'case exact':len(results)==2,'preflight 200':pre_http==200,'technical unknown zero':technical==0,'positive control resolved':bool(qualified),'search contract qualified':out['summary']['search_contract_qualified'],'result identity qualified':out['summary']['result_identity_qualified'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S210 national law Seongnam urban planning ordinance contract replay positive control failed')
if __name__=='__main__':main()
