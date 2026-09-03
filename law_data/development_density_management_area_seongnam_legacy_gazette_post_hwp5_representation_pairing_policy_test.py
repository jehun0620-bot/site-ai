# -*- coding: utf-8 -*-
"""S122: derive a safe per-gazette attachment representation pairing policy from S113 metadata.

S121 established that HWPX/HWTX content and preview text are encrypted. Before using PDF as the
primary extraction representation, this stage works offline from the S113 immutable metadata
registry only. It groups attachments by pstSn, compares normalized filename stems across PDF and
HWP/HWPX/HWTX items, classifies exact/near pairing, and proposes a conservative preferred source
policy. It performs no network requests, no downloads, no target-term search, and no legal inference.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REGISTRY = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_metadata_registry.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_representation_pairing_policy.json'
EXPECTED_REGISTRY_SHA = '1df06268311b3d1a1a1922bb3266c1cd26001477c4e8e688e22cbbbe98f3e570'
DOC_EXTS = {'hwp', 'hwpx', 'hwtx', 'pdf'}
SOURCE_EXTS = {'hwp', 'hwpx', 'hwtx'}


def norm(v):
    return str(v or '').strip()


def filename_stem(name):
    s = norm(name).replace('\\', '/').split('/')[-1]
    s = re.sub(r'\.[^.]+$', '', s)
    s = s.lower()
    s = re.sub(r'\s+', '', s)
    s = re.sub(r'[\[\](){}<>_\-]+', '', s)
    return s


def stem_similarity(a, b):
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return min(len(a), len(b)) / max(len(a), len(b))
    # lightweight common-prefix/suffix signal only; avoid fuzzy overreach.
    pref = 0
    for x, y in zip(a, b):
        if x != y:
            break
        pref += 1
    suf = 0
    for x, y in zip(reversed(a), reversed(b)):
        if x != y:
            break
        suf += 1
    return max(pref, suf) / max(len(a), len(b))


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 REPRESENTATION PAIRING POLICY - S122')
    print('=' * 60)
    print('Network: DISABLED')
    print('Downloads: DISABLED')
    print('Target-term search: DISABLED')
    print('Negative evidence: DISABLED')

    if not REGISTRY.exists():
        raise FileNotFoundError(REGISTRY)
    reg = json.loads(REGISTRY.read_text(encoding='utf-8'))
    summary = reg.get('summary') or {}
    if summary.get('registry_identity_sha256') != EXPECTED_REGISTRY_SHA:
        raise AssertionError('registry identity mismatch')

    attachments = [a for a in (reg.get('attachments') or []) if norm(a.get('extension')).lower() in DOC_EXTS]
    by_pst = defaultdict(list)
    for a in attachments:
        by_pst[str(a.get('pstSn'))].append(a)

    rows = []
    class_counts = Counter()
    policy_counts = Counter()

    def sort_key(a):
        return (int(a.get('position') or 0), int(a.get('fileNo') or 0))

    for pst, items in sorted(by_pst.items(), key=lambda kv: int(kv[0])):
        items = sorted(items, key=sort_key)
        pdfs = [a for a in items if norm(a.get('extension')).lower() == 'pdf']
        srcs = [a for a in items if norm(a.get('extension')).lower() in SOURCE_EXTS]
        pairs = []
        for src in srcs:
            sstem = filename_stem(src.get('filename') or src.get('orginlFileNm'))
            best = None
            for pdf in pdfs:
                pstem = filename_stem(pdf.get('filename') or pdf.get('orginlFileNm'))
                sim = stem_similarity(sstem, pstem)
                cand = {'source_fileNo': src.get('fileNo'), 'source_ext': norm(src.get('extension')).lower(), 'source_filename': src.get('filename') or src.get('orginlFileNm'), 'source_stem': sstem, 'pdf_fileNo': pdf.get('fileNo'), 'pdf_filename': pdf.get('filename') or pdf.get('orginlFileNm'), 'pdf_stem': pstem, 'stem_similarity': round(sim, 4)}
                if best is None or sim > best['stem_similarity']:
                    best = cand
            if best:
                pairs.append(best)

        if not srcs and pdfs:
            cls = 'PDF_ONLY'
            policy = 'PDF_PRIMARY'
        elif srcs and not pdfs:
            cls = 'SOURCE_ONLY_NO_PDF'
            policy = 'NO_PDF_FALLBACK_TECHNICAL_UNKNOWN'
        elif len(srcs) == 1 and len(pdfs) == 1 and pairs and pairs[0]['stem_similarity'] == 1.0:
            cls = 'ONE_TO_ONE_EXACT_STEM'
            policy = 'PDF_PRIMARY_SOURCE_REPRESENTATION_PAIRED'
        elif srcs and pdfs and pairs and all(p['stem_similarity'] == 1.0 for p in pairs) and len(srcs) == len(pdfs):
            cls = 'MULTI_EXACT_STEM_PAIRING'
            policy = 'PDF_PRIMARY_SOURCE_REPRESENTATION_PAIRED'
        elif srcs and pdfs and pairs and all(p['stem_similarity'] >= 0.8 for p in pairs):
            cls = 'NEAR_STEM_PAIRING_REVIEW'
            policy = 'PAIRING_REVIEW_REQUIRED'
        else:
            cls = 'AMBIGUOUS_PAIRING'
            policy = 'PAIRING_REVIEW_REQUIRED'

        class_counts[cls] += 1
        policy_counts[policy] += 1
        rows.append({
            'pstSn': pst,
            'gazette_number': items[0].get('gazette_number'),
            'date': items[0].get('date'),
            'attachment_count': len(items),
            'source_count': len(srcs),
            'pdf_count': len(pdfs),
            'classification': cls,
            'proposed_policy': policy,
            'pairs': pairs,
            'attachments': [{
                'fileNo': a.get('fileNo'),
                'extension': norm(a.get('extension')).lower(),
                'filename': a.get('filename') or a.get('orginlFileNm'),
                'fileSize': a.get('fileSize'),
                'position': a.get('position'),
            } for a in items],
        })

    review_rows = [r for r in rows if r['proposed_policy'] == 'PAIRING_REVIEW_REQUIRED']
    no_pdf_rows = [r for r in rows if r['proposed_policy'] == 'NO_PDF_FALLBACK_TECHNICAL_UNKNOWN']
    pdf_primary_rows = [r for r in rows if r['proposed_policy'] in {'PDF_PRIMARY', 'PDF_PRIMARY_SOURCE_REPRESENTATION_PAIRED'}]

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S122',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_registry': str(REGISTRY),
        'registry_identity_sha256': summary.get('registry_identity_sha256'),
        'summary': {
            'gazette_row_count': len(rows),
            'attachment_item_count': len(attachments),
            'classification_counts': dict(class_counts),
            'policy_counts': dict(policy_counts),
            'pdf_primary_authorized_row_count': len(pdf_primary_rows),
            'pairing_review_required_row_count': len(review_rows),
            'no_pdf_fallback_row_count': len(no_pdf_rows),
            'semantic_state': 'POST_HWP5_REPRESENTATION_PAIRING_POLICY_CAPTURED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'rows': rows,
        'network_executed': False,
        'download_executed': False,
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
        'all 219 gazette rows accounted': len(rows) == 219,
        'all 434 attachment items accounted': len(attachments) == 434,
        'network disabled': not out['network_executed'],
        'downloads disabled': not out['download_executed'],
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
    if review_rows:
        print('\nPAIRING REVIEW REQUIRED (first 20)')
        for r in review_rows[:20]:
            print('GAZETTE:', r.get('gazette_number'), 'pstSn:', r.get('pstSn'), 'CLASS:', r.get('classification'), 'ATTACHMENTS:', [(a['extension'], a['filename']) for a in r['attachments']])
    if no_pdf_rows:
        print('\nNO PDF FALLBACK')
        for r in no_pdf_rows:
            print('GAZETTE:', r.get('gazette_number'), 'pstSn:', r.get('pstSn'), 'ATTACHMENTS:', [(a['extension'], a['filename']) for a in r['attachments']])
    print('Output:', OUT)
    print('\nVALIDATION')
    for k, v in vals.items():
        print(f'{k}: {v}')
    print('all_pass:', all(vals.values()))
    if not all(vals.values()):
        raise AssertionError('S122 representation pairing policy failed')


if __name__ == '__main__':
    main()
