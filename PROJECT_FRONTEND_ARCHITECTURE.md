# AI 대지분석 자동화 시스템 — Frontend Architecture

## 1. 문서 목적

이 문서는 AI 대지분석 자동화 시스템의 Frontend 제품 구조와 사용자 경험, UI 상태, 지도 표현, Backend API 연동 경계를 정의한다.

기존 `PROJECT_ARCHITECTURE.md`가 PNU canonical identity, SITE truth, 공간·역사 규제 해석, verified registry, Rule Engine, SITE analysis 등 Backend/Core Architecture의 기준이라면, 이 문서는 그 Backend 결과를 사용자가 안전하고 이해하기 쉽게 탐색·확인·조회하는 Frontend Architecture의 기준이다.

이 문서는 Backend Architecture를 대체하거나 변경하지 않는다. Backend의 신뢰 경계와 architecture invariant가 항상 우선하며, Frontend는 SITE truth 또는 법적 적용 여부를 독자적으로 생성하지 않는다.

---

## 2. Frontend Architecture 기본 원칙

Frontend의 책임은 다음과 같다.

- 사용자의 지번주소 입력을 받는다.
- Backend가 반환한 parcel candidate를 목록과 지도 marker로 표현한다.
- 사용자의 candidate 선택 상태를 관리한다.
- Backend에 선택 candidate의 실제 parcel verification을 요청한다.
- Backend가 검증한 parcel polygon을 지도에 표시한다.
- 사용자가 검증된 필지를 최종 확인한 후 SITE analysis를 요청하도록 한다.
- Backend의 분석 결과를 요약, 상세 법규, 근거 정보로 이해하기 쉽게 표현한다.
- `UNKNOWN`, `CONDITIONAL` 등 Backend 판정 의미를 변경하지 않고 표현한다.

Frontend가 해서는 안 되는 일은 다음과 같다.

- candidate PNU를 canonical parcel identity로 독자 확정하지 않는다.
- candidate point를 실제 parcel geometry로 간주하지 않는다.
- Frontend 선택 상태를 Backend verification으로 간주하지 않는다.
- SITE truth를 생성하지 않는다.
- 법규 applicability를 독자 판정하지 않는다.
- `UNKNOWN`을 `FALSE` 또는 `NOT_APPLICABLE`로 변환하지 않는다.
- 서로 다른 PNU의 identity, geometry, evidence 또는 분석 결과를 재사용하지 않는다.

핵심 신뢰 원칙:

```text
candidate marker != parcel truth
selected candidate != verified parcel
frontend selection != canonical identity
verified polygon = Backend verification result
Frontend != SITE truth authority
Frontend != legal applicability authority
UNKNOWN != FALSE
```

---

## 3. 제품 UX 기준안 — A안 지도 중심 구조

Frontend MVP의 기준 UX는 지도 중심 A안으로 한다.

Desktop 기본 구조:

```text
+-----------------------------+---------------------------------------+
| Search / Candidate / Result |                                       |
| information panel           |                 MAP                   |
|                             |                                       |
|                             |                                       |
+-----------------------------+---------------------------------------+
```

주소 검색과 candidate 선택 단계에서는 지도를 크게 유지한다. 분석 완료 후에는 결과 정보의 중요도가 높아지므로 정보 패널을 확장하고 지도 영역을 축소할 수 있는 혼합형 구조를 목표로 한다.

이 구조는 향후 parcel geometry뿐 아니라 용도지역, 공간규제, 지구단위계획 등 검증된 spatial layer를 지도에 확장할 수 있어야 한다.

---

## 4. 핵심 사용자 흐름

Frontend MVP의 핵심 사용자 흐름은 다음과 같다.

```text
Site Entry
    ↓
Address Input
    ↓
Candidate Search
    ↓
Candidate List <-> Map Markers
    ↓
Candidate Selection
    ↓
Parcel Verification Request
    ↓
Verified Parcel Polygon
    ↓
User Parcel Confirmation
    ↓
"이 필지 분석"
    ↓
SITE Analysis Request
    ↓
Analysis Loading
    ↓
Result Summary
    ↓
Regulation Details / Evidence
```

제품의 첫 번째 성공 기준은 사용자가 전문적인 PNU나 법정동 코드를 직접 알지 않아도 `주소 입력 → 정확한 필지 선택 → 지도 확인 → 분석 → 결과 이해`를 완료할 수 있는 것이다.

---

## 5. Frontend / Backend 책임 경계

전체 흐름의 책임 경계는 다음과 같다.

```text
[Frontend]

Address Search
    ↓
Candidate Discovery UI
    ↓
Candidate List <-> Map Marker
    ↓
Candidate Selection
    ↓
Parcel Verification Request
    ↓
Verified Polygon Display
    ↓
User Parcel Confirmation
    ↓
Analysis Request
    ↓
Result Presentation

================ API / TRUST BOUNDARY ================

[Backend]

Candidate Search
    ↓
Selected Candidate Verification
    ↓
Live Parcel Polygon Query
    ↓
Polygon PNU Match
    ↓
Canonical PNU Verification
    ↓
Existing SITE Analysis Pipeline
    ↓
Rule Engine
    ↓
SITE_ANALYSIS_API_V1
```

Frontend가 candidate를 선택하는 행위는 사용자의 분석 대상 선택일 뿐 canonical identity 확정이 아니다.

Backend는 Frontend가 전달한 `candidate_pnu`, `x`, `y`를 authoritative truth로 신뢰해서는 안 되며, 기존 verification 절차를 통해 다시 확인해야 한다.

---

## 6. 주소 검색 화면

MVP의 기본 입력은 현재 Backend에서 검증된 지번주소 중심으로 한다.

사용자에게 PNU, 시군구코드, 법정동코드, 본번·부번, Building HUB 내부 코드 등을 직접 요구하지 않는다.

검색 실행 시 현재 공개 API 계약의 다음 endpoint를 사용한다.

```text
POST /v1/parcel-candidates/address
```

주소 검색 시점에는 full SITE analysis를 실행하지 않는다.

검색 결과가 없는 경우와 API 오류는 서로 다른 UI 상태로 관리한다.

---

## 7. Candidate List와 Map Marker

Candidate 검색 결과는 좌측 목록과 우측 지도 marker로 동시에 표현한다.

현재 candidate UI에서 사용할 수 있는 주요 데이터는 다음과 같다.

```text
candidate_pnu
parcel_address
road_address
building_name
x
y
```

`candidate_pnu`는 Frontend 내부 selection/verification 요청에 사용할 수 있으나 사용자에게 핵심 정보처럼 강조할 필요는 없다.

목록과 지도는 동일한 selection state를 사용한다.

```text
List Candidate Selection
          ↕
Map Marker Selection
```

목록에서 candidate를 선택하면 해당 marker도 선택되고, marker를 선택하면 해당 목록 candidate도 선택되어야 한다.

---

## 8. Map Data Contract

### 8.1 Candidate Marker

Candidate marker는 discovery data이다.

```text
x / y
CRS: EPSG:4326
```

Candidate marker가 의미하는 것은 검색 서비스가 반환한 후보 위치이다.

Candidate marker는 다음을 의미하지 않는다.

- verified parcel
- verified parcel boundary
- canonical SITE identity
- SITE truth

### 8.2 Verified Parcel Polygon

실제 parcel boundary는 Backend verification 성공 이후에만 표시한다.

Frontend에서 요구되는 목표 데이터 형태는 다음과 같다.

```text
verified PNU
GeoJSON Polygon or MultiPolygon
CRS / coordinate contract
verification status
verification resolution
basic parcel identity information
```

구체적인 lightweight confirmation API response schema는 Backend 구현 시 실제 기존 verifier와 geometry contract를 확인한 뒤 별도 확정한다. 이 문서에서 아직 구현되지 않은 schema를 실제 API 계약으로 선언하지 않는다.

### 8.3 Analysis Spatial Layers

SITE analysis 이후 parcel geometry와 regulation/spatial layer가 제공되는 경우 지도는 검증된 Backend 결과만 표현한다.

서로 다른 PNU의 geometry 또는 spatial evidence를 Frontend cache/state에서 잘못 재사용하지 않도록 parcel identity를 기준으로 상태를 분리해야 한다.

---

## 9. Parcel Verification / Confirmation UX

Candidate를 선택한 직후 full analysis를 실행하지 않는 것을 목표 UX로 한다.

목표 흐름:

```text
candidate selected
    ↓
Backend parcel verification
    ↓
verified parcel polygon
    ↓
map polygon display
    ↓
user confirms parcel
    ↓
"이 필지 분석"
```

검증 중에는 `선택한 필지를 확인하고 있습니다`와 같은 loading state를 표시한다.

검증 성공 후 marker 중심 표현에서 verified polygon 중심 표현으로 전환한다.

사용자는 이 단계에서 다른 candidate로 돌아가거나 해당 필지의 분석을 실행할 수 있다.

Full analysis 요청 시에는 이전 confirmation 성공을 Frontend authority로 사용하지 않는다. 기존 selected-candidate analysis Backend가 분석 실행 시에도 필요한 verification을 다시 수행하는 구조를 유지한다.

---

## 10. SITE Analysis 연동

현재 selected candidate 기반 full analysis의 공개 endpoint는 다음과 같다.

```text
POST /v1/site-analysis/selected-candidate
```

Frontend는 분석 요청 후 응답 완료 전까지 `ANALYZING` 상태를 유지한다.

Backend가 실제 단계별 progress event를 제공하지 않는 동안 Frontend가 임의의 percentage 또는 완료된 내부 처리 단계를 만들어 표시해서는 안 된다.

MVP에서는 indeterminate loading을 사용한다.

예:

```text
대지 정보를 분석하고 있습니다.
잠시만 기다려 주세요.
```

향후 실제 progress API 또는 event contract가 도입되면 단계형 progress UI를 별도로 설계한다.

---

## 11. 분석 결과 Presentation

현재 Backend public response schema는 `SITE_ANALYSIS_API_V1`이다.

MVP Frontend는 이 응답을 기반으로 먼저 다음 핵심 정보를 요약한다.

- 분석 대상 주소
- 용도지역
- 공식 대지면적
- 건폐율
- 용적률
- parcel geometry/map
- Rule Engine 결과 요약
- 추가 확인이 필요한 규제

Backend raw 구조 전체를 첫 화면에 그대로 노출하지 않는다.

결과 화면은 `요약 → 상세 법규 → 근거` 순서로 정보 깊이를 단계적으로 제공한다.

향후 Frontend presentation 전용 Backend model이 추가될 수 있으나, 현재 `SITE_ANALYSIS_API_V1`만으로 MVP result UI를 시작할 수 있다.

---

## 12. Rule Engine 상태 표현

Rule Engine의 상태 의미를 Frontend가 변경해서는 안 된다.

기본 UI 표현 예시는 다음과 같다.

```text
APPLICABLE       → 적용
NOT_APPLICABLE   → 비적용
CONDITIONAL      → 조건부
UNKNOWN          → 확인 필요
```

특히 `UNKNOWN`은 오류나 비적용이 아니다.

사용자 설명 예:

```text
공식 자료만으로 현재 적용 여부를 확정할 수 없습니다.
추가 확인이 필요합니다.
```

UNKNOWN이 존재하더라도 전체 분석이 성공한 경우 이를 analysis failure 화면으로 전환하지 않는다.

---

## 13. 법규 상세 / Evidence UX

상세 법규는 전체 규칙을 단순 나열하기보다 상태별 filter를 제공하는 방향으로 한다.

예:

```text
전체 | 적용 | 조건부 | 확인 필요
```

각 법규 항목은 Backend에서 실제 제공되는 범위 안에서 다음 정보 계층을 목표로 한다.

```text
규제/법규 명칭
판정 상태
기준 또는 결과
사용자 설명
근거
상세 evidence
```

Frontend 설명 계층은 Backend의 판정 결과를 설명할 수는 있지만 새로운 법적 결론을 생성해서는 안 된다.

---

## 14. Frontend State Model

MVP의 기본 상태 모델은 다음을 기준으로 한다.

```text
IDLE

SEARCHING
SEARCH_RESULTS
SEARCH_EMPTY
SEARCH_ERROR

CANDIDATE_SELECTED

VERIFYING_PARCEL
PARCEL_VERIFIED
PARCEL_VERIFICATION_FAILED

ANALYZING

ANALYSIS_READY
ANALYSIS_FAILED
```

Framework를 선택할 때도 이 state model과 API boundary를 보존한다.

Frontend framework가 product architecture를 결정하게 하지 않는다.

---

## 15. Error / Empty / Unknown State

MVP는 최소 다음 사용자 상태를 구분한다.

### 주소 검색 결과 없음

```text
검색 결과가 없습니다.
지번주소를 다시 확인해주세요.
```

### Parcel verification 실패

```text
선택한 필지를 확인하지 못했습니다.
다른 후보를 선택하거나 다시 검색해주세요.
```

### 외부 데이터 또는 분석 요청 실패

```text
토지 정보를 불러오지 못했습니다.
잠시 후 다시 시도해주세요.
```

### 일부 법규 UNKNOWN

오류 페이지로 이동시키지 않는다. 정상 결과 안에서 `확인 필요`로 표시한다.

현재 public API의 일부 오류가 HTTP status + string `detail` 형태이므로, 제품용 machine-readable error schema는 향후 Backend 보완 대상으로 관리한다.

---

## 16. Responsive 원칙

Desktop은 지도 중심 split layout을 기본으로 한다.

```text
Information Panel | Map
```

Mobile에서는 같은 기능을 세로 흐름으로 변환한다.

```text
Address Search
    ↓
Map
    ↓
Candidate / Selected Parcel
    ↓
Analysis / Result
```

MVP 구현이 Desktop 우선이어도 component와 layout은 responsive 확장을 방해하지 않도록 설계한다.

---

## 17. 현재 구현 상태

이 절은 실제 Backend 및 repository 상태와 목표 Frontend 상태를 구분하기 위한 것이다.

### CURRENT — Backend에서 확인된 기반

- 주소 기반 parcel candidate search API
- candidate의 PNU/address/building name/x/y 데이터
- selected candidate live verification 로직
- selected candidate 기반 full SITE analysis orchestration
- `POST /v1/parcel-candidates/address`
- `POST /v1/site-analysis/selected-candidate`
- `SITE_ANALYSIS_API_V1`
- verified SITE analysis 내부에서 parcel geometry/spatial data 사용
- Rule Engine 분석 결과

### NOT YET IMPLEMENTED — Frontend / Product Gap

- 실제 Frontend application
- 지도 UI
- candidate list / map marker synchronization
- lightweight parcel confirmation API
- full analysis 이전 verified polygon confirmation UX
- Frontend presentation 전용 model
- machine-readable product error schema
- 실제 Backend progress event/API

이 목록의 `CURRENT` 상태는 실제 repository 구현이 확인된 경우에만 갱신한다. 목표 설계를 구현 완료로 기록하지 않는다.

---

## 18. Lightweight Parcel Confirmation API 필요성

현재 Backend에는 selected candidate를 검증한 뒤 full analysis로 연결하는 경로가 존재한다.

그러나 A안의 목표 UX는 다음 순서를 요구한다.

```text
candidate selection
    ↓
parcel verification
    ↓
verified polygon display
    ↓
user confirmation
    ↓
full analysis
```

따라서 full SITE analysis를 실행하지 않고 selected candidate를 live re-verification하여 verified parcel identity와 polygon을 반환하는 lightweight confirmation API가 중요한 Backend 보완 후보이다.

이 API는 새로운 parcel truth path를 만들어서는 안 된다. 기존 selected candidate verifier와 canonical identity/geometry verification 경로를 재사용해야 한다.

구체적인 파일, endpoint, response schema, contract test는 별도의 READ-ONLY 조사와 WRITE 승인 후 확정한다.

---

## 19. MVP Vertical Slice

첫 Frontend 구현의 목표 vertical slice는 다음과 같다.

```text
실제 지번주소 입력
    ↓
실제 candidate API
    ↓
실제 candidate cards
    ↓
실제 map markers
    ↓
candidate selection
    ↓
실제 Backend parcel verification
    ↓
실제 verified parcel polygon
    ↓
"이 필지 분석"
    ↓
실제 selected-candidate analysis API
    ↓
실제 SITE_ANALYSIS_API_V1
    ↓
result summary
    ↓
regulation detail / UNKNOWN / evidence
```

Mock data만으로 완성된 화면을 먼저 만드는 방식보다 실제 Backend contract와 연결된 작은 end-to-end vertical slice를 우선한다.

---

## 20. MVP 범위 밖의 기능

첫 vertical slice에서는 다음 SaaS 기능을 우선 범위에 포함하지 않는다.

- authentication
- organization/team management
- billing
- usage metering
- project management
- saved analyses/history
- favorites
- report management

이 기능들은 핵심 parcel analysis UX가 안정화된 이후 별도 architecture와 요구사항을 정의한다.

---

## 21. 기술 스택 결정 원칙

현재 repository에는 재사용 가능한 Frontend framework 기반이 확인되지 않았다.

React, Vue, Next.js, Vite 등 구체적인 Frontend 기술 선택은 이 문서의 UX/state/API/map contract를 기준으로 별도 결정한다.

기술 스택 결정 순서는 다음 원칙을 따른다.

```text
Product UX
    ↓
State / Trust Boundary
    ↓
API Contract
    ↓
Map Requirements
    ↓
Frontend Framework / Build Tool
    ↓
Directory Structure
    ↓
First Vertical Slice
```

Framework 선택 때문에 Backend trust boundary 또는 product flow를 변경하지 않는다.

---

## 22. Backend Architecture와의 관계

Frontend 개발 중 Backend Architecture의 다음 원칙은 그대로 보호한다.

- canonical parcel identity는 Backend가 검증한다.
- SITE truth는 Backend에서만 생성한다.
- `resolver result != parcel applicability`
- `SITE-decision eligibility != SITE truth`
- `SITE applicability admission != runtime registration authority`
- 서로 다른 PNU의 identity/address/zone/coordinate/geometry/evidence를 재사용하지 않는다.
- `source not found != FALSE`
- `notice found != currently valid`
- 두 번째 SITE truth path를 만들지 않는다.
- 두 번째 Rule Engine path를 만들지 않는다.
- Frontend 기능을 이유로 기존 Architecture STEP 번호 체계를 확장하거나 재해석하지 않는다.

Frontend는 이 경계를 침범하지 않고 Backend의 검증 결과를 사용자에게 전달하는 product layer로 유지한다.

---

## 23. 다음 개발 순서

이 Frontend Architecture baseline 이후 개발은 다음 순서로 구체화한다.

```text
1. Frontend 기술 스택 결정
2. Frontend repository/directory structure 결정
3. 지도 provider 및 map component contract 결정
4. lightweight parcel confirmation API READ-ONLY 설계
5. 필요한 Backend 최소 WRITE scope 승인 및 구현
6. Frontend shell + address search vertical slice
7. candidate list <-> map synchronization
8. verified parcel polygon confirmation
9. selected-candidate full analysis 연결
10. result summary / regulation detail / evidence UI
11. error/empty/UNKNOWN state hardening
12. responsive hardening
```

각 단계는 실제 repository 상태를 다시 확인하고 최소 WRITE scope를 명시한 뒤 진행한다.

---

## 24. Baseline Summary

Frontend 제품의 핵심은 다음 한 문장으로 요약한다.

> 사용자가 주소만으로 분석 대상을 찾고, Backend가 검증한 실제 필지를 지도에서 확인한 뒤, 기존 SITE analysis와 Rule Engine 결과를 신뢰 경계를 훼손하지 않고 이해하기 쉽게 확인할 수 있게 한다.

Frontend의 핵심 책임은 **선택, 확인, 표현**이다.

Backend의 핵심 책임은 **검증, SITE truth, 법규 판정**이다.
