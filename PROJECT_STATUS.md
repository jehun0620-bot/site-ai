# AI 대지분석 자동화 시스템 --- PROJECT STATUS

*Last updated: 2026-08-19*

## 1. 프로젝트 목표

주소 또는 필지를 입력하면 시스템이 자동으로 다음을 수행하는 **AI
대지분석 자동화 시스템**을 구축한다.

1.  주소 정규화 및 SITE 식별
2.  PNU / 좌표 / 필지 Polygon 확보
3.  토지·건축물·도시계획 공간정보 수집
4.  용도지역·용도지구·용도구역 판정
5.  관련 법률·시행령·조례 수집
6.  법령 원문을 조/항/호/목/세부 clause 단위로 구조화
7.  SITE와 관련 있는 규정만 선별
8.  SITE / SITE_HISTORY / PROJECT / PROCEDURE 조건 판정
9.  기본 건폐율·용적률·높이 및 특례·완화·강화 규정 계산
10. 최종 대지분석 결과 객체 생성
11. AI가 규칙엔진의 판정 결과를 설명하고 보고서로 생성

핵심 원칙:

> **Rule Engine이 판정하고, AI는 설명한다.**

## 2. 현재 테스트 SITE

-   주소: 서울특별시 강남구 개포동 12번지
-   SITE ID: `11680-10300-0012-0000`
-   PNU: `1168010300100120000`
-   시군구코드: `11680`
-   법정동코드: `10300`
-   본번: `0012`
-   부번: `0000`
-   산여부 코드: `1`
-   용도지역: 제3종일반주거지역
-   대표 좌표:
    -   X: `127.07539280356858`
    -   Y: `37.494197498186885`

## 3. 전체 아키텍처

``` text
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

``` text
법규 clause
+ 용도지역 적합성
+ SITE 공간조건
+ SITE_HISTORY 조건
+ PROJECT 조건
+ PROCEDURE 조건
= 실제 적용 가능성
```

## 4. STEP 1 \~ STEP 16 요약

### STEP 1 \~ STEP 15

-   주소 기반 SITE 생성
-   SITE ID 생성
-   시군구 / 법정동 / 본번 / 부번 구조화
-   외부 API 연결 기반 구축
-   `.env` 기반 API Key 관리
-   SITE Builder 구축
-   외부 API 응답을 내부 SITE 데이터 구조로 변환
-   테스트 데이터 중심 구조에서 실제 공공 API 기반 구조로 전환
-   환경변수 이름 불일치 문제 수정 및 실제 API Key 로딩 정상화

### STEP 16 --- 실제 토지/건축물 데이터 연결

가상 데이터에서 실제 필지 데이터 기반으로 전환하였다.

실제 건축물 API에서 총 34건을 정상 조회하였다.

``` text
가상 SITE
→ 실제 공공 API 기반 SITE
```

## 5. STEP 17 --- 법규 자동분석 엔진

목표:

> 특정 SITE에 실제 적용 가능성이 있는 법규를 자동으로
> 추출·구조화·판정한다.

주요 분석 법규:

-   국토의 계획 및 이용에 관한 법률
-   국토의 계획 및 이용에 관한 법률 시행령
-   서울특별시 도시계획 조례

주요 효과 대상:

-   건폐율
-   용적률
-   높이
-   건축제한
-   완화 규정
-   강화 규정
-   예외 규정
-   특례 규정

국가법령정보센터 API를 통해 법률/시행령/자치법규 상세조회 JSON 연결을
검증하였다.

## 6. 특례 조건 모델

### SITE

현재 필지가 실제로 특정 공간구역에 속하는지 여부.

예: - 지구단위계획 - 개발진흥지구 - 개발밀도관리구역 - 자연경관지구 -
취락지구 - 수산자원보호구역 - 입체복합구역 - 도시혁신구역 -
복합용도구역 - 산업단지 - 자연공원

### SITE_HISTORY

현재 상태가 아니라 과거의 용도·시설·도시계획 변경 이력이 필요한 조건.

예: - 학교이적지 - 도시지역편입해제구역

### PROJECT

사업계획 또는 건축계획에 의해 결정되는 조건.

예: - 공개공지 - 공공시설제공 - 공공주택 - 공동주택 - 기부채납 - 대학 -
사회복지시설 - 임대주택 - 종합의료시설 - 주거복합 - 한옥

### PROCEDURE

심의 또는 행정절차에 관한 조건.

예: - 도시계획위원회심의 - 시장정비사업심의

## 7. STEP 17-21-C-8 --- 특례 Clause Parser

법령 원문을 다음 단계로 세분화하는 파서를 개발하였다.

``` text
조 → 항 → 호 → 목 → 세부 clause
```

### C-8-8 최종 검증 완료

주요 해결 항목:

-   개정일자 조각 제거
-   도시지역 외 규정 배제
-   상업/공업/녹지지역 → 주거지역 오인 방지
-   용도지역 그룹 substring 중복 제거
-   도시지역(녹지지역만) 한정 처리
-   무공백 후속 호 경계 분리
-   DIRECT 규정 내부 다중 목 잔존 제거
-   문장 종결 `다.`를 `다목`으로 오인하는 문제 해결
-   제46조 ⑮항 제3종일반주거지역 제외
-   시장정비사업 제3종일반주거지역 60% 나목 분리
-   시장정비사업 상업지역 다목 제외
-   학교이적지 제3종일반주거지역 200% 바목 분리
-   학교이적지 타 용도지역 목 제외

``` text
C-8 파서 최종 검증: ALL PASS
```

## 8. 용도지역 관련성 판정

Clause 상태:

-   `DIRECT`: 현재 SITE 용도지역 직접 명시
-   `GROUP`: 현재 용도지역이 상위 그룹에 포함
-   `UNSPECIFIED`: 용도지역이 명확히 특정되지 않음
-   `EXCLUDED`: 다른 용도지역에만 적용

현재 SITE 계층:

``` text
제3종일반주거지역
⊂ 일반주거지역
⊂ 주거지역
⊂ 도시지역
```

## 9. STEP 17-21-C-9 --- 실제 SITE 공간조건 판정

C-8에서 추출된 공간조건을 실제 필지와 공간정보 레이어를 교차하여
`TRUE / FALSE / UNKNOWN`으로 판정한다.

핵심 원칙:

``` text
법규명/조문명/검토문구의 문자열 출현
≠
해당 SITE가 실제 공간구역에 포함됨
```

## 10. 공간조건 판정 상태 모델

Resolution: - `TRUE` - `FALSE` - `UNKNOWN`

Query status: - `NOT_CONNECTED` - `NOT_QUERIED` - `QUERY_FAILED` -
`QUERY_SUCCESS`

Confidence: - `NONE` - `MEDIUM` - `HIGH`

안전 원칙:

``` text
조회 실패 → UNKNOWN
source 미연결 → UNKNOWN
데이터 없음 → 자동 FALSE 금지
정상조회 + 유효한 비교근거 + 교차 없음 → FALSE
실제 면적 교차 확인 → TRUE
HTTP 403 자체 → TRUE/FALSE 근거로 사용 금지
기존 정상 HTTP 200 evidence는 후속 접근 실패만으로 폐기하지 않음
```

## 11. SITE Query Context / Parcel

``` text
SITE ID: 11680-10300-0012-0000
시군구코드: 11680
법정동코드: 10300
산여부: 1
본번: 0012
부번: 0000
Parcel Key: 11680-10300-0012-0000
PNU: 1168010300100120000
```

VWorld 대표 좌표:

``` text
X: 127.07539280356858
Y: 37.494197498186885
```

Parcel Polygon dataset:

``` text
LP_PA_CBND_BUBUN
```

대상 PNU와 직접 일치하는 Parcel geometry를 확보하였다.

MapPlan 기준 Parcel:

``` text
geometry: Polygon
area: 120945.65223377591
bounds:
(962201.02522, 1943722.58159, 962711.06096, 1944220.16506)
```

## 12. 지구단위계획 --- TRUE / HIGH

VWorld dataset:

``` text
LT_C_UPISUQ161
```

Parcel Polygon과 지구단위계획 Polygon 실제 교차:

``` text
intersects: True
최대 필지 교차 비율: 0.9998418727573524
```

최종:

``` text
resolution: TRUE
confidence: HIGH
```

## 13. 개발진흥지구 --- FALSE / HIGH

서울시 공식 source:

-   데이터셋: 서울시 용도지구(개발진흥지구) 공간정보
-   공간정보 코드: `UQ129`
-   OpenAPI: `upiSCUq129`
-   SHP CRS: `EPSG:5174`
-   로컬 파일: `UQ129_용도지구(개발진흥지구)_202602.zip`

교차 결과:

``` text
전체 UQ129 Feature: 11
실제 교차 Feature: 0
최대 교차 비율: 0.0
```

최종:

``` text
resolution: FALSE
confidence: HIGH
```

## 14. 개발밀도관리구역 --- UNKNOWN / NONE

토지이음 공식 용어 존재는 확인했으나 아직 다음이 미확정이다.

-   공식 지역·지구 공간코드
-   공식 Polygon geometry source

``` text
resolution: UNKNOWN
confidence: NONE
```

UNKNOWN을 의도적으로 보존한다.

## 15. 자연경관지구 --- FALSE / HIGH

서울시 공식 source:

-   데이터셋: 서울시 용도지구(경관지구) 공간정보
-   공간정보 코드: `UQ121`
-   OpenAPI: `upisCUq121`
-   SHP CRS: `EPSG:5174`
-   SHP 인코딩: `windows-949`
-   로컬 파일: `UQ121_용도지구(경관지구)_202602.zip`

최종 식별 기준:

``` text
DGM_NM == 자연경관지구
```

교차 결과:

``` text
자연경관지구 Feature: 6
실제 면적 교차 Feature: 0
최대 교차 비율: 0.0
```

최종:

``` text
resolution: FALSE
confidence: HIGH
```

## 16. 입체복합구역 --- FALSE / HIGH

### STEP 17-21-C-9-2-6A 계열

토지이음 MapPlan의 UQQ 계열을 조사하여 입체복합구역을 검증하였다.

후속 접근에서 HTTP 403이 발생했으나, 이전 A-6 단계에서 확보한 HTTP 200
정상응답 evidence를 복원하여 판정 근거를 consolidation하였다.

A-6 정상응답 evidence:

``` text
analysis HTTP: 200
analysis parse success: True
analysis layer: AA, AC, BA, CA, CB, DA, DC
```

동일 `AC` layer 양성대조:

``` text
UQQ300
found: True
count: 1
area: 120945.48190180371
```

입체복합구역 대상 `UQQ905`:

``` text
PNU analysis:
found: False
count: 0
area: 0

geometry:
HTTP 200
GeoJSON 정상
Feature 수: 0
```

Evidence consolidation:

``` text
UQQ300 양성대조 유효
+ UQQ905 analysis 음성
+ UQQ905 geometry 음성
= FALSE 판정 가능
```

최종:

``` text
query_status: QUERY_SUCCESS
resolution: FALSE
confidence: HIGH
evidence_state: POSITIVE_CONTROL_VALID_TARGET_DOUBLE_NEGATIVE
```

중요 원칙:

``` text
후속 HTTP 403은 접근 상태 회귀로만 처리
403 자체를 FALSE 근거로 사용하지 않음
후속 403으로 기존 정상 HTTP 200 evidence를 폐기하지 않음
```

결과 파일:

``` text
law_data/output/eum_vertical_mixed_use_zone_evidence_consolidation.json
```

## 17. 도시혁신구역 --- FALSE / HIGH

### STEP 17-21-C-9-2-7A

서울 열린데이터 카탈로그와 토지이음 공식 지도 HTML을 조사하였다.

토지이음에서 다음 직접 연결을 확인:

``` text
도시혁신구역 ↔ UQQ903
candidate MapPlan layer: AC
```

7A 단계에서는 source/code 의미만 검증하고 공간교차 전이므로 `UNKNOWN`을
유지하였다.

### STEP 17-21-C-9-2-7B

MapPlan 실제 공간교차 검증 완료.

MapPlan:

``` text
endpoint: https://www.eum.ne.kr:9003/MapPlan/MapPlan
version: 20260614
EPSG:5179 BBOX:
[962170.4865538419, 1943690.920233938, 962741.8650744666, 1944251.3866923628]
```

양성대조 `UQQ300`:

``` text
layer: AC
found: True
count: 1
area: 120945.48190180371
```

대상 `UQQ903`:

``` text
analysis:
found: False
count: 0
area: 0

geometry:
HTTP 200
GeoJSON 정상
Feature 수: 0
```

Parcel:

``` text
HTTP 200
Feature 수: 1
geometry: Polygon
area: 120945.65223377591
```

교차:

``` text
실제 교차 면적: 0.0
필지 교차 비율: 0.0
면적 교차 존재: False
```

최종:

``` text
query_status: QUERY_SUCCESS
resolution: FALSE
confidence: HIGH
evidence_state: POSITIVE_CONTROL_VALID_TARGET_ANALYSIS_NEGATIVE_NO_AREA_INTERSECTION
```

결과 파일:

``` text
law_data/output/seoul_urban_innovation_zone_mapplan_intersection.json
```

## 18. 복합용도구역 --- FALSE / HIGH

### STEP 17-21-C-9-2-8A

토지이음 공식 지도에서 직접 연결 확인:

``` text
복합용도구역 ↔ UQQ904
layer: AC
```

MapPlan:

``` text
server: https://www.eum.ne.kr:9002/MapPlan
endpoint: https://www.eum.ne.kr:9002/MapPlan/MapPlan
version: 20260614
```

양성대조 `UQQ300`:

``` text
found: True
count: 1
area: 120945.48190180371
```

대상 `UQQ904`:

``` text
analysis:
found: False
count: 0
area: 0

geometry:
HTTP 200
GeoJSON 정상
Feature 수: 0
```

Parcel:

``` text
HTTP 200
Feature 수: 1
geometry: Polygon
area: 120945.65223377591
```

교차:

``` text
조회된 UQQ904 면적: 0.0
실제 교차 면적: 0.0
필지 교차 비율: 0.0
면적 교차 존재: False
```

최종:

``` text
query_status: QUERY_SUCCESS
resolution: FALSE
confidence: HIGH
evidence_state: POSITIVE_CONTROL_VALID_TARGET_ANALYSIS_NEGATIVE_NO_AREA_INTERSECTION
```

결과 파일:

``` text
law_data/output/seoul_mixed_use_zone_mapplan_intersection.json
```

## 19. MapPlan UQQ 계열 검증 패턴

현재까지 다음 코드 의미가 공식 지도 HTML 및 실제 MapPlan 요청으로
검증되었다.

``` text
UQQ903 → 도시혁신구역
UQQ904 → 복합용도구역
UQQ905 → 입체복합구역(도시군계획시설입체복합구역 계열)
```

공통 검증 패턴:

``` text
1. 토지이음 공식 HTML에서 명칭 ↔ 코드 직접 연결 확인
2. MapPlan req=analysis HTTP 200 / JSON 정상 확인
3. 동일 layer AC의 UQQ300 양성대조 확인
4. 대상 UQQ 코드 analysis 확인
5. Parcel geometry 정상조회
6. 대상 UQQ geometry 정상조회
7. Parcel × 대상 geometry 실제 면적교차
8. TRUE는 실제 양성/면적교차 evidence 필요
9. FALSE는 양성대조 정상 + 대상 음성 + 실제 교차 없음 필요
10. HTTP 403/접근 실패 자체는 FALSE 근거로 사용 금지
```

## 20. 현재 공간조건 판정 현황

  조건                   상태      신뢰도   비고
  ---------------------- --------- -------- -------------------------------
  지구단위계획           TRUE      HIGH     Parcel 실제 교차
  개발진흥지구           FALSE     HIGH     서울시 UQ129
  자연경관지구           FALSE     HIGH     서울시 UQ121
  입체복합구역           FALSE     HIGH     UQQ905 evidence consolidation
  도시혁신구역           FALSE     HIGH     UQQ903 MapPlan
  복합용도구역           FALSE     HIGH     UQQ904 MapPlan
  개발밀도관리구역       UNKNOWN   NONE     공식 geometry source 미확정
  수산자원보호구역       UNKNOWN   NONE     미해결
  취락지구               UNKNOWN   NONE     미해결
  산업단지               UNKNOWN   NONE     미해결
  자연공원               UNKNOWN   NONE     미해결
  도시지역편입해제구역   UNKNOWN   NONE     HISTORY 로직 필요

현재 문서에 추적되는 12개 조건 기준:

``` text
TRUE: 1
FALSE: 5
UNKNOWN: 6
```

기존 C-9 최초 요구 10개 외에 후속 법규/공간조건 검토 과정에서
`도시혁신구역`, `복합용도구역`을 추가 추적한다.

## 21. 현재 정확한 중단 위치

``` text
STEP 17
└─ STEP 17-21
   └─ C
      └─ C-9
         └─ C-9-2
            └─ STEP 17-21-C-9-2-8A
```

완료 내용:

``` text
복합용도구역 UQQ904 공식 코드 검증 완료
MapPlan req=analysis 검증 완료
UQQ300 양성대조 정상
UQQ904 analysis 음성
UQQ904 geometry HTTP 200 / Feature 0
Parcel Polygon 정상
Parcel × UQQ904 실제 면적교차 없음
복합용도구역 최종 판정: FALSE / HIGH
```

## 22. 다음 재개 지점

다음 단계:

``` text
STEP 17-21-C-9-2-9
다음 미해결 공간조건 식별 및 실제 공간조회
```

우선 후보:

``` text
수산자원보호구역
취락지구
산업단지
자연공원
도시지역편입해제구역
개발밀도관리구역 재탐색
```

다음 채팅에서는 먼저 **현재 미해결 조건 중 STEP 17-21-C-9-2-9의 정확한
대상 조건을 확정**한 뒤 source 탐색/코드 의미 검증/geometry 교차 순서로
진행한다.

## 23. C-9 잔여 조건 권장 순서

``` text
수산자원보호구역
↓
취락지구
↓
산업단지
↓
자연공원
↓
도시지역편입해제구역
↓
개발밀도관리구역 재탐색
```

`도시지역편입해제구역`은 현재 상태 layer가 아니라 HISTORY 전용 로직이
필요하다.

필요 데이터 예:

-   도시관리계획 결정·변경 이력
-   용도지역 변경 이력
-   용도구역 해제 이력
-   도시지역 편입 이력

## 24. C-9 완료 후 핵심 개발 항목

### 24.1 특례 Clause 적용 엔진

권장 상태:

-   `APPLICABLE`
-   `NOT_APPLICABLE`
-   `CONDITIONAL`
-   `UNKNOWN`

### 24.2 PROJECT 조건 입력 모델

``` text
ProjectProfile
- building_use
- project_type
- housing_type
- public_housing
- rental_housing
- public_open_space
- public_facility_contribution
- donation
- mixed_use
- hanok
- university
- medical_facility
...
```

### 24.3 PROCEDURE 조건 모델

-   도시계획위원회심의
-   시장정비사업심의
-   건축위원회심의
-   공동위원회심의

### 24.4 수치 규정 계산 엔진

-   `ABSOLUTE_LIMIT`
-   `RELATIVE_MULTIPLIER`
-   `ADDITIVE_BONUS`
-   `FORMULA`
-   `MAX_LIMIT`
-   `MIN_LIMIT`

### 24.5 Formula Parser

법규 내 산식을 실제 계산 가능한 객체로 구조화한다.

### 24.6 기본 건폐율·용적률 결정 엔진

``` text
Base Rule
↓
Local Ordinance
↓
Restriction
↓
Relaxation
↓
Special Rule
↓
Final Limit
```

### 24.7 법규 우선순위 / 중첩 규정 엔진

-   법률
-   시행령
-   조례
-   도시관리계획 / 지구단위계획
-   개별 특별법

### 24.8 지구단위계획 결정도서 자동분석

현재 SITE는 지구단위계획구역 TRUE이다.

주요 추출 대상:

-   건폐율
-   용적률
-   최고높이
-   건축선
-   벽면선
-   허용용도 / 불허용도
-   공동개발
-   특별계획구역
-   공공기여
-   계획지침

권장 모듈:

``` text
DistrictUnitPlanDocumentResolver
```

## 25. 공간정보 공통 엔진 리팩터링

권장 구조:

``` text
law_data/spatial/
    parcel.py
    layer_loader.py
    crs.py
    intersection.py
    source_registry.py
    semantic_filter.py
    resolver.py
    mapplan.py
```

장기 목표:

``` python
resolve_condition("자연경관지구", parcel)
resolve_condition("복합용도구역", parcel)
```

MapPlan UQQ 계열 공통화 시 고려 항목:

-   EUM session 초기화
-   gisServer 동적 복원
-   version 동적 복원
-   req=analysis
-   positive control
-   Parcel geometry
-   target geometry
-   intersection
-   evidence consolidation
-   HTTP 403 / 접근회귀 처리

## 26. Spatial Layer Registry

현재 검증 항목 예:

``` text
UQ121 → 경관지구
UQ129 → 개발진흥지구
LT_C_UPISUQ161 → 지구단위계획구역
LP_PA_CBND_BUBUN → Parcel Polygon
UQQ903 → 도시혁신구역
UQQ904 → 복합용도구역
UQQ905 → 입체복합구역 계열
```

각 registry 항목:

-   provider
-   dataset name
-   official code
-   API service / endpoint
-   file pattern
-   CRS
-   encoding
-   semantic filter
-   geometry type
-   update cycle / version
-   positive control
-   confidence / verification status

## 27. 최종 SiteAnalysis 객체

``` text
SiteAnalysis

site
parcel

land
building

zoning
spatial_conditions
site_history

base_rules
special_rules

project_conditions
procedure_conditions

formula_results
final_constraints

evidence
sources
```

## 28. AI 설명 계층

``` text
공공 데이터 / 법규 / 공간정보
↓
Parser
↓
Rule Engine
↓
판정 결과
↓
AI 설명
↓
보고서 / UI
```

AI가 직접 법적 판정을 생성하는 것이 아니라 규칙 엔진의 구조화된 결과를
설명한다.

## 29. 현재 전체 개발 단계

``` text
PHASE 1  기초 SITE / API                     완료
PHASE 2  실제 토지·건축물 데이터             완료
PHASE 3  법령 API / 법규 수집                완료
PHASE 4  법규 Clause Parser                  핵심 완료
PHASE 5  용도지역 관련성 판정                 완료
PHASE 6  SITE 공간조건 판정                   진행 중
PHASE 7  SITE_HISTORY 판정                    예정
PHASE 8  PROJECT 조건 모델                    예정
PHASE 9  PROCEDURE 조건 모델                  예정
PHASE 10 특례 적용 가능성 엔진                예정
PHASE 11 기본 건폐율·용적률 결정              예정
PHASE 12 법규 우선순위 / 중첩 규정 처리        예정
PHASE 13 Formula / 수치 계산 엔진             예정
PHASE 14 지구단위계획 결정도서 자동분석        예정
PHASE 15 최종 SITE 규제값 계산                예정
PHASE 16 대지분석 결과 객체 통합               예정
PHASE 17 AI 설명 / 보고서 생성                예정
PHASE 18 서비스 UI / 자동화 API               예정
```

## 30. 현재 프로젝트 핵심 안전 원칙

``` text
문자열 존재 ≠ SITE 해당
HTTP 200 ≠ 조회 성공
QUERY_SUCCESS ≠ dataset 의미 검증
dataset의 일부 Feature 이름 일치 ≠ dataset 의미
geometry 미확보 ≠ FALSE
조회 실패 ≠ FALSE
HTTP 403 ≠ FALSE
후속 접근 실패 ≠ 기존 정상 evidence 무효
UNKNOWN은 오류가 아니라 정상 상태
TRUE는 실제 근거가 필요
FALSE도 정상조회와 비교 근거가 필요
MapPlan FALSE 판정은 가능한 경우 양성대조를 요구
대표 Point 포함 판정보다 Parcel Polygon intersection을 우선
코드 의미는 공식 source에서 명칭과 직접 연결 검증 후 사용
```

## 31. 체크포인트

``` text
PROJECT:
AI 대지분석 자동화 시스템

CURRENT STEP:
STEP 17-21-C-9-2-8A

STATUS:
복합용도구역 공간조건 판정 완료

SITE:
서울특별시 강남구 개포동 12번지

PNU:
1168010300100120000

RESOLVED:
- 지구단위계획: TRUE / HIGH
- 개발진흥지구: FALSE / HIGH
- 자연경관지구: FALSE / HIGH
- 입체복합구역: FALSE / HIGH
- 도시혁신구역: FALSE / HIGH
- 복합용도구역: FALSE / HIGH

UNRESOLVED:
- 개발밀도관리구역: UNKNOWN
- 수산자원보호구역: UNKNOWN
- 취락지구: UNKNOWN
- 산업단지: UNKNOWN
- 자연공원: UNKNOWN
- 도시지역편입해제구역: UNKNOWN

NEXT STEP:
STEP 17-21-C-9-2-9
다음 미해결 공간조건 식별 및 실제 공간조회
```

## 32. 다음 채팅 시작용 핸드오프

``` text
AI 대지분석 자동화 시스템 개발을 계속한다.

기준 문서:
PROJECT_STATUS.md

현재 완료 단계:
STEP 17-21-C-9-2-8A

현재 SITE:
서울특별시 강남구 개포동 12번지
SITE ID: 11680-10300-0012-0000
PNU: 1168010300100120000
용도지역: 제3종일반주거지역

현재 공간조건:
- 지구단위계획: TRUE / HIGH
- 개발진흥지구: FALSE / HIGH
- 자연경관지구: FALSE / HIGH
- 입체복합구역: FALSE / HIGH
- 도시혁신구역: FALSE / HIGH
- 복합용도구역: FALSE / HIGH
- 개발밀도관리구역: UNKNOWN / NONE
- 수산자원보호구역: UNKNOWN / NONE
- 취락지구: UNKNOWN / NONE
- 산업단지: UNKNOWN / NONE
- 자연공원: UNKNOWN / NONE
- 도시지역편입해제구역: UNKNOWN / NONE

직전 완료:
STEP 17-21-C-9-2-8A
복합용도구역 UQQ904 MapPlan 실제 공간교차 검증
최종 판정: FALSE / HIGH

MapPlan 공통 검증 원칙:
- 공식 HTML에서 명칭 ↔ 코드 직접 연결 확인
- req=analysis 정상응답 확인
- 동일 요청체계의 양성대조 확인
- 대상 code analysis 확인
- Parcel geometry 정상 확보
- 대상 geometry 정상조회
- 실제 Parcel Polygon intersection 수행
- TRUE는 실제 양성/면적교차 evidence 필요
- FALSE는 정상조회 + 유효한 비교근거 + 대상 음성 + 교차 없음 필요
- HTTP 403/접근 실패 자체를 FALSE 근거로 사용하지 않음
- 후속 접근 실패만으로 기존 정상 HTTP 200 evidence를 폐기하지 않음

다음 단계:
STEP 17-21-C-9-2-9

목표:
현재 미해결 공간조건 중 다음 대상을 확정하고
공식 source → 관리코드/semantic 검증 → geometry 확보
→ Parcel intersection → TRUE/FALSE/UNKNOWN 판정 순으로 진행한다.

우선 검토 순서:
수산자원보호구역
→ 취락지구
→ 산업단지
→ 자연공원
→ 도시지역편입해제구역
→ 개발밀도관리구역 재탐색

기존 안전 원칙:
- 실제 공간교차 없이는 TRUE 확정 금지
- 정상조회 및 비교근거 없이 FALSE 확정 금지
- source/geometry 미확정은 UNKNOWN 유지
- 문자열 출현만으로 SITE 조건 판정 금지
- dataset 일부 Feature 명칭만으로 dataset 의미 확정 금지
- Point보다 Parcel Polygon intersection 우선
- UNKNOWN은 정상 상태로 보존

PROJECT_STATUS.md를 기준 상태로 삼아 바로 STEP 17-21-C-9-2-9부터 진행한다.
```

## 33. Git 체크포인트 권장

이번 체크포인트에서 최소 저장 대상:

``` text
PROJECT_STATUS.md
law_data/seoul_urban_innovation_zone_source_probe_test.py
law_data/seoul_urban_innovation_zone_mapplan_intersection_test.py
law_data/seoul_mixed_use_zone_mapplan_intersection_test.py
law_data/output/seoul_urban_innovation_zone_source_probe.json
law_data/output/seoul_urban_innovation_zone_mapplan_intersection.json
law_data/output/seoul_mixed_use_zone_mapplan_intersection.json
law_data/output/eum_vertical_mixed_use_zone_evidence_consolidation.json
```

실제 저장 전에는 `git status`로 변경 파일을 확인하고, 프로젝트 정책상
output JSON을 Git에서 추적하지 않는 경우에는 해당 JSON을 강제로 add하지
않는다.

권장 commit message:

``` text
Complete C-9 MapPlan zone validations through STEP 17-21-C-9-2-8A
```
