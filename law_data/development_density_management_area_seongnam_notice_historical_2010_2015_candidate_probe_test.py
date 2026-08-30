# -*- coding: utf-8 -*-
"""S81: probe 2010-2015 Seongnam notice historical candidates for UQQ700 context.

Uses the validated /pm010301 search contract. It replays broad urban-planning
queries, keeps only 2010-2015 rows, then performs bounded detail-HTML inspection
for direct/related 개발밀도 context. Search/detail hits remain candidate evidence
only. No attachments, state mutation, legal negative evidence, or SITE/runtime
promotion are allowed.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_notice_historical_2010_2015_candidate_probe.json"

SEARCH_URL = "https://www.seongnam.go.kr/pm010301"
DETAIL_PREFIX = "https://www.seongnam.go.kr/pm010301/"
OFFICIAL_HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_TOTAL_REQUESTS = 36
CNT_PER_PAGE = 30
MAX_SEARCH_PAGES = 12
MAX_DETAIL_TARGETS = 18
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

QUERY_MATRIX = [("sj", "도시관리계획"), ("sj", "지형도면")]

TAG_RE = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_RE = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
ROW_RE = re.compile(r"<(tr|li)\b[^>]*>.*?</\1>", re.I | re.S)
ANCHOR_RE = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
VIEW_RE = re.compile(r"f_view\(['\"](\d+)['\"]\)", re.I)
NOTICE_RE = re.compile(r"(성남시\s*(?:[가-힣]+구\s*)?(?:고시|공고)\s*제?\s*(\d{4})\s*[-－]\s*\d+\s*호)")
DIRECT_RE = re.compile(r"개발\s*밀도\s*관리\s*구역", re.I)
RELATED_RE = re.compile(r"개발\s*밀도", re.I)


def attrs(raw: str) -> dict[str, str]:
    out={}
    for m in ATTR_RE.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def clean(raw: str) -> str:
    raw=SCRIPT_STYLE_RE.sub(" ", raw or "")
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw))).strip()


def fetch(session, url, counter, params=None):
    if counter[0] >= MAX_TOTAL_REQUESTS:
        raise AssertionError("request budget exceeded")
    counter[0]+=1
    r=session.get(url,params=params,timeout=TIMEOUT,allow_redirects=True)
    body=r.content[:MAX_RESPONSE_BYTES]
    text=body.decode(r.encoding or "utf-8",errors="replace")
    return {"http":r.status_code,"url":str(r.url),"host":(urlparse(str(r.url)).hostname or "").lower(),"text":text}


def parse_rows(text: str):
    out=[]
    for rm in ROW_RE.finditer(text or ""):
        block=rm.group(0); row_text=clean(block)
        nm=NOTICE_RE.search(row_text)
        if not nm: continue
        year=int(nm.group(2))
        if year < 2010 or year > 2015: continue
        did=None; title=""
        for am in ANCHOR_RE.finditer(block):
            aa=attrs(am.group("attrs")); vm=VIEW_RE.search(aa.get("onclick", ""))
            if vm:
                did=vm.group(1); title=clean(am.group("body")); break
        if not did: continue
        out.append({"document_id":did,"notice_number":nm.group(1),"notice_year":year,"title":title,"detail_url":DETAIL_PREFIX+did})
    return out


def contexts(text: str, pattern, radius=220, limit=8):
    out=[]
    for m in pattern.finditer(text or ""):
        s=text[max(0,m.start()-radius):min(len(text),m.end()+radius)].strip()
        if s not in out: out.append(s)
        if len(out)>=limit: break
    return out


def priority(c):
    t=(c.get('title') or '').replace(' ','')
    score=0
    if '용도구역' in t: score+=50
    if '용도지역' in t: score+=20
    if '도시관리계획' in t: score+=18
    if '지형도면' in t: score+=15
    if '결정' in t: score+=10
    if '변경' in t: score+=8
    for x in ['도로','공원','하천','주차장','학교']:
        if x in t: score-=12
    score += max(0, 2016-int(c['notice_year']))
    return score


def main():
    print('='*60); print('SEONGNAM NOTICE HISTORICAL 2010-2015 CANDIDATE PROBE - S81'); print('='*60)
    print('Attachment download: DISABLED'); print('State mutation: DISABLED'); print('Negative evidence: DISABLED')
    s=requests.Session(); s.headers.update({'User-Agent':USER_AGENT,'Accept-Language':'ko-KR,ko;q=0.9'})
    counter=[0]; canonical={}; provenance={}; search_records=[]

    for key,term in QUERY_MATRIX:
        for page in range(1,MAX_SEARCH_PAGES+1):
            rec=fetch(s,SEARCH_URL,counter,{'curPage':str(page),'cntPerPage':str(CNT_PER_PAGE),'sortType':'1','srchKey':key,'srchText':term})
            rows=parse_rows(rec['text']) if rec['http']==200 and rec['host']==OFFICIAL_HOST else []
            all_ids=VIEW_RE.findall(rec['text'])
            years=[int(y) for _,y in NOTICE_RE.findall(clean(rec['text']))]
            search_records.append({'query':term,'page':page,'http_status':rec['http'],'official_host':rec['host']==OFFICIAL_HOST,'historical_row_count':len(rows),'page_min_year':min(years) if years else None,'page_max_year':max(years) if years else None})
            for row in rows:
                canonical.setdefault(row['document_id'],row)
                provenance.setdefault(row['document_id'],[]).append({'query':term,'page':page})
            print('SEARCH:',{'query':term,'page':page,'historical_rows':len(rows),'min_year':min(years) if years else None,'max_year':max(years) if years else None})
            if not all_ids or (years and min(years) <= 2010):
                if len(set(all_ids)) < CNT_PER_PAGE or (years and max(years) <= 2010): break
            if len(set(all_ids)) < CNT_PER_PAGE: break

    candidates=[]
    for did,row in canonical.items():
        x=dict(row); x['provenance']=provenance.get(did,[]); x['priority_score']=priority(x); candidates.append(x)
    candidates.sort(key=lambda x:(-x['priority_score'],x['notice_year'],int(x['document_id'])))
    targets=candidates[:MAX_DETAIL_TARGETS]

    details=[]
    for c in targets:
        rec=fetch(s,c['detail_url'],counter)
        text=clean(rec['text'])
        direct=contexts(text,DIRECT_RE); related=contexts(text,RELATED_RE)
        cls='DIRECT_DETAIL_CANDIDATE' if direct else ('RELATED_DETAIL_CANDIDATE' if related else 'NO_TARGET_TERM_IN_DETAIL_HTML_TEXT')
        item={**c,'http_status':rec['http'],'official_host':rec['host']==OFFICIAL_HOST,'classification':cls,'direct_contexts':direct,'related_contexts':related}
        details.append(item)
        print('DETAIL:',{'id':c['document_id'],'year':c['notice_year'],'notice':c['notice_number'],'score':c['priority_score'],'classification':cls,'title':c['title']})
        if direct or related: print('  CONTEXT:',(direct or related)[:3])

    direct=sum(x['classification']=='DIRECT_DETAIL_CANDIDATE' for x in details)
    related=sum(x['classification']=='RELATED_DETAIL_CANDIDATE' for x in details)
    summary={'historical_candidate_count_2010_2015':len(candidates),'detail_target_count':len(details),'direct_detail_candidate_count':direct,'related_detail_candidate_count':related,'no_target_term_count':len(details)-direct-related,'oldest_candidate_year':min((x['notice_year'] for x in candidates),default=None),'newest_candidate_year':max((x['notice_year'] for x in candidates),default=None),'request_count':counter[0]}
    payload={'step':'STEP 17-21-C-16-8-T-35-S81','target_name':'개발밀도관리구역','standard_code':'UQQ700','resolution_type':'HYBRID_SPATIAL_NOTICE','source_family':'NOTICE_NUMBER_REVERSE_LOOKUP','search_records':search_records,'historical_candidates':candidates,'detail_records':details,'summary':summary,'attachment_body_download_executed':False,'state_mutation_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False,'final_positive_promotion_allowed':False}
    OUTPUT_PATH.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'historical candidates discovered':len(candidates)>0,'bounded detail targets':len(details)<=MAX_DETAIL_TARGETS,'all detail transport official':all(x['http_status']==200 and x['official_host'] for x in details),'request budget respected':counter[0]<=MAX_TOTAL_REQUESTS,'attachment download disabled':not payload['attachment_body_download_executed'],'state mutation disabled':not payload['state_mutation_executed'],'negative evidence disabled':not payload['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(payload[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed','final_positive_promotion_allowed']),'output written':OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size>0}
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]
    print('TOP HISTORICAL:',[(x['document_id'],x['notice_year'],x['notice_number'],x['priority_score'],x['title']) for x in candidates[:20]])
    print('Output:',OUTPUT_PATH)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S81 historical candidate probe failed')

if __name__=='__main__': main()
