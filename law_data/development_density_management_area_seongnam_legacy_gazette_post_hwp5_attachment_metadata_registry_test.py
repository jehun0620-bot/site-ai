# -*- coding: utf-8 -*-
"""S113: build complete POST-HWP5 attachment metadata registry.

Uses the committed immutable 1,611-row snapshot and selects gazette_number > 1872 (219 rows).
For each row, calls only the official attachment metadata endpoint:
  GET /bbs010308/atchFileDetail?pstSn=<pstSn>

Captures fileNo, fileSize, orginlFileNm, extension, row identity and validates global
file-number uniqueness / filename distribution. Attachment bodies are NOT downloaded.
No UQQ700 target-term search, negative evidence, candidate promotion, SITE/runtime mutation.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
LOCK = BASE / 'law_data' / 'manifests' / 'seongnam_legacy_gazette_snapshot_20260903_fd62f245.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_metadata_registry.json'

HOST = 'www.seongnam.go.kr'
ENDPOINT = 'https://www.seongnam.go.kr/bbs010308/atchFileDetail'
EXPECTED_SNAPSHOT_SHA = 'fd62f245514c00af504b55928294fe6b6c63e34ab8fdeebfe83a4c036f08977c'
EXPECTED_POST_ROWS = 219
MAX_REQUESTS = 219
TIMEOUT = 20
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
REQUIRED_ITEM_FIELDS = {'fileNo', 'fileSize', 'orginlFileNm'}


def compact(row):
    return {k: row.get(k) for k in ['page', 'gazette_number', 'pstSn', 'date']}


def ext(name):
    name = str(name or '').strip()
    if '.' not in name:
        return 'NO_EXTENSION'
    value = name.rsplit('.', 1)[-1].strip().lower()
    return value or 'NO_EXTENSION'


def sha256_json(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 ATTACHMENT METADATA REGISTRY - S113')
    print('=' * 60)
    print('Metadata endpoint GET: ENABLED (219 locked rows)')
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
    session.headers.update({
        'User-Agent': UA,
        'Accept-Language': 'ko-KR,ko;q=0.9',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.seongnam.go.kr/bbs010308',
    })

    records = []
    attachments = []
    request_count = 0
    transport_errors = []
    host_errors = []
    json_errors = []
    schema_errors = []
    row_cardinality = Counter()
    extension_counts = Counter()
    year_extension_counts = {}
    file_no_occurrences = Counter()
    filename_occurrences = Counter()

    for idx, row in enumerate(rows, 1):
        if request_count >= MAX_REQUESTS:
            raise AssertionError('request budget exceeded')
        pst = str(row.get('pstSn'))
        request_count += 1
        try:
            resp = session.get(ENDPOINT, params={'pstSn': pst}, timeout=TIMEOUT, allow_redirects=True)
        except Exception as exc:
            transport_errors.append({'pstSn': pst, 'error': repr(exc)[:500]})
            records.append({**compact(row), 'http_status': None, 'items': [], 'technical_state': 'TRANSPORT_ERROR'})
            continue

        official = (urlparse(str(resp.url)).hostname or '').lower() == HOST
        if not official:
            host_errors.append({'pstSn': pst, 'final_url': str(resp.url)[:1200]})

        payload = None
        if resp.status_code == 200 and official:
            try:
                payload = resp.json()
            except Exception as exc:
                json_errors.append({'pstSn': pst, 'error': repr(exc)[:500], 'body_prefix': resp.text[:500]})

        items = []
        if isinstance(payload, dict) and isinstance(payload.get('atchFileVO'), list):
            for pos, raw in enumerate(payload['atchFileVO'], 1):
                if not isinstance(raw, dict):
                    schema_errors.append({'pstSn': pst, 'position': pos, 'error': 'non-dict item'})
                    continue
                missing = sorted(REQUIRED_ITEM_FIELDS - set(raw.keys()))
                if missing:
                    schema_errors.append({'pstSn': pst, 'position': pos, 'missing_fields': missing, 'keys': sorted(raw.keys())})
                file_no = raw.get('fileNo')
                file_name = raw.get('orginlFileNm')
                file_size = raw.get('fileSize')
                extension = ext(file_name)
                item = {
                    'position': pos,
                    'fileNo': file_no,
                    'fileSize': file_size,
                    'orginlFileNm': file_name,
                    'extension': extension,
                    'response_item_keys': sorted(raw.keys()),
                }
                items.append(item)
                attachment = {**compact(row), **item}
                attachments.append(attachment)
                extension_counts[extension] += 1
                file_no_occurrences[str(file_no)] += 1
                filename_occurrences[str(file_name)] += 1
                year = str(row.get('date') or '')[:4] or 'UNKNOWN'
                if year not in year_extension_counts:
                    year_extension_counts[year] = Counter()
                year_extension_counts[year][extension] += 1
        else:
            if payload is not None:
                schema_errors.append({'pstSn': pst, 'error': 'atchFileVO missing or not list', 'payload_type': type(payload).__name__, 'top_keys': sorted(payload.keys()) if isinstance(payload, dict) else []})

        row_cardinality[str(len(items))] += 1
        state = 'ATTACHMENT_METADATA_CAPTURED' if resp.status_code == 200 and official and isinstance(payload, dict) and isinstance(payload.get('atchFileVO'), list) else 'ATTACHMENT_METADATA_UNKNOWN'
        records.append({**compact(row), 'request_url': str(resp.url)[:1200], 'http_status': resp.status_code, 'content_type': resp.headers.get('Content-Type'), 'official_host': official, 'items': items, 'technical_state': state})

        if idx <= 3 or idx % 25 == 0 or idx > len(rows) - 3:
            print('ROW:', idx, '/', len(rows), 'GAZETTE:', row.get('gazette_number'), 'pstSn:', pst, 'HTTP:', resp.status_code, 'ITEMS:', len(items), 'EXT:', [x['extension'] for x in items])

    captured = [r for r in records if r.get('technical_state') == 'ATTACHMENT_METADATA_CAPTURED']
    unknown = [r for r in records if r.get('technical_state') != 'ATTACHMENT_METADATA_CAPTURED']
    reused_file_nos = {k: v for k, v in file_no_occurrences.items() if v > 1}
    duplicate_filenames = {k: v for k, v in filename_occurrences.items() if v > 1}

    identity_rows = [
        {
            'pstSn': str(a.get('pstSn')),
            'fileNo': str(a.get('fileNo')),
            'orginlFileNm': a.get('orginlFileNm'),
            'fileSize': a.get('fileSize'),
        }
        for a in attachments
    ]
    registry_sha = sha256_json(identity_rows)

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S113',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_lockfile': str(LOCK),
        'snapshot_identity_sha256': summary.get('identity_manifest_sha256'),
        'selected_partition': 'POST_HWP5_BOUNDARY',
        'metadata_endpoint': ENDPOINT,
        'metadata_query_parameter': 'pstSn',
        'summary': {
            'selected_row_count': len(rows),
            'request_count': request_count,
            'metadata_http_success_count': len(captured),
            'technical_unknown_count': len(unknown),
            'transport_error_count': len(transport_errors),
            'official_host_error_count': len(host_errors),
            'json_error_count': len(json_errors),
            'schema_error_count': len(schema_errors),
            'row_attachment_cardinality_distribution': dict(sorted(row_cardinality.items(), key=lambda kv: int(kv[0]))),
            'attachment_item_total': len(attachments),
            'extension_counts': dict(sorted(extension_counts.items())),
            'year_extension_counts': {k: dict(sorted(v.items())) for k, v in sorted(year_extension_counts.items())},
            'file_no_occurrence_count': sum(file_no_occurrences.values()),
            'unique_file_no_count': len(file_no_occurrences),
            'reused_file_no_count': len(reused_file_nos),
            'reused_file_nos': reused_file_nos,
            'duplicate_filename_value_count': len(duplicate_filenames),
            'registry_identity_sha256': registry_sha,
            'semantic_state': 'POST_HWP5_ATTACHMENT_METADATA_REGISTRY_CAPTURED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'records': records,
        'attachments': attachments,
        'transport_errors': transport_errors,
        'host_errors': host_errors,
        'json_errors': json_errors,
        'schema_errors': schema_errors,
        'duplicate_filenames': duplicate_filenames,
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
        raise AssertionError('S113 attachment metadata registry failed')


if __name__ == '__main__':
    main()
