# -*- coding: utf-8 -*-
"""STEP 17-21-C-16-8-T-13-S1: harden T-13 result-row identity before T-14."""
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse, parse_qsl

BASE_DIR=Path(__file__).resolve().parent.parent
INPUT_PATH=BASE_DIR/'law_data'/'output'/'development_density_management_area_competent_authority_historical_pagination_discovery.json'
OUTPUT_PATH=BASE_DIR/'law_data'/'output'/'development_density_management_area_competent_authority_result_row_structure_hardening.json'
TARGET_NAME='개발밀도관리구역'; STANDARD_CODE='UQQ700'
INPUT_CLASSES={'RECOVERED_AUTHORITY_NOTICE_RESULT_ROW','RECOVERED_AUTHORITY_URBAN_RESULT_ROW'}
GENERIC={'고시 공고','고시공고','열람','목록','보기','상세보기','검색','다음','이전','처음','마지막'}
DATE_RE=re.compile(r'(?<!\d)(?:19|20)\d{2}[.\-/년\s]+(?:0?[1-9]|1[0-2])[.\-/월\s]+(?:0?[1-9]|[12]\d|3[01])(?:일)?(?!\d)')
NOTICE_RE=re.compile(r'(?:고시|공고)\s*제?\s*\d{2,4}\s*[-－]\s*\d+\s*호?',re.I)
DETAIL_HINTS=('view','detail','read','bbsview','article','idx','seq','nttid','article_no','board_seq')

def norm(v:Any)->str:return re.sub(r'\s+',' ',str(v or '')).strip()
def unique(v):
 out=[]
 for x in v:
  x=norm(x)
  if x and x not in out:out.append(x)
 return out

def detail_identity(url:str)->bool:
 p=urlparse(norm(url)); blob=(p.path+'?'+p.query).lower(); q={k.lower():v for k,v in parse_qsl(p.query)}
 return any(x in blob for x in DETAIL_HINTS) or any(k in q for k in ('idx','seq','nttid','articleno','board_seq','boardseq'))

def main():
 print('='*60);print('DEVELOPMENT DENSITY MANAGEMENT AREA');print('COMPETENT AUTHORITY RESULT-ROW STRUCTURE HARDENING');print('='*60)
 data=json.loads(INPUT_PATH.read_text(encoding='utf-8')); rows=data.get('next_stage_result_row_pool') or []
 accepted:List[Dict[str,Any]]=[]; rejected=[]
 for i,row in enumerate(rows,1):
  if not isinstance(row,dict) or norm(row.get('classification')) not in INPUT_CLASSES:continue
  text=norm(row.get('row_text')); variants=unique(row.get('row_text_variants') or []); url=norm(row.get('url'))
  evidence=norm(' '.join([text]+variants)); dates=unique((row.get('dates') or [])+DATE_RE.findall(evidence)); notices=unique((row.get('notice_numbers') or [])+[m.group(0) for m in NOTICE_RE.finditer(evidence)])
  generic=text.lower() in {x.lower() for x in GENERIC} or (len(text)<=8 and any(x.lower()==text.lower() for x in GENERIC))
  detail=detail_identity(url)
  metadata=bool(dates or notices or detail)
  source_endpoint=any(url==norm(x) for x in (row.get('source_urls') or [])) or any(url==norm(x) for x in (row.get('page_urls') or []))
  reasons=[]
  if generic:reasons.append('GENERIC_MENU_OR_NAV_TEXT')
  if not metadata:reasons.append('DOCUMENT_METADATA_IDENTITY_MISSING')
  if source_endpoint:reasons.append('SOURCE_OR_PAGE_ENDPOINT_IDENTITY')
  qualified=not reasons
  item=dict(row);item['structure_hardened']=qualified;item['structure_hardening_reasons']=reasons or ['MEANINGFUL_ROW_AND_DOCUMENT_METADATA_PRESENT'];item['dates']=dates;item['notice_numbers']=notices;item['detail_identity']=detail;item['verified_positive']=False;item['runtime_registration_allowed']=False;item['site_positive_allowed']=False;item['site_negative_allowed']=False
  (accepted if qualified else rejected).append(item)
  print('-'*60);print('ROW',i);print('URL:',url);print('Text:',text);print('Metadata identity:',metadata);print('Accepted:',qualified);print('Reasons:',item['structure_hardening_reasons'])
 out={'step':'STEP 17-21-C-16-8-T-13-S1 Competent Authority Result-Row Structure Hardening','target':{'name':TARGET_NAME,'standard_code':STANDARD_CODE},'summary':{'t13_result_row_count':len(rows),'structurally_accepted_count':len(accepted),'structurally_rejected_count':len(rejected)},'accepted_result_rows':accepted,'rejected_result_rows':rejected,'next_stage_result_row_pool':accepted,'resolution':'COMPETENT_AUTHORITY_RESULT_ROW_STRUCTURE_HARDENING_COMPLETED','next_action':'Accepted rows only may enter T-14. If zero, preserve UNKNOWN and deepen historical archive discovery; do not run direct document verification.','verified_positive':False,'runtime_registration_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False}
 OUTPUT_PATH.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 leakage=sum(1 for x in accepted if norm(x.get('row_text')).lower() in {v.lower() for v in GENERIC} or not ((x.get('dates') or []) or (x.get('notice_numbers') or []) or x.get('detail_identity')))
 validations={'target name':TARGET_NAME=='개발밀도관리구역','standard code':STANDARD_CODE=='UQQ700','T-13 input exists':INPUT_PATH.exists(),'T-13 rows loaded':len(rows)>0,'generic menu leakage zero':leakage==0,'verified positive remains blocked':out['verified_positive'] is False,'runtime registration remains blocked':out['runtime_registration_allowed'] is False,'SITE TRUE remains blocked':out['site_positive_allowed'] is False,'SITE FALSE remains blocked':out['site_negative_allowed'] is False,'output written':OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size>0}
 print();print('='*60);print('RESULT');print('='*60);print('T-13 result row count:',len(rows));print('Structurally accepted:',len(accepted));print('Structurally rejected:',len(rejected));print('Generic/menu leakage:',leakage);print('Output:',OUTPUT_PATH);print();print('='*60);print('VALIDATION');print('='*60)
 for k,v in validations.items():print(f'{k}: {v}')
 print();print('all_pass:',all(validations.values()))
 if not all(validations.values()):raise AssertionError('UQQ700 result-row structure hardening failed')
if __name__=='__main__':main()
