# -*- coding: utf-8 -*-
"""S112: validate the POST-HWP5 attachment metadata endpoint contract.

S111 recovered the concrete metadata endpoint:
  GET /bbs010308/atchFileDetail?pstSn=<pstSn>
with response field `atchFileVO`, whose items expose at least:
  fileNo, fileSize, orginlFileNm

This stage calls that metadata endpoint for 9 deterministic rows from the committed POST-HWP5
snapshot partition. It validates JSON shape, item fields, file number uniqueness/cardinality,
and filename/extension distribution. Attachment bodies are NOT downloaded and UQQ700 target
terms are NOT searched.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
LOCK = BASE / 'law_data' / 'manifests' / 'seongnam_legacy_gazette_snapshot_20260903_fd62f245.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_metadata_endpoint_contract.json'

HOST = 'www.seongnam.go.kr'
ENDPOINT = 'https://www.seongnam.go.kr/bbs010308/atchFileDetail'
EXPECTED_SNAPSHOT_SHA = 'fd62f245514c00af504b55928294fe6b6c63e34ab8fdeebfe83a4c036f08977c'
EXPECTED_POST_ROWS = 219
MAX_REQUESTS = 9
TIMEOUT = 20
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
REQUIRED_ITEM_FIELDS = {'fileNo', 'fileSize', 'orginlFileNm'}


def pick_sample(rows):
    return [rows[i] for i in [0, 27, 54, 81, 109, 136, 163, 190, 218]]


def compact(row):
    return {k: row.get(k) for k in ['page', 'gazette_number', 'pstSn', 'date']}


def extension(name):
    name = str(name or '').strip()
    if '.' not in name:
        return 'NO_EXTENSION'
    ext = name.rsplit('.', 1)[-1].strip().lower()
    return ext or 'NO_EXTENSION'


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 ATTACHMENT METADATA ENDPOINT CONTRACT - S112')
    print('=' * 60)
    print('Metadata endpoint GET: ENABLED (9 deterministic rows)')
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
    session.headers.update({
        'User-Agent': UA,
        'Accept-Language': 'ko-KR,ko;q=0.9',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.seongnam.go.kr/bbs010308',
    })

    records = []
    request_count = 0
    transport_errors = []
    host_errors = []
    json_errors = []
    schema_errors = []
    extension_counts = Counter()
    attachment_cardinality = Counter()
    all_file_nos = []

    for idx, row in enumerate(sample, 1):
        if request_count >= MAX_REQUESTS:
            raise AssertionError('request budget exceeded')
        pst = str(row.get('pstSn'))
        request_count += 1
        try:
            resp = session.get(ENDPOINT, params={'pstSn': pst}, timeout=TIMEOUT, allow_redirects=True)
        except Exception as exc:
            transport_errors.append({'pstSn': pst, 'error': repr(exc)[:500]})
            records.append({**compact(row), 'http_status': None, 'official_host': False, 'items': [], 'technical_state': 'TRANSPORT_ERROR'})
            continue

        official = (urlparse(str(resp.url)).hostname or '').lower() == HOST
        if not official:
            host_errors.append({'pstSn': pst, 'final_url': str(resp.url)[:1200]})

        payload = None
        if resp.status_code == 200 and official:
            try:
                payload = resp.json()
            except Exception as exc:
                json_errors.append({'pstSn': pst, 'error': repr(exc)[:500], 'content_type': resp.headers.get('Content-Type'), 'body_prefix': resp.text[:500]})

        items = []
        top_keys = []
        if isinstance(payload, dict):
            top_keys = sorted(payload.keys())
            raw_items = payload.get('atchFileVO')
            if isinstance(raw_items, list):
                for raw in raw_items:
                    if not isinstance(raw, dict):
                        schema_errors.append({'pstSn': pst, 'error': 'non-dict atchFileVO item', 'item_repr': repr(raw)[:500]})
                        continue
                    missing = sorted(REQUIRED_ITEM_FIELDS - set(raw.keys()))
                    if missing:
                        schema_errors.append({'pstSn': pst, 'fileNo': raw.get('fileNo'), 'missing_fields': missing, 'keys': sorted(raw.keys())})
                    item = {
                        'fileNo': raw.get('fileNo'),
                        'fileSize': raw.get('fileSize'),
                        'orginlFileNm': raw.get('orginlFileNm'),
                        'extension': extension(raw.get('orginlFileNm')),
                        'response_item_keys': sorted(raw.keys()),
                    }
                    items.append(item)
                    extension_counts[item['extension']] += 1
                    if item['fileNo'] is not None:
                        all_file_nos.append(str(item['fileNo']))
            else:
                schema_errors.append({'pstSn': pst, 'error': 'atchFileVO missing or not list', 'top_keys': top_keys, 'atchFileVO_type': type(raw_items).__name__})
        elif payload is not None:
            schema_errors.append({'pstSn': pst, 'error': 'top-level JSON not dict', 'type': type(payload).__name__})

        attachment_cardinality[str(len(items))] += 1
        state = 'ATTACHMENT_METADATA_CAPTURED' if resp.status_code == 200 and official and isinstance(payload, dict) and isinstance(payload.get('atchFileVO'), list) else 'ATTACHMENT_METADATA_UNKNOWN'
        records.append({
            **compact(row),
            'request_url': str(resp.url)[:1200],
            'http_status': resp.status_code,
            'content_type': resp.headers.get('Content-Type'),
            'official_host': official,
            'top_level_keys': top_keys,
            'items': items,
            'technical_state': state,
        })
        print('SAMPLE:', idx, '/', len(sample), 'GAZETTE:', row.get('gazette_number'), 'pstSn:', pst, 'HTTP:', resp.status_code, 'ITEMS:', len(items), 'EXT:', [x['extension'] for x in items])

    captured = [r for r in records if r.get('technical_state') == 'ATTACHMENT_METADATA_CAPTURED']
    technical_unknown = [r for r in records if r.get('technical_state') != 'ATTACHMENT_METADATA_CAPTURED']
    unique_file_nos = sorted(set(all_file_nos))
    file_no_reuse_count = len(all_file_nos) - len(unique_file_nos)

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S112',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_lockfile': str(LOCK),
        'snapshot_identity_sha256': summary.get('identity_manifest_sha256'),
        'selected_partition': 'POST_HWP5_BOUNDARY',
        'sample_strategy': 'DETERMINISTIC_STRATIFIED_9_OF_219',
        'metadata_endpoint': ENDPOINT,
        'metadata_query_parameter': 'pstSn',
        'summary': {
            'post_partition_row_count': len(rows),
            'sample_row_count': len(sample),
            'request_count': request_count,
            'metadata_http_success_count': len(captured),
            'technical_unknown_count': len(technical_unknown),
            'transport_error_count': len(transport_errors),
            'official_host_error_count': len(host_errors),
            'json_error_count': len(json_errors),
            'schema_error_count': len(schema_errors),
            'attachment_cardinality_distribution': dict(sorted(attachment_cardinality.items(), key=lambda kv: int(kv[0]))),
            'sample_attachment_item_total': sum(len(r.get('items') or []) for r in records),
            'extension_counts': dict(sorted(extension_counts.items())),
            'file_no_occurrence_count': len(all_file_nos),
            'unique_file_no_count': len(unique_file_nos),
            'file_no_reuse_count': file_no_reuse_count,
            'required_item_fields': sorted(REQUIRED_ITEM_FIELDS),
            'semantic_state': 'POST_HWP5_ATTACHMENT_METADATA_ENDPOINT_CONTRACT_VALIDATED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'records': records,
        'transport_errors': transport_errors,
        'host_errors': host_errors,
        'json_errors': json_errors,
        'schema_errors': schema_errors,
        'attachment_metadata_semantics_confirmed': True,
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
        raise AssertionError('S112 attachment metadata endpoint contract test failed')


if __name__ == '__main__':
    main()
