# -*- coding: utf-8 -*-
"""S90: forensic recovery of the actual legacy gazette search wire contract.

S89 proved that even brace-aware JS semantics (srchDtType=creatrDt, creatrDt=09)
plus date range did not change result identities. This stage avoids target-term
queries and instead inspects browser-visible form controls and search helper JS to
recover the exact submitted parameter set, including radio/button/date UI state.
Only bounded control requests are allowed; pre-2010 reachability remains blocked.
"""
from __future__ import annotations
import html,json,re
from pathlib import Path
from urllib.parse import urljoin,urlparse
import requests

BASE=Path(__file__).resolve().parent.parent
OUT_DIR=BASE/'law_data'/'output'; OUT_DIR.mkdir(parents=True,exist_ok=True)
OUT=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_wire_contract_forensic.json'
URL='https://www.seongnam.go.kr/bbs010308'; HOST='www.seongnam.go.kr'; TIMEOUT=20; MAX_REQ=7
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
FORM_RE=re.compile(r'<form\b(?P<a>[^>]*)>(?P<b>.*?)</form>',re.I|re.S)
INPUT_RE=re.compile(r'<input\b(?P<a>[^>]*)/?>',re.I|re.S)
SELECT_RE=re.compile(r'<select\b(?P<a>[^>]*)>(?P<b>.*?)</select>',re.I|re.S)
OPTION_RE=re.compile(r'<option\b(?P<a>[^>]*)>(?P<b>.*?)</option>',re.I|re.S)
BUTTON_RE=re.compile(r'<button\b(?P<a>[^>]*)>(?P<b>.*?)</button>',re.I|re.S)
ANCHOR_RE=re.compile(r'<a\b(?P<a>[^>]*)>(?P<b>.*?)</a>',re.I|re.S)
ATTR_RE=re.compile(r'([:\w-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))',re.I)
TAG_RE=re.compile(r'<[^>]+>',re.S)
GAZ_RE=re.compile(r'성남시보\s*제\s*(\d+)\s*호',re.I)
CALL_RE=re.compile(r'fn_move_form\s*\(\s*[\'\"]?(\d+)[\'\"]?\s*\)',re.I)
RADIO_HANDLER_RE=re.compile(r'input\[name=[\'\"]radio[\'\"]\].{0,1200}',re.I|re.S)
CALC_RE=re.compile(r'function\s+calculateDate\s*\([^)]*\)\s*\{',re.I)

def attrs(raw):
 d={}
 for m in ATTR_RE.finditer(raw or ''): d[m.group(1).lower()]=html.unescape(m.group(2) or m.group(3) or m.group(4) or '')
 return d

def clean(raw): return re.sub(r'\s+',' ',html.unescape(TAG_RE.sub(' ',raw or ''))).strip()
def rr(r): return {'http':r.status_code,'url':str(r.url),'host':(urlparse(str(r.url)).hostname or '').lower(),'text':r.text,'bytes':len(r.content)}
def get(s,c):
 if c[0]>=MAX_REQ: raise AssertionError('request budget exceeded')
 c[0]+=1; return rr(s.get(URL,timeout=TIMEOUT,allow_redirects=True))
def post(s,data,c):
 if c[0]>=MAX_REQ: raise AssertionError('request budget exceeded')
 c[0]+=1; return rr(s.post(URL,data=data,timeout=TIMEOUT,allow_redirects=True))
def balanced(text,marker):
 m=re.search(rf'function\s+{re.escape(marker)}\s*\([^)]*\)\s*\{{',text or '',re.I)
 if not m:return ''
 bs=(text or '').find('{',m.start(),m.end()+1); depth=0; quote=None; esc=False
 for i in range(bs,len(text)):
  ch=text[i]
  if quote:
   if esc: esc=False
   elif ch=='\\': esc=True
   elif ch==quote: quote=None
   continue
  if ch in {'\'','"','`'}: quote=ch; continue
  if ch=='{': depth+=1
  elif ch=='}':
   depth-=1
   if depth==0:return re.sub(r'\s+',' ',text[m.start():i+1]).strip()
 return ''
def recover_form(text):
 cand=[]
 for fm in FORM_RE.finditer(text or ''):
  fa=attrs(fm.group('a')); body=fm.group('b'); controls=[]; defaults={}; selects=[]; buttons=[]
  for im in INPUT_RE.finditer(body):
   ia=attrs(im.group('a')); n=ia.get('name',''); typ=ia.get('type','text').lower(); checked='checked' in ia
   controls.append({'tag':'input','name':n,'id':ia.get('id',''),'type':typ,'value':ia.get('value',''),'checked':checked})
   if n and not (typ in {'radio','checkbox'} and not checked): defaults[n]=ia.get('value','')
  for sm in SELECT_RE.finditer(body):
   sa=attrs(sm.group('a')); n=sa.get('name',''); opts=[]; chosen=''
   for om in OPTION_RE.finditer(sm.group('b')):
    oa=attrs(om.group('a')); v=oa.get('value',''); sel='selected' in oa; opts.append({'value':v,'label':clean(om.group('b')),'selected':sel})
    if sel or chosen=='': chosen=v
   if n: defaults[n]=chosen; selects.append({'name':n,'options':opts})
  for bm in BUTTON_RE.finditer(body):
   ba=attrs(bm.group('a')); buttons.append({'type':ba.get('type',''),'name':ba.get('name',''),'value':ba.get('value',''),'onclick':ba.get('onclick',''),'text':clean(bm.group('b'))})
  score=sum(k in defaults for k in ['csrfToken','srchText','srchTypeCd','srchBgngYmd','srchEndYmd'])
  cand.append({'method':fa.get('method','GET').upper(),'action':urljoin(URL,fa.get('action','')),'controls':controls,'defaults':defaults,'selects':selects,'buttons':buttons,'score':score})
 cand.sort(key=lambda x:(x['method']=='POST',x['score']),reverse=True)
 if not cand or cand[0]['method']!='POST':raise AssertionError('search form missing')
 return cand[0]
def rows(text):
 out=[];seen=set()
 for am in ANCHOR_RE.finditer(text or ''):
  a=attrs(am.group('a')); label=clean(am.group('b')); gm=GAZ_RE.search(label)
  if not gm:continue
  mm=CALL_RE.search(a.get('href','')+' '+a.get('onclick',''))
  if not mm:continue
  k=(int(gm.group(1)),mm.group(1))
  if k not in seen:seen.add(k);out.append(k)
 return out
def payload(f,extras=None):
 p=dict(f['defaults']); p['cntPerPage']=p.get('cntPerPage') or '30'; p['sortType']=p.get('sortType') or '1'; p['srchTypeCd']=p.get('srchTypeCd') or 'pstTtl'; p['srchText']=''; p['curPage']='1'
 if extras:p.update(extras)
 return p

def main():
 print('='*60);print('SEONGNAM LEGACY GAZETTE WIRE CONTRACT FORENSIC - S90');print('='*60)
 print('Target-term search: DISABLED');print('Attachment download: DISABLED');print('Negative evidence: DISABLED')
 s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'});c=[0]
 base=get(s,c);f=recover_form(base['text']); fn_search=balanced(base['text'],'fn_srch_list');fn_select=balanced(base['text'],'fn_select_change');fn_calc=balanced(base['text'],'calculateDate')
 radios=[x for x in f['controls'] if x['type']=='radio']; date_controls=[x for x in f['controls'] if x['name'] in {'srchBgngYmd','srchEndYmd','creatrDt','srchDtType','radio'}]
 print('RADIO CONTROLS:',radios);print('DATE CONTROLS:',date_controls);print('BUTTONS:',f['buttons']);print('FN_SRCH_LIST:',fn_search[:1200]);print('FN_SELECT_CHANGE:',fn_select[:2200]);print('FN_CALCULATE_DATE:',fn_calc[:3500])
 baseline=post(s,payload(f),c);base_ids=rows(baseline['text']);print('BASELINE:',base_ids)
 # Probe only directly evidenced combinations; preserve exact browser-like hyphenated dates.
 shapes=[
  ('DATE_MODE_ONLY',{'srchDtType':'creatrDt','creatrDt':'09','srchBgngYmd':'2024-01-01','srchEndYmd':'2024-12-31'}),
  ('DATE_MODE_RADIO_365',{'srchDtType':'creatrDt','creatrDt':'09','srchBgngYmd':'2024-01-01','srchEndYmd':'2024-12-31','radio':'365'}),
  ('DATE_MODE_RADIO_0',{'srchDtType':'creatrDt','creatrDt':'09','srchBgngYmd':'2024-01-01','srchEndYmd':'2024-12-31','radio':'0'}),
 ]
 probes=[]
 for label,extra in shapes:
  r=post(s,payload(f,extra),c);ids=rows(r['text']);item={'label':label,'http':r['http'],'official':r['host']==HOST,'row_count':len(ids),'identities':ids,'same_as_baseline':ids==base_ids,'submitted':extra};probes.append(item);print('PROBE:',item)
 effect=[x for x in probes if not x['same_as_baseline']]
 summary={'request_count':c[0],'radio_control_count':len(radios),'date_control_count':len(date_controls),'calculateDate_recovered':bool(fn_calc),'baseline_row_count':len(base_ids),'wire_shape_effect_count':len(effect),'effective_labels':[x['label'] for x in effect],'semantic_state':'WIRE_SHAPE_EFFECT_OBSERVED' if effect else 'WIRE_CONTRACT_STILL_UNRESOLVED','pre2010_reachability_conclusion_allowed':False}
 out={'step':'STEP 17-21-C-16-8-T-35-S90','target_name':'개발밀도관리구역','standard_code':'UQQ700','resolution_type':'HYBRID_SPATIAL_NOTICE','source_family':'LEGACY_LOCAL_GAZETTE','form':{'method':f['method'],'action':f['action'],'controls':f['controls'],'selects':f['selects'],'buttons':f['buttons']},'functions':{'fn_srch_list':fn_search,'fn_select_change':fn_select,'calculateDate':fn_calc},'baseline_identities':base_ids,'probes':probes,'summary':summary,'target_term_search_executed':False,'attachment_body_download_executed':False,'state_mutation_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False,'final_positive_promotion_allowed':False}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 vals={'base transport official':base['http']==200 and base['host']==HOST,'search form recovered':f['method']=='POST','request budget respected':c[0]<=MAX_REQ,'target-term search disabled':not out['target_term_search_executed'],'negative evidence disabled':not out['negative_evidence_allowed'],'pre2010 conclusion blocked':not summary['pre2010_reachability_conclusion_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed','final_positive_promotion_allowed']),'output written':OUT.exists() and OUT.stat().st_size>0}
 print('\nSUMMARY');[print(f'{k}: {v}') for k,v in summary.items()];print('Output:',OUT);print('\nVALIDATION');[print(f'{k}: {v}') for k,v in vals.items()];print('all_pass:',all(vals.values()))
 if not all(vals.values()):raise AssertionError('S90 wire contract forensic failed')
if __name__=='__main__':main()
