# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-08-24

## 1. 현재 단계

현재 STEP 17 진행 중이며, 최근 작업 구간은 Runtime Spatial Condition 일반화 및 방재지구 연계 검증이다.

현재 체크포인트:

- STEP 17-21-C-16-5 Runtime Spatial Condition Generalization
- STEP 17-21-C-16-7 Disaster Prevention District
- Multi-SITE / Runtime Spatial Condition / FastAPI End-to-End 회귀 검증

현재 상태: PASS

---

## 2. Runtime Spatial Condition 현재 지원 목록

현재 `spatial_condition_evaluator` registry에서 지원하는 SITE runtime spatial condition은 다음 4종이다.

1. 지구단위계획
   - Dataset: `LT_C_UPISUQ161`
   - Parcel geometry 기반 intersection
   - BASE / LIVE 모두 TRUE 검증 완료

2. 개발진흥지구
   - Dataset: `LT_C_UQ129`
   - FALSE / TRUE positive case 검증 완료
   - Positive:
     - 서울특별시 동대문구 제기동 1082
     - PNU: `1123010300110820000`
     - Feature: `LT_C_UQ129.2952`
     - 특정개발진흥지구

3. 취락지구
   - Dataset: `LT_C_UQ128`
   - FALSE / TRUE positive case 검증 완료
   - Positive:
     - 서울특별시 구로구 천왕동 10-39
     - PNU: `1153011100100100039`
     - Feature: `LT_C_UQ128.20689`
     - 집단취락지구

4. 방재지구
   - Dataset: `LT_C_UQ125`
   - FALSE / TRUE positive case 검증 완료
   - Positive:
     - 전남광주통합특별시 목포시 죽교동 580-6
     - PNU: `1211015700105800006`
     - Feature: `LT_C_UQ125.22`
     - 방재지구

---

## 3. Parcel Geometry 정책

현재 runtime spatial condition 판정은 POINT 포함 여부만으로 TRUE를 확정하지 않는다.

필수 검증:

- 현재 SITE PNU 확보
- `LP_PA_CBND_BUBUN` Parcel Polygon / MultiPolygon 확보
- Feature PNU와 target PNU 직접 일치
- CRS `EPSG:4326`
- 대상 공간 dataset geometry 확보
- Parcel geometry와 대상 geometry 실제 `intersects()` 확인

다른 PNU에 대표 SITE snapshot 재사용 금지.

대표 snapshot PNU가 target PNU와 불일치하면 VWorld live Parcel provider fallback을 사용한다.

---

## 4. 대표 BASE / LIVE SITE

### BASE

- SITE ID: `11680-10300-0012-0000`
- 주소: 서울특별시 강남구 개포동 12번지
- PNU: `1168010300100120000`
- 용도지역: 제3종일반주거지역
- BCR: 50.0
- FAR: 250.0

Runtime conditions:

- 지구단위계획: TRUE / HIGH
- 개발진흥지구: FALSE / HIGH
- 취락지구: FALSE / HIGH
- 방재지구: FALSE / HIGH

Rule summary:

- total: 314
- applicable: 62
- not_applicable: 214
- conditional: 36
- unknown: 2

### LIVE

- SITE ID: `11680-10300-0013-0000`
- 주소: 서울특별시 강남구 개포동 13번지
- PNU: `1168010300100130000`
- 용도지역: 제1종일반주거지역
- BCR: 60.0
- FAR: 150.0

Runtime conditions:

- 지구단위계획: TRUE / HIGH
- 개발진흥지구: FALSE / HIGH
- 취락지구: FALSE / HIGH
- 방재지구: FALSE / HIGH

Rule summary:

- total: 314
- applicable: 62
- not_applicable: 216
- conditional: 34
- unknown: 2

---

## 5. 방재지구 C-16-7 완료 상태

### C-16-7-A Dataset Probe

`LT_C_UQ125`에 대해 초기 후보 주소를 조회했으나 positive candidate를 확보하지 못했다.

결론:
- 초기 단계에서는 runtime condition 등록 보류

### C-16-7-B BBOX Discovery

목포 지역 BBOX 탐색에서 positive feature 발견.

- Feature ID: `LT_C_UQ125.22`
- Geometry: MultiPolygon
- uname: 방재지구
- Representative point:
  - x: `126.37369914302997`
  - y: `34.801980483931146`

### C-16-7-C Positive Parcel Regression

Reverse address + address search를 조합하여 PNU 확보.

- Address: 전남광주통합특별시 목포시 죽교동 580-6
- PNU: `1211015700105800006`
- Parcel dataset: `LP_PA_CBND_BUBUN`
- Parcel geometry: MultiPolygon
- Strict PNU verified: True
- District feature: `LT_C_UQ125.22`
- Parcel intersects district: True
- all_pass: True

### Runtime Regression

BASE / LIVE / POSITIVE 3개 PNU에 대해 검증 완료.

- BASE: FALSE / HIGH
- LIVE: FALSE / HIGH
- POSITIVE: TRUE / HIGH
- geometry_verified: True
- all_pass: True

Resolution:

- FALSE: `NO_DISASTER_PREVENTION_DISTRICT_FEATURE`
- TRUE: `PARCEL_INTERSECTS_DISASTER_PREVENTION_DISTRICT`

---

## 6. 방재지구 Rule Propagation / Clause 189

서울특별시 도시계획 조례 clause 189 `용적률의 완화`는 상위 근거:

- 국토계획법 시행령 제85조제5항

필수 조건:

1. 방재지구 — SITE
2. 재해예방시설 — PROJECT

현재 Rule Engine 연계 결과:

### 방재지구 TRUE + 재해예방시설 UNSET

- clause 189 applicability: `CONDITIONAL`
- 방재지구: TRUE / HIGH / RUNTIME_SPATIAL_CONDITION
- 재해예방시설: UNSET / PROJECT_INPUT_REQUIRED
- numeric status: `POTENTIAL_CONDITIONAL`
- 현재 BCR/FAR에는 미반영

### 방재지구 FALSE

- clause 189 applicability: `NOT_APPLICABLE`
- 방재지구: FALSE / HIGH
- numeric status: `INACTIVE`

Rule propagation regression:
- all_pass: True

---

## 7. Clause 189 Static Numeric Guard Leakage 제거

기존 문제:

방재지구 TRUE + 재해예방시설 TRUE로 clause 189가 실제 APPLICABLE이어도,
legacy `disaster_prevention_district_resolution.json`의 static guard가
`NOT_APPLICABLE` 상태를 유지하여 runtime 결과를 차단했다.

재현 결과:

- clause 189: APPLICABLE
- current_numeric_effect: ACTIVE_CANDIDATE
- static numeric guard에서 차단
- direct relaxation count: 0
- BCR/FAR: 50 / 250

수정 후:

### A. 방재지구 FALSE + 재해예방시설 TRUE

- applicability: NOT_APPLICABLE
- numeric: INACTIVE
- direct relaxation: 0
- BCR/FAR: 50 / 250

### B. 방재지구 TRUE + 재해예방시설 UNSET

- applicability: CONDITIONAL
- numeric: POTENTIAL_CONDITIONAL
- direct relaxation: 0
- BCR/FAR: 50 / 250

### C. 방재지구 TRUE + 재해예방시설 TRUE

- applicability: APPLICABLE
- numeric: ACTIVE_CANDIDATE
- clause 189 retained: True
- direct relaxation count: 1
- numeric resolution: `RECALC_REQUIRED`
- BCR/FAR: pending (`None`, `None`)

Regression:

- `STATIC_NUMERIC_GUARD_LEAKAGE_REMOVED: True`
- all_pass: True

중요:
현재 clause 189가 완전 충족되면 숫자를 임의 확정하지 않고 `RECALC_REQUIRED`로 넘긴다.

---

## 8. Runtime Spatial Condition Generalization

`build_site_analysis()`는 현재 특정 condition을 개별 하드코딩하지 않고,
`get_supported_spatial_conditions()` 결과 전체를 자동 실행한다.

지원 condition:

```text
['지구단위계획', '개발진흥지구', '취락지구', '방재지구']
```

검증:

- BASE runtime keys == supported
- LIVE runtime keys == supported
- 모든 dataset / confidence / state 검증
- BASE rule summary 일치
- LIVE rule summary 일치
- all_pass: True

---

## 9. Multi-SITE End-to-End

`site_data/test_real_multi_site_analysis.py`

실제 Building HUB API에서 개포동 13번지 조회 후:

Building HUB
→ `create_site()`
→ VWorld 토지정보
→ `analyze_site_object()`
→ PNU-aware Parcel resolver
→ Runtime spatial conditions
→ Rule Engine overlay
→ Final SITE Analysis

검증 결과:

- API success: True
- PNU target 일치
- 대표 BASE PNU 재사용 없음
- VWorld live Parcel geometry 확보
- `LP_PA_CBND_BUBUN`
- strict PNU verified
- runtime condition 4종 존재
- zone / BCR / FAR 정상
- rules 314
- expected rule summary 일치
- all_pass: True

---

## 10. FastAPI End-to-End

`test_api_app.py`

최종 재실행 결과:

- Health HTTP: 200
- Analysis HTTP: 200
- Schema: `SITE_ANALYSIS_API_V1`
- Status: READY
- SITE ID: `11680-10300-0012-0000`
- PNU: `1168010300100120000`
- BCR: 50.0
- FAR: 250.0
- Building count: 34
- Rule summary:
  - total 314
  - applicable 62
  - not_applicable 214
  - conditional 36
  - unknown 2
- all_pass: True

직전 한 차례 발생한:

`502 / 건축HUB 응답 JSON 파싱 실패`

는 이후 동일 테스트가 정상 통과했으므로 현재는 지속적인 코드 결함보다
Building HUB upstream의 일시적 비정상/비JSON 응답 가능성이 높은 상태다.

운영 안정화를 위해 `site_analysis_orchestrator.fetch_building_items()`의
JSON 파싱 실패 메시지에 다음 diagnostics 추가 권장:

- HTTP status
- Content-Type
- response length
- body preview (API key 제외)

---

## 11. 최근 전체 회귀 검증 상태

다음 주요 회귀 테스트는 현재 PASS 상태다.

- `district_unit_plan_dual_site_regression_test`
- `development_promotion_district_runtime_regression_test`
- `settlement_district_runtime_regression_test`
- `disaster_prevention_district_runtime_regression_test`
- `development_promotion_rule_propagation_regression_test`
- `settlement_district_rule_propagation_regression_test`
- `disaster_prevention_district_rule_propagation_regression_test`
- `disaster_prevention_district_numeric_guard_runtime_regression_test`
- `runtime_spatial_condition_generalization_regression_test`
- `runtime_site_condition_overlay_regression_test`
- `site_data.test_site_analysis_service`
- `site_data.test_real_multi_site_analysis`
- `test_api_app.py`

---

## 12. 현재 완료 판정

### C-16-5 Runtime Spatial Generalization

완료.

### C-16-7 방재지구

완료.

완료 기준:

- dataset 확인
- positive feature 확보
- positive PNU 확보
- Parcel PNU 직접 검증
- geometry intersection 검증
- FALSE / TRUE runtime regression
- Rule Engine propagation
- 상위 branch 조건 연결
- PROJECT 조건 유지
- numeric guard leakage 제거
- multi-site non-regression
- FastAPI E2E 통과

---

## 13. 다음 작업 권장 순서

### 1순위: 현재 변경사항 Git 체크포인트 저장

권장:

```powershell
git status
git add .
git commit -m "Complete disaster prevention runtime spatial condition integration"
git status
```

필요하면 commit 전에 `.env`, 생성 cache, 임시 output 파일이 staging에 포함되지 않았는지 확인한다.

### 2순위: Building HUB JSON parsing diagnostics 보강

대상:

`site_data/site_analysis_orchestrator.py`

목표:

일시적인 upstream non-JSON 응답 발생 시 원인을 즉시 식별할 수 있도록
HTTP / Content-Type / Length / Preview를 `BuildingAPIError`에 포함한다.

기존 동작 및 성공 경로는 변경하지 않는다.

### 3순위: STEP 17-21-C-16-8

다음 runtime 공간조건을 선정한다.

선정 원칙:

1. Rule registry에 SITE predicate가 존재
2. 실제 공간 dataset 후보 존재
3. positive feature 확보 가능
4. Parcel intersection으로 TRUE/FALSE 판정 가능
5. Rule propagation 효과를 회귀 테스트할 수 있음

새 condition을 추가할 때 기존 4종과 동일한 공통 registry/evaluator 경로를 사용하고,
개별 builder 하드코딩은 추가하지 않는다.

---

## 14. 핵심 설계 원칙

현재 유지해야 할 원칙:

- SITE 공간조건은 runtime spatial evaluator registry 중심
- POINT 단독 TRUE 확정 금지
- PNU Parcel Polygon 검증 필수
- target PNU와 Feature PNU 직접 일치
- Polygon / MultiPolygon만 판정
- CRS 명확성 필수
- 다른 SITE에 대표 snapshot 재사용 금지
- Rule Engine은 runtime SITE condition을 우선 사용
- historical/static resolution JSON이 runtime 결과를 덮어쓰지 않도록 주의
- PROJECT / PROCEDURE 조건은 SITE spatial condition과 분리 유지
- 조건 충족 전 숫자 완화값 확정 금지
- 실제 direct relaxation 발생 시 재계산 필요 상태를 명시적으로 유지

---

## 15. 현재 안정 상태 요약

```text
Runtime Spatial Conditions: 4

지구단위계획   PASS
개발진흥지구   PASS
취락지구       PASS
방재지구       PASS

Parcel PNU verification         PASS
Runtime condition overlay       PASS
Rule propagation                PASS
Clause 189 upper branch         PASS
Numeric guard leakage removal   PASS
BASE regression                 PASS
LIVE multi-site regression      PASS
FastAPI end-to-end              PASS
```

현재 상태에서 다음 단계 개발을 진행해도 된다.

STEP 17-21-C-16-8

Target:
- 개발밀도관리구역
- UQQ700

Resolution type:
- HYBRID_SPATIAL_NOTICE

Completed:
- regulation resolution type registry
- S-3 historical endpoint qualification hardening
- municipality exact region binding
- T-1 bounded historical target document discovery
- T-2 canonical reverse discovery
- T-2-S1 semantic candidate gate hardening

T-2-S1 result:
- S-3 endpoints: 7
- requests: 120
- query contamination rejected: 41,664
- raw candidates: 0
- canonical candidates: 0
- next-stage documents: 0
- all_pass: True

Interpretation:
- previous reverse-discovery candidates were query-contaminated false positives
- current source scope provides no verified UQQ700 historical document
- absence is not negative evidence
- SITE remains UNKNOWN

Safety:
- verified positive: blocked
- runtime registration: blocked
- SITE TRUE: blocked
- SITE FALSE from source failure: blocked

Next:
STEP 17-21-C-16-8-T-3
Historical Search Form Action & Notice Identity Recovery