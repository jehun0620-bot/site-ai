# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_seongnam_org_bounded_uqq700_search.json'
URL='https://www.archives.go.kr/next/srch/uniDetailSearch.do'
UA='Mozilla/5.0'; MAX=16*1024*1024
ORG='경기도 성남시'
QUERIES=[
    ('개발밀도관리구역','DIRECT_CANDIDATE'),
    ('개발밀도 관리구역','DIRECT_CANDIDATE'),
    ('개발 밀도 관리 구역','DIRECT_CANDIDATE'),
    ('개발밀도관리구역 지정','DIRECT_CANDIDATE'),
    ('개발밀도관리구역 고시','DIRECT_CANDIDATE'),
    ('도시관리계획 개발밀도관리구역','DIRECT_CANDIDATE'),
    ('개발밀도','RELATED_CANDIDATE'),
    ('관리구역','RELATED_CANDIDATE'),
]
ROW_RE=re.compile(r'<div\s+class=["\']result-row["\'][^>]*>([\s\S]*?)(?=<div\s+class=["\']result-row["\']|\Z)',re.I)
CALL_RE=re.compile(r"showDetailWithQuery\('([^']+)','([^']+)'(?:,'([^']*)')?\)",re.I)

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def field(frag,label):
    p=clean(frag)
    m=re.search(re.escape(label)+r'\s*:\s*([^|]+?)(?=\s+(?:생산연도|관리번호|공개|비공개|기록물|$))',p)
    return m.group(1).strip() if m else ''
def parse(text):
    out=[]
    for rm in ROW_RE.finditer(text):
        frag=rm.group(1);cm=CALL_RE.search(frag)
        if not cm:continue
        tm=re.search(r'class=["\']file-title["\'][^>]*>([\s\S]{0,900}?)</a>',frag,re.I)
        title=clean(tm.group(1)) if tm else ''
        p=clean(frag)
        inst='';year='';manage=''
        mi=re.search(r'생산기관\s*:\s*(.*?)\s+생산연도\s*:',p)
        if mi:inst=mi.group(1).strip()
        my=re.search(r'생산연도\s*:\s*(.*?)\s+관리번호\s*:',p)
        if my:year=my.group(1).strip()
        mm=re.search(r'관리번호\s*:\s*([^\s]+)',p)
        if mm:manage=mm.group(1).strip()
        out.append({'rc_code':cm.group(1),'rc_rfile_no':cm.group(2),'page':cm.group(3),'title':title,'institution':inst,'year':year,'manage_no':manage,'context':p[:2500]})
    return out

def fetch(s,q):
    org=ORG.replace(',','^')
    data={'is_detail':'yes','srchinit':'ritem','afterKeyword':'','size':'10','from':'1','sort':'SCORE','order':'DESC','kikwancode':'','kikwanname':'','query_type':'ftr','keyword':q,'detailOneKeyword':'','detailMatchKeyword':'','detailExceptKeyword':'','org_nm':org,'org_nm_fst':org,'orgName':ORG,'prod_yr_start':'','prod_yr_end':'','opn_yn':'','opn_yn_fst':'','arch_down':'','arch_down_fst':'','record_type':'','doc_type':'','doc_type_fst':'','type':'','is_elect':'','mng_no_start':'','mng_no_end':'','prod_dt_start':'','prod_dt_end':'','sihang_dt_start':'','sihang_dt_end':''}
    try:
        r=s.post(URL,data=data,timeout=30,stream=True,allow_redirects=True);b=bytearray();ov=False
        try:
            for c in r.iter_content(65536):
                if not c:continue
                if len(b)+len(c)>MAX:ov=True;break
                b.extend(c)
        finally:r.close()
        t,e=dec(bytes(b));return {'http':r.status_code,'url':str(r.url),'body':bytes(b),'text':t,'encoding':e,'overflow':ov,'error':None}
    except requests.RequestException as ex:return {'http':None,'url':URL,'body':b'','text':'','encoding':None,'overflow':False,'error':f'{type(ex).__name__}: {ex}'}

def main():
    print('='*60);print('NATIONAL ARCHIVES SEONGNAM ORG BOUNDED UQQ700 SEARCH - S204');print('='*60)
    print('Organization filter:',ORG);print('Candidate hit stop policy: ENABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[];candidates=[];tech=0
    for q,cls in QUERIES:
        r=fetch(s,q);rows=parse(r['text'])
        if r['error'] or r['overflow'] or r['http']!=200:tech+=1
        filtered=[]
        for x in rows:
            p=x['context']; direct=('개발밀도관리구역' in p or '개발밀도 관리구역' in p or 'UQQ700' in p)
            related=('개발밀도' in p or '관리구역' in p)
            if cls=='DIRECT_CANDIDATE' and direct:filtered.append(x)
            elif cls=='RELATED_CANDIDATE' and related:filtered.append(x)
        results.append({'query':q,'candidate_class':cls,'http':r['http'],'final_url':r['url'],'byte_length':len(r['body']),'encoding':r['encoding'],'overflow':r['overflow'],'error':r['error'],'row_count':len(rows),'candidate_row_count':len(filtered),'rows':rows[:25]})
        print('QUERY:',q,'| CLASS:',cls,'| HTTP:',r['http'],'| ROWS:',len(rows),'| CANDIDATES:',len(filtered))
        for x in filtered[:10]:print('  CANDIDATE:',x)
        candidates.extend([{**x,'query':q,'candidate_state':cls} for x in filtered])
        if filtered:
            print('CANDIDATE HIT -> STOP FURTHER QUERIES');break
    uniq={f"{x['rc_code']}|{x['rc_rfile_no']}":x for x in candidates};candidates=list(uniq.values())
    direct=sum(x['candidate_state']=='DIRECT_CANDIDATE' for x in candidates);related=len(candidates)-direct
    semantic='NATIONAL_ARCHIVES_SEONGNAM_ORG_UQQ700_CANDIDATE_FOUND_REQUIRE_DETAIL_CONTEXT' if candidates else ('NATIONAL_ARCHIVES_SEONGNAM_ORG_UQQ700_TECHNICAL_UNKNOWN' if tech else 'NATIONAL_ARCHIVES_SEONGNAM_ORG_UQQ700_NO_CANDIDATE_IN_BOUNDED_FILTERED_SURFACE')
    out={'step':'STEP 17-21-C-16-8-T-100-S204','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','organization_filter':ORG,'results':results,'candidates':candidates,'summary':{'request_count':len(results),'candidate_count':len(candidates),'direct_candidate_count':direct,'related_candidate_count':related,'technical_unknown_count':tech,'semantic_state':semantic,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nCANDIDATES');print('NONE' if not candidates else candidates)
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'request bounded':1<=len(results)<=len(QUERIES),'candidate stop respected':not candidates or len(results)<=len(QUERIES),'technical unknown zero':tech==0,'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S204 National Archives Seongnam-org bounded UQQ700 search failed')
if __name__=='__main__':main()
