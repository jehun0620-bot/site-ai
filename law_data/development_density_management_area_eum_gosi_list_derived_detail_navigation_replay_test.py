# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
from urllib.parse import quote_plus, urljoin
import requests

BASE=Path(__file__).resolve().parent.parent
SRC=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_seongnam_full_metadata_crawl.json'
OUT=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_list_derived_detail_navigation_replay.json'
LIST='https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp'
UA='Mozilla/5.0'
GYEONGGI='4100000000'; SEONGNAM='4113000000'; MAX=12*1024*1024
SAMPLES=['638968','117916','117520']

ROW_RE=re.compile(r"<tr[^>]*>\s*<td[^>]*>(?P<date>[\s\S]*?)</td>\s*<td[^>]*title=[\"'](?P<notice>[^\"']*)[\"'][^>]*>[\s\S]*?</td>\s*<td[^>]*>[\s\S]*?<a\s+href=[\"'](?P<href>[^\"']*gvGosiDet\.jsp[^\"']*)[\"'][^>]*title=[\"'](?P<title>[^\"']*)[\"']",re.I)
SEQ_RE=re.compile(r'(?:\?|&)seq=(\d+)')


def enc(v:str)->str:return quote_plus(v.encode('euc-kr'),safe='')
def body(page:int)->bytes:
    # EXACT S176 successful payload, including terminal zonenm=''.
    pairs=[('pageNo',str(page)),('mode',''),('zonenm_t',''),('area',''),('chrgorg_t',''),('selSggCd',SEONGNAM),('mobile_yn',''),('select2',GYEONGGI),('select3',SEONGNAM),('startdt',''),('enddt',''),('chrgorg',''),('gosichrg',''),('gosino',''),('prj_nm',''),('prj_cat_cd',''),('listSize','50'),('zonenm','')]
    return '&'.join(f'{k}={enc(v)}' for k,v in pairs).encode('ascii')
def dec(raw:bytes):
    for e in ('euc-kr','cp949','utf-8'):
        try:return raw.decode(e),e
        except UnicodeDecodeError:pass
    return raw.decode('euc-kr',errors='ignore'),'euc-kr-ignore'
def find_page(rows,seq):
    for r in rows:
        if str(r.get('seq',''))==seq:return int(r.get('page') or 0)
    return 0
def fetch_list(s,page):
    try:
        r=s.post(LIST,data=body(page),headers={'Content-Type':'application/x-www-form-urlencoded','Referer':LIST,'Origin':'https://www.eum.go.kr'},timeout=25)
        text,encoding=dec(r.content)
        return {'state':'HTTP_RESPONSE_CAPTURED','http':r.status_code,'url':str(r.url),'text':text,'encoding':encoding,'error':None}
    except requests.RequestException as e:return {'state':'TECHNICAL_REQUEST_UNKNOWN','http':None,'url':LIST,'text':'','encoding':None,'error':f'{type(e).__name__}: {e}'}
def extract_row(text,seq):
    for m in ROW_RE.finditer(text):
        href=html.unescape(m.group('href')); sm=SEQ_RE.search(href)
        if sm and sm.group(1)==seq:
            return {'href':href,'notice':re.sub(r'\s+',' ',html.unescape(m.group('notice'))).strip(),'title':html.unescape(m.group('title')).strip()}
    return None
def fetch_detail(s,url,referer):
    try:
        r=s.get(url,headers={'Referer':referer},timeout=25,stream=True,allow_redirects=True); b=bytearray();ov=False
        try:
            for c in r.iter_content(65536):
                if not c:continue
                if len(b)+len(c)>MAX:ov=True;break
                b.extend(c)
        finally:r.close()
        text,encoding=dec(bytes(b)); abnormal=bool(re.search(r'비정상\s*접근|잘못된\s*접근|접근이\s*제한',text,re.I))
        return {'state':'HTTP_RESPONSE_CAPTURED' if not ov else 'TECHNICAL_REQUEST_UNKNOWN','http':r.status_code,'url':str(r.url),'encoding':encoding,'byte_length':len(b),'download_marker_count':text.lower().count('download('),'download_zip_marker_count':text.lower().count('downloadzip.jsp'),'form_frm_marker':bool(re.search(r'<form\b[^>]*(?:name|id)=["\']frm["\']',text,re.I)),'abnormal_access_marker':abnormal,'error':'RESPONSE_SIZE_LIMIT_EXCEEDED' if ov else None}
    except requests.RequestException as e:return {'state':'TECHNICAL_REQUEST_UNKNOWN','http':None,'url':url,'encoding':None,'byte_length':0,'download_marker_count':0,'download_zip_marker_count':0,'form_frm_marker':False,'abnormal_access_marker':False,'error':f'{type(e).__name__}: {e}'}

def main():
    print('='*60);print('EUM GOSI LIST-DERIVED DETAIL NAVIGATION REPLAY - S185');print('='*60)
    print("Payload: EXACT S176 INCLUDING zonenm=''");print('Attachment download: DISABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    src=json.loads(SRC.read_text(encoding='utf-8')); rows=src.get('rows') or []
    results=[]
    for seq in SAMPLES:
        page=find_page(rows,seq);s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
        pre=s.get(LIST,timeout=25)
        listing=fetch_list(s,page); row=extract_row(listing['text'],seq)
        detail=None
        if row:
            detail_url=urljoin(listing['url'],row['href']);detail=fetch_detail(s,detail_url,listing['url'])
        rec={'seq':seq,'page':page,'preflight_http':pre.status_code,'list_state':listing['state'],'list_http':listing['http'],'row_found':bool(row),'row':row,'detail':detail,'cookies':sorted(c.name for c in s.cookies)};results.append(rec)
        print('SEQ:',seq,'| PAGE:',page,'| LIST_HTTP:',listing['http'],'| ROW_FOUND:',bool(row))
        if row: print('  HREF:',row['href']);print('  NOTICE:',row['notice']);print('  TITLE:',row['title'])
        if detail: print('  DETAIL | HTTP:',detail['http'],'| BYTES:',detail['byte_length'],'| DOWNLOAD:',detail['download_marker_count'],'| ZIP:',detail['download_zip_marker_count'],'| FORM:',detail['form_frm_marker'],'| ABNORMAL:',detail['abnormal_access_marker'])
    tech=sum(1 for r in results if r['list_state']=='TECHNICAL_REQUEST_UNKNOWN' or (r['detail'] and r['detail']['state']=='TECHNICAL_REQUEST_UNKNOWN'))
    rowq=sum(1 for r in results if r['row_found']); attachq=sum(1 for r in results if r['detail'] and (r['detail']['download_marker_count']>0 or r['detail']['download_zip_marker_count']>0))
    out={'step':'STEP 17-21-C-16-8-T-81-S185','target_name':'개발밀도관리구역','standard_code':'UQQ700','results':results,'summary':{'sample_count':len(results),'row_found_count':rowq,'attachment_marker_qualified_count':attachq,'technical_unknown_count':tech,'semantic_state':'EUM_EXACT_S176_DETAIL_NAVIGATION_REPLAY_CAPTURED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'attachment_download_executed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'sample exact':len(results)==len(SAMPLES),'technical unknown zero':tech==0,'all source rows found':rowq==len(results),'attachment download disabled':not out['attachment_download_executed'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S185 exact S176 detail navigation replay failed')
if __name__=='__main__':main()
