# AI 대지분석 자동화 시스템 — PROJECT STATUS

*Last updated: 2026-08-20*

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
11. AI가 규칙엔진의 판정 결과를 설명하고 보고서로 생성

핵심 원칙:

> **Rule Engine이 판정하고, AI는 설명한다.**

---

## 2. 현재 테스트 SITE

- 주소: 서울특별시 강남구 개포동 12번지
- SITE ID: `11680-10300-0012-0000`
- PNU: `1168010300100120000`
- 시군구코드: `11680`
- 법정동코드: `10300`
- 본번: `0012`
- 부번: `0000`
- 산여부 코드: `1`
- 용도지역: **제3종일반주거지역**
- 대표 좌표:
  - X: `127.07539280356858`
  - Y: `37.494197498186885`

Parcel Polygon dataset:

```text
LP_PA_CBND_BUBUN
```

MapPlan 기준 Parcel:

```text
geometry: Polygon
area: 120945.65223377591
bounds:
(962201.02522, 1943722.58159, 962711.06096, 1944220.16506)
```

---

## 3. 전체 아키텍처

```text
SITE
│
├─ 주소 / SITE ID / PNU / 좌표 / Parcel Polygon
├─ 토지정보
├─ 건축물정보
├─ 용도지역
├─ 용도지구
├─ 용도구역
├─ 도시계획시설
│
└─ 법규 분석
    ├─ 법률
    ├─ 시행령
    ├─ 서울시 조례
    ├─ 일반 규정
    └─ 특례 규정
        ├─ SITE
        ├─ SITE_HISTORY
        ├─ PROJECT
        └─ PROCEDURE
```

최종 판정 구조:

```text
법규 clause
+ 용도지역 적합성
+ SITE 공간조건
+ SITE_HISTORY 조건
+ PROJECT 조건
+ PROCEDURE 조건
+ branch-local predicate
+ numeric semantic / guard
= 실제 적용 가능성 및 최종 수치
```

---

## 4. STEP 1 ~ STEP 16 요약

### STEP 1 ~ STEP 15

- 주소 기반 SITE 생성
- SITE ID 생성
- 시군구 / 법정동 / 본번 / 부번 구조화
- 외부 API 연결 기반 구축
- `.env` 기반 API Key 관리
- SITE Builder 구축
- 외부 API 응답을 내부 SITE 데이터 구조로 변환
- 테스트 데이터 중심 구조에서 실제 공공 API 기반 구조로 전환
- 환경변수 이름 불일치 문제 수정 및 실제 API Key 로딩 정상화

### STEP 16 — 실제 토지/건축물 데이터 연결

가상 데이터에서 실제 필지 데이터 기반으로 전환하였다.

실제 건축물 API:

```text
전체 데이터 수: 34
현재 받은 건축물 수: 34
```

---

## 5. STEP 17 — 법규 자동분석 엔진

주요 분석 법규:

- 국토의 계획 및 이용에 관한 법률
- 국토의 계획 및 이용에 관한 법률 시행령
- 서울특별시 도시계획 조례

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

### C-8 최종 핵심 검증

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

```text
C-8 parser: ALL PASS
```

현재 규칙 단위:

```text
총 clause: 314
```

---

## 8. 용도지역 관련성 판정

현재 SITE 계층:

```text
제3종일반주거지역
⊂ 일반주거지역
⊂ 주거지역
⊂ 도시지역
```

Clause 관련성:

- `DIRECT`
- `GROUP`
- `UNSPECIFIED`
- `EXCLUDED`

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

### C-9 최종 상태

```text
STEP 17-21-C-9
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
| 개발밀도관리구역 | 이후 C-10에서 FALSE로 해결 | HIGH |
| 학교이적지 | 이후 C-10에서 FALSE로 해결 | HIGH |
| 서울도심 | 이후 C-10에서 FALSE로 해결 | HIGH |
| 방재지구 | 이후 C-10에서 FALSE로 해결 | HIGH |
| 도시지역편입해제구역 | UNKNOWN | MEDIUM |

---

## 10. STEP 17-21-C-10 — Rule Applicability / Numeric Evaluation

C-9에서 구축한 SITE / SITE_HISTORY 결과를 실제 314개 clause의 applicability와 numeric effect에 연결하였다.

---

## 11. C-10 SITE Rule Evaluation 완료

최종 SITE 단계:

```text
SITE stage: COMPLETE_WITH_EXTERNAL_DEPENDENCY
Rule engine ready: True

APPLICABLE: 58
NOT_APPLICABLE: 211
CONDITIONAL: 43
UNKNOWN: 2

Confirmed BCR: 50.0
Confirmed FAR: 250.0
```

일반 SITE unresolved:

```text
0
```

외부 역사자료 dependency:

```text
1
```

### 해결 완료된 주요 SITE 조건

```text
서울도심             FALSE / HIGH
개발밀도관리구역     FALSE / HIGH
학교이적지           FALSE / HIGH
방재지구             FALSE / HIGH
지구단위계획         TRUE / HIGH
```

---

## 12. 개발밀도관리구역 — FALSE / HIGH

서울시 공식 고시 DB와 공간/토지이음 자료를 다중 검증하였다.

최종:

```text
Announcement DB: OK
Rows: 43508
Exact hits: 0
Broad hits: 0

UQ145: OK
Feature: 1
Target hits: 0

EUM: OK
Name present: False

개발밀도관리구역: FALSE / HIGH
```

Rule overlay:

```text
Touched rules: 11
Changed rules: 11
UNKNOWN -> NOT_APPLICABLE: 11
```

---

## 13. 학교이적지 — FALSE / HIGH

서울시 공식 고시 DB 전체 검색:

```text
Total: 43508
Direct school history: 0
Strong relocation candidates: 1
```

개포동 강한 후보:

```text
서울특별시 고시 제2015-10호
대상: 강남구 개포동 153번지 일대
```

현재 SITE:

```text
강남구 개포동 12번지
```

주소 불일치가 명확하여:

```text
학교이적지: FALSE / HIGH
```

Rule overlay:

```text
Touched rules: 7
Changed rules: 7
UNKNOWN -> NOT_APPLICABLE: 7
```

---

## 14. 서울도심 — FALSE / HIGH

현재 SITE는 서울도심 범위에 해당하지 않음.

```text
서울도심: FALSE / HIGH
```

영향 clause:

```text
clause 208
UNKNOWN -> NOT_APPLICABLE
```

---

## 15. 방재지구 — FALSE / HIGH

서울특별시 고시 제2019-133호의 방재지구 폐지와 이후 재지정 여부를 검증하였다.

후속 고시 DB:

```text
Post-2019-04-25 notices: 3952
방재지구 hits: 0
Strong redesignation: 0
Gangnam/Gaepo hits: 0
```

최종:

```text
방재지구: FALSE / HIGH
NO_REDESIGNATION_EVIDENCE
```

이에 따라 FAR 300% 후보가 제거되었다.

---

## 16. 도시지역편입해제구역 — UNKNOWN / MEDIUM

이 조건은 현재 상태가 아니라 과거 도시계획 변경 이력이 필요한 `SITE_HISTORY` 조건이다.

검증 자료:

```text
서울시 공식 고시 DB: 43508건
Combined candidates: 8
Target candidates: 0
Direct notices: 1
Direct target history: 0

Current urban: True
Current greenbelt: False

Historic missing content: True
Archive candidates: 10
Archive pending: True
```

최종:

```text
도시지역편입해제구역: UNKNOWN / MEDIUM
automation_state: HISTORICAL_SOURCE_PENDING
overlay: KEEP_UNKNOWN
```

핵심 정책:

> 과거 핵심 원문이 미확인된 상태에서는 negative DB 검색만으로 FALSE를 강제하지 않는다.

이 조건은 외부 역사자료 dependency로 격리한다.

```text
blocking_site_stage: False
```

따라서 SITE Rule Evaluation은:

```text
COMPLETE_WITH_EXTERNAL_DEPENDENCY
```

로 완료 처리한다.

---

## 17. 기본 건폐율 / 용적률 확정

현재 SITE 용도지역:

```text
제3종일반주거지역
```

기본 규제값:

```text
Base BCR: 50.0
Base FAR: 250.0
```

국가 상한:

```text
National BCR ceiling: 70.0
National FAR ceiling: 500.0
```

현재 확정값:

```text
Confirmed BCR: 50.0
Confirmed FAR: 250.0
```

---

## 18. Numeric Semantic Engine

Numeric clause:

```text
Numeric clauses: 124
```

hierarchy dedup 이후 후보:

```text
Final numeric candidates: 28
```

주요 semantic type:

- `RANGE`
- `BASE_RATIO_MULTIPLIER`
- `ABSOLUTE_MAX`
- `MAX_LIMIT_REDUCTION_RATIO`
- `ABSOLUTE_CEILING`
- `NON_EFFECT_THRESHOLD`
- `MAX_LIMIT_MULTIPLIER`

부모 aggregate clause는 child leaf clause가 존재하면 계산 후보에서 제외한다.

---

## 19. Numeric-specific SITE guard

단순 applicability만으로 숫자 특례를 적용하지 않는다.

### clause 4 — BCR 60% 후보

```text
서울특별시 도시계획 조례
해당 용도지역별 건폐율의 120%
```

상위 시행령 branch를 추적한 결과 현재 SITE 용도지역과 불일치.

```text
clause 4: NOT_APPLICABLE
BCR 60% 적용 금지
```

### clause 189 — FAR 300% 후보

방재지구 조건이 필수.

```text
방재지구: FALSE / HIGH
clause 189: NOT_APPLICABLE
FAR 300% 적용 금지
```

---

## 20. PROJECT / PROCEDURE Profile

PROJECT condition template:

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
```

PROCEDURE condition:

```text
도시계획위원회심의
시장정비사업심의
```

초기 상태:

```text
UNSET
```

---

## 21. PROJECT / PROCEDURE Dynamic Evaluation

동적 입력을 Rule Engine에 주입하는 구조를 검증하였다.

테스트 scenario:

```text
PROJECT
공동주택 = TRUE

PROCEDURE
도시계획위원회심의 = TRUE
```

결과:

```text
Before:
APPLICABLE: 58
NOT_APPLICABLE: 211
CONDITIONAL: 43
UNKNOWN: 2

After:
APPLICABLE: 64
NOT_APPLICABLE: 211
CONDITIONAL: 37
UNKNOWN: 2

Touched rules: 16
Changed rules: 6
Transitions:
CONDITIONAL -> APPLICABLE: 6
```

---

## 22. Dynamic Numeric Guard

동적 입력 이후 잘못 재활성화된 숫자 특례를 별도 guard로 검증하였다.

초기 immediate 후보:

```text
clause 4   → BCR 60
clause 189 → FAR 300
clause 205 → FAR 325
```

### clause 4

```text
상위 branch 불일치
→ NOT_APPLICABLE
```

### clause 189

```text
방재지구 FALSE / HIGH
→ NOT_APPLICABLE
```

### clause 205

본문:

```text
제48조제7호부터 제10호까지의 지역에서
관광숙박시설을 건축하는 경우
용적률 130% 이하
```

현재 SITE:

```text
제3종일반주거지역
서울시 조례 제48조 제5호
```

따라서:

```text
서울조례제48조7호부터10호지역 = FALSE
관광숙박시설 = UNSET
clause 205 = NOT_APPLICABLE / HIGH
FAR 325% 적용 금지
```

---

## 23. Branch-local Predicate Generalization

개별 numeric clause를 수동 패치하는 대신, 조문 내부 branch-local predicate를 자동 탐지하는 probe를 구축하였다.

전체 numeric 후보:

```text
Numeric rules: 28
Rules with missing predicates: 3
Active rules with missing predicates: 1
HIGH-priority missing: 7
```

검출된 주요 누락 predicate:

```text
서울도심 / SITE
서울조례제48조7호부터10호지역 / SITE
관광숙박시설 / PROJECT
감염병대응필요시설 / PROJECT
```

clause 205 regression:

```text
Detected:
- 관광숙박시설
- 서울도심
- 서울조례제48조7호부터10호지역

Expected:
- 관광숙박시설
- 서울조례제48조7호부터10호지역

Complete: True
```

---

## 24. Branch-local Condition Overlay

HIGH confidence + clause 본문 직접 등장 predicate만 실제 condition model에 추가한다.

결과:

```text
Selected predicates: 7
Added conditions: 7
Touched rules: 3
Changed rules: 2
```

상태 변화:

```text
Before:
APPLICABLE: 64
NOT_APPLICABLE: 211
CONDITIONAL: 37
UNKNOWN: 2

After:
APPLICABLE: 63
NOT_APPLICABLE: 213
CONDITIONAL: 36
UNKNOWN: 2
```

주요 regression:

```text
clause 205
APPLICABLE -> NOT_APPLICABLE

clause 188
APPLICABLE -> CONDITIONAL
감염병대응필요시설 = UNSET
```

---

## 25. SITE Resolution Registry Reuse

branch-local predicate가 새로 만들어질 때 이미 해결한 SITE condition을 재사용해야 한다.

서울도심 registry:

```text
서울도심 = FALSE / HIGH
```

repair 결과:

```text
clause 201 | 서울도심 | UNKNOWN -> FALSE
clause 205 | 서울도심 | UNKNOWN -> FALSE
```

---

## 26. Dynamic Numeric Final Guard Recheck

현재 dynamic scenario에서:

```text
Active numeric before guard: 11
Excluded: 2
- clause 4
- clause 189

Active numeric after guard: 9
```

Roles:

```text
CONDITIONAL_PLAN_RANGE: 1
DISTRICT_PLAN_CEILING: 2
NATIONAL_CEILING: 2
CONDITIONAL_STRENGTHENING: 2
SPECIAL_AREA_REFERENCE: 1
OTHER_ACTIVE: 1
```

즉시 적용 relaxation:

```text
0
```

따라서:

```text
Numeric resolution: BASE_VALUES_RETAINED

Confirmed BCR: 50.0
Confirmed FAR: 250.0
```

---

## 27. Residual Numeric Role Probe

남아 있던 `OTHER_ACTIVE: 1`을 확인하였다.

Residual:

```text
clause 250
국토의 계획 및 이용에 관한 법률
용도지역에서의 용적률
제78조제7항제2호
```

본문:

```text
지구단위계획구역 외의 지역:
제1항 및 제2항에 따라 대통령령으로 정하고 있는
해당 용도지역별 용적률 최대한도의 120퍼센트 이하
```

상위 문맥:

```text
다른 법률에 따른 용적률 완화 규정을 중첩 적용할 수 있음
```

현재 preliminary 판단:

```text
직접 FAR 완화가 아님
중첩 완화 상한(cap) 조문
```

현재 SITE:

```text
지구단위계획 = TRUE
```

따라서 clause 250의:

```text
지구단위계획구역 외의 지역
```

branch는 현재 SITE와 불일치할 가능성이 높다.

---

## 28. 현재 정확한 중단 위치

오늘 작업은 아래까지 완료하였다.

```text
STEP 17
└─ STEP 17-21
   └─ C-10
      └─ 4B
         └─ 2D
            dynamic_numeric_residual_role_probe_test.py
            ALL PASS
```

직전 실행 결과:

```text
Active before guard: 11
Blocked: [4, 189, 205]
Active after guard: 9

Residual roles: 1
Residual immediate risk: 0

Residual clause:
250
```

---

## 29. 다음 재개 지점

다음 작업:

```text
STEP 17-21-C-10-4B-2E
Clause 250 stacking ceiling resolution
```

### 아직 작성/실행하지 않은 파일

```text
law_data/clause_250_stacking_ceiling_resolution_test.py
```

### 검증 목표

예상 role:

```text
STACKING_CEILING_OUTSIDE_DISTRICT_PLAN
```

검증 내용:

```text
clause 250
= 직접 FAR 효과가 아니라
  여러 용적률 완화 규정 중첩 시 적용하는 ceiling

현재 SITE
지구단위계획 = TRUE

clause 250 대상
지구단위계획구역 외의 지역

예상:
branch match = False
clause 250 = NOT_APPLICABLE
direct numeric effect = False
```

**2026-08-20 작업 종료 시점에는 이 파일을 작성하거나 실행하지 않았다.**

---

## 30. Clause 250 완료 후 예정 작업

Clause 250 검증이 완료되면 개별 numeric clause 탐색을 종료하고 다음 요소를 하나의 재사용 가능한 evaluation pipeline으로 통합한다.

```text
SITE resolution registry
+
SITE_HISTORY external dependency
+
PROJECT dynamic input
+
PROCEDURE dynamic input
+
branch-local predicate detector
+
numeric semantic override
+
parent-child hierarchy dedup
+
verified numeric guard
+
ceiling / stacking rule
=
Reusable Rule Evaluation Pipeline
```

목표 API 형태 예:

```python
evaluate_site_rules(
    site=site,
    project_profile=project_profile,
    procedure_profile=procedure_profile,
)
```

출력 목표:

```text
rule applicability
numeric effects
confirmed BCR/FAR
conditional alternatives
unknown external dependencies
evidence
```

---

## 31. 현재 Rule Engine 핵심 상태

```text
Total rules: 314

SITE evaluation:
COMPLETE_WITH_EXTERNAL_DEPENDENCY

Rule engine ready:
True

SITE baseline:
APPLICABLE: 58
NOT_APPLICABLE: 211
CONDITIONAL: 43
UNKNOWN: 2

Dynamic test:
공동주택 TRUE
도시계획위원회심의 TRUE

branch-local overlay 이후:
APPLICABLE: 63
NOT_APPLICABLE: 213
CONDITIONAL: 36
UNKNOWN: 2

Confirmed BCR:
50.0

Confirmed FAR:
250.0
```

---

## 32. 현재 프로젝트 핵심 안전 원칙

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
코드 의미는 공식 source에서 명칭과 직접 연결 검증 후 사용

PROJECT/PROCEDURE TRUE만으로 numeric 특례 적용 금지
상위 법령 branch 조건을 반드시 검증
branch-local SITE/PROJECT/PROCEDURE predicate를 함께 평가
부모 aggregate numeric + child numeric 중복 적용 금지
상한(ceiling)과 직접 완화(effect)를 구분
중첩(stacking) 허용 여부를 별도 판정

외부 역사 원문 미확인은 UNKNOWN으로 보존
negative search만으로 SITE_HISTORY FALSE 강제 금지
```

---

## 33. 현재 전체 개발 단계

```text
PHASE 1  기초 SITE / API                         완료
PHASE 2  실제 토지·건축물 데이터                 완료
PHASE 3  법령 API / 법규 수집                    완료
PHASE 4  법규 Clause Parser                      핵심 완료
PHASE 5  용도지역 관련성 판정                     완료
PHASE 6  SITE 공간조건 판정                       완료
PHASE 7  SITE_HISTORY 판정                        완료*
PHASE 8  PROJECT 조건 모델                        핵심 구축
PHASE 9  PROCEDURE 조건 모델                      핵심 구축
PHASE 10 특례 적용 가능성 엔진                    진행 중
PHASE 11 기본 건폐율·용적률 결정                  핵심 완료
PHASE 12 법규 우선순위 / 중첩 규정 처리            진행 중
PHASE 13 Formula / 수치 계산 엔진                 진행 중
PHASE 14 지구단위계획 결정도서 자동분석            예정
PHASE 15 최종 SITE 규제값 계산                    진행 중
PHASE 16 대지분석 결과 객체 통합                   예정
PHASE 17 AI 설명 / 보고서 생성                    예정
PHASE 18 서비스 UI / 자동화 API                   예정
```

`PHASE 7`의 `완료*` 의미:

```text
자동화 가능한 SITE_HISTORY 검증은 완료.
도시지역편입해제구역은 HISTORICAL_SOURCE_PENDING external dependency로 보존.
```

---

## 34. 주요 결과 파일

현재 중요 snapshot / resolution:

```text
law_data/output/site_spatial_condition_final_snapshot.json
law_data/output/special_rule_applicability.json
law_data/output/project_profile_template.json
law_data/output/procedure_profile_template.json
law_data/output/site_numeric_regulation_final_snapshot.json
law_data/output/site_rule_evaluation_final_snapshot.json

law_data/output/seoul_downtown_condition_resolution.json
law_data/output/development_density_management_evidence_resolution.json
law_data/output/school_relocation_site_candidate_resolution.json
law_data/output/urban_area_conversion_history_final_resolution.json

law_data/output/site_rule_evaluation_site_complete.json
law_data/output/project_procedure_dynamic_rule_evaluation.json
law_data/output/dynamic_active_numeric_context_probe.json
law_data/output/dynamic_numeric_guard_reconciliation.json
law_data/output/clause_205_tourism_branch_guard.json
law_data/output/numeric_branch_local_condition_generalization_probe.json
law_data/output/numeric_branch_local_condition_overlay.json
law_data/output/dynamic_numeric_final_guard_recheck.json
law_data/output/dynamic_numeric_residual_role_probe.json
```

---

## 35. 다음 작업 시작용 핸드오프

```text
AI 대지분석 자동화 시스템 개발을 계속한다.

기준 문서:
PROJECT_STATUS.md

현재 SITE:
서울특별시 강남구 개포동 12번지
SITE ID: 11680-10300-0012-0000
PNU: 1168010300100120000
용도지역: 제3종일반주거지역

현재 SITE Rule Evaluation:
COMPLETE_WITH_EXTERNAL_DEPENDENCY

Rule Engine ready:
True

Confirmed BCR:
50%

Confirmed FAR:
250%

일반 SITE unresolved:
0

External historical dependency:
도시지역편입해제구역
UNKNOWN / MEDIUM
HISTORICAL_SOURCE_PENDING

현재 dynamic test:
공동주택 = TRUE
도시계획위원회심의 = TRUE

branch-local condition / verified numeric guard 적용 후
즉시 적용 numeric relaxation:
0

직전 완료:
STEP 17-21-C-10-4B-2D
dynamic_numeric_residual_role_probe_test.py
all_pass: True

Residual:
clause 250
국토의 계획 및 이용에 관한 법률 제78조제7항제2호
"지구단위계획구역 외의 지역:
해당 용도지역별 용적률 최대한도의 120퍼센트 이하"

현재 판단:
직접 FAR effect가 아니라 stacking ceiling일 가능성이 높음.

다음 단계:
STEP 17-21-C-10-4B-2E
Clause 250 stacking ceiling resolution

다음 작성 파일:
law_data/clause_250_stacking_ceiling_resolution_test.py

주의:
2026-08-20 종료 시점에는 위 파일을 아직 작성/실행하지 않았다.

검증 목표:
role = STACKING_CEILING_OUTSIDE_DISTRICT_PLAN
현재 SITE 지구단위계획 TRUE
따라서 "지구단위계획구역 외의 지역" branch 불일치 확인
direct numeric effect = False 확인

그 다음:
SITE registry
+ PROJECT/PROCEDURE dynamic inputs
+ branch-local predicates
+ numeric semantic overrides
+ verified guards
+ stacking/ceiling
을 하나의 reusable Rule Evaluation Pipeline으로 통합한다.
```

---

## 36. Git 체크포인트

GitHub 원격 저장소:

```text
jehun0620-bot/site-ai
branch: main
```

현재 원격 기준 직전 체크포인트:

```text
37e1a4a
Complete C-9 SITE spatial condition validation
```

이번 체크포인트에는 C-10에서 생성·수정된 Python 코드와 `PROJECT_STATUS.md`를 저장한다.

권장 commit message:

```text
Checkpoint C-10 dynamic rule and numeric evaluation
```

Git 저장 전 반드시:

```powershell
git status --short
git diff --stat
```

으로 실제 변경 범위를 확인한다.

`git add .`, `git add -A`, `git add --all`은 사용하지 않는다.

`law_data/output/*.json`은 프로젝트에서 기존부터 추적하는 경우에만 stage한다.

---

# STEP 17-21-C-12 CHECKPOINT

최종 업데이트: 2026-08-21

## 현재 단계

STEP 17-21-C-12-5 완료

FastAPI Thin HTTP Layer까지 구현 및 실제 서버 검증 완료.

다음 작업:

STEP 17-21-C-12-6
API Contract / Error Handling Regression

검증 예정:
- 잘못된 입력 -> 422
- 존재하지 않는 필지 -> 404
- Building HUB 오류 -> 502
- 내부 분석 오류 -> 500


## 최종 서비스 흐름

건축HUB 실제 API
→ create_site()
→ Site dataclass
→ analyze_site_object()
→ build_site_analysis()
→ SITE spatial / rule evaluation
→ build_site_analysis_response()
→ analyze_site_by_parcel()
→ FastAPI
→ POST /v1/site-analysis


## HTTP API

FastAPI app:

api_app.py

Endpoints:

GET /health
POST /v1/site-analysis

Swagger:

/docs

OpenAPI:

/openapi.json


## 실제 서버 검증

실행:

uvicorn api_app:app --reload

검증 결과:

GET /health
→ 200 OK

GET /docs
→ 200 OK

GET /openapi.json
→ 200 OK

POST /v1/site-analysis
→ 200 OK


## API Schema

SITE_ANALYSIS_API_V1

대표 응답:

status = READY

SITE ID:
11680-10300-0012-0000

주소:
서울특별시 강남구 개포동 12번지

도로명주소:
서울특별시 강남구 개포로109길 21 (개포동)

PNU:
1168010300100120000

용도지역:
제3종일반주거지역


## SITE Spatial

대표 좌표:

x = 127.07539280356858
y = 37.494197498186885
CRS = EPSG:4326

Parcel:

geometry = Polygon

MapPlan geometry area:
120945.65223377591

bounds:

[
  962201.02522,
  1943722.58159,
  962711.06096,
  1944220.16506
]

Parcel CRS:

None

CRS status:

SOURCE_CRS_NOT_EXPLICIT

주의:
Parcel CRS는 추정하지 않고 미확정 상태로 유지.


## Land Area Source Policy

VWorld 공식/속성 면적:

121040.4 m²

source:
VWORLD_LAND_CHARACTERISTICS

role:
LEGAL_OR_ATTRIBUTE_LAND_AREA

primary:
official


MapPlan geometry 면적:

120945.65223377591

source:
MAPPLAN_PARCEL_GEOMETRY

role:
SPATIAL_GEOMETRY_AREA


차이:

94.74776622408535

difference ratio:

0.07827780329880384 %

resolution:

KEEP_BOTH_WITH_SOURCE_ROLES


## Rule Engine

Rule Engine:

READY

Stateless:

True

총 rule:

314

현재 representative scenario:

PROJECT:
공동주택 = TRUE

PROCEDURE:
도시계획위원회심의 = TRUE


결과:

APPLICABLE = 63
NOT_APPLICABLE = 213
CONDITIONAL = 36
UNKNOWN = 2


확정 건폐율:

50.0 %

확정 용적률:

250.0 %


Remaining PROJECT inputs:

14

Remaining PROCEDURE inputs:

1


External historical dependency:

도시지역편입해제구역

state:

HISTORICAL_SOURCE_PENDING

분석 실행을 차단하지 않음.


## Parcel Snapshot

공식 C-11 Parcel spatial snapshot:

law_data/output/site_parcel_spatial_snapshot.geojson

metadata:

law_data/output/site_parcel_spatial_recovery.json

source recovery:

law_data/output/seoul_urban_innovation_zone_mapplan_intersection.json


## 주요 신규 모듈

law_data/site_analysis_builder.py
law_data/site_identity_resolver.py
law_data/site_spatial_payload_resolver.py

site_data/site_analysis_service.py
site_data/site_analysis_response.py
site_data/site_analysis_orchestrator.py

api_app.py


## Python package import 정책

C-12부터 site_data / law_data는 package import 방식 사용.

권장 실행:

python -m site_data.<module>

기존 site_data 내부 import는 상대 import 사용:

from .site_data_model import ...
from .building_converter import ...
from .land_converter import ...


## FastAPI Test Dependency

Starlette TestClient 사용을 위해 httpx2 필요.

테스트:

python test_api_app.py

결과:

all_pass: True


## 최종 검증된 테스트

python -m site_data.test_site_analysis_service
→ all_pass: True

python -m site_data.test_real_api_to_site_analysis
→ all_pass: True

python -m site_data.test_land_area_source_reconciliation
→ all_pass: True

python -m site_data.test_site_analysis_land_area_integration
→ all_pass: True

python -m site_data.test_site_analysis_response
→ all_pass: True

python -m site_data.test_site_analysis_orchestrator
→ all_pass: True

python test_api_app.py
→ all_pass: True

uvicorn api_app:app --reload
→ 실제 HTTP server 정상 실행

POST /v1/site-analysis
→ HTTP 200


## 다음 시작 지점

STEP 17-21-C-12-6

API Contract / Error Handling Regression

정상 path는 더 이상 수정하지 않고,
HTTP error mapping을 회귀 테스트할 것.