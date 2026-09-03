# -*- coding: utf-8 -*-
"""S114: recover the concrete attachment download/preview form contract.

S113 showed that fileNo is not globally unique (notably values 1 and 2 repeat), so fileNo alone
must not be treated as a stable attachment identity. This bounded forensic stage inspects the
HTML form definitions used by fn_get_file(fileNo) and fn_view_file(fileNo), capturing form
action, method, and hidden/input field names for 5 deterministic POST-HWP5 rows.

No attachment body is downloaded. No target-term search, negative evidence, candidate
promotion, SITE/runtime mutation, or legal inference is allowed.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
LOCK = BASE / 'law_data' / 'manifests' / 'seongnam_legacy_gazette_snapshot_20260903_fd62f245.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_download_form_contract_forensic.json'

HOST = 'www.seongnam.go.kr'
DETAIL_BASE = 'https://www.seongnam.go.kr/bbs010308/'
EXPECTED_SNAPSHOT_SHA = 'fd62f245514c00af504b55928294fe6b6c63e34ab8fdeebfe83a4c036f08977c'
EXPECTED_POST_ROWS = 219
MAX_REQUESTS = 5
TIMEOUT = 20
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'

FORM_RE = re.compile(r'<form\b([^>]*)>(.*?)</form>', re.I | re.S)
ATTR_RE = re.compile(r'([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.S)
INPUT_RE = re.compile(r'<input\b([^>]*)>', re.I | re.S)
GET_FN_RE = re.compile(r'function\s+fn_get_file\s*\([^)]*\)\s*\{(.*?)\}', re.I | re.S)
VIEW_FN_RE = re.compile(r'function\s+fn_view_file\s*\([^)]*\)\s*\{(.*?)\}', re.I | re.S)


def attrs(raw):
    out = {}
    for m in ATTR_RE.finditer(raw or ''):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or '')
    return out


def compact(row):
    return {k: row.get(k) for k in ['page', 'gazette_number', 'pstSn', 'date']}


def pick_sample(rows):
    return [rows[i] for i in [0, 54, 109, 163, 218]]


def parse_forms(raw_html, base_url):
    forms = []
    for m in FORM_RE.finditer(raw_html or ''):
        fa = attrs(m.group(1))
        body = m.group(2)
        inputs = []
        for im in INPUT_RE.finditer(body):
            ia = attrs(im.group(1))
            inputs.append({
                'name': ia.get('name'),
                'id': ia.get('id'),
                'type': ia.get('type'),
                'value': ia.get('value'),
            })
        form_id = fa.get('id') or ''
        form_name = fa.get('name') or ''
        if form_id in {'getFileVO', 'getFilePreviewVO'} or form_name in {'getFileVO', 'getFilePreviewVO'} or any((x.get('id') or '') in {'getFileFileNo', 'getFilePreviewFileNo'} for x in inputs):
            action = fa.get('action') or ''
            forms.append({
                'id': fa.get('id'),
                'name': fa.get('name'),
                'method': (fa.get('method') or 'get').lower(),
                'action': action,
                'resolved_action': urljoin(base_url, action) if action else base_url,
                'target': fa.get('target'),
                'enctype': fa.get('enctype'),
                'inputs': inputs,
            })
    return forms


def function_body(regex, raw_html):
    m = regex.search(raw_html or '')
    return re.sub(r'\s+', ' ', html.unescape(m.group(1))).strip()[:3000] if m else ''


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 DOWNLOAD FORM CONTRACT FORENSIC - S114')
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

    sample = pick_sample(rows)
    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9'})
    records = []
    request_count = 0
    transport_errors = []
    host_errors = []

    for idx, row in enumerate(sample, 1):
        pst = str(row.get('pstSn'))
        url = DETAIL_BASE + pst
        request_count += 1
        try:
            resp = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        except Exception as exc:
            transport_errors.append({'pstSn': pst, 'error': repr(exc)[:500]})
            records.append({**compact(row), 'http_status': None, 'forms': [], 'technical_state': 'TRANSPORT_ERROR'})
            continue
        official = (urlparse(str(resp.url)).hostname or '').lower() == HOST
        if not official:
            host_errors.append({'pstSn': pst, 'final_url': str(resp.url)[:1200]})
        forms = parse_forms(resp.text if resp.status_code == 200 and official else '', str(resp.url))
        get_body = function_body(GET_FN_RE, resp.text if resp.status_code == 200 and official else '')
        view_body = function_body(VIEW_FN_RE, resp.text if resp.status_code == 200 and official else '')
        state = 'DOWNLOAD_FORM_CONTRACT_CAPTURED' if resp.status_code == 200 and official and forms else 'DOWNLOAD_FORM_CONTRACT_UNKNOWN'
        records.append({
            **compact(row),
            'detail_url': url,
            'final_url': str(resp.url)[:1200],
            'http_status': resp.status_code,
            'official_host': official,
            'forms': forms,
            'fn_get_file_body': get_body,
            'fn_view_file_body': view_body,
            'technical_state': state,
        })
        print('SAMPLE:', idx, '/', len(sample), 'GAZETTE:', row.get('gazette_number'), 'pstSn:', pst, 'HTTP:', resp.status_code, 'FORMS:', [(f.get('id'), f.get('method'), f.get('action')) for f in forms])

    ok = [r for r in records if r.get('technical_state') == 'DOWNLOAD_FORM_CONTRACT_CAPTURED']
    unknown = [r for r in records if r.get('technical_state') != 'DOWNLOAD_FORM_CONTRACT_CAPTURED']
    signatures = {}
    for rec in ok:
        sig = json.dumps(rec.get('forms') or [], ensure_ascii=False, sort_keys=True)
        signatures[sig] = signatures.get(sig, 0) + 1

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S114',
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
            'http_success_with_form_contract_count': len(ok),
            'technical_unknown_count': len(unknown),
            'transport_error_count': len(transport_errors),
            'official_host_error_count': len(host_errors),
            'unique_form_contract_signature_count': len(signatures),
            'form_contract_signature_counts': signatures,
            'file_no_global_identity_authorized': False,
            'semantic_state': 'POST_HWP5_DOWNLOAD_FORM_CONTRACT_FORENSIC_CAPTURED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'records': records,
        'transport_errors': transport_errors,
        'host_errors': host_errors,
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
        'fileNo global identity disabled': not out['summary']['file_no_global_identity_authorized'],
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
        raise AssertionError('S114 download form contract forensic failed')


if __name__ == '__main__':
    main()
