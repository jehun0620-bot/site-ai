# AI 대지분석 자동화 시스템 — Frontend Status

## 1. 문서 역할

이 문서는 Frontend의 **실제 구현·검증 현황과 다음 작업**을 기록한다.

- Frontend 구조/UX 기준: `PROJECT_FRONTEND_ARCHITECTURE.md`
- Frontend 구현/검증 현황: `PROJECT_FRONTEND_STATUS.md`
- Backend/Core 구조 기준: `PROJECT_ARCHITECTURE.md`
- Backend 구현/검증 현황: `PROJECT_STATUS.md`

Architecture의 목표 상태와 실제 구현 상태를 혼동하지 않는다.

`IMPLEMENTED`, `VERIFIED`, `PASS`는 실제 repository 구현 또는 실제 검증 근거가 확인된 경우에만 사용한다. 계획 또는 합의된 UX는 구현 완료로 기록하지 않는다.

---

## 2. Current Frontend Baseline

기준 branch:

```text
cleanup/repository-organization-20260916
```

Frontend application 구현 시작 전 Backend confirmation behavioral baseline HEAD:

```text
44876524289401f82dc4b23d87d84822fb57df58
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

기술 방향 검토 결과는 React + TypeScript + Vite를 우선안으로 하고, MVP map provider는 Kakao Maps를 우선 검토하되 provider-neutral map adapter 경계를 유지하는 것이다. 실제 Frontend application/dependency는 아직 생성하지 않았다.

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
Backend parcel confirmation
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
BACKEND CONFIRMATION BOUNDARY IMPLEMENTED + LOCALLY VERIFIED
FRONTEND IMPLEMENTATION NOT STARTED
```

---

## 4. Confirmed Backend Dependencies

Frontend 개발에서 실제 존재가 확인된 public API:

```text
GET  /health
POST /v1/site-analysis
POST /v1/site-analysis/address
POST /v1/parcel-candidates/address
POST /v1/parcel-candidates/confirm
POST /v1/site-analysis/selected-candidate
```

### Candidate Discovery

`POST /v1/parcel-candidates/address`는 주소 기반 candidate discovery를 제공한다.

Frontend candidate 표현의 주요 개념:

```text
candidate_pnu
parcel_address
road_address
building_name
x
y
```

Candidate는 discovery 결과이며 verified canonical parcel identity가 아니다.

### Lightweight Parcel Confirmation

`POST /v1/parcel-candidates/confirm`은 선택 candidate의 PNU와 EPSG:4326 point를 Backend verifier로 검증한다.

검증 성공 response contract:

```text
schema_version = PARCEL_CONFIRMATION_V1
status = READY
parcel = verified parcel identity + selected point + CRS
verification.status = VERIFIED
verification.resolution = SELECTED_PARCEL_CANDIDATE_VERIFIED
geometry = verification에 실제 사용된 Polygon 또는 MultiPolygon
```

이 endpoint는 full SITE analysis를 실행하지 않는다. candidate 선택 후 사용자가 실제 필지 경계를 확인하기 위한 lightweight product boundary이다.

Frontend는 반환된 verified geometry만 실제 parcel polygon으로 표현하며 candidate marker 자체를 parcel truth로 승격하지 않는다.

### Selected Candidate Full Analysis

`POST /v1/site-analysis/selected-candidate`는 선택 candidate를 다시 검증한 뒤 기존 SITE analysis 경로로 연결한다.

Pre-analysis confirmation 성공은 full analysis verification을 대체하지 않는다.

### Analysis Response

현재 public analysis response schema:

```text
SITE_ANALYSIS_API_V1
```

MVP result UI를 시작할 수 있는 site, land area, spatial, regulation, rule evaluation, requirements 등의 데이터 기반이 존재한다.

---

## 5. Confirmed Backend Behavioral Baseline Relevant to Frontend

실제 selected-candidate 검증 예시:

```text
서울특별시 강남구 개포동 12-2
candidate PNU: 1168010300100120002
x: 127.07662495509604
y: 37.49629354642009
```

해당 candidate는 live polygon PNU와 일치하는 경로로 검증되고 기존 SITE analysis로 연결된 이력이 있다.

Frontend에 hard-code된 truth 또는 mock authority로 사용하지 않는다.

Backend는 서로 다른 PNU의 저장 geometry를 재사용하지 않고 requested PNU 기준 live geometry verification을 수행한다. Frontend도 PNU가 바뀌면 이전 verified geometry/result를 새 parcel에 승계하지 않아야 한다.

### 2026-09-17 User Local Behavioral Validation

사용자가 local root `D:\site-ai`에서 working branch를 다음 HEAD까지 fast-forward한 뒤 직접 검증했다.

```text
44876524289401f82dc4b23d87d84822fb57df58
```

실행 결과:

```text
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_CONFIRMATION_CONTRACT_PASS
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_CONTRACT_PASS
```

검증 후 `git status --short`에는 의도적으로 보호 중인 다음 파일만 modified 상태로 남아 있었다.

```text
M law_data/output/urban_area_conversion_history_final_resolution.json
```

따라서 lightweight parcel confirmation public contract와 기존 selected-candidate full analysis public contract의 공존은 **USER LOCAL BEHAVIORAL PASS**로 기록한다.

---

## 6. Frontend Implementation Status

| 영역 | 상태 | 설명 |
|---|---|---|
| Frontend architecture baseline | DOCUMENTED | A안 지도 중심 구조와 trust boundary 문서화 |
| Frontend status tracking | DOCUMENTED | 이 문서에서 실제 구현/검증 상태 관리 |
| Frontend framework | DECISION CANDIDATE | React + TypeScript + Vite 우선안; application 미생성 |
| Map provider | DECISION CANDIDATE | Kakao Maps MVP 우선 검토; provider-neutral adapter 원칙 |
| Frontend directory | NOT IMPLEMENTED | Backend와 분리된 `frontend/` root 생성 예정 |
| Address search UI | NOT IMPLEMENTED | Backend candidate API 존재 |
| Candidate cards | NOT IMPLEMENTED | Backend candidate data 존재 |
| Map UI | NOT IMPLEMENTED | 실제 SDK/dependency 미도입 |
| Candidate list/map sync | NOT IMPLEMENTED | Architecture contract만 확정 |
| Parcel confirmation Backend API | IMPLEMENTED + USER LOCAL PASS | `PARCEL_CONFIRMATION_V1` |
| Parcel verification UI | NOT IMPLEMENTED | Backend confirmation API 연결 가능 상태 |
| Verified polygon UI | NOT IMPLEMENTED | verified Polygon/MultiPolygon contract 확보 |
| Full analysis UI | NOT IMPLEMENTED | Backend selected-candidate endpoint 존재 |
| Result summary | NOT IMPLEMENTED | `SITE_ANALYSIS_API_V1` 기반 가능 |
| Regulation detail/evidence UI | NOT IMPLEMENTED | presentation 설계 필요 |
| Error/empty/UNKNOWN UI | NOT IMPLEMENTED | Architecture 의미 규칙 확정 |
| Responsive UI | NOT IMPLEMENTED | Desktop split baseline 확정 |

---

## 7. A안 Backend Readiness

이전에 A안 vertical slice의 직접 blocker였던 lightweight parcel confirmation public contract는 구현되고 사용자 로컬 검증까지 완료됐다.

현재 Backend 경계:

```text
candidate search
    ↓
selected candidate
    ↓
POST /v1/parcel-candidates/confirm
    ↓
verified parcel identity + Polygon/MultiPolygon
    ↓
Frontend user confirmation
    ↓
POST /v1/site-analysis/selected-candidate
    ↓
full SITE analysis
```

상태:

```text
BACKEND CONFIRMATION BOUNDARY READY
USER LOCAL BEHAVIORAL PASS
```

따라서 다음 직접 작업은 Backend truth path 추가가 아니라 독립 Frontend application root 생성과 실제 API consumption이다.

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

---

## 10. Frontend / Backend Repository Separation Rule

Frontend source code는 Backend Python source와 혼합하지 않는다.

목표 repository 경계:

```text
D:\site-ai
├─ api_app.py
├─ site_data/
├─ law_data/
├─ regulations/
├─ requirements.txt
│
└─ frontend/
   ├─ package.json
   ├─ TypeScript / Vite configuration
   └─ src/
      ├─ api/
      ├─ components/
      ├─ features/
      ├─ map/
      └─ types/
```

Frontend dependency는 `frontend/package.json`에서 관리하고 Python dependency는 기존 Backend dependency 체계에 유지한다.

Frontend와 Backend의 runtime 연결은 HTTP/JSON public API boundary를 사용한다. Frontend가 Python module을 직접 import하거나 Backend verification logic을 TypeScript로 복제하지 않는다.

---

## 11. Protected Development Rules

Frontend 작업 때문에 Backend architecture를 우회하거나 두 번째 truth path를 만들지 않는다.

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

## 12. Current Validation Status

### Backend Boundary Required by Frontend A안

```text
Candidate search                         IMPLEMENTED
Lightweight parcel confirmation          IMPLEMENTED
Verified Polygon/MultiPolygon contract   IMPLEMENTED
Selected-candidate full analysis         IMPLEMENTED
```

Focused local contract validation:

```text
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_CONFIRMATION_CONTRACT_PASS
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_CONTRACT_PASS
```

### Frontend Runtime

```text
NOT STARTED
```

### Frontend Behavioral Validation

```text
NO FRONTEND PASS YET
```

Frontend application이 아직 존재하지 않으므로 정상 상태다.

---

## 13. Next Development Target

다음 목표는 **Backend와 명확히 분리된 `frontend/` application root를 생성하고 첫 실제 vertical slice를 시작하는 것**이다.

첫 Frontend implementation scope의 방향:

```text
frontend/
    ↓
React + TypeScript + Vite shell
    ↓
Frontend-owned API types/client
    ↓
POST /v1/parcel-candidates/address 연결
    ↓
주소 검색 UI
    ↓
실제 candidate result state / cards
```

첫 shell 단계에서는 지도 SDK와 API key 문제를 동시에 섞지 않는다. Candidate search가 실제 FastAPI contract와 연결되는 것을 먼저 검증한 뒤 map adapter/provider integration으로 이동한다.

Frontend 코드를 root Python 영역, `site_data/`, `law_data/`, `regulations/` 안에 생성하지 않는다.

---

## 14. Immediate Next Step Status

```text
CURRENT TASK:
Create isolated frontend/ application root and candidate-search vertical slice foundation

MODE:
WRITE scope must be explicitly approved before application files are created

BACKEND PRECONDITION:
READY + USER LOCAL BEHAVIORAL PASS
```

---

## 15. Status Update Rule

이 문서는 다음 이벤트가 실제 발생했을 때 갱신한다.

- Frontend technology stack 확정 및 dependency 생성
- `frontend/` application 생성
- API client contract 구현
- candidate search vertical slice 구현
- map provider/component 구현
- parcel confirmation API Frontend 연동
- verified polygon rendering
- full analysis 연동
- result presentation 구현
- focused test/contract PASS
- 사용자 로컬 behavioral PASS
- blocker 또는 architecture-impacting gap 발견

목표나 예상만으로 IMPLEMENTED/PASS 상태를 올리지 않는다.
