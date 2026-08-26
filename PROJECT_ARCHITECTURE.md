# AI 대지분석 자동화 시스템 — PROJECT ARCHITECTURE

문서 목적
======================================================================

이 문서는 `PROJECT_STATUS.md`와 역할이 다르다.

- `PROJECT_STATUS.md`
  - 현재 어디까지 개발되었는지 기록한다.
  - 최근 테스트 결과, 체크포인트, 다음 작업을 기록한다.
  - 단기 실행 상태 문서다.

- `PROJECT_ARCHITECTURE.md`
  - 프로젝트가 시작부터 최종 완성까지 어떤 구조로 발전해야 하는지 정의한다.
  - 시스템의 레이어, 책임, 데이터 흐름, 판정 원칙, 완료 기준을 정의한다.
  - 장기 설계 기준선이다.
  - 실제 개발 결과에 따라 버전업하며 수정한다.

이 문서는 현재 구현을 절대적인 최종안으로 고정하지 않는다.
새로운 공식 데이터, 법적 구조, 제품 요구사항, 성능 요구사항이 확인되면
아키텍처를 수정하되, 변경 이유를 명시하고 기존 안전 원칙을 훼손하지 않는다.

최초 작성 기준일: 2026-08-26
Architecture Baseline: v1.0


1. 프로젝트 최종 목표
======================================================================

사용자가 주소 또는 필지를 입력하면 시스템이 해당 SITE에 대해
공식 데이터와 법적 근거를 추적하여 다음을 자동 생성한다.

1. 정확한 필지 identity
2. 토지/건축물 현황
3. 적용되는 용도지역·지구·구역 및 기타 규제
4. 각 규제의 TRUE / FALSE / UNKNOWN
5. 각 판정의 공식 출처와 provenance
6. 적용 법률·시행령·시행규칙·조례·고시·별표
7. 건폐율·용적률·높이·주차·이격·조경 등 계산 가능한 규제값
8. 조건부 규제 및 추가 입력이 필요한 PROJECT 조건
9. 규제 간 충돌, 중첩, 우선순위
10. AI가 설명한 최종 대지분석 보고서
11. 모든 결과의 citation / reverse verification

최종 제품의 핵심 질문은 다음과 같다.

> 이 필지에는 정확히 어떤 규제가 적용되고,
> 그 사실은 어느 공식 데이터·공간정보·지정고시·법령에서 확정되며,
> 따라서 무엇을 얼마나 지을 수 있는가?


2. 최상위 설계 철학
======================================================================

시스템은 다음 순서를 지킨다.

```text
OFFICIAL FACT
    ↓
SITE FACT
    ↓
REGULATION RESOLUTION
    ↓
LEGAL RULE
    ↓
DETERMINISTIC ENGINE
    ↓
AI ANALYSIS
    ↓
VERIFICATION
```

AI가 공식 사실을 추측하거나 규제 존재 여부를 임의 생성하지 않는다.
AI는 확정된 데이터와 법적 근거 위에서 설명·쟁점 탐지·추론을 수행한다.

핵심 원칙:

- 검색 결과 ≠ 법적 사실
- 문서 발견 ≠ 규제 TRUE
- endpoint 발견 ≠ 문서 검증
- 고시 발견 ≠ 현재 유효
- 지역명 일치 ≠ 권한 있는 발행기관
- point 포함 ≠ parcel 포함
- source 미발견 ≠ FALSE
- 조건 미충족 상태에서 수치 확정 금지
- LLM 합의 ≠ source verification


3. 전체 시스템 아키텍처
======================================================================

```text
┌─────────────────────────────────────────────────────────────┐
│ LAYER 0 — USER / PROJECT INPUT                              │
│ 주소, PNU, 프로젝트 용도, 규모, 사업조건                    │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1 — PARCEL IDENTITY & OFFICIAL LAND DATA              │
│ 주소 정규화 / 법정동 / PNU / 지번 / 토지 / 건축물대장       │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2 — SITE FACT MODEL                                   │
│ Parcel Geometry / Zoning / Building / Runtime Conditions    │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3 — REGULATION RESOLUTION                             │
│ 표준코드 / source policy / authority / notice / spatial     │
│ TRUE / FALSE / UNKNOWN                                      │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4 — LEGAL KNOWLEDGE                                   │
│ 법률 → 시행령 → 시행규칙 → 조례 → 고시 → 별표 → 지침        │
│ version history / delegation chain                          │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 5 — RULE NORMALIZATION                                │
│ 조문 → predicate / condition / effect / numeric / source    │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 6 — DETERMINISTIC EVALUATION                          │
│ applicability / BCR / FAR / height / parking / setback      │
│ incentive / relaxation / ceiling / stacking                 │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 7 — RETRIEVAL & LEGAL CONTEXT                         │
│ Rule / BM25 / Vector / Parent-Child / Delegation / Reranker │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 8 — AI ANALYSIS                                       │
│ 쟁점 발견 / 설명 / 대안 / 충돌 탐지 / 보고서                │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 9 — VERIFICATION & PROVENANCE                         │
│ citation reverse check / contradiction / confidence         │
└────────────────────────────┬────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 10 — PRODUCT / API / REPORT                            │
│ FastAPI / Web UI / GIS Map / PDF Report / Batch Analysis    │
└─────────────────────────────────────────────────────────────┘
```


4. LAYER 0 — USER / PROJECT INPUT
======================================================================

목표:

SITE 자체의 사실과 사용자가 계획하는 PROJECT 조건을 분리한다.

SITE INPUT 예:

- 주소
- PNU
- 지번

PROJECT INPUT 예:

- 건축물 용도
- 층수
- 연면적
- 세대수
- 공개공지 제공 여부
- 재해예방시설 설치 여부
- 인센티브 선택

원칙:

```text
SITE CONDITION != PROJECT CONDITION
```

SITE에 존재하지 않는 프로젝트 조건을 자동으로 TRUE 처리하지 않는다.

완료 기준:

- SITE 입력 schema 확정
- PROJECT 입력 schema 확정
- optional / required 조건 분리
- API validation 적용


5. LAYER 1 — PARCEL IDENTITY & OFFICIAL LAND DATA
======================================================================

목표:

모든 후속 판정이 동일한 실제 필지를 바라보도록 parcel identity를 확정한다.

주요 데이터:

- 주소
- 법정동코드
- 시군구코드
- 본번/부번
- PNU
- 건축물대장
- 토지특성
- 용도지역/지구/구역

핵심 흐름:

```text
주소
→ 법정동 identity
→ PNU
→ official land API
→ building API
→ SITE identity
```

필수 불변조건:

- 다른 PNU의 snapshot 재사용 금지
- API key는 source code에 저장 금지
- upstream API 오류와 규제 FALSE를 구분
- raw API data와 normalized SITE data를 분리

현재 구현 기반:

- Building HUB API
- VWorld 기반 토지/공간정보
- Site / Building model
- FastAPI service orchestration


6. LAYER 2 — SITE FACT MODEL
======================================================================

목표:

공식 source에서 수집된 정보를 downstream rule engine이 사용할 수 있는
일관된 SITE FACT로 변환한다.

SITE FACT 예:

```json
{
  "pnu": "...",
  "parcel_geometry": "...",
  "zone": "...",
  "building_count": 0,
  "runtime_conditions": {
    "지구단위계획": {
      "state": "TRUE",
      "confidence": "HIGH",
      "source": "RUNTIME_SPATIAL_CONDITION"
    }
  }
}
```

Runtime Spatial Condition 원칙:

- POINT 단독 TRUE 확정 금지
- Parcel Polygon / MultiPolygon 확보
- target PNU 직접 검증
- CRS 명시
- parcel geometry와 regulation geometry `intersects()` 검증
- spatial dataset 미응답과 FALSE 구분

공통 evaluator registry를 사용하며 condition별 builder 하드코딩은 최소화한다.


7. LAYER 3 — REGULATION RESOLUTION
======================================================================

이 프로젝트의 핵심 차별화 계층이다.

목표:

각 규제 표준코드에 대해 해당 SITE가 실제로 규제를 받는지
공식 evidence를 조합하여 TRUE / FALSE / UNKNOWN으로 확정한다.

표준 결과:

```text
TRUE
FALSE
UNKNOWN
```

UNKNOWN은 오류가 아니라 정식 상태다.

현재 resolution type:

```text
SPATIAL_DATA_CONFIRMED
NOTICE_CONFIRMED
LEGAL_RULE_CALCULATED
HYBRID_SPATIAL_NOTICE
EXTERNAL_AUTHORITY_REQUIRED
```

추후 필요하면 resolution type을 추가할 수 있다.

예:

```text
UQQ700 개발밀도관리구역
→ HYBRID_SPATIAL_NOTICE
```

규제별 policy는 최소 다음을 정의한다.

- standard_code
- regulation name
- resolution type
- official source requirement
- designation notice requirement
- historical notice requirement
- spatial confirmation requirement
- negative evidence policy
- TRUE requirements
- FALSE requirements
- UNKNOWN conditions


8. REGULATION RESOLUTION 내부 파이프라인
======================================================================

규제 성격에 따라 모든 단계를 실행하지 않는다.

기본 구조:

```text
REGULATION STANDARD CODE
        ↓
RESOLUTION POLICY
        ↓
COMPETENT AUTHORITY RESOLUTION
        ↓
OFFICIAL SOURCE FAMILY DISCOVERY
        ↓
ENTRY ENDPOINT QUALIFICATION
        ↓
TARGET DOCUMENT DISCOVERY
        ↓
DOCUMENT DIRECT VERIFICATION
        ↓
DESIGNATION / CHANGE / RELEASE VALIDITY
        ↓
SPATIAL SCOPE VERIFICATION
        ↓
FINAL TRUE / FALSE / UNKNOWN
```


9. COMPETENT AUTHORITY & SOURCE SCOPE
======================================================================

향후 Regulation Resolution에서 반드시 포함해야 하는 공통 계층이다.

문제:

`go.kr`이라고 해서 해당 규제를 지정할 권한이 있는 기관은 아니다.

예:

```text
성남시청 고시공고
→ 도시계획 규제 지정 source가 될 수 있음

성남소방서 고시공고
→ 공식 사이트지만 UQQ700 지정권한 source는 아님
```

따라서 source qualification은 다음 구조로 발전한다.

```text
OFFICIAL HOST
    ↓
REGION BINDING
    ↓
SOURCE ROLE
    ↓
LEGAL AUTHORITY SCOPE
    ↓
TARGET REGULATION COMPATIBILITY
```

향후 registry 후보:

```text
AUTHORITY_SCOPE
SOURCE_AUTHORITY_REGISTRY
REGULATION_AUTHORITY_REQUIREMENTS
```

Primary / Secondary source도 구분한다.

예:

- PRIMARY: 실제 지정권자 고시
- SECONDARY: 구보/시보 mirror 또는 재게시
- SUPPORTING: 설명자료 / 보도자료
- INCOMPATIBLE: target 규제 지정권한 없음


10. HISTORICAL NOTICE / DOCUMENT DISCOVERY
======================================================================

목표:

현재 API나 지도 데이터만으로 규제 validity를 확정할 수 없는 경우
과거 지정·변경·해제 고시 identity를 복원한다.

필수 안전 원칙:

- endpoint 발견 ≠ target document 발견
- query 자체를 candidate evidence로 사용 금지
- search page title만으로 candidate 승격 금지
- generic navigation link 승격 금지
- detail/document identity 검증
- municipality/authority binding
- official host 검증
- canonical URL dedupe
- provenance merge
- discovery 실패로 SITE FALSE 금지

문서 형식:

- HTML
- PDF
- HWP
- HWPX
- 첨부파일
- gazette archive

Raw artifact는 Git repository에 저장하지 않는 것을 기본 원칙으로 한다.


11. DOCUMENT DIRECT VERIFICATION
======================================================================

후속 검증에서는 candidate URL만 믿지 않는다.

직접 확인 항목:

- document title
- notice number
- issuing authority
- publication date
- effective date
- designation/change/release action
- target regulation identity
- target region
- spatial scope
- attachment identity
- superseded/repealed 여부

Document candidate 단계에서는:

```text
verified_positive = False
runtime_registration_allowed = False
site_positive_allowed = False
```

를 유지한다.


12. DESIGNATION VALIDITY ENGINE
======================================================================

규제의 역사적 문서가 발견되더라도 현재 적용 여부를 판단해야 한다.

기본 event model:

```text
DESIGNATED
CHANGED
EXPANDED
REDUCED
REPLACED
RELEASED
CANCELLED
SUPERSEDED
```

규제 timeline:

```text
initial designation
    ↓
change 1
    ↓
change 2
    ↓
partial release
    ↓
current valid scope
```

최종 TRUE는 현재 validity가 확인되어야 한다.


13. SPATIAL SCOPE VERIFICATION
======================================================================

지정 고시만으로 특정 parcel 포함 여부를 자동 TRUE 처리하지 않는다.

가능한 evidence:

- official GIS layer
- official 지형도면
- notice attachment polygon
- parcel list
- coordinate boundary
- official map service

HYBRID_SPATIAL_NOTICE의 TRUE 예:

```text
OFFICIAL_DESIGNATION_IDENTITY_VERIFIED
+
DESIGNATION_VALIDITY_VERIFIED
+
SITE_SPATIAL_INCLUSION_VERIFIED
=
TRUE
```

FALSE 예:

```text
OFFICIAL_SPATIAL_EXCLUSION_VERIFIED
or
OFFICIAL_RELEASE_OR_CANCELLATION_VERIFIED
or
AUTHORITATIVE_NON_DESIGNATION_VERIFIED
```

단순 검색 실패는 FALSE가 아니다.


14. LAYER 4 — LEGAL KNOWLEDGE
======================================================================

목표:

현재 SITE 규제와 계산에 필요한 법적 텍스트를 구조화한다.

대상:

- 법률
- 시행령
- 시행규칙
- 행정규칙
- 자치법규
- 고시
- 별표
- 지침
- 유권해석
- 판례/행정심판

Source of truth 우선순위는 공식 원문을 기본으로 한다.

Versioning 원칙:

- 개정 전 원문 삭제 금지
- effective date 저장
- promulgation date 저장
- superseded 상태 유지
- 특정 분석시점(as-of date) 조회 가능하도록 발전


15. DELEGATION CHAIN
======================================================================

법령 검색은 단일 조문에서 끝나지 않는다.

예:

```text
법률
→ 시행령
→ 시행규칙
→ 조례
→ 별표
→ 고시
```

위임관계를 graph 형태로 저장하는 것을 목표로 한다.

향후 필요 필드:

- parent provision
- delegated provision
- delegation type
- required follow-up source
- effective period


16. LAYER 5 — RULE NORMALIZATION
======================================================================

법령 원문을 deterministic engine이 사용할 수 있는 구조로 변환한다.

Rule schema 예:

```json
{
  "rule_id": "...",
  "source": "...",
  "clause": "...",
  "predicates": [],
  "site_conditions": [],
  "project_conditions": [],
  "numeric_effect": {},
  "priority": "...",
  "effective_from": "...",
  "effective_to": null
}
```

조건 유형을 구분한다.

```text
SITE
PROJECT
PROCEDURE
AUTHORITY
TEMPORAL
SPATIAL
```


17. LAYER 6 — DETERMINISTIC EVALUATION
======================================================================

목표:

계산 가능한 결과는 AI가 아니라 rule engine이 계산한다.

주요 계산 대상:

- 건폐율
- 용적률
- 높이
- 층수
- 주차
- 조경
- 도로/접도
- 건축선
- 이격
- 공개공지
- 인센티브
- 완화
- 상한
- 중첩 적용

Rule 상태:

```text
APPLICABLE
NOT_APPLICABLE
CONDITIONAL
UNKNOWN
```

Numeric 상태 예:

```text
INACTIVE
POTENTIAL_CONDITIONAL
ACTIVE_CANDIDATE
RECALC_REQUIRED
RESOLVED
```

조건이 모두 확정되지 않았을 때 숫자를 임의 결정하지 않는다.


18. RULE CONFLICT / PRIORITY ENGINE
======================================================================

향후 반드시 별도 계층으로 강화한다.

처리 대상:

- 상위법 / 하위법
- 일반규정 / 특별규정
- 조례 상한 / 시행령 상한
- 완화 규정
- 중복 인센티브
- 누적 상한
- 적용 시점 차이

결과는 단순 숫자뿐 아니라 계산 trace를 보존한다.

예:

```text
BASE FAR 200
+ incentive A
+ incentive B
→ statutory ceiling 250
→ final 250
```


19. LAYER 7 — HYBRID RETRIEVAL
======================================================================

Rule Engine이 모든 법적 설명을 대체하지 않는다.
AI 분석에 필요한 legal context를 검색한다.

권장 구조:

```text
Rule Matching
+
BM25
+
Vector Search
+
Parent–Child Retrieval
+
Delegation Chain
+
Reranker
```

법령은 정확한 용어 검색과 의미 검색이 모두 필요하므로
vector-only architecture는 사용하지 않는다.

Parent–Child 원칙:

- 검색은 항/호 단위로 정밀하게 수행 가능
- AI에 제공할 때는 부모 조문 context를 함께 제공


20. LAYER 8 — AI ANALYSIS
======================================================================

AI의 역할:

- 쟁점 발견
- 법적 맥락 설명
- 조건부 결과 설명
- 규제 충돌 설명
- 추가 확인 필요사항 제시
- 설계 대안 비교
- 사용자 친화적인 보고서 생성

AI가 하지 않아야 하는 것:

- 규제 TRUE/FALSE 임의 생성
- PNU 추측
- 법령 조문 존재 여부 추측
- 수치 상한 임의 결정
- 없는 고시번호 생성
- citation 없는 법적 사실 확정

Multi-Agent는 필요할 경우 사용하되 agent 수 자체를 목표로 하지 않는다.


21. LAYER 9 — VERIFICATION
======================================================================

AI 출력 후 반드시 reverse verification한다.

검증 대상:

- 조문 번호
- 법령명
- 시행일
- 고시번호
- 판례번호
- 수치값
- SITE FACT
- 규제 상태

Verification 결과 예:

```text
VERIFIED
PARTIALLY_VERIFIED
CONFLICT
UNVERIFIED
```

AI confidence와 source confidence를 분리한다.


22. PROVENANCE MODEL
======================================================================

모든 중요한 결과에는 source chain을 남긴다.

예:

```text
Final FAR
→ Rule 123
→ 서울특별시 도시계획 조례 제XX조
→ law.go.kr ordinance ID
→ effective version
```

규제 TRUE 예:

```text
UQQ700 TRUE
→ parcel intersects official scope
→ current designation event
→ notice number
→ issuing authority
→ official document URL
```

향후 provenance는 graph 또는 structured trace로 관리한다.


23. LAYER 10 — PRODUCT / API
======================================================================

최종 서비스 기능 후보:

1. 단일 필지 분석
2. 다중 필지 분석
3. 블록 / polygon 분석
4. 지도 overlay
5. 법령 질의
6. 개발가능규모 분석
7. 인센티브 시뮬레이션
8. 규제 변경이력
9. as-of-date analysis
10. PDF 보고서
11. API 제공
12. batch analysis

현재 FastAPI는 이 최종 product layer의 기반으로 유지한다.


24. 데이터 저장 아키텍처
======================================================================

Git repository와 runtime data를 분리한다.

권장 구조:

```text
law_data/
    source_registry/
    rule_registry/
    fixtures/
    output/
        summary/
        raw/
        cache/
```

Git에 포함 권장:

- source code
- 작은 regression fixture
- summary JSON
- registry
- schema

Git 제외 권장:

- 대용량 raw discovery JSON
- downloaded PDF/HWP binary
- cache
- temporary extraction files
- API raw dumps

대용량 artifact는 별도 storage strategy를 사용한다.


25. TEST ARCHITECTURE
======================================================================

테스트를 다음 범주로 나눈다.

A. UNIT

- parser
- normalization
- URL canonicalization
- predicates

B. BEHAVIORAL REGRESSION

- known TRUE
- known FALSE
- known UNKNOWN
- known false positive

C. INTEGRATION

- Building API
- VWorld
- law.go.kr
- municipality source

D. END-TO-END

```text
address
→ SITE
→ regulation
→ rules
→ numeric result
→ API response
```

E. POLICY ASSERTION

- runtime registration blocked
- discovery positive blocked
- source failure does not create FALSE

중요:

`all_pass=True`는 실제 법적 정확성과 동일하지 않다.
Behavioral test와 Policy assertion을 출력에서 명시적으로 구분한다.


26. ERROR / UNKNOWN POLICY
======================================================================

다음 상태를 명확하게 분리한다.

```text
NOT_APPLICABLE
UNKNOWN
SOURCE_UNAVAILABLE
SOURCE_ERROR
UNVERIFIED
```

API 장애 또는 historical source 미발견을 규제 FALSE로 바꾸지 않는다.

Fail-safe 원칙:

```text
잘못된 TRUE보다 UNKNOWN이 낫다.
잘못된 FALSE보다 UNKNOWN이 낫다.
```


27. SECURITY / OPERATION
======================================================================

- API key `.env`
- secret Git 저장 금지
- request timeout 필수
- maximum response size 필수
- external source rate limit 고려
- retry bounded
- logging 시 secret 제거
- raw HTML/body preview 크기 제한
- source별 transport diagnostics


28. 성능 아키텍처
======================================================================

초기에는 correctness를 우선한다.

전국화 단계에서는 다음을 추가한다.

- source cache
- law cache
- spatial tile/cache
- document hash dedupe
- request scheduler
- municipality source registry
- async/batch pipeline
- incremental refresh

동일 historical source를 SITE별로 무한 재탐색하지 않는다.

향후 핵심 전환:

```text
SITE마다 crawling
→ source registry 구축
→ document index 구축
→ SITE에서는 indexed evidence lookup
```


29. 전국화 전략
======================================================================

전국화를 위해 지자체별 코드를 무한 하드코딩하지 않는다.

필요 registry:

```text
MUNICIPALITY_REGISTRY
OFFICIAL_SOURCE_REGISTRY
SOURCE_AUTHORITY_REGISTRY
SPATIAL_DATASET_REGISTRY
REGULATION_RESOLUTION_REGISTRY
LEGAL_SOURCE_REGISTRY
```

지자체별 차이는 adapter/config로 흡수한다.


30. 개발 단계 MASTER ROADMAP
======================================================================

PHASE 0 — FOUNDATION

목표:

- repository
- Python environment
- FastAPI skeleton
- configuration
- logging

완료 상태: 현재 완료


PHASE 1 — BUILDING / SITE DATA

목표:

- Building HUB 연결
- Building model
- Site model
- address/PNU identity

완료 상태: 현재 완료


PHASE 2 — LAND / SPATIAL DATA

목표:

- VWorld 연결
- 토지정보
- parcel geometry
- zoning

완료 상태: 핵심 완료, 확장 지속


PHASE 3 — SITE ANALYSIS CORE

목표:

- normalized SITE facts
- analysis response
- FastAPI E2E

완료 상태: 핵심 완료


PHASE 4 — LEGAL DATA INGESTION

목표:

- 국가법령
- 시행령/시행규칙
- 자치법규
- 행정규칙
- version metadata

완료 상태: 상당 부분 진행, 지속 확장


PHASE 5 — RULE ENGINE

목표:

- legal clause normalization
- predicates
- applicability
- numeric effects

완료 상태: 핵심 구조 진행 완료, 규제별 확장 중


PHASE 6 — RUNTIME SPATIAL CONDITIONS

목표:

- common spatial registry/evaluator
- parcel intersection
- known positive/negative regressions

완료 상태: 핵심 구조 완료, condition 추가 진행


PHASE 7 — REGULATION RESOLUTION

목표:

- standard code registry
- resolution type
- authority
- source discovery
- notice/document verification
- TRUE/FALSE/UNKNOWN

완료 상태: 현재 핵심 개발 구간

현재 대표 target:

```text
UQQ700 개발밀도관리구역
```


PHASE 8 — AUTHORITY / HISTORICAL PROVENANCE

목표:

- competent authority registry
- official source registry
- historical archive adapter
- designation timeline
- release/cancellation verification

완료 상태: 다음 핵심 구간


PHASE 9 — NATIONWIDE REGULATION REGISTRY

목표:

각 규제를 resolution type에 따라 분류하고 반복 가능한 pipeline으로 전환한다.

결과:

```text
standard_code
→ resolution policy
→ source adapters
→ verifier
```


PHASE 10 — LEGAL KNOWLEDGE GRAPH / VERSIONING

목표:

- delegation chain
- provision graph
- effective version
- superseded history


PHASE 11 — NUMERIC / DESIGN RULE ENGINE COMPLETION

목표:

- FAR/BCR
- height
- parking
- setback
- landscaping
- incentives
- stacking ceiling


PHASE 12 — HYBRID RETRIEVAL

목표:

- BM25
- Vector
- Parent-Child
- Reranker
- delegation-aware retrieval


PHASE 13 — AI ANALYSIS

목표:

- structured legal analysis
- issue detection
- alternatives
- explanation


PHASE 14 — CITATION REVERSE VERIFICATION

목표:

AI가 언급한 모든 핵심 법적 사실을 source DB와 다시 대조한다.


PHASE 15 — PRODUCTIZATION

목표:

- stable API
- web UI
- map
- report
- user/project input
- error UX


PHASE 16 — BLOCK / MULTI-PARCEL ANALYSIS

목표:

- GeoJSON polygon
- multi parcel union
- zoning overlay
- area weighted calculation


PHASE 17 — HISTORICAL / AS-OF ANALYSIS

목표:

특정 과거 날짜 기준 법령·고시·공간규제를 재현한다.


PHASE 18 — SCALE / OPERATIONS

목표:

- nationwide cache
- source refresh scheduler
- monitoring
- regression CI
- document index
- cost optimization


PHASE 19 — PRODUCTION QUALITY

완료 기준:

- 주요 규제 coverage 목표 충족
- 주요 도시 regression fixture 확보
- source provenance complete
- deterministic numeric coverage 확보
- AI citation verification
- failure-safe UNKNOWN policy
- observability
- performance target


31. CURRENT ARCHITECTURE CHECKPOINT
======================================================================

2026-08-26 기준 프로젝트는 MASTER ROADMAP상 대략 다음 위치다.

```text
PHASE 0   Foundation                    COMPLETE
PHASE 1   Building/SITE                 COMPLETE
PHASE 2   Land/Spatial                  CORE COMPLETE
PHASE 3   SITE Analysis                 CORE COMPLETE
PHASE 4   Legal ingestion               IN PROGRESS
PHASE 5   Rule Engine                   IN PROGRESS / CORE STABLE
PHASE 6   Runtime spatial               CORE STABLE
PHASE 7   Regulation Resolution         ACTIVE
PHASE 8   Authority/Historical          STARTING
PHASE 9+  Nationwide/AI/Product         FUTURE
```

현재 개발이 후반부라는 뜻이 아니다.
현재는 향후 AI 분석의 정확성을 결정하는 deterministic data foundation을 구축하는 단계다.


32. 현재 UQQ700에서 얻은 아키텍처 교훈
======================================================================

개발밀도관리구역 historical discovery에서 다음 교훈을 얻었다.

1. official host만으로 source qualification 불충분
2. municipality identity만으로 source qualification 불충분
3. target query는 document evidence가 될 수 없음
4. page-wide text는 candidate contamination을 만들 수 있음
5. canonical URL dedupe 필수
6. historical source 실패는 UNKNOWN
7. competent authority resolution이 discovery보다 앞에 있어야 함
8. 모든 규제에 동일 crawling depth를 적용하면 비용이 과도함

따라서 Regulation Resolution architecture는 앞으로 다음 순서를 기본으로 한다.

```text
RESOLUTION TYPE
→ AUTHORITY
→ SOURCE
→ DOCUMENT
→ VALIDITY
→ SPATIAL
→ FINAL STATUS
```


33. 향후 아키텍처 변경 규칙
======================================================================

이 문서는 개발 중 변경될 수 있다.

변경 시 다음을 기록한다.

- Architecture version
- 변경 날짜
- 변경 대상 layer
- 변경 이유
- 기존 behavior 영향
- migration 필요 여부
- regression test 필요 여부

큰 구조 변경은 `PROJECT_STATUS.md`의 단기 작업과 별도로 이 문서를 먼저 수정한다.


34. ARCHITECTURE DECISION PRINCIPLES
======================================================================

새 기능을 추가할 때 다음 질문을 우선한다.

1. 이 정보는 SITE FACT인가 PROJECT INPUT인가?
2. official source가 있는가?
3. TRUE/FALSE를 deterministic하게 결정할 수 있는가?
4. 미확정이면 UNKNOWN을 유지할 수 있는가?
5. regulation resolution type은 무엇인가?
6. competent authority는 누구인가?
7. spatial verification이 필요한가?
8. historical validity가 필요한가?
9. AI가 아니라 rule engine에서 처리 가능한가?
10. provenance를 끝까지 추적할 수 있는가?
11. regression fixture를 만들 수 있는가?
12. 전국화 가능한 registry/adapter 구조인가?


35. 프로젝트 성공 기준
======================================================================

이 프로젝트는 단순히 많은 법령을 검색하는 서비스가 되는 것을 목표로 하지 않는다.

성공 기준은 다음에 가깝다.

```text
INPUT SITE
    ↓
확정된 parcel identity
    ↓
공식 SITE facts
    ↓
규제별 TRUE / FALSE / UNKNOWN
    ↓
공식 designation / spatial / legal provenance
    ↓
결정론적 법규 계산
    ↓
AI 설명
    ↓
reverse verification
```

최종 사용자에게는 간단한 결과를 보여주되,
내부적으로는 모든 중요한 판단이 source까지 역추적 가능해야 한다.


36. ARCHITECTURE CHANGE LOG
======================================================================

### v1.0 — 2026-08-26

초기 master architecture baseline 작성.

반영 내용:

- STEP 1~16에서 구축된 SITE / API / spatial foundation
- STEP 17 Rule Engine 및 runtime spatial condition 구조
- Regulation Resolution Type 도입
- UrbanLaw 비교에서 도출한 deterministic-first 전략
- UQQ700 historical discovery에서 확인한 false-positive 문제
- competent authority layer 필요성
- future legal knowledge / hybrid retrieval / AI / verification roadmap

다음 architecture review trigger:

- Regulation Authority/Source Scope 계층 구현 완료 시
- UQQ700 최종 TRUE/FALSE/UNKNOWN resolution 완료 시
- Nationwide regulation registry 설계 시작 시
- Hybrid Retrieval / AI 단계 진입 시
