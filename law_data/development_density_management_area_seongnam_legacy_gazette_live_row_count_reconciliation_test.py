# -*- coding: utf-8 -*-
"""S100: reconcile the live /bbs010308 row count after S99 observed 1,609 parsed rows.

S98 inferred 1,612 from terminal page arithmetic (161 full pages + 2 rows). S99's full
scan parsed 1,609 rows. This stage locates the three-row discrepancy by recording, for every
page, both raw gazette-title anchor occurrences and strict row-local parsed identities.
No UQQ700 target-term search, detail request, attachment request, negative evidence, or
SITE/runtime promotion is allowed.
"""
from __future__ import annotations
import html, json, re
from pathlib import Path
from urllib.parse import urlencode, urlparse
import requests

BASE=Path(__file__).resolve().parent.parent
OUT_DIR=BASE/'law_data'/'output'; OUT_DIR.mkdir(parents=True,exist_ok=True)
OUT=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_live_row_count_reconciliation.json'
URL='https://www.seongnam.go.kr/bbs010308'; HOST='www.seongnam.go.kr'; TIMEOUT=20; MAX_REQ=165
TOTAL_PAGES=162
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
 out=[]; seen=set(); orphan=[]
 for tm in TR_RE.finditer(text or ''):
  body=tm.group('b'); rt=clean(body); gaz_matches=[]
  for am in ANCHOR_RE.finditer(body):
   a=attrs(am.group('a')); anchor_text=clean(am.group('b')); gm=GAZ_RE.search(anchor_text)
   if not gm: continue
   gaz_matches.append({'gazette_number':int(gm.group(1)),'anchor_text':anchor_text,'href':a.get('href',''),'onclick':a.get('onclick','')})
  if not gaz_matches: continue
  accepted=False
  for g in gaz_matches:
   mm=CALL_RE.search(g['href']+' '+g['onclick'])
   if not mm: continue
   gaz=g['gazette_number']; pst=mm.group(1); key=(gaz,pst)
   if key in seen: continue
   seen.add(key); years=sorted({int(y) for y in YEAR_RE.findall(rt)})
   out.append({'page':page,'gazette_number':gaz,'pstSn':pst,'years':years,'row_text':rt[:1200]}); accepted=True; break
  if not accepted:
   orphan.append({'page':page,'gazette_anchors':gaz_matches,'row_text':rt[:1600]})
 return out,orphan

def raw_gazette_anchors(text):
 vals=[]
 for am in ANCHOR_RE.finditer(text or ''):
  t=clean(am.group('b')); gm=GAZ_RE.search(t)
  if gm:
   a=attrs(am.group('a')); vals.append({'gazette_number':int(gm.group(1)),'text':t,'href':a.get('href',''),'onclick':a.get('onclick','')})
 return vals

def main():
 print('='*60); print('SEONGNAM LEGACY GAZETTE LIVE ROW COUNT RECONCILIATION - S100'); print('='*60)
 print('Target-term search: DISABLED'); print('Detail/attachment request: DISABLED'); print('Negative evidence: DISABLED')
 s=requests.Session(); s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'}); req=0; pages=[]; all_rows=[]; all_orphans=[]
 for page in range(1,TOTAL_PAGES+1):
  if req>=MAX_REQ: raise AssertionError('request budget exceeded')
  req+=1; r=s.get(page_url(page),timeout=TIMEOUT,allow_redirects=True)
  official=(urlparse(str(r.url)).hostname or '').lower()==HOST
  if r.status_code!=200 or not official: raise AssertionError(f'page {page} transport failed')
  rows,orphans=parse_rows(r.text,page); raw=raw_gazette_anchors(r.text)
  rec={'page':page,'http':r.status_code,'official':official,'raw_gazette_anchor_count':len(raw),'parsed_row_count':len(rows),'orphan_row_count':len(orphans),'identities':[(x['gazette_number'],x['pstSn']) for x in rows],'observed_years':sorted({y for x in rows for y in x['years']})}
  pages.append(rec); all_rows.extend(rows); all_orphans.extend(orphans)
  if len(rows)!=10 or len(raw)!=len(rows) or orphans:
   print('ANOMALY PAGE:',rec)
 parsed_ids={x['pstSn'] for x in all_rows}; duplicate_count=len(all_rows)-len(parsed_ids)
 short_pages=[x for x in pages if x['parsed_row_count']<10]
 parser_gap_pages=[x for x in pages if x['raw_gazette_anchor_count']!=x['parsed_row_count'] or x['orphan_row_count']>0]
 raw_total=sum(x['raw_gazette_anchor_count'] for x in pages); parsed_total=sum(x['parsed_row_count'] for x in pages)
 summary={'request_count':req,'page_count':len(pages),'raw_gazette_anchor_total':raw_total,'parsed_row_total':parsed_total,'parsed_unique_pstsn_total':len(parsed_ids),'parsed_duplicate_count':duplicate_count,'short_page_count':len(short_pages),'short_pages':[(x['page'],x['parsed_row_count']) for x in short_pages],'parser_gap_page_count':len(parser_gap_pages),'parser_gap_pages':[(x['page'],x['raw_gazette_anchor_count'],x['parsed_row_count'],x['orphan_row_count']) for x in parser_gap_pages],'terminal_page':162,'terminal_page_row_count':pages[-1]['parsed_row_count'],'semantic_state':'LIVE_ROW_COUNT_RECONCILED' if raw_total==parsed_total and duplicate_count==0 else 'PARSER_GAP_REQUIRES_FORENSIC','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'}
 out={'step':'STEP 17-21-C-16-8-T-35-S100','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'LEGACY_LOCAL_GAZETTE','pages':pages,'orphan_rows':all_orphans,'summary':summary,'target_term_search_executed':False,'detail_request_executed':False,'attachment_body_download_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 vals={'all transport official':all(x['http']==200 and x['official'] for x in pages),'request budget respected':req<=MAX_REQ,'all pages observed':len(pages)==TOTAL_PAGES,'no parsed duplicates':duplicate_count==0,'target-term search disabled':not out['target_term_search_executed'],'detail request disabled':not out['detail_request_executed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'output written':OUT.exists() and OUT.stat().st_size>0}
 print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]; print('Output:',OUT); print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
 if not all(vals.values()): raise AssertionError('S100 live row count reconciliation failed')
if __name__=='__main__': main()
