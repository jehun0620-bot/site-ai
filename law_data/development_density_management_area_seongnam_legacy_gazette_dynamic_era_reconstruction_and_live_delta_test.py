# -*- coding: utf-8 -*-
"""S101: reconstruct the 1,338-row dynamic-HWP era from T23 and compare to the live 1,609-row list.

The prior cumulative state may be absent because law_data/output is not versioned. The original
selection rule is reproducible from T23 historical_row_registry_recovery.json: sort canonical
rows by parsed date, gazette number, pstSn and slice inclusively from HWP5_FIRST_PST=28675
(Gazette 526, 2004-01-12) through HWP5_LAST_PST=344241 (Gazette 1872, 2023-07-17).

This stage performs identity reconciliation only. No target-term search, detail request,
attachment request, negative evidence, SITE/runtime promotion, or legal absence inference.
"""
from __future__ import annotations
import html, json, re
from datetime import date
from pathlib import Path
from urllib.parse import urlencode, urlparse
import requests

BASE=Path(__file__).resolve().parent.parent
OUT_DIR=BASE/'law_data'/'output'; OUT_DIR.mkdir(parents=True,exist_ok=True)
T23=OUT_DIR/'development_density_management_area_municipal_gazette_historical_row_registry_recovery.json'
OUT=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_dynamic_era_reconstruction_and_live_delta.json'
URL='https://www.seongnam.go.kr/bbs010308'; HOST='www.seongnam.go.kr'; TIMEOUT=20; MAX_REQ=165
TOTAL_PAGES=162; EXPECTED_LIVE_ROWS=1609; EXPECTED_ERA_ROWS=1338
FIRST_PST='28675'; LAST_PST='344241'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
TR_RE=re.compile(r'<tr\b[^>]*>(?P<b>.*?)</tr>',re.I|re.S)
ANCHOR_RE=re.compile(r'<a\b(?P<a>[^>]*)>(?P<b>.*?)</a>',re.I|re.S)
ATTR_RE=re.compile(r'([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|\'([^\']*)\'|([^\s>]+))',re.I)
TAG_RE=re.compile(r'<[^>]+>',re.S)
GAZ_RE=re.compile(r'성남시보\s*제\s*(\d+)\s*호',re.I)
CALL_RE=re.compile(r'fn_move_form\s*\(\s*[\'\"]?(\d+)[\'\"]?\s*\)',re.I)
YEAR_RE=re.compile(r'\b((?:19|20)\d{2})\b')

def norm(v): return re.sub(r'\s+',' ',str(v or '')).strip()

def parse_date(v):
 try:
  y,m,d=[int(x) for x in norm(v).split('-')]; return date(y,m,d)
 except Exception: return None

def attrs(raw):
 out={}
 for m in ATTR_RE.finditer(raw or ''): out[m.group(1).lower()]=html.unescape(m.group(2) or m.group(3) or m.group(4) or '')
 return out

def clean(raw): return re.sub(r'\s+',' ',html.unescape(TAG_RE.sub(' ',raw or ''))).strip()

def page_url(page): return URL+'?'+urlencode({'curPage':str(page),'cntPerPage':'10','pstSn':'0','srchText':'','srchBgngYmd':'','srchEndYmd':'','sortType':'1','srchTypeCd':'pstTtl','srchDtType':''})

def parse_live_rows(text,page):
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

def main():
 print('='*60); print('SEONGNAM GAZETTE DYNAMIC ERA RECONSTRUCTION / LIVE DELTA - S101'); print('='*60)
 print('Target-term search: DISABLED'); print('Detail/attachment request: DISABLED'); print('Negative evidence: DISABLED')
 if not T23.exists():
  raise FileNotFoundError(f'T23 registry not found: {T23}')
 reg=json.loads(T23.read_text(encoding='utf-8'))
 canonical=reg.get('canonical_gazette_rows') or []
 rows=[r for r in canonical if parse_date(r.get('date')) and norm(r.get('pstSn'))]
 rows.sort(key=lambda r:(parse_date(r.get('date')),int(r.get('gazette_number') or 0),norm(r.get('pstSn'))))
 try:
  start=next(i for i,r in enumerate(rows) if norm(r.get('pstSn'))==FIRST_PST)
  end=next(i for i,r in enumerate(rows) if norm(r.get('pstSn'))==LAST_PST)
 except StopIteration as exc:
  raise AssertionError('dynamic-era boundary pstSn missing from T23 registry') from exc
 if end<start: raise AssertionError('dynamic-era boundary order invalid')
 era=rows[start:end+1]; era_ids={norm(r.get('pstSn')) for r in era}
 print('T23 CANONICAL ROWS:',len(canonical)); print('SORTABLE ROWS:',len(rows)); print('ERA ROWS:',len(era))
 print('ERA FIRST:',{k:era[0].get(k) for k in ['date','gazette_number','pstSn']}); print('ERA LAST:',{k:era[-1].get(k) for k in ['date','gazette_number','pstSn']})
 s=requests.Session(); s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'}); req=0; live=[]
 for page in range(1,TOTAL_PAGES+1):
  if req>=MAX_REQ: raise AssertionError('request budget exceeded')
  req+=1; r=s.get(page_url(page),timeout=TIMEOUT,allow_redirects=True)
  official=(urlparse(str(r.url)).hostname or '').lower()==HOST
  if r.status_code!=200 or not official: raise AssertionError(f'page {page} transport failed')
  live.extend(parse_live_rows(r.text,page))
 live_ids={x['pstSn'] for x in live}; overlap=live_ids & era_ids
 live_not_era=[x for x in live if x['pstSn'] not in era_ids]
 era_not_live=sorted(era_ids-live_ids,key=int)
 delta_years={}
 for x in live_not_era:
  for y in x['years']: delta_years[str(y)]=delta_years.get(str(y),0)+1
 before=[x for x in live_not_era if x['pstSn'].isdigit() and int(x['pstSn'])<int(FIRST_PST)]
 after=[x for x in live_not_era if x['pstSn'].isdigit() and int(x['pstSn'])>int(LAST_PST)]
 summary={'request_count':req,'t23_canonical_row_count':len(canonical),'sortable_registry_row_count':len(rows),'reconstructed_dynamic_era_row_count':len(era),'reconstructed_dynamic_era_unique_pstsn_count':len(era_ids),'live_row_count':len(live),'live_unique_pstsn_count':len(live_ids),'overlap_count':len(overlap),'live_not_dynamic_era_count':len(live_not_era),'dynamic_era_not_live_count':len(era_not_live),'dynamic_era_not_live_pstSn':era_not_live,'delta_year_counts':dict(sorted(delta_years.items())),'delta_min_page':min((x['page'] for x in live_not_era),default=None),'delta_max_page':max((x['page'] for x in live_not_era),default=None),'numeric_pst_before_first_count':len(before),'numeric_pst_after_last_count':len(after),'semantic_state':'DYNAMIC_ERA_RECONSTRUCTED_AND_LIVE_DELTA_IDENTIFIED','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'}
 out={'step':'STEP 17-21-C-16-8-T-35-S101','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'LEGACY_LOCAL_GAZETTE','dynamic_era_boundary':{'first_pstSn':FIRST_PST,'last_pstSn':LAST_PST},'summary':summary,'live_not_dynamic_era_rows':live_not_era,'target_term_search_executed':False,'detail_request_executed':False,'attachment_body_download_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 vals={'era row count exact':len(era)==EXPECTED_ERA_ROWS,'era unique exact':len(era_ids)==EXPECTED_ERA_ROWS,'live row count exact':len(live)==EXPECTED_LIVE_ROWS,'live unique exact':len(live_ids)==EXPECTED_LIVE_ROWS,'era fully present in live':not era_not_live,'overlap equals era':len(overlap)==EXPECTED_ERA_ROWS,'delta arithmetic exact':len(live_not_era)==EXPECTED_LIVE_ROWS-EXPECTED_ERA_ROWS,'request budget respected':req<=MAX_REQ,'target-term search disabled':not out['target_term_search_executed'],'detail request disabled':not out['detail_request_executed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'output written':OUT.exists() and OUT.stat().st_size>0}
 print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]; print('Output:',OUT); print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
 if not all(vals.values()): raise AssertionError('S101 dynamic-era/live delta reconciliation failed')
if __name__=='__main__': main()
