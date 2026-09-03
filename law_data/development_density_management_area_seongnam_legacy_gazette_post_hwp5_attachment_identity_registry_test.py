# -*- coding: utf-8 -*-
"""S110: build POST-HWP5 attachment identity registry from detail-page JS contracts.

Input corpus: committed 1,611-row immutable snapshot lockfile.
Selected rows: gazette_number > 1872 (expected 219).

Allowed network activity:
- GET official detail pages only.
- Parse fn_get_file(<one arg>) and fn_view_file(<one arg>) contracts.

Forbidden:
- attachment body download
- target-term/body search
- legal negative evidence
- candidate/SITE/runtime promotion

The single JS argument is treated only as a technical attachment-identity token candidate until
a later bounded download-contract validation confirms its semantics.
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
LOCK = BASE / 'law_data' / 'manifests' / 'seongnam_legacy_gazette_snapshot_20260903_fd62f245.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_identity_registry.json'

HOST = 'www.seongnam.go.kr'
DETAIL_BASE = 'https://www.seongnam.go.kr/bbs010308/'
EXPECTED_POST_ROWS = 219
EXPECTED_SNAPSHOT_SHA = 'fd62f245514c00af504b55928294fe6b6c63e34ab8fdeebfe83a4c036f08977c'
MAX_REQUESTS = 219
TIMEOUT = 20
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'

CALL_RE = re.compile(r'\b(fn_get_file|fn_view_file)\s*\(\s*([\'\"])(.*?)\2\s*\)', re.I | re.S)


def compact(row):
    return {k: row.get(k) for k in ['page', 'gazette_number', 'pstSn', 'date']}


def extract_tokens(raw_html):
    found = {'fn_get_file': [], 'fn_view_file': []}
    seen = {'fn_get_file': set(), 'fn_view_file': set()}
    for m in CALL_RE.finditer(html.unescape(raw_html or '')):
        fn = m.group(1).lower()
        token = m.group(3).strip()
        if token not in seen[fn]:
            seen[fn].add(token)
            found[fn].append(token)
    return found


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 ATTACHMENT IDENTITY REGISTRY - S110')
    print('=' * 60)
    print('Attachment body download: DISABLED')
    print('Target-term search: DISABLED')
    print('Negative evidence: DISABLED')

    if not LOCK.exists():
        raise FileNotFoundError(LOCK)
    lock = json.loads(LOCK.read_text(encoding='utf-8'))
    summary = lock.get('summary') or {}
    rows = [r for r in (lock.get('canonical_rows') or []) if int(r.get('gazette_number') or 0) > 1872]
    rows.sort(key=lambda r: (int(r.get('gazette_number') or 0), int(r.get('pstSn') or 0)))

    if summary.get('identity_manifest_sha256') != EXPECTED_SNAPSHOT_SHA:
        raise AssertionError('snapshot identity mismatch')
    if len(rows) != EXPECTED_POST_ROWS:
        raise AssertionError(f'post-HWP5 row count changed: {len(rows)}')

    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9'})

    records = []
    request_count = 0
    transport_errors = []
    host_errors = []
    get_cardinality = Counter()
    view_cardinality = Counter()
    pair_equality = Counter()
    token_reuse = Counter()

    for idx, row in enumerate(rows, 1):
        if request_count >= MAX_REQUESTS:
            raise AssertionError('request budget exceeded')
        pst = str(row.get('pstSn'))
        url = DETAIL_BASE + pst
        request_count += 1
        try:
            resp = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        except Exception as exc:
            transport_errors.append({'pstSn': pst, 'error': repr(exc)[:500]})
            records.append({**compact(row), 'http_status': None, 'official_host': False, 'get_tokens': [], 'view_tokens': [], 'technical_state': 'TRANSPORT_ERROR'})
            continue

        official = (urlparse(str(resp.url)).hostname or '').lower() == HOST
        if not official:
            host_errors.append({'pstSn': pst, 'final_url': str(resp.url)[:1200]})
        tokens = extract_tokens(resp.text if resp.status_code == 200 and official else '')
        gets = tokens['fn_get_file']
        views = tokens['fn_view_file']
        get_cardinality[str(len(gets))] += 1
        view_cardinality[str(len(views))] += 1
        equal = gets == views and len(gets) > 0
        pair_equality[str(equal)] += 1
        for token in gets:
            token_reuse[token] += 1

        state = 'ATTACHMENT_IDENTITY_TOKEN_CAPTURED' if resp.status_code == 200 and official and gets else 'ATTACHMENT_IDENTITY_UNKNOWN'
        records.append({
            **compact(row),
            'detail_url': url,
            'final_url': str(resp.url)[:1200],
            'http_status': resp.status_code,
            'official_host': official,
            'get_tokens': gets,
            'view_tokens': views,
            'get_view_tokens_exact_equal': equal,
            'technical_state': state,
        })

        if idx <= 3 or idx % 25 == 0 or idx > len(rows) - 3:
            print('ROW:', idx, '/', len(rows), 'GAZETTE:', row.get('gazette_number'), 'pstSn:', pst, 'HTTP:', resp.status_code, 'GET:', len(gets), 'VIEW:', len(views), 'EQUAL:', equal)

    captured = [r for r in records if r.get('technical_state') == 'ATTACHMENT_IDENTITY_TOKEN_CAPTURED']
    unknown = [r for r in records if r.get('technical_state') != 'ATTACHMENT_IDENTITY_TOKEN_CAPTURED']
    unique_get_tokens = sorted({t for r in records for t in (r.get('get_tokens') or [])})
    reused_tokens = {k: v for k, v in token_reuse.items() if v > 1}

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S110',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_lockfile': str(LOCK),
        'snapshot_identity_sha256': summary.get('identity_manifest_sha256'),
        'selected_partition': 'POST_HWP5_BOUNDARY',
        'summary': {
            'selected_row_count': len(rows),
            'request_count': request_count,
            'captured_identity_row_count': len(captured),
            'technical_unknown_count': len(unknown),
            'transport_error_count': len(transport_errors),
            'official_host_error_count': len(host_errors),
            'get_token_cardinality_distribution': dict(sorted(get_cardinality.items(), key=lambda kv: int(kv[0]))),
            'view_token_cardinality_distribution': dict(sorted(view_cardinality.items(), key=lambda kv: int(kv[0]))),
            'get_view_pair_equality_distribution': dict(sorted(pair_equality.items())),
            'unique_get_token_count': len(unique_get_tokens),
            'reused_get_token_count': len(reused_tokens),
            'reused_get_tokens': reused_tokens,
            'semantic_state': 'POST_HWP5_ATTACHMENT_IDENTITY_REGISTRY_CAPTURED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'records': records,
        'unique_get_tokens': unique_get_tokens,
        'transport_errors': transport_errors,
        'host_errors': host_errors,
        'attachment_identity_token_semantics_confirmed': False,
        'attachment_body_download_executed': False,
        'target_term_search_executed': False,
        'candidate_promotion_allowed': False,
        'negative_evidence_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    vals = {
        'snapshot identity exact': summary.get('identity_manifest_sha256') == EXPECTED_SNAPSHOT_SHA,
        'selected row count exact': len(rows) == EXPECTED_POST_ROWS,
        'request budget exact': request_count == EXPECTED_POST_ROWS,
        'all records accounted': len(records) == EXPECTED_POST_ROWS,
        'attachment semantics unconfirmed': not out['attachment_identity_token_semantics_confirmed'],
        'attachment body download disabled': not out['attachment_body_download_executed'],
        'target-term search disabled': not out['target_term_search_executed'],
        'candidate promotion disabled': not out['candidate_promotion_allowed'],
        'negative evidence disabled': not out['negative_evidence_allowed'],
        'unsafe promotion leakage zero': not any(out[k] for k in ['site_positive_allowed', 'site_negative_allowed', 'runtime_registration_allowed']),
        'final resolution unknown': out['summary']['uqq700_final_resolution'] == 'UNKNOWN',
        'output written': OUT.exists() and OUT.stat().st_size > 0,
    }

    print('\nSUMMARY')
    for k, v in out['summary'].items():
        print(f'{k}: {v}')
    print('Output:', OUT)
    print('\nVALIDATION')
    for k, v in vals.items():
        print(f'{k}: {v}')
    print('all_pass:', all(vals.values()))
    if not all(vals.values()):
        raise AssertionError('S110 post-HWP5 attachment identity registry failed')


if __name__ == '__main__':
    main()
