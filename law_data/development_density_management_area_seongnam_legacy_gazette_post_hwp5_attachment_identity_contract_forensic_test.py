# -*- coding: utf-8 -*-
"""S109: recover attachment identity/download contract from POST-HWP5 detail HTML.

This is a bounded forensic stage over a small stratified sample of the locked POST-HWP5
partition. It may request official detail HTML, but it does NOT download attachment bodies
and does NOT search UQQ700 terms. The goal is to discover the concrete filename / file-id /
JavaScript argument contract hidden behind the uniform download/view/helper action links.
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
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_identity_contract_forensic.json'

HOST = 'www.seongnam.go.kr'
DETAIL_BASE = 'https://www.seongnam.go.kr/bbs010308/'
EXPECTED_SNAPSHOT_SHA = 'fd62f245514c00af504b55928294fe6b6c63e34ab8fdeebfe83a4c036f08977c'
EXPECTED_POST_ROWS = 219
MAX_REQUESTS = 9
TIMEOUT = 20
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'

# Broad patterns for file names and file-ish identifiers, without target-term searching.
FILENAME_RE = re.compile(r'([^\s<>"\']+\.(?:hwp|hwpx|pdf|docx?|xlsx?|zip))', re.I)
ONCLICK_RE = re.compile(r'onclick\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', re.I)
HREF_RE = re.compile(r'href\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', re.I)
FUNC_CALL_RE = re.compile(r'([A-Za-z_$][\w$]*)\s*\(([^)]{0,2000})\)', re.S)
ARG_RE = re.compile(r'[\'\"]([^\'\"]*)[\'\"]|(-?\d+)')
FILE_CONTEXT_RE = re.compile(r'(download|file|atch|attach|첨부|미리보기|hwp|hwpx|pdf)', re.I)
TAG_RE = re.compile(r'<[^>]+>', re.S)


def norm(v):
    return re.sub(r'\s+', ' ', str(v or '')).strip()


def compact(row):
    return {k: row.get(k) for k in ['page', 'gazette_number', 'pstSn', 'date']}


def pick_sample(rows):
    # 9 deterministic stratified positions spanning the fixed 219-row partition.
    idxs = [0, 27, 54, 81, 109, 136, 163, 190, 218]
    return [rows[i] for i in idxs]


def extract_contract(raw_html):
    filenames = []
    seen_names = set()
    for m in FILENAME_RE.finditer(html.unescape(raw_html or '')):
        name = norm(m.group(1))
        if name and name not in seen_names:
            seen_names.add(name)
            filenames.append(name[:500])

    actions = []
    seen_actions = set()
    for regex, attr_name in [(ONCLICK_RE, 'onclick'), (HREF_RE, 'href')]:
        for m in regex.finditer(raw_html or ''):
            value = html.unescape(m.group(1) or m.group(2) or '')
            if not FILE_CONTEXT_RE.search(value):
                continue
            key = (attr_name, value)
            if key in seen_actions:
                continue
            seen_actions.add(key)
            calls = []
            for cm in FUNC_CALL_RE.finditer(value):
                args = []
                for am in ARG_RE.finditer(cm.group(2)):
                    args.append(am.group(1) if am.group(1) is not None else am.group(2))
                calls.append({'function': cm.group(1), 'args': args[:20]})
            actions.append({'attribute': attr_name, 'value': value[:1500], 'calls': calls[:20]})

    # Capture short source snippets around filenames / file-related markers for structure clues.
    plain = html.unescape(raw_html or '')
    snippets = []
    markers = []
    for pattern in [r'첨부파일', r'file', r'atch', r'download', r'미리보기']:
        for m in re.finditer(pattern, plain, re.I):
            markers.append(m.start())
    for pos in sorted(set(markers))[:40]:
        s = max(0, pos - 220)
        e = min(len(plain), pos + 500)
        snippet = norm(plain[s:e])[:1200]
        if snippet and snippet not in snippets:
            snippets.append(snippet)
        if len(snippets) >= 12:
            break

    return {
        'filename_candidates': filenames[:100],
        'file_action_attributes': actions[:100],
        'context_snippets': snippets,
    }


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 ATTACHMENT IDENTITY CONTRACT FORENSIC - S109')
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
        if request_count >= MAX_REQUESTS:
            raise AssertionError('request budget exceeded')
        pst = str(row.get('pstSn'))
        url = DETAIL_BASE + pst
        request_count += 1
        try:
            resp = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        except Exception as exc:
            transport_errors.append({'pstSn': pst, 'error': repr(exc)[:500]})
            records.append({**compact(row), 'http_status': None, 'official_host': False, 'contract': {}, 'technical_state': 'TRANSPORT_ERROR'})
            continue

        official = (urlparse(str(resp.url)).hostname or '').lower() == HOST
        if not official:
            host_errors.append({'pstSn': pst, 'final_url': str(resp.url)[:1200]})
        contract = extract_contract(resp.text if resp.status_code == 200 and official else '')
        state = 'CONTRACT_EVIDENCE_CAPTURED' if resp.status_code == 200 and official else 'DETAIL_REQUEST_UNKNOWN'
        records.append({
            **compact(row),
            'detail_url': url,
            'final_url': str(resp.url)[:1200],
            'http_status': resp.status_code,
            'official_host': official,
            'contract': contract,
            'technical_state': state,
        })
        print('SAMPLE:', idx, '/', len(sample), 'GAZETTE:', row.get('gazette_number'), 'pstSn:', pst, 'HTTP:', resp.status_code, 'FILENAMES:', len(contract['filename_candidates']), 'ACTIONS:', len(contract['file_action_attributes']))

    ok = [r for r in records if r.get('technical_state') == 'CONTRACT_EVIDENCE_CAPTURED']
    filename_rows = [r for r in ok if (r.get('contract') or {}).get('filename_candidates')]
    action_rows = [r for r in ok if (r.get('contract') or {}).get('file_action_attributes')]

    function_counts = {}
    arg_shape_counts = {}
    for rec in ok:
        for action in (rec.get('contract') or {}).get('file_action_attributes') or []:
            for call in action.get('calls') or []:
                fn = call.get('function') or ''
                function_counts[fn] = function_counts.get(fn, 0) + 1
                shape = f"{fn}/{len(call.get('args') or [])}"
                arg_shape_counts[shape] = arg_shape_counts.get(shape, 0) + 1

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S109',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_lockfile': str(LOCK),
        'snapshot_identity_sha256': summary.get('identity_manifest_sha256'),
        'selected_partition': 'POST_HWP5_BOUNDARY',
        'sample_strategy': 'DETERMINISTIC_STRATIFIED_9_OF_219',
        'summary': {
            'post_partition_row_count': len(rows),
            'sample_row_count': len(sample),
            'request_count': request_count,
            'http_success_count': len(ok),
            'transport_error_count': len(transport_errors),
            'official_host_error_count': len(host_errors),
            'rows_with_filename_candidates': len(filename_rows),
            'rows_with_file_action_attributes': len(action_rows),
            'function_counts': dict(sorted(function_counts.items())),
            'function_arg_shape_counts': dict(sorted(arg_shape_counts.items())),
            'semantic_state': 'POST_HWP5_ATTACHMENT_IDENTITY_CONTRACT_FORENSIC_CAPTURED',
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
        raise AssertionError('S109 attachment identity contract forensic failed')


if __name__ == '__main__':
    main()
