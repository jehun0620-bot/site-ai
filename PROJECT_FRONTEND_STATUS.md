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
CANDIDATE LIST / MAP SYNC              IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
CANDIDATE REFERENCE GEOMETRY           IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
CANDIDATE PARCEL BOUNDARY RENDERING    IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
PARCEL CONFIRMATION FRONTEND           IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
VERIFIED PARCEL STATE                  IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
MAP / VERIFIED POLYGON RENDERING       IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
DETAILED SITE ANALYSIS RESULT UI       IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
RESULT UX / PRESENTATION               IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
RESULT-CENTERED LAYOUT                 IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
VERIFIED MAP RESIZE / REFIT            IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
ADDITIONAL INPUT UX / REANALYSIS        IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
PLAYWRIGHT MULTI-PARCEL E2E             IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
ERROR / EMPTY SEMANTICS                  IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
RESPONSIVE RESULT NAVIGATION              IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
```

---

## 3. Confirmed Product Flow

```text
주소 입력
    ↓
parcel candidate 검색
    ↓
candidate list / map marker / discovery reference boundary
    ↓
candidate 선택 (list / marker / boundary)
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
→ candidate card + marker + reference boundary 렌더링
→ list / marker / boundary candidate 선택 동기화
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

Candidate는 discovery 결과이며 verified canonical parcel identity가 아니다. Candidate의 optional `reference_geometry`도 검색/탐색 UX를 위한 discovery-only geometry이며 VERIFIED parcel truth가 아니다.

`POST /v1/parcel-candidates/confirm` 성공 contract:

```text
schema_version = PARCEL_CONFIRMATION_V1
status = READY
parcel = verified parcel identity + selected point + CRS
verification.status = VERIFIED
verification.resolution = SELECTED_PARCEL_CANDIDATE_VERIFIED
geometry = verification에 실제 사용된 Polygon 또는 MultiPolygon
```

Frontend는 Backend confirmation response의 verified geometry만 VERIFIED parcel polygon으로 취급한다. Pre-analysis confirmation은 full selected-candidate analysis의 재검증을 대체하지 않는다.

---

## 5. Backend Behavioral Baseline Relevant to Frontend

Backend focused contract validation:

```text
PUBLIC_API_ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS
ADDRESS_PARCEL_CANDIDATE_GEOMETRY_CONTRACT_PASS
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_CONFIRMATION_CONTRACT_PASS
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_CONTRACT_PASS
```

Candidate reference geometry live validation:

```text
query            서울특별시 강남구 개포동 12
candidate_count  10
geometry_count   10
geometry_type    MultiPolygon (10/10)
elapsed_sec      0.901
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
test-results/   ignored
playwright-report/ ignored
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
| Candidate list/map sync | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | candidate card와 map marker 선택이 동일 selection 경로로 동기화됨 |
| Candidate reference geometry | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | Backend discovery-only reference geometry 10/10 MultiPolygon 실데이터 확인 |
| Candidate parcel boundary rendering | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 검색 후보 경계를 지도에 표시하고 boundary click으로 동일 candidate 선택 확인 |
| Candidate boundary presentation | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 붉은 계열 경계 + 옅은 파스텔 red/pink 반투명 fill 실제 화면 확인 |
| Parcel confirmation API client | IMPLEMENTED + USER LOCAL PASS | `/v1/parcel-candidates/confirm` 실제 `200 OK` |
| Parcel confirmation response typing | IMPLEMENTED | `PARCEL_CONFIRMATION_V1`, VERIFIED, Polygon/MultiPolygon contract |
| Verified parcel state | IMPLEMENTED + USER LOCAL PASS | PNU/geometry type/CRS 표시 확인 |
| Previous parcel state invalidation | IMPLEMENTED | 새 검색 시작 시 이전 selection/confirmation 제거 |
| Map provider | IMPLEMENTED + USER LOCAL PASS | Kakao Maps SDK 실제 브라우저 로딩 확인; provider-neutral adapter 유지 |
| Map UI | IMPLEMENTED + USER LOCAL PASS | Kakao Maps 실제 지도 렌더링 확인 |
| Verified polygon rendering | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | Backend VERIFIED MultiPolygon 실제 지도 렌더링 확인 |
| Full analysis UI | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | selected-candidate 분석 요청 및 SITE_ANALYSIS_API_V1 표시 확인 |
| Detailed result UI | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 대지면적/건폐율/용적률/법규 집계/추가 입력/외부 확인정보 표시 확인 |
| Result UX / presentation | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 사용자 친화적 상태, UNKNOWN 설명, requirements 요약, 정보 없음 설명 확인 |
| Result-centered layout | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 분석 후 좌측 compact parcel flow + 우상단 지도 + 하단 전체폭 SITE 결과 확인 |
| Verified map resize/refit | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 작은 지도에서도 VERIFIED parcel polygon 전체가 다시 viewport에 맞춰지는 것 확인 |
| Additional input UX / reanalysis | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 사업/절차 requirement에 TRUE/FALSE/UNKNOWN 입력 후 selected-candidate 재분석 확인; 미응답 key는 profile에서 생략 |
| Playwright multi-parcel E2E | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 실제 Browser → Frontend → Backend 경로에서 일반지번 + 산지번 + 건축물 없는 필지, VERIFIED, 분석, 추가입력 재분석, PNU 보존, 필지 전환 상태 격리 검증 |
| Error/empty/UNKNOWN UI | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | 빈 입력/검색 결과 없음/실패 상태를 구분하고 Backend `detail`을 보존; UNKNOWN은 오류/FALSE로 변환하지 않음 |
| Responsive result navigation | IMPLEMENTED + USER LOCAL BEHAVIORAL PASS | PC에서는 결과 바로가기를 숨기고, 920px 이하 1열 결과 화면에서 6개 섹션 바로가기를 제공 |

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
✓ built in 90ms
```

후보 reference geometry / map boundary 구현에서도 production build가 사용자 로컬에서 PASS했다. 최종 behavioral PASS는 실제 브라우저 화면 검증을 기준으로 기록한다.

---

## 9. Candidate Search / Parcel Confirmation Runtime Validation

실제 검색:

```text
서울특별시 강남구 개포동 12
```

검색 단계에서 10개 candidate 모두 discovery-only `reference_geometry`가 MultiPolygon으로 확인됐고, 지도에서 marker와 candidate parcel boundary가 함께 표시되는 것을 사용자 로컬 화면으로 확인했다.

선택/확인 예시:

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

Candidate reference geometry는 discovery UX 전용이다. Parcel truth authority는 계속 Backend verification boundary에 있다.

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

## 12. Candidate Reference Boundary + Map Selection Validation

### 2026-09-17 User Local Behavioral Validation

최종 presentation 구현 HEAD:

```text
06bbdd9f277bfffac5e7d17ab9c630986380b11c
```

검증된 흐름:

```text
candidate search
→ Backend discovery-only reference geometry
→ candidate card + marker + parcel boundary rendering
→ card / marker / boundary selection sync
→ selected candidate visual focus
→ Backend /confirm
→ VERIFIED parcel geometry
```

실제 `서울특별시 강남구 개포동 12` 검색에서 candidate 10개와 reference geometry 10개가 확인됐으며 geometry type은 모두 MultiPolygon이었다. Backend live enrichment 실측은 0.901초였다.

Frontend 실제 화면에서는 candidate parcel boundary가 Kakao 지도 위에 표시됐고, 최종 presentation은 붉은 계열 경계와 옅은 파스텔 red/pink 반투명 내부 채움으로 사용자 확인을 완료했다.

Candidate boundary는 parcel truth가 아니다. `reference_geometry`는 검색/탐색 편의를 위한 discovery-only geometry이며, 선택 후 Backend `/v1/parcel-candidates/confirm` 검증을 통과한 geometry만 VERIFIED parcel로 취급한다.

따라서 다음은 **USER LOCAL BEHAVIORAL PASS**이다.

```text
CANDIDATE LIST / MAP MARKER SYNC
CANDIDATE REFERENCE GEOMETRY
CANDIDATE PARCEL BOUNDARY RENDERING
CANDIDATE BOUNDARY CLICK SELECTION
CANDIDATE BOUNDARY PRESENTATION
```

---

## 13. A안 Backend / Frontend Boundary

현재 실제 연결 상태:

```text
candidate search                         PASS
    ↓
candidate reference geometry             USER LOCAL BEHAVIORAL PASS
    ↓
candidate card / marker / boundary       USER LOCAL BEHAVIORAL PASS
    ↓
candidate selection sync                 USER LOCAL BEHAVIORAL PASS
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

Frontend는 PNU를 canonical truth로 자체 승격하지 않는다. Candidate `reference_geometry`도 canonical truth로 승격하지 않는다. VERIFIED polygon은 Backend confirmation response에서만 가져온다. 법규 적용 여부도 Frontend에서 재판정하지 않는다.

---

## 14. Validation Policy

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

## 15. Protected Development Rules

```text
candidate marker != parcel truth
candidate reference geometry != parcel truth
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

## 16. Current Validation Status

```text
Backend candidate search                    IMPLEMENTED
Backend candidate reference geometry        IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
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
Candidate list/map sync                     IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
Candidate reference boundary rendering      IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
Candidate boundary click selection          IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
Candidate boundary presentation             IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
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

Error/empty product semantics               IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
Responsive SITE result navigation           IMPLEMENTED + USER LOCAL BEHAVIORAL PASS
```

---

## 17. Next Development Target

분석 전 candidate 탐색 UX의 list/marker/boundary sync와 분석 후 result-centered layout 및 verified map resize/refit은 구현 및 사용자 로컬 behavioral validation까지 완료됐다.

다음 Frontend 작업은 기존 화면을 기준으로 **남은 UX 개선 항목을 READ-ONLY로 점검하고 우선순위를 정하는 것**이다.

우선 조사 후보:

```text
긴 SITE 결과의 섹션 탐색 구조 — responsive navigation USER LOCAL BEHAVIORAL PASS 완료
Playwright E2E의 검증된 필지 seed 확대
전체 product error / empty semantics — 1차 USER LOCAL BEHAVIORAL PASS 완료
모바일 결과/지도 순서와 반응형 가독성
candidate/verified 상태 설명의 사용자 친화적 표현
```

아직 구현 방식이나 우선순위는 확정하지 않는다. 실제 repository 파일과 현재 화면을 기준으로 READ-ONLY 확인 후 최소 변경 범위를 정한다.

Frontend는 계속 Backend 결과를 재판정하거나 임의 보정하지 않는다.

---

## 18. Additional Input + Playwright Multi-Parcel E2E Validation

### 2026-09-18 User Local Behavioral Validation

추가 입력 UX는 Backend Rule Engine의 기존 profile contract를 그대로 사용한다.

```text
해당함         → TRUE
해당하지 않음 → FALSE
잘 모르겠음   → UNKNOWN
미응답         → profile key 생략
```

Frontend는 UNSET을 사용자 선택값으로 전송하지 않으며, Backend가 반환한 requirements를 사용해 입력 UI를 구성한다. 입력 후 `POST /v1/site-analysis/selected-candidate`를 다시 호출하고, 재분석 결과의 PNU가 확인된 parcel PNU와 같은지 검증한다.

Playwright 실제 브라우저 E2E도 사용자 로컬에서 PASS했다. 최종 검증 HEAD:

```text
b38ffa77baebe639429e13dbb92d86179a0ce47f
```

검증된 기본 address seed:

```text
서울특별시 강남구 개포동 12
서울특별시 동작구 동작동 산 29-3
```

산지번은 현재 Desktop B에서 별도로 재검증했다.

```text
address       서울특별시 동작구 동작동 산 29-3
candidate     1개
verification  VERIFIED
PNU           1159010600200290003
geometry      MultiPolygon
CRS           EPSG:4326
SITE analysis 분석 완료
```

건축물 없는 필지 fixture도 실제 Backend 응답으로 확인했다.

```text
address               서울특별시 강남구 개포동 12-6
PNU                   1168010300100120006
SITE status           READY
identity_status       COMPLETE
geometry              MultiPolygon
building_count        0
building_total_count  0
building_api_status   00
```

`building_count = 0`은 건물명 공란 등의 추정이 아니라 실제 `SITE_ANALYSIS_API_V1` 응답의 `service.building_count`에서 확인했다. 이 PNU는 E2E에서 명시적으로 선택하여 VERIFIED → SITE 분석 → 추가 입력 재분석 → 분석 PNU 유지까지 검증한다.

최종 multi-parcel Playwright 실행:

```text
Running 1 test using 1 worker
1 passed (12.1s)
```

따라서 현재 E2E behavioral baseline은 일반지번 후보군 + 산지번 + 건축물 없는 필지의 세 유형을 포함한다.

E2E는 실제 Backend를 사용하며 각 주소에서 최대 2개 candidate를 선택한다. 추가 입력은 고정 seed 기반 pseudo-random 방식으로 TRUE/FALSE/UNKNOWN을 선택해 실패를 재현 가능하게 유지한다. 환경변수 `SITE_AI_E2E_ADDRESSES`로 검증된 주소 seed를 추가할 수 있다.

검증 범위:

```text
actual browser
→ address candidate search
→ candidate selection
→ Backend parcel confirmation / VERIFIED
→ selected-candidate SITE analysis
→ additional input selection
→ reanalysis
→ analysis PNU == verified parcel PNU
→ parcel switch
→ previous additional-input state isolation
```

Candidate와 reference geometry는 계속 discovery-only이며, Playwright도 Frontend에서 parcel truth를 생성하거나 법규 적용 여부를 재판정하지 않는다.

---

## 19. Error / Empty Semantics Validation

### 2026-09-18 User Local Behavioral Validation

Frontend API client가 Backend의 기존 FastAPI `detail`을 HTTP status 숫자로 축약하지 않고 보존하도록 개선했다. 별도의 machine-readable product error schema를 새로 추정하거나 Frontend에서 오류 의미를 재판정하지 않는다.

최종 구현 및 사용자 로컬 검증 HEAD:

```text
986d5b45a9848d9f580f02c9e20e675b903d5dbb
```

검증 결과:

```text
production build                         PASS
Playwright real Backend E2E              1 passed (11.9s)
empty address input                      USER LOCAL PASS
zero-candidate / empty-result UX         USER LOCAL PASS
normal / empty / error state separation  USER LOCAL PASS
Backend detail preservation              IMPLEMENTED
UNKNOWN != FALSE                         PRESERVED
```

빈 검색어는 서버 장애와 같은 `SEARCH_ERROR`로 표시하지 않고 입력/empty 계열 상태로 구분한다. 정상 검색 결과가 0개인 경우도 서버 실패와 구분해 사용자에게 검색은 완료됐지만 후보가 없음을 안내한다.

후보 검색, 필지 확인, SITE 분석의 HTTP 실패에서는 Backend가 실제로 제공한 문자열 `detail`이 있으면 이를 보존한다. 현재 Backend에는 machine-readable product error schema가 없으므로 Frontend는 HTTP 404/500/502만 보고 법적·데이터 의미, 재시도 가능 여부 등을 임의 추론하지 않는다.

기존 정상 분석 경로는 같은 HEAD에서 production build 및 실제 Browser → Frontend → Backend Playwright E2E로 회귀 검증했다.

---

## 20. Responsive SITE Result Navigation Validation

### 2026-09-18 User Local Behavioral Validation

긴 SITE 결과의 탐색성을 개선하되 기존 결과 카드 구조와 Backend trust boundary는 변경하지 않았다. 결과 섹션에는 고정 anchor를 두고, 좁은 화면에서만 6개 바로가기를 표시한다.

최종 구현 및 사용자 로컬 검증 HEAD:

```text
a7b87b1ea387450115eee9c2c80d84672b9e5266
```

검증된 navigation:

```text
기본정보
대지면적
건축규모
법규평가
추가입력
외부확인
```

반응형 기준:

```text
width > 920px   → 결과 바로가기 숨김
width <= 920px  → 결과 바로가기 표시 + 세로 1열 결과 탐색
```

PC 결과 화면에서는 주요 결과 카드가 한 화면에 함께 보이므로 별도 navigation의 실익이 작다는 사용자 실제 화면 검증을 반영했다. 모바일/좁은 화면에서는 결과가 1열로 길어지므로 동일 anchor navigation을 유지한다.

6개 바로가기의 실제 섹션 이동과 PC/좁은 화면 표시 전환을 사용자 로컬 브라우저에서 확인했다. Backend, API contract, Rule Engine, 분석 결과 값, 추가 입력/reanalysis 의미는 변경하지 않았다.

---

## 21. Other Known Product Gaps

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

## 22. Immediate Next Step Status

```text
CURRENT TASK:
Frontend UX improvement READ-ONLY investigation

CURRENT FRONTEND STATUS:
CANDIDATE LIST / MAP SYNC              USER LOCAL BEHAVIORAL PASS
CANDIDATE REFERENCE GEOMETRY           USER LOCAL BEHAVIORAL PASS
CANDIDATE PARCEL BOUNDARY RENDERING    USER LOCAL BEHAVIORAL PASS
RESULT-CENTERED LAYOUT                 USER LOCAL BEHAVIORAL PASS
VERIFIED PARCEL MAP RESIZE / REFIT     USER LOCAL BEHAVIORAL PASS
ADDITIONAL INPUT UX / REANALYSIS       USER LOCAL BEHAVIORAL PASS
PLAYWRIGHT MULTI-PARCEL E2E            USER LOCAL BEHAVIORAL PASS
ERROR / EMPTY SEMANTICS                 USER LOCAL BEHAVIORAL PASS
RESPONSIVE RESULT NAVIGATION             USER LOCAL BEHAVIORAL PASS

NEXT WRITE:
None until actual UX gaps are inspected and exact minimal scope is approved
```

---

## 23. Status Update Rule

이 문서는 실제 이벤트가 발생했을 때만 갱신한다. 목표나 예상만으로 IMPLEMENTED/PASS 상태를 올리지 않는다.
