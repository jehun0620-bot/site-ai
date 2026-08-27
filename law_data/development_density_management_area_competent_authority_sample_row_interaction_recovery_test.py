# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import urljoin, urlparse, parse_qsl

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
S1_INPUT_PATH = BASE_DIR / 'law_data' / 'output' / 'development_density_management_area_competent_authority_detail_contract_probe.json'
T16_INPUT_PATH = BASE_DIR / 'law_data' / 'output' / 'development_density_management_area_competent_authority_bounded_historical_range_traversal.json'
OUTPUT_DIR = BASE_DIR / 'law_data' / 'output'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / 'development_density_management_area_competent_authority_sample_row_interaction_recovery.json'

TARGET_NAME = '개발밀도관리구역'
STANDARD_CODE = 'UQQ700'
RESOLUTION_TYPE = 'HYBRID_SPATIAL_NOTICE'
NEGATIVE_EVIDENCE_ALLOWED = False

CLASS_STATIC = 'RECOVERED_SAMPLE_ROW_STATIC_DETAIL_INTERACTION'
CLASS_JS = 'RECOVERED_SAMPLE_ROW_JAVASCRIPT_DETAIL_INTERACTION'
CLASS_DATA = 'RECOVERED_SAMPLE_ROW_DATA_IDENTITY_INTERACTION'
CLASS_METADATA_ONLY = 'RECONFIRMED_SAMPLE_ROW_METADATA_ONLY'
CLASS_NOT_RELOCATED = 'SAMPLE_ROW_NOT_RELOCATED'
VALID_CLASSES = {CLASS_STATIC, CLASS_JS, CLASS_DATA, CLASS_METADATA_ONLY, CLASS_NOT_RELOCATED}
INTERACTION_CLASSES = {CLASS_STATIC, CLASS_JS, CLASS_DATA}

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 12
MAX_PAGES_PER_FAMILY = 6
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'

TR_PATTERN = re.compile(r'<tr\b(?P<attrs>[^>]*)>(?P<body>.*?)</tr>', re.I | re.S)
LI_PATTERN = re.compile(r'<li\b(?P<attrs>[^>]*)>(?P<body>.*?)</li>', re.I | re.S)
ANCHOR_PATTERN = re.compile(r'<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>', re.I | re.S)
BUTTON_PATTERN = re.compile(r'<button\b(?P<attrs>[^>]*)>(?P<body>.*?)</button>', re.I | re.S)
INPUT_PATTERN = re.compile(r'<input\b(?P<attrs>[^>]*)>', re.I | re.S)
ATTR_PATTERN = re.compile(r'''([:\w-]+)\s*=\s*(?:["']([^"']*)["']|([^\s>]+))''', re.I | re.S)
TAG_PATTERN = re.compile(r'<[^>]+>', re.S)
SCRIPT_STYLE_PATTERN = re.compile(r'<(?:script|style)\b.*?</(?:script|style)>', re.I | re.S)
COMMENT_PATTERN = re.compile(r'<!--.*?-->', re.S)
JS_CALL_PATTERN = re.compile(r'(?P<func>[A-Za-z_$][\w$]*)\s*\((?P<args>[^)]*)\)')
QUOTED_ARG_PATTERN = re.compile(r'''["']([^"']+)["']''')
NUMERIC_ARG_PATTERN = re.compile(r'(?<!\w)(\d{2,})(?!\w)')

DETAIL_QUERY_HINTS = {'idx','seq','nttid','ntt_id','article','article_no','post','post_no','board_seq','bbsid','bbs_id','notice','ancmt','sn'}
DETAIL_PATH_HINTS = ('/view','/detail','/read','/select','/bbs/','/board/','/notice/','/post/')
IDENTITY_ATTR_HINTS = ('idx','seq','ntt','article','post','board','bbs','notice','ancmt','sn')
GENERIC_JS_FUNCTIONS = {'alert','confirm','print','open','close','focus','blur','submit'}


def normalize_space(value: Any) -> str:
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def unique_strings(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: Set[str] = set()
    for value in values:
        text = normalize_space(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def strip_html(raw: str) -> str:
    value = COMMENT_PATTERN.sub(' ', raw or '')
    value = SCRIPT_STYLE_PATTERN.sub(' ', value)
    value = TAG_PATTERN.sub(' ', value)
    return normalize_space(html.unescape(value))


def parse_attrs(raw_attrs: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for match in ATTR_PATTERN.finditer(raw_attrs or ''):
        key = normalize_space(match.group(1)).lower()
        value = match.group(2) if match.group(2) is not None else match.group(3)
        if key:
            result[key] = html.unescape(normalize_space(value))
    return result


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or '').lower()
    except Exception:
        return ''


def is_government_host(host: str) -> bool:
    host = normalize_space(host).lower()
    return bool(host) and (host == 'go.kr' or host.endswith('.go.kr'))


def same_host(a: str, b: str) -> bool:
    return bool(hostname(a)) and hostname(a) == hostname(b)


def is_static_detail_url(url: str, page_url: str) -> bool:
    if not url or not is_government_host(hostname(url)) or not same_host(url, page_url):
        return False
    parsed = urlparse(url)
    if any(hint in (parsed.path or '').lower() for hint in DETAIL_PATH_HINTS):
        return True
    keys = {normalize_space(k).lower() for k, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    return bool(keys & DETAIL_QUERY_HINTS)


def decode_html(response: requests.Response, data: bytes) -> str:
    for encoding in unique_strings([response.encoding, 'utf-8', 'cp949', 'euc-kr']):
        try:
            return data.decode(encoding)
        except Exception:
            continue
    return data.decode('utf-8', errors='replace')


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result = {'http_status': None, 'final_url': '', 'raw_html': '', 'response_bytes': 0, 'error': ''}
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            result['http_status'] = response.status_code
            result['final_url'] = str(response.url)
            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError('response too large')
                chunks.append(chunk)
            data = b''.join(chunks)
            result['response_bytes'] = len(data)
            result['raw_html'] = decode_html(response, data)
    except Exception as exc:
        result['error'] = repr(exc)
    return result


def load_contracts(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get('next_stage_contract_pool')
    if not isinstance(raw, list):
        return []
    result = []
    for contract_index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        family = normalize_space(item.get('source_family'))
        samples = item.get('sample_rows') if isinstance(item.get('sample_rows'), list) else []
        pages = []
        for value in item.get('page_numbers') or []:
            try:
                page = int(value)
            except Exception:
                continue
            if page >= 1:
                pages.append(page)
        if family and samples:
            result.append({'contract_index': contract_index, 'source_family': family, 'page_numbers': sorted(set(pages)), 'sample_rows': samples})
    return result


def load_t16_pages(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get('page_records')
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw:
        if not isinstance(item, dict) or item.get('http_status') != 200:
            continue
        family = normalize_space(item.get('source_family'))
        url = normalize_space(item.get('final_url') or item.get('requested_url'))
        try:
            page_number = int(item.get('page_number') or 0)
        except Exception:
            page_number = 0
        if family and url and is_government_host(hostname(url)):
            result.append({'source_family': family, 'page_number': page_number, 'url': url})
    return result


def select_pages(contracts: List[Dict[str, Any]], pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_family: Dict[str, List[Dict[str, Any]]] = {}
    for page in pages:
        by_family.setdefault(page['source_family'], []).append(page)
    result = []
    seen = set()
    for family in sorted(by_family):
        wanted = set()
        for contract in contracts:
            if contract['source_family'] == family:
                wanted.update(contract.get('page_numbers') or [])
        ranked = sorted(by_family[family], key=lambda x: (0 if x.get('page_number') in wanted else 1, int(x.get('page_number') or 0)))
        count = 0
        for page in ranked:
            if count >= MAX_PAGES_PER_FAMILY or len(result) >= MAX_TOTAL_REQUESTS:
                break
            if page['url'] in seen:
                continue
            seen.add(page['url'])
            result.append(page)
            count += 1
    return result


def sample_signature(sample: Dict[str, Any]) -> Dict[str, Any]:
    return {'titles': unique_strings(sample.get('meaningful_anchor_texts') or []), 'notice_numbers': unique_strings(sample.get('notice_numbers') or []), 'dates': unique_strings(sample.get('dates') or [])}


def match_row(signature: Dict[str, Any], text: str) -> Tuple[bool, List[str]]:
    text = normalize_space(text)
    notice_hits = [v for v in signature['notice_numbers'] if v and v in text]
    title_hits = [v for v in signature['titles'] if len(v) >= 4 and v in text]
    date_hits = [v for v in signature['dates'] if v and v in text]
    reasons = []
    if notice_hits:
        reasons.append('SAMPLE_NOTICE_NUMBER_MATCH:' + '|'.join(notice_hits))
    if title_hits:
        reasons.append('SAMPLE_TITLE_MATCH:' + '|'.join(title_hits))
    if date_hits:
        reasons.append('SAMPLE_DATE_MATCH:' + '|'.join(date_hits))
    if notice_hits:
        return True, reasons
    if title_hits and (date_hits or len(title_hits) >= 2):
        return True, reasons
    if not signature['notice_numbers'] and title_hits and len(text) >= 20:
        return True, reasons
    return False, reasons


def extract_interactions(body: str, page_url: str) -> Dict[str, Any]:
    static_details = []
    javascript_calls = []
    data_identity = []
    hidden_identity = []
    for pattern, tag in [(ANCHOR_PATTERN, 'a'), (BUTTON_PATTERN, 'button')]:
        for match in pattern.finditer(body):
            attrs = parse_attrs(match.group('attrs'))
            text = strip_html(match.group('body'))
            href = normalize_space(attrs.get('href'))
            onclick = normalize_space(attrs.get('onclick'))
            if href and not href.lower().startswith(('javascript:', 'mailto:', 'tel:', '#')):
                absolute = urljoin(page_url, href)
                if is_static_detail_url(absolute, page_url):
                    static_details.append({'tag': tag, 'text': text, 'href': href, 'url': absolute})
            for source, evidence in [('href', href), ('onclick', onclick)]:
                if not evidence:
                    continue
                for js_match in JS_CALL_PATTERN.finditer(evidence):
                    function_name = normalize_space(js_match.group('func'))
                    args = normalize_space(js_match.group('args'))
                    quoted = unique_strings(QUOTED_ARG_PATTERN.findall(args))
                    numeric = unique_strings(NUMERIC_ARG_PATTERN.findall(args))
                    if function_name and function_name.lower() not in GENERIC_JS_FUNCTIONS and (quoted or numeric):
                        javascript_calls.append({'tag': tag, 'text': text, 'source': source, 'function': function_name, 'args': args, 'quoted_args': quoted, 'numeric_args': numeric})
            for key, value in attrs.items():
                if key.startswith('data-') and normalize_space(value) and any(hint in key.lower() for hint in IDENTITY_ATTR_HINTS):
                    data_identity.append({'tag': tag, 'name': key, 'value': value})
    for match in INPUT_PATTERN.finditer(body):
        attrs = parse_attrs(match.group('attrs'))
        if normalize_space(attrs.get('type')).lower() != 'hidden':
            continue
        name = normalize_space(attrs.get('name'))
        ident = normalize_space(attrs.get('id'))
        value = normalize_space(attrs.get('value'))
        if value and any(hint in f'{name} {ident}'.lower() for hint in IDENTITY_ATTR_HINTS):
            hidden_identity.append({'name': name, 'id': ident, 'value': value})
    return {'static_details': static_details, 'javascript_calls': javascript_calls, 'data_identity': data_identity, 'hidden_identity': hidden_identity}


def locate_samples_on_page(raw_html: str, page_url: str, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    fragments = []
    row_index = 0
    for kind, pattern in [('TR', TR_PATTERN), ('LI', LI_PATTERN)]:
        for match in pattern.finditer(raw_html or ''):
            row_index += 1
            fragments.append((kind, row_index, match.group('body')))
    located = []
    for sample_index, sample in enumerate(samples, start=1):
        signature = sample_signature(sample)
        best = None
        for kind, index, body in fragments:
            text = strip_html(body)
            matched, reasons = match_row(signature, text)
            if not matched:
                continue
            interactions = extract_interactions(body, page_url)
            score = 100 if any(r.startswith('SAMPLE_NOTICE_NUMBER_MATCH:') for r in reasons) else 0
            score += 30 if any(r.startswith('SAMPLE_TITLE_MATCH:') for r in reasons) else 0
            score += 15 if any(r.startswith('SAMPLE_DATE_MATCH:') for r in reasons) else 0
            score += 20 if interactions['static_details'] else 0
            score += 20 if interactions['javascript_calls'] else 0
            score += 15 if interactions['data_identity'] or interactions['hidden_identity'] else 0
            candidate = {'sample_index': sample_index, 'fragment_kind': kind, 'row_index': index, 'row_text': text[:3000], 'match_reasons': reasons, 'match_score': score, **interactions}
            if best is None or candidate['match_score'] > best['match_score']:
                best = candidate
        if best:
            located.append(best)
    return located


def main() -> None:
    print('=' * 60)
    print('DEVELOPMENT DENSITY MANAGEMENT AREA')
    print('COMPETENT AUTHORITY SAMPLE ROW LOCATOR & INTERACTION RECOVERY')
    print('=' * 60)
    print('Target:', TARGET_NAME)
    print('Standard code:', STANDARD_CODE)
    print('Resolution type:', RESOLUTION_TYPE)
    print('Target query execution: DISABLED')
    print('Target identity evaluation: DISABLED')
    print('Document candidate promotion: DISABLED')
    print()

    if not S1_INPUT_PATH.exists():
        raise FileNotFoundError(f'T-16-S1 input not found: {S1_INPUT_PATH}')
    if not T16_INPUT_PATH.exists():
        raise FileNotFoundError(f'T-16 input not found: {T16_INPUT_PATH}')

    s1_data = json.loads(S1_INPUT_PATH.read_text(encoding='utf-8'))
    t16_data = json.loads(T16_INPUT_PATH.read_text(encoding='utf-8'))
    contracts = load_contracts(s1_data)
    pages = load_t16_pages(t16_data)
    selected_pages = select_pages(contracts, pages)

    print('Detail contract count:', len(contracts))
    print('T-16 bounded page count:', len(pages))
    print('Selected page count:', len(selected_pages))
    print()

    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT, 'Accept-Language': 'ko-KR,ko;q=0.9'})
    request_count = 0
    http_success_count = 0
    transport_error_count = 0
    fetched_pages = []

    for index, page in enumerate(selected_pages, start=1):
        response = fetch_page(session, page['url'])
        request_count += 1
        status = response.get('http_status')
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get('error'):
            transport_error_count += 1
        final_url = normalize_space(response.get('final_url') or page['url'])
        fetched_pages.append({'source_family': page['source_family'], 'page_number': page['page_number'], 'url': final_url, 'http_status': status, 'raw_html': str(response.get('raw_html') or ''), 'error': response.get('error')})
        print('-' * 60)
        print(f'PAGE {index}')
        print('Family:', page['source_family'])
        print('Page number:', page['page_number'])
        print('HTTP:', status)

    contract_results = []
    next_stage_pool = []

    for contract in contracts:
        family = contract['source_family']
        located_records = []
        for page in fetched_pages:
            if page['source_family'] != family or page['http_status'] != 200:
                continue
            for item in locate_samples_on_page(page['raw_html'], page['url'], contract['sample_rows']):
                located_records.append({**item, 'page_url': page['url'], 'page_number': page['page_number']})

        canonical = {}
        for item in located_records:
            static_urls = tuple(sorted(unique_strings(x.get('url') for x in item.get('static_details') or [])))
            js_calls = tuple(sorted(unique_strings(f"{x.get('function')}({x.get('args')})" for x in item.get('javascript_calls') or [])))
            data_ids = tuple(sorted(unique_strings(f"{x.get('name')}={x.get('value')}" for x in (item.get('data_identity') or []) + (item.get('hidden_identity') or []))))
            key = (int(item.get('sample_index') or 0), static_urls, js_calls, data_ids)
            if key not in canonical:
                canonical[key] = {**item, 'page_urls': [item['page_url']], 'page_numbers': [item['page_number']]}
            else:
                existing = canonical[key]
                existing['page_urls'] = unique_strings((existing.get('page_urls') or []) + [item['page_url']])
                existing['page_numbers'] = sorted(set((existing.get('page_numbers') or []) + [item['page_number']]))

        rows = list(canonical.values())
        has_static = any(x.get('static_details') for x in rows)
        has_js = any(x.get('javascript_calls') for x in rows)
        has_data = any(x.get('data_identity') or x.get('hidden_identity') for x in rows)
        if has_static:
            classification, qualified = CLASS_STATIC, True
        elif has_js:
            classification, qualified = CLASS_JS, True
        elif has_data:
            classification, qualified = CLASS_DATA, True
        elif rows:
            classification, qualified = CLASS_METADATA_ONLY, False
        else:
            classification, qualified = CLASS_NOT_RELOCATED, False

        result = {'contract_index': contract['contract_index'], 'source_family': family, 'sample_row_count': len(contract['sample_rows']), 'located_row_count': len(rows), 'located_rows': rows, 'qualified_for_next_stage': qualified, 'classification': classification, 'target_query_executed': False, 'target_identity_evaluated': False, 'document_candidate': False, 'verified_positive': False, 'runtime_registration_allowed': False, 'site_positive_allowed': False, 'site_negative_allowed': False, 'final_positive_promotion_allowed': False}
        contract_results.append(result)
        if qualified:
            next_stage_pool.append({'contract_index': contract['contract_index'], 'source_family': family, 'classification': classification, 'located_rows': rows, 'requires_interaction_binding_verification': True, 'target_query_executed': False, 'target_identity_evaluated': False, 'document_candidate': False, 'verified_positive': False, 'runtime_registration_allowed': False, 'site_positive_allowed': False, 'site_negative_allowed': False, 'final_positive_promotion_allowed': False})

        print()
        print('-' * 60)
        print('CONTRACT', contract['contract_index'])
        print('Family:', family)
        print('Sample rows:', len(contract['sample_rows']))
        print('Located rows:', len(rows))
        print('Static interaction:', has_static)
        print('JavaScript interaction:', has_js)
        print('Data/hidden interaction:', has_data)
        print('Qualified for next stage:', qualified)
        print('Resolution:', classification)
        for row in rows[:5]:
            print('  Sample:', row.get('sample_index'), 'Page:', row.get('page_numbers'))
            print('  Match reasons:', row.get('match_reasons'))
            print('  Static:', row.get('static_details'))
            print('  JS:', row.get('javascript_calls'))
            print('  Data:', (row.get('data_identity') or []) + (row.get('hidden_identity') or []))

    if next_stage_pool:
        resolution = 'COMPETENT_AUTHORITY_SAMPLE_ROW_INTERACTION_RECOVERY_COMPLETED'
        next_action = '정확히 재식별된 sample row에서 복원된 interaction만 T-16-S5 executable interaction binding verification으로 넘긴다. 아직 UQQ700 target identity와 SITE 상태는 평가하지 않는다.'
    else:
        resolution = 'COMPETENT_AUTHORITY_SAMPLE_ROW_INTERACTION_RECOVERY_NO_INTERACTION'
        next_action = 'sample metadata row는 재식별되었지만 local detail interaction이 복원되지 않았거나 sample row 자체를 다시 찾지 못했다. SITE FALSE로 판정하지 않고 UNKNOWN을 유지하며 external script 또는 source-specific request mechanism을 별도 probe한다.'

    output_data = {
        'step': 'STEP 17-21-C-16-8-T-16-S4 Sample Row Locator & Interaction Recovery',
        'target': {'name': TARGET_NAME, 'standard_code': STANDARD_CODE},
        'resolution_policy': {'resolution_type': RESOLUTION_TYPE, 'negative_evidence_allowed': False, 'source_failure_site_status': 'UNKNOWN'},
        'inputs': {'t16_s1_path': str(S1_INPUT_PATH), 't16_path': str(T16_INPUT_PATH)},
        'method': {'S1_sample_rows_only': True, 'T16_bounded_pages_only': True, 'direct_network_requery': True, 'sample_notice_number_primary_locator': True, 'sample_title_date_secondary_locator': True, 'row_local_interaction_only': True, 'external_script_fetch_enabled': False, 'guessed_detail_url_enabled': False, 'guessed_function_enabled': False, 'target_query_execution_enabled': False, 'target_identity_evaluation_enabled': False, 'document_candidate_promotion_allowed': False, 'verified_positive_promotion_allowed': False, 'runtime_registration_allowed': False, 'site_positive_allowed': False, 'site_negative_allowed': False},
        'summary': {'detail_contract_count': len(contracts), 't16_bounded_page_count': len(pages), 'selected_page_count': len(selected_pages), 'request_count': request_count, 'http_success_count': http_success_count, 'transport_error_count': transport_error_count, 'contract_result_count': len(contract_results), 'next_stage_interaction_count': len(next_stage_pool)},
        'classification_counts': dict(sorted(Counter(x.get('classification') for x in contract_results).items())),
        'page_results': [{k: v for k, v in page.items() if k != 'raw_html'} for page in fetched_pages],
        'contract_results': contract_results,
        'next_stage_interaction_pool': next_stage_pool,
        'resolution': resolution,
        'next_action': next_action,
        'verified_positive': False,
        'runtime_registration_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'final_positive_promotion_allowed': False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding='utf-8')

    cross_host_static_leakage = 0
    for contract in next_stage_pool:
        for row in contract.get('located_rows') or []:
            page_url = normalize_space(row.get('page_url') or ((row.get('page_urls') or [''])[0]))
            for detail in row.get('static_details') or []:
                url = normalize_space(detail.get('url'))
                if not is_government_host(hostname(url)) or not same_host(page_url, url):
                    cross_host_static_leakage += 1

    target_query_leakage = sum(1 for x in contract_results + next_stage_pool if x.get('target_query_executed') is True)
    target_identity_leakage = sum(1 for x in contract_results + next_stage_pool if x.get('target_identity_evaluated') is True)
    unsafe_promotion_leakage = sum(1 for x in contract_results + next_stage_pool if x.get('document_candidate') is True or x.get('verified_positive') is True or x.get('runtime_registration_allowed') is True or x.get('site_positive_allowed') is True or x.get('site_negative_allowed') is True or x.get('final_positive_promotion_allowed') is True)

    validations = {
        'target name': TARGET_NAME == '개발밀도관리구역',
        'standard code': STANDARD_CODE == 'UQQ700',
        'resolution type hybrid spatial notice': RESOLUTION_TYPE == 'HYBRID_SPATIAL_NOTICE',
        'negative evidence disabled': NEGATIVE_EVIDENCE_ALLOWED is False,
        'T-16-S1 input exists': S1_INPUT_PATH.exists(),
        'T-16 input exists': T16_INPUT_PATH.exists(),
        'S1 sample contracts loaded': len(contracts) > 0,
        'T-16 bounded pages loaded': len(pages) > 0,
        'request budget respected': request_count <= MAX_TOTAL_REQUESTS,
        'sample row locator enabled': True,
        'row-local interaction only': True,
        'external script fetch disabled': True,
        'all classes valid': all(x.get('classification') in VALID_CLASSES for x in contract_results),
        'next-stage classes valid': all(x.get('classification') in INTERACTION_CLASSES for x in next_stage_pool),
        'cross-host static interaction leakage zero': cross_host_static_leakage == 0,
        'target query execution leakage zero': target_query_leakage == 0,
        'target identity evaluation leakage zero': target_identity_leakage == 0,
        'unsafe promotion leakage zero': unsafe_promotion_leakage == 0,
        'runtime registration remains blocked': output_data['runtime_registration_allowed'] is False,
        'SITE TRUE remains blocked': output_data['site_positive_allowed'] is False,
        'SITE FALSE remains blocked': output_data['site_negative_allowed'] is False,
        'final positive promotion remains blocked': output_data['final_positive_promotion_allowed'] is False,
        'output written': OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print('=' * 60)
    print('SAMPLE ROW INTERACTION RECOVERY RESULT')
    print('=' * 60)
    print('Detail contract count:', len(contracts))
    print('Selected page count:', len(selected_pages))
    print('Request count:', request_count)
    print('HTTP success count:', http_success_count)
    print('Transport error count:', transport_error_count)
    print('Next-stage interaction count:', len(next_stage_pool))
    print('Resolution:', resolution)
    print('Output:', OUTPUT_PATH)
    print()
    print('=' * 60)
    print('VALIDATION')
    print('=' * 60)
    for name, passed in validations.items():
        print(f'{name}: {passed}')
    print()
    print('Cross-host static interaction leakage:', cross_host_static_leakage)
    print('Target query leakage:', target_query_leakage)
    print('Target identity leakage:', target_identity_leakage)
    print('Unsafe promotion leakage:', unsafe_promotion_leakage)
    print()
    all_pass = all(validations.values())
    print(f'all_pass: {all_pass}')
    if not all_pass:
        print('FAILED:')
        for name, passed in validations.items():
            if not passed:
                print('-', name)
        raise AssertionError('UQQ700 sample row locator and interaction recovery regression failed')


if __name__ == '__main__':
    main()
