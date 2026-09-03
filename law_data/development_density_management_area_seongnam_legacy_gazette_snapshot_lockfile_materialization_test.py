# -*- coding: utf-8 -*-
"""S104: materialize the validated S103 current-archive snapshot as a versioned lockfile.

This stage is network-disabled. It reads the S103 output-only manifest, verifies the exact
snapshot identity observed on 2026-09-03, and copies it once into law_data/manifests/.
The destination is deliberately immutable: if a file already exists with different bytes,
execution fails rather than overwriting it.

Subsequent current-snapshot stages must consume this lockfile, not the mutable live archive.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SOURCE = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_current_archive_immutable_manifest.json'
MANIFEST_DIR = BASE / 'law_data' / 'manifests'
DEST = MANIFEST_DIR / 'seongnam_legacy_gazette_snapshot_20260903_fd62f245.json'

EXPECTED_ROW_COUNT = 1611
EXPECTED_IDENTITY_SHA256 = 'fd62f245514c00af504b55928294fe6b6c63e34ab8fdeebfe83a4c036f08977c'
EXPECTED_PSTSN_SET_SHA256 = 'faab54a8beea14ea79f11abb4448a9e454c390e42d1b95e28c9cd46ab0fdf411'
EXPECTED_CAPTURED_AT_UTC = '2026-09-03T00:25:06.727535+00:00'
EXPECTED_BOUNDARY_PAGE = 163


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE SNAPSHOT LOCKFILE MATERIALIZATION - S104')
    print('=' * 60)
    print('Network: DISABLED')
    print('Target-term search: DISABLED')
    print('Negative evidence: DISABLED')
    print('Overwrite: DISABLED')

    if not SOURCE.exists():
        raise FileNotFoundError(f'S103 manifest missing: {SOURCE}')

    source_bytes = SOURCE.read_bytes()
    doc = json.loads(source_bytes.decode('utf-8'))
    summary = doc.get('summary') or {}
    policy = doc.get('snapshot_policy') or {}

    validations = {
        'S103 semantic state exact': summary.get('semantic_state') == 'CURRENT_ARCHIVE_IMMUTABLE_MANIFEST_CAPTURED',
        'row count exact': int(summary.get('manifest_row_count') or 0) == EXPECTED_ROW_COUNT,
        'unique pstSn exact': int(summary.get('manifest_unique_pstsn_count') or 0) == EXPECTED_ROW_COUNT,
        'identity hash exact': summary.get('identity_manifest_sha256') == EXPECTED_IDENTITY_SHA256,
        'pstSn set hash exact': summary.get('pstsn_set_sha256') == EXPECTED_PSTSN_SET_SHA256,
        'capture timestamp exact': policy.get('captured_at_utc') == EXPECTED_CAPTURED_AT_UTC,
        'boundary guard exact': int(summary.get('boundary_guard_page') or 0) == EXPECTED_BOUNDARY_PAGE,
        'historical substitution disabled': policy.get('historical_1338_snapshot_substitution_allowed') is False,
        'live recrawl disabled as corpus input': policy.get('subsequent_stage_live_recrawl_as_corpus_input_allowed') is False,
        'target-term search disabled': doc.get('target_term_search_executed') is False,
        'detail request disabled': doc.get('detail_request_executed') is False,
        'negative evidence disabled': doc.get('negative_evidence_allowed') is False,
        'unsafe promotion leakage zero': not any(doc.get(k) for k in ['site_positive_allowed', 'site_negative_allowed', 'runtime_registration_allowed']),
        'final legal resolution unknown': summary.get('uqq700_final_resolution') == 'UNKNOWN',
    }

    if not all(validations.values()):
        for k, v in validations.items():
            print(f'{k}: {v}')
        raise AssertionError('S103 source snapshot does not match the approved S104 lock identity')

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    created = False
    if DEST.exists():
        existing = DEST.read_bytes()
        if existing != source_bytes:
            raise AssertionError(f'immutable lockfile collision: {DEST}')
    else:
        DEST.write_bytes(source_bytes)
        created = True

    locked_bytes = DEST.read_bytes()
    locked_doc = json.loads(locked_bytes.decode('utf-8'))
    locked_summary = locked_doc.get('summary') or {}

    post = {
        'destination exists': DEST.exists(),
        'destination bytes equal source': locked_bytes == source_bytes,
        'locked row count exact': int(locked_summary.get('manifest_row_count') or 0) == EXPECTED_ROW_COUNT,
        'locked identity hash exact': locked_summary.get('identity_manifest_sha256') == EXPECTED_IDENTITY_SHA256,
        'locked pstSn set hash exact': locked_summary.get('pstsn_set_sha256') == EXPECTED_PSTSN_SET_SHA256,
        'locked canonical row cardinality exact': len(locked_doc.get('canonical_rows') or []) == EXPECTED_ROW_COUNT,
    }

    print('Source:', SOURCE)
    print('Destination:', DEST)
    print('Created this run:', created)
    print('Locked file byte sha256:', sha256_bytes(locked_bytes))
    print('Manifest row count:', locked_summary.get('manifest_row_count'))
    print('Identity manifest sha256:', locked_summary.get('identity_manifest_sha256'))
    print('pstSn set sha256:', locked_summary.get('pstsn_set_sha256'))
    print('\nVALIDATION')
    for k, v in {**validations, **post}.items():
        print(f'{k}: {v}')
    all_pass = all(validations.values()) and all(post.values())
    print('all_pass:', all_pass)
    if not all_pass:
        raise AssertionError('S104 snapshot lockfile materialization failed')


if __name__ == '__main__':
    main()
