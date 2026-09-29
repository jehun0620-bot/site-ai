# AI 대지분석 자동화 시스템 — Legal Coverage

최초 작성: 2026-09-28
관리 목적: 법규 Coverage, 자동판정 성숙도, 필요한 Fact 및 외부 API/Data dependency를 통합 추적한다.

---

## 1. 문서 역할

이 문서는 현재 시스템이 어떤 법규를 어느 수준까지 지원하는지를 관리하는 기준 문서다.

단순히 법령 원문이나 clause가 존재한다는 이유로 해당 법규를 "지원" 또는 "자동판정 가능"으로 간주하지 않는다.

Coverage는 다음 단계를 분리하여 관리한다.

- 법령 Source 확보
- Clause 구조화
- 판정에 필요한 SITE / BUILDING / PROJECT / PROCEDURE Fact 확보
- Spatial data 확보
- Predicate 표현 가능성
- Condition expression 표현 가능성
- Rule Engine 평가 가능성
- 실제 Behavioral regression 검증

이 문서는 법규 확장뿐 아니라 향후 추가 API 및 공간데이터 연결 필요성을 함께 관리한다.

---

## 2. Coverage maturity model

법규 또는 법규군의 구현 수준은 다음 상태를 사용한다.

### OUT

현재 시스템 Coverage 대상에 포함되지 않는다.

### IDENTIFIED

향후 Coverage 대상임을 식별했지만 공식 법령 및 구현 범위를 아직 확정하지 않았다.

### SOURCE_VERIFIED

현행 공식 법령 Source와 대상 규정의 존재를 확인했다.

### PARSED

법령 Source가 normalized clause 또는 이에 준하는 구조화 데이터로 변환된다.

### FACT_READY

판정에 필요한 SITE / BUILDING / PROJECT / PROCEDURE Fact를 시스템에서 확보할 수 있다.

### SEMANTIC_READY

조건, predicate, numeric semantic, branch 관계 등 법적 의미를 Rule Engine이 사용할 수 있는 구조로 표현할 수 있다.

### ENGINE_READY

Rule Engine이 해당 규정을 deterministic하게 평가할 수 있다.

### BEHAVIORAL_PASS

대표 실제 SITE 또는 승인된 regression corpus에서 최종 behavior까지 검증됐다.

상위 상태는 하위 상태를 자동으로 의미하지 않는다. 각 단계의 근거를 별도로 확인한다.

---

## 3. API / Data dependency status

법규 판정에 필요한 외부 데이터 또는 API는 다음 상태로 관리한다.

### NONE

추가 외부 API 또는 데이터 연결이 필요하지 않음이 확인됐다.

### EXISTING

현재 시스템에 연결된 provider/API/data로 필요한 Fact를 확보할 수 있다.

### RESEARCH_REQUIRED

필요한 Fact는 식별됐지만 기존 provider로 충분한지 또는 신규 데이터 연결이 필요한지 아직 조사되지 않았다.

### NEW_API_REQUIRED

현재 시스템의 provider만으로 필요한 Fact를 확보할 수 없어 신규 API 연결이 필요함이 확인됐다.

### SPATIAL_DATA_REQUIRED

법규 판정을 위해 별도 GIS / Polygon / spatial layer가 필요하다.

### MANUAL_INPUT

공식 SITE 데이터가 아니라 사용자의 사업계획, 설계조건 또는 절차 진행상태 입력이 필요하다.

하나의 법규는 둘 이상의 dependency 상태를 동시에 가질 수 있다.

예:

EXISTING + MANUAL_INPUT

또는

EXISTING + SPATIAL_DATA_REQUIRED

---

## 4. Fact domain

법규 판정에 필요한 사실은 최소 다음 영역으로 분리한다.

### SITE

현재 필지 자체의 공식 또는 공간적 사실.

예:
- PNU
- 용도지역
- 지구 / 구역
- 산업단지 여부
- 지구단위계획 여부
- 필지면적
- 도로 / 공간 관계

### BUILDING

기존 또는 계획 건축물의 사실.

예:
- 용도
- 구조
- 층수
- 높이
- 연면적
- 건축면적
- 주차
- 설비

### PROJECT

사용자가 계획하는 사업 또는 설계조건.

예:
- 공공주택
- 임대주택
- 공개공지
- 기부채납
- 공공시설 제공

### PROCEDURE

심의, 허가 또는 별도 행정절차 상태.

예:
- 도시계획위원회 심의
- 시장정비사업 심의

### SPATIAL

공식 GIS 또는 geometry intersection이 필요한 사실.

---

## 5. Current repository legal baseline

현재 E-5 조사에서 확인된 production legal corpus baseline:

- normalized clauses: 314
- distinct laws: 3
- distinct law-title groups: 20

현재 corpus는 도시계획, 용도지역, 건폐율, 용적률 및 관련 특례를 중심으로 구성되어 있다.

314 clauses를 314개 법률 또는 314개의 완전 자동판정 법규로 해석하지 않는다.

현재 corpus의 구체적 Coverage는 clause source, semantic structure 및 Rule Engine 평가수준을 기준으로 별도 측정한다.

---

## 6. Current Rule Engine baseline

대표 SITE의 현재 verified regression baseline:

- Rules: 314
- APPLICABLE: 58
- NOT_APPLICABLE: 192
- CONDITIONAL: 43
- UNKNOWN: 21
- Numeric candidates: 28
- Rules requiring input: 50
- Rules with unknown condition: 22
- PROJECT input types: 14
- PROCEDURE input types: 2
- Unresolved SITE condition types: 4

이 값은 현재 대표 regression SITE의 평가 결과이며 전체 법규 Coverage 비율을 의미하지 않는다.

---

## 7. Current E-5 semantic capability

현재 확인된 semantic capability:

- raw numeric value 보존
- verified numeric semantic override
- RESULT와 APPLICABILITY_THRESHOLD 분리
- numeric effect promotion guard
- structural_role = CONTAINER / LEAF
- SITE / PROJECT / PROCEDURE condition 구분
- VERIFIED expression 전용 evaluation gate
- expression operators: ATOM / AND / OR / NUMERIC
- typed numeric fact_context
- additional_site_area_ratio derived fact foundation
- numeric predicate four-state evaluation: TRUE / FALSE / UNSET / UNKNOWN

현재 확인된 limitation:

- production 314-clause corpus의 condition_expression은 현재 모두 NONE
- production VERIFIED expression corpus가 아직 구축되지 않음
- NUMERIC predicate foundation은 production rule expression에 아직 연결되지 않음
- branch-local zone predicate를 모두 표현하지 못함
- spatial predicate는 아직 expression grammar에 구현되지 않음
- aggregate parent와 child의 법적 관계가 완전한 semantic relation으로 모델링되지 않음
- base rule / exception / branch / formula / threshold 관계의 추가 구조화가 필요함

따라서 현재 legal corpus 전체를 SEMANTIC_READY 또는 ENGINE_READY로 일괄 분류하지 않는다.

---

## 8. Structural legal hierarchy rule

현재 normalized clause hierarchy:

- CONTAINER: 63
- LEAF: 251
- TOTAL: 314

structural_role은 법문 구조만 의미한다.

다음 등식은 성립하지 않는다.

- CONTAINER != NOT_APPLICABLE
- CONTAINER != non-evaluable
- CONTAINER != no numeric effect
- CONTAINER != no independent legal meaning

Parent condition을 모든 child에 자동 상속하지 않는다.

Parent가 자체적인 base rule, ceiling, threshold 또는 기타 독립 법적 의미를 가지는 경우 이를 보존한다.

---

## 9. Current verified terminology normalization

현재 확인된 예:

농공단지 → 산업단지

이는 canonical SITE condition과 법령 terminology를 연결하기 위한 normalization이다.

별도의 법적 branch를 병합하거나 branch-local qualifier를 제거하는 의미가 아니다.

---

## 10. Legal Coverage master matrix

아래 Matrix는 건축설계 및 대지분석에서 검토가 필요한 법규 영역을 관리하기 위한 초기 목록이다.

아직 공식 법령 및 repository mapping을 조사하지 않은 영역은 RESEARCH_REQUIRED로 유지한다.

| 법규 영역 | Current Coverage | Fact Domain | Spatial | API/Data | Semantic/Engine | 비고 |
|---|---|---|---|---|---|---|
| 국토계획 / 용도지역 / 밀도 | PARTIAL | SITE / PROJECT / PROCEDURE | 일부 | EXISTING + RESEARCH_REQUIRED | E-5 진행 중 | 현재 314-clause corpus의 중심 |
| 건축 기본규정 | IDENTIFIED | SITE / BUILDING / PROJECT | 조사 필요 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 건축법 계열 상세 조사 필요 |
| 대지와 도로 / 건축선 | IDENTIFIED | SITE / SPATIAL | 필요 가능 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 도로 geometry 및 법적 도로 구분 필요 |
| 건축물 용도 / 용도변경 | IDENTIFIED | BUILDING / PROJECT | 일부 가능 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 용도 taxonomy 필요 |
| 높이 / 사선 / 일조 | IDENTIFIED | SITE / BUILDING / PROJECT / SPATIAL | 필요 가능 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 높이·방향·인접관계 predicate 필요 가능 |
| 피난 / 방화 | IDENTIFIED | BUILDING / PROJECT | 일부 가능 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 건축물 내부 계획정보 필요 가능 |
| 건축물 설비 | IDENTIFIED | BUILDING / PROJECT | 낮음 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 설비별 Fact 정의 필요 |
| 주차 | IDENTIFIED | SITE / BUILDING / PROJECT | 일부 가능 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 지자체 조례 연계 가능성 |
| 소방 | IDENTIFIED | BUILDING / PROJECT | 일부 가능 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 소방 법규군 별도 조사 필요 |
| 장애인 편의 | IDENTIFIED | BUILDING / PROJECT | 낮음 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 대상시설 및 설치기준 구조화 필요 |
| 에너지 절약 | IDENTIFIED | BUILDING / PROJECT | 낮음 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 에너지 관련 기준 조사 필요 |
| 녹색건축 | IDENTIFIED | BUILDING / PROJECT | 낮음 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 인증/의무 대상 구분 필요 |
| 전기차 충전 / 전용주차 | IDENTIFIED | BUILDING / PROJECT | 낮음 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 대상시설 및 주차규모 Fact 필요 |
| 경관 | IDENTIFIED | SITE / PROJECT / PROCEDURE | 가능 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 지자체/구역별 차이 조사 필요 |
| 교육환경 | IDENTIFIED | SITE / SPATIAL / PROJECT | 높음 | SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED | RESEARCH_REQUIRED | 교육환경보호구역 등 검토 |
| 도로 관련 개별규제 | IDENTIFIED | SITE / SPATIAL | 높음 | SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED | RESEARCH_REQUIRED | 도로 종류별 공식 source 필요 |
| 하천 | IDENTIFIED | SITE / SPATIAL | 높음 | SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED | RESEARCH_REQUIRED | 구역 및 점용 관련 조사 필요 |
| 농지 | IDENTIFIED | SITE / SPATIAL | 높음 | SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED | RESEARCH_REQUIRED | 농지전용 등 조사 필요 |
| 산지 / 산림 | IDENTIFIED | SITE / SPATIAL | 높음 | SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED | RESEARCH_REQUIRED | 산지전용 및 산림규제 조사 필요 |
| 문화유산 | IDENTIFIED | SITE / SPATIAL / PROJECT | 높음 | SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED | RESEARCH_REQUIRED | 보호구역/영향검토 조사 필요 |
| 군사시설 | IDENTIFIED | SITE / SPATIAL / BUILDING | 높음 | SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED | RESEARCH_REQUIRED | 고도/협의조건 조사 필요 |
| 공항 / 항공고도 | IDENTIFIED | SITE / SPATIAL / BUILDING | 높음 | SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED | RESEARCH_REQUIRED | 제한표면/높이 데이터 조사 필요 |
| 특수용도 건축물 | IDENTIFIED | BUILDING / PROJECT | 다양 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 용도별 개별법 확장 필요 |
| 지방자치단체 조례 | IDENTIFIED | SITE / BUILDING / PROJECT / PROCEDURE | 다양 | RESEARCH_REQUIRED | RESEARCH_REQUIRED | 지역별 ordinance resolver 필요 |

이 Matrix는 초기 조사대상 목록이며 현행 법령 Coverage 확정표가 아니다.

---

## 11. API / Data Dependency Matrix

법규 확장 시 신규 API를 바로 추가하지 않는다.

먼저 필요한 Fact를 정의한 후 현재 provider 또는 공식 spatial source에서 확보 가능한지 확인한다.

| Data / Fact | 현재 상태 | 현재 Source | 추가 API 가능성 | 관련 법규 |
|---|---|---|---|---|
| Canonical PNU | EXISTING | 현재 parcel pipeline | 낮음 | 공통 |
| Parcel Polygon | EXISTING | 현재 parcel geometry pipeline | 낮음 | 공간규제 공통 |
| 공식 토지 기본정보 | EXISTING | 현재 land provider | 추가 필드 조사 가능 | 국토계획 / 건축 |
| 기존 건축물 기본정보 | EXISTING | Building HUB | 추가 필드 조사 가능 | 건축 / 용도 / 설비 |
| 산업단지 geometry | EXISTING | 현재 official spatial dataset | 낮음 | 국토계획 |
| 지구단위계획 등 runtime spatial fact | PARTIAL | 현재 spatial condition pipeline | 확대 필요 | 국토계획 |
| 법적 도로 / 도로 폭 / 접도 | RESEARCH_REQUIRED | 미확정 | 가능성 높음 | 건축 / 도로 |
| 건축선 | RESEARCH_REQUIRED | 미확정 | 조사 필요 | 건축 |
| 교육환경보호구역 | RESEARCH_REQUIRED | 미확정 | spatial source 필요 가능 | 교육환경 |
| 문화유산 영향범위 | RESEARCH_REQUIRED | 미확정 | spatial source 필요 가능 | 문화유산 |
| 하천구역 | RESEARCH_REQUIRED | 미확정 | spatial source 필요 가능 | 하천 |
| 농지 관련 구역 | RESEARCH_REQUIRED | 미확정 | spatial source 필요 가능 | 농지 |
| 산지 관련 구역 | RESEARCH_REQUIRED | 미확정 | spatial source 필요 가능 | 산지 |
| 군사시설 제한구역 | RESEARCH_REQUIRED | 미확정 | spatial source 필요 가능 | 군사 |
| 공항 제한표면 / 고도 | RESEARCH_REQUIRED | 미확정 | spatial source/API 필요 가능 | 항공 |
| 건축물 계획 용도 | MANUAL_INPUT 후보 | 프로젝트 입력 | 공식 자동취득 대상 아님 | 건축 / 주차 / 소방 등 |
| 계획 연면적 / 층수 / 높이 | MANUAL_INPUT 후보 | 프로젝트 입력 | 공식 자동취득 대상 아님 | 건축 / 피난 / 주차 등 |
| 심의 여부 | MANUAL_INPUT | 사용자 / 절차 입력 | 경우별 조사 | PROCEDURE 계열 |

`RESEARCH_REQUIRED`는 신규 API가 반드시 필요하다는 의미가 아니다.

공식 open data, SHP/WFS/WMS, 기존 provider 확장, 정적 공식 dataset 또는 사용자 입력 중 어떤 방식이 적합한지 조사 후 결정한다.

---

## 12. API adoption rule

신규 API 또는 외부 dataset은 다음 순서로 검토한다.

1. 법규 판정에 필요한 정확한 Fact를 정의한다.
2. 해당 Fact가 SITE / BUILDING / PROJECT / PROCEDURE / SPATIAL 중 어디에 속하는지 결정한다.
3. 현재 provider에서 이미 확보 가능한지 확인한다.
4. 현재 공식 spatial dataset으로 해결 가능한지 확인한다.
5. 사용자 입력이 더 정확한 Project/Procedure Fact인지 확인한다.
6. 위 경로로 해결할 수 없는 경우에만 신규 API 또는 dataset을 검토한다.
7. provider failure와 true negative를 반드시 분리할 수 있어야 한다.
8. provenance를 보존할 수 없는 source는 canonical truth로 바로 승격하지 않는다.

API 수를 늘리는 것이 목표가 아니다.

법규 판정에 필요한 검증 가능한 Fact를 안정적으로 확보하는 것이 목표다.

---

## 13. Coverage measurement rule

향후 Coverage percentage를 계산할 경우 최소 세 종류를 분리한다.

### Source Coverage

공식 Source를 확보한 법규 비율.

### Semantic Coverage

현재 schema로 법적 의미를 충분히 표현할 수 있는 법규 비율.

### Behavioral Coverage

실제 Rule Engine 평가와 regression까지 검증된 법규 비율.

따라서 Source Coverage가 높더라도 Behavioral Coverage는 낮을 수 있다.

단일 "법규 Coverage %" 숫자로 세 수준을 혼합하지 않는다.

---

## 14. Current major gaps

현재 가장 큰 Legal Coverage gap:

1. production verified condition-expression corpus 구축
2. NUMERIC predicate foundation의 production rule 연결
3. branch-local zone predicate 표현
4. spatial predicate 표현
5. parent base-rule / child exception relation
6. aggregate-parent required-input 정리
7. 건축법 계열 Coverage 조사
8. 도로 / 접도 관련 Fact source 조사
9. 건축물 용도 taxonomy
10. 피난 / 방화 / 주차 / 소방 등 building/project 중심 법규 구조화
11. 특수입지 spatial regulation source 조사
12. 지역별 조례 resolution architecture

---

## 15. Recommended research order

현재 권장 조사 순서:

### Phase A — E-5 semantic foundation

- Predicate model
- Verified expression
- Parent / child semantic relation
- Required-input normalization
- Regression

### Phase B — Core architectural regulation

- 건축 기본규정
- 대지와 도로 / 건축선
- 건축물 용도
- 높이 / 일조
- 주차
- 피난 / 방화

### Phase C — Building-specific regulation

- 소방
- 장애인 편의
- 건축물 설비
- 에너지
- 녹색건축
- 전기차 충전

### Phase D — Site-specific regulation

- 교육환경
- 문화유산
- 하천
- 농지
- 산지
- 군사시설
- 공항 / 항공고도
- 기타 특수입지

### Phase E — Local ordinance expansion

- 서울시 조례
- 자치구 규정
- 타 지자체 확장
- 지역별 ordinance resolution

각 Phase는 공식 현행법 검증 후 세부 법령 목록과 Coverage 상태를 확정한다.

---

## 16. Change log

### 2026-09-28

- Legal Coverage 독립 관리 문서 최초 생성.
- 현재 repository baseline 3 laws / 20 law-title groups / 314 normalized clauses 기록.
- E-5 semantic capability와 limitation 기록.
- Legal Coverage maturity model 정의.
- API / Data dependency status 정의.
- 건축설계 법규군 초기 master matrix 생성.
- 향후 신규 API 및 spatial data 필요성을 법규 Coverage와 함께 추적하도록 관리원칙 확정.


---

## 17. Legal Coverage research reconciliation — 2026-09-28

이 절은 2026-09-28까지 수행한 1차 Legal Coverage 공식법령 조사 결과를 현재 프로젝트의 개발 범위에 맞게 정리한 checkpoint다.

기존 초기 Matrix의 RESEARCH_REQUIRED 상태를 무조건 지원 상태로 승격하지 않는다.

공식 법령에서 필요한 법적 Fact와 Rule 구조를 확인한 결과를 기록하며, 실제 API / spatial source / repository implementation이 검증되지 않은 항목은 계속 RESEARCH_REQUIRED로 유지한다.

---

## 18. Current service boundary

현재 프로젝트의 서비스 범위는 다음과 같다.

### 포함

- AI 대지분석
- 규모검토
- 법규검토
- 적용 법규 판정
- 허용규모 산정
- 법적 의무사항 안내
- 필요한 수량 / 비율 / 거리 / 면적 등 Requirement Calculation
- 허가 / 신고 / 협의 / 심의 / 제출 필요성 안내
- 조건 / 예외 / 추가확인사항 안내
- 근거 법령 안내

### 현재 범위에서 제외

- 실제 설계도면의 법적 적합성 판정
- 실제 계단 / 복도 / 출입구 배치 적합성 판정
- 실제 방화구획 적합성 판정
- 실제 장애인 편의시설 상세치수 적합성 판정
- BIM / CAD 도면 자동 Compliance 검사
- 설계도서 전체의 허가 적합성 인증

현재 서비스는 다음 질문에 답하는 것을 목표로 한다.

"이 대지와 계획에는 어떤 법규가 적용되고, 무엇을 얼마나 확보하거나 준수해야 하는가?"

현재 서비스는 다음 질문에 대한 최종 판정을 목표로 하지 않는다.

"현재 설계도면이 모든 법규를 만족하는가?"

---

## 19. Legal Result Model

현재 서비스의 법규 결과는 다음 구조를 기본으로 한다.

### APPLICABILITY

해당 법규가 현재 SITE / PROJECT에 적용되는지 판정한다.

상태:

- APPLICABLE
- NOT_APPLICABLE
- CONDITIONAL
- UNKNOWN

### REQUIREMENT

적용되는 경우 사용자가 무엇을 해야 하는지 제공한다.

대표 Requirement 유형:

- INSTALL
- SECURE
- SUBMIT
- REVIEW
- CONSULT
- REPORT
- PERMIT
- LIMIT
- PROHIBIT
- CALCULATE
- OTHER

### REQUIREMENT_CALCULATION

법규가 요구하는 정량기준을 계산할 수 있는 경우 계산한다.

예:

- 최대 건폐율
- 최대 용적률
- 최소 주차대수
- 최소 확보수량
- 설치비율
- 거리
- 면적
- 높이
- 세대수 / 객실수 / 좌석수 등에 따른 필요수량

Requirement Calculation은 설계도면 Compliance 판정과 다르다.

예:

"주차 20대를 확보해야 한다."

는 현재 서비스 범위다.

"현재 설계도면에 주차 20대가 적법하게 배치되어 있다."

는 현재 서비스 범위가 아니다.

### GUIDANCE

상세설계 또는 후속 행정절차에서 준수해야 할 기준을 사용자에게 안내한다.

예:

- 해당 기준을 만족해야 함
- 별도 심의 필요
- 관계기관 협의 필요
- 조례 추가확인 필요
- 고시 추가확인 필요
- 전문분야 상세검토 필요

---

## 20. Core reusable legal infrastructure discovered by Coverage research

1차 Coverage 조사에서 법규별 hardcoding보다 먼저 필요한 공통 기반이 확인됐다.

### Legal Predicate Model

최소 다음 predicate 계열이 필요하다.

- SITE predicate
- BUILDING predicate
- PROJECT predicate
- PROCEDURE predicate
- NUMERIC predicate
- ZONE predicate
- SPATIAL predicate

### Boolean Expression Model

현재 기반:

- ATOM
- AND
- OR

표현할 수 없는 법적 조건을 억지로 단순 Boolean으로 변환하지 않는다.

### Canonical Building Use Taxonomy

건축물 용도는 여러 법규에서 반복 사용된다.

대표 적용 영역:

- 건축법
- 주차장법
- 피난 / 방화
- 소방
- 장애인 편의
- 에너지
- 친환경자동차 충전시설

법규별 자유 문자열 matching을 반복하지 않고 공통 canonical use taxonomy를 구축하는 방향으로 관리한다.

### Project Action Taxonomy

법규는 신축 / 증축 / 개축 / 재축 / 이전 / 대수선 / 용도변경 등에 따라 적용범위가 달라질 수 있다.

향후 PROJECT 입력은 사업행위를 구조화할 필요가 있다.

### Cross-Rule Dependency

일부 법규는 다른 Rule 결과를 다시 사용한다.

대표 예:

- 건축법 건폐율 / 용적률과 국토계획법 기준
- 대지분할과 도로 / 건폐율 / 용적률 / 공지 / 높이 / 일조 기준
- 건축물 용도분류와 주차 / 소방 / 장애인 / 에너지 / EV 기준

---

## 21. Project Fact model discovered by Coverage research

현재 법규 확장을 위해 필요한 주요 PROJECT Fact 후보:

### ACTION

- new_construction
- extension
- reconstruction
- relocation
- major_repair
- change_of_use
- 기타 사업행위

### BUILDING PROGRAM

- building_use
- gross_floor_area
- building_area
- floor_count
- basement_floor_count
- building_height
- household_count
- room_count
- seat_count

### FACILITY

- parking_count
- mechanical_parking_count
- heating
- cooling
- 기타 법규 산정에 필요한 시설조건

모든 값을 최초 분석에서 일괄 입력받지 않는다.

현재 reanalysis architecture를 확장하여 실제 Rule 판정에 필요한 값만 추가 입력으로 요청하는 것을 기본 방향으로 한다.

---

## 22. Road and building-line Coverage findings

대지와 도로 관련 법규는 단순 도로명주소만으로 판정할 수 없다.

필요 Fact 후보:

- legal_road
- road_width
- road_frontage_length
- road_geometry
- building_line_geometry

현재 Parcel Polygon은 활용 가능하지만 법적 도로의 자격, 도로 폭, 접도길이 및 건축선 source는 추가 조사가 필요하다.

API / Data 상태:

RESEARCH_REQUIRED

신규 API 필요 여부는 아직 확정하지 않는다.

---

## 23. Setback, height and daylight Coverage findings

대지 안의 공지, 높이 및 일조 관련 규정은 다음 요소를 조합할 수 있다.

- 용도지역 / 용도지구
- 건축물 용도
- 건축물 규모
- 계획 높이
- 대지경계
- 도로
- 인접대지
- 조례
- 가로구역별 높이 지정 / 고시

규모검토 단계에서는 적용되는 거리 / 높이 / 제한기준을 산정하거나 안내하는 것을 목표로 한다.

실제 설계도면의 배치가 해당 기준을 만족하는지는 현재 자동 Compliance 범위에서 제외한다.

가로구역 높이 등은 조례뿐 아니라 공식 지정 / 고시 데이터가 필요할 수 있다.

---

## 24. Parking Coverage findings

주차기준은 건축물 용도와 규모를 중심으로 Requirement Calculation 가치가 높은 영역이다.

주요 필요 Fact:

- canonical building use
- gross floor area
- household / room / seat 등 용도별 산정값
- project location
- local ordinance

목표 결과:

- 부설주차장 설치의무
- 최소 필요 주차대수
- 적용 산정기준
- 조례 추가확인사항

실제 주차배치의 설계 적합성 판정은 현재 범위에서 제외한다.

---

## 25. Evacuation and fire-protection Coverage findings

피난 / 방화 규정은 다음 조건을 광범위하게 사용한다.

- building use
- floor count
- basement
- floor area
- gross floor area
- height
- structure
- fire compartment
- evacuation-related conditions

현재 규모검토 서비스에서는 다음을 우선한다.

- 해당 피난 / 방화 의무 적용 여부
- 필요한 시설 또는 구조적 의무 안내
- 정량기준이 있는 경우 Requirement Calculation
- 상세설계 단계에서 준수해야 할 기준 안내

실제 평면의 보행거리, 계단 배치, 복도, 방화구획 적합성 판정은 현재 범위에서 제외한다.

따라서 BIM / CAD integration은 현재 Legal Coverage 핵심 dependency로 두지 않는다.

---

## 26. Fire-safety Coverage findings

소방 법규는 건축물 용도와 규모에 따라 특정소방대상물 여부 및 필요한 의무가 달라질 수 있다.

주요 공통 기반:

- canonical building use
- project action
- floor / area / height
- 특정소방대상물 classification
- 허가 / 협의 관련 procedure

세부 화재안전기준은 사용자에게 준수해야 할 기준으로 안내할 수 있다.

실제 소방설계 도면의 Compliance 판정은 현재 범위에서 제외한다.

---

## 27. Accessibility Coverage findings

장애인 편의 관련 법규는 크게 다음 흐름으로 관리한다.

대상시설 판정
→ 필요한 편의시설 의무 확인
→ 준수해야 할 세부기준 안내

현재 서비스 목표:

- 대상시설 여부
- 설치해야 하는 편의시설
- 적용되는 주요 정량기준
- 추가 전문검토 필요사항

실제 설계된 경사로, 출입구, 화장실 등의 상세치수 Compliance 판정은 현재 범위에서 제외한다.

---

## 28. Energy, green-building and EV Coverage findings

### Energy

규모 / 용도 / 사업행위 등에 따라 에너지절약계획서 제출 등의 의무를 판정할 수 있다.

세부 에너지 설계기준은 준수사항으로 안내한다.

### Green Building

인증 또는 의무대상 여부를 규모검토 단계에서 확인할 수 있는 영역을 우선 조사한다.

세부 인증점수 또는 설계도서 적합성 판정은 별도 범위다.

### EV charging

친환경자동차 충전시설 및 전용주차구역은 Requirement Calculation에 적합한 영역이다.

주요 Fact:

- canonical building use
- total parking count
- household count
- facility scale
- local ordinance

목표 결과:

- 설치 대상 여부
- 최소 설치수량 / 비율
- 적용 조례
- 추가확인사항

실제 충전구역 배치 Compliance는 현재 범위에서 제외한다.

---

## 29. Building-equipment Coverage findings

건축설비는 규모검토에서 직접 유용한 의무와 상세설계 기준을 분리한다.

### SCALE_REVIEW

예:

- 승강기 설치대상
- 비상용승강기 필요 여부
- 전기설비 공간 확보의무
- 기타 규모에 따라 직접 발생하는 설치의무

### DETAIL_DESIGN_GUIDANCE

예:

- 급수 / 배수 상세기준
- 환기 상세기준
- 냉난방 상세기준
- 설비 구조 및 유지관리 기준

DETAIL_DESIGN_GUIDANCE는 사용자에게 준수사항을 제공하되 현재 자동 Compliance 판정 대상으로 두지 않는다.

---

## 30. Spatial Regulation Layer

특수입지 법규는 공통 Spatial Architecture로 관리하는 방향을 사용한다.

기본 흐름:

Parcel Polygon
→ Official Regulation Geometry
→ Intersection / Distance
→ Canonical SITE FACT
→ Project Action
→ Legal Rule
→ Requirement / Procedure / Limit

대표 대상:

- 교육환경보호구역
- 역사문화환경 관련 보호 / 보존지역
- 하천구역
- 농지 관련 규제
- 산지 관련 규제
- 군사시설 보호구역
- 공항 / 항공 장애물 제한표면

법규별로 별도의 geometry engine을 만들지 않고 가능한 경우 공통 spatial adapter와 intersection / distance infrastructure를 사용한다.

---

## 31. Special-site Coverage findings

### Education environment

학교 및 교육환경보호구역과 필지의 공간관계가 핵심이다.

필요 데이터:

SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED

목표 결과:

- 보호구역 해당 여부
- 보호구역 종류
- 적용되는 제한 / 추가절차 안내

### Heritage

임의 거리기준을 생성하지 않는다.

공식 보호 / 보존지역 및 관련 지정정보를 기준으로 적용 여부를 판정해야 한다.

필요 데이터:

SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED

### River

하천구역 여부와 계획행위를 조합하여 점용허가 등 관련 절차를 안내하는 구조가 적합하다.

필요 데이터:

SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED

### Farmland

농지 여부, 지역조건 및 project action을 조합하여 전용허가 / 협의 / 신고 관련 요구사항을 판정하는 구조가 적합하다.

필요 데이터:

SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED

### Mountain / Forest land

산지 종류, 면적 및 project action을 조합하여 산지전용 관련 요구사항을 판정하는 구조가 적합하다.

필요 데이터:

SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED

### Military

보호구역 종류와 project action을 조합하여 제한 및 관계기관 협의 필요성을 안내하는 구조가 적합하다.

필요 데이터:

SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED

### Airport / aviation height

필지 위치와 장애물 제한표면, 계획높이를 조합하여 적용되는 높이 제한과 추가 협의사항을 안내하는 구조가 적합하다.

필요 데이터:

SPATIAL_DATA_REQUIRED + RESEARCH_REQUIRED

---

## 32. Spatial data acquisition rule

특수입지 법규에 신규 API가 필요하다고 미리 단정하지 않는다.

다음 순서로 조사한다.

1. 공식 SHP / spatial dataset 존재 여부
2. 공식 WFS / WMS 존재 여부
3. 공식 OpenAPI 존재 여부
4. 공식 지형도면 또는 정기배포 dataset 존재 여부
5. 현재 provider 확장 가능 여부
6. 위 방식으로 해결되지 않을 경우 신규 API 검토

목표는 API 개수를 늘리는 것이 아니라 검증 가능한 공식 Spatial Fact를 확보하는 것이다.

---

## 33. Resolver requirements

Coverage 조사 결과 다음 resolver가 장기적으로 필요할 가능성이 높다.

### Local Ordinance Resolver

중앙 법령이 지자체 조례에 위임하는 기준을 지역별로 연결한다.

대표 영역:

- 주차
- 대지 안의 공지
- 일부 높이기준
- EV 충전
- 기타 지역별 강화 / 완화기준

### Official Notice Resolver

법률 / 시행령 / 조례 외에 지정 / 고시로 정해지는 규제를 연결한다.

대표 후보:

- 가로구역별 높이
- 각종 보호 / 제한구역
- 개별 지정사항

실제 구현방식은 source 조사 후 결정한다.

---

## 34. Updated API / Data dependency categories

Coverage 관리 시 다음 dependency를 구분한다.

- NONE
- EXISTING
- RESEARCH_REQUIRED
- NEW_API_REQUIRED
- SPATIAL_DATA_REQUIRED
- MANUAL_INPUT
- OFFICIAL_NOTICE_REQUIRED

MANUAL_INPUT은 단순 자유문자열 입력보다 구조화된 PROJECT Fact를 우선한다.

SPATIAL_DATA_REQUIRED가 NEW_API_REQUIRED를 자동으로 의미하지 않는다.

---

## 35. Legal Coverage Layer model

현재 1차 Coverage 조사 결과 법규를 다음 세 층으로 이해할 수 있다.

### Layer A — SITE / LOCATION

"이 땅이 어디에 있고 어떤 규제를 받는가?"

예:

- 용도지역
- 지구 / 구역
- 산업단지
- 교육환경
- 하천
- 농지
- 산지
- 국가유산 관련 구역
- 군사
- 공항

### Layer B — PROJECT

"무엇을 얼마나 지으려는가?"

예:

- project action
- building use
- area
- floors
- height
- households
- rooms
- seats
- parking

### Layer C — LEGAL REQUIREMENT

"그러면 무엇을 해야 하는가?"

예:

- 허용규모
- 설치
- 확보
- 제출
- 허가
- 신고
- 협의
- 심의
- 제한
- 추가확인

기본 구조:

SITE + PROJECT
→ Rule Engine
→ LEGAL REQUIREMENT

---

## 36. Coverage inventory checkpoint

2026-09-28 1차 Coverage 조사에서 다음 주요 영역을 식별했다.

- 국토계획 / 용도지역 / 밀도
- 건축 기본규정
- 대지와 도로 / 건축선
- 건축물 용도
- 대지 안의 공지
- 높이 / 일조
- 주차
- 피난 / 방화
- 소방
- 장애인 편의
- 에너지
- 녹색건축
- EV 충전
- 건축설비
- 교육환경
- 국가유산 관련 규제
- 하천
- 농지
- 산지
- 군사시설
- 공항 / 항공고도
- 지방자치단체 조례
- 공식 지정 / 고시 기반 규제

이 목록은 모든 대한민국 건축 관련 법규가 완전 조사됐다는 의미가 아니다.

현재 대지분석 / 규모검토 / 법규검토 서비스에서 우선 관리해야 할 주요 Coverage 영역의 1차 inventory다.

---

## 37. Post-Coverage development sequence

1차 Coverage inventory 이후 권장 개발순서:

### Step 1 — Coverage gap finalization

- 필요한 Fact 확정
- API / spatial / ordinance / notice dependency 정리
- 구현 우선순위 확정

### Step 2 — E-5 Semantic Foundation

- Legal Predicate Model
- Numeric Predicate
- Zone / Spatial Predicate
- Verified Expression
- Parent / Child semantic relation
- Required-input normalization

### Step 3 — Canonical Project Model

- Canonical Building Use
- Project Action
- Building Program
- 필요한 Facility Fact

### Step 4 — SITE / Spatial Fact expansion

- Legal Road
- Road width / frontage
- Building line
- 필요한 특수입지 spatial layer

### Step 5 — Resolver foundation

- Local Ordinance Resolver
- Official Notice Resolver

### Step 6 — Core legal expansion

우선순위는 Coverage gap과 데이터 확보 가능성을 검토한 뒤 확정한다.

주요 후보:

- 건축법 핵심 규모규정
- 도로 / 건축선
- 대지 안의 공지
- 높이 / 일조
- 주차
- 피난 / 방화의 규모검토 영역
- 에너지 / EV 등 명확한 Requirement Calculation 영역

### Step 7 — End-to-End regression

실제 Parcel + Project 입력으로 다음 전체 경로를 검증한다.

SITE
→ PROJECT
→ Rule Engine
→ Requirement
→ Additional Input
→ Reanalysis
→ Frontend

### Step 8 — Frontend legal-result expansion

사용자에게 다음을 명확하게 제공한다.

- 적용 여부
- 의무사항
- 정량기준
- 조건
- 예외
- 추가확인
- 근거 법령

---

## 38. 2026-09-28 Coverage research checkpoint conclusion

1차 Legal Coverage 조사의 핵심 결론:

현재 시스템은 단순히 법령 수를 늘리는 방식으로 확장해서는 안 된다.

먼저 다음 공통기반을 안정화해야 한다.

- Legal Predicate
- Canonical Building Use
- Project Fact
- Spatial Regulation Layer
- Ordinance / Notice resolution
- Requirement model

현재 서비스의 목표는 설계도면의 최종 적합성 인증이 아니다.

목표는 사용자에게 다음 정보를 신뢰성 있게 제공하는 것이다.

"이 대지와 계획에 어떤 법규가 적용되고, 무엇을 얼마나 확보하거나 준수해야 하며, 어떤 허가·신고·협의·심의 또는 추가확인이 필요한가?"

## 39. Building Use official-source / structural-parser reconciliation — 2026-09-28

기존 Building Use 초기 inventory의 `IDENTIFIED / RESEARCH_REQUIRED` 기록 이후 공식 source/API 및 structural parser를 실제 검증했다. 아래 checkpoint는 Building Use에 관한 이전의 **API/Data = RESEARCH_REQUIRED** 상태를 현재 증거 범위에서 갱신한다.

### Verified source / data status

- 대상: `건축법 시행령 별표 1 용도별 건축물의 종류(제3조의5 관련)`
- 공식 source existence: **SOURCE_VERIFIED**
- API / Data dependency: **EXISTING**
- 사용 경로: 기존 국가법령정보 `lawSearch.do` / `lawService.do` 및 기존 appendix normalization
- current MST 자동 탐색: 사용자 로컬 PASS
- Annex 1 non-empty official content 취득: 사용자 로컬 PASS
- Annex 1 body / explicit `비고` 분리: 사용자 로컬 PASS
- source MAJOR hierarchy 30개 extraction(기본번호 `1..29` + 가지번호 `23의2`): 사용자 로컬 PASS
- reconstructed structural units: `188`
- `23/라 삭제 <2023. 5. 15.>`와 `23의2 국방ㆍ군사시설` 독립 source node 분리: 사용자 로컬 PASS
- selected detail paths `2/라/1`, `2/라/2`, `14/나/2`: 사용자 로컬 PASS
- physical API `raw_lines` provenance 보존: 사용자 로컬 PASS

Coverage maturity 관점에서 **공식 source는 SOURCE_VERIFIED이며 source hierarchy는 PARSED 수준까지 검증**됐다.

### Not yet promoted

다음은 아직 완료되지 않았으므로 Building Use 전체를 `SEMANTIC_READY` 또는 `ENGINE_READY`로 승격하지 않는다.

- Canonical Building Use taxonomy
- Building Use Identity / Qualification Predicate 의미 구분
- 별표 1 전체 세부조건의 numeric / exception / cross-reference semantic mapping
- current 314 normalized clauses와 canonical use mapping
- PROJECT fact normalization
- deterministic Rule Engine production integration

따라서 현재 상태는 다음처럼 구분한다.

```text
Official Annex 1 source       SOURCE_VERIFIED
Official API / data path      EXISTING
Structural source hierarchy   PARSED / Behavioral PASS
Canonical semantic taxonomy   RESEARCH / IMPLEMENTATION REQUIRED
Rule Engine integration       NOT ENGINE_READY
```

### Source text integrity rule

API physical line wrap은 띄어쓰기 위치와 일치하지 않는다. 단어 사이에서도 끊기고 단어 내부에서도 끊길 수 있음이 실제 Annex 1에서 확인됐다. Structural Parser의 reconstructed text는 구조 판정을 위한 보조 표현이며 공식 원문의 완전한 lexical 복원본으로 간주하지 않는다. 원래 physical `raw_lines`를 node provenance로 보존한다.

### Coverage consequence

Canonical Building Use는 주차, 피난/방화, 소방, 장애인 편의, 에너지, EV 충전 등 여러 Coverage 영역의 공통 PROJECT 기반이다. 따라서 이후 개발은 별표 1 source tree를 다시 수작업으로 만드는 대신, 현재 검증된 official source tree 위에서 semantic taxonomy를 구축한다.

공식 source 자동 취득/구조 파싱 성공은 자동 법적 의미 승인과 동일하지 않다. 법령 개정 시에도 source diff → structural validation → semantic 영향 검토 → affected-rule regression → 승인/promotion 경계를 유지한다.
## Building Use Qualification coverage depth policy — 2026-09-29

Building Use의 official source 또는 qualification 문구가 존재한다는 사실만으로 해당 조건을 자동판정 대상으로 승격하지 않는다. Building Use coverage는 source 확보, semantic 표현 가능성, 실제 evaluation 가능성을 계속 분리해서 관리한다.

자동판정 우선순위가 높은 Qualification은 다음과 같다.

- 면적·층수·세대수·객석·비율·개수처럼 입력 Fact와 법적 경계가 명확한 정량조건
- 다른 Annex 1 용도에 해당하는지 여부처럼 Canonical Building Use 결과를 실제로 바꾸는 명확한 분류 제외조건
- 출처와 입력 의미가 명확한 검증 가능한 상태조건

반대로 다음 조건은 공식 원문이 존재하더라도 현재 Fact/Data/semantic contract가 충분하지 않으면 자동 TRUE/FALSE 판정으로 승격하지 않는다.

- 별도 전문판단 또는 복잡한 타법 자격판단이 필요한 조건
- '이와 유사한 것'처럼 추가 semantic 판단이 필요한 조건
- 현재 제품 입력이나 공식 데이터에서 안정적으로 확보할 수 없는 사실
- 자동화 이득보다 잘못된 분류 위험이 큰 세부조건

이 경우 REVIEW_REQUIRED / UNSET 등 fail-closed 상태와 공식 근거를 유지한다. 이는 미구현을 숨기는 것이 아니라 현재 자동판정 coverage의 한계를 명시적으로 표현하는 것이다.

현재 검증된 Qualification 구조는 SourcePath-common 29건 + Canonical-specific 1건이다. 이 수치는 Annex 1 전체 qualification coverage 비율을 의미하지 않는다. Canonical-specific 첫 사례인 `3/아 + 통신용 시설`은 같은 source path의 다른 canonical use에 조건이 전파되지 않도록 분리한 검증 사례다.

향후 Building Use coverage는 '모든 문구 구현'을 완료조건으로 사용하지 않는다. Canonical final classification과 후속 PROJECT 기반 법규검토에 필요한 핵심 Qualification의 coverage를 점검하고, 충분한 시점에는 PROJECT Mapping 및 다른 고가치 법규영역으로 개발 우선순위를 이동한다.
