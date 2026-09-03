# -*- coding: utf-8 -*-
"""S106: partition the locked Seongnam gazette snapshot into processing phases.

Network-disabled. Consumes only the committed S103/S104 lockfile and partitions rows into:
- PRE_HWP5_BOUNDARY: gazette < 526
- INSIDE_HWP5_GAZETTE_BOUNDARY: 526..1872 inclusive
- POST_HWP5_BOUNDARY: gazette > 1872

This is a technical routing step only. The historical 1,338-row identity snapshot is not
reconstructed, so INSIDE_HWP5_GAZETTE_BOUNDARY must not be treated as equivalent to the old
closed dynamic-HWP corpus. No UQQ700 target search, detail request, attachment request,
negative evidence, or SITE/runtime promotion is allowed.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOCK = BASE / 'law_data' / 'manifests' / 'seongnam_legacy_gazette_snapshot_20260903_fd62f245.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_snapshot_processing_partition.json'

EXPECTED_ROWS = 1611
EXPECTED_IDENTITY_SHA256 = 'fd62f245514c00af504b55928294fe6b6c63e34ab8fdeebfe83a4c036f08977c'
FIRST_GAZETTE = 526
LAST_GAZETTE = 1872


def compact(row):
    return {k: row.get(k) for k in ['page', 'gazette_number', 'pstSn', 'date']}


def stats(rows):
    years = Counter()
    pages = []
    gazettes = []
    for r in rows:
        d = str(r.get('date') or '')
        if len(d) >= 4 and d[:4].isdigit():
            years[d[:4]] += 1
        p = int(r.get('page') or 0)
        g = int(r.get('gazette_number') or 0)
        if p:
            pages.append(p)
        if g:
            gazettes.append(g)
    return {
        'count': len(rows),
        'page_min': min(pages) if pages else None,
        'page_max': max(pages) if pages else None,
        'gazette_min': min(gazettes) if gazettes else None,
        'gazette_max': max(gazettes) if gazettes else None,
        'year_counts': dict(sorted(years.items())),
    }


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE LOCKED SNAPSHOT PROCESSING PARTITION - S106')
    print('=' * 60)
    print('Network: DISABLED')
    print('Target-term search: DISABLED')
    print('Detail/attachment request: DISABLED')
    print('Negative evidence: DISABLED')

    if not LOCK.exists():
        raise FileNotFoundError(LOCK)
    doc = json.loads(LOCK.read_text(encoding='utf-8'))
    summary = doc.get('summary') or {}
    rows = doc.get('canonical_rows') or []

    pre = []
    inside = []
    post = []
    invalid = []

    for r in rows:
        try:
            g = int(r.get('gazette_number'))
        except Exception:
            invalid.append(r)
            continue
        if g < FIRST_GAZETTE:
            pre.append(r)
        elif g > LAST_GAZETTE:
            post.append(r)
        else:
            inside.append(r)

    phases = {
        'PRE_HWP5_BOUNDARY': {
            **stats(pre),
            'processing_policy': 'SEPARATE_LEGACY_FORMAT_INVENTORY_REQUIRED',
            'old_dynamic_hwp_pipeline_reuse_allowed': False,
            'target_search_allowed_now': False,
            'rows': [compact(r) for r in pre],
        },
        'INSIDE_HWP5_GAZETTE_BOUNDARY': {
            **stats(inside),
            'processing_policy': 'HISTORICAL_IDENTITY_RECONCILIATION_REQUIRED_BEFORE_ANY_REPROCESSING',
            'equivalent_to_historical_1338_corpus': False,
            'old_dynamic_hwp_pipeline_rerun_allowed': False,
            'target_search_allowed_now': False,
            'rows': [compact(r) for r in inside],
        },
        'POST_HWP5_BOUNDARY': {
            **stats(post),
            'processing_policy': 'SEPARATE_MODERN_FORMAT_INVENTORY_REQUIRED',
            'old_dynamic_hwp_pipeline_reuse_allowed': False,
            'target_search_allowed_now': False,
            'rows': [compact(r) for r in post],
        },
    }

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S106',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_lockfile': str(LOCK),
        'snapshot_identity_sha256': summary.get('identity_manifest_sha256'),
        'manifest_row_count': len(rows),
        'partition': phases,
        'invalid_gazette_number_rows': [compact(r) for r in invalid],
        'routing': {
            'next_priority_phase': 'POST_HWP5_BOUNDARY_FORMAT_INVENTORY',
            'secondary_phase': 'PRE_HWP5_BOUNDARY_FORMAT_INVENTORY',
            'inside_boundary_phase': 'DEFER_UNTIL_HISTORICAL_IDENTITY_RECONCILIATION_OR_EXPLICIT_NEW_SNAPSHOT_REPROCESSING_POLICY',
            'reason': 'Post-boundary rows are outside the closed historical HWP5 era and likely require modern attachment-format handling; pre-boundary rows require legacy-format handling. Inside-boundary rows cannot be equated with the unrecoverable historical 1,338-row identity corpus.',
        },
        'network_request_count': 0,
        'target_term_search_executed': False,
        'detail_request_executed': False,
        'attachment_request_executed': False,
        'negative_evidence_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
        'uqq700_final_resolution': 'UNKNOWN',
        'semantic_state': 'LOCKED_SNAPSHOT_PROCESSING_PHASES_PARTITIONED',
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    vals = {
        'snapshot identity exact': summary.get('identity_manifest_sha256') == EXPECTED_IDENTITY_SHA256,
        'row count exact': len(rows) == EXPECTED_ROWS,
        'invalid rows zero': len(invalid) == 0,
        'partition arithmetic exact': len(pre) + len(inside) + len(post) == EXPECTED_ROWS,
        'pre partition nonempty': len(pre) > 0,
        'inside partition nonempty': len(inside) > 0,
        'post partition nonempty': len(post) > 0,
        'inside not equated to historical corpus': not phases['INSIDE_HWP5_GAZETTE_BOUNDARY']['equivalent_to_historical_1338_corpus'],
        'old dynamic HWP rerun disabled': not phases['INSIDE_HWP5_GAZETTE_BOUNDARY']['old_dynamic_hwp_pipeline_rerun_allowed'],
        'network disabled': out['network_request_count'] == 0,
        'target-term search disabled': not out['target_term_search_executed'],
        'detail request disabled': not out['detail_request_executed'],
        'attachment request disabled': not out['attachment_request_executed'],
        'negative evidence disabled': not out['negative_evidence_allowed'],
        'unsafe promotion leakage zero': not any(out[k] for k in ['site_positive_allowed', 'site_negative_allowed', 'runtime_registration_allowed']),
        'final resolution unknown': out['uqq700_final_resolution'] == 'UNKNOWN',
        'output written': OUT.exists() and OUT.stat().st_size > 0,
    }

    print('PRE_HWP5_BOUNDARY:', phases['PRE_HWP5_BOUNDARY']['count'], phases['PRE_HWP5_BOUNDARY']['year_counts'])
    print('INSIDE_HWP5_GAZETTE_BOUNDARY:', phases['INSIDE_HWP5_GAZETTE_BOUNDARY']['count'])
    print('POST_HWP5_BOUNDARY:', phases['POST_HWP5_BOUNDARY']['count'], phases['POST_HWP5_BOUNDARY']['year_counts'])
    print('Next priority phase:', out['routing']['next_priority_phase'])
    print('Secondary phase:', out['routing']['secondary_phase'])
    print('Inside-boundary phase:', out['routing']['inside_boundary_phase'])
    print('Output:', OUT)
    print('\nVALIDATION')
    for k, v in vals.items():
        print(f'{k}: {v}')
    print('all_pass:', all(vals.values()))
    if not all(vals.values()):
        raise AssertionError('S106 locked snapshot processing partition failed')


if __name__ == '__main__':
    main()
