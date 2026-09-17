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

현재 Frontend application baseline HEAD:

```text
1bd5130272aa853ed927dd14a32a56c89cee9931
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
IMPLEMENTED — INITIAL SHELL + CANDIDATE SEARCH FOUNDATION
```

기술 스택:

```text
React
TypeScript
Vite
```

Frontend source는 Backend Python source와 분리된 독립 `frontend/` application root에서 관리한다.

MVP map provider는 Kakao Maps를 우선 검토하되 provider-neutral map adapter 경계를 유지한다. 실제 지도 SDK는 아직 도입하지 않았다.

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
BACKEND CONFIRMATION BOUNDARY IMPLEMENTED + USER LOCAL PASS
FRONTEND SHELL IMPLEMENTED + USER LOCAL BUILD PASS
RUNTIME BACKEND API INTEGRATION VALIDATION PENDING
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

### 2026-09-17 User Local Backend Behavioral Validation

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

## 6. Frontend Application Structure

현재 실제 repository에는 Backend와 분리된 다음 application root가 존재한다.

```text
frontend/
├─ .gitignore
├─ index.html
├─ package.json
├─ package-lock.json
├─ tsconfig.json
├─ tsconfig.app.json
├─ vite.config.ts
└─ src/
   ├─ App.tsx
   ├─ app.css
   ├─ main.tsx
   ├─ vite-env.d.ts
   ├─ api/
   │  └─ parcelCandidates.ts
   └─ types/
      └─ parcel.ts
```

생성물 관리:

```text
node_modules/   ignored
dist/           ignored
*.tsbuildinfo   ignored
package-lock.json tracked
```

Frontend dependency는 `frontend/package.json` / `frontend/package-lock.json`에서 관리하며 Python dependency와 섞지 않는다.

---

## 7. Frontend Implementation Status

| 영역 | 상태 | 설명 |
|---|---|---|
| Frontend architecture baseline | DOCUMENTED | A안 지도 중심 구조와 trust boundary 문서화 |
| Frontend status tracking | DOCUMENTED | 이 문서에서 실제 구현/검증 상태 관리 |
| Frontend framework | IMPLEMENTED | React + TypeScript + Vite |
| Frontend directory | IMPLEMENTED | 독립 `frontend/` application root |
| Frontend dependency lock | IMPLEMENTED | actual local npm resolution `package-lock.json` tracked |
| Frontend production build | USER LOCAL PASS | `tsc -b && vite build` 성공 |
| Address search UI | IMPLEMENTED FOUNDATION | 주소 입력/search state UI 존재 |
| Candidate API client | IMPLEMENTED | `POST /v1/parcel-candidates/address` client 존재 |
| Candidate response typing | IMPLEMENTED | `PARCEL_CANDIDATE_SEARCH_V1` frontend contract typing |
| Candidate cards | IMPLEMENTED FOUNDATION | response candidate 목록 표시 코드 존재 |
| Actual browser-to-Backend candidate search | NOT YET USER VALIDATED | Vite proxy + FastAPI runtime 통합 검증 필요 |
| Map provider | DECISION CANDIDATE | Kakao Maps 우선 검토; provider-neutral adapter 원칙 |
| Map UI | NOT IMPLEMENTED | 실제 SDK/dependency 미도입 |
| Candidate list/map sync | NOT IMPLEMENTED | Architecture contract만 확정 |
| Parcel confirmation Backend API | IMPLEMENTED + USER LOCAL PASS | `PARCEL_CONFIRMATION_V1` |
| Parcel verification UI | NOT IMPLEMENTED | Backend confirmation API 연결 가능 상태 |
| Verified polygon UI | NOT IMPLEMENTED | verified Polygon/MultiPolygon contract 확보 |
| Full analysis UI | NOT IMPLEMENTED | Backend selected-candidate endpoint 존재 |
| Result summary | NOT IMPLEMENTED | `SITE_ANALYSIS_API_V1` 기반 가능 |
| Regulation detail/evidence UI | NOT IMPLEMENTED | presentation 설계 필요 |
| Error/empty/UNKNOWN UI | PARTIAL FOUNDATION | candidate search empty/error state 존재; full product semantics 미완성 |
| Responsive UI | PARTIAL FOUNDATION | initial responsive styles 존재; map split 미구현 |

---

## 8. Frontend Local Build Validation

### Environment

사용자 로컬에서 확인된 runtime:

```text
Node.js v24.21.0
npm 11.19.0
```

Node executable:

```text
C:\Program Files\nodejs\node.exe
```

### Dependency Install

사용자 로컬 실행:

```text
npm install
```

결과:

```text
added 24 packages
found 0 vulnerabilities
```

실제 npm resolution으로 생성된 `frontend/package-lock.json`은 사용자가 정확한 파일만 stage하여 commit/push했다.

Commit:

```text
1bd5130272aa853ed927dd14a32a56c89cee9931
chore: lock frontend dependencies
```

### Production Build

초기 build에서 Vite client declaration 누락으로 다음 TypeScript 오류가 발생했다.

```text
TS2882: Cannot find module or type declarations for side-effect import of './app.css'
```

이에 Frontend 범위에서 다음을 추가했다.

```text
frontend/src/vite-env.d.ts
frontend/.gitignore
```

그 후 사용자가 다시 실행:

```text
npm run build
```

실제 결과:

```text
> site-ai-frontend@0.1.0 build
> tsc -b && vite build

vite v8.3.0 building client environment for production...
✓ 17 modules transformed.
computing gzip size...
dist/index.html                   0.49 kB │ gzip:  0.33 kB
dist/assets/index-Cq8pTj30.css    2.50 kB │ gzip:  0.98 kB
dist/assets/index-Dbhrtih3.js   223.15 kB │ gzip: 70.19 kB

✓ built in 1.22s
```

검증 후 `git status --short`에는 보호 파일과 아직 commit 전이던 `frontend/package-lock.json`만 남았고, package-lock은 이후 사용자 commit/push로 정상 추적됐다.

따라서 현재 Frontend shell은 **USER LOCAL BUILD PASS** 상태이다.

이 PASS는 production compile/build에 대한 PASS이며, 실제 브라우저에서 FastAPI를 호출하는 runtime integration PASS와는 구분한다.

---

## 9. A안 Backend Readiness

A안 vertical slice의 직접 Backend blocker였던 lightweight parcel confirmation public contract는 구현되고 사용자 로컬 검증까지 완료됐다.

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

---

## 10. Other Known Product Gaps

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

## 11. Validation Policy

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

Production build PASS를 runtime Backend integration PASS로 확대 해석하지 않는다.

Mock-only UI 성공을 실제 Backend 연동 PASS로 기록하지 않는다.

---

## 12. Frontend / Backend Repository Separation Rule

Frontend source code는 Backend Python source와 혼합하지 않는다.

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
   ├─ package-lock.json
   ├─ TypeScript / Vite configuration
   └─ src/
      ├─ api/
      ├─ components/
      ├─ features/
      ├─ map/
      └─ types/
```

Frontend와 Backend의 runtime 연결은 HTTP/JSON public API boundary를 사용한다. Frontend가 Python module을 직접 import하거나 Backend verification logic을 TypeScript로 복제하지 않는다.

---

## 13. Protected Development Rules

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

## 14. Current Validation Status

### Backend Boundary Required by Frontend A안

```text
Candidate search                         IMPLEMENTED
Lightweight parcel confirmation          IMPLEMENTED
Verified Polygon/MultiPolygon contract   IMPLEMENTED
Selected-candidate full analysis         IMPLEMENTED
```

Focused Backend local contract validation:

```text
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_CONFIRMATION_CONTRACT_PASS
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_CONTRACT_PASS
```

### Frontend Shell

```text
React + TypeScript + Vite application    IMPLEMENTED
npm dependency installation              PASS
TypeScript production compile            PASS
Vite production build                    PASS
package-lock tracking                     IMPLEMENTED
```

### Frontend Runtime Integration

```text
Browser rendering                         NOT YET USER VALIDATED
Vite -> FastAPI proxy                     NOT YET USER VALIDATED
Real candidate API search                 NOT YET USER VALIDATED
```

---

## 15. Next Development Target

다음 목표는 **첫 실제 browser-to-Backend runtime integration을 검증하는 것**이다.

검증 대상:

```text
FastAPI backend running on 127.0.0.1:8000
    ↑
Vite dev proxy
    ↑
React candidate search UI
    ↓
POST /v1/parcel-candidates/address
    ↓
real candidate results rendered in browser
```

이 단계에서는 아직 Kakao Maps SDK를 추가하지 않는다.

먼저 다음을 실제 사용자 로컬 환경에서 확인한다.

```text
1. FastAPI server 정상 기동
2. Vite frontend dev server 정상 기동
3. 브라우저에서 Frontend UI 표시
4. 실제 지번주소 검색
5. Backend candidate response 성공
6. candidate cards 표시
7. SEARCHING / SEARCH_RESULTS / SEARCH_EMPTY / SEARCH_ERROR 상태가 예상대로 동작
```

실제 runtime integration PASS 이후 map provider / map adapter 단계로 이동한다.

---

## 16. Immediate Next Step Status

```text
CURRENT TASK:
User local browser-to-Backend candidate search runtime validation

MODE:
VALIDATION FIRST

CURRENT FRONTEND STATUS:
USER LOCAL BUILD PASS

NEXT WRITE:
Runtime validation 결과에 따라 결정
```

---

## 17. Status Update Rule

이 문서는 다음 이벤트가 실제 발생했을 때 갱신한다.

- Frontend technology stack 확정 및 dependency 생성
- `frontend/` application 생성
- API client contract 구현
- candidate search vertical slice 구현
- Frontend production build PASS
- browser-to-Backend candidate search runtime PASS
- map provider/component 구현
- parcel confirmation API Frontend 연동
- verified polygon rendering
- full analysis 연동
- result presentation 구현
- focused test/contract PASS
- 사용자 로컬 behavioral PASS
- blocker 또는 architecture-impacting gap 발견

목표나 예상만으로 IMPLEMENTED/PASS 상태를 올리지 않는다.
