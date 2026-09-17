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
A안 — 지도 중심 탐색 + 분석 후 결과 중심 전환
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
RESULT UX / PRESENTATION               IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
RESULT-CENTERED LAYOUT                 IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
VERIFIED MAP RESIZE / REFIT            IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
```

---

## 3. Confirmed Product Flow

```text
주소 입력
    ↓
parcel candidate 검색
    ↓
candidate list / map marker
    ↓
candidate 선택
    ↓
Backend parcel confirmation
    ↓
verified parcel polygon
    ↓
사용자 필지 확인
    ↓
selected-candidate full analysis
    ↓
분석 후 결과 중심 layout 전환
    ↓
detailed result presentation + verified parcel map
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
→ result-centered layout
→ verified parcel map resize/refit
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
| Frontend architecture baseline | DOCUMENTED | 지도 중심 탐색과 trust boundary 문서화 |
| Frontend framework | IMPLEMENTED | React + TypeScript + Vite |
| Frontend production build | USER LOCAL PASS | `tsc -b && vite build` 성공 |
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
| Candidate list/map sync | NOT IMPLEMENTED | Architecture contract만 확정; 완료로 승격하지 않음 |
| Verified polygon rendering | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | Backend VERIFIED MultiPolygon 실제 지도 렌더링 확인 |
| Full analysis UI | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | selected-candidate 분석 요청 및 SITE_ANALYSIS_API_V1 표시 확인 |
| Detailed result UI | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 대지면적/건폐율/용적률/법규 집계/추가 입력/외부 확인정보 표시 확인 |
| Result UX / presentation | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 사용자 친화적 상태, UNKNOWN 설명, requirements 요약, 정보 없음 설명 확인 |
| Result-centered layout | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 분석 후 좌측 compact parcel flow + 우상단 지도 + 하단 전체폭 SITE 결과 확인 |
| Verified map resize/refit | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 작은 지도에서도 VERIFIED parcel polygon 전체가 다시 viewport에 맞춰지는 것 확인 |
| Error/empty/UNKNOWN UI | PARTIAL | UNKNOWN 의미 보존은 PASS; 전체 product error/empty semantics는 추가 개선 필요 |

---

## 8. Frontend Build Validation

사용자 로컬 runtime:

```text
Node.js v24.21.0
npm 11.19.0
Vite v8.3.0
```

확인된 production build 예시:

```text
> site-ai-frontend@0.1.0 build
> tsc -b && vite build

vite v8.3.0 building client environment for production...
✓ 20 modules transformed.
✓ built in 87ms
```

레이아웃 작업 과정에서도 production build가 사용자 로컬에서 PASS했다. 최종 map resize/refit의 behavioral PASS는 실제 브라우저 화면 검증을 기준으로 기록한다.

---

## 9. Candidate Search / Parcel Confirmation Runtime Validation

실제 검색:

```text
서울특별시 강남구 개포동 12-2
```

확인된 parcel:

```text
필지 확인 완료
VERIFIED
지번주소  서울특별시 강남구 개포동 12-2
PNU       1168010300100120002
경계 형식  MultiPolygon
좌표계     EPSG:4326
```

Backend 실제 request 경계:

```text
POST /v1/parcel-candidates/address HTTP/1.1 200 OK
POST /v1/parcel-candidates/confirm HTTP/1.1 200 OK
POST /v1/site-analysis/selected-candidate HTTP/1.1 200 OK
```

Parcel truth authority는 계속 Backend verification boundary에 있다.

---

## 10. Detailed Result Behavioral Baseline

실제 Frontend 표시값:

```text
PNU                 1168010300100120002
공식 대지면적        15,487.3㎡
건폐율               50%
용적률               250%
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

Presentation 개선도 실제 화면에서 확인됐다.

```text
READY        → 분석 완료
CONFIRMED    → 확인된 기준
SITE_HISTORY → 과거 이력 확인 + 원본 분류 보존
UNKNOWN 2    → 확인 필요 2 + 오류/비적용이 아니라는 설명
사업/절차 requirements → 16개/2개 요약 + 목록 보기
공간 면적 미제공 → 정보 없음 + Backend 응답에 값이 없어 계산하지 않음
```

따라서 **VERIFIED parcel → Backend re-verification → SITE_ANALYSIS_API_V1 → detailed result UI → presentation** 경계는 USER LOCAL BEHAVIORAL PASS이다.

---

## 11. Result-Centered Layout + Verified Map Resize/Refit Validation

### 2026-09-17 User Local Behavioral Validation

최종 구현 HEAD:

```text
913cc5cafe85f7036323e2a85569b23c850ae30e
```

관련 최종 commit:

```text
fix: refit verified parcel after map resize
```

사용자 로컬 화면에서 다음 레이아웃이 실제 확인됐다.

```text
상단 좌측
  주소 검색
  → 필지 후보
  → 필지 확인 완료

상단 우측
  Kakao 지도 카드
  → VERIFIED PARCEL badge
  → Backend VERIFIED parcel polygon

하단 전체 폭
  SITE 분석 결과
  → 필지 기본정보
  → 대지면적
  → 건축 규모 기준
  → 법규 평가 집계
  → 추가 입력 필요사항
  → 외부 확인 정보
```

초기 결과 중심 레이아웃에서 지도 컨테이너가 큰 화면 기준 viewport를 유지해 작은 카드 안에서 대상 필지가 잘리는 현상이 확인됐다. 최종 수정에서는 지도 컨테이너 resize 이후 Kakao map을 relayout하고, 기존 Backend confirmation의 VERIFIED geometry bounds를 다시 적용하도록 했다.

```text
지도 container resize
→ Kakao map.relayout()
→ Backend VERIFIED geometry 재사용
→ verified geometry bounds 재계산
→ map.setBounds()
→ 현재 지도 카드 크기에 맞춰 대상 필지 전체 표시
```

사용자 최종 화면에서 검증된 MultiPolygon 대상 필지가 우상단 작은 지도 안에 전체적으로 표시되고 주변 지도 맥락도 유지되는 것이 확인됐다.

이 동작은 Frontend가 parcel geometry를 새로 추정하거나 수정하는 것이 아니다. Backend confirmation response의 VERIFIED geometry를 viewport 계산에 다시 사용하는 presentation 동작이다.

따라서 다음은 **USER LOCAL BEHAVIORAL PASS**이다.

```text
RESULT-CENTERED LAYOUT
VERIFIED PARCEL MAP CARD
MAP RESIZE / RELAYOUT
VERIFIED GEOMETRY REFIT
```

---

## 12. A안 Backend / Frontend Boundary

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
selected-candidate full analysis         USER LOCAL BEHAVIORAL PASS
    ↓
detailed result presentation             USER LOCAL BEHAVIORAL PASS
    ↓
result UX / presentation refinement      USER LOCAL BEHAVIORAL PASS
    ↓
result-centered layout transition        USER LOCAL BEHAVIORAL PASS
    ↓
verified map resize/refit                 USER LOCAL BEHAVIORAL PASS
```

Frontend는 PNU를 canonical truth로 자체 승격하지 않는다. 실제 polygon은 Backend confirmation response에서만 가져온다. 법규 적용 여부도 Frontend에서 재판정하지 않는다.

---

## 13. Validation Policy

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
Result UX / presentation refinement         IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
Result-centered layout transition           IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
Verified parcel map resize/refit             IMPLEMENTED + USER LOCAL BEHAVIORAL PASS

Candidate list/map sync                     NOT IMPLEMENTED
Error/empty product semantics               PARTIAL
```

---

## 16. Next Development Target

분석 전/후 레이아웃 전환과 verified map resize/refit은 구현 및 사용자 로컬 behavioral validation까지 완료됐다.

다음 Frontend 작업은 기존 화면을 기준으로 **추가 UX 개선 항목을 READ-ONLY로 점검하고 우선순위를 정하는 것**이다.

우선 조사 후보:

```text
candidate list <-> map sync
선택 candidate의 지도상 시각적 구분 / focus
긴 SITE 결과의 섹션 탐색 구조
추가 입력 필요사항의 실제 입력 UX
전체 product error / empty semantics
모바일 결과/지도 순서와 반응형 가독성
```

아직 구현 방식이나 우선순위는 확정하지 않는다. 실제 repository 파일과 현재 화면을 기준으로 READ-ONLY 확인 후 최소 변경 범위를 정한다.

Frontend는 계속 Backend 결과를 재판정하거나 임의 보정하지 않는다.

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
Frontend UX improvement READ-ONLY investigation

CURRENT FRONTEND STATUS:
RESULT-CENTERED LAYOUT                 USER LOCAL BEHAVIORAL PASS
VERIFIED PARCEL MAP RESIZE / REFIT     USER LOCAL BEHAVIORAL PASS

NEXT WRITE:
None until actual UX gaps are inspected and exact minimal scope is approved
```

---

## 19. Status Update Rule

이 문서는 실제 이벤트가 발생했을 때만 갱신한다. 목표나 예상만으로 IMPLEMENTED/PASS 상태를 올리지 않는다.
