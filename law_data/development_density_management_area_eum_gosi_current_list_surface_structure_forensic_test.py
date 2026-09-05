# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
from urllib.parse import quote_plus
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_current_list_surface_structure_forensic.json'
URL='https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp'
UA='Mozilla/5.0'
GYEONGGI='4100000000'; SEONGNAM='4113000000'
PAGES=[1,73]

ROW_RE=re.compile(r"<tr[^>]*>\s*<td[^>]*>(?P<date>[\s\S]*?)</td>\s*<td[^>]*title=[\"'](?P<notice>[^\"']*)[\"'][^>]*>[\s\S]*?</td>\s*<td[^>]*>[\s\S]*?<a\s+href=[\"'](?P<href>[^\"']*gvGosiDet\.jsp[^\"']*)[\"'][^>]*title=[\"'](?P<title>[^\"']*)[\"']",re.I)

def enc(v:str)->str:return quote_plus(v.encode('euc-kr'),safe='')
def body(page:int)->bytes:
    pairs=[('pageNo',str(page)),('mode',''),('zonenm_t',''),('area',''),('chrgorg_t',''),('selSggCd',SEONGNAM),('mobile_yn',''),('select2',GYEONGGI),('select3',SEONGNAM),('startdt',''),('enddt',''),('chrgorg',''),('gosichrg',''),('gosino',''),('prj_nm',''),('prj_cat_cd',''),('listSize','50'),('zonenm','')]
    return '&'.join(f'{k}={enc(v)}' for k,v in pairs).encode('ascii')
def dec(raw:bytes):
    for e in ('euc-kr','cp949','utf-8'):
        try:return raw.decode(e),e
        except UnicodeDecodeError:pass
    return raw.decode('euc-kr',errors='ignore'),'euc-kr-ignore'
def snippet(text,needle,radius=260,limit=5):
    out=[];low=text.lower();n=needle.lower();start=0
    while len(out)<limit:
        i=low.find(n,start)
        if i<0:break
        frag=re.sub(r'\s+',' ',text[max(0,i-radius):min(len(text),i+len(n)+radius)]).strip()
        if frag not in out:out.append(frag)
        start=i+len(n)
    return out

def main():
    print('='*60);print('EUM GOSI CURRENT LIST SURFACE STRUCTURE FORENSIC - S186');print('='*60)
    print('Detail navigation: DISABLED');print('Attachment download: DISABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    pre=s.get(URL,timeout=25)
    results=[]
    for page in PAGES:
        try:
            r=s.post(URL,data=body(page),headers={'Content-Type':'application/x-www-form-urlencoded','Referer':URL,'Origin':'https://www.eum.go.kr'},timeout=25)
            text,encoding=dec(r.content)
            row_matches=list(ROW_RE.finditer(text))
            abnormal=bool(re.search(r'비정상\s*접근|잘못된\s*접근|접근이\s*제한|alert\s*\(',text,re.I))
            result={
                'page':page,'state':'HTTP_RESPONSE_CAPTURED','http':r.status_code,'byte_length':len(r.content),'encoding':encoding,
                'seongnam_count':text.count('성남시'),'gyeonggi_code_count':text.count(GYEONGGI),'seongnam_code_count':text.count(SEONGNAM),
                'seq_marker_count':len(re.findall(r'(?:\?|&)seq=\d+',text,re.I)),'detail_marker_count':text.lower().count('gvgosidet.jsp'),
                'tr_count':len(re.findall(r'<tr\b',text,re.I)),'anchor_count':len(re.findall(r'<a\b',text,re.I)),
                's176_row_regex_count':len(row_matches),'abnormal_access_marker':abnormal,
                'no_result_marker':bool(re.search(r'검색\s*결과가\s*없|조회된\s*자료가\s*없|등록된\s*자료가\s*없',text,re.I)),
                'seq_snippets':snippet(text,'seq='),'detail_snippets':snippet(text,'gvGosiDet.jsp'),'seongnam_snippets':snippet(text,'성남시'),
                'error':None,
            }
        except requests.RequestException as e:
            result={'page':page,'state':'TECHNICAL_REQUEST_UNKNOWN','http':None,'byte_length':0,'encoding':None,'seongnam_count':0,'gyeonggi_code_count':0,'seongnam_code_count':0,'seq_marker_count':0,'detail_marker_count':0,'tr_count':0,'anchor_count':0,'s176_row_regex_count':0,'abnormal_access_marker':False,'no_result_marker':False,'seq_snippets':[],'detail_snippets':[],'seongnam_snippets':[],'error':f'{type(e).__name__}: {e}'}
        results.append(result)
        print('PAGE:',page,'| HTTP:',result['http'],'| BYTES:',result['byte_length'],'| TR:',result['tr_count'],'| A:',result['anchor_count'],'| SEONGNAM:',result['seongnam_count'],'| SEQ:',result['seq_marker_count'],'| DETAIL:',result['detail_marker_count'],'| S176_ROW_RE:',result['s176_row_regex_count'],'| ABNORMAL:',result['abnormal_access_marker'],'| NO_RESULT:',result['no_result_marker'])
        for x in result['seq_snippets'][:3]:print('  SEQ_CONTEXT:',x)
        for x in result['detail_snippets'][:3]:print('  DETAIL_CONTEXT:',x)
        for x in result['seongnam_snippets'][:3]:print('  SEONGNAM_CONTEXT:',x)
    tech=sum(x['state']=='TECHNICAL_REQUEST_UNKNOWN' for x in results)
    structural_rows=sum(x['s176_row_regex_count'] for x in results)
    raw_detail=sum(x['detail_marker_count'] for x in results)
    semantic='EUM_CURRENT_LIST_RAW_DETAIL_PRESENT_PARSER_REVIEW_REQUIRED' if raw_detail and not structural_rows else ('EUM_CURRENT_LIST_ROWS_PRESENT' if structural_rows else 'EUM_CURRENT_LIST_SURFACE_NO_ROW_MARKERS_CURRENT_RESPONSE')
    out={'step':'STEP 17-21-C-16-8-T-82-S186','target_name':'개발밀도관리구역','standard_code':'UQQ700','preflight_http':pre.status_code,'results':results,'summary':{'page_count':len(results),'technical_unknown_count':tech,'s176_row_regex_total':structural_rows,'raw_detail_marker_total':raw_detail,'semantic_state':semantic,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'detail_navigation_executed':False,'attachment_download_executed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'preflight http 200':pre.status_code==200,'page exact':len(results)==len(PAGES),'technical unknown zero':tech==0,'detail navigation disabled':not out['detail_navigation_executed'],'attachment download disabled':not out['attachment_download_executed'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S186 EUM current list surface structure forensic failed')
if __name__=='__main__':main()
