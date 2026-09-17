# AI 대지분석 자동화 시스템 — Frontend Status

## 1. 문서 역할

이 문서는 Frontend의 실제 구현·검증 현황과 다음 작업을 기록한다.

- Frontend 구조/UX 기준: `PROJECT_FRONTEND_ARCHITECTURE.md`
- Frontend 구현/검증 현황: `PROJECT_FRONTEND_STATUS.md`
- Backend/Core 구조 기준: `PROJECT_ARCHITECTURE.md`
- Backend 구현/검증 현황: `PROJECT_STATUS.md`

Architecture의 목표 상태와 실제 구현 상태를 혼동하지 않는다. `IMPLEMENTED`, `VERIFIED`, `PASS`는 실제 repository 구현 또는 실제 검증 근거가 확인된 경우에만 사용한다.

---

## 2. Current Frontend Baseline

기준 branch:

```text
cleanup/repository-organization-20260916
```

현재 제품 UX baseline:

```text
A안 — 지도 중심 UX
```

기술 스택:

```text
React + TypeScript + Vite
```

Frontend source는 Backend Python source와 분리된 독립 `frontend/` application root에서 관리한다. Frontend와 Backend의 연결은 HTTP/JSON public API boundary만 사용한다.

현재 상태:

```text
FRONTEND SHELL                         IMPLEMENTED + USER LOCAL BUILD PASS
CANDIDATE SEARCH UI                    IMPLEMENTED + USER LOCAL RUNTIME PASS
BROWSER -> VITE -> FASTAPI INTEGRATION USER LOCAL RUNTIME PASS
MAP / PARCEL CONFIRMATION UI           NOT IMPLEMENTED
```

---

## 3. Confirmed Product Flow

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

현재 첫 구간인 `주소 입력 → 실제 candidate 검색 → candidate card 렌더링`까지 사용자 로컬 runtime 검증이 완료됐다.

---

## 4. Confirmed Backend Dependencies

현재 Frontend에서 사용할 수 있는 public API:

```text
GET  /health
POST /v1/site-analysis
POST /v1/site-analysis/address
POST /v1/parcel-candidates/address
POST /v1/parcel-candidates/confirm
POST /v1/site-analysis/selected-candidate
```

Candidate는 discovery 결과이며 verified canonical parcel identity가 아니다.

`POST /v1/parcel-candidates/confirm` 성공 contract:

```text
schema_version = PARCEL_CONFIRMATION_V1
status = READY
parcel = verified parcel identity + selected point + CRS
verification.status = VERIFIED
verification.resolution = SELECTED_PARCEL_CANDIDATE_VERIFIED
geometry = verification에 실제 사용된 Polygon 또는 MultiPolygon
```

Frontend는 이 Backend 검증 결과만 verified parcel polygon으로 취급한다. Pre-analysis confirmation은 full selected-candidate analysis의 재검증을 대체하지 않는다.

---

## 5. Backend Behavioral Baseline Relevant to Frontend

2026-09-17 사용자 로컬 Backend contract validation:

```text
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_CONFIRMATION_CONTRACT_PASS
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_CONTRACT_PASS
```

검증된 실제 예시:

```text
서울특별시 강남구 개포동 12-2
candidate PNU: 1168010300100120002
x: 127.07662495509604
y: 37.49629354642009
```

Backend는 서로 다른 PNU의 저장 geometry를 재사용하지 않고 requested PNU 기준 live geometry verification을 수행한다. Frontend도 PNU가 바뀌면 이전 verified geometry/result를 새 parcel에 승계하지 않는다.

---

## 6. Frontend Application Structure

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

---

## 7. Frontend Implementation Status

| 영역 | 상태 | 설명 |
|---|---|---|
| Frontend architecture baseline | DOCUMENTED | A안 지도 중심 구조와 trust boundary 문서화 |
| Frontend framework | IMPLEMENTED | React + TypeScript + Vite |
| Frontend directory | IMPLEMENTED | 독립 `frontend/` application root |
| Frontend dependency lock | IMPLEMENTED | actual local npm resolution lockfile tracked |
| Frontend production build | USER LOCAL PASS | `tsc -b && vite build` 성공 |
| Address search UI | IMPLEMENTED + USER LOCAL PASS | 실제 브라우저 렌더링 확인 |
| Candidate API client | IMPLEMENTED + USER LOCAL PASS | 실제 FastAPI 호출 확인 |
| Candidate response typing | IMPLEMENTED | `PARCEL_CANDIDATE_SEARCH_V1` typing |
| Candidate cards | IMPLEMENTED + USER LOCAL PASS | 실제 검색 결과 1건 렌더링 확인 |
| Browser-to-Backend candidate search | USER LOCAL RUNTIME PASS | Vite proxy → FastAPI `200 OK` 확인 |
| Map provider | DECISION CANDIDATE | Kakao Maps 우선 검토; provider-neutral adapter 원칙 |
| Map UI | NOT IMPLEMENTED | 실제 SDK/dependency 미도입 |
| Candidate list/map sync | NOT IMPLEMENTED | Architecture contract만 확정 |
| Parcel confirmation Backend API | IMPLEMENTED + USER LOCAL PASS | `PARCEL_CONFIRMATION_V1` |
| Parcel verification UI | NOT IMPLEMENTED | 다음 구현 대상 |
| Verified polygon UI | NOT IMPLEMENTED | verified Polygon/MultiPolygon contract 확보 |
| Full analysis UI | NOT IMPLEMENTED | Backend selected-candidate endpoint 존재 |
| Result summary | NOT IMPLEMENTED | `SITE_ANALYSIS_API_V1` 기반 가능 |
| Error/empty/UNKNOWN UI | PARTIAL FOUNDATION | candidate search 상태 UI 존재; 전체 의미 규칙 미완성 |

---

## 8. Frontend Local Build Validation

사용자 로컬 runtime:

```text
Node.js v24.21.0
npm 11.19.0
Vite v8.3.0
```

`npm install` 결과:

```text
added 24 packages
found 0 vulnerabilities
```

초기 production build에서는 `./app.css` side-effect import에 대한 Vite client declaration 누락으로 `TS2882`가 발생했다. `frontend/src/vite-env.d.ts`를 추가한 뒤 사용자 로컬에서 다시 실행한 결과:

```text
> tsc -b && vite build
✓ 17 modules transformed.
✓ built in 1.22s
```

따라서 Frontend shell production build는 **USER LOCAL BUILD PASS**이다.

실제 npm resolution으로 생성된 `frontend/package-lock.json`은 사용자가 정확한 파일만 stage/commit/push했다.

```text
1bd5130272aa853ed927dd14a32a56c89cee9931
chore: lock frontend dependencies
```

---

## 9. Browser-to-Backend Candidate Search Runtime Validation

### 2026-09-17 User Local Runtime Validation

Backend:

```text
python -m uvicorn api_app:app --host 127.0.0.1 --port 8000
```

확인 결과:

```text
Application startup complete.
Uvicorn running on http://127.0.0.1:8000
```

Frontend:

```text
npm run dev
```

확인 결과:

```text
VITE v8.3.0 ready
Local: http://localhost:5173/
```

브라우저에서 실제 Frontend UI가 정상 렌더링됐다.

실제 검색 입력:

```text
서울특별시 강남구 개포동 12-2
```

Frontend 결과:

```text
1개의 필지 후보를 찾았습니다.
서울특별시 강남구 개포동 12-2
개포자이
개포로109길 69
후보 위치 · EPSG:4326
```

Backend 실제 request log:

```text
POST /v1/parcel-candidates/address HTTP/1.1 200 OK
```

사용자 확인:

```text
1. Frontend 화면 정상 표시
2. 검색 오류 미발생
3. 실제 candidate card 정상 표시
```

따라서 다음 경계는 **USER LOCAL RUNTIME PASS**로 기록한다.

```text
Browser
→ React
→ Vite dev server
→ Vite proxy
→ FastAPI
→ POST /v1/parcel-candidates/address
→ real candidate response
→ candidate card rendering
```

이 PASS는 candidate discovery runtime 경계에 대한 것이다. Candidate는 여전히 discovery 결과이며 verified parcel truth가 아니다.

---

## 10. A안 Backend Readiness

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

Backend confirmation boundary는 구현 및 사용자 로컬 behavioral PASS 상태다. 다음 Frontend 작업은 이 기존 경계를 소비해야 하며 새로운 truth path를 만들지 않는다.

---

## 11. Validation Policy

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

GitHub commit 성공만으로 Frontend behavioral PASS를 선언하지 않는다. Production build PASS와 runtime Backend integration PASS도 구분한다. Mock-only UI 성공을 실제 Backend 연동 PASS로 기록하지 않는다.

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
```

Frontend dependency는 `frontend/package.json` / `frontend/package-lock.json`에서 관리한다. Frontend가 Python module을 직접 import하거나 Backend verification logic을 TypeScript로 복제하지 않는다.

---

## 13. Protected Development Rules

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

Frontend 작업과 무관하며 수정, 복원, reset, checkout, 삭제, staging, commit 또는 clean 대상으로 삼지 않는다. `.env`와 `law_data/output/*`도 명시적 별도 승인 없이 Frontend 작업 범위에 포함하지 않는다.

---

## 14. Current Validation Status

```text
Backend candidate search                    IMPLEMENTED
Backend lightweight parcel confirmation     IMPLEMENTED + USER LOCAL PASS
Backend verified Polygon/MultiPolygon       IMPLEMENTED
Backend selected-candidate full analysis    IMPLEMENTED + USER LOCAL PASS

Frontend React/TypeScript/Vite shell        IMPLEMENTED
Frontend production build                   USER LOCAL PASS
Browser rendering                           USER LOCAL RUNTIME PASS
Vite -> FastAPI proxy                       USER LOCAL RUNTIME PASS
Real candidate API search                   USER LOCAL RUNTIME PASS
Real candidate card rendering               USER LOCAL RUNTIME PASS

Candidate selection UI                      NOT IMPLEMENTED
Parcel confirmation Frontend integration    NOT IMPLEMENTED
Map adapter/provider                        NOT IMPLEMENTED
Verified polygon rendering                  NOT IMPLEMENTED
```

---

## 15. Next Development Target

다음 목표는 **candidate 선택 → Backend parcel confirmation → verified parcel 상태**를 Frontend에 연결하고, 지도 표시를 위한 provider-neutral 경계를 준비하는 것이다.

다음 vertical slice의 논리 흐름:

```text
real candidate card
    ↓ user selection
selected candidate
    ↓
POST /v1/parcel-candidates/confirm
    ↓
PARCEL_CONFIRMATION_V1
    ↓
VERIFIED parcel identity + Polygon/MultiPolygon
    ↓
Frontend verified parcel state
    ↓
map adapter/provider rendering
```

구현 시에도 candidate marker를 verified polygon으로 간주하지 않는다. verified geometry는 Backend confirmation response에서만 받는다.

Map provider는 Kakao Maps를 우선 검토하되 provider-neutral adapter boundary를 유지한다. 실제 SDK/API 세부사항은 구현 직전 공식 문서를 다시 확인한다.

---

## 16. Other Known Product Gaps

```text
road-address support
machine-readable product error schema
presentation/result model
provider timeout/retry/cache/rate-limit handling
provider health / logging / partial-result policy
actual progress event/API
```

Authentication, project/history, organization, billing, usage, report management 등은 첫 vertical slice 범위 밖이다.

---

## 17. Immediate Next Step Status

```text
CURRENT TASK:
Candidate selection + parcel confirmation Frontend integration design/implementation

CURRENT FRONTEND STATUS:
CANDIDATE SEARCH USER LOCAL RUNTIME PASS

NEXT WRITE:
Must inspect actual frontend files and define minimal approved scope before implementation
```

---

## 18. Status Update Rule

이 문서는 실제 이벤트가 발생했을 때만 갱신한다. 목표나 예상만으로 IMPLEMENTED/PASS 상태를 올리지 않는다.
