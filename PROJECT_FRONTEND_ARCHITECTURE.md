# AI 대지분석 자동화 시스템 — Frontend Architecture

## 1. 문서 역할

이 문서는 Frontend의 **구조적 기준과 불변 원칙**을 정의한다.

- Backend/Core 기준: `PROJECT_ARCHITECTURE.md`
- Backend 구현/검증 현황: `PROJECT_STATUS.md`
- Frontend 구조/UX 기준: `PROJECT_FRONTEND_ARCHITECTURE.md`
- Frontend 구현/검증 현황: `PROJECT_FRONTEND_STATUS.md`

이 문서에는 목표 구조, 책임 경계, UX/state/map/API 원칙을 기록한다. 실제 구현 완료 여부, 테스트 PASS, 현재 blocker, 다음 작업은 `PROJECT_FRONTEND_STATUS.md`에서 관리한다.

Frontend Architecture는 Backend Architecture를 대체하거나 변경하지 않는다. Backend의 PNU canonical identity, SITE truth, spatial/historical regulation resolution, verified registry, Rule Engine과 신뢰 경계가 우선한다.

---

## 2. Frontend 핵심 책임

Frontend의 핵심 책임은 **선택, 확인, 표현**이다.

Frontend는 사용자의 지번주소 입력을 받고, Backend가 반환한 parcel candidate를 목록과 지도 marker로 표현하며, 사용자 selection state를 관리한다. 선택 candidate의 실제 parcel verification은 Backend에 요청하고, Backend가 검증한 polygon만 실제 필지 경계로 표시한다. 사용자가 검증된 필지를 확인한 뒤 SITE analysis를 요청하고, Backend 결과를 요약·상세 법규·근거의 정보 계층으로 표현한다.

Frontend는 다음 권한을 갖지 않는다.

- candidate PNU를 canonical parcel identity로 독자 확정
- candidate point를 실제 parcel geometry로 간주
- Frontend selection을 Backend verification으로 간주
- SITE truth 생성
- 법규 applicability 독자 판정
- `UNKNOWN`을 `FALSE` 또는 `NOT_APPLICABLE`로 변환
- 서로 다른 PNU의 identity/address/zone/coordinate/geometry/evidence/result 재사용

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

## 3. 제품 UX Baseline — A안 지도 중심

Frontend MVP의 기준 UX는 **A안 지도 중심 구조**로 한다.

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

지도 구조는 향후 verified parcel geometry뿐 아니라 용도지역, 공간규제, 지구단위계획 등 Backend가 검증한 spatial layer를 확장할 수 있어야 한다.

---

## 4. 핵심 사용자 흐름

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

제품의 첫 번째 성공 기준은 사용자가 PNU나 법정동코드 같은 내부 식별자를 직접 알지 않아도 `주소 입력 → 정확한 필지 선택 → 지도 확인 → 분석 → 결과 이해`를 완료하는 것이다.

현재 검증된 Backend 범위를 고려하여 MVP 주소 입력은 지번주소 중심으로 한다. 도로명주소 지원이 완성된 것으로 표현하지 않는다.

---

## 5. Frontend / Backend Trust Boundary

```text
[Frontend]

Address Search UI
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

Backend는 Frontend가 전달한 `candidate_pnu`, `x`, `y`를 authoritative truth로 신뢰해서는 안 되며 기존 verification 절차로 다시 확인해야 한다.

Pre-analysis confirmation이 성공했더라도 full analysis 요청에서 필요한 verification을 다시 수행하는 기존 Backend 원칙을 유지한다.

---

## 6. API Interaction 원칙

주소 검색은 candidate discovery만 수행하며 full analysis를 실행하지 않는다.

현재 사용되는 공개 candidate endpoint:

```text
POST /v1/parcel-candidates/address
```

사용자가 검증된 필지를 최종 확인한 뒤 full analysis를 실행한다.

현재 selected-candidate full analysis endpoint:

```text
POST /v1/site-analysis/selected-candidate
```

Pre-analysis polygon confirmation is now provided by the validated lightweight `POST /v1/parcel-candidates/confirm` boundary. It reuses Backend verification semantics without treating confirmation as a substitute for the full selected-candidate analysis re-verification.

---

## 7. Candidate List / Map Selection Contract

Candidate 결과는 좌측 목록과 우측 지도 marker로 동시에 표현한다.

Frontend selection은 하나의 state를 공유한다.

```text
List Candidate Selection
          ↕
Map Marker Selection
```

목록에서 candidate를 선택하면 해당 marker도 선택되고, marker를 선택하면 해당 목록 candidate도 선택된다.

Candidate UI가 소비하는 Backend data의 핵심 개념은 다음과 같다.

```text
candidate_pnu
parcel_address
road_address
building_name
x
y
```

PNU는 verification 요청과 내부 identity 연결에 사용할 수 있으나 일반 사용자에게 핵심 입력값으로 요구하지 않는다.

---

## 8. Map Data Contract

### 8.1 Candidate Marker

Candidate marker는 discovery data이다.

```text
x / y
CRS: EPSG:4326
```

Candidate marker는 verified parcel, verified boundary, canonical SITE identity 또는 SITE truth를 의미하지 않는다.

### 8.2 Verified Parcel Polygon

실제 parcel boundary는 Backend verification 성공 이후에만 표시한다.

목표 표현에 필요한 개념:

```text
verified PNU
GeoJSON Polygon or MultiPolygon
coordinate/CRS contract
verification status
verification resolution
basic parcel identity
```

현재 lightweight confirmation response는 `PARCEL_CONFIRMATION_V1`이며 VERIFIED parcel identity와 Backend verification에 사용된 Polygon/MultiPolygon geometry를 제공한다. Frontend는 이 verified geometry만 실제 parcel boundary로 취급한다.

### 8.3 Analysis Spatial Layers

SITE analysis 이후 parcel/regulation/spatial layer를 표시할 때도 Backend가 검증한 결과만 사용한다.

Frontend cache/state는 parcel identity를 기준으로 격리하여 서로 다른 PNU의 geometry 또는 evidence가 섞이지 않도록 한다.

---

## 9. Parcel Verification / Confirmation UX

목표 UX는 candidate 선택 직후 full analysis를 실행하지 않는다.

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

검증 중에는 실제 진행률을 만들지 않고 `선택한 필지를 확인하고 있습니다`와 같은 indeterminate state를 사용한다.

검증 성공 후 discovery marker 중심 표현에서 verified polygon 중심 표현으로 전환한다. 사용자는 다른 candidate를 선택하거나 해당 필지 분석을 실행할 수 있다.

---

## 10. Frontend State Model

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

Framework 또는 state library 선택이 이 product state model과 Backend trust boundary를 변경하게 하지 않는다.

서로 다른 주소 검색 또는 PNU로 context가 전환되면 이전 parcel verification/result state가 새 parcel에 승계되지 않도록 초기화 또는 identity-scoped state를 사용한다.

---

## 11. Loading / Progress 원칙

Backend가 실제 단계별 progress event를 제공하지 않는 동안 Frontend는 임의의 percentage나 완료 단계를 만들어 표시하지 않는다.

MVP analysis loading은 indeterminate 방식으로 한다.

```text
대지 정보를 분석하고 있습니다.
잠시만 기다려 주세요.
```

실제 progress API/event contract가 도입된 이후에만 단계형 progress UI를 추가한다.

---

## 12. Analysis Result Presentation

Frontend는 `SITE_ANALYSIS_API_V1`의 raw 구조 전체를 첫 화면에 그대로 노출하지 않는다.

결과 정보 계층은 다음을 기준으로 한다.

```text
Result Summary
    ↓
Regulation Details
    ↓
Evidence / Source Detail
```

MVP 요약의 핵심 개념은 다음과 같다.

- 분석 대상 주소
- 용도지역
- 공식 대지면적
- 건폐율
- 용적률
- verified parcel geometry/map
- Rule Engine 결과 요약
- 추가 확인이 필요한 규제

향후 presentation 전용 Backend model을 추가할 수 있으나 기존 SITE truth나 Rule Engine의 두 번째 판정 경로를 만들지 않는다.

---

## 13. Rule Engine 상태 표현

Backend 상태 의미를 Frontend가 변경하지 않는다.

```text
APPLICABLE       → 적용
NOT_APPLICABLE   → 비적용
CONDITIONAL      → 조건부
UNKNOWN          → 확인 필요
```

`UNKNOWN`은 analysis failure나 비적용이 아니다.

사용자 설명 예:

```text
공식 자료만으로 현재 적용 여부를 확정할 수 없습니다.
추가 확인이 필요합니다.
```

UNKNOWN이 존재하더라도 전체 분석이 성공했다면 정상 result 안에서 표현한다.

---

## 14. Regulation Detail / Evidence UX

상세 법규는 전체 규칙을 무조건 나열하기보다 상태별 filter를 제공하는 방향으로 한다.

```text
전체 | 적용 | 조건부 | 확인 필요
```

Backend가 실제 제공하는 범위 안에서 각 항목은 다음 정보 계층을 목표로 한다.

```text
규제/법규 명칭
판정 상태
기준 또는 결과
사용자 설명
근거
상세 evidence
```

Frontend 설명은 Backend 판정을 이해하기 쉽게 표현할 수 있지만 새로운 법적 결론을 생성해서는 안 된다.

---

## 15. Error / Empty / Unknown 원칙

MVP는 최소 다음 상태를 구분한다.

- 주소 검색 결과 없음
- parcel verification 실패
- 외부 데이터/API 또는 full analysis 실패
- 분석 성공 + 일부 규칙 UNKNOWN

UNKNOWN은 error page로 전환하지 않는다.

현재 일부 public API 오류가 HTTP status + string `detail` 형태이므로 향후 machine-readable product error schema가 도입되면 Frontend error mapping을 그 계약에 맞춰 강화한다. 그 전에는 존재하지 않는 error code를 Frontend에서 가정하지 않는다.

---

## 16. Responsive 원칙

Desktop은 지도 중심 split layout을 기본으로 한다.

```text
Information Panel | Map
```

Mobile은 동일 기능을 세로 흐름으로 변환한다.

```text
Address Search
    ↓
Map
    ↓
Candidate / Selected Parcel
    ↓
Analysis / Result
```

Desktop 우선 구현이어도 responsive 확장을 막는 고정 구조를 만들지 않는다.

---

## 17. MVP Vertical Slice 원칙

첫 Frontend 구현은 실제 Backend contract와 연결된 작은 end-to-end vertical slice를 우선한다.

```text
실제 지번주소 입력
    ↓
실제 candidate API
    ↓
candidate cards
    ↓
map markers
    ↓
candidate selection
    ↓
실제 Backend parcel verification
    ↓
verified parcel polygon
    ↓
"이 필지 분석"
    ↓
실제 selected-candidate analysis API
    ↓
SITE_ANALYSIS_API_V1
    ↓
result summary
    ↓
regulation detail / UNKNOWN / evidence
```

Mock-only 완성 화면을 먼저 만드는 방식보다 실제 Backend와 연결되는 vertical slice를 우선한다.

---

## 18. MVP 범위 밖의 기능

첫 vertical slice에는 다음 SaaS 기능을 우선 포함하지 않는다.

- authentication
- organization/team management
- billing
- usage metering
- project management
- saved analyses/history
- favorites
- report management

핵심 parcel analysis UX 안정화 이후 별도 요구사항과 architecture를 정의한다.

---

## 19. 기술 스택 결정 원칙

Frontend 기술은 Architecture보다 먼저 확정하지 않는다.

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

현재 구현 기술은 React + TypeScript + Vite이며 Kakao Maps를 MVP map provider로 사용한다. Map Adapter 경계를 유지하여 provider 선택이 canonical parcel/SITE trust boundary를 변경하지 않도록 한다.

---

## 20. Backend Architecture 보호 규칙

Frontend 개발 중에도 다음 Backend 원칙을 그대로 보호한다.

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

Frontend는 Backend의 검증 결과를 소비하는 product layer로 유지한다.

---

## 21. Architecture 변경 관리

다음과 같은 변경은 이 Architecture 문서를 갱신할 수 있다.

- 핵심 사용자 흐름 변경
- Frontend/Backend 책임 경계 변경
- map truth contract 변경
- Frontend state model의 구조적 변경
- API interaction 원칙 변경
- result presentation 계층의 구조적 변경
- 기술 스택 확정 후 장기적으로 유지할 구조적 결정

반면 구현 완료 여부, 테스트 결과, 현재 blocker, 현재 HEAD, 다음 작업은 `PROJECT_FRONTEND_STATUS.md`에만 기록한다.

---

## 22. Baseline Summary

Frontend 제품의 핵심은 다음과 같다.

> 사용자가 주소만으로 분석 대상을 찾고, Backend가 검증한 실제 필지를 지도에서 확인한 뒤, 기존 SITE analysis와 Rule Engine 결과를 신뢰 경계를 훼손하지 않고 이해하기 쉽게 확인할 수 있게 한다.

Frontend의 책임은 **선택, 확인, 표현**이다.

Backend의 책임은 **검증, SITE truth, 법규 판정**이다.


---

## 23. Product Workspace Direction — Single Parcel / Integrated Development

현재 구현된 workspace는 Single Parcel 분석이다. Single Parcel v1을 명확한 종료선까지 완성한 뒤, 향후 HOME에서 분석 목적을 선택하고 각 workspace로 진입하는 구조를 목표로 한다.

```text
HOME
├─ Single Parcel Development
│  └─ current verified-PNU SITE analysis workspace
└─ Integrated Development
   └─ future multi-PNU assembled-site workspace
```

Integrated Development는 단순한 "여러 개별 필지 동시 분석" UI가 아니다. 여러 VERIFIED parcel을 하나의 proposed development site로 구성하고, 합병 가능성·건축대지 구성·공동/통합개발 계획조건·혼재 규제·주변 context를 단계적으로 검토하는 별도 분석 흐름이다.

Frontend가 여러 parcel을 선택했다는 사실은 합병 가능, 하나의 법적 대지, 또는 target-level applicability를 의미하지 않는다. 해당 판정은 향후 Backend Analysis Target contract가 제공해야 한다.

## 24. Public Rule Detail Presentation Direction

PC rule-detail UX는 Backend의 product-safe public rule presentation model만 소비한다. Frontend는 raw `debug.rule_engine`, branch/registry/repair internals 또는 raw conditions를 제품 계약으로 사용하지 않는다.

정보 계층은 다음 방향을 따른다.

```text
Rule Summary
→ status filter / disclosure
→ law + rule title + paragraph/item/subitem
→ Backend applicability + reason
→ required / unresolved / blocking condition presentation
→ rule text / supported numeric effect
```

Frontend는 법령 조문번호, 공식 URL, legal conclusion을 원 데이터에 없는 형태로 합성하지 않는다. `UNKNOWN`과 `CONDITIONAL`의 의미도 Backend 계약을 그대로 보존한다.

모바일 전용 UX 개발/검증은 테스트 환경 준비 전까지 보류하며, 현재 제품 종료 검증은 PC FHD/QHD를 우선한다.
