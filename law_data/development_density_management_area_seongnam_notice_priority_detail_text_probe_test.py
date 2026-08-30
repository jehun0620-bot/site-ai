# -*- coding: utf-8 -*-
"""S79: bounded detail-text probe for top S78 Seongnam notice candidates.

Fetches only the top priority records whose titles include 용도구역, inspects
official detail HTML text for direct/strong UQQ700 context, and preserves
candidate-only semantics. No attachment download, state mutation, or legal
negative evidence is allowed.
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
INPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_notice_candidate_triage.json"
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_notice_priority_detail_text_probe.json"

OFFICIAL_HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_TOTAL_REQUESTS = 10
MAX_TARGETS = 8
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

TAG_RE = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_RE = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
DIRECT_RE = re.compile(r"개발\s*밀도\s*관리\s*구역", re.I)
RELATED_RE = re.compile(r"개발\s*밀도", re.I)
STRONG_CONTEXT_RES = [
    re.compile(r"도시관리계획.{0,120}개발\s*밀도", re.I),
    re.compile(r"개발\s*밀도.{0,120}(?:관리구역|용도구역|지정|결정|변경|고시)", re.I),
    re.compile(r"(?:관리구역|용도구역|지정|결정|변경).{0,120}개발\s*밀도", re.I),
]


def clean_html(raw: str) -> str:
    raw = SCRIPT_STYLE_RE.sub(" ", raw or "")
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw))).strip()


def contexts(text: str, pattern: re.Pattern, radius: int = 180, limit: int = 8):
    out=[]
    for m in pattern.finditer(text or ""):
        lo=max(0,m.start()-radius); hi=min(len(text),m.end()+radius)
        snippet=text[lo:hi].strip()
        if snippet not in out:
            out.append(snippet)
        if len(out)>=limit:
            break
    return out


def fetch(session, url, counter):
    if counter[0]>=MAX_TOTAL_REQUESTS:
        raise AssertionError("request budget exceeded")
    counter[0]+=1
    r=session.get(url,timeout=TIMEOUT,allow_redirects=True)
    body=r.content[:MAX_RESPONSE_BYTES]
    text=body.decode(r.encoding or "utf-8",errors="replace")
    return {"http_status":r.status_code,"final_url":str(r.url),"final_host":(urlparse(str(r.url)).hostname or "").lower(),"body_bytes_read":len(body),"html":text}


def main():
    print('='*60); print('SEONGNAM NOTICE PRIORITY DETAIL TEXT PROBE - S79'); print('='*60)
    print('Attachment download: DISABLED'); print('State mutation: DISABLED'); print('Negative evidence: DISABLED')
    if not INPUT_PATH.exists(): raise FileNotFoundError(INPUT_PATH)
    src=json.loads(INPUT_PATH.read_text(encoding='utf-8'))
    pool=src.get('priority_pool') or []
    targets=[r for r in pool if '용도구역' in str(r.get('title') or '')][:MAX_TARGETS]
    if not targets:
        raise AssertionError('no 용도구역 priority targets')

    s=requests.Session(); s.headers.update({'User-Agent':USER_AGENT,'Accept-Language':'ko-KR,ko;q=0.9'})
    counter=[0]; records=[]
    for t in targets:
        rec=fetch(s,t['detail_url'],counter)
        text=clean_html(rec.pop('html'))
        direct=contexts(text,DIRECT_RE)
        related=contexts(text,RELATED_RE)
        strong=[]
        for p in STRONG_CONTEXT_RES:
            for c in contexts(text,p):
                if c not in strong: strong.append(c)
        classification='DIRECT_DETAIL_TEXT_CANDIDATE' if direct else ('STRONG_CONTEXT_DETAIL_CANDIDATE' if strong else ('RELATED_DETAIL_TEXT_CANDIDATE' if related else 'NO_TARGET_TERM_IN_DETAIL_HTML_TEXT'))
        item={
            'document_id':t['document_id'],
            'notice_number':t['notice_number'],
            'title':t['title'],
            'triage_score':t['triage_score'],
            'detail_url':t['detail_url'],
            **rec,
            'detail_text_chars':len(text),
            'direct_contexts':direct,
            'strong_contexts':strong[:8],
            'related_contexts':related[:8],
            'classification':classification,
        }
        records.append(item)
        print('RECORD:', {'id':item['document_id'],'notice':item['notice_number'],'http':item['http_status'],'classification':classification,'direct':len(direct),'strong':len(strong),'related':len(related)})
        if classification in {'DIRECT_DETAIL_TEXT_CANDIDATE','STRONG_CONTEXT_DETAIL_CANDIDATE'}:
            print('  CONTEXT:', (direct or strong)[:3])

    direct_count=sum(r['classification']=='DIRECT_DETAIL_TEXT_CANDIDATE' for r in records)
    strong_count=sum(r['classification']=='STRONG_CONTEXT_DETAIL_CANDIDATE' for r in records)
    related_count=sum(r['classification']=='RELATED_DETAIL_TEXT_CANDIDATE' for r in records)
    summary={
        'target_count':len(records),
        'all_http_200':all(r['http_status']==200 for r in records),
        'all_official_host':all(r['final_host']==OFFICIAL_HOST for r in records),
        'direct_detail_candidate_count':direct_count,
        'strong_context_detail_candidate_count':strong_count,
        'related_detail_candidate_count':related_count,
        'no_target_term_count':len(records)-direct_count-strong_count-related_count,
        'request_count':counter[0],
    }
    payload={
        'step':'STEP 17-21-C-16-8-T-35-S79',
        'target_name':'개발밀도관리구역',
        'standard_code':'UQQ700',
        'resolution_type':'HYBRID_SPATIAL_NOTICE',
        'source_family':'NOTICE_NUMBER_REVERSE_LOOKUP',
        'records':records,
        'summary':summary,
        'attachment_body_download_executed':False,
        'state_mutation_executed':False,
        'negative_evidence_allowed':False,
        'site_positive_allowed':False,
        'site_negative_allowed':False,
        'runtime_registration_allowed':False,
        'final_positive_promotion_allowed':False,
    }
    OUTPUT_PATH.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={
        'bounded targets inspected':0<len(records)<=MAX_TARGETS,
        'detail transport ok':summary['all_http_200'] and summary['all_official_host'],
        'request budget respected':counter[0]<=MAX_TOTAL_REQUESTS,
        'attachment download disabled':not payload['attachment_body_download_executed'],
        'state mutation disabled':not payload['state_mutation_executed'],
        'negative evidence disabled':not payload['negative_evidence_allowed'],
        'unsafe promotion leakage zero':not any(payload[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed','final_positive_promotion_allowed']),
        'output written':OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size>0,
    }
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]; print('Output:',OUTPUT_PATH)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S79 priority detail text probe failed')

if __name__=='__main__': main()
