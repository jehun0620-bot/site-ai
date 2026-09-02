# -*- coding: utf-8 -*-
"""S103: capture an immutable identity manifest of the current Seongnam gazette archive.

This stage intentionally starts a NEW current-snapshot processing lineage after S102 proved
that the historical 1,338-row dynamic-HWP identity snapshot cannot be reconstructed exactly
from mutable live inputs.

Scope / safety
--------------
- list pages only: https://www.seongnam.go.kr/bbs010308
- no UQQ700 target-term search
- no detail request
- no attachment request/download
- no negative evidence
- no SITE/runtime promotion
- canonical identity is pstSn; gazette number/date/page are row-local metadata
- page 163 is checked as the previously established first-empty boundary guard

The JSON output is the immutable local manifest for subsequent stages. Later stages must read
this file rather than re-derive their processing corpus directly from the mutable live list.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_current_archive_immutable_manifest.json'

URL = 'https://www.seongnam.go.kr/bbs010308'
HOST = 'www.seongnam.go.kr'
LAST_KNOWN_NONEMPTY_PAGE = 162
BOUNDARY_GUARD_PAGE = 163
MAX_REQUESTS = 163
TIMEOUT = 20
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'

TR_RE = re.compile(r'<tr\b[^>]*>(?P<body>.*?)</tr>', re.I | re.S)
ANCHOR_RE = re.compile(r'<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>', re.I | re.S)
ATTR_RE = re.compile(r'([:\w-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.I)
TAG_RE = re.compile(r'<[^>]+>', re.S)
GAZ_RE = re.compile(r'성남시보\s*제\s*(\d+)\s*호', re.I)
CALL_RE = re.compile(r'fn_move_form\s*\(\s*[\'\"]?(\d+)[\'\"]?\s*\)', re.I)
DATE_RE = re.compile(r'\b((?:19|20)\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})\b')


def norm(v):
    return re.sub(r'\s+', ' ', str(v or '')).strip()


def attrs(raw):
    out = {}
    for m in ATTR_RE.finditer(raw or ''):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or '')
    return out


def clean(raw):
    return norm(html.unescape(TAG_RE.sub(' ', raw or '')))


def row_date(text):
    m = DATE_RE.search(text or '')
    if not m:
        return ''
    try:
        return f'{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'
    except Exception:
        return ''


def page_url(page):
    return URL + '?' + urlencode({
        'curPage': str(page),
        'cntPerPage': '10',
        'pstSn': '0',
        'srchText': '',
        'srchBgngYmd': '',
        'srchEndYmd': '',
        'sortType': '1',
        'srchTypeCd': 'pstTtl',
        'srchDtType': '',
    })


def parse_rows(raw_html, page):
    rows = []
    seen = set()
    for tm in TR_RE.finditer(raw_html or ''):
        body = tm.group('body')
        text = clean(body)
        gazette = None
        pst = None
        for am in ANCHOR_RE.finditer(body):
            gm = GAZ_RE.search(clean(am.group('body')))
            if not gm:
                continue
            a = attrs(am.group('attrs'))
            mm = CALL_RE.search(a.get('href', '') + ' ' + a.get('onclick', ''))
            if not mm:
                continue
            gazette = int(gm.group(1))
            pst = mm.group(1)
            break
        if gazette is None or pst is None:
            continue
        if pst in seen:
            continue
        seen.add(pst)
        rows.append({
            'page': page,
            'gazette_number': gazette,
            'pstSn': pst,
            'date': row_date(text),
            'row_text': text[:1000],
        })
    return rows


def digest(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE CURRENT ARCHIVE IMMUTABLE MANIFEST - S103')
    print('=' * 60)
    print('Target-term search: DISABLED')
    print('Detail/attachment request: DISABLED')
    print('Negative evidence: DISABLED')
    print('Historical snapshot substitution: DISABLED')

    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9'})

    request_count = 0
    rows = []
    page_manifest = []

    for page in range(1, BOUNDARY_GUARD_PAGE + 1):
        if request_count >= MAX_REQUESTS:
            raise AssertionError('request budget exceeded')
        request_count += 1
        response = session.get(page_url(page), timeout=TIMEOUT, allow_redirects=True)
        official = (urlparse(str(response.url)).hostname or '').lower() == HOST
        if response.status_code != 200 or not official:
            raise AssertionError(f'page {page} transport/host validation failed')

        parsed = parse_rows(response.text, page)
        identities = [
            {'gazette_number': r['gazette_number'], 'pstSn': r['pstSn'], 'date': r['date']}
            for r in parsed
        ]
        page_manifest.append({
            'page': page,
            'row_count': len(parsed),
            'identity_sha256': digest(identities),
            'first_identity': identities[0] if identities else None,
            'last_identity': identities[-1] if identities else None,
        })
        if page <= LAST_KNOWN_NONEMPTY_PAGE:
            rows.extend(parsed)

        if page <= 3 or page % 20 == 0 or page >= LAST_KNOWN_NONEMPTY_PAGE - 2:
            print('PAGE:', page, 'ROWS:', len(parsed),
                  'FIRST:', identities[0] if identities else None,
                  'LAST:', identities[-1] if identities else None)

    pst_ids = [r['pstSn'] for r in rows]
    unique_ids = set(pst_ids)
    duplicate_pst = sorted({x for x in pst_ids if pst_ids.count(x) > 1}, key=int)
    nonempty_pages = [p['page'] for p in page_manifest if p['row_count'] > 0]
    empty_pages = [p['page'] for p in page_manifest if p['row_count'] == 0]

    identity_projection = [
        {
            'page': r['page'],
            'gazette_number': r['gazette_number'],
            'pstSn': r['pstSn'],
            'date': r['date'],
        }
        for r in rows
    ]
    identity_sha = digest(identity_projection)
    pstsn_set_sha = digest(sorted(unique_ids, key=int))
    captured_at = datetime.now(timezone.utc).isoformat()

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S103',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'resolution_type': 'HYBRID_SPATIAL_NOTICE',
        'snapshot_policy': {
            'snapshot_type': 'CURRENT_OFFICIAL_ARCHIVE_IDENTITY_MANIFEST',
            'captured_at_utc': captured_at,
            'source_url': URL,
            'immutable_after_capture': True,
            'historical_1338_snapshot_substitution_allowed': False,
            'subsequent_stage_live_recrawl_as_corpus_input_allowed': False,
        },
        'summary': {
            'request_count': request_count,
            'last_known_nonempty_page': LAST_KNOWN_NONEMPTY_PAGE,
            'boundary_guard_page': BOUNDARY_GUARD_PAGE,
            'manifest_row_count': len(rows),
            'manifest_unique_pstsn_count': len(unique_ids),
            'duplicate_pstsn_count': len(duplicate_pst),
            'duplicate_pstSn': duplicate_pst,
            'nonempty_pages': nonempty_pages,
            'empty_pages': empty_pages,
            'identity_manifest_sha256': identity_sha,
            'pstsn_set_sha256': pstsn_set_sha,
            'semantic_state': 'CURRENT_ARCHIVE_IMMUTABLE_MANIFEST_CAPTURED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'page_manifest': page_manifest,
        'canonical_rows': rows,
        'target_term_search_executed': False,
        'detail_request_executed': False,
        'attachment_body_download_executed': False,
        'negative_evidence_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    page162 = next(p for p in page_manifest if p['page'] == LAST_KNOWN_NONEMPTY_PAGE)
    page163 = next(p for p in page_manifest if p['page'] == BOUNDARY_GUARD_PAGE)
    vals = {
        'request budget exact': request_count == MAX_REQUESTS,
        'page 162 remains nonempty': page162['row_count'] > 0,
        'page 163 remains empty': page163['row_count'] == 0,
        'all corpus pages nonempty': all(p['row_count'] > 0 for p in page_manifest if p['page'] <= LAST_KNOWN_NONEMPTY_PAGE),
        'canonical rows recovered': len(rows) > 0,
        'pstSn globally unique': len(rows) == len(unique_ids) and not duplicate_pst,
        'identity hash present': len(identity_sha) == 64,
        'pstSn set hash present': len(pstsn_set_sha) == 64,
        'historical substitution disabled': not out['snapshot_policy']['historical_1338_snapshot_substitution_allowed'],
        'future live recrawl disabled as corpus input': not out['snapshot_policy']['subsequent_stage_live_recrawl_as_corpus_input_allowed'],
        'target-term search disabled': not out['target_term_search_executed'],
        'detail request disabled': not out['detail_request_executed'],
        'negative evidence disabled': not out['negative_evidence_allowed'],
        'unsafe promotion leakage zero': not any(out[k] for k in ['site_positive_allowed', 'site_negative_allowed', 'runtime_registration_allowed']),
        'final resolution unknown': out['summary']['uqq700_final_resolution'] == 'UNKNOWN',
        'output written': OUT.exists() and OUT.stat().st_size > 0,
    }

    print('\nSUMMARY')
    for k, v in out['summary'].items():
        print(f'{k}: {v}')
    print('captured_at_utc:', captured_at)
    print('Output:', OUT)
    print('\nVALIDATION')
    for k, v in vals.items():
        print(f'{k}: {v}')
    print('all_pass:', all(vals.values()))
    if not all(vals.values()):
        raise AssertionError('S103 immutable current archive manifest capture failed')


if __name__ == '__main__':
    main()
