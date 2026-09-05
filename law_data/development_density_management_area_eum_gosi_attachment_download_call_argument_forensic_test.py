# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_attachment_download_call_argument_forensic.json'
DETAIL='https://www.eum.go.kr/web/gs/gv/gvGosiDet.jsp'
UA='Mozilla/5.0'; SAMPLES=['638968','117916','117520']


def get_text(s,seq):
    try:
        r=s.get(DETAIL,params={'seq':seq},timeout=25); r.raise_for_status(); raw=r.content
        for enc in ('euc-kr','cp949','utf-8'):
            try:return {'state':'HTTP_RESPONSE_CAPTURED','http':r.status_code,'url':str(r.url),'text':raw.decode(enc),'encoding':enc,'error':None}
            except UnicodeDecodeError: pass
        return {'state':'HTTP_RESPONSE_CAPTURED','http':r.status_code,'url':str(r.url),'text':raw.decode('euc-kr',errors='ignore'),'encoding':'euc-kr-ignore','error':None}
    except requests.RequestException as e:
        return {'state':'TECHNICAL_REQUEST_UNKNOWN','http':None,'url':DETAIL,'text':'','encoding':None,'error':f'{type(e).__name__}: {e}'}

def snippets(text, needle, radius=420, limit=20):
    out=[]; start=0
    low=text.lower(); target=needle.lower()
    while len(out)<limit:
        i=low.find(target,start)
        if i<0: break
        frag=text[max(0,i-radius):min(len(text),i+len(target)+radius)]
        frag=re.sub(r'\s+',' ',frag).strip()
        if frag not in out: out.append(frag)
        start=i+len(target)
    return out

def form_forensic(text):
    m=re.search(r'<form\b[^>]*(?:name=["\']frm["\']|id=["\']frm["\'])[^>]*>[\s\S]*?</form>',text,re.I)
    if not m:return {'found':False,'form_html_snippet':None,'hidden_inputs':[]}
    form=m.group(0)
    hidden=[]
    for im in re.finditer(r'<input\b[^>]*>',form,re.I):
        tag=im.group(0)
        typ=re.search(r'type\s*=\s*["\']([^"\']*)',tag,re.I)
        if not typ or typ.group(1).lower()!='hidden': continue
        name=re.search(r'name\s*=\s*["\']([^"\']*)',tag,re.I)
        value=re.search(r'value\s*=\s*["\']([^"\']*)',tag,re.I)
        hidden.append({'name':html.unescape(name.group(1)) if name else None,'value':html.unescape(value.group(1)) if value else ''})
    return {'found':True,'form_html_snippet':re.sub(r'\s+',' ',form[:4000]).strip(),'hidden_inputs':hidden}

def main():
    print('='*60);print('EUM GOSI ATTACHMENT DOWNLOAD CALL ARGUMENT FORENSIC - S182');print('='*60)
    print('Attachment download execution: DISABLED');print('Text extraction: DISABLED');print('OCR: DISABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    rows=[]
    for seq in SAMPLES:
        r=get_text(s,seq); text=r['text']
        dl=snippets(text,'download('); zip_snips=snippets(text,'DownloadZip.jsp'); form=form_forensic(text)
        row={'seq':seq,'state':r['state'],'http':r['http'],'encoding':r['encoding'],'download_call_snippets':dl,'download_zip_snippets':zip_snips,'form':form,'error':r['error']}
        rows.append(row)
        print('SEQ:',seq,'| STATE:',r['state'],'| HTTP:',r['http'],'| DOWNLOAD_SNIPPETS:',len(dl),'| ZIP_SNIPPETS:',len(zip_snips),'| FORM_FOUND:',form['found'])
        for x in dl[:8]: print('  DOWNLOAD_CONTEXT:',x)
        for x in zip_snips[:4]: print('  ZIP_CONTEXT:',x)
        print('  HIDDEN_INPUTS:',form['hidden_inputs'])
    tech=sum(x['state']=='TECHNICAL_REQUEST_UNKNOWN' for x in rows)
    out={'step':'STEP 17-21-C-16-8-T-78-S182','target_name':'개발밀도관리구역','standard_code':'UQQ700','results':rows,'summary':{'sample_count':len(rows),'technical_unknown_count':tech,'semantic_state':'EUM_ATTACHMENT_DOWNLOAD_CALL_ARGUMENT_FORENSIC_CAPTURED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'attachment_download_executed':False,'attachment_text_extraction_executed':False,'ocr_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'sample exact':len(rows)==len(SAMPLES),'technical unknown zero':tech==0,'download context observed':all(x['download_call_snippets'] for x in rows),'attachment download disabled':not out['attachment_download_executed'],'text extraction disabled':not out['attachment_text_extraction_executed'],'OCR disabled':not out['ocr_allowed'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()): raise AssertionError('S182 EUM attachment download-call argument forensic failed')
if __name__=='__main__':main()
