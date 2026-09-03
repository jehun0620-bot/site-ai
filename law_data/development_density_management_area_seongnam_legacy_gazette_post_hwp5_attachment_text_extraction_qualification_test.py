# -*- coding: utf-8 -*-
"""S116: qualify deterministic text extraction for each POST-HWP5 attachment format.

Inputs:
- S113 metadata registry (local output)
- S115 validated composite download contract: bbsCrtSn + pstSn + fileNo

For at most one deterministic sample per observed extension (hwp, hwpx, hwtx, pdf), this stage:
1) downloads the attachment with strict byte ceilings;
2) extracts text using format-specific non-OCR methods;
3) records extraction success, text length and safe diagnostic prefix.

Extraction methods:
- PDF: pypdf text layer only
- HWPX/HWTX: ZIP/XML text nodes only
- HWP: pyhwp/hwp5txt subprocess if available; otherwise technical unsupported

OCR is disabled. UQQ700 target-term search is disabled. Extracted text is diagnostic only and
must not be interpreted as legal negative evidence. Downloaded binary files are not retained.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import requests

BASE = Path(__file__).resolve().parent.parent
REGISTRY = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_metadata_registry.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_text_extraction_qualification.json'

HOST = 'www.seongnam.go.kr'
DOWNLOAD = 'https://www.seongnam.go.kr/bbs010308/getFile'
BBS_CRT_SN = '16002'
EXPECTED_REGISTRY_SHA = '1df06268311b3d1a1a1922bb3266c1cd26001477c4e8e688e22cbbbe98f3e570'
FORMATS = ['hwp', 'hwpx', 'hwtx', 'pdf']
MAX_REQUESTS = 4
PER_FILE_BYTE_LIMIT = 32 * 1024 * 1024
TOTAL_BYTE_LIMIT = 64 * 1024 * 1024
TIMEOUT = 30
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'


def norm(v):
    return str(v or '').strip()


def select_samples(attachments):
    out = []
    for ext in FORMATS:
        xs = [a for a in attachments if norm(a.get('extension')).lower() == ext]
        xs.sort(key=lambda a: (str(a.get('date') or ''), int(a.get('gazette_number') or 0), int(a.get('pstSn') or 0), int(a.get('position') or 0)))
        if xs:
            out.append(xs[0])
    return out


def clean_text(text):
    return re.sub(r'\s+', ' ', str(text or '')).strip()


def extract_pdf(data):
    try:
        from pypdf import PdfReader
    except Exception as exc:
        return '', 'PDF_DEPENDENCY_UNAVAILABLE', repr(exc)[:500]
    try:
        reader = PdfReader(io.BytesIO(data))
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or '')
            except Exception:
                continue
        text = clean_text('\n'.join(parts))
        return text, ('EXTRACTED' if text else 'NO_TEXT_LAYER'), ''
    except Exception as exc:
        return '', 'PDF_EXTRACTION_ERROR', repr(exc)[:500]


def extract_zip_xml(data, ext):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            xml_names = [n for n in names if n.lower().endswith(('.xml', '.xhtml', '.html'))]
            parts = []
            parse_errors = 0
            for name in xml_names:
                try:
                    raw = zf.read(name)
                    root = ET.fromstring(raw)
                    vals = [t.strip() for t in root.itertext() if t and t.strip()]
                    if vals:
                        parts.append(' '.join(vals))
                except Exception:
                    parse_errors += 1
            text = clean_text('\n'.join(parts))
            if text:
                return text, 'EXTRACTED', f'xml_files={len(xml_names)};parse_errors={parse_errors}'
            return '', 'NO_XML_TEXT', f'xml_files={len(xml_names)};parse_errors={parse_errors}'
    except Exception as exc:
        return '', f'{ext.upper()}_ZIP_EXTRACTION_ERROR', repr(exc)[:500]


def find_hwp5txt():
    candidates = ['hwp5txt', 'hwp5txt.exe', 'pyhwp']
    for c in candidates:
        p = shutil.which(c)
        if p:
            return p
    return ''


def extract_hwp(data):
    tool = find_hwp5txt()
    if not tool:
        return '', 'HWP5TXT_UNAVAILABLE', 'hwp5txt/pyhwp command not found'
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'sample.hwp'
        p.write_bytes(data)
        commands = []
        name = Path(tool).name.lower()
        if 'hwp5txt' in name:
            commands.append([tool, str(p)])
        else:
            commands.extend([[tool, 'txt', str(p)], [tool, str(p)]])
        last_error = ''
        for cmd in commands:
            try:
                cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
                raw = cp.stdout
                text = ''
                for enc in ('utf-8', 'cp949', 'utf-16'):
                    try:
                        text = raw.decode(enc)
                        break
                    except Exception:
                        continue
                text = clean_text(text)
                if cp.returncode == 0 and text:
                    return text, 'EXTRACTED', f'command={cmd[0]};returncode=0'
                last_error = f'returncode={cp.returncode};stderr={cp.stderr[:300]!r}'
            except Exception as exc:
                last_error = repr(exc)[:500]
        return '', 'HWP_EXTRACTION_ERROR', last_error


def extract_by_format(ext, data):
    if ext == 'pdf':
        return extract_pdf(data)
    if ext in {'hwpx', 'hwtx'}:
        return extract_zip_xml(data, ext)
    if ext == 'hwp':
        return extract_hwp(data)
    return '', 'UNSUPPORTED_FORMAT', ext


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 ATTACHMENT TEXT EXTRACTION QUALIFICATION - S116')
    print('=' * 60)
    print('OCR: DISABLED')
    print('Target-term search: DISABLED')
    print('Negative evidence: DISABLED')

    if not REGISTRY.exists():
        raise FileNotFoundError(REGISTRY)
    reg = json.loads(REGISTRY.read_text(encoding='utf-8'))
    summary = reg.get('summary') or {}
    if summary.get('registry_identity_sha256') != EXPECTED_REGISTRY_SHA:
        raise AssertionError('registry identity mismatch')

    attachments = reg.get('attachments') or []
    sample = select_samples(attachments)
    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9'})

    records = []
    request_count = 0
    total_bytes = 0
    technical_unknown = 0

    for idx, a in enumerate(sample, 1):
        ext = norm(a.get('extension')).lower()
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
        data = bytes(buf)

        if resp.status_code != 200 or not official or overflow:
            technical_unknown += 1
            records.append({**a, 'http_status': resp.status_code, 'official_host': official, 'downloaded_byte_count': len(data), 'byte_limit_overflow': overflow, 'technical_state': 'DOWNLOAD_UNKNOWN'})
            continue

        text, extraction_state, detail = extract_by_format(ext, data)
        qualified = extraction_state == 'EXTRACTED' and len(text) > 0
        if not qualified:
            technical_unknown += 1
        records.append({
            **a,
            'http_status': resp.status_code,
            'official_host': official,
            'downloaded_byte_count': len(data),
            'byte_limit_overflow': overflow,
            'extraction_state': extraction_state,
            'extraction_detail': detail,
            'extracted_text_length': len(text),
            'diagnostic_text_prefix': text[:1000],
            'technical_state': 'EXTRACTION_QUALIFIED' if qualified else 'EXTRACTION_TECHNICAL_UNKNOWN',
        })
        print('SAMPLE:', idx, '/', len(sample), 'EXT:', ext, 'GAZETTE:', a.get('gazette_number'), 'pstSn:', a.get('pstSn'), 'fileNo:', a.get('fileNo'), 'BYTES:', len(data), 'EXTRACTION:', extraction_state, 'TEXT_LEN:', len(text))

    per_format = {}
    for r in records:
        e = norm(r.get('extension')).lower()
        per_format[e] = {
            'technical_state': r.get('technical_state'),
            'extraction_state': r.get('extraction_state'),
            'extracted_text_length': r.get('extracted_text_length', 0),
        }

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S116',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_registry': str(REGISTRY),
        'registry_identity_sha256': summary.get('registry_identity_sha256'),
        'download_endpoint': DOWNLOAD,
        'summary': {
            'sample_format_count': len(sample),
            'request_count': request_count,
            'qualified_format_count': sum(1 for r in records if r.get('technical_state') == 'EXTRACTION_QUALIFIED'),
            'technical_unknown_count': technical_unknown,
            'total_downloaded_bytes': total_bytes,
            'per_format': per_format,
            'semantic_state': 'POST_HWP5_ATTACHMENT_TEXT_EXTRACTION_QUALIFICATION_CAPTURED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'records': records,
        'downloaded_binary_retained': False,
        'ocr_executed': False,
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
        'request budget respected': request_count <= MAX_REQUESTS,
        'all selected samples accounted': len(records) == len(sample),
        'total byte budget respected': total_bytes <= TOTAL_BYTE_LIMIT,
        'downloaded binary not retained': not out['downloaded_binary_retained'],
        'ocr disabled': not out['ocr_executed'],
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
        raise AssertionError('S116 text extraction qualification failed')


if __name__ == '__main__':
    main()
