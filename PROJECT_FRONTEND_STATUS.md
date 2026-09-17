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

제품 UX baseline:

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
CANDIDATE SEARCH                       IMPLEMENTED + USER LOCAL RUNTIME PASS
CANDIDATE SELECTION                    IMPLEMENTED + USER LOCAL RUNTIME PASS
PARCEL CONFIRMATION FRONTEND           IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
VERIFIED PARCEL STATE                  IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
MAP / VERIFIED POLYGON RENDERING       IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
DETAILED SITE ANALYSIS RESULT UI       IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
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
detailed result presentation
```

현재 사용자 로컬에서 다음 구간까지 실제 runtime/behavioral 검증이 완료됐다.

```text
주소 입력
→ candidate 검색
→ candidate card 렌더링
→ candidate 선택
→ Backend parcel confirmation
→ VERIFIED parcel identity + geometry 수신
→ Frontend VERIFIED 상태 표시
→ selected-candidate full analysis
→ SITE_ANALYSIS_API_V1
→ detailed result UI
```

---

## 4. Confirmed Backend Dependencies

현재 Frontend에서 사용하는/사용 가능한 public API:

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

Frontend는 Backend confirmation response의 verified geometry만 실제 parcel polygon으로 취급한다. Pre-analysis confirmation은 full selected-candidate analysis의 재검증을 대체하지 않는다.

---

## 5. Backend Behavioral Baseline Relevant to Frontend

Backend focused contract validation:

```text
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_CONFIRMATION_CONTRACT_PASS
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_CONTRACT_PASS
```

실제 검증 예시:

```text
서울특별시 강남구 개포동 12-2
candidate PNU: 1168010300100120002
x: 127.07662495509604
y: 37.49629354642009
```

Backend는 서로 다른 PNU의 저장 geometry를 재사용하지 않고 requested PNU 기준 live geometry verification을 수행한다. Frontend도 새 검색 시작 시 이전 selected candidate, confirmation, verified geometry state를 폐기한다.

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
   │  ├─ parcelCandidates.ts
   │  └─ siteAnalysis.ts
   ├─ map/
   │  ├─ MapAdapter.ts
   │  └─ KakaoMap.tsx
   └─ types/
      ├─ parcel.ts
      └─ siteAnalysis.ts
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
| Frontend production build | USER LOCAL PASS | 상세 결과 UI 포함 `tsc -b && vite build` 성공 |
| Address search UI | IMPLEMENTED + USER LOCAL PASS | 실제 브라우저 렌더링 확인 |
| Candidate API client | IMPLEMENTED + USER LOCAL PASS | 실제 FastAPI 호출 확인 |
| Candidate cards | IMPLEMENTED + USER LOCAL PASS | 실제 candidate 렌더링 확인 |
| Browser-to-Backend candidate search | USER LOCAL RUNTIME PASS | Vite proxy → FastAPI `200 OK` |
| Candidate selection UI | IMPLEMENTED + USER LOCAL PASS | 실제 candidate card 클릭 확인 |
| Parcel confirmation API client | IMPLEMENTED + USER LOCAL PASS | `/v1/parcel-candidates/confirm` 실제 `200 OK` |
| Parcel confirmation response typing | IMPLEMENTED | `PARCEL_CONFIRMATION_V1`, VERIFIED, Polygon/MultiPolygon contract |
| Verified parcel state | IMPLEMENTED + USER LOCAL PASS | PNU/geometry type/CRS 표시 확인 |
| Previous parcel state invalidation | IMPLEMENTED | 새 검색 시작 시 이전 selection/confirmation 제거 |
| Map provider | IMPLEMENTED + USER LOCAL PASS | Kakao Maps SDK 실제 브라우저 로딩 확인; provider-neutral adapter 유지 |
| Map UI | IMPLEMENTED + USER LOCAL PASS | Kakao Maps 실제 지도 렌더링 확인 |
| Candidate list/map sync | NOT IMPLEMENTED | Architecture contract만 확정 |
| Verified polygon rendering | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | Backend VERIFIED MultiPolygon 실제 지도 렌더링 확인 |
| Full analysis UI | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 실제 selected-candidate 분석 요청 및 SITE_ANALYSIS_API_V1 결과 표시 확인 |
| Detailed result UI | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 대지면적/건폐율/용적률/법규 집계/추가 입력/외부 확인정보 실제 표시 확인 |
| Result summary | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 실제 Backend 상세 결과를 사용자 화면에 표시 확인 |
| Error/empty/UNKNOWN UI | PARTIAL FOUNDATION | UNKNOWN은 `확인 필요`로 유지; 전체 product semantics/UX는 추가 개선 필요 |

---

## 8. Frontend Build Validation

사용자 로컬 runtime:

```text
Node.js v24.21.0
npm 11.19.0
Vite v8.3.0
```

상세 결과 UI 구현 후 2026-09-17 사용자 로컬 production build:

```text
> site-ai-frontend@0.1.0 build
> tsc -b && vite build

vite v8.3.0 building client environment for production...
✓ 20 modules transformed.
dist/index.html                   0.49 kB │ gzip: 0.33 kB
dist/assets/index-D77GtQKV.css   5.42 kB │ gzip: 1.68 kB
dist/assets/index-BLUNFI47.js  238.65 kB │ gzip: 74.05 kB
✓ built in 89ms
```

검증 HEAD:

```text
7947b88e8ac6b52ab2e64a451137e768770ef16a
```

따라서 상세 결과 UI가 포함된 Frontend production build는 **USER LOCAL BUILD PASS**이다.

---

## 9. Candidate Search Runtime Validation

2026-09-17 사용자 로컬에서 다음 실제 경계가 검증됐다.

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

실제 검색:

```text
서울특별시 강남구 개포동 12-2
```

Backend log:

```text
POST /v1/parcel-candidates/address HTTP/1.1 200 OK
```

상태:

```text
USER LOCAL RUNTIME PASS
```

---

## 10. Parcel Confirmation Frontend Runtime Validation

### 2026-09-17 User Local Behavioral Validation

검증 HEAD:

```text
862812cbd5eb0e7a024191f954fcb278c18c5a83
```

사용자는 실제 candidate card를 선택했다.

Frontend 화면에서 확인된 결과:

```text
필지 확인 완료
VERIFIED

지번주소  서울특별시 강남구 개포동 12-2
PNU       1168010300100120002
경계 형식  MultiPolygon
좌표계     EPSG:4326
```

Backend 실제 request log:

```text
POST /v1/parcel-candidates/address HTTP/1.1 200 OK
POST /v1/parcel-candidates/confirm HTTP/1.1 200 OK
```

따라서 다음 경계는 **USER LOCAL BEHAVIORAL PASS**로 기록한다.

```text
real candidate
→ user selection
→ POST /v1/parcel-candidates/confirm
→ Backend live parcel verification
→ PARCEL_CONFIRMATION_V1
→ VERIFIED parcel identity
→ MultiPolygon geometry
→ Frontend verified parcel state
```

이 PASS는 Frontend가 parcel truth를 생성했다는 의미가 아니다. Parcel truth authority는 계속 Backend verification boundary에 있다.

---

## 11. A안 Backend / Frontend Boundary

현재 실제 연결 상태:

```text
candidate search                         PASS
    ↓
candidate selection                      PASS
    ↓
Backend parcel confirmation              PASS
    ↓
verified parcel identity + geometry      PASS
    ↓
map rendering                            PASS
    ↓
user parcel confirmation
    ↓
selected-candidate full analysis         USER LOCAL BEHAVIORAL PASS
    ↓
detailed result presentation             USER LOCAL BEHAVIORAL PASS
```

Frontend는 PNU를 canonical truth로 자체 승격하지 않는다. 실제 polygon은 Backend confirmation response에서만 가져온다. 법규 적용 여부도 Frontend에서 재판정하지 않는다.

---

## 12. Validation Policy

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

GitHub commit 성공만으로 behavioral PASS를 선언하지 않는다. Build PASS와 runtime integration PASS를 구분한다. Mock-only UI 성공을 실제 Backend 연동 PASS로 기록하지 않는다.

---

## 13. Frontend / Backend Repository Separation Rule

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

## 14. Protected Development Rules

```text
candidate marker != parcel truth
selected candidate != verified parcel
frontend selection != canonical identity
verified polygon = Backend confirmation result only
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

## 15. Current Validation Status

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
Candidate selection UI                      USER LOCAL RUNTIME PASS
Parcel confirmation Frontend integration    USER LOCAL BEHAVIORAL PASS
Verified parcel state                       USER LOCAL BEHAVIORAL PASS

Map adapter/provider                        IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
Candidate marker rendering                  IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
Verified polygon rendering                  IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
Full analysis Frontend integration          IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
Detailed result Frontend presentation       IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
```

### 2026-09-17 Detailed Result User Local Behavioral Validation

검증 HEAD:

```text
7947b88e8ac6b52ab2e64a451137e768770ef16a
```

Backend 실제 request log:

```text
POST /v1/parcel-candidates/address HTTP/1.1 200 OK
POST /v1/parcel-candidates/confirm HTTP/1.1 200 OK
POST /v1/site-analysis/selected-candidate HTTP/1.1 200 OK
```

실제 Frontend 표시값:

```text
PNU                 1168010300100120002
공식 대지면적        15,487.3㎡
건폐율               50% / CONFIRMED
용적률               250% / CONFIRMED
법규 전체            314
적용                  57
비적용                214
조건부                41
확인 필요             2
사업 추가입력         16
절차 추가입력         2
외부 확인정보         SITE_HISTORY
```

`UNKNOWN` 2건은 Frontend에서 `FALSE` 또는 오류로 변환되지 않고 `확인 필요` 2건으로 유지됐다. 공간 면적/면적 차이가 응답에서 제공되지 않은 경우에도 Frontend는 임의 계산하지 않고 `정보 없음`으로 표시했다.

따라서 **VERIFIED parcel → Backend re-verification → SITE_ANALYSIS_API_V1 → detailed result UI** 경계는 **USER LOCAL BEHAVIORAL PASS**이다.

---

## 16. Next Development Target

다음 목표는 **검증된 상세 분석 결과를 일반 사용자가 더 쉽게 이해하도록 결과 화면 UX/presentation을 개선하는 것**이다.

현재 상세 데이터 연결 자체는 완료됐으며, 다음 작업은 Backend 판단을 바꾸는 것이 아니라 presentation 계층을 다듬는 것이다.

현재 실제 화면에서 확인된 UX 개선 후보:

```text
긴 추가 입력 목록의 정보 구조 개선
Backend 상태 용어의 사용자 친화적 presentation
결과 영역과 지도 영역의 화면 비율/가독성 개선
UNKNOWN = 확인 필요 의미의 명확한 설명
정보 없음과 분석 실패의 시각적 구분
```

구현 전에 현재 Frontend 결과 컴포넌트 구조와 `SITE_ANALYSIS_API_V1` presentation 의미를 READ-ONLY로 다시 확인한다. Frontend는 법규 적용 여부를 재판정하거나 Backend 결과를 임의 보정하지 않는다.

---

## 17. Other Known Product Gaps

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

## 18. Immediate Next Step Status

```text
CURRENT TASK:
Detailed result UX / presentation READ-ONLY investigation

CURRENT FRONTEND STATUS:
DETAILED SITE ANALYSIS RESULT UI USER LOCAL BEHAVIORAL PASS

NEXT WRITE:
Must inspect actual Frontend result UI + response presentation semantics and define exact minimal UX improvement scope
```

---

## 19. Status Update Rule

이 문서는 실제 이벤트가 발생했을 때만 갱신한다. 목표나 예상만으로 IMPLEMENTED/PASS 상태를 올리지 않는다.
