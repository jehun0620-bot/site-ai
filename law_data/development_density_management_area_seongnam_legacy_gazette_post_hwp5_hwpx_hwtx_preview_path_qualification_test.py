# -*- coding: utf-8 -*-
"""S121: qualify Preview/PrvText.txt as a safe text fallback for encrypted HWPX/HWTX packages.

S120 established that Contents/*.xml is AES-256-CBC protected in the package manifest. This stage
checks only Preview/PrvText.txt in the same deterministic HWPX/HWTX samples. It records whether the
preview member exists, whether the manifest marks it encrypted, whether ZIP-level bytes look like
plain text, and whether decoding produces useful text. It does not search UQQ700 terms.
"""
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
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_hwpx_hwtx_preview_path_qualification.json'

HOST = 'www.seongnam.go.kr'
DOWNLOAD = 'https://www.seongnam.go.kr/bbs010308/getFile'
BBS_CRT_SN = '16002'
EXPECTED_REGISTRY_SHA = '1df06268311b3d1a1a1922bb3266c1cd26001477c4e8e688e22cbbbe98f3e570'
FORMATS = ['hwpx', 'hwtx']
PREVIEW = 'Preview/PrvText.txt'
MANIFEST = 'META-INF/manifest.xml'
MAX_REQUESTS = 2
PER_FILE_BYTE_LIMIT = 32 * 1024 * 1024
TOTAL_BYTE_LIMIT = 40 * 1024 * 1024
TIMEOUT = 30
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'


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


def manifest_preview_contract(raw):
    root = ET.fromstring(raw)
    result = {'listed': False, 'media_type': None, 'size': None, 'encrypted': False}
    for el in root.iter():
        if local_name(el.tag) != 'file-entry':
            continue
        attrs = {local_name(k): str(v) for k, v in el.attrib.items()}
        if attrs.get('full-path') != PREVIEW:
            continue
        result['listed'] = True
        result['media_type'] = attrs.get('media-type')
        result['size'] = attrs.get('size')
        for child in el:
            if local_name(child.tag) == 'encryption-data':
                result['encrypted'] = True
                break
        break
    return result


def decode_preview(raw):
    candidates = ['utf-8-sig', 'utf-16', 'cp949', 'euc-kr']
    for enc in candidates:
        try:
            text = raw.decode(enc)
            cleaned = re.sub(r'\s+', ' ', text).strip()
            printable = sum(1 for ch in cleaned if ch.isprintable())
            ratio = printable / max(1, len(cleaned))
            if cleaned and ratio >= 0.90:
                return {'decode_state': 'PLAINTEXT_DECODED', 'encoding': enc, 'text_length': len(cleaned), 'printable_ratio': round(ratio, 4), 'text_prefix': cleaned[:1000]}
        except Exception:
            pass
    return {'decode_state': 'NOT_PLAINTEXT', 'encoding': None, 'text_length': 0, 'printable_ratio': 0.0, 'text_prefix': ''}


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 HWPX/HWTX PREVIEW PATH QUALIFICATION - S121')
    print('=' * 60)
    print('Encrypted Contents decryption: DISABLED')
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

        try:
            with zipfile.ZipFile(io.BytesIO(bytes(buf))) as zf:
                names = set(zf.namelist())
                contract = manifest_preview_contract(zf.read(MANIFEST)) if MANIFEST in names else {'listed': False, 'media_type': None, 'size': None, 'encrypted': None}
                exists = PREVIEW in names
                preview_raw = zf.read(PREVIEW) if exists else b''
                decoded = decode_preview(preview_raw) if exists else {'decode_state': 'MISSING', 'encoding': None, 'text_length': 0, 'printable_ratio': 0.0, 'text_prefix': ''}
            state = 'PREVIEW_PATH_QUALIFIED' if exists and decoded['decode_state'] == 'PLAINTEXT_DECODED' else 'PREVIEW_PATH_NOT_PLAINTEXT'
        except Exception as exc:
            technical_unknown += 1
            contract = {'listed': False, 'media_type': None, 'size': None, 'encrypted': None}
            exists = False
            preview_raw = b''
            decoded = {'decode_state': 'ERROR', 'encoding': None, 'text_length': 0, 'printable_ratio': 0.0, 'text_prefix': ''}
            state = 'ZIP_ANALYSIS_UNKNOWN'
            err = repr(exc)[:500]
        else:
            err = ''

        rec = {**a, 'http_status': resp.status_code, 'official_host': official, 'downloaded_byte_count': len(buf), 'preview_exists': exists, 'preview_byte_size': len(preview_raw), 'manifest_preview_contract': contract, **decoded, 'technical_state': state, 'error': err}
        records.append(rec)
        print('SAMPLE:', idx, '/', len(samples), 'EXT:', a.get('extension'), 'PREVIEW_EXISTS:', exists, 'MANIFEST_ENCRYPTED:', contract.get('encrypted'), 'DECODE:', decoded['decode_state'], 'TEXT_LEN:', decoded['text_length'])
        if decoded.get('text_prefix'):
            print('TEXT_PREFIX:', decoded['text_prefix'][:500])

    qualified = sum(1 for r in records if r.get('technical_state') == 'PREVIEW_PATH_QUALIFIED')
    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S121',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_registry': str(REGISTRY),
        'registry_identity_sha256': summary.get('registry_identity_sha256'),
        'summary': {
            'sample_format_count': len(samples),
            'request_count': request_count,
            'preview_qualified_count': qualified,
            'technical_unknown_count': technical_unknown,
            'total_downloaded_bytes': total_bytes,
            'semantic_state': 'POST_HWP5_HWPX_HWTX_PREVIEW_PATH_QUALIFICATION_CAPTURED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'records': records,
        'downloaded_binary_retained': False,
        'encrypted_contents_decryption_attempted': False,
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
        'encrypted decryption disabled': not out['encrypted_contents_decryption_attempted'],
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
        raise AssertionError('S121 preview path qualification failed')


if __name__ == '__main__':
    main()
