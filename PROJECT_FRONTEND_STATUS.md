# AI 대지분석 자동화 시스템 — Frontend Status

## 1. 문서 역할

이 문서는 Frontend의 **실제 구현·검증 현황과 다음 작업**을 기록한다.

- Frontend 구조/UX 기준: `PROJECT_FRONTEND_ARCHITECTURE.md`
- Frontend 구현/검증 현황: `PROJECT_FRONTEND_STATUS.md`
- Backend/Core 구조 기준: `PROJECT_ARCHITECTURE.md`
- Backend 구현/검증 현황: `PROJECT_STATUS.md`

Architecture의 목표 상태와 실제 구현 상태를 혼동하지 않는다.

이 문서에서 `IMPLEMENTED`, `VERIFIED`, `PASS`는 실제 repository 구현 또는 실제 검증 근거가 확인된 경우에만 사용한다. 계획 또는 합의된 UX는 구현 완료로 기록하지 않는다.

---

## 2. Current Frontend Baseline

기준 branch:

```text
cleanup/repository-organization-20260916
```

Frontend Architecture 문서 분리 직전 확인 HEAD:

```text
a432c082fb7ea9bbd7635a2849e4136455a0d5c5
```

Frontend 문서 체계:

```text
PROJECT_FRONTEND_ARCHITECTURE.md
PROJECT_FRONTEND_STATUS.md
```

현재 제품 UX baseline:

```text
A안 — 지도 중심 UX
```

현재 Frontend application 구현 상태:

```text
NOT IMPLEMENTED
```

현재 repository 조사에서 재사용 가능한 기존 JavaScript Frontend framework 기반은 확인되지 않았다. 구체적인 framework/build tool/map provider는 아직 확정하지 않았다.

---

## 3. Confirmed Product Flow

설계 기준으로 확정된 MVP 흐름:

```text
주소 입력
    ↓
parcel candidate 검색
    ↓
candidate list <-> map marker
    ↓
candidate 선택
    ↓
Backend parcel verification
    ↓
verified parcel polygon
    ↓
사용자 필지 확인
    ↓
"이 필지 분석"
    ↓
selected-candidate full analysis
    ↓
result summary
    ↓
regulation detail / evidence
```

상태:

```text
DESIGN BASELINE CONFIRMED
IMPLEMENTATION NOT STARTED
```

---

## 4. Confirmed Backend Dependencies

Frontend 개발에서 실제 존재가 확인된 Backend 기반은 다음과 같다.

### Public API

```text
GET  /health
POST /v1/site-analysis
POST /v1/site-analysis/address
POST /v1/parcel-candidates/address
POST /v1/site-analysis/selected-candidate
```

### Candidate Discovery

`POST /v1/parcel-candidates/address`를 통해 주소 기반 candidate discovery가 가능하다.

Frontend candidate 표현에 필요한 주요 개념:

```text
candidate_pnu
parcel_address
road_address
building_name
x
y
```

Candidate는 discovery 결과이며 verified canonical parcel identity가 아니다.

### Selected Candidate Verification / Full Analysis

Backend에는 selected candidate의 PNU와 point를 live parcel polygon과 대조하여 검증하고, 검증 성공 후 기존 parcel analysis 경로로 연결하는 로직이 존재한다.

Full analysis public endpoint:

```text
POST /v1/site-analysis/selected-candidate
```

Frontend는 이 verification을 대체하거나 우회하지 않는다.

### Analysis Response

현재 public analysis response schema:

```text
SITE_ANALYSIS_API_V1
```

MVP result UI를 시작할 수 있는 site, land area, spatial, regulation, rule evaluation, requirements 등의 데이터 기반이 존재한다.

---

## 5. Confirmed Backend Behavioral Baseline Relevant to Frontend

실제 Backend 검증에서 확인된 selected-candidate 예시는 다음과 같다.

```text
서울특별시 강남구 개포동 12-2
candidate PNU: 1168010300100120002
x: 127.07662495509604
y: 37.49629354642009
```

해당 candidate는 live polygon PNU와 일치하는 경로로 검증되었고 기존 SITE analysis로 연결된 이력이 있다.

Frontend 개발 시 이 값은 실제 연동 회귀 확인에 사용할 수 있는 알려진 예시일 뿐, Frontend에 hard-code된 truth 또는 mock authority로 사용하지 않는다.

또한 Backend는 서로 다른 PNU의 저장 geometry를 재사용하지 않고 requested PNU 기준 live geometry verification을 수행한 검증 이력이 있다. Frontend도 동일하게 PNU가 바뀔 때 이전 verified geometry/result를 새 parcel에 승계하지 않아야 한다.

---

## 6. Frontend Implementation Status

| 영역 | 상태 | 설명 |
|---|---|---|
| Frontend architecture baseline | DOCUMENTED | A안 지도 중심 구조와 trust boundary 문서화 |
| Frontend status tracking | DOCUMENTED | 이 문서에서 실제 구현/검증 상태 관리 |
| Frontend framework | NOT DECIDED | 실제 요구사항 비교 후 결정 |
| Build tool | NOT DECIDED | framework 결정과 함께 확정 |
| Frontend directory | NOT IMPLEMENTED | 기존 reusable frontend base 확인되지 않음 |
| Address search UI | NOT IMPLEMENTED | Backend candidate API는 존재 |
| Candidate cards | NOT IMPLEMENTED | Backend candidate data는 존재 |
| Map UI | NOT IMPLEMENTED | provider 미확정 |
| Candidate list/map sync | NOT IMPLEMENTED | Architecture contract만 확정 |
| Parcel verification UI | NOT IMPLEMENTED | pre-analysis lightweight API 필요 |
| Verified polygon UI | NOT IMPLEMENTED | pre-analysis contract 미구현 |
| Full analysis UI | NOT IMPLEMENTED | Backend selected-candidate endpoint 존재 |
| Result summary | NOT IMPLEMENTED | SITE_ANALYSIS_API_V1 기반 가능 |
| Regulation detail/evidence UI | NOT IMPLEMENTED | presentation 설계 필요 |
| Error/empty/UNKNOWN UI | NOT IMPLEMENTED | Architecture 의미 규칙 확정 |
| Responsive UI | NOT IMPLEMENTED | Desktop split baseline만 확정 |

---

## 7. Current Backend Gap Blocking Full A안 Flow

A안의 핵심 흐름은 full analysis 전에 실제 parcel polygon을 보여주고 사용자가 분석 대상을 확인하는 것이다.

현재 확인된 Backend 공개 흐름은 candidate search와 selected-candidate full analysis를 제공하지만, 다음 중간 product boundary를 위한 lightweight public contract는 아직 구현된 것으로 확인되지 않았다.

```text
candidate selection
    ↓
lightweight live parcel verification
    ↓
verified parcel polygon/basic identity
    ↓
user confirmation
    ↓
full analysis
```

따라서 **lightweight parcel confirmation API**가 현재 A안 vertical slice의 가장 직접적인 Backend 보완 후보이다.

이 API는 새로운 SITE truth 또는 geometry truth 경로를 만들지 않고 기존 selected candidate verifier와 canonical parcel/geometry verification을 재사용해야 한다.

상태:

```text
REQUIRED FOR TARGET A안 FLOW
NOT YET IMPLEMENTED
```

---

## 8. Other Known Product Gaps

첫 Frontend MVP를 막지는 않지만 이후 보완이 필요한 항목:

```text
road-address support
machine-readable product error schema
presentation/result model
provider timeout/retry/cache/rate-limit handling
provider health / logging / partial-result policy
actual progress event/API
```

SaaS 기능인 authentication, project/history, organization, billing, usage, report management 등은 첫 vertical slice 범위 밖으로 유지한다.

---

## 9. Validation Policy

Frontend도 Backend와 동일한 evidence-first 원칙을 따른다.

```text
actual GitHub HEAD
    ↓
actual files
    ↓
actual API/contracts
    ↓
focused implementation
    ↓
focused contract/test
    ↓
GitHub save
    ↓
user local validation
    ↓
behavioral PASS
```

GitHub commit 성공만으로 Frontend behavioral PASS를 선언하지 않는다.

Mock-only UI 성공을 실제 Backend 연동 PASS로 기록하지 않는다.

실제 API와 연결되는 vertical slice는 사용자 로컬 환경에서 실행 결과를 확인한 뒤 PASS로 기록한다.

---

## 10. Protected Development Rules

Frontend 작업 때문에 Backend architecture를 우회하거나 두 번째 truth path를 만들지 않는다.

특히 다음을 유지한다.

```text
candidate marker != parcel truth
selected candidate != verified parcel
frontend selection != canonical identity
UNKNOWN != FALSE
```

Backend 보호 원칙:

```text
resolver result != parcel applicability
SITE-decision eligibility != SITE truth
SITE applicability admission != runtime registration authority
```

기존 Backend Architecture STEP 번호 체계를 Frontend 단계 번호로 재사용하거나 확장하지 않는다.

로컬 보호 파일:

```text
law_data/output/urban_area_conversion_history_final_resolution.json
```

Frontend 작업과 무관하며 수정, 복원, reset, checkout, 삭제, staging, commit 또는 clean 대상으로 삼지 않는다.

`.env`와 `law_data/output/*`도 명시적 별도 승인 없이 Frontend 작업 범위에 포함하지 않는다.

---

## 11. Current Validation Status

### Documentation

```text
PROJECT_FRONTEND_ARCHITECTURE.md
- created
- A안 map-centered baseline documented
- Backend trust boundary documented

PROJECT_FRONTEND_STATUS.md
- created as separate implementation/status ledger
```

### Frontend Runtime

```text
NOT STARTED
```

### Frontend Behavioral Validation

```text
NO PASS YET
```

이 상태는 정상이다. 아직 Frontend application을 구현하지 않았기 때문이다.

---

## 12. Next Development Target

다음 단계는 코드를 바로 생성하기 전에 **Frontend 기술 스택과 지도 provider를 READ-ONLY로 결정**하는 것이다.

검토 순서:

```text
1. 현재 Backend/FastAPI 연동 요구사항
2. A안 split-map UX 요구사항
3. GeoJSON Polygon/MultiPolygon 지원
4. candidate marker/list synchronization
5. responsive 요구사항
6. 개발·테스트 복잡도
7. repository와 배포 구조
8. framework/build tool 선택
9. map provider 선택
10. 최소 Frontend directory/write scope 제안
```

그 다음 Backend의 lightweight parcel confirmation API를 실제 코드 기준으로 조사하여 정확한 최소 WRITE scope를 제안한다.

---

## 13. Immediate Next Step Status

```text
CURRENT TASK:
Frontend technology stack + map provider decision

MODE:
READ-ONLY investigation / design

WRITE APPROVAL:
Not yet requested for application code
```

기술 선택 이후에도 실제 Frontend 파일 생성 전에는 생성/수정할 파일, 목적, 보호 영역을 명시하고 승인된 최소 범위만 WRITE한다.

---

## 14. Status Update Rule

이 문서는 다음 이벤트가 실제 발생했을 때 갱신한다.

- Frontend 기술 스택 확정
- Frontend directory/application 생성
- API client contract 구현
- map provider/component 구현
- candidate search vertical slice 구현
- parcel confirmation API 구현/연동
- full analysis 연동
- result presentation 구현
- focused test/contract PASS
- 사용자 로컬 behavioral PASS
- blocker 또는 architecture-impacting gap 발견

목표나 예상만으로 IMPLEMENTED/PASS 상태를 올리지 않는다.
