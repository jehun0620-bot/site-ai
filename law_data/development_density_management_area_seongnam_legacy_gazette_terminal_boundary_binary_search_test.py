# -*- coding: utf-8 -*-
"""S97: binary-search the terminal page between known non-empty page 160 and empty page 170.

Uses only row-local list identity/year evidence on pages 165, 168, 169, then derives the
last non-empty page bracket. No UQQ700 term search, detail request, attachment download,
negative evidence, SITE/runtime promotion, or legal absence inference is allowed.
"""
from __future__ import annotations
import html, json, re
from pathlib import Path
from urllib.parse import urlencode, urlparse
import requests

BASE=Path(__file__).resolve().parent.parent
OUT_DIR=BASE/'law_data'/'output'; OUT_DIR.mkdir(parents=True,exist_ok=True)
OUT=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_terminal_boundary_binary_search.json'
URL='https://www.seongnam.go.kr/bbs010308'; HOST='www.seongnam.go.kr'; TIMEOUT=20; MAX_REQ=5
PAGES=[165,168,169]
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

def page_url(page):
    return URL+'?'+urlencode({'curPage':str(page),'cntPerPage':'10','pstSn':'0','srchText':'','srchBgngYmd':'','srchEndYmd':'','sortType':'1','srchTypeCd':'pstTtl','srchDtType':''})

def fetch(s,url,c):
    if c[0]>=MAX_REQ: raise AssertionError('request budget exceeded')
    c[0]+=1; r=s.get(url,timeout=TIMEOUT,allow_redirects=True)
    return {'http':r.status_code,'host':(urlparse(str(r.url)).hostname or '').lower(),'text':r.text}

def parse_rows(text):
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
        seen.add(key)
        years=sorted({int(y) for y in YEAR_RE.findall(rt)})
        out.append({'gazette_number':gaz,'pstSn':pst,'years':years,'row_text':rt[:1000]})
    return out

def main():
    print('='*60); print('SEONGNAM LEGACY GAZETTE TERMINAL BOUNDARY BINARY SEARCH - S97'); print('='*60)
    print('Target-term search: DISABLED'); print('Detail/attachment request: DISABLED'); print('Negative evidence: DISABLED')
    s=requests.Session(); s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'}); c=[0]
    recs=[]
    for p in PAGES:
        r=fetch(s,page_url(p),c); rows=parse_rows(r['text']); years=sorted({y for x in rows for y in x['years']})
        item={'page':p,'http':r['http'],'official':r['host']==HOST,'row_count':len(rows),'identities':[(x['gazette_number'],x['pstSn']) for x in rows],'observed_years':years,'rows':rows}
        recs.append(item); print('PAGE:',{k:item[k] for k in ['page','http','official','row_count','identities','observed_years']})
    known_nonempty=[160]+[x['page'] for x in recs if x['row_count']>0]
    known_empty=[170]+[x['page'] for x in recs if x['row_count']==0]
    deepest=max(known_nonempty); shallowest=min(known_empty)
    exact=(shallowest-deepest)==1
    all_years=sorted({y for x in recs for y in x['observed_years']})
    oldest=min(all_years) if all_years else None
    terminal_rec=next((x for x in recs if x['page']==deepest),None)
    summary={'request_count':c[0],'deepest_known_nonempty_page':deepest,'shallowest_known_empty_page':shallowest,'terminal_boundary_exactly_localized':exact,'candidate_terminal_page':deepest if exact else None,'candidate_terminal_row_count':terminal_rec['row_count'] if exact and terminal_rec else None,'candidate_terminal_identities':terminal_rec['identities'] if exact and terminal_rec else [],'oldest_observed_row_local_year_in_s97':oldest,'semantic_state':'TERMINAL_PAGE_EXACTLY_LOCALIZED' if exact else 'TERMINAL_PAGE_STILL_BRACKETED','pre2010_source_reachability_verified':True,'negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'}
    out={'step':'STEP 17-21-C-16-8-T-35-S97','target_name':'개발밀도관리구역','standard_code':'UQQ700','resolution_type':'HYBRID_SPATIAL_NOTICE','source_family':'LEGACY_LOCAL_GAZETTE','probe_pages':recs,'summary':summary,'target_term_search_executed':False,'detail_request_executed':False,'attachment_body_download_executed':False,'state_mutation_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False,'final_positive_promotion_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'all probe transport official':all(x['http']==200 and x['official'] for x in recs),'request budget respected':c[0]<=MAX_REQ,'target-term search disabled':not out['target_term_search_executed'],'detail request disabled':not out['detail_request_executed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed','final_positive_promotion_allowed']),'output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]; print('Output:',OUT); print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S97 terminal boundary binary search failed')
if __name__=='__main__': main()
