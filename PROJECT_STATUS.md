# AI 대지분석 자동화 시스템 — PROJECT STATUS

**Last updated: 2026-08-22**

---

## 1. 프로젝트 목표

주소 또는 필지를 입력하면 시스템이 자동으로 다음을 수행하는 **AI 대지분석 자동화 시스템**을 구축한다.

1. 주소 정규화 및 SITE 식별
2. PNU / 좌표 / 필지 Polygon 확보
3. 토지·건축물·도시계획 공간정보 수집
4. 용도지역·용도지구·용도구역 판정
5. 관련 법률·시행령·조례 수집
6. 법령 원문을 조/항/호/목/세부 clause 단위로 구조화
7. SITE와 관련 있는 규정만 선별
8. SITE / SITE_HISTORY / PROJECT / PROCEDURE 조건 판정
9. 기본 건폐율·용적률·높이 및 특례·완화·강화 규정 계산
10. 최종 대지분석 결과 객체 생성
11. HTTP API로 분석 서비스 제공
12. AI가 규칙엔진의 판정 결과를 설명하고 보고서로 생성

핵심 원칙:

> **Rule Engine이 판정하고, AI는 설명한다.**

---

## 2. 현재 대표 테스트 SITE

- 주소: 서울특별시 강남구 개포동 12번지
- 도로명주소: 서울특별시 강남구 개포로109길 21 (개포동)
- SITE ID: `11680-10300-0012-0000`
- PNU: `1168010300100120000`
- 시군구코드: `11680`
- 법정동코드: `10300`
- 본번: `0012`
- 부번: `0000`
- 용도지역: **제3종일반주거지역**
- 대표 좌표:
  - X: `127.07539280356858`
  - Y: `37.494197498186885`
  - CRS: `EPSG:4326`

Parcel Polygon dataset:

```text
LP_PA_CBND_BUBUN
```

MapPlan recovery 기준 Parcel:

```text
geometry: Polygon
area: 120945.65223377591
bounds:
[962201.02522, 1943722.58159, 962711.06096, 1944220.16506]

CRS: None
CRS status: SOURCE_CRS_NOT_EXPLICIT
```

공식 토지면적:

```text
121040.4 m²
source: VWORLD_LAND_CHARACTERISTICS
role: LEGAL_OR_ATTRIBUTE_LAND_AREA
```

MapPlan geometry 면적:

```text
120945.65223377591
source: MAPPLAN_PARCEL_GEOMETRY
role: SPATIAL_GEOMETRY_AREA
```

면적 차이 정책:

```text
difference: 94.74776622408535
difference ratio: 0.07827780329880384 %

resolution:
KEEP_BOTH_WITH_SOURCE_ROLES

primary:
official
```

---

## 3. 현재 서비스 아키텍처

```text
건축HUB / 토지 API
        ↓
create_site()
        ↓
Site dataclass
        ↓
analyze_site_object()
        ↓
build_site_analysis()
        ↓
SITE identity / spatial / land area
        +
Rule Evaluation Pipeline
        ↓
build_site_analysis_response()
        ↓
analyze_site_by_parcel()
        ↓
FastAPI
        ↓
POST /v1/site-analysis
```

법규 분석 내부 구조:

```text
법규 clause
+ 현재 SITE 용도지역 적합성
+ SITE 공간조건
+ SITE_HISTORY 조건
+ PROJECT 조건
+ PROCEDURE 조건
+ branch-local predicate
+ numeric semantic / guard
+ dynamic zone base numeric
= 실제 적용 가능성 및 최종 수치
```

---

## 4. STEP 1 ~ STEP 16 요약

### STEP 1 ~ STEP 15

완료:

- 주소 기반 SITE 생성
- SITE ID 생성
- 시군구 / 법정동 / 본번 / 부번 구조화
- 외부 API 연결 기반 구축
- `.env` 기반 API Key 관리
- SITE Builder 구축
- 외부 API 응답을 내부 SITE 데이터 구조로 변환
- 테스트 데이터 중심 구조에서 실제 공공 API 기반 구조로 전환
- 환경변수 이름 불일치 문제 수정
- 실제 API Key 로딩 정상화

### STEP 16 — 실제 토지/건축물 데이터 연결

실제 건축물 API:

```text
전체 데이터 수: 34
현재 받은 건축물 수: 34
resultCode: 00
resultMsg: NORMAL SERVICE
```

실제 토지 데이터:

```text
토지면적: 121040.4
지목: 대
용도지역: 제3종일반주거지역
```

---

## 5. STEP 17 — 법규 자동분석 엔진

주요 분석 법규:

- 국토의 계획 및 이용에 관한 법률
- 국토의 계획 및 이용에 관한 법률 시행령
- 서울특별시 도시계획 조례
- 관련 자치구 조례 / 행정규정

주요 효과 대상:

- 건폐율
- 용적률
- 높이
- 건축제한
- 완화 규정
- 강화 규정
- 예외 규정
- 특례 규정

국가법령정보센터 API를 통해 법률/시행령/자치법규 상세조회 JSON 연결을 검증하였다.

---

## 6. 특례 조건 모델

### SITE

현재 필지가 실제 특정 공간구역에 포함되는지 여부.

예:

- 지구단위계획
- 개발진흥지구
- 개발밀도관리구역
- 자연경관지구
- 취락지구
- 수산자원보호구역
- 입체복합구역
- 도시혁신구역
- 복합용도구역
- 산업단지
- 자연공원
- 방재지구
- 서울도심

### SITE_HISTORY

현재 상태가 아니라 과거 도시계획 또는 시설 변경 이력이 필요한 조건.

예:

- 학교이적지
- 도시지역편입해제구역

### PROJECT

사업계획 또는 건축계획에 의해 결정되는 조건.

예:

- 공개공지
- 공공시설제공
- 공공주택
- 공동주택
- 기부채납
- 대학
- 사회복지시설
- 임대주택
- 종합의료시설
- 주거복합
- 한옥
- 관광숙박시설
- 감염병대응필요시설

### PROCEDURE

심의 또는 행정절차에 관한 조건.

예:

- 도시계획위원회심의
- 시장정비사업심의

---

## 7. STEP 17-21-C-8 — 특례 Clause Parser

법령 원문을 다음 단계로 세분화하는 파서를 구축하였다.

```text
조 → 항 → 호 → 목 → 세부 clause
```

주요 검증 완료:

- 개정일자 조각 제거
- 도시지역 외 규정 배제
- 상업/공업/녹지지역 → 주거지역 오인 방지
- 용도지역 그룹 substring 중복 제거
- 도시지역(녹지지역만) 한정 처리
- 무공백 후속 호 경계 분리
- DIRECT 규정 내부 다중 목 잔존 제거
- 문장 종결 `다.`를 `다목`으로 오인하는 문제 해결
- 제46조 ⑮항 제3종일반주거지역 제외
- 시장정비사업 제3종일반주거지역 60% 나목 분리
- 학교이적지 제3종일반주거지역 200% 바목 분리

최종:

```text
C-8 parser: ALL PASS
총 clause: 314
```

---

## 8. 용도지역 관련성 판정

대표 SITE 계층:

```text
제3종일반주거지역
⊂ 일반주거지역
⊂ 주거지역
⊂ 도시지역
```

현재 dynamic zone relevance 상태:

```text
DIRECT
GROUP
OTHER_ZONE
UNSPECIFIED
```

C-13부터 기존 단일 SITE snapshot의 `zone_relevance`를 그대로 신뢰하지 않고,
현재 `site_zone_context`를 기준으로 재평가한다.

---

## 9. STEP 17-21-C-9 — SITE 공간조건 판정

핵심 원칙:

```text
법규명/조문명/검토문구의 문자열 출현
≠
해당 SITE가 실제 공간구역에 포함됨
```

안전 원칙:

```text
조회 실패 → UNKNOWN
source 미연결 → UNKNOWN
데이터 없음 → 자동 FALSE 금지
정상조회 + 유효한 비교근거 + 교차 없음 → FALSE
실제 면적 교차 확인 → TRUE
HTTP 403 자체 → TRUE/FALSE 근거로 사용 금지
후속 접근 실패만으로 기존 정상 HTTP 200 evidence를 폐기하지 않음
대표 Point보다 Parcel Polygon intersection 우선
```

C-9 최종 상태:

```text
status: COMPLETE_WITH_UNKNOWNS
```

주요 확정 조건:

| 조건 | 상태 | 신뢰도 |
|---|---|---|
| 지구단위계획 | TRUE | HIGH |
| 개발진흥지구 | FALSE | HIGH |
| 자연경관지구 | FALSE | HIGH |
| 입체복합구역 | FALSE | HIGH |
| 도시혁신구역 | FALSE | HIGH |
| 복합용도구역 | FALSE | HIGH |
| 수산자원보호구역 | FALSE | HIGH |
| 취락지구 | FALSE | HIGH |
| 산업단지 | FALSE | HIGH |
| 자연공원 | FALSE | HIGH |
| 개발밀도관리구역 | FALSE | HIGH |
| 학교이적지 | FALSE | HIGH |
| 서울도심 | FALSE | HIGH |
| 방재지구 | FALSE | HIGH |
| 도시지역편입해제구역 | UNKNOWN | MEDIUM |

---

## 10. SITE_HISTORY external dependency

도시지역편입해제구역:

```text
status: UNKNOWN
confidence: MEDIUM
automation_state: HISTORICAL_SOURCE_PENDING
blocking_site_stage: False
```

핵심 정책:

> 과거 핵심 원문이 미확인된 상태에서는 negative DB 검색만으로 FALSE를 강제하지 않는다.

따라서 현재 Rule Engine은:

```text
COMPLETE_WITH_EXTERNAL_DEPENDENCY
```

로 동작하며 분석 실행 자체는 차단하지 않는다.

---

## 11. STEP 17-21-C-10 — Rule Applicability / Numeric Evaluation

C-9 SITE / SITE_HISTORY 결과를 314개 clause의 applicability와 numeric effect에 연결하였다.

CLEAN baseline:

```text
APPLICABLE: 58
NOT_APPLICABLE: 211
CONDITIONAL: 43
UNKNOWN: 2
TOTAL: 314
```

대표 dynamic scenario:

```text
PROJECT:
공동주택 = TRUE

PROCEDURE:
도시계획위원회심의 = TRUE
```

branch-local overlay + verified numeric guard 이후:

```text
APPLICABLE: 63
NOT_APPLICABLE: 213
CONDITIONAL: 36
UNKNOWN: 2
TOTAL: 314
```

Numeric:

```text
Active numeric before guard: 11
Excluded: 3
Retained: 8
Direct relaxation: 0

Numeric resolution:
BASE_VALUES_RETAINED

Confirmed BCR: 50.0
Confirmed FAR: 250.0
```

---

## 12. Numeric Semantic / Guard Engine

Numeric clause:

```text
Numeric clauses: 124
Final numeric candidates after hierarchy dedup: 28
```

주요 semantic type:

- `RANGE`
- `BASE_RATIO_MULTIPLIER`
- `ABSOLUTE_MAX`
- `MAX_LIMIT_REDUCTION_RATIO`
- `ABSOLUTE_CEILING`
- `NON_EFFECT_THRESHOLD`
- `MAX_LIMIT_MULTIPLIER`

핵심 정책:

- 부모 aggregate clause + child leaf clause 중복 적용 금지
- applicability만으로 numeric effect 적용 금지
- 상위 법령 branch 검증 필수
- ceiling과 direct relaxation을 구분
- stacking 허용 여부 별도 판정

검증 완료 주요 clause:

```text
clause 4
→ 상위 branch 불일치
→ direct BCR relaxation 금지

clause 189
→ 방재지구 FALSE
→ FAR 300 후보 제거

clause 205
→ 관광숙박시설 / 서울도심 / 서울조례 제48조 7~10호 branch 검증
→ current SITE direct effect 금지

clause 250
→ stacking ceiling / outside district plan branch로 정리
→ current representative SITE direct effect 아님
```

---

## 13. Reusable Rule Evaluation Pipeline

구축 완료 모듈:

```text
law_data/rule_evaluation_pipeline.py
```

주요 입력:

```python
evaluate_site_rules(
    project_profile=...,
    procedure_profile=...,
    base_numeric_context=...,
    site_zone_context=...,
)
```

현재 기능:

```text
CLEAN baseline load
+ dynamic SITE zone relevance
+ SITE resolution registry
+ PROJECT input
+ PROCEDURE input
+ branch-local predicate
+ numeric semantic / guard
+ dynamic base numeric
+ external dependency
= reusable rule evaluation
```

대표 regression:

```text
Pipeline ready: True

Baseline:
58 / 211 / 43 / 2

Final representative scenario:
63 / 213 / 36 / 2

Confirmed BCR/FAR:
50 / 250

all_pass: True
```

---

## 14. STEP 17-21-C-11 — SITE Analysis Object 통합

상위 서비스가 개별 `law_data/output/*.json`을 직접 해석하지 않도록
단일 분석 객체를 구축하였다.

핵심 API:

```python
build_site_analysis()
```

통합 내용:

- SITE identity
- PNU
- 도로명주소
- 좌표
- Parcel geometry
- 토지면적 source reconciliation
- 용도지역
- BCR/FAR
- Rule summary
- remaining PROJECT/PROCEDURE inputs
- external dependencies
- debug/evidence

대표 상태:

```text
Analysis status: READY
Engine: RULE_EVALUATION_PIPELINE
```

---

## 15. SITE Identity Resolver

대표 결과:

```text
SITE ID: 11680-10300-0012-0000
PNU: 1168010300100120000

Sigungu: 11680
Bjdong: 10300
Main/Sub: 0012 / 0000

Coordinate:
127.07539280356858
37.494197498186885
EPSG:4326

Identity status: COMPLETE
Coordinate status: CONFIRMED
```

Parcel reference:

```text
dataset: LP_PA_CBND_BUBUN
status: VERIFIED
strict_pnu_verified: True
```

---

## 16. Parcel Spatial Recovery / Multi-SITE Spatial Resolver

로컬 원본 shapefile은 발견하지 못했으나,
기존 정상 MapPlan response JSON에서 representative SITE Polygon을 복구하였다.

복구 source:

```text
law_data/output/seoul_urban_innovation_zone_mapplan_intersection.json
```

복구 결과:

```text
PNU: 1168010300100120000
Geometry: Polygon
Area evidence: 120945.65223377591
Bounds:
[962201.02522, 1943722.58159, 962711.06096, 1944220.16506]
```

C-13에서는 spatial payload resolver가 현재 SITE PNU와 snapshot PNU를 비교한다.

정책:

```text
PNU 일치
→ snapshot geometry 사용 가능

PNU 불일치
→ 대표 SITE geometry를 재사용하지 않음
→ geometry_loaded = False
→ bounds = None
→ spatial area = None
```

이로써 대표 SITE Polygon이 다른 SITE에 누수되는 문제를 제거했다.

---

## 17. STEP 17-21-C-12 — Service / API Layer

### 서비스 흐름

```text
건축HUB 실제 API
→ create_site()
→ Site dataclass
→ analyze_site_object()
→ build_site_analysis()
→ build_site_analysis_response()
→ analyze_site_by_parcel()
→ FastAPI
```

### FastAPI

App:

```text
api_app.py
```

Endpoints:

```text
GET /health
POST /v1/site-analysis
```

Swagger:

```text
/docs
```

OpenAPI:

```text
/openapi.json
```

Schema:

```text
SITE_ANALYSIS_API_V1
```

실제 서버 검증:

```text
GET /health → 200
GET /docs → 200
GET /openapi.json → 200
POST /v1/site-analysis → 200
```

대표 API 결과:

```text
Status: READY
BCR: 50.0
FAR: 250.0
Rules: 63 / 213 / 36 / 2
Building count: 34
```

---

## 18. C-12 API Contract / Error Handling 완료

검증 완료 HTTP contract:

```text
Normal request: 200
Invalid schema: 422
Missing field: 422
Site not found: 404
Building API error: 502
Analysis error: 500
Unexpected error: 500
```

Final contract regression:

```text
SITE_ANALYSIS_API_V1 FINAL CONTRACT
Missing top keys: []

HTTP success: 200
HTTP validation: 422
HTTP not found: 404
HTTP upstream: 502
HTTP internal: 500

Schema freeze: READY
all_pass: True
```

주요 테스트:

```text
test_api_error_contract.py
test_api_contract_final_regression.py
test_api_app.py
```

---

## 19. STEP 17-21-C-13 — Multi-SITE Generalization

### 문제 발견

초기 leakage probe에서 synthetic SITE를 넣어도:

```text
대표 SITE Parcel geometry가 재사용됨
BCR/FAR가 50/250으로 고정됨
Rule summary가 동일함
```

초기 signal:

```text
SPATIAL_SNAPSHOT_FIXED_TO_BASE_SITE
NUMERIC_BASELINE_SINGLE_SITE_SUSPECTED
RULE_EVALUATION_SINGLE_SITE_SUSPECTED
```

따라서 C-13에서 다음 세 축을 분리하여 수정하였다.

```text
1. Spatial
2. Numeric
3. Rule applicability
```

---

## 20. C-13 Spatial Leakage 제거

대표 SITE snapshot PNU:

```text
1168010300100120000
```

synthetic SITE PNU:

```text
1168010300100130000
```

PNU가 다르면 대표 snapshot을 사용하지 않도록 수정.

최종 synthetic SITE spatial:

```text
Parcel PNU: 1168010300100130000
Parcel loaded: False
Parcel bounds: None
Spatial area: None
```

결과:

```text
Parcel still base PNU: False
Same parcel bounds: False
Same spatial area: False
```

Spatial leakage 제거 완료.

---

## 21. C-13 Dynamic Zone Base Numeric Resolver

기존 문제:

```text
제3종일반주거지역 → 50 / 250
일반상업지역 → 50 / 250
자연녹지지역 → 50 / 250
```

즉 base numeric이 대표 SITE snapshot에 고정되어 있었다.

### Source resolution

서울시 조례와 국가 시행령의 용도지역별 BCR/FAR source를 다시 추적하였다.

16개 주요 용도지역 모두 해결:

```text
Zones: 16
Resolved: 16
Unresolved: 0
Ambiguous: 0

resolution:
SEOUL_ZONE_BASE_NUMERIC_COMPLETE
```

Resolved Seoul base numeric:

| 용도지역 | BCR | FAR |
|---|---:|---:|
| 제1종전용주거지역 | 50 | 100 |
| 제2종전용주거지역 | 40 | 120 |
| 제1종일반주거지역 | 60 | 150 |
| 제2종일반주거지역 | 60 | 200 |
| 제3종일반주거지역 | 50 | 250 |
| 준주거지역 | 60 | 400 |
| 중심상업지역 | 60 | 1000 |
| 일반상업지역 | 60 | 800 |
| 근린상업지역 | 60 | 600 |
| 유통상업지역 | 60 | 600 |
| 전용공업지역 | 60 | 200 |
| 일반공업지역 | 60 | 200 |
| 준공업지역 | 60 | 400 |
| 보전녹지지역 | 20 | 50 |
| 생산녹지지역 | 20 | 50 |
| 자연녹지지역 | 20 | 50 |

신규 resolver:

```text
law_data/zone_base_numeric_resolver.py
```

대표 테스트:

```text
제3종일반주거지역 => 50 / 250
일반상업지역 => 60 / 800
자연녹지지역 => 20 / 50
준주거지역 => 60 / 400
준공업지역 => 60 / 400

all_pass: True
```

---

## 22. C-13 Dynamic Numeric Injection

`evaluate_site_rules()` 확장:

```python
base_numeric_context
```

dynamic context 직접 테스트:

```text
Input:
BCR 60
FAR 800

Result:
Confirmed BCR: 60.0
Confirmed FAR: 800.0
Numeric resolution: BASE_VALUES_RETAINED

all_pass: True
```

`site_analysis_builder.py`는 현재 SITE zone을 확정한 후:

```text
site.zone
→ resolve_zone_base_numeric()
→ evaluate_site_rules(base_numeric_context=...)
```

순서로 실행한다.

결과:

```text
BASE:
제3종일반주거지역 → 50 / 250

ALTERNATE:
일반상업지역 → 60 / 800
```

Numeric leakage 제거 완료.

---

## 23. C-13 Dynamic Rule SITE Context

`evaluate_site_rules()` 확장:

```python
site_zone_context
```

기존 문제:

```text
site_rule_evaluation_site_complete.json
```

안의 `zone_relevance`가 대표 SITE인 제3종일반주거지역 기준으로 이미 생성되어 있었다.

C-13에서는 현재 SITE zone을 기준으로:

```python
classify_zone_relevance()
```

를 다시 호출한다.

상태:

```text
DIRECT
GROUP
OTHER_ZONE
UNSPECIFIED
```

---

## 24. Zone Transition Safety Policy

전체 rule applicability를 무조건 재계산했을 때 BASE regression이 깨지는 문제가 발견되었다.

실패 사례:

```text
BASE expected:
63 / 213 / 36 / 2

unsafe full recalc:
106 / 170 / 36 / 2
```

따라서 전체 재계산을 폐기하고,
zone transition만 제한적으로 반영한다.

정책:

```text
DIRECT/GROUP → OTHER_ZONE
=> NOT_APPLICABLE

OTHER_ZONE → DIRECT/GROUP
=> 무조건 APPLICABLE 금지
```

자동 재활성화는 현재 검증된 다음 기본/reference 규칙 유형으로 제한:

```text
국토의 계획 및 이용에 관한 법률
- 용도지역의 건폐율
- 용도지역에서의 용적률
```

예:

```text
주거지역 BCR leaf
clause 61:
GROUP → OTHER_ZONE
=> NOT_APPLICABLE

상업지역 BCR leaf
clause 62:
OTHER_ZONE → GROUP
=> APPLICABLE

주거지역 FAR leaf
clause 233:
GROUP → OTHER_ZONE
=> NOT_APPLICABLE

상업지역 FAR leaf
clause 234:
OTHER_ZONE → GROUP
=> APPLICABLE
```

시장정비사업 / 주거복합 / 임대주택 등은:

```text
REACTIVATION_DEFERRED
```

로 보존한다.

---

## 25. Applicability Priority Fix

C-13 과정에서 추가로 발견:

기존 `recalculate_applicability()` 순서:

```text
blocked
unknown
required
OTHER_ZONE
```

이면 현재 SITE가 `OTHER_ZONE`이어도 required input이 존재할 때
잘못 `CONDITIONAL`로 재활성화될 수 있었다.

수정 후:

```text
blocked
OTHER_ZONE
unknown
required
applicable
```

즉 용도지역 불일치는 PROJECT/PROCEDURE 추가 입력보다 우선한다.

대표 regression:

```text
clause 206

before fix:
NOT_APPLICABLE → CONDITIONAL

after fix:
NOT_APPLICABLE 유지
```

---

## 26. C-13 Multi-SITE 최종 검증

### BASE SITE

```text
SITE ID: 11680-10300-0012-0000
PNU: 1168010300100120000
Zone: 제3종일반주거지역

Parcel loaded: True
Official area: 121040.4
Spatial area: 120945.65223377591

BCR/FAR:
50 / 250

Rules:
APPLICABLE: 63
NOT_APPLICABLE: 213
CONDITIONAL: 36
UNKNOWN: 2
TOTAL: 314
```

### ALTERNATE synthetic SITE

```text
SITE ID: 11680-10300-0013-0000
Address: SYNTHETIC TEST SITE
PNU: 1168010300100130000
Zone: 일반상업지역

Parcel PNU:
1168010300100130000

Parcel loaded:
False

Parcel bounds:
None

Official area:
1000.0

Spatial area:
None

BCR/FAR:
60 / 800

Rules:
APPLICABLE: 63
NOT_APPLICABLE: 216
CONDITIONAL: 33
UNKNOWN: 2
TOTAL: 314
```

Leakage audit:

```text
Identity changed: True
PNU changed: True
Zone changed: True
Official area changed: True

Parcel PNU matches SITE: True
Parcel still base PNU: False
Same parcel bounds: False
Same spatial area: False

Same numeric: False
Same rule summary: False

Leakage signals: []

Multi-SITE ready: True
Resolution: MULTI_SITE_READY

probe_pass: True
```

C-13 상태:

```text
C-13 STATUS: COMPLETE
MULTI-SITE CORE: READY
```

---

## 27. 최신 전체 회귀 테스트

2026-08-22 기준 아래 테스트 모두 정상 통과.

```text
python -m law_data.rule_evaluation_pipeline_module_test
→ all_pass: True

python -m law_data.zone_base_numeric_resolver_test
→ all_pass: True

python -m site_data.test_site_analysis_service
→ all_pass: True

python -m site_data.test_site_analysis_orchestrator
→ all_pass: True

python test_api_app.py
→ all_pass: True

python -m law_data.multi_site_state_leakage_probe_test
→ probe_pass: True
→ Multi-SITE ready: True
→ Resolution: MULTI_SITE_READY
```

추가로 이전 검증 완료:

```text
python -m site_data.test_real_api_to_site_analysis
python -m site_data.test_land_area_source_reconciliation
python -m site_data.test_site_analysis_land_area_integration
python -m site_data.test_site_analysis_response
python test_api_error_contract.py
python test_api_contract_final_regression.py
```

모두 정상 완료 상태.

---

## 28. 현재 Rule Engine 핵심 상태

Representative BASE scenario:

```text
Total rules: 314

CLEAN baseline:
APPLICABLE: 58
NOT_APPLICABLE: 211
CONDITIONAL: 43
UNKNOWN: 2

PROJECT:
공동주택 = TRUE

PROCEDURE:
도시계획위원회심의 = TRUE

Final:
APPLICABLE: 63
NOT_APPLICABLE: 213
CONDITIONAL: 36
UNKNOWN: 2

Confirmed BCR:
50.0

Confirmed FAR:
250.0
```

General commercial synthetic SITE:

```text
Zone:
일반상업지역

Confirmed BCR:
60.0

Confirmed FAR:
800.0

Final:
APPLICABLE: 63
NOT_APPLICABLE: 216
CONDITIONAL: 33
UNKNOWN: 2
```

---

## 29. 현재 서비스 상태

```text
SITE Analysis Object: READY
Rule Engine: READY
Stateless: True
Multi-SITE core: READY
API Schema: SITE_ANALYSIS_API_V1
FastAPI: READY
```

Health:

```text
GET /health
→ 200 OK
```

Analysis:

```text
POST /v1/site-analysis
→ 200 OK
```

API contract:

```text
200 / 422 / 404 / 502 / 500
```

---

## 30. 현재 프로젝트 핵심 안전 원칙

```text
문자열 존재 ≠ SITE 해당
HTTP 200 ≠ 조회 성공
QUERY_SUCCESS ≠ dataset 의미 검증
dataset 일부 Feature 이름 일치 ≠ dataset 의미
geometry 미확보 ≠ FALSE
조회 실패 ≠ FALSE
HTTP 403 ≠ FALSE
후속 접근 실패 ≠ 기존 정상 evidence 무효
UNKNOWN은 오류가 아니라 정상 상태
TRUE는 실제 근거가 필요
FALSE도 정상조회와 비교 근거가 필요
대표 Point보다 Parcel Polygon intersection 우선
Parcel snapshot은 PNU 일치 시에만 재사용
다른 SITE에 대표 SITE geometry 재사용 금지
코드 의미는 공식 source에서 명칭과 직접 연결 검증 후 사용
PROJECT/PROCEDURE TRUE만으로 numeric 특례 적용 금지
상위 법령 branch 조건을 반드시 검증
branch-local SITE/PROJECT/PROCEDURE predicate를 함께 평가
부모 aggregate numeric + child numeric 중복 적용 금지
상한(ceiling)과 직접 완화(effect)를 구분
중첩(stacking) 허용 여부를 별도 판정
용도지역 불일치는 PROJECT/PROCEDURE 미입력보다 우선
OTHER_ZONE → DIRECT/GROUP만으로 무조건 APPLICABLE 금지
deferred 특례는 추가 조건 검증 전까지 기존 판정 유지
외부 역사 원문 미확인은 UNKNOWN으로 보존
negative search만으로 SITE_HISTORY FALSE 강제 금지
.env는 Git 추적 금지
실제 API key를 저장소에 commit 금지
```

---

## 31. 현재 전체 개발 단계

```text
PHASE 1  기초 SITE / API                       완료
PHASE 2  실제 토지·건축물 데이터               완료
PHASE 3  법령 API / 법규 수집                  완료
PHASE 4  법규 Clause Parser                    핵심 완료
PHASE 5  용도지역 관련성 판정                   완료
PHASE 6  SITE 공간조건 판정                    완료
PHASE 7  SITE_HISTORY 판정                     완료*
PHASE 8  PROJECT 조건 모델                     핵심 구축
PHASE 9  PROCEDURE 조건 모델                   핵심 구축
PHASE 10 특례 적용 가능성 엔진                 핵심 완료 / 일반화 진행
PHASE 11 기본 건폐율·용적률 결정               16개 zone dynamic 완료
PHASE 12 법규 우선순위 / 중첩 규정 처리         핵심 완료 / 확장 예정
PHASE 13 Formula / 수치 계산 엔진               핵심 완료 / 확장 예정
PHASE 14 지구단위계획 결정도서 자동분석         예정
PHASE 15 최종 SITE 규제값 계산                  핵심 완료
PHASE 16 대지분석 결과 객체 통합                완료
PHASE 17 AI 설명 / 보고서 생성                 예정
PHASE 18 서비스 UI / 자동화 API                API 핵심 완료 / UI 예정
PHASE 19 Multi-SITE generalization              핵심 완료
```

`PHASE 7 완료*` 의미:

```text
자동화 가능한 SITE_HISTORY 검증은 완료.
도시지역편입해제구역은
HISTORICAL_SOURCE_PENDING external dependency로 보존.
```

---

## 32. 주요 현재 모듈

Rule / law:

```text
law_data/rule_evaluation_pipeline.py
law_data/rule_condition_registry.py
law_data/zone_base_numeric_resolver.py
law_data/site_analysis_builder.py
law_data/site_identity_resolver.py
law_data/site_spatial_payload_resolver.py
```

Service:

```text
site_data/site_analysis_service.py
site_data/site_analysis_response.py
site_data/site_analysis_orchestrator.py
site_data/site_builder.py
```

API:

```text
api_app.py
```

주요 C-13 테스트:

```text
law_data/multi_site_state_leakage_probe_test.py
law_data/dynamic_base_numeric_context_test.py
law_data/numeric_baseline_source_audit_test.py
law_data/zone_numeric_regulation_source_probe_test.py
law_data/base_zone_numeric_clause_exact_probe_test.py
law_data/seoul_base_zone_numeric_article_probe_test.py
law_data/zone_ratio_map_layer_resolution_test.py
law_data/zone_base_numeric_resolver_test.py
```

API contract tests:

```text
test_api_error_contract.py
test_api_contract_final_regression.py
test_api_app.py
```

---

## 33. 주요 현재 output / snapshot

```text
law_data/output/site_spatial_condition_final_snapshot.json
law_data/output/site_rule_evaluation_site_complete.json
law_data/output/base_numeric_regulation_hierarchy.json
law_data/output/site_parcel_spatial_snapshot.geojson
law_data/output/site_parcel_spatial_recovery.json
law_data/output/zone_numeric_regulation_source_probe.json
law_data/output/base_zone_numeric_clause_exact_probe.json
law_data/output/seoul_base_zone_numeric_article_probe.json
law_data/output/zone_ratio_map_layer_resolution.json
law_data/output/numeric_baseline_source_audit.json
```

대표 zone ratio resolution:

```text
resolution:
SEOUL_ZONE_BASE_NUMERIC_COMPLETE
```

---

## 34. Python package import 정책

`site_data` / `law_data`는 package import 방식을 기본으로 한다.

권장 실행:

```powershell
python -m site_data.<module>
python -m law_data.<module>
```

패키지 내부 import는 가능하면 상대 import를 사용한다.

예:

```python
from .site_data_model import Site
```

직접 script 실행과 `python -m` 실행이 혼재할 경우 import 호환성을 명시적으로 고려한다.

---

## 35. 환경변수 / API Key 정책

실제 API Key는:

```text
.env
```

에만 저장한다.

현재 확인:

```text
git check-ignore -v .env
→ .gitignore:4:.env .env

git ls-files .env
→ no output
```

즉 `.env`는 Git 추적 대상이 아니다.

`.env.example`은 2026-08-22 의도적으로 삭제하였다.

주의:

```text
.env
실제 API Key
credential
secret
token
```

은 절대 Git commit하지 않는다.

---

## 36. 현재 정확한 완료 지점

```text
STEP 17
└─ STEP 17-21
   ├─ C-10 Rule / Numeric Evaluation        COMPLETE
   ├─ C-11 SITE Analysis Object             COMPLETE
   ├─ C-12 Service / FastAPI / Contract     COMPLETE
   └─ C-13 Multi-SITE Generalization        COMPLETE
```

C-13 최종:

```text
Spatial leakage: removed
Numeric leakage: removed
Rule leakage: removed

Leakage signals: []

Multi-SITE ready: True
Resolution: MULTI_SITE_READY
```

---

## 37. 다음 개발 시작 지점

다음 단계는 **C-14 — Multi-SITE Real Parcel Validation & Deferred Rule Generalization**으로 진행한다.

권장 작업 순서:

```text
1. synthetic SITE가 아니라 실제 다른 필지 2~3개를 선정
2. 실제 Building HUB / 토지 API로 SITE 생성
3. 현재 PNU 기반 spatial resolver의 live geometry source 확장
4. 각 SITE의 실제 zone에 따라 dynamic BCR/FAR 검증
5. Rule summary가 zone에 따라 합리적으로 변화하는지 검증
6. REACTIVATION_DEFERRED rule을 유형별로 일반화
7. 주거복합 / 시장정비사업 / 임대주택 / 개발진흥지구 등
   추가 PROJECT / PROCEDURE / SITE 조건을 동적 condition으로 연결
8. 대표 SITE snapshot 의존 output을 점진적으로 runtime source로 교체
```

우선순위 1:

```text
실제 두 번째 SITE를 API로 분석하여
synthetic test가 아닌 real Multi-SITE regression 확보
```

우선순위 2:

```text
REACTIVATION_DEFERRED 규칙의
PROJECT / PROCEDURE / SITE predicate 일반화
```

우선순위 3:

```text
다른 PNU의 Parcel Polygon을 runtime에서 확보하는
live spatial payload source 구축
```

---

## 38. 다음 작업 시작용 핸드오프

```text
AI 대지분석 자동화 시스템 개발을 계속한다.

기준 문서:
PROJECT_STATUS.md

현재 단계:
STEP 17-21-C-13 COMPLETE

현재 대표 SITE:
서울특별시 강남구 개포동 12번지

SITE ID:
11680-10300-0012-0000

PNU:
1168010300100120000

용도지역:
제3종일반주거지역

대표 SITE 분석:
READY

BCR:
50%

FAR:
250%

Rules:
APPLICABLE 63
NOT_APPLICABLE 213
CONDITIONAL 36
UNKNOWN 2

Rule Engine:
READY
Stateless: True

API:
SITE_ANALYSIS_API_V1
FastAPI 정상
API contract freeze READY

C-13 완료:
Spatial leakage 제거
Numeric leakage 제거
Rule leakage 제거

Synthetic alternate SITE:
11680-10300-0013-0000
일반상업지역

BCR/FAR:
60 / 800

Rules:
63 / 216 / 33 / 2

Leakage signals:
[]

Multi-SITE ready:
True

Resolution:
MULTI_SITE_READY

External historical dependency:
도시지역편입해제구역
UNKNOWN / MEDIUM
HISTORICAL_SOURCE_PENDING
분석 차단하지 않음

다음 단계:
C-14
Multi-SITE Real Parcel Validation
+
Deferred Rule Generalization

첫 목표:
실제 다른 PNU를 가진 SITE를 API로 분석하여
real Multi-SITE regression을 확보한다.
```

---

## 39. Git 체크포인트

현재 branch:

```text
checkpoint/c12-fastapi-20260821
```

원격:

```text
origin/checkpoint/c12-fastapi-20260821
```

현재 C-13 체크포인트 권장 commit message:

```text
Complete C-13 multi-site rule and numeric generalization
```

Git 저장 전:

```powershell
git status --short
git diff --stat
```

사용 금지:

```powershell
git add .
git add -A
git add --all
```

이유:

- `.env` 등 비밀정보 안전
- 불필요한 output / 임시파일 자동 stage 방지
- 의도하지 않은 파일 삭제/추가 방지

`.env.example` 삭제는 의도된 변경이다.

`law_data/output/*.json`은 이번 C-13의 source/resolution으로 실제 필요한 파일만 명시적으로 stage한다.

---

# CURRENT CHECKPOINT SUMMARY

```text
C-10: COMPLETE
C-11: COMPLETE
C-12: COMPLETE
C-13: COMPLETE

SITE Analysis:
READY

Rule Engine:
READY

API:
READY

Multi-SITE core:
READY

Next:
C-14 Real Multi-SITE Validation
```
