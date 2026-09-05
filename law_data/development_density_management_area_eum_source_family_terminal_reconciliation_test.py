# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'law_data' / 'output'
S176 = OUT_DIR / 'development_density_management_area_eum_gosi_seongnam_full_metadata_crawl.json'
S178 = OUT_DIR / 'development_density_management_area_eum_gosi_detail_html_bounded_scan.json'
S187 = OUT_DIR / 'development_density_management_area_eum_gosi_abnormal_response_signature_forensic.json'
OUT = OUT_DIR / 'development_density_management_area_eum_source_family_terminal_reconciliation.json'


def load(path: Path):
    if not path.exists():
        raise AssertionError(f'missing required input: {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    print('=' * 60)
    print('EUM SOURCE FAMILY TERMINAL RECONCILIATION - S188')
    print('=' * 60)
    print('Network: DISABLED')
    print('Attachment retry: DISABLED')
    print('Negative evidence: DISABLED')
    print('Legal absence inference: DISABLED')
    print('UQQ700 resolution: UNKNOWN')

    s176 = load(S176)
    s178 = load(S178)
    s187 = load(S187)

    m176 = s176.get('summary', {})
    m178 = s178.get('summary', {})
    m187 = s187.get('summary', {})

    row_count = int(m176.get('row_count') or 0)
    title_candidate_count = int(m176.get('candidate_count') or 0)
    detail_candidate_count = int(m178.get('candidate_count') or 0)
    detail_technical_unknown_count = int(m178.get('technical_unknown_count') or 0)

    records = s187.get('records', [])
    abnormal_records = [r for r in records if r.get('abnormal_marker')]
    alert_sets = [r.get('alerts', []) for r in abnormal_records]
    login_timeout_seen = any(any('로그인 시간 제한이 만료되었습니다.' in a for a in alerts) for alerts in alert_sets)
    abnormal_access_seen = any(any('정상적인 접근이 아닙니다.' in a for a in alerts) for alerts in alert_sets)

    attachment_surface_state = 'CURRENT_LIVE_ATTACHMENT_SURFACE_TECHNICALLY_BLOCKED_UNRESOLVED'
    source_family_state = 'EUM_QUALIFIED_METADATA_AND_DETAIL_HTML_SURFACES_RECONCILED_ATTACHMENT_SURFACE_TECHNICALLY_BLOCKED'

    out = {
        'step': 'STEP 17-21-C-16-8-T-84-S188',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'source_family': 'NATIONAL_LAND_USE_PORTAL_EUM',
        'network_executed': False,
        'attachment_retry_executed': False,
        'preserved_snapshot': {
            'metadata_row_count': row_count,
            'title_candidate_count': title_candidate_count,
            'detail_html_candidate_count': detail_candidate_count,
            'detail_html_technical_unknown_count': detail_technical_unknown_count,
            'metadata_surface_state': m176.get('semantic_state'),
            'detail_html_surface_state': m178.get('semantic_state'),
        },
        'current_live_surface': {
            'record_count': len(records),
            'abnormal_record_count': len(abnormal_records),
            'login_timeout_alert_seen': login_timeout_seen,
            'abnormal_access_alert_seen': abnormal_access_seen,
            'attachment_surface_state': attachment_surface_state,
            's187_semantic_state': m187.get('semantic_state'),
        },
        'terminal_reconciliation': {
            'searchable_title_surface_closed': row_count > 0 and title_candidate_count == 0,
            'searchable_detail_html_surface_closed': row_count > 0 and detail_candidate_count == 0 and detail_technical_unknown_count == 0,
            'attachment_surface_closed_as_technical_unknown': login_timeout_seen and abnormal_access_seen,
            'source_family_semantic_state': source_family_state,
            'negative_evidence_allowed': False,
            'legal_absence_inference_allowed': False,
            'site_positive_allowed': False,
            'site_negative_allowed': False,
            'runtime_registration_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
            'next_source_family': 'OTHER_HISTORICAL_OFFICIAL_SOURCE_FAMILY_OR_NOTICE_IDENTITY_REVERSE_DISCOVERY',
        },
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    print('PRESERVED SNAPSHOT')
    print('metadata_row_count:', row_count)
    print('title_candidate_count:', title_candidate_count)
    print('detail_html_candidate_count:', detail_candidate_count)
    print('detail_html_technical_unknown_count:', detail_technical_unknown_count)
    print('metadata_surface_state:', m176.get('semantic_state'))
    print('detail_html_surface_state:', m178.get('semantic_state'))

    print('\nCURRENT LIVE SURFACE')
    print('record_count:', len(records))
    print('abnormal_record_count:', len(abnormal_records))
    print('login_timeout_alert_seen:', login_timeout_seen)
    print('abnormal_access_alert_seen:', abnormal_access_seen)
    print('attachment_surface_state:', attachment_surface_state)

    print('\nTERMINAL RECONCILIATION')
    for k, v in out['terminal_reconciliation'].items():
        print(f'{k}: {v}')
    print('Output:', OUT)

    t = out['terminal_reconciliation']
    checks = {
        'network disabled': not out['network_executed'],
        'attachment retry disabled': not out['attachment_retry_executed'],
        'historical metadata snapshot preserved': row_count == 3409,
        'title surface no candidate': title_candidate_count == 0,
        'detail html surface no candidate': detail_candidate_count == 0,
        'detail html technical unknown zero': detail_technical_unknown_count == 0,
        'abnormal live response captured': len(abnormal_records) == 3,
        'login timeout alert captured': login_timeout_seen,
        'abnormal access alert captured': abnormal_access_seen,
        'title surface closed': t['searchable_title_surface_closed'],
        'detail html surface closed': t['searchable_detail_html_surface_closed'],
        'attachment surface technical unknown': t['attachment_surface_closed_as_technical_unknown'],
        'negative evidence disabled': not t['negative_evidence_allowed'],
        'legal absence inference disabled': not t['legal_absence_inference_allowed'],
        'unsafe promotion leakage zero': not any(t[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),
        'final resolution unknown': t['uqq700_final_resolution'] == 'UNKNOWN',
        'output written': OUT.exists() and OUT.stat().st_size > 0,
    }

    print('\nVALIDATION')
    for k, v in checks.items():
        print(f'{k}: {v}')
    print('all_pass:', all(checks.values()))
    if not all(checks.values()):
        raise AssertionError('S188 EUM source family terminal reconciliation failed')


if __name__ == '__main__':
    main()
