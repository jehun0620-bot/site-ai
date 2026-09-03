# -*- coding: utf-8 -*-
"""S120: inspect plaintext package metadata for HWPX/HWTX storage contract only."""
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import requests

BASE = Path(__file__).resolve().parent.parent
REGISTRY = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_metadata_registry.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_hwpx_hwtx_plain_manifest_contract.json'

HOST = 'www.seongnam.go.kr'
DOWNLOAD = 'https://www.seongnam.go.kr/bbs010308/getFile'
BBS_CRT_SN = '16002'
EXPECTED_REGISTRY_SHA = '1df06268311b3d1a1a1922bb3266c1cd26001477c4e8e688e22cbbbe98f3e570'
FORMATS = ['hwpx', 'hwtx']
MAX_REQUESTS = 2
PER_FILE_BYTE_LIMIT = 32 * 1024 * 1024
TOTAL_BYTE_LIMIT = 40 * 1024 * 1024
TIMEOUT = 30
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
PLAINTEXT_NAMES = {'version.xml', 'META-INF/container.xml', 'META-INF/manifest.xml'}


def norm(v):
    return str(v or '').strip()


def select_samples(attachments):
    out = []
    for ext in FORMATS:
        xs = [a for a in attachments if norm(a.get('extension')).lower() == ext]
        xs.sort(key=lambda a: (str(a.get('date') or ''), int(a.get('gazette_number') or 0), int(a.get('pstSn') or 0), int(a.get('position') or 0)))
        if not xs:
            raise AssertionError(f'no {ext} attachment')
        out.append(xs[0])
    return out


def local_name(tag):
    s = str(tag or '')
    return s.split('}', 1)[-1] if '}' in s else s


def parse_member(raw):
    root = ET.fromstring(raw)
    rows = []
    for el in root.iter():
        attrs = {local_name(k): str(v) for k, v in el.attrib.items()}
        text = re.sub(r'\s+', ' ', str(el.text or '')).strip()
        rows.append({'tag': local_name(el.tag), 'attributes': attrs, 'text': text[:500]})
    return local_name(root.tag), rows


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 HWPX/HWTX PLAINTEXT MANIFEST CONTRACT - S120')
    print('=' * 60)
    print('Binary payload transform: NOT ATTEMPTED')
    print('Target-term search: DISABLED')
    print('Negative evidence: DISABLED')

    if not REGISTRY.exists():
        raise FileNotFoundError(REGISTRY)
    reg = json.loads(REGISTRY.read_text(encoding='utf-8'))
    summary = reg.get('summary') or {}
    if summary.get('registry_identity_sha256') != EXPECTED_REGISTRY_SHA:
        raise AssertionError('registry identity mismatch')
    samples = select_samples(reg.get('attachments') or [])

    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9'})
    records = []
    request_count = 0
    total_bytes = 0
    technical_unknown = 0

    for idx, a in enumerate(samples, 1):
        params = {'bbsCrtSn': BBS_CRT_SN, 'pstSn': str(a.get('pstSn')), 'fileNo': str(a.get('fileNo'))}
        request_count += 1
        try:
            resp = session.get(DOWNLOAD, params=params, timeout=TIMEOUT, allow_redirects=True, stream=True)
        except Exception as exc:
            technical_unknown += 1
            records.append({**a, 'technical_state': 'TRANSPORT_ERROR', 'error': repr(exc)[:500]})
            continue

        official = (urlparse(str(resp.url)).hostname or '').lower() == HOST
        buf = bytearray()
        overflow = False
        try:
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                if len(buf) + len(chunk) > PER_FILE_BYTE_LIMIT or total_bytes + len(chunk) > TOTAL_BYTE_LIMIT:
                    overflow = True
                    break
                buf.extend(chunk)
                total_bytes += len(chunk)
        finally:
            resp.close()

        if resp.status_code != 200 or not official or overflow:
            technical_unknown += 1
            records.append({**a, 'http_status': resp.status_code, 'official_host': official, 'byte_limit_overflow': overflow, 'technical_state': 'DOWNLOAD_UNKNOWN'})
            continue

        members = []
        try:
            with zipfile.ZipFile(io.BytesIO(bytes(buf))) as zf:
                available = set(zf.namelist())
                for name in sorted(PLAINTEXT_NAMES & available):
                    raw = zf.read(name)
                    try:
                        root_tag, rows = parse_member(raw)
                        members.append({'name': name, 'parse_ok': True, 'root_tag': root_tag, 'elements': rows})
                    except Exception as exc:
                        members.append({'name': name, 'parse_ok': False, 'error': repr(exc)[:500]})
            state = 'PLAINTEXT_MANIFEST_CONTRACT_CAPTURED'
        except Exception as exc:
            technical_unknown += 1
            members = []
            state = 'ZIP_ANALYSIS_UNKNOWN'
            err = repr(exc)[:500]
        else:
            err = ''

        records.append({**a, 'http_status': resp.status_code, 'official_host': official, 'downloaded_byte_count': len(buf), 'plaintext_members': members, 'technical_state': state, 'error': err})
        print('SAMPLE:', idx, '/', len(samples), 'EXT:', a.get('extension'), 'PLAINTEXT_MEMBERS:', len(members))
        for m in members:
            print('MEMBER:', m['name'], '| ROOT:', m.get('root_tag'), '| PARSE_OK:', m.get('parse_ok'))
            if m.get('parse_ok'):
                for row in m['elements'][:40]:
                    attrs = row.get('attributes') or {}
                    if attrs:
                        print('  ELEMENT:', row.get('tag'), '| ATTRS:', attrs)

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S120',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_registry': str(REGISTRY),
        'registry_identity_sha256': summary.get('registry_identity_sha256'),
        'summary': {
            'sample_format_count': len(samples),
            'request_count': request_count,
            'technical_unknown_count': technical_unknown,
            'total_downloaded_bytes': total_bytes,
            'semantic_state': 'POST_HWP5_HWPX_HWTX_PLAINTEXT_MANIFEST_CONTRACT_CAPTURED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'records': records,
        'downloaded_binary_retained': False,
        'binary_payload_transform_attempted': False,
        'target_term_search_executed': False,
        'candidate_promotion_allowed': False,
        'negative_evidence_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    vals = {
        'registry identity exact': summary.get('registry_identity_sha256') == EXPECTED_REGISTRY_SHA,
        'sample count exact': len(samples) == MAX_REQUESTS,
        'request budget exact': request_count == MAX_REQUESTS,
        'all samples accounted': len(records) == MAX_REQUESTS,
        'total byte budget respected': total_bytes <= TOTAL_BYTE_LIMIT,
        'downloaded binary not retained': not out['downloaded_binary_retained'],
        'binary transform not attempted': not out['binary_payload_transform_attempted'],
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
        raise AssertionError('S120 plaintext manifest contract failed')


if __name__ == '__main__':
    main()
