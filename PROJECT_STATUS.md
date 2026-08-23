# AI 대지분석 자동화 시스템 — PROJECT STATUS

**Last updated: 2026-08-23**

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
12. AI가 Rule Engine의 판정 결과를 설명하고 보고서로 생성

핵심 원칙:

> **Rule Engine이 판정하고, AI는 설명한다.**

---

## 2. 대표 테스트 SITE

- 주소: 서울특별시 강남구 개포동 12번지
- 도로명주소: 서울특별시 강남구 개포로109길 21 (개포동)
- SITE ID: `11680-10300-0012-0000`
- PNU: `1168010300100120000`
- 용도지역: **제3종일반주거지역**
- 대표 좌표: `127.07539280356858, 37.494197498186885`
- CRS: `EPSG:4326`

대표 SITE Parcel:

```text
dataset: LP_PA_CBND_BUBUN
provider: MapPlan snapshot
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

대표 SITE 확정값:

```text
BCR: 50.0
FAR: 250.0
Rules: APPLICABLE 63 / NOT_APPLICABLE 213 / CONDITIONAL 36 / UNKNOWN 2
TOTAL: 314
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

법규 판정:

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

## 4. STEP 1 ~ STEP 16

완료:

- 주소 기반 SITE 생성
- SITE ID / PNU 구조화
- 시군구 / 법정동 / 본번 / 부번 구조화
- `.env` 기반 API Key 관리
- SITE Builder 구축
- 실제 건축물 API 연결
- 실제 토지정보 연결
- 외부 API 응답을 내부 SITE 데이터 구조로 변환

대표 SITE Building HUB:

```text
전체 데이터 수: 34
현재 받은 건축물 수: 34
resultCode: 00
resultMsg: NORMAL SERVICE
```

---

## 5. STEP 17 법규 자동분석

주요 분석 법규:

- 국토의 계획 및 이용에 관한 법률
- 국토의 계획 및 이용에 관한 법률 시행령
- 서울특별시 도시계획 조례
- 관련 자치구 조례 / 행정규정

Clause parser:

```text
조 → 항 → 호 → 목 → 세부 clause
총 clause: 314
C-8 parser: ALL PASS
```

---

## 6. 조건 모델

```text
SITE
SITE_HISTORY
PROJECT
PROCEDURE
```

주요 SITE 조건:

```text
지구단위계획
개발진흥지구
개발밀도관리구역
자연경관지구
취락지구
수산자원보호구역
입체복합구역
도시혁신구역
복합용도구역
산업단지
자연공원
방재지구
서울도심
```

SITE_HISTORY:

```text
학교이적지
도시지역편입해제구역
```

PROJECT:

```text
공개공지
공공시설제공
공공주택
공동주택
기부채납
대학
사회복지시설
임대주택
종합의료시설
주거복합
한옥
관광숙박시설
감염병대응필요시설
```

PROCEDURE:

```text
도시계획위원회심의
시장정비사업심의
```

---

## 7. SITE 공간조건 / HISTORY 상태

대표 SITE C-9 결과:

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

외부 역사자료 dependency:

```text
도시지역편입해제구역
state: UNKNOWN
confidence: MEDIUM
automation_state: HISTORICAL_SOURCE_PENDING
blocking_site_stage: False
```

---

## 8. Reusable Rule Evaluation Pipeline

모듈:

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

대표 regression:

```text
Baseline: 58 / 211 / 43 / 2
Final:    63 / 213 / 36 / 2
Numeric active: 11
Numeric excluded: 3
Numeric retained: 8
Direct relaxation: 0
resolution: BASE_VALUES_RETAINED
BCR/FAR: 50 / 250
all_pass: True
```

---

## 9. Numeric Semantic / Guard

```text
Numeric clauses: 124
Final numeric candidates: 28
```

검증 완료 핵심:

```text
clause 4   → 상위 branch 불일치 → direct BCR relaxation 금지
clause 189 → 방재지구 FALSE → FAR 300 후보 제거
clause 205 → 관광숙박시설 / 서울도심 / 조례 제48조 branch 검증 → direct effect 금지
clause 250 → stacking ceiling → current SITE direct FAR effect 아님
```

---

## 10. STEP 17-21-C-11 SITE Analysis Object

핵심 API:

```python
build_site_analysis()
```

통합:

- SITE identity
- PNU / 주소
- 대표 좌표
- Parcel geometry
- 공식/공간 토지면적
- 용도지역
- BCR/FAR
- Rule summary
- remaining PROJECT/PROCEDURE
- external dependency
- debug/evidence

상태:

```text
Analysis status: READY
```

---

## 11. STEP 17-21-C-12 Service / FastAPI

App:

```text
api_app.py
```

Endpoints:

```text
GET /health
POST /v1/site-analysis
```

Schema:

```text
SITE_ANALYSIS_API_V1
```

HTTP contract:

```text
200 / 422 / 404 / 502 / 500
```

FastAPI / API contract:

```text
READY
```

---

## 12. STEP 17-21-C-13 Multi-SITE Generalization

C-13에서 단일 대표 SITE 의존성을 다음 세 축에서 제거하였다.

```text
Spatial
Numeric
Rule applicability
```

16개 서울시 주요 용도지역 base numeric 해결:

```text
Resolved: 16
Unresolved: 0
Ambiguous: 0
resolution: SEOUL_ZONE_BASE_NUMERIC_COMPLETE
```

대표:

```text
제3종일반주거지역 → 50 / 250
제1종일반주거지역 → 60 / 150
일반상업지역       → 60 / 800
자연녹지지역       → 20 / 50
준주거지역         → 60 / 400
준공업지역         → 60 / 400
```

Zone transition safety:

```text
DIRECT/GROUP → OTHER_ZONE
=> NOT_APPLICABLE

OTHER_ZONE → DIRECT/GROUP
=> 무조건 APPLICABLE 금지
```

Applicability priority:

```text
blocked
OTHER_ZONE
unknown
required
applicable
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

## 13. STEP 17-21-C-14 Real Multi-SITE Live Spatial Resolution

완료 단계:

```text
C-14-1 Real Multi-SITE Validation
C-14-2 Live Parcel Geometry Source
C-14-3 Dual-Source Parcel Regression
C-14-4 Coordinate Leakage Guard
C-14-5 Dual-Source Coordinate Regression
C-14-6 Final Multi-SITE Regression
```

최종:

```text
C-14 status: COMPLETE
Multi-SITE spatial source isolation: PASS
Representative coordinate isolation: PASS
Final regression: ALL PASS
```

---

## 14. 실제 두 번째 SITE

```text
주소: 서울특별시 강남구 개포동 13번지
도로명주소: 서울특별시 강남구 개포로109길 74 (개포동)
SITE ID: 11680-10300-0013-0000
PNU: 1168010300100130000
용도지역: 제1종일반주거지역
토지면적: 13000.5
지목: 학교용지
건축물 수: 6
```

Building HUB:

```text
HTTP 200
resultCode: 00
resultMsg: NORMAL SERVICE
```

최종 분석:

```text
Analysis status: READY
BCR: 60.0
FAR: 150.0
Rules: APPLICABLE 63 / NOT_APPLICABLE 215 / CONDITIONAL 34 / UNKNOWN 2
TOTAL: 314
```

---

## 15. Live Parcel Geometry Provider

모듈:

```text
law_data/parcel_geometry_provider.py
law_data/live_parcel_geometry_provider_test.py
```

source:

```text
provider: VWorld
dataset: LP_PA_CBND_BUBUN
query_mode: POINT
crs: EPSG:4326
```

개포동 13번지:

```text
geometry: MultiPolygon
geometry_loaded: True
resolution: PNU_POLYGON_VERIFIED
feature_pnu: 1168010300100130000
query: HTTP 200 / VWorld OK / QUERY_SUCCESS
bounds:
[127.07724437760275, 37.49597502060932, 127.07884059043805, 37.497397366483824]
```

---

## 16. Dual Parcel Source Policy

```text
현재 SITE PNU == snapshot PNU
→ 검증된 MapPlan snapshot 사용

현재 SITE PNU != snapshot PNU
→ snapshot geometry 사용 금지
→ VWorld live provider 실행
→ PNU 직접 일치 Polygon/MultiPolygon만 사용

live provider 실패
→ geometry_loaded = False
```

대표 SITE:

```text
provider: MapPlan
snapshot match: True
geometry: Polygon
loaded: True
```

개포동 13번지:

```text
provider: VWorld
snapshot match: False
geometry: MultiPolygon
loaded: True
CRS: EPSG:4326
```

회귀:

```text
different PNU: True
different provider: True
different bounds: True
all_pass: True
```

---

## 17. Representative Coordinate Leakage Guard

발견된 문제:

```text
개포동 13번지에 개포동 12번지 좌표가 상속됨
```

해결 정책:

```text
base coordinate
→ current resolved PNU == base PNU일 때만 재사용

historical parcel probe point
→ current resolved PNU == probe PNU일 때만 재사용

둘 다 불일치
→ 기존 coordinate 사용 금지
```

---

## 18. Representative Coordinate Promotion

개포동 13번지 live coordinate:

```text
x: 127.07804416954306
y: 37.49668484241573
crs: EPSG:4326
source: VWORLD_ADDRESS_SEARCH
status: CONFIRMED
```

Dual coordinate regression:

```text
BASE: 127.07539280356858 / 37.494197498186885
LIVE: 127.07804416954306 / 37.49668484241573
coordinate x differs: True
coordinate y differs: True
live coordinate matches parcel coordinate: True
live not base coordinate: True
all_pass: True
```

---

## 19. Geometry Area 정책

```text
MapPlan snapshot:
native projected coordinate area 유지

VWorld live geometry:
EPSG:4326
→ bounds 계산 가능
→ degree²를 parcel area로 사용 금지
→ area status = NOT_CALCULATED_FOR_LIVE_GEOMETRY
```

---

## 20. Multi-SITE 최종 상태

Synthetic leakage probe:

```text
Identity changed: True
PNU changed: True
Zone changed: True
Official area changed: True
Parcel PNU matches SITE: True
Parcel still BASE PNU: False
Same parcel bounds: False
Same spatial area: False
Same numeric: False
Same rule summary: False
Leakage signals: []
Multi-SITE ready: True
Resolution: MULTI_SITE_READY
probe_pass: True
```

---

## 21. C-14 Final Regression

실행 완료:

```text
python -m site_data.test_site_analysis_service
python -m site_data.test_site_analysis_orchestrator
python test_api_app.py
python -m law_data.rule_evaluation_pipeline_module_test
python -m law_data.multi_site_state_leakage_probe_test
python -m law_data.dual_source_parcel_regression_test
python -m law_data.dual_source_coordinate_regression_test
python -m site_data.test_real_multi_site_analysis
```

결과:

```text
SITE analysis: all_pass True
Orchestrator: all_pass True
FastAPI: all_pass True
Rule pipeline: all_pass True
Multi-SITE leakage: probe_pass True
Dual Parcel source: all_pass True
Dual Coordinate source: all_pass True
Real Multi-SITE: all_pass True
```

---

## 22. 현재 서비스 상태

```text
SITE Analysis Object: READY
Rule Engine: READY
Stateless: True
Multi-SITE core: READY
Live Parcel Geometry: READY
Coordinate source isolation: READY
API Schema: SITE_ANALYSIS_API_V1
FastAPI: READY
```

---

## 23. 핵심 안전 원칙

```text
문자열 존재 ≠ SITE 해당
HTTP 200 ≠ 조회 성공
QUERY_SUCCESS ≠ dataset 의미 검증
geometry 미확보 ≠ FALSE
조회 실패 ≠ FALSE
UNKNOWN은 오류가 아니라 정상 상태
대표 Point보다 Parcel Polygon intersection 우선

Parcel snapshot은 PNU 일치 시에만 재사용
다른 SITE에 대표 SITE geometry 재사용 금지
snapshot mismatch는 live fallback 조건
live Polygon은 Feature PNU 직접 검증 후 사용
coordinate source에도 PNU guard 적용
EPSG:4326 geometry에서 parcel 면적 임의 계산 금지

PROJECT/PROCEDURE TRUE만으로 numeric 특례 적용 금지
상위 법령 branch 조건 검증 필수
부모 aggregate + child numeric 중복 적용 금지
ceiling과 direct effect 구분
OTHER_ZONE → DIRECT/GROUP만으로 무조건 APPLICABLE 금지
deferred 특례는 추가 조건 검증 전 기존 판정 유지

SITE_HISTORY 원문 미확인은 UNKNOWN 보존
negative search만으로 FALSE 강제 금지

.env는 Git 추적 금지
실제 API key commit 금지
```

---

## 24. 주요 모듈

```text
law_data/rule_evaluation_pipeline.py
law_data/rule_condition_registry.py
law_data/zone_base_numeric_resolver.py
law_data/site_analysis_builder.py
law_data/site_identity_resolver.py
law_data/site_spatial_payload_resolver.py
law_data/parcel_geometry_provider.py

site_data/site_analysis_service.py
site_data/site_analysis_response.py
site_data/site_analysis_orchestrator.py
site_data/site_builder.py

api_app.py
```

C-14 regression:

```text
law_data/dual_source_parcel_regression_test.py
law_data/dual_source_coordinate_regression_test.py
law_data/live_parcel_geometry_provider_test.py
site_data/test_real_multi_site_analysis.py
```

---

## 25. 환경변수 / Git 정책

실제 API Key:

```text
.env
```

`.env`는 Git 추적 대상이 아니다.

`.env.example`은 2026-08-22 의도적으로 삭제하였다.

금지:

```text
git add .
git add -A
git add --all
```

항상 필요한 파일만 명시적으로 stage한다.

---

## 26. STEP 17-21-C-15 — Runtime SITE Spatial Condition Integration

### 목표

기존 C-9 대표 SITE 공간조건 snapshot을 모든 SITE에 재사용하지 않고, 현재 분석 SITE의 Parcel geometry를 이용해 SITE 공간조건을 runtime에서 직접 판정하여 Rule Engine에 연결한다.

첫 runtime 일반화 대상:

```text
지구단위계획
```

공식 VWorld dataset:

```text
LT_C_UPISUQ161
```

### C-15-1 — Runtime Spatial Condition Evaluator

신규 모듈:

```text
law_data/spatial_condition_evaluator.py
```

주요 API:

```python
resolve_site_spatial_condition(
    condition_name=...,
    site=...,
    parcel=...,
)
```

현재 지원:

```text
지구단위계획
```

핵심 안전 정책:

```text
조회 실패 ≠ FALSE
geometry 미확보 ≠ FALSE
CRS 불일치 상태에서 강제 intersection 금지
runtime TRUE / FALSE / UNKNOWN 모두 유효한 현재 SITE 결과
EPSG:4326 degree² 면적을 법정 면적값으로 사용하지 않음
```

현재는 면적비가 아니라 실제 geometry의 `intersects` 여부를 핵심 공간 판정 근거로 사용한다.

### C-15-2 — 실제 LIVE SITE 지구단위계획 판정

대상:

```text
서울특별시 강남구 개포동 13번지
SITE ID: 11680-10300-0013-0000
PNU: 1168010300100130000
```

Parcel:

```text
Provider: VWorld
Dataset: LP_PA_CBND_BUBUN
Geometry: MultiPolygon
CRS: EPSG:4326
PNU direct verified: True
```

지구단위계획 runtime query:

```text
Dataset: LT_C_UPISUQ161
HTTP: 200
VWorld: OK
Classification: QUERY_SUCCESS
Feature: LT_C_UPISUQ161.1154
District: 대치택지개발지구
Intersects: True
```

최종:

```text
State: TRUE
Confidence: HIGH
Resolution: PARCEL_INTERSECTS_DISTRICT_UNIT_PLAN
Geometry verified: True
```

Regression:

```text
python -m law_data.district_unit_plan_runtime_live_test
→ all_pass: True
```

### C-15-3 — BASE/LIVE Compatible Geometry Strategy

C-15에서 다음 아키텍처 원칙을 확정하였다.

```text
Analysis Primary Parcel Source
≠
Spatial Condition Evaluation Geometry Source
```

BASE SITE의 primary Parcel은 기존 MapPlan snapshot을 보존한다.

```text
PNU: 1168010300100120000
Primary provider: MapPlan
Geometry: Polygon
CRS: None
```

MapPlan CRS를 임의 추정하지 않는다. 지구단위계획 평가 시 동일 PNU의 VWorld Parcel을 별도로 확보한다.

```text
Provider: VWorld
Dataset: LP_PA_CBND_BUBUN
Resolution: PNU_POLYGON_VERIFIED
CRS: EPSG:4326
Mode: LIVE_COMPATIBLE_FALLBACK
```

LIVE SITE:

```text
PNU: 1168010300100130000
Primary provider: VWorld
Geometry: MultiPolygon
CRS: EPSG:4326
Evaluation mode: PRIMARY_PARCEL
```

Dual-SITE 결과:

```text
BASE: TRUE / HIGH / 대치택지개발지구
LIVE: TRUE / HIGH / 대치택지개발지구
BASE evaluation mode: LIVE_COMPATIBLE_FALLBACK
LIVE evaluation mode: PRIMARY_PARCEL
```

Regression:

```text
python -m law_data.district_unit_plan_dual_site_regression_test
→ all_pass: True
```

### C-15-4 — Runtime SITE Condition → Rule Engine Overlay

`evaluate_site_rules()`에 신규 context를 추가하였다.

```python
site_condition_context
```

신규 overlay:

```text
overlay_runtime_site_conditions()
```

우선순위:

```text
runtime SITE condition
>
기존 SITE registry / snapshot
```

중요 정책:

```text
TRUE만 overlay하지 않음
FALSE도 반드시 overlay
UNKNOWN도 현재 SITE runtime 결과이므로 overlay
```

검증:

```text
BASE registry FALSE + runtime TRUE → final TRUE
BASE registry TRUE + runtime FALSE → final FALSE
```

314개 Rule Engine condition까지 TRUE/FALSE propagation을 확인하였다.

```text
runtime TRUE → 관련 지구단위계획 condition TRUE
runtime FALSE → 관련 지구단위계획 condition FALSE
TRUE scenario rule count: 314
FALSE scenario rule count: 314
```

Regression:

```text
python -m law_data.runtime_site_condition_overlay_regression_test
→ all_pass: True
```

### C-15-5 — SITE Analysis Builder 자동 연결

실서비스 분석 경로:

```text
build_site_analysis()
    ↓
resolve_site_identity()
    ↓
resolve_site_spatial_payload()
    ↓
resolve_site_spatial_condition()
    ↓
runtime_conditions
    ↓
site_condition_context
    ↓
evaluate_site_rules()
```

Final SITE object:

```python
analysis["site"]["runtime_conditions"]["지구단위계획"]
```

대표 확인 결과:

```text
state: TRUE
confidence: HIGH
resolution: PARCEL_INTERSECTS_DISTRICT_UNIT_PLAN
source: VWorld / LT_C_UPISUQ161 / EPSG:4326
```

기존 BASE regression:

```text
Analysis: READY
BCR/FAR: 50 / 250
Rules: 63 / 213 / 36 / 2
all_pass: True
```

실제 LIVE SITE regression:

```text
Zone: 제1종일반주거지역
BCR/FAR: 60 / 150
Rules: 63 / 215 / 34 / 2
Parcel: VWorld / MultiPolygon / EPSG:4326
all_pass: True
```

참고:

```text
analysis.debug.rule_engine.site_registry 경로는 현재 외부 debug object에 노출되지 않음.
이는 실패가 아니며, C-15-4에서 evaluate_site_rules() 반환 registry와 314개 rule condition propagation을 직접 검증함.
향후 observability 개선 시 debug 노출 가능.
```

C-15 상태:

```text
C-15 STATUS: COMPLETE
Runtime Parcel: READY
Runtime SITE Spatial Condition: READY
Runtime SITE Condition → Rule Engine: READY
```

---

## 27. C-15 최종 회귀 테스트

2026-08-23 기준:

```text
python -m law_data.district_unit_plan_runtime_live_test
→ all_pass: True

python -m law_data.district_unit_plan_dual_site_regression_test
→ all_pass: True

python -m law_data.runtime_site_condition_overlay_regression_test
→ all_pass: True

python -m site_data.test_site_analysis_service
→ all_pass: True

python -m site_data.test_real_multi_site_analysis
→ all_pass: True
```

BASE 최종:

```text
SITE ID: 11680-10300-0012-0000
PNU: 1168010300100120000
Zone: 제3종일반주거지역
BCR/FAR: 50 / 250
Rules: 63 / 213 / 36 / 2
지구단위계획: TRUE / HIGH
Evaluation mode: LIVE_COMPATIBLE_FALLBACK
District: 대치택지개발지구
```

LIVE 최종:

```text
SITE ID: 11680-10300-0013-0000
PNU: 1168010300100130000
Zone: 제1종일반주거지역
BCR/FAR: 60 / 150
Rules: 63 / 215 / 34 / 2
지구단위계획: TRUE / HIGH
Evaluation mode: PRIMARY_PARCEL
District: 대치택지개발지구
```

---

## 28. 현재 정확한 완료 지점

```text
STEP 17
└─ STEP 17-21
   ├─ C-10 Rule / Numeric Evaluation              COMPLETE
   ├─ C-11 SITE Analysis Object                   COMPLETE
   ├─ C-12 Service / FastAPI / Contract           COMPLETE
   ├─ C-13 Multi-SITE Generalization              COMPLETE
   ├─ C-14 Real Multi-SITE Live Spatial           COMPLETE
   └─ C-15 Runtime SITE Spatial Condition         COMPLETE
```

현재 핵심 상태:

```text
SITE Analysis: READY
Rule Engine: READY
API: READY
Multi-SITE core: READY
Live Parcel Geometry: READY
Coordinate Isolation: READY
Runtime District Unit Plan Evaluation: READY
Runtime SITE Condition → Rule Engine: READY
```

---

## 29. 다음 개발 시작 지점 — C-16

다음 단계:

```text
STEP 17-21-C-16
Runtime SITE Condition Generalization
```

현재 runtime 자동화 완료:

```text
지구단위계획
```

다음 일반화 후보:

```text
개발진흥지구
자연경관지구
취락지구
수산자원보호구역
산업단지
자연공원
개발밀도관리구역
방재지구
기타 C-9 SITE condition
```

권장 순서:

```text
1. C-9 registry condition 전체 목록과 runtime source 후보 매핑
2. 공식 VWorld/UPIS dataset 의미가 이미 검증된 condition부터 선정
3. spatial_condition_evaluator를 condition별 adapter/registry 구조로 일반화
4. 현재 PNU Parcel Polygon intersection을 우선 근거로 사용
5. TRUE/FALSE/UNKNOWN 안전 정책 유지
6. runtime condition을 site_condition_context에 자동 추가
7. 대표 SITE snapshot fallback 의존도를 점진적으로 축소
8. BASE + LIVE + 추가 실제 SITE regression 확대
```

C-16 첫 목표:

> **공식 spatial dataset/source가 이미 검증된 C-9 SITE condition을 선정하여, 지구단위계획과 동일한 runtime evaluator 구조로 일반화한다.**

---

## 30. C-16 시작 시 유지할 안전 원칙

```text
조회 실패 ≠ FALSE
geometry 미확보 ≠ FALSE
HTTP 403 ≠ FALSE
HTTP 200 ≠ 의미 검증 완료
QUERY_SUCCESS ≠ dataset 의미 검증 완료
TRUE/FALSE 모두 실제 runtime evidence 필요
Parcel Polygon intersection 우선
대표 SITE snapshot을 다른 PNU에 재사용 금지
CRS를 임의 추정하지 않음
runtime FALSE도 기존 TRUE registry를 override
runtime UNKNOWN도 현재 SITE 결과로 보존
Analysis Primary Parcel Source와 Evaluation Geometry Source는 분리 가능
PNU가 다른 geometry의 fallback 사용 금지
```

---

## 31. C-15 Git 체크포인트

현재 branch:

```text
checkpoint/c12-fastapi-20260821
```

직전 원격 체크포인트:

```text
a14ec80
Checkpoint C-14 multi-site live spatial resolution
```

C-15 stage 대상:

```text
PROJECT_STATUS.md
law_data/spatial_condition_evaluator.py
law_data/district_unit_plan_runtime_live_test.py
law_data/district_unit_plan_dual_site_regression_test.py
law_data/runtime_site_condition_overlay_regression_test.py
law_data/rule_evaluation_pipeline.py
law_data/site_analysis_builder.py
```

이번 C-15에서 제외:

```text
law_data/output/seoul_base_zone_numeric_article_probe.json
```

권장 commit:

```text
Checkpoint C-15 runtime spatial condition integration
```

저장 명령:

```powershell
git add PROJECT_STATUS.md
git status
git diff --cached --stat

git commit -m "Checkpoint C-15 runtime spatial condition integration"
git push

git status
git log -1 --oneline
```

`git add .`, `git add -A`, `git add --all`은 사용하지 않는다.

---

## 32. 새 채팅 시작용 핸드오프

```text
AI 대지분석 자동화 시스템 개발을 계속한다.

기준 문서:
PROJECT_STATUS.md

현재 branch:
checkpoint/c12-fastapi-20260821

현재 완료 단계:
STEP 17-21-C-15 COMPLETE

현재 시스템 상태:
SITE Analysis READY
Rule Engine READY
FastAPI READY
Multi-SITE core READY
Live Parcel Geometry READY
Runtime SITE Spatial Condition READY

대표 SITE:
서울특별시 강남구 개포동 12번지
SITE ID: 11680-10300-0012-0000
PNU: 1168010300100120000
Zone: 제3종일반주거지역
BCR/FAR: 50 / 250
Rules: 63 / 213 / 36 / 2

실제 두 번째 SITE:
서울특별시 강남구 개포동 13번지
SITE ID: 11680-10300-0013-0000
PNU: 1168010300100130000
Zone: 제1종일반주거지역
BCR/FAR: 60 / 150
Rules: 63 / 215 / 34 / 2

C-14 완료:
VWorld LP_PA_CBND_BUBUN live Parcel provider 구축
PNU 직접 검증
MultiPolygon / EPSG:4326
대표좌표 확보
BASE/LIVE coordinate leakage 제거

C-15 완료:
신규 모듈 law_data/spatial_condition_evaluator.py
첫 runtime SITE condition: 지구단위계획
공식 dataset: LT_C_UPISUQ161

BASE runtime:
TRUE / HIGH
대치택지개발지구
Evaluation mode: LIVE_COMPATIBLE_FALLBACK

LIVE runtime:
TRUE / HIGH
대치택지개발지구
Evaluation mode: PRIMARY_PARCEL

중요 아키텍처:
Analysis Primary Parcel Source
≠
Spatial Condition Evaluation Geometry Source

Runtime SITE condition이:
site_condition_context
→ Rule Engine site_registry overlay
→ 314개 rule condition
까지 연결됨.

runtime TRUE propagation 검증 완료
runtime FALSE override 검증 완료
runtime UNKNOWN도 기존 snapshot보다 우선하도록 설계

주요 regression 모두 all_pass True.

현재 제외된 untracked output:
law_data/output/seoul_base_zone_numeric_article_probe.json
C-15 commit에 포함하지 않음.

다음 단계:
STEP 17-21-C-16
Runtime SITE Condition Generalization

첫 목표:
기존 C-9 SITE condition 중 공식 spatial dataset/source가 이미 검증된 조건을 선정하여 지구단위계획과 동일한 runtime evaluator 구조로 일반화한다.

우선 후보:
개발진흥지구
자연경관지구
취락지구
수산자원보호구역
산업단지
자연공원
개발밀도관리구역
방재지구

안전 원칙:
조회 실패 ≠ FALSE
geometry 미확보 ≠ FALSE
HTTP 403 ≠ FALSE
TRUE/FALSE 모두 실제 runtime evidence 필요
Parcel Polygon intersection 우선
대표 SITE snapshot을 다른 PNU에 재사용 금지
CRS를 임의 추정하지 않음
runtime FALSE도 기존 TRUE registry를 override
```

---

# CURRENT CHECKPOINT SUMMARY

```text
C-10 COMPLETE
C-11 COMPLETE
C-12 COMPLETE
C-13 COMPLETE
C-14 COMPLETE
C-15 COMPLETE

SITE Analysis READY
Rule Engine READY
API READY
Multi-SITE READY
Live Parcel Geometry READY
Coordinate Isolation READY
Runtime District Unit Plan Evaluation READY
Runtime SITE Condition → Rule Engine READY

Next:
C-16 Runtime SITE Condition Generalization
```
