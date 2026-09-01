# -*- coding: utf-8 -*-
"""S87: exact row interaction recovery for Seongnam legacy gazette.

Reuses the previously validated municipal-gazette row contract:
anchor text `성남시보 제N호` + row-local `fn_move_form(pstSn)` interaction.
Compares baseline GET and session-preserving POST responses for 2024 and 2009
without drawing any pre-2010 legal/search absence conclusion.
"""
from __future__ import annotations
import html,json,re
from pathlib import Path
from urllib.parse import urljoin,urlparse
import requests

BASE=Path(__file__).resolve().parent.parent
OUT_DIR=BASE/'law_data'/'output'; OUT_DIR.mkdir(parents=True,exist_ok=True)
OUT=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_exact_row_interaction_recovery.json'
URL='https://www.seongnam.go.kr/bbs010308'; HOST='www.seongnam.go.kr'; TIMEOUT=20; MAX_REQ=5
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
FORM_RE=re.compile(r'<form\b(?P<a>[^>]*)>(?P<b>.*?)</form>',re.I|re.S)
INPUT_RE=re.compile(r'<input\b(?P<a>[^>]*)/?>',re.I|re.S)
SELECT_RE=re.compile(r'<select\b(?P<a>[^>]*)>(?P<b>.*?)</select>',re.I|re.S)
OPTION_RE=re.compile(r'<option\b(?P<a>[^>]*)>(?P<b>.*?)</option>',re.I|re.S)
ANCHOR_RE=re.compile(r'<a\b(?P<a>[^>]*)>(?P<b>.*?)</a>',re.I|re.S)
ATTR_RE=re.compile(r'([:\w-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))',re.I)
TAG_RE=re.compile(r'<[^>]+>',re.S)
GAZ_RE=re.compile(r'성남시보\s*제\s*(\d+)\s*호',re.I)
CALL_RE=re.compile(r'([A-Za-z_$][\w$]*)\s*\(\s*[\'\"]?(\d+)[\'\"]?\s*\)')
FN_MOVE_RE=re.compile(r'function\s+fn_move_form\s*\(([^)]*)\)\s*\{(.*?)\}',re.S)

def attrs(raw):
 d={}
 for m in ATTR_RE.finditer(raw or ''): d[m.group(1).lower()]=html.unescape(m.group(2) or m.group(3) or m.group(4) or '')
 return d

def clean(raw): return re.sub(r'\s+',' ',html.unescape(TAG_RE.sub(' ',raw or ''))).strip()
def rec(r): return {'http':r.status_code,'url':str(r.url),'host':(urlparse(str(r.url)).hostname or '').lower(),'text':r.text,'bytes':len(r.content)}
def get(s,c):
 if c[0]>=MAX_REQ: raise AssertionError('request budget exceeded')
 c[0]+=1; return rec(s.get(URL,timeout=TIMEOUT,allow_redirects=True))
def post(s,data,c):
 if c[0]>=MAX_REQ: raise AssertionError('request budget exceeded')
 c[0]+=1; return rec(s.post(URL,data=data,timeout=TIMEOUT,allow_redirects=True))
def form(text):
 cand=[]
 for fm in FORM_RE.finditer(text or ''):
  fa=attrs(fm.group('a')); body=fm.group('b'); controls={}; selects=[]
  for im in INPUT_RE.finditer(body):
   ia=attrs(im.group('a')); n=ia.get('name',''); typ=ia.get('type','text').lower()
   if n and not (typ in {'checkbox','radio'} and 'checked' not in ia): controls[n]=ia.get('value','')
  for sm in SELECT_RE.finditer(body):
   sa=attrs(sm.group('a')); n=sa.get('name',''); opts=[]; chosen=''
   for om in OPTION_RE.finditer(sm.group('b')):
    oa=attrs(om.group('a')); v=oa.get('value',''); opts.append({'value':v,'label':clean(om.group('b'))})
    if not chosen: chosen=v
   if n: controls[n]=chosen; selects.append({'name':n,'options':opts})
  score=sum(k in controls for k in ['csrfToken','srchText','srchTypeCd','srchBgngYmd','srchEndYmd'])
  cand.append({'method':fa.get('method','GET').upper(),'action':urljoin(URL,fa.get('action','')),'controls':controls,'selects':selects,'score':score})
 cand.sort(key=lambda x:(x['method']=='POST',x['score']),reverse=True)
 if not cand or cand[0]['method']!='POST': raise AssertionError('search POST form missing')
 return cand[0]
def payload(f,bg='',end=''):
 p=dict(f['controls']); p['cntPerPage']=p.get('cntPerPage') or '30'; p['sortType']=p.get('sortType') or '1'; p['srchTypeCd']=p.get('srchTypeCd') or 'pstTtl'; p['srchText']=''; p['srchBgngYmd']=bg; p['srchEndYmd']=end; p['curPage']='1'; return p
def rows(text):
 out=[]; seen=set()
 for am in ANCHOR_RE.finditer(text or ''):
  a=attrs(am.group('a')); label=clean(am.group('b')); gm=GAZ_RE.search(label)
  if not gm: continue
  href=a.get('href',''); onclick=a.get('onclick',''); calls=[]
  for cm in CALL_RE.finditer(href+' '+onclick): calls.append({'function':cm.group(1),'argument':cm.group(2)})
  move=[x for x in calls if x['function']=='fn_move_form']
  if not move: continue
  pst=move[0]['argument']; key=(int(gm.group(1)),pst)
  if key in seen: continue
  seen.add(key); out.append({'gazette_number':key[0],'pstSn':pst,'text':label,'href':href,'onclick':onclick})
 return out
def summarize(label,r):
 rr=rows(r['text']); x={'label':label,'http':r['http'],'official':r['host']==HOST,'bytes':r['bytes'],'row_count':len(rr),'identities':[(z['gazette_number'],z['pstSn']) for z in rr],'rows':rr[:30]}; print('RESULT:',{k:x[k] for k in ['label','http','official','bytes','row_count','identities']}); return x

def main():
 print('='*60); print('SEONGNAM LEGACY GAZETTE EXACT ROW INTERACTION RECOVERY - S87'); print('='*60)
 print('Target-term search: DISABLED'); print('Attachment download: DISABLED'); print('Negative evidence: DISABLED')
 s=requests.Session(); s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'}); c=[0]
 base=get(s,c); f=form(base['text']); fn=FN_MOVE_RE.search(base['text'])
 print('FN_MOVE_FORM:', clean(fn.group(0))[:1200] if fn else 'NOT FOUND')
 base_result=summarize('BASE_GET',base)
 baseline=summarize('BASELINE_POST',post(s,payload(f),c))
 control=summarize('DATE_2024_CONTROL',post(s,payload(f,'20240101','20241231'),c))
 old=summarize('DATE_2009_PROBE',post(s,payload(f,'20090101','20091231'),c))
 base_ids=baseline['identities']; comp=[]
 for x in [control,old]:
  ids=x['identities']; comp.append({'label':x['label'],'same_as_baseline':ids==base_ids,'overlap':len(set(ids)&set(base_ids)),'new_vs_baseline':[i for i in ids if i not in set(base_ids)]})
 print('COMPARISONS:',comp)
 row_contract=base_result['row_count']>0 or baseline['row_count']>0
 date_effect=control['identities']!=base_ids if row_contract else False
 summary={'request_count':c[0],'fn_move_form_recovered':bool(fn),'exact_row_contract_recovered':row_contract,'base_get_row_count':base_result['row_count'],'baseline_post_row_count':baseline['row_count'],'date_2024_row_count':control['row_count'],'date_2009_row_count':old['row_count'],'date_filter_effect_observed':date_effect,'date_2009_same_identity_as_baseline':old['identities']==base_ids,'semantic_state':'DATE_FILTER_EFFECT_OBSERVED' if row_contract and date_effect else 'ROW_CONTRACT_ONLY' if row_contract else 'UNRESOLVED','pre2010_reachability_conclusion_allowed':False}
 out={'step':'STEP 17-21-C-16-8-T-35-S87','target_name':'개발밀도관리구역','standard_code':'UQQ700','resolution_type':'HYBRID_SPATIAL_NOTICE','source_family':'LEGACY_LOCAL_GAZETTE','base_result':base_result,'baseline_post_result':baseline,'date_2024_control':control,'date_2009_probe':old,'comparisons':comp,'summary':summary,'target_term_search_executed':False,'attachment_body_download_executed':False,'state_mutation_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False,'final_positive_promotion_allowed':False}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 vals={'all transport official':all(x['http']==200 and x['official'] for x in [base_result,baseline,control,old]),'fn_move_form recovered':bool(fn),'request budget respected':c[0]<=MAX_REQ,'target-term search disabled':not out['target_term_search_executed'],'negative evidence disabled':not out['negative_evidence_allowed'],'pre2010 conclusion blocked':not summary['pre2010_reachability_conclusion_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed','final_positive_promotion_allowed']),'output written':OUT.exists() and OUT.stat().st_size>0}
 print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]; print('Output:',OUT); print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
 if not all(vals.values()): raise AssertionError('S87 exact row interaction recovery failed')
if __name__=='__main__': main()
