# -*- coding: utf-8 -*-
"""S108: forensic classification of the three file-like links on POST-HWP5 detail pages.

Consumes the S107 local output only. Network-disabled. The purpose is to distinguish actual
attachment identities from UI/download/helper links before any attachment-body request is
allowed. This stage does not search target terms, download files, create candidates, infer
negative evidence, or promote SITE/runtime state.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_detail_attachment_format_inventory.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_link_role_forensic.json'

EXPECTED_ROWS = 219
EXPECTED_LINKS = 657
EXPECTED_SNAPSHOT_SHA = 'fd62f245514c00af504b55928294fe6b6c63e34ab8fdeebfe83a4c036f08977c'

EXT_RE = re.compile(r'\.([A-Za-z0-9]{1,8})(?:\?|#|$)', re.I)
DOWNLOADISH = re.compile(r'(download|filedown|atch|attach|첨부|다운로드)', re.I)
VIEWISH = re.compile(r'(view|preview|미리보기)', re.I)
JS_RE = re.compile(r'^javascript:', re.I)


def norm(v):
    return re.sub(r'\s+', ' ', str(v or '')).strip()


def ext_from(*values):
    for value in values:
        m = EXT_RE.search(str(value or ''))
        if m:
            return m.group(1).lower()
    return ''


def role(item):
    label = norm(item.get('label'))
    href = norm(item.get('href'))
    resolved = norm(item.get('resolved_url'))
    onclick = norm(item.get('onclick'))
    combined = ' '.join([label, href, resolved, onclick])
    ext = ext_from(label, href, resolved, onclick)

    if ext in {'hwp', 'hwpx', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'zip'}:
        return 'ATTACHMENT_FILENAME_OR_DIRECT_LINK'
    if JS_RE.search(href) or onclick:
        if DOWNLOADISH.search(combined):
            return 'DOWNLOAD_ACTION_LINK'
        if VIEWISH.search(combined):
            return 'VIEW_ACTION_LINK'
        return 'JAVASCRIPT_ACTION_LINK'
    if resolved:
        parsed = urlparse(resolved)
        path = parsed.path.lower()
        query = parse_qs(parsed.query)
        if DOWNLOADISH.search(path) or DOWNLOADISH.search(parsed.query):
            return 'DOWNLOAD_ENDPOINT_LINK'
        if path.endswith('.html') or path.endswith('.htm') or ext == 'html':
            return 'HTML_HELPER_LINK'
        if query:
            return 'QUERY_ENDPOINT_LINK'
        return 'RESOLVED_LINK_OTHER'
    return 'UNRESOLVED_FILELIKE_LINK'


def signature(item):
    href = norm(item.get('href'))
    onclick = norm(item.get('onclick'))
    resolved = norm(item.get('resolved_url'))
    parsed = urlparse(resolved) if resolved else None
    return {
        'label': norm(item.get('label'))[:300],
        'href': href[:500],
        'onclick': onclick[:500],
        'resolved_path': parsed.path[:500] if parsed else '',
        'resolved_query_keys': sorted(parse_qs(parsed.query).keys()) if parsed else [],
        'extension_hint': norm(item.get('extension_hint')),
        'derived_extension': ext_from(item.get('label'), href, onclick, resolved),
    }


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 ATTACHMENT LINK ROLE FORENSIC - S108')
    print('=' * 60)
    print('Network: DISABLED')
    print('Attachment body download: DISABLED')
    print('Target-term search: DISABLED')
    print('Negative evidence: DISABLED')

    if not SRC.exists():
        raise FileNotFoundError(f'S107 output missing: {SRC}')
    doc = json.loads(SRC.read_text(encoding='utf-8'))
    records = doc.get('records') or []

    role_counts = Counter()
    per_position_role = defaultdict(Counter)
    position_signatures = defaultdict(Counter)
    row_role_patterns = Counter()
    examples = defaultdict(list)
    all_links = 0

    for rec in records:
        roles = []
        for pos, item in enumerate(rec.get('attachments') or [], 1):
            all_links += 1
            r = role(item)
            roles.append(r)
            role_counts[r] += 1
            per_position_role[str(pos)][r] += 1
            sig = signature(item)
            sig_key = json.dumps(sig, ensure_ascii=False, sort_keys=True)
            position_signatures[str(pos)][sig_key] += 1
            if len(examples[r]) < 5:
                examples[r].append({
                    'gazette_number': rec.get('gazette_number'),
                    'pstSn': rec.get('pstSn'),
                    'position': pos,
                    **sig,
                })
        row_role_patterns[' | '.join(roles)] += 1

    compact_position_signatures = {}
    for pos, counts in position_signatures.items():
        compact_position_signatures[pos] = [
            {'count': count, 'signature': json.loads(sig)}
            for sig, count in counts.most_common(20)
        ]

    actual_identity_roles = {'ATTACHMENT_FILENAME_OR_DIRECT_LINK'}
    action_roles = {'DOWNLOAD_ACTION_LINK', 'VIEW_ACTION_LINK', 'JAVASCRIPT_ACTION_LINK', 'DOWNLOAD_ENDPOINT_LINK', 'HTML_HELPER_LINK', 'QUERY_ENDPOINT_LINK', 'RESOLVED_LINK_OTHER', 'UNRESOLVED_FILELIKE_LINK'}
    actual_identity_count = sum(role_counts[r] for r in actual_identity_roles)
    action_or_helper_count = sum(role_counts[r] for r in action_roles)

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S108',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_s107_output': str(SRC),
        'snapshot_identity_sha256': doc.get('snapshot_identity_sha256'),
        'summary': {
            'record_count': len(records),
            'total_filelike_link_count': all_links,
            'role_counts': dict(sorted(role_counts.items())),
            'per_position_role_counts': {k: dict(v) for k, v in sorted(per_position_role.items(), key=lambda kv: int(kv[0]))},
            'row_role_patterns': dict(row_role_patterns),
            'actual_attachment_identity_role_count': actual_identity_count,
            'action_or_helper_role_count': action_or_helper_count,
            'semantic_state': 'POST_HWP5_ATTACHMENT_LINK_ROLES_CLASSIFIED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'top_position_signatures': compact_position_signatures,
        'role_examples': dict(examples),
        'network_request_count': 0,
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
        'snapshot identity exact': doc.get('snapshot_identity_sha256') == EXPECTED_SNAPSHOT_SHA,
        'record count exact': len(records) == EXPECTED_ROWS,
        'total links exact': all_links == EXPECTED_LINKS,
        'three links per record': all(len(r.get('attachments') or []) == 3 for r in records),
        'roles account for all links': sum(role_counts.values()) == EXPECTED_LINKS,
        'network disabled': out['network_request_count'] == 0,
        'attachment download disabled': not out['attachment_body_download_executed'],
        'target-term search disabled': not out['target_term_search_executed'],
        'candidate promotion disabled': not out['candidate_promotion_allowed'],
        'negative evidence disabled': not out['negative_evidence_allowed'],
        'unsafe promotion leakage zero': not any(out[k] for k in ['site_positive_allowed', 'site_negative_allowed', 'runtime_registration_allowed']),
        'final resolution unknown': out['summary']['uqq700_final_resolution'] == 'UNKNOWN',
        'output written': OUT.exists() and OUT.stat().st_size > 0,
    }

    print('Records:', len(records))
    print('Total file-like links:', all_links)
    print('Role counts:', dict(sorted(role_counts.items())))
    print('Per-position roles:', out['summary']['per_position_role_counts'])
    print('Row role patterns:', out['summary']['row_role_patterns'])
    print('Actual attachment identity role count:', actual_identity_count)
    print('Action/helper role count:', action_or_helper_count)
    print('Output:', OUT)
    print('\nVALIDATION')
    for k, v in vals.items():
        print(f'{k}: {v}')
    print('all_pass:', all(vals.values()))
    if not all(vals.values()):
        raise AssertionError('S108 attachment link role forensic failed')


if __name__ == '__main__':
    main()
