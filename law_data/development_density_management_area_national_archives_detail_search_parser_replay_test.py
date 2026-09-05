# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_detail_search_parser_replay.json'
GET_URL='https://www.archives.go.kr/next/newsearch/searchTotalUp.do'
POST_URL='https://www.archives.go.kr/next/srch/uniDetailSearch.do'
UA='Mozilla/5.0';MAX=16*1024*1024
CASES=[
    {'label':'BASELINE_SEONGNAM','keyword':'성남시','orgName':'','expected_title':'성남시지'},
    {'label':'ORG_FILTER_ROAD_POSITIVE','keyword':'도로명주소','orgName':'경기도 성남시','expected_title':None},
    {'label':'ORG_FILTER_DENSITY_DIAGNOSTIC','keyword':'개발밀도','orgName':'경기도 성남시','expected_title':None},
]
CALL_RE=re.compile(r"showDetailWithQuery\('([^']+)','([^']+)'(?:,'([^']*)')?\)",re.I)
ROW_RE=re.compile(r'<div\b[^>]*class=["\'][^"\']*result-row[^"\']*["\'][^>]*>([\s\S]*?)(?=<div\b[^>]*class=["\'][^"\']*result-row[^"\']*["\']|\Z)',re.I)

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def fetch(method,url,s,**kwargs):
    try:
        r=s.request(method,url,timeout=30,stream=True,allow_redirects=True,**kwargs);b=bytearray();ov=False
        try:
            for c in r.iter_content(65536):
                if not c:continue
                if len(b)+len(c)>MAX:ov=True;break
                b.extend(c)
        finally:r.close()
        t,e=dec(bytes(b));return {'http':r.status_code,'url':str(r.url),'body':bytes(b),'text':t,'encoding':e,'overflow':ov,'error':None}
    except requests.RequestException as ex:return {'http':None,'url':url,'body':b'','text':'','encoding':None,'overflow':False,'error':f'{type(ex).__name__}: {ex}'}
def parse_rows(text):
    out=[]
    for rm in ROW_RE.finditer(text):
        frag=rm.group(1);cm=CALL_RE.search(frag)
        if not cm:continue
        def pick(pats):
            for p in pats:
                m=re.search(p,frag,re.I)
                if m:return clean(m.group(1))
            return ''
        title=pick([r'class=["\']file-title["\'][^>]*>([\s\S]*?)</a>',r'class=["\']title["\'][^>]*>([\s\S]*?)</(?:div|span|a)>'])
        inst=pick([r'class=["\']institution["\'][^>]*>([\s\S]*?)</(?:div|span|p)>',r'생산기관\s*:\s*</?[^>]*>\s*([^<]+)'])
        year=pick([r'class=["\']year["\'][^>]*>([\s\S]*?)</(?:div|span|p)>',r'생산연도\s*:\s*</?[^>]*>\s*([^<]+)'])
        manage=pick([r'class=["\']manage-number["\'][^>]*>([\s\S]*?)</(?:div|span|p)>',r'관리번호\s*:\s*</?[^>]*>\s*([^<]+)'])
        out.append({'rc_code':cm.group(1),'rc_rfile_no':cm.group(2),'page':cm.group(3),'title':title,'institution':inst,'year':year,'manage_no':manage,'context':clean(frag)[:1800]})
    return out

def payload(c):
    org=c['orgName'];orgx=org.replace(',', '^')
    return {'is_detail':'yes','srchinit':'ritem','afterKeyword':'','size':'10','from':'1','sort':'SCORE','order':'DESC','kikwancode':'','kikwanname':'','query_type':'ftr','keyword':c['keyword'],'detailOneKeyword':'','detailMatchKeyword':'','detailExceptKeyword':'','org_nm':orgx,'org_nm_fst':orgx,'orgName':org,'prod_yr_start':'','prod_yr_end':'','opn_yn':'','opn_yn_fst':'','arch_down':'','arch_down_fst':'','record_type':'','doc_type':'','doc_type_fst':'','type':'','is_elect':'','mng_no_start':'','mng_no_end':'','prod_dt_start':'','prod_dt_end':'','sihang_dt_start':'','sihang_dt_end':''}

def main():
    print('='*60);print('NATIONAL ARCHIVES DETAIL SEARCH PARSER REPLAY - S203');print('='*60)
    print('POST result parser: result-row + showDetailWithQuery(rfile identity)')
    print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    pre=fetch('GET',GET_URL,s,params={'query_type':'keyword','is_detail':'yes','upside_query':'성남시','keyword':'성남시','srchinit':'ritem'})
    results=[];tech=0
    for c in CASES:
        r=fetch('POST',POST_URL,s,data=payload(c),headers={'Referer':pre['url'],'Origin':'https://www.archives.go.kr'});rows=parse_rows(r['text'])
        if r['error'] or r['overflow'] or r['http']!=200:tech+=1
        expected=c['expected_title'];expected_matches=[x for x in rows if expected and expected in x['title']]
        seongnam_rows=[x for x in rows if '성남' in x['institution'] or '성남' in x['title']]
        density_rows=[x for x in rows if '개발밀도' in x['title'] or '개발밀도' in x['context']]
        results.append({'label':c['label'],'keyword':c['keyword'],'orgName':c['orgName'],'http':r['http'],'byte_length':len(r['body']),'encoding':r['encoding'],'row_count':len(rows),'expected_match_count':len(expected_matches),'seongnam_related_row_count':len(seongnam_rows),'development_density_related_row_count':len(density_rows),'rows':rows[:30],'error':r['error']})
        print('CASE:',c['label'],'| KEYWORD:',c['keyword'],'| ORG:',c['orgName'] or '-','| HTTP:',r['http'],'| ROWS:',len(rows),'| EXPECTED:',len(expected_matches),'| SEONGNAM:',len(seongnam_rows),'| DENSITY:',len(density_rows))
        for x in rows[:10]:print('  ROW:',x)
    by={x['label']:x for x in results};baseline=by['BASELINE_SEONGNAM']['row_count']>0 and by['BASELINE_SEONGNAM']['expected_match_count']>0
    org_road=by['ORG_FILTER_ROAD_POSITIVE']['row_count']>0 and by['ORG_FILTER_ROAD_POSITIVE']['seongnam_related_row_count']>0
    density_count=by['ORG_FILTER_DENSITY_DIAGNOSTIC']['development_density_related_row_count']
    semantic='NATIONAL_ARCHIVES_DETAIL_SEARCH_POST_PARSER_QUALIFIED' if baseline and org_road and tech==0 else 'NATIONAL_ARCHIVES_DETAIL_SEARCH_POST_PARSER_PARTIAL'
    out={'step':'STEP 17-21-C-16-8-T-99-S203','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','results':results,'summary':{'case_count':len(results),'baseline_positive_control_resolved':baseline,'org_filter_positive_control_resolved':org_road,'org_filtered_development_density_related_row_count':density_count,'technical_unknown_count':tech,'semantic_state':semantic,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'case exact':len(results)==3,'baseline positive resolved':baseline,'org filter positive resolved':org_road,'technical unknown zero':tech==0,'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S203 National Archives detail-search parser replay failed')
if __name__=='__main__':main()
