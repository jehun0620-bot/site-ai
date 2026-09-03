# -*- coding: utf-8 -*-
"""S111: recover the real attachment identity contract from JavaScript template construction.

S110 proved that a naive fn_get_file(<quoted arg>) regex captured JavaScript source text such
as "+ item.fileNo; html +=" rather than a concrete file identifier. This stage therefore
invalidates S110 token semantics and performs a bounded forensic capture of JavaScript
function definitions, template-building snippets, AJAX/file-list endpoints, and item fields.

Network scope: official detail HTML for 5 deterministic POST-HWP5 sample rows only.
No attachment body download. No UQQ700 target search. No legal inference.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
LOCK = BASE / 'law_data' / 'manifests' / 'seongnam_legacy_gazette_snapshot_20260903_fd62f245.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_javascript_template_forensic.json'

HOST = 'www.seongnam.go.kr'
DETAIL_BASE = 'https://www.seongnam.go.kr/bbs010308/'
EXPECTED_SNAPSHOT_SHA = 'fd62f245514c00af504b55928294fe6b6c63e34ab8fdeebfe83a4c036f08977c'
EXPECTED_POST_ROWS = 219
MAX_REQUESTS = 5
TIMEOUT = 20
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'

SCRIPT_RE = re.compile(r'<script\b[^>]*>(.*?)</script>', re.I | re.S)
FUNC_DEF_RE = re.compile(r'(?:function\s+)?(fn_get_file|fn_view_file)\s*\(([^)]*)\)\s*\{', re.I)
URLISH_RE = re.compile(r'''(?P<q>["'])(?P<url>[^"']*(?:file|atch|attach|download)[^"']*)(?P=q)''', re.I)
ITEM_FIELD_RE = re.compile(r'\bitem\.([A-Za-z_$][\w$]*)')
FILE_NO_RE = re.compile(r'\bfileNo\b', re.I)
AJAX_RE = re.compile(r'\$\.(?:ajax|get|post)\s*\(|\bfetch\s*\(', re.I)


def compact(row):
    return {k: row.get(k) for k in ['page', 'gazette_number', 'pstSn', 'date']}


def norm(v):
    return re.sub(r'\s+', ' ', str(v or '')).strip()


def pick_sample(rows):
    return [rows[i] for i in [0, 54, 109, 163, 218]]


def snippets_around(text, patterns, radius=700, limit=20):
    positions = []
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            positions.append(m.start())
    out = []
    for pos in sorted(set(positions)):
        s = max(0, pos - radius)
        e = min(len(text), pos + radius)
        snip = norm(text[s:e])[:2500]
        if snip and snip not in out:
            out.append(snip)
        if len(out) >= limit:
            break
    return out


def analyze(raw_html):
    decoded = html.unescape(raw_html or '')
    scripts = SCRIPT_RE.findall(decoded)
    relevant_scripts = []
    function_defs = []
    url_candidates = []
    item_fields = set()
    ajax_snippets = []

    for idx, script in enumerate(scripts):
        if not re.search(r'(fn_get_file|fn_view_file|fileNo|첨부|download|atch|attach)', script, re.I):
            continue
        relevant_scripts.append({'script_index': idx, 'length': len(script), 'excerpt': norm(script)[:6000]})
        for m in FUNC_DEF_RE.finditer(script):
            function_defs.append({
                'function': m.group(1),
                'params': [norm(x) for x in m.group(2).split(',') if norm(x)],
                'snippet': snippets_around(script, [re.escape(m.group(1))], radius=900, limit=1)[0] if snippets_around(script, [re.escape(m.group(1))], radius=900, limit=1) else '',
            })
        for m in URLISH_RE.finditer(script):
            val = norm(m.group('url'))
            if val and val not in url_candidates:
                url_candidates.append(val[:1200])
        for m in ITEM_FIELD_RE.finditer(script):
            item_fields.add(m.group(1))
        if AJAX_RE.search(script):
            ajax_snippets.extend(snippets_around(script, [r'\$\.ajax', r'\$\.get', r'\$\.post', r'\bfetch\s*\('], radius=900, limit=10))

    template_snippets = snippets_around(decoded, [r'fn_get_file', r'fn_view_file', r'item\.fileNo', r'fileNo'], radius=850, limit=20)
    return {
        'script_count': len(scripts),
        'relevant_script_count': len(relevant_scripts),
        'relevant_scripts': relevant_scripts[:10],
        'function_definitions': function_defs[:20],
        'url_candidates': url_candidates[:50],
        'item_fields': sorted(item_fields),
        'contains_fileNo': bool(FILE_NO_RE.search(decoded)),
        'ajax_snippets': ajax_snippets[:20],
        'template_snippets': template_snippets[:20],
    }


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 ATTACHMENT JAVASCRIPT TEMPLATE FORENSIC - S111')
    print('=' * 60)
    print('S110 token semantics: INVALIDATED')
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

    sample = pick_sample(rows)
    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9'})
    records = []
    request_count = 0
    transport_errors = []
    host_errors = []

    for idx, row in enumerate(sample, 1):
        if request_count >= MAX_REQUESTS:
            raise AssertionError('request budget exceeded')
        pst = str(row.get('pstSn'))
        url = DETAIL_BASE + pst
        request_count += 1
        try:
            resp = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        except Exception as exc:
            transport_errors.append({'pstSn': pst, 'error': repr(exc)[:500]})
            records.append({**compact(row), 'http_status': None, 'official_host': False, 'analysis': {}, 'technical_state': 'TRANSPORT_ERROR'})
            continue
        official = (urlparse(str(resp.url)).hostname or '').lower() == HOST
        if not official:
            host_errors.append({'pstSn': pst, 'final_url': str(resp.url)[:1200]})
        ana = analyze(resp.text if resp.status_code == 200 and official else '')
        state = 'JAVASCRIPT_TEMPLATE_EVIDENCE_CAPTURED' if resp.status_code == 200 and official else 'DETAIL_REQUEST_UNKNOWN'
        records.append({**compact(row), 'detail_url': url, 'final_url': str(resp.url)[:1200], 'http_status': resp.status_code, 'official_host': official, 'analysis': ana, 'technical_state': state})
        print('SAMPLE:', idx, '/', len(sample), 'GAZETTE:', row.get('gazette_number'), 'pstSn:', pst, 'HTTP:', resp.status_code, 'RELEVANT_SCRIPTS:', ana['relevant_script_count'], 'FUNCTION_DEFS:', len(ana['function_definitions']), 'URLS:', len(ana['url_candidates']), 'ITEM_FIELDS:', ana['item_fields'])

    ok = [r for r in records if r.get('technical_state') == 'JAVASCRIPT_TEMPLATE_EVIDENCE_CAPTURED']
    all_fields = sorted({f for r in ok for f in (r.get('analysis') or {}).get('item_fields', [])})
    all_urls = []
    for r in ok:
        for u in (r.get('analysis') or {}).get('url_candidates', []):
            if u not in all_urls:
                all_urls.append(u)
    all_functions = []
    for r in ok:
        for f in (r.get('analysis') or {}).get('function_definitions', []):
            key = (f.get('function'), tuple(f.get('params') or []), f.get('snippet'))
            if key not in [(x.get('function'), tuple(x.get('params') or []), x.get('snippet')) for x in all_functions]:
                all_functions.append(f)

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S111',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_lockfile': str(LOCK),
        'snapshot_identity_sha256': summary.get('identity_manifest_sha256'),
        'selected_partition': 'POST_HWP5_BOUNDARY',
        'sample_strategy': 'DETERMINISTIC_STRATIFIED_5_OF_219',
        'summary': {
            'post_partition_row_count': len(rows),
            'sample_row_count': len(sample),
            'request_count': request_count,
            'http_success_count': len(ok),
            'transport_error_count': len(transport_errors),
            'official_host_error_count': len(host_errors),
            'aggregate_item_fields': all_fields,
            'aggregate_url_candidates': all_urls,
            'aggregate_function_definitions': all_functions,
            's110_token_semantics_valid': False,
            'semantic_state': 'POST_HWP5_ATTACHMENT_JAVASCRIPT_TEMPLATE_FORENSIC_CAPTURED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'records': records,
        'transport_errors': transport_errors,
        'host_errors': host_errors,
        's110_identity_registry_authoritative': False,
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
        'post partition count exact': len(rows) == EXPECTED_POST_ROWS,
        'sample count exact': len(sample) == MAX_REQUESTS,
        'request budget exact': request_count == MAX_REQUESTS,
        'all sample records accounted': len(records) == MAX_REQUESTS,
        's110 registry deauthorized': not out['s110_identity_registry_authoritative'],
        's110 token semantics invalid': not out['summary']['s110_token_semantics_valid'],
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
        raise AssertionError('S111 attachment JavaScript template forensic failed')


if __name__ == '__main__':
    main()
