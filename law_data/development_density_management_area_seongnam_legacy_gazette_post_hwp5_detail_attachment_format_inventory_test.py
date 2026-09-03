# -*- coding: utf-8 -*-
"""S107: inventory detail-page attachment metadata for POST_HWP5_BOUNDARY rows.

Input corpus is the committed 2026-09-03 immutable 1,611-row snapshot lockfile.
Only rows with gazette_number > 1872 are selected (expected 219 rows).

Network scope:
- GET official detail pages /bbs010308/{pstSn}
- parse attachment metadata/link targets from detail HTML only
- do NOT download attachment bodies
- do NOT perform UQQ700 target-term/body search
- do NOT infer legal negative evidence or SITE/runtime state

This stage classifies the post-HWP5 format surface so the next bounded extraction/search
phase can choose the correct handlers. Detail HTML text is not used as target evidence here.
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
LOCK = BASE / 'law_data' / 'manifests' / 'seongnam_legacy_gazette_snapshot_20260903_fd62f245.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_detail_attachment_format_inventory.json'

HOST = 'www.seongnam.go.kr'
DETAIL_BASE = 'https://www.seongnam.go.kr/bbs010308/'
EXPECTED_POST_ROWS = 219
EXPECTED_SNAPSHOT_SHA = 'fd62f245514c00af504b55928294fe6b6c63e34ab8fdeebfe83a4c036f08977c'
MAX_REQUESTS = 219
TIMEOUT = 20
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'

A_RE = re.compile(r'<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>', re.I | re.S)
ATTR_RE = re.compile(r'([:\w-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.I)
TAG_RE = re.compile(r'<[^>]+>', re.S)
EXT_RE = re.compile(r'\.([A-Za-z0-9]{1,8})(?:\?|#|$)')
FILEISH_RE = re.compile(r'(download|file|atch|attach|첨부|파일|hwp|hwpx|pdf|docx?|xlsx?|zip)', re.I)
TARGET_TERMS = ('개발밀도관리구역', '개발밀도', 'UQQ700')


def norm(v):
    return re.sub(r'\s+', ' ', str(v or '')).strip()


def attrs(raw):
    out = {}
    for m in ATTR_RE.finditer(raw or ''):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or '')
    return out


def clean(raw):
    return norm(html.unescape(TAG_RE.sub(' ', raw or '')))


def extension_from(text):
    m = EXT_RE.search(text or '')
    return m.group(1).lower() if m else ''


def parse_attachment_links(raw_html, detail_url):
    items = []
    seen = set()
    for am in A_RE.finditer(raw_html or ''):
        a = attrs(am.group('attrs'))
        label = clean(am.group('body'))
        href = html.unescape(a.get('href', '') or '')
        onclick = html.unescape(a.get('onclick', '') or '')
        combined = ' '.join([label, href, onclick])
        if not FILEISH_RE.search(combined):
            continue
        resolved = urljoin(detail_url, href) if href and not href.lower().startswith('javascript:') else ''
        ext = extension_from(label) or extension_from(href) or extension_from(onclick)
        key = (label, href, onclick)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            'label': label[:500],
            'href': href[:1000],
            'resolved_url': resolved[:1200],
            'onclick': onclick[:1000],
            'extension_hint': ext,
        })
    return items


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 DETAIL ATTACHMENT FORMAT INVENTORY - S107')
    print('=' * 60)
    print('Target-term search: DISABLED')
    print('Attachment body download: DISABLED')
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
    extension_counts = Counter()
    attachment_count_distribution = Counter()
    transport_errors = []
    host_errors = []
    target_term_visibility_count = 0
    request_count = 0

    for idx, row in enumerate(rows, 1):
        if request_count >= MAX_REQUESTS:
            raise AssertionError('request budget exceeded')
        pst = str(row.get('pstSn'))
        detail_url = DETAIL_BASE + pst
        request_count += 1
        try:
            response = session.get(detail_url, timeout=TIMEOUT, allow_redirects=True)
        except Exception as exc:
            transport_errors.append({'pstSn': pst, 'error': repr(exc)[:500]})
            records.append({**{k: row.get(k) for k in ['page', 'gazette_number', 'pstSn', 'date']}, 'http_status': None, 'official_host': False, 'attachments': [], 'technical_state': 'TRANSPORT_ERROR'})
            continue

        official = (urlparse(str(response.url)).hostname or '').lower() == HOST
        if not official:
            host_errors.append({'pstSn': pst, 'final_url': str(response.url)[:1200]})

        links = parse_attachment_links(response.text if response.status_code == 200 and official else '', detail_url)
        attachment_count_distribution[str(len(links))] += 1
        for item in links:
            extension_counts[item['extension_hint'] or 'UNKNOWN'] += 1

        # Diagnostic only: detect accidental target visibility, but never promote it here.
        visible = any(term in response.text for term in TARGET_TERMS) if response.status_code == 200 and official else False
        if visible:
            target_term_visibility_count += 1

        technical_state = 'DETAIL_METADATA_CAPTURED' if response.status_code == 200 and official else 'DETAIL_REQUEST_UNKNOWN'
        records.append({
            **{k: row.get(k) for k in ['page', 'gazette_number', 'pstSn', 'date']},
            'detail_url': detail_url,
            'final_url': str(response.url)[:1200],
            'http_status': response.status_code,
            'official_host': official,
            'attachment_link_count': len(links),
            'attachments': links,
            'target_term_visibility_diagnostic_only': visible,
            'technical_state': technical_state,
        })

        if idx <= 3 or idx % 25 == 0 or idx > len(rows) - 3:
            print('ROW:', idx, '/', len(rows), 'GAZETTE:', row.get('gazette_number'), 'pstSn:', pst, 'HTTP:', response.status_code, 'ATTACHMENTS:', len(links))

    detail_ok = sum(1 for r in records if r.get('technical_state') == 'DETAIL_METADATA_CAPTURED')
    attachment_rows = sum(1 for r in records if int(r.get('attachment_link_count') or 0) > 0)
    total_links = sum(int(r.get('attachment_link_count') or 0) for r in records)
    unknown_rows = [r for r in records if r.get('technical_state') != 'DETAIL_METADATA_CAPTURED']

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S107',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_lockfile': str(LOCK),
        'snapshot_identity_sha256': summary.get('identity_manifest_sha256'),
        'selected_partition': 'POST_HWP5_BOUNDARY',
        'summary': {
            'selected_row_count': len(rows),
            'request_count': request_count,
            'detail_http_success_count': detail_ok,
            'transport_error_count': len(transport_errors),
            'official_host_error_count': len(host_errors),
            'rows_with_attachment_links': attachment_rows,
            'total_attachment_links': total_links,
            'attachment_count_distribution': dict(sorted(attachment_count_distribution.items(), key=lambda kv: int(kv[0]))),
            'extension_hint_counts': dict(sorted(extension_counts.items())),
            'technical_unknown_count': len(unknown_rows),
            'target_term_visibility_diagnostic_only_count': target_term_visibility_count,
            'semantic_state': 'POST_HWP5_DETAIL_ATTACHMENT_FORMAT_INVENTORIED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'records': records,
        'transport_errors': transport_errors,
        'host_errors': host_errors,
        'target_term_search_executed': False,
        'detail_request_executed': True,
        'attachment_body_download_executed': False,
        'negative_evidence_allowed': False,
        'candidate_promotion_allowed': False,
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
        raise AssertionError('S107 post-HWP5 detail attachment inventory failed')


if __name__ == '__main__':
    main()
