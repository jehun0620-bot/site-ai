# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S28
Compare legacy Gazette 938 preview behavior with modern Gazette 2087 control.
For each target: detail -> metadata -> choose HWP/HWPX attachment -> filePreview ->
derive runtime fn/rs with decodeURIComponent semantics -> request rs/fn.xml.
No OCR, no state mutation, no legal promotion.
"""
from __future__ import annotations
import json,re
from pathlib import Path
from urllib.parse import urlparse,urlsplit,unquote
import requests

BASE_DIR=Path(__file__).resolve().parent.parent
OUT=BASE_DIR/'law_data'/'output'/'development_density_management_area_municipal_gazette_legacy_preview_modern_control_comparison.json'
BASE='https://www.seongnam.go.kr'; HOST='www.seongnam.go.kr'; BBS='16002'; TIMEOUT=20; MAX_REQUESTS=10
TARGETS=[
 {'label':'LEGACY_938','gazette':938,'pstSn':'29098','known_fileNo':'28559'},
 {'label':'MODERN_2087','gazette':2087,'pstSn':'404960','known_fileNo':None},
]

def host(u): return (urlparse(u).hostname or '').lower()
def js_params(u):
 q=urlsplit(u).query; out={}
 for p in q.split('&'):
  if not p: continue
  a=p.split('=',1); out[a[0]]=unquote(a[1] if len(a)>1 else '')
 return out

def choose_attachment(html, known=None):
 # robustly capture fileNo near original filename in official metadata fragment
 candidates=[]
 for m in re.finditer(r'fileNo[^0-9]{0,40}(\d+)',html,re.I):
  no=m.group(1); a=max(0,m.start()-500); b=min(len(html),m.end()+900); ctx=html[a:b]
  names=re.findall(r'([\w가-힣().\-+ ]+\.(?:hwpx|hwp))',ctx,re.I)
  candidates.append((no,names[-1].strip() if names else None))
 if known:
  for no,name in candidates:
   if no==known: return {'fileNo':no,'name':name}
  return {'fileNo':known,'name':None}
 for no,name in candidates:
  if name and name.lower().endswith(('.hwpx','.hwp')): return {'fileNo':no,'name':name}
 return None

def main():
 print('='*60); print('DEVELOPMENT DENSITY MANAGEMENT AREA'); print('LEGACY PREVIEW MODERN CONTROL COMPARISON'); print('='*60)
 s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0','Accept-Language':'ko-KR,ko;q=0.9'})
 reqs=0; rows=[]
 for t in TARGETS:
  print('\n--',t['label'],'--')
  d=s.get(f"{BASE}/bbs010308/{t['pstSn']}",timeout=TIMEOUT); reqs+=1
  m=s.get(f"{BASE}/bbs010308/atchFileDetail",params={'pstSn':t['pstSn']},headers={'X-Requested-With':'XMLHttpRequest','Referer':d.url},timeout=TIMEOUT); reqs+=1
  att=choose_attachment(m.text,t['known_fileNo'])
  print('Detail:',d.status_code,'Meta:',m.status_code,'Attachment:',att)
  row={'target':t,'detail_status':d.status_code,'meta_status':m.status_code,'attachment':att}
  if not att:
   row['result']='NO_HWP_ATTACHMENT_DISCOVERED'; rows.append(row); continue
  p=s.get(f"{BASE}/bbs010308/filePreview",params={'bbsCrtSn':BBS,'pstSn':t['pstSn'],'fileNo':att['fileNo']},headers={'Referer':d.url},allow_redirects=True,timeout=TIMEOUT); reqs+=1
  pars=js_params(p.url); fn=pars.get('fn'); rs=pars.get('rs'); info=None
  print('Preview:',p.status_code,p.url); print('Runtime fn:',repr(fn)); print('Runtime rs:',repr(rs))
  if fn and rs:
   iu=BASE+rs.rstrip('/')+'/'+fn+'.xml'; ir=s.get(iu,headers={'Referer':p.url},timeout=TIMEOUT); reqs+=1
   info={'url':ir.url,'status':ir.status_code,'content_type':ir.headers.get('Content-Type',''),'bytes':len(ir.content)}
   print('Info XML:',ir.status_code,ir.url,ir.headers.get('Content-Type',''),len(ir.content))
  row.update({'preview_status':p.status_code,'preview_url':p.url,'runtime_fn':fn,'runtime_rs':rs,'info':info}); rows.append(row)
 out={'step':'STEP 17-21-C-16-8-T-34-S28','rows':rows,'network_request_count':reqs,'negative_evidence_allowed':False,'state_mutation_allowed':False,'legal_promotion_allowed':False}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 vals={'request budget respected':reqs<=MAX_REQUESTS,'all target detail/meta succeeded':all(r.get('detail_status')==200 and r.get('meta_status')==200 for r in rows),'both preview paths attempted':all('preview_status' in r for r in rows),'negative evidence disabled':True,'state mutation disabled':True,'legal promotion disabled':True,'output written':OUT.exists() and OUT.stat().st_size>0}
 print('\nSUMMARY'); print('Requests:',reqs)
 for r in rows: print(r['target']['label'],'preview=',r.get('preview_status'),'info=',(r.get('info') or {}).get('status'))
 print('Output:',OUT); print('\nVALIDATION')
 for k,v in vals.items(): print(f'{k}: {v}')
 print('all_pass:',all(vals.values()))
 if not all(vals.values()): raise AssertionError('modern control comparison validation failed')
if __name__=='__main__': main()
