# -*- coding: utf-8 -*-
"""S105: inventory the versioned Seongnam gazette snapshot lockfile.

Network-disabled. Reads only the committed immutable S103/S104 lockfile and summarizes
its chronology, page distribution, gazette-number range, and position relative to the
historical dynamic-HWP boundary. No target-term search, detail request, attachment request,
negative evidence, or SITE/runtime promotion is allowed.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOCK = BASE / 'law_data' / 'manifests' / 'seongnam_legacy_gazette_snapshot_20260903_fd62f245.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_snapshot_inventory.json'

EXPECTED_ROWS = 1611
EXPECTED_IDENTITY_SHA256 = 'fd62f245514c00af504b55928294fe6b6c63e34ab8fdeebfe83a4c036f08977c'
EXPECTED_PSTSN_SET_SHA256 = 'faab54a8beea14ea79f11abb4448a9e454c390e42d1b95e28c9cd46ab0fdf411'
HWP5_FIRST_GAZETTE = 526
HWP5_LAST_GAZETTE = 1872
HWP5_FIRST_PST = '28675'
HWP5_LAST_PST = '344241'
HWP5_FIRST_DATE = date(2004, 1, 15)
HWP5_LAST_DATE = date(2023, 7, 17)


def parse_date(v):
    try:
        return date.fromisoformat(str(v))
    except Exception:
        return None


def digest(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE LOCKED SNAPSHOT INVENTORY - S105')
    print('=' * 60)
    print('Network: DISABLED')
    print('Target-term search: DISABLED')
    print('Detail/attachment request: DISABLED')
    print('Negative evidence: DISABLED')

    if not LOCK.exists():
        raise FileNotFoundError(f'lockfile missing: {LOCK}')

    doc = json.loads(LOCK.read_text(encoding='utf-8'))
    summary = doc.get('summary') or {}
    rows = doc.get('canonical_rows') or []
    policy = doc.get('snapshot_policy') or {}

    identity_projection = [
        {
            'page': r.get('page'),
            'gazette_number': r.get('gazette_number'),
            'pstSn': str(r.get('pstSn') or ''),
            'date': r.get('date') or '',
        }
        for r in rows
    ]
    ids = [str(r.get('pstSn') or '') for r in rows]
    unique_ids = set(ids)

    year_counts = Counter()
    page_counts = Counter()
    valid_dates = []
    valid_gazettes = []
    pre = []
    inside = []
    post = []
    inside_anomaly = []

    for r in rows:
        d = parse_date(r.get('date'))
        g = int(r.get('gazette_number') or 0)
        p = int(r.get('page') or 0)
        if d:
            valid_dates.append(d)
            year_counts[str(d.year)] += 1
        if g:
            valid_gazettes.append(g)
        if p:
            page_counts[str(p)] += 1

        if g < HWP5_FIRST_GAZETTE:
            pre.append(r)
        elif g > HWP5_LAST_GAZETTE:
            post.append(r)
        else:
            inside.append(r)
            if d and not (HWP5_FIRST_DATE <= d <= HWP5_LAST_DATE):
                inside_anomaly.append(r)

    first_boundary = [r for r in rows if str(r.get('pstSn')) == HWP5_FIRST_PST]
    last_boundary = [r for r in rows if str(r.get('pstSn')) == HWP5_LAST_PST]

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S105',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_lockfile': str(LOCK),
        'snapshot_identity': {
            'captured_at_utc': policy.get('captured_at_utc'),
            'identity_manifest_sha256': summary.get('identity_manifest_sha256'),
            'pstsn_set_sha256': summary.get('pstsn_set_sha256'),
            'row_count': len(rows),
        },
        'historical_dynamic_hwp_boundary': {
            'first_gazette': HWP5_FIRST_GAZETTE,
            'first_pstSn': HWP5_FIRST_PST,
            'first_date': HWP5_FIRST_DATE.isoformat(),
            'last_gazette': HWP5_LAST_GAZETTE,
            'last_pstSn': HWP5_LAST_PST,
            'last_date': HWP5_LAST_DATE.isoformat(),
            'historical_identity_snapshot_recoverable': False,
        },
        'summary': {
            'manifest_row_count': len(rows),
            'manifest_unique_pstsn_count': len(unique_ids),
            'min_gazette_number': min(valid_gazettes) if valid_gazettes else None,
            'max_gazette_number': max(valid_gazettes) if valid_gazettes else None,
            'earliest_date': min(valid_dates).isoformat() if valid_dates else None,
            'latest_date': max(valid_dates).isoformat() if valid_dates else None,
            'pre_hwp5_boundary_count': len(pre),
            'inside_hwp5_gazette_boundary_count': len(inside),
            'post_hwp5_boundary_count': len(post),
            'inside_boundary_date_anomaly_count': len(inside_anomaly),
            'first_boundary_identity_count': len(first_boundary),
            'last_boundary_identity_count': len(last_boundary),
            'year_counts': dict(sorted(year_counts.items())),
            'page_row_counts': dict(sorted(page_counts.items(), key=lambda kv: int(kv[0]))),
            'semantic_state': 'LOCKED_CURRENT_ARCHIVE_SNAPSHOT_INVENTORIED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'pre_hwp5_boundary_rows': [
            {k: r.get(k) for k in ['page', 'gazette_number', 'pstSn', 'date']}
            for r in pre
        ],
        'post_hwp5_boundary_rows': [
            {k: r.get(k) for k in ['page', 'gazette_number', 'pstSn', 'date']}
            for r in post
        ],
        'inside_boundary_date_anomalies': [
            {k: r.get(k) for k in ['page', 'gazette_number', 'pstSn', 'date']}
            for r in inside_anomaly
        ],
        'network_request_count': 0,
        'target_term_search_executed': False,
        'detail_request_executed': False,
        'attachment_request_executed': False,
        'negative_evidence_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    validations = {
        'lock semantic state exact': summary.get('semantic_state') == 'CURRENT_ARCHIVE_IMMUTABLE_MANIFEST_CAPTURED',
        'row count exact': len(rows) == EXPECTED_ROWS,
        'unique pstSn exact': len(unique_ids) == EXPECTED_ROWS,
        'identity hash exact': summary.get('identity_manifest_sha256') == EXPECTED_IDENTITY_SHA256,
        'pstSn set hash exact': summary.get('pstsn_set_sha256') == EXPECTED_PSTSN_SET_SHA256,
        'recomputed identity hash exact': digest(identity_projection) == EXPECTED_IDENTITY_SHA256,
        'first boundary identity unique': len(first_boundary) == 1,
        'last boundary identity unique': len(last_boundary) == 1,
        'partition arithmetic exact': len(pre) + len(inside) + len(post) == EXPECTED_ROWS,
        'network disabled': out['network_request_count'] == 0,
        'target-term search disabled': not out['target_term_search_executed'],
        'detail request disabled': not out['detail_request_executed'],
        'attachment request disabled': not out['attachment_request_executed'],
        'negative evidence disabled': not out['negative_evidence_allowed'],
        'unsafe promotion leakage zero': not any(out[k] for k in ['site_positive_allowed', 'site_negative_allowed', 'runtime_registration_allowed']),
        'final resolution unknown': out['summary']['uqq700_final_resolution'] == 'UNKNOWN',
        'output written': OUT.exists() and OUT.stat().st_size > 0,
    }

    print('Manifest rows:', len(rows))
    print('Unique pstSn:', len(unique_ids))
    print('Gazette range:', (out['summary']['min_gazette_number'], out['summary']['max_gazette_number']))
    print('Date range:', (out['summary']['earliest_date'], out['summary']['latest_date']))
    print('Pre-HWP5 boundary:', len(pre))
    print('Inside HWP5 gazette boundary:', len(inside))
    print('Post-HWP5 boundary:', len(post))
    print('Inside-boundary date anomalies:', len(inside_anomaly))
    print('Boundary identities:', len(first_boundary), len(last_boundary))
    print('Year counts:', out['summary']['year_counts'])
    print('Output:', OUT)
    print('\nVALIDATION')
    for k, v in validations.items():
        print(f'{k}: {v}')
    print('all_pass:', all(validations.values()))
    if not all(validations.values()):
        raise AssertionError('S105 locked snapshot inventory failed')


if __name__ == '__main__':
    main()
