# -*- coding: utf-8 -*-
"""S99: inventory the live /bbs010308 corpus and compare it to prior dynamic-HWP identities.

The live list boundary is known exactly: 162 pages, 1,612 rows. This stage identifies
which live row identities are not represented in locally retained dynamic-HWP output/state
JSON. Because output JSON is intentionally not committed to git, discovery is filename-
agnostic: scan law_data/output JSON files for UQQ700 municipal-gazette artifacts carrying
pstSn identities, prefer a 1,338-identity corpus if available, and union compatible files
only when needed. No detail/attachment request or UQQ700 target-term search is performed.
"""
from __future__ import annotations
import html, json, re
from pathlib import Path
from urllib.parse import urlencode, urlparse
import requests

BASE=Path(__file__).resolve().parent.parent
OUT_DIR=BASE/'law_data'/'output'; OUT_DIR.mkdir(parents=True,exist_ok=True)
OUT=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_live_vs_dynamic_hwp_delta_inventory.json'
URL='https://www.seongnam.go.kr/bbs010308'; HOST='www.seongnam.go.kr'; TIMEOUT=20; MAX_REQ=165
TOTAL_PAGES=162; EXPECTED_LIVE_ROWS=1612; EXPECTED_DYNAMIC_ROWS=1338
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
TR_RE=re.compile(r'<tr\b[^>]*>(?P<b>.*?)</tr>',re.I|re.S)
ANCHOR_RE=re.compile(r'<a\b(?P<a>[^>]*)>(?P<b>.*?)</a>',re.I|re.S)
ATTR_RE=re.compile(r'([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|\'([^\']*)\'|([^\s>]+))',re.I)
TAG_RE=re.compile(r'<[^>]+>',re.S)
GAZ_RE=re.compile(r'성남시보\s*제\s*(\d+)\s*호',re.I)
CALL_RE=re.compile(r'fn_move_form\s*\(\s*[\'\"]?(\d+)[\'\"]?\s*\)',re.I)
YEAR_RE=re.compile(r'\b((?:19|20)\d{2})\b')

def attrs(raw):
 out={}
 for m in ATTR_RE.finditer(raw or ''): out[m.group(1).lower()]=html.unescape(m.group(2) or m.group(3) or m.group(4) or '')
 return out

def clean(raw): return re.sub(r'\s+',' ',html.unescape(TAG_RE.sub(' ',raw or ''))).strip()

def page_url(page): return URL+'?'+urlencode({'curPage':str(page),'cntPerPage':'10','pstSn':'0','srchText':'','srchBgngYmd':'','srchEndYmd':'','sortType':'1','srchTypeCd':'pstTtl','srchDtType':''})

def parse_rows(text,page):
 out=[]; seen=set()
 for tm in TR_RE.finditer(text or ''):
  body=tm.group('b'); rt=clean(body); gaz=None; pst=None
  for am in ANCHOR_RE.finditer(body):
   a=attrs(am.group('a')); gm=GAZ_RE.search(clean(am.group('b')))
   if not gm: continue
   mm=CALL_RE.search(a.get('href','')+' '+a.get('onclick',''))
   if not mm: continue
   gaz=int(gm.group(1)); pst=mm.group(1); break
  if gaz is None or pst is None: continue
  key=(gaz,pst)
  if key in seen: continue
  seen.add(key); years=sorted({int(y) for y in YEAR_RE.findall(rt)})
  out.append({'page':page,'gazette_number':gaz,'pstSn':pst,'years':years,'row_text':rt[:800]})
 return out

def extract_pstsn(obj):
 vals=set()
 def walk(x):
  if isinstance(x,dict):
   for k,v in x.items():
    if str(k).lower() in {'pstsn','pst_sn','post_sn'} and str(v).isdigit(): vals.add(str(v))
    walk(v)
  elif isinstance(x,list):
   for v in x: walk(v)
 walk(obj); return vals

def discover_prior_ids():
 artifacts=[]
 for p in sorted(OUT_DIR.glob('*.json')):
  name=p.name.lower()
  if p==OUT: continue
  if 'development_density_management_area' not in name: continue
  if 'gazette' not in name: continue
  try: obj=json.loads(p.read_text(encoding='utf-8'))
  except Exception: continue
  ids=extract_pstsn(obj)
  if not ids: continue
  artifacts.append({'path':p,'count':len(ids),'ids':ids})
 exact=[a for a in artifacts if a['count']==EXPECTED_DYNAMIC_ROWS]
 if exact:
  chosen=max(exact,key=lambda a:a['path'].stat().st_mtime)
  return chosen['ids'],[chosen],artifacts,'EXACT_1338_ARTIFACT'
 # Prefer the largest individual retained artifact; if it is close to the expected corpus,
 # union all compatible artifacts to recover identities distributed across stage outputs.
 if artifacts:
  largest=max(artifacts,key=lambda a:a['count'])
  union=set()
  for a in artifacts: union.update(a['ids'])
  if len(union)==EXPECTED_DYNAMIC_ROWS:
   return union,artifacts,artifacts,'UNION_EXACT_1338'
  return largest['ids'],[largest],artifacts,'LARGEST_AVAILABLE_ARTIFACT'
 return set(),[],[],'NO_LOCAL_GAZETTE_JSON'

def main():
 print('='*60); print('SEONGNAM LEGACY GAZETTE LIVE VS DYNAMIC-HWP DELTA INVENTORY - S99'); print('='*60)
 print('Target-term search: DISABLED'); print('Detail/attachment request: DISABLED'); print('Negative evidence: DISABLED')
 prior_ids,selected,artifacts,discovery_mode=discover_prior_ids()
 print('LOCAL GAZETTE JSON ARTIFACT COUNT:',len(artifacts)); print('STATE DISCOVERY MODE:',discovery_mode)
 for a in selected: print('SELECTED STATE:',a['path'],'PSTSN',a['count'])
 print('PRIOR PSTSN COUNT:',len(prior_ids))
 if not prior_ids:
  print('No local dynamic-HWP identity artifact is retained under law_data/output.')
  print('This is a local artifact-retention issue, not legal/data negative evidence.')
  print('Available JSON sample:',[p.name for p in sorted(OUT_DIR.glob('*.json'))[:30]])
  raise FileNotFoundError('no local gazette output JSON with pstSn identities found')
 s=requests.Session(); s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'}); req=0; live=[]
 for page in range(1,TOTAL_PAGES+1):
  if req>=MAX_REQ: raise AssertionError('request budget exceeded')
  req+=1; r=s.get(page_url(page),timeout=TIMEOUT,allow_redirects=True)
  official=(urlparse(str(r.url)).hostname or '').lower()==HOST
  if r.status_code!=200 or not official: raise AssertionError(f'page {page} transport failed')
  rows=parse_rows(r.text,page); live.extend(rows)
  if page in {1,50,100,150,160,161,162}: print('PAGE',page,'ROWS',len(rows),'YEARS',sorted({y for x in rows for y in x['years']}))
 live_ids={x['pstSn'] for x in live}; dup=len(live)-len(live_ids); delta=[x for x in live if x['pstSn'] not in prior_ids]; overlap=live_ids & prior_ids
 delta_years={}
 for x in delta:
  for y in x['years']: delta_years[str(y)]=delta_years.get(str(y),0)+1
 summary={'request_count':req,'state_discovery_mode':discovery_mode,'local_gazette_artifact_count':len(artifacts),'selected_state_artifact_count':len(selected),'live_row_count':len(live),'live_unique_pstsn_count':len(live_ids),'live_duplicate_count':dup,'prior_state_unique_pstsn_count':len(prior_ids),'overlap_count':len(overlap),'live_not_in_dynamic_state_count':len(delta),'expected_live_rows':EXPECTED_LIVE_ROWS,'expected_dynamic_rows':EXPECTED_DYNAMIC_ROWS,'expected_nominal_delta':EXPECTED_LIVE_ROWS-EXPECTED_DYNAMIC_ROWS,'delta_year_counts':dict(sorted(delta_years.items())),'delta_min_page':min((x['page'] for x in delta),default=None),'delta_max_page':max((x['page'] for x in delta),default=None),'semantic_state':'LIVE_DYNAMIC_DELTA_INVENTORIED','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'}
 out={'step':'STEP 17-21-C-16-8-T-35-S99','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'LEGACY_LOCAL_GAZETTE','selected_state_paths':[str(a['path']) for a in selected],'summary':summary,'delta_rows':delta,'target_term_search_executed':False,'detail_request_executed':False,'attachment_body_download_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 vals={'state pstSn recovered':len(prior_ids)>0,'live row count exact':len(live)==EXPECTED_LIVE_ROWS,'live unique exact':len(live_ids)==EXPECTED_LIVE_ROWS,'no live duplicates':dup==0,'request budget respected':req<=MAX_REQ,'target-term search disabled':not out['target_term_search_executed'],'detail request disabled':not out['detail_request_executed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'output written':OUT.exists() and OUT.stat().st_size>0}
 print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]; print('Output:',OUT); print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
 if not all(vals.values()): raise AssertionError('S99 live/dynamic delta inventory failed')
if __name__=='__main__': main()
