# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
from urllib.parse import quote_plus, urljoin
import requests

BASE=Path(__file__).resolve().parent.parent
SRC=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_seongnam_full_metadata_crawl.json'
OUT=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_list_derived_detail_navigation_forensic.json'
LIST='https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
GYEONGGI='4100000000'; SEONGNAM='4113000000'; MAX=12*1024*1024
SAMPLES=['638968','117916','117520']

BASE_CONTROLS=[('pageNo','1'),('mode',''),('zonenm_t',''),('area',''),('chrgorg_t',''),('selSggCd',SEONGNAM),('mobile_yn',''),('select2',GYEONGGI),('select3',SEONGNAM),('startdt',''),('enddt',''),('chrgorg',''),('gosichrg',''),('gosino',''),('prj_nm',''),('prj_cat_cd',''),('listSize','50')]


def enc(v): return quote_plus(str(v).encode('euc-kr'),safe='')
def form_body(pairs): return '&'.join(f'{quote_plus(k,safe="")}={enc(v)}' for k,v in pairs).encode('ascii')

def req(s,method,url,body=None,referer=None):
    try:
        h={}
        if referer: h['Referer']=referer
        if method=='POST':
            h['Content-Type']='application/x-www-form-urlencoded'; h['Origin']='https://www.eum.go.kr'; r=s.post(url,data=body,headers=h,timeout=25,stream=True,allow_redirects=True)
        else:r=s.get(url,headers=h,timeout=25,stream=True,allow_redirects=True)
        b=bytearray();ov=False
        try:
            for c in r.iter_content(65536):
                if not c: continue
                if len(b)+len(c)>MAX: ov=True;break
                b.extend(c)
        finally:r.close()
        return {'state':'HTTP_RESPONSE_CAPTURED' if not ov else 'TECHNICAL_REQUEST_UNKNOWN','http':r.status_code,'url':str(r.url),'body':bytes(b),'error':'RESPONSE_SIZE_LIMIT_EXCEEDED' if ov else None}
    except requests.RequestException as e:return {'state':'TECHNICAL_REQUEST_UNKNOWN','http':None,'url':url,'body':b'','error':f'{type(e).__name__}: {e}'}

def dec(b):
    for encname in ('euc-kr','cp949','utf-8'):
        try:return b.decode(encname),encname
        except UnicodeDecodeError:pass
    return b.decode('euc-kr',errors='ignore'),'euc-kr-ignore'

def find_page(rows,seq):
    for r in rows:
        if str(r.get('seq',''))==seq:return int(r.get('page') or 0)
    return 0

def extract_href(text,seq):
    m=re.search(r'href=["\']([^"\']*gvGosiDet\.jsp\?[^"\']*seq='+re.escape(seq)+r'[^"\']*)["\']',text,re.I)
    return html.unescape(m.group(1)) if m else None

def inspect(seq,r):
    text,encoding=dec(r['body'])
    abnormal=bool(re.search(r'비정상\s*접근|잘못된\s*접근|접근이\s*제한|alert\s*\(',text,re.I))
    return {'state':r['state'],'http':r['http'],'final_url':r['url'],'encoding':encoding,'byte_length':len(r['body']),'content_identity':(seq in text) and not abnormal,'download_marker_count':text.lower().count('download('),'download_zip_marker_count':text.lower().count('downloadzip.jsp'),'form_frm_marker':bool(re.search(r'<form\b[^>]*(?:name|id)=["\']frm["\']',text,re.I)),'abnormal_access_marker':abnormal,'error':r['error']}

def main():
    print('='*60);print('EUM GOSI LIST-DERIVED DETAIL NAVIGATION FORENSIC - S184');print('='*60)
    print('Attachment download: DISABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    src=json.loads(SRC.read_text(encoding='utf-8')); rows=src.get('rows') or src.get('metadata_rows') or []
    results=[]
    for seq in SAMPLES:
        page=find_page(rows,seq)
        s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
        pre=req(s,'GET',LIST)
        pairs=[(k,str(page) if k=='pageNo' else v) for k,v in BASE_CONTROLS]
        listing=req(s,'POST',LIST,form_body(pairs),LIST)
        list_text,_=dec(listing['body']); href=extract_href(list_text,seq)
        if href:
            detail_url=urljoin(listing['url'],href); detail=req(s,'GET',detail_url,referer=listing['url']); detail_info=inspect(seq,detail)
        else:
            detail_url=None; detail_info={'state':'DETAIL_HREF_NOT_FOUND','http':None,'final_url':None,'encoding':None,'byte_length':0,'content_identity':False,'download_marker_count':0,'download_zip_marker_count':0,'form_frm_marker':False,'abnormal_access_marker':False,'error':None}
        rec={'seq':seq,'page':page,'preflight_http':pre['http'],'list_http':listing['http'],'detail_href':href,'detail_url':detail_url,'detail':detail_info,'cookie_names':sorted(c.name for c in s.cookies)};results.append(rec)
        print('SEQ:',seq,'| PAGE:',page,'| LIST_HTTP:',listing['http'],'| HREF_FOUND:',bool(href))
        print('  DETAIL | HTTP:',detail_info['http'],'| BYTES:',detail_info['byte_length'],'| CONTENT_IDENTITY:',detail_info['content_identity'],'| DOWNLOAD:',detail_info['download_marker_count'],'| ZIP:',detail_info['download_zip_marker_count'],'| FORM:',detail_info['form_frm_marker'],'| ABNORMAL:',detail_info['abnormal_access_marker'])
        if href: print('  HREF:',href)
    tech=sum(1 for r in results if r['detail']['state']=='TECHNICAL_REQUEST_UNKNOWN' or r['list_http'] is None)
    hrefq=sum(1 for r in results if r['detail_href'])
    contentq=sum(1 for r in results if r['detail']['content_identity'])
    attachq=sum(1 for r in results if r['detail']['download_marker_count']>0 or r['detail']['download_zip_marker_count']>0)
    out={'step':'STEP 17-21-C-16-8-T-80-S184','target_name':'개발밀도관리구역','standard_code':'UQQ700','results':results,'summary':{'sample_count':len(results),'detail_href_qualified_count':hrefq,'content_identity_qualified_count':contentq,'attachment_marker_qualified_count':attachq,'technical_unknown_count':tech,'semantic_state':'EUM_LIST_DERIVED_DETAIL_NAVIGATION_FORENSIC_CAPTURED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'attachment_download_executed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'sample exact':len(results)==len(SAMPLES),'technical unknown zero':tech==0,'detail hrefs found':hrefq==len(results),'attachment download disabled':not out['attachment_download_executed'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()): raise AssertionError('S184 EUM list-derived detail navigation forensic failed')
if __name__=='__main__':main()
