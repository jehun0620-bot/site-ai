# AI 대지분석 자동화 시스템 — PROJECT STATUS

_Last updated: 2026-08-19_

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

핵심 원칙은 다음과 같다.

> **Rule Engine이 판정하고, AI는 설명한다.**

## 2. 현재 테스트 SITE

- 주소: 서울특별시 강남구 개포동 12번지
- SITE ID: `11680-10300-0012-0000`
- PNU: `1168010300100120000`
- 시군구코드: `11680`
- 법정동코드: `10300`
- 본번: `0012`
- 부번: `0000`
- 산여부 코드: `1`
- 용도지역: 제3종일반주거지역
- 대표 좌표:
  - X: `127.07539280356858`
  - Y: `37.494197498186885`

## 3. 전체 아키텍처

```text
SITE
│
├─ 주소 / SITE ID / PNU / 좌표 / Parcel Polygon
│
├─ 토지정보
├─ 건축물정보
├─ 용도지역
├─ 용도지구
├─ 용도구역
├─ 도시계획시설
│
└─ 법규 분석
    │
    ├─ 법률
    ├─ 시행령
    ├─ 서울시 조례
    │
    ├─ 일반 규정
    └─ 특례 규정
        │
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
= 실제 적용 가능성
```

## 4. STEP 1 ~ STEP 15

초기 시스템 골격과 데이터 흐름 구축.

완료한 주요 항목:

- 주소 기반 SITE 생성
- SITE ID 생성
- 시군구 / 법정동 / 본번 / 부번 구조화
- 외부 API 연결 기반 구축
- `.env` 기반 API Key 관리
- SITE Builder 구축
- 외부 API 응답을 내부 SITE 데이터 구조로 변환
- 테스트 데이터 중심 구조에서 실제 공공 API 기반 구조로 전환

환경변수 이름 불일치 문제도 수정하여 실제 API Key 로딩을 정상화하였다.

## 5. STEP 16 — 실제 토지/건축물 데이터 연결

가상 데이터에서 실제 필지 데이터 기반으로 전환.

대표 테스트 SITE:

```text
서울특별시 강남구 개포동 12번지
SITE ID: 11680-10300-0012-0000
PNU: 1168010300100120000
용도지역: 제3종일반주거지역
```

실제 건축물 API에서 총 34건을 정상 조회하였다.

STEP 16의 핵심 성과:

```text
가상 SITE
→ 실제 공공 API 기반 SITE
```

## 6. STEP 17 — 법규 자동분석 엔진

STEP 17의 목표는 다음과 같다.

> 특정 SITE에 실제 적용 가능성이 있는 법규를 자동으로 추출·구조화·판정한다.

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

## 7. 특례 조건 모델

특례 clause의 조건을 다음 네 계층으로 분리하였다.

### SITE

현재 필지가 실제로 특정 공간구역에 속하는지 여부.

예:

- 지구단위계획
- 개발진흥지구
- 개발밀도관리구역
- 자연경관지구
- 취락지구
- 수산자원보호구역
- 입체복합구역
- 산업단지
- 자연공원

### SITE_HISTORY

현재 상태가 아니라 과거의 용도·시설·도시계획 변경 이력이 필요한 조건.

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

### PROCEDURE

심의 또는 행정절차에 관한 조건.

예:

- 도시계획위원회심의
- 시장정비사업심의

## 8. STEP 17-21-C-8 — 특례 Clause Parser

법령 원문을 다음 단계로 세분화하는 파서를 개발하였다.

```text
조
↓
항
↓
호
↓
목
↓
세부 clause
```

### C-8-8 최종 검증 완료

다음 주요 오류를 해결하였다.

- 개정일자 조각 제거
- 도시지역 외 규정 배제
- 상업지역 → 주거지역 오인 방지
- 공업지역 → 주거지역 오인 방지
- 녹지지역 → 주거지역 오인 방지
- 용도지역 그룹 substring 중복 제거
- 도시지역(녹지지역만) 한정 처리
- 무공백 후속 호 경계 분리
- DIRECT 규정 내부 다중 목 잔존 제거
- 문장 종결 `다.`를 `다목`으로 오인하는 문제 해결
- 제46조 ⑮항 제3종일반주거지역 제외
- 시장정비사업 제3종일반주거지역 60% 나목 분리
- 시장정비사업 상업지역 다목 제외
- 학교이적지 제3종일반주거지역 200% 바목 분리
- 학교이적지 타 용도지역 목 제외

최종 결과:

```text
C-8 파서 최종 검증: ALL PASS
```

## 9. 용도지역 관련성 판정

Clause를 다음 상태로 분류한다.

### DIRECT

현재 SITE의 용도지역이 직접 명시된 규정.

예:

```text
제3종일반주거지역: 300퍼센트 이하
```

### GROUP

현재 용도지역이 상위 그룹에 포함되는 규정.

예:

```text
주거지역: 500퍼센트 이하
```

현재 SITE의 계층 예:

```text
제3종일반주거지역
⊂ 일반주거지역
⊂ 주거지역
⊂ 도시지역
```

### UNSPECIFIED

용도지역이 명확히 특정되지 않은 규정.

### EXCLUDED

다른 용도지역에만 적용되는 규정.

## 10. STEP 17-21-C-9 — 실제 SITE 공간조건 판정

C-8에서 추출된 공간조건을 실제 필지와 공간정보 레이어를 교차하여 TRUE / FALSE / UNKNOWN으로 판정한다.

### 핵심 의미 보정

초기에는 기존 SITE snapshot 내부에 `지구단위계획`, `자연경관지구` 등의 문자열이 있으면 TRUE로 보려는 문제가 있었다.

이를 C-9-1A에서 수정하였다.

핵심 원칙:

```text
법규명/조문명/검토문구의 문자열 출현
≠
해당 SITE가 실제 공간구역에 포함됨
```

실제 공간교차가 없으면 UNKNOWN으로 유지한다.

## 11. 공간조건 판정 상태 모델

Resolution:

- `TRUE`
- `FALSE`
- `UNKNOWN`

Query status:

- `NOT_CONNECTED`
- `NOT_QUERIED`
- `QUERY_FAILED`
- `QUERY_SUCCESS`

Confidence:

- `NONE`
- `MEDIUM`
- `HIGH`

안전 원칙:

```text
조회 실패 → UNKNOWN
source 미연결 → UNKNOWN
데이터 없음 → 자동 FALSE 금지
정상 전체 조회 + 교차 없음 → FALSE
실제 면적 교차 확인 → TRUE
```

## 12. C-9에서 요구된 SITE 조건 10개

### URBAN_PLANNING_ZONE

- 개발밀도관리구역
- 개발진흥지구
- 수산자원보호구역
- 입체복합구역
- 자연경관지구
- 지구단위계획
- 취락지구

### THEMATIC_LAYER

- 산업단지
- 자연공원

### HISTORY

- 도시지역편입해제구역

## 13. SITE Query Context 정규화

공간조회 공통 입력을 다음과 같이 정규화하였다.

```text
SITE ID: 11680-10300-0012-0000
시군구코드: 11680
법정동코드: 10300
산여부: 1
본번: 0012
부번: 0000
Parcel Key: 11680-10300-0012-0000
PNU: 1168010300100120000
```

검증:

- Parcel Key 생성 PASS
- 코드 자릿수 PASS
- PNU 19자리 PASS
- 개포동 12번지 기준값 PASS

## 14. VWorld 연동

### 주소 검색

VWorld 주소 검색 API를 통해 대표 좌표 확보:

```text
X: 127.07539280356858
Y: 37.494197498186885
```

### 필지 Polygon

VWorld Data API의 필지 Polygon dataset 후보 탐색 결과:

```text
LP_PA_CBND_BUBUN
```

대상 PNU와 직접 일치하는 MultiPolygon Feature를 확인하였다.

## 15. 지구단위계획 — 최종 TRUE

VWorld Data API에서 검증된 dataset:

```text
LT_C_UPISUQ161
```

대표점이 지구단위계획 geometry 내부에 포함됨을 확인하였다.

이후 대상 PNU Parcel Polygon과 지구단위계획 Polygon을 실제 교차하였다.

결과:

```text
intersects: True
최대 필지 교차 비율: 0.9998418727573524
```

최종 상태:

```text
지구단위계획
resolution: TRUE
confidence: HIGH
```

## 16. 개발진흥지구 — 최종 FALSE

초기 VWorld dataset 코드 추측 탐색 과정에서 `LT_C_UPISUQ161` 내부 Feature 이름에 개발진흥지구 문자열이 포함되어 false-positive 가능성이 확인되었다.

의미 보정 후 다음 원칙을 확립하였다.

```text
dataset 내부 일부 Feature 이름에 특정 단어 존재
≠
그 dataset 자체가 해당 용도지구 전용 layer
```

서울시 공식 source를 확정하였다.

- 데이터셋: 서울시 용도지구(개발진흥지구) 공간정보
- 공간정보 코드: `UQ129`
- OpenAPI: `upiSCUq129`
- SHP CRS: `EPSG:5174`
- 로컬 파일: `UQ129_용도지구(개발진흥지구)_202602.zip`

Parcel Polygon × UQ129 Polygon 교차 결과:

```text
전체 UQ129 Feature: 11
실제 교차 Feature: 0
최대 교차 비율: 0.0
```

최종 상태:

```text
개발진흥지구
resolution: FALSE
confidence: HIGH
```

## 17. 개발밀도관리구역 — UNKNOWN 유지

서울시 공식 공간정보 목록 및 열린데이터 카탈로그에서 `개발밀도관리구역` 전용 공간 source를 확정하지 못하였다.

국가 단위 source로 확장하여 토지이음 공식 용어사전을 탐색하였다.

토지이음 pagination 탐색을 통해 공식 용어 존재는 확인하였다.

```text
개발밀도관리구역
```

그러나 아직 다음은 미확정이다.

- 공식 지역·지구 공간코드
- 공식 Polygon geometry source

따라서:

```text
개발밀도관리구역
resolution: UNKNOWN
confidence: NONE
```

UNKNOWN을 의도적으로 보존한다.

## 18. 자연경관지구 — 최종 FALSE

서울시 공식 카탈로그 source:

- 데이터셋: 서울시 용도지구(경관지구) 공간정보
- 공간정보 코드: `UQ121`
- OpenAPI: `upisCUq121`
- SHP CRS: `EPSG:5174`
- SHP 인코딩: `windows-949`
- 로컬 파일: `UQ121_용도지구(경관지구)_202602.zip`

OpenAPI에서 자연경관지구가 명시된 Row를 확인하였다.

```text
LBL_NM = 자연경관지구
```

OpenAPI ↔ SHP schema 대응을 검증하였다.

```text
PRESENT_SN   -> STUT_FIG_MNG_NO
LCLAS_CL     -> FIG_LCLSF_CD
MLSFC_CL     -> FIG_MCLSF_CD
SCLAS_CL     -> FIG_SCLSF_CD
ATRB_SE      -> FIG_ATRB_CD
WTNNC_SN     -> FIG_RPT_MNG_CD
NTFC_SN      -> DCSN_ANCMNT_MNG_CD
DGM_NM       -> LBL_NM
DGM_AR       -> AREA
DGM_LT       -> LEN
SIGNGU_SE    -> SGG_CD
DRAWING_NO   -> FLRPLN_NO
CREATE_DAT   -> STUT_FIG_CRT_DT
```

중요한 검증:

```text
ATRB_SE = UQF110 Feature: 20개
DGM_NM = 자연경관지구 Feature: 6개
```

따라서 `UQF110`만으로 자연경관지구를 판정하지 않는다.

최종 식별 기준:

```text
DGM_NM == 자연경관지구
```

Parcel Polygon × 자연경관지구 Polygon 교차 결과:

```text
자연경관지구 Feature: 6
실제 면적 교차 Feature: 0
최대 교차 비율: 0.0
```

최종 상태:

```text
자연경관지구
resolution: FALSE
confidence: HIGH
```

## 19. 현재 공간조건 판정 현황

| 조건 | 상태 | 신뢰도 |
|---|---|---|
| 지구단위계획 | TRUE | HIGH |
| 개발진흥지구 | FALSE | HIGH |
| 자연경관지구 | FALSE | HIGH |
| 개발밀도관리구역 | UNKNOWN | NONE |
| 입체복합구역 | UNKNOWN | NONE |
| 수산자원보호구역 | UNKNOWN | NONE |
| 취락지구 | UNKNOWN | NONE |
| 산업단지 | UNKNOWN | NONE |
| 자연공원 | UNKNOWN | NONE |
| 도시지역편입해제구역 | UNKNOWN | NONE |

현재 요약:

```text
TRUE: 1
FALSE: 2
UNKNOWN: 7
```

## 20. 현재 정확한 중단 위치

```text
STEP 17
└─ STEP 17-21
   └─ C
      └─ C-9
         └─ C-9-2
            └─ STEP 17-21-C-9-2-5C-2
```

완료 내용:

```text
자연경관지구 Parcel Polygon × 서울시 UQ121 Polygon 실제 공간교차 검증 완료
자연경관지구 최종 판정: FALSE / HIGH
```

## 21. 다음 재개 지점

다음 단계는 정확히 다음이다.

```text
STEP 17-21-C-9-2-6A
입체복합구역 공식 Source 탐색
```

이 단계에서 해야 할 일:

1. 서울시 공식 공간정보 카탈로그 탐색
2. `입체복합구역` 전용 dataset 또는 parent layer 식별
3. OpenAPI / 공간파일 schema 검증
4. 명칭 또는 공식 분류코드 검증
5. SHP/GeoJSON geometry 확보
6. 대상 PNU Parcel Polygon과 intersection
7. 정상 전체 layer 조회 + 교차 없음 → FALSE
8. 실제 면적 교차 → TRUE
9. source 또는 geometry 미확정 → UNKNOWN

## 22. C-9 이후 남은 공간조건 권장 순서

```text
입체복합구역
↓
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

`도시지역편입해제구역`은 현재 상태 layer가 아니라 HISTORY 전용 로직이 필요하다.

필요 데이터 예:

- 도시관리계획 결정·변경 이력
- 용도지역 변경 이력
- 용도구역 해제 이력
- 도시지역 편입 이력

## 23. C-9 완료 후 개발해야 할 핵심 기능

### 23.1 특례 Clause 적용 엔진

최종 clause 상태 모델 권장:

- `APPLICABLE`
- `NOT_APPLICABLE`
- `CONDITIONAL`
- `UNKNOWN`

예:

```text
지구단위계획 = TRUE
공공시설제공 = UNKNOWN
→ CONDITIONAL
```

```text
개발진흥지구 필요
SITE 개발진흥지구 = FALSE
→ NOT_APPLICABLE
```

### 23.2 PROJECT 조건 입력 모델

예시:

```text
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

### 23.3 PROCEDURE 조건 모델

예:

- 도시계획위원회심의
- 시장정비사업심의
- 건축위원회심의
- 공동위원회심의

최종 결과는 단순 TRUE/FALSE가 아니라 조건부 설명이 가능해야 한다.

### 23.4 수치 규정 계산 엔진

다음 타입을 구분해야 한다.

- `ABSOLUTE_LIMIT`
- `RELATIVE_MULTIPLIER`
- `ADDITIVE_BONUS`
- `FORMULA`
- `MAX_LIMIT`
- `MIN_LIMIT`

### 23.5 Formula Parser

법규 내 산식을 실제 계산 가능한 객체로 구조화한다.

### 23.6 기본 건폐율·용적률 결정 엔진

```text
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

### 23.7 법규 우선순위 / 중첩 규정 엔진

- 법률
- 시행령
- 조례
- 도시관리계획 / 지구단위계획
- 개별 특별법

### 23.8 지구단위계획 결정도서 자동분석

현재 SITE는 지구단위계획구역 TRUE이다.

주요 추출 대상:

- 건폐율
- 용적률
- 최고높이
- 건축선
- 벽면선
- 허용용도 / 불허용도
- 공동개발
- 특별계획구역
- 공공기여
- 계획지침

별도 모듈 권장:

```text
DistrictUnitPlanDocumentResolver
```

## 24. 공간정보 공통 엔진 리팩터링

현재 여러 테스트 파일에서 반복되는 로직을 공통 모듈화한다.

권장 구조:

```text
law_data/spatial/
    parcel.py
    layer_loader.py
    crs.py
    intersection.py
    source_registry.py
    semantic_filter.py
    resolver.py
```

장기적으로:

```python
resolve_condition("자연경관지구", parcel)
```

형태로 호출 가능하도록 한다.

## 25. Spatial Layer Registry

예:

```text
UQ121 → 경관지구
UQ129 → 개발진흥지구
LT_C_UPISUQ161 → 지구단위계획구역
LP_PA_CBND_BUBUN → Parcel Polygon
```

각 registry 항목에는 다음 정보가 필요하다.

- provider
- dataset name
- official code
- API service
- file pattern
- CRS
- encoding
- semantic filter
- geometry type
- update cycle
- confidence / verification status

## 26. 최종 SiteAnalysis 객체

```text
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

## 27. 최종 출력 목표

주소 하나를 입력하면 SITE 기본정보, 용도지역·지구·구역, 기본 건폐율·용적률·높이, 적용 가능한 특례·조건부 특례·적용 제외 규정까지 자동 생성한다.

## 28. AI 설명 계층

```text
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

AI가 직접 법적 판정을 생성하는 것이 아니라 규칙 엔진의 구조화된 결과를 설명한다.

## 29. 현재 전체 개발 단계

```text
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

```text
문자열 존재 ≠ SITE 해당
HTTP 200 ≠ 조회 성공
QUERY_SUCCESS ≠ dataset 의미 검증
dataset의 일부 Feature 이름 일치 ≠ dataset 의미
geometry 미확보 ≠ FALSE
조회 실패 ≠ FALSE
UNKNOWN은 오류가 아니라 정상 상태
TRUE는 실제 근거가 필요
FALSE도 정상 전체 조회와 비교 근거가 필요
대표 Point 포함 판정보다 Parcel Polygon intersection을 우선
```

## 31. 체크포인트

```text
PROJECT:
AI 대지분석 자동화 시스템

CURRENT STEP:
STEP 17-21-C-9-2-5C-2

STATUS:
자연경관지구 공간조건 판정 완료

SITE:
서울특별시 강남구 개포동 12번지

PNU:
1168010300100120000

RESOLVED:
- 지구단위계획: TRUE / HIGH
- 개발진흥지구: FALSE / HIGH
- 자연경관지구: FALSE / HIGH

UNRESOLVED:
- 개발밀도관리구역: UNKNOWN
- 입체복합구역: UNKNOWN
- 수산자원보호구역: UNKNOWN
- 취락지구: UNKNOWN
- 산업단지: UNKNOWN
- 자연공원: UNKNOWN
- 도시지역편입해제구역: UNKNOWN

NEXT STEP:
STEP 17-21-C-9-2-6A
입체복합구역 공식 Source 탐색
```

## 32. 다음 채팅 시작용 핸드오프

```text
AI 대지분석 자동화 시스템 개발을 계속한다.

기준 문서:
PROJECT_STATUS.md

현재 완료 단계:
STEP 17-21-C-9-2-5C-2

현재 공간조건:
- 지구단위계획: TRUE / HIGH
- 개발진흥지구: FALSE / HIGH
- 자연경관지구: FALSE / HIGH
- 개발밀도관리구역: UNKNOWN
- 입체복합구역: UNKNOWN
- 수산자원보호구역: UNKNOWN
- 취락지구: UNKNOWN
- 산업단지: UNKNOWN
- 자연공원: UNKNOWN
- 도시지역편입해제구역: UNKNOWN

다음 단계:
STEP 17-21-C-9-2-6A
입체복합구역 공식 Source 탐색

기존 안전 원칙:
- 실제 공간교차 없이는 TRUE 확정 금지
- 정상 전체 레이어 조회 없이 FALSE 확정 금지
- source/geometry 미확정은 UNKNOWN 유지
- 문자열 출현만으로 SITE 조건 판정 금지
- Point보다 Parcel Polygon intersection 우선
```
