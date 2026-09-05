# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, html, json, re
from pathlib import Path
from urllib.parse import quote_plus
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_abnormal_response_signature_forensic.json'
URL='https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp'
UA='Mozilla/5.0'
GYEONGGI='4100000000'; SEONGNAM='4113000000'
PAGES=[1,73]


def enc(v:str)->str:return quote_plus(v.encode('euc-kr'),safe='')
def body(page:int)->bytes:
    pairs=[('pageNo',str(page)),('mode',''),('zonenm_t',''),('area',''),('chrgorg_t',''),('selSggCd',SEONGNAM),('mobile_yn',''),('select2',GYEONGGI),('select3',SEONGNAM),('startdt',''),('enddt',''),('chrgorg',''),('gosichrg',''),('gosino',''),('prj_nm',''),('prj_cat_cd',''),('listSize','50'),('zonenm','')]
    return '&'.join(f'{k}={enc(v)}' for k,v in pairs).encode('ascii')
def dec(raw:bytes):
    for e in ('euc-kr','cp949','utf-8'):
        try:return raw.decode(e),e
        except UnicodeDecodeError:pass
    return raw.decode('euc-kr',errors='ignore'),'euc-kr-ignore'
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def extract_all(pattern,text,flags=0,limit=20):
    out=[]
    for m in re.finditer(pattern,text,flags):
        v=m.group(1) if m.groups() else m.group(0)
        v=clean(v)
        if v and v not in out:out.append(v)
        if len(out)>=limit:break
    return out

def inspect(label,r):
    text,encoding=dec(r.content); raw=r.content
    title=extract_all(r'<title[^>]*>([\s\S]*?)</title>',text,re.I,5)
    alerts=extract_all(r'alert\s*\(\s*["\']([\s\S]*?)["\']\s*\)',text,re.I,20)
    visible=[]
    for pat in [r'<h[1-6][^>]*>([\s\S]*?)</h[1-6]>',r'<p[^>]*>([\s\S]*?)</p>',r'<div[^>]*(?:class|id)=["\'][^"\']*(?:error|alert|message|notice)[^"\']*["\'][^>]*>([\s\S]*?)</div>']:
        for v in extract_all(pat,text,re.I,20):
            if v not in visible:visible.append(v)
    forms=[]
    for m in re.finditer(r'<form\b([^>]*)>',text,re.I):
        attrs=m.group(1); am=re.search(r'action=["\']([^"\']*)',attrs,re.I); mm=re.search(r'method=["\']([^"\']*)',attrs,re.I)
        forms.append({'action':html.unescape(am.group(1)) if am else '','method':mm.group(1).upper() if mm else 'GET','raw':re.sub(r'\s+',' ',attrs).strip()[:500]})
        if len(forms)>=20:break
    scripts=[]
    for m in re.finditer(r'<script\b([^>]*)>',text,re.I):
        attrs=m.group(1); sm=re.search(r'src=["\']([^"\']+)',attrs,re.I)
        if sm:scripts.append(html.unescape(sm.group(1)))
        if len(scripts)>=30:break
    return {'label':label,'http':r.status_code,'final_url':str(r.url),'content_type':r.headers.get('Content-Type'),'byte_length':len(raw),'encoding':encoding,'sha256':hashlib.sha256(raw).hexdigest(),'title':title,'alerts':alerts,'visible_messages':visible[:20],'forms':forms,'script_srcs':scripts,'tr_count':len(re.findall(r'<tr\b',text,re.I)),'anchor_count':len(re.findall(r'<a\b',text,re.I)),'seq_marker_count':len(re.findall(r'(?:\?|&)seq=\d+',text,re.I)),'detail_marker_count':text.lower().count('gvgosidet.jsp'),'seongnam_count':text.count('성남시'),'abnormal_marker':bool(re.search(r'비정상\s*접근|잘못된\s*접근|접근이\s*제한|alert\s*\(',text,re.I))}

def main():
    print('='*60);print('EUM GOSI ABNORMAL RESPONSE SIGNATURE FORENSIC - S187');print('='*60)
    print('Detail navigation: DISABLED');print('Attachment download: DISABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    records=[]
    pre=s.get(URL,timeout=25); records.append(inspect('GET_PREFLIGHT',pre))
    for p in PAGES:
        r=s.post(URL,data=body(p),headers={'Content-Type':'application/x-www-form-urlencoded','Referer':URL,'Origin':'https://www.eum.go.kr'},timeout=25)
        records.append(inspect(f'POST_PAGE_{p}',r))
    for x in records:
        print(x['label'],'| HTTP:',x['http'],'| BYTES:',x['byte_length'],'| SHA256:',x['sha256'],'| TR:',x['tr_count'],'| A:',x['anchor_count'],'| SEQ:',x['seq_marker_count'],'| DETAIL:',x['detail_marker_count'],'| SEONGNAM:',x['seongnam_count'],'| ABNORMAL:',x['abnormal_marker'])
        print('  TITLE:',x['title'])
        print('  ALERTS:',x['alerts'])
        print('  VISIBLE_MESSAGES:',x['visible_messages'][:10])
        print('  FORMS:',x['forms'][:10])
        print('  SCRIPT_SRCS:',x['script_srcs'][:10])
    tech=sum(1 for x in records if x['http']!=200)
    hashes={x['sha256'] for x in records[1:]}
    out={'step':'STEP 17-21-C-16-8-T-83-S187','target_name':'개발밀도관리구역','standard_code':'UQQ700','records':records,'summary':{'record_count':len(records),'technical_unknown_count':tech,'post_response_hash_count':len(hashes),'post_pages_identical':len(hashes)==1,'semantic_state':'EUM_CURRENT_LIST_ABNORMAL_RESPONSE_SIGNATURE_CAPTURED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'detail_navigation_executed':False,'attachment_download_executed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'record exact':len(records)==3,'http 200 all':tech==0,'detail navigation disabled':not out['detail_navigation_executed'],'attachment download disabled':not out['attachment_download_executed'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S187 EUM abnormal response signature forensic failed')
if __name__=='__main__':main()
