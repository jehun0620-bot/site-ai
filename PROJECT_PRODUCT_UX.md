# AI 대지분석 자동화 시스템 — PRODUCT / UX DESIGN

최종 업데이트: 2026-09-21
문서 역할: 웹·애플리케이션 제품 UX 아이디어와 구현 backlog 관리
관련 문서: `PROJECT_ARCHITECTURE.md`, `PROJECT_STATUS.md`

## 1. 상태 표기

- `IDEA`: 아이디어
- `PROPOSED`: 제품 방향 제안
- `DESIGNED`: 상세 흐름/계약 설계
- `IMPLEMENTING`: 구현 중
- `VALIDATED`: 실제 구현 + 검증 완료

제품 문서는 architecture authority가 아니다. Canonical PNU/SITE truth safety boundary는 `PROJECT_ARCHITECTURE.md`를 따른다.

## 2. UX 불변 원칙

```text
검색 결과 ≠ canonical parcel truth
candidate PNU ≠ canonical parcel truth
지도 point ≠ parcel inclusion proof
지도 클릭 ≠ canonical parcel truth
사용자 선택 ≠ canonical parcel truth
```

```text
SEARCH / MAP
→ candidate parcel
→ user selection
→ backend same-PNU verification
→ VERIFIED canonical parcel identity
→ existing analysis pipeline
```

## 3. 주소 검색 후보 리스트 backend/public API — VALIDATED

Candidate discovery backend and `POST /v1/parcel-candidates/address` are implemented and user-local real-data validated.

Real query `서울특별시 강남구 개포동 12`, size 10 returned `PARCEL_CANDIDATE_SEARCH_V1`, READY, count 10, including `개포동 12-2 / 개포자이`.

Candidate payload contains candidate PNU, parcel address, road address/building name when available, and EPSG:4326 x/y. Discovery deliberately does not return VERIFIED identity and does not start analysis.

## 4. Selected candidate verification/full analysis/public HTTP — VALIDATED

The selected-candidate backend boundary is now implemented and user-local live validated:

```text
candidate_pnu + x/y
→ live LP_PA_CBND_BUBUN query
→ require selected PNU == polygon feature PNU
→ PNU decomposition/regeneration
→ VERIFIED canonical parcel identity
→ existing analyze_site_by_parcel()
```

Public endpoint:

```text
POST /v1/site-analysis/selected-candidate
```

Real `개포동 12-2 / 개포자이` HTTP E2E returned `SITE_ANALYSIS_API_V1 / READY`, canonical PNU `1168010300100120002`, identity COMPLETE, official land area 15487.3㎡, and Building HUB count 9/status 00.

A stale snapshot for PNU `1168010300100120000` was explicitly not reused as truth; live geometry for selected PNU `1168010300100120002` was re-queried and verified.

## 5. Candidate list UI — NEXT / PROPOSED

Desktop/web concept:

```text
┌──────────────────────────┬──────────────────────────┐
│ 주소 검색                 │ MAP                      │
│                          │                          │
│ ○ 개포동 12              │       ● 12              │
│   대청아파트302동         │                          │
│   개포로109길 21         │ ● 12-1      ● 12-2      │
│                          │                          │
│ ○ 개포동 12-1            │                          │
│                          │                          │
│ ○ 개포동 12-2            │                          │
│   개포자이                │                          │
│                          │                          │
│ [선택한 필지 확인]        │                          │
└──────────────────────────┴──────────────────────────┘
```

PNU may remain hidden from ordinary users while being retained as backend candidate identity.

Before UI implementation, inspect the repository for an existing frontend/web foundation. Reuse existing technology if present. Do not introduce React/Vue/another framework merely for convenience without explicit design/write approval.

## 6. Map candidate display — PROPOSED

Current real candidate x/y coordinates are sufficient to center the map and place candidate markers. They are not parcel truth.

Initial map behavior:
1. show candidate markers
2. list click centers/highlights candidate marker
3. show parcel/road/building labels
4. do not treat marker click as VERIFIED
5. selected candidate analysis request goes through the validated public selected-candidate endpoint

Verified parcel polygon display should use geometry returned by the validated analysis path or a separately designed safe geometry boundary; never infer a parcel polygon from the marker point.

## 7. Exact-address fast path — VALIDATED

Exact-address public analysis remains a separate validated path:

```text
exact parcel address
→ backend VERIFIED identity
→ existing full analysis
```

Candidate selection is an additional UX path, not a replacement.

## 8. Road-name address support — IDEA

Current real-data validation centers on parcel-address search. Road-name address behavior needs separate provider investigation. Any road→parcel conversion must still end in same-PNU verification.

## 9. Analysis confirmation UX — PROPOSED

Before expensive/full analysis, consider a confirmation card showing selected parcel address, road/building label and candidate location. The action `이 필지 분석` sends candidate PNU + x/y to the validated backend endpoint, where live same-PNU verification occurs before analysis.

The UI must not label the candidate as VERIFIED before the backend succeeds.

## 10. Result UX — IDEA

Future result screen should prioritize parcel basics, regulation status TRUE/FALSE/UNKNOWN, numeric limits, conditional/unresolved items, map overlays, legal/official provenance, AI explanation, and data/verification date.

UNKNOWN must be explained rather than hidden.

## 11. Updated backlog

```text
1. exact address → full analysis                       VALIDATED
2. public exact-address HTTP                           VALIDATED
3. candidate discovery backend                         VALIDATED
4. public candidate-search HTTP                        VALIDATED
5. selected candidate same-PNU verification            VALIDATED
6. selected candidate → existing full analysis         VALIDATED
7. public selected-candidate analysis HTTP              VALIDATED
8. repository frontend/web foundation audit             NEXT
9. candidate list UI                                    PROPOSED
10. candidate markers / map                             PROPOSED
11. verified parcel polygon highlight                   PROPOSED
12. list ↔ map synchronization                          PROPOSED
13. analysis confirmation UX                            PROPOSED
14. road-name address strategy                          IDEA
15. mobile refinement                                   IDEA
16. result/provenance visualization                     IDEA
```

## 12. 관리 규칙

- Architecture invariant: `PROJECT_ARCHITECTURE.md`
- Behavioral PASS/current checkpoint: `PROJECT_STATUS.md`
- Product ideas/UI/backlog: this document
- UI convenience never bypasses backend canonical PNU verification.
- Architecture-changing UX requires architecture review first.
- Implementation requires exact WRITE scope and focused validation.


---

## 13. 2026-09-21 Product Direction Reconciliation

2026-09-17 backlog의 candidate list/map, verified parcel confirmation/polygon, list-map synchronization, analysis confirmation, detailed result presentation은 이후 실제 구현 및 사용자 로컬 검증까지 진행되었다. 최신 구현/PASS 상태의 authority는 `PROJECT_FRONTEND_STATUS.md`이며, 위의 과거 `NEXT / PROPOSED` 표기는 당시 시점의 기록으로 본다.

현재 제품 전략은 Single Parcel v1을 명확한 종료선까지 마무리한 뒤 Integrated Development로 넘어가는 것이다.

### Top-level analysis choice — PROPOSED

```text
HOME
"어떤 개발 분석이 필요하신가요?"

[단일 필지 개발]
한 개의 공식 PNU를 기준으로 개발조건과 규제를 분석

[통합 개발]
여러 필지를 하나의 proposed development site로 구성하여
통합 가능성, 개발조건, 혼재 규제와 주변 context를 검토
```

별도의 "블록 분석"을 top-level 상품으로 두는 방향은 현재 보류한다. 블록/주변 공간 검토는 Integrated Development 안의 surrounding context analysis로 포함하는 방향을 우선 검토한다.

### Integrated Development is not just cadastral merge

`통합 개발`을 `합필`과 동의어로 정의하지 않는다.

```text
verified member parcels
→ cadastral merge eligibility
→ building-site composition / development-site composition
→ planning/common-development constraints
→ assembled-site regulation
→ surrounding context
```

지적 합병 가능 여부는 중요한 사전검토 항목이지만, 그 결과 하나만으로 통합개발 전체 가능/불가를 자동 판정하지 않는다. 여러 parcel 선택 자체도 합병 또는 통합개발 가능성을 증명하지 않는다.

### Single Parcel v1 closure — CURRENT

통합개발 구현 전에 현재 Single Parcel을 다음 종료선까지 마무리한다.

```text
1. Public Rule Presentation Model
2. PC rule-detail UX
3. Machine-readable Product Error Model
4. PC product-error UX
5. Final Single Parcel regression
6. Single Parcel v1 baseline freeze
```

Road-name-address 입력, 광범위한 provider operational hardening, SaaS auth/project/history/billing/report 기능은 현재 Single Parcel v1 종료를 막는 필수조건으로 두지 않는다. 모바일 전용 refinement는 테스트 환경 준비 전까지 보류한다.

### Future discovery

Integrated Development 착수 전에는 실제 Backend의 PNU verification → SITE truth → Rule Engine 경계를 기준으로 Analysis Target을 설계한다. 독립적인 복수필지 병렬분석을 core mode로 만들지 않고, 1..N VERIFIED parcels가 하나의 assembled site를 구성하는 모델을 우선 검토한다.

## 14. Canonical Building Use selection UX — PROPOSED (2026-09-29)

건축계획의 용도 입력은 사용자가 임의 문자열을 타이핑하는 방식보다, 현행 「건축법 시행령」 별표 1의 공식 용도 체계에서 선택하는 UX를 우선한다.

기본 흐름:

```text
대분류 선택
→ 선택 가능한 세부 건축물 용도 표시
→ 실제 법정 용도 선택
→ 해당 용도에 추가 법정 요건이 있는 경우 필요한 조건만 후속 입력
→ Canonical Building Use 확정
→ PROJECT mapping
→ existing Rule Engine
```

제품 원칙:
- UI의 용도 선택지는 Annex 1 Semantic Model에서 검증된 canonical use를 기준으로 생성한다.
- 구조상 MAJOR/SUBITEM/DETAIL이라는 이유만으로 UI 선택 가능 여부를 자동 결정하지 않는다. Semantic role이 실제 선택 가능한 USE인지 확인한다.
- CATEGORY는 탐색/그룹화에 사용하고, 그 자체가 법정 USE로 검증되지 않은 경우 최종 용도로 선택시키지 않는다.
- 공장·발전시설처럼 MAJOR 자체가 USE인 경우에는 구조 깊이와 무관하게 실제 선택 가능한 용도로 취급할 수 있다.
- 자유입력 문자열을 canonical legal use로 직접 승격하지 않는다.
- 법령 source path와 사용자 선택용 canonical use를 분리한다. 하나의 공식 source node가 복수의 실제 선택용 용도를 포함할 수 있다.
- 예: 교육연구시설의 동일 source node가 학원과 교습소를 함께 규정하면 UI에서는 각각 독립 선택지로 제공하되 동일 공식 source provenance에 연결할 수 있어야 한다.
- 면적·층수·세대수 등 추가 법정 qualification이 필요한 용도는 용도 선택 이후 필요한 입력만 단계적으로 요청한다.
- 원문, source path, qualification, exclusion 및 법령 provenance는 UI 편의를 위해 소실하거나 합성하지 않는다.
- UNRESOLVED semantic node는 검증 전까지 canonical 선택지로 자동 노출하지 않는다.

목표 UI 예시:

```text
건축물 용도
└─ 교육연구시설
   ├─ 학교
   ├─ 교육원
   ├─ 직업훈련소
   ├─ 학원
   ├─ 교습소
   ├─ 연구소
   └─ 도서관
```

필요한 Semantic Model 방향:

```text
Official Annex 1 Source Node
        ↓ 1:N
Canonical Building Use choices
        ↓
Product selection UI
        ↓
Project facts / qualifications
        ↓
existing PROJECT profile mapping
        ↓
existing Rule Engine
```

현재 상태는 제품/모델 방향 제안(PROPOSED)이며, 전체 Annex 1 canonical coverage, 1:N semantic contract, public API, frontend selection component 및 Rule Engine 연결이 구현·검증되었다는 의미가 아니다.
## Building Use qualification input UX boundary — 2026-09-29

Canonical Building Use 선택 과정에서 법령 내부의 모든 qualification predicate를 그대로 사용자 입력항목으로 노출하지 않는다.

기본 UX 원칙은 다음과 같다.

```text
사용자가 이해할 수 있는 실제 계획정보
(용도 / 종류 / 면적 / 층수 / 객석 / 세대·실 수 등)
        ↓
validated input
        ↓
Building Use Mapping Layer
        ↓
내부 STATE / NUMERIC / classification facts
        ↓
Canonical Building Use 후보 판정
```

명확한 숫자 입력은 필요한 시점에 단계적으로 요청한다. 법률상 제외유형처럼 내부적으로 boolean/state 판정이 필요한 경우에도 가능한 한 사용자가 법률 predicate 이름 자체를 TRUE/FALSE로 입력하게 하지 않는다. 실제 계획 종류를 선택하거나 이해 가능한 질문에 답하게 하고 Mapping Layer가 내부 Fact로 변환하는 방식을 우선한다.

현재 제품 입력만으로 신뢰성 있게 판단할 수 없는 qualification은 사용자의 임의 체크 하나로 자동 확정하지 않는다. 필요한 경우 추가 확인이 필요함을 표시하고 REVIEW_REQUIRED / UNSET 상태를 유지한다.

이 UX 원칙의 목적은 Annex 1의 복잡성을 사용자에게 그대로 전가하지 않으면서도, 자동판정할 수 없는 조건을 숨기거나 임의 추정하지 않는 것이다.


## Progressive Building Use qualification / undecided-value UX — 2026-09-30

Building Use qualification questions should follow the user's actual project decisions and expose only currently necessary information. For the verified 체육관 / 운동장 cross-classification example:

```text
체육관 또는 운동장
→ "관람석이 있습니까?"
   ├─ 아니오 → 관람석 면적을 묻지 않음
   └─ 예
       → "관람석 바닥면적의 합계는 얼마입니까?"
          ├─ 구체값 입력
          └─ 아직 미정
```

The product meaning of "아직 미정" must be different from leaving the question unanswered.

```text
미입력 / UNSET
= 사용자가 아직 답하지 않음
= 필요한 경우 계속 입력 대상으로 표시

아직 미정 / UNKNOWN
= 사용자가 답했지만 현재 설계·사업계획에서 값이 아직 결정되지 않음
= 같은 질문을 단순 미입력으로 반복하지 않음
= 관련 법적 분류/판정은 확정하지 않고 fail-closed 상태로 유지
```

This is a UX/contract direction, not a claim that the current public API or Frontend already supports a numeric "아직 미정" control. Current implementation support is limited to the Backend four-state evaluation semantics and the Building Use classification requirement bridge. Public API and Frontend controls require separate implementation and user-local validation.

The UI should prefer understandable project questions such as 관람석 유무 and 관람석 면적 rather than exposing internal names such as `has_spectator_seating` or asking the user to choose Rule Engine states directly.


## Backend support for progressive qualification answers — 2026-09-30

The Backend contract now distinguishes the user-facing concepts needed for progressive Building Use questions: a dedicated yes/no spectator-seating answer and a numeric answer that can be either a concrete value or explicitly undecided. Internal Rule Engine words such as TRUE/FALSE/UNKNOWN are not intended as user-facing choices.

The public requirement response can now distinguish Building Use classification STATE questions from direct Rule Engine clause requirements. This enables a later Frontend to render understandable prompts such as "관람석이 있습니까?" and, only when needed, "관람석 바닥면적의 합계는 얼마입니까?".

Frontend controls are still not implemented by this checkpoint. The existing UI must not be described as already supporting these answers until the Frontend request/response types, controls, reanalysis transport, and E2E tests are separately updated and validated.

## 15. Verified public Building Use progressive-input UX — 2026-10-01

The earlier canonical Building Use direction now has a deliberately narrow verified product path.

Current user flow:
```text
verified parcel analysis
→ Backend public Building Use catalog
→ user selects planned canonical use
→ selected-candidate reanalysis
→ Backend returns only currently required classification facts
→ user answers those facts
→ reanalysis
```

For the verified 체육관 / 운동장 cross-classification path:
```text
체육관 or 운동장
→ 관람석 유무
→ if 아니오: no spectator-area question
→ if 예: 관람석 바닥면적의 합계
→ numeric value or "아직 미정"
→ Backend reanalysis
```

The Frontend must not encode the legal rule that a particular use requires a particular follow-up question. It displays the public catalog and the requirements returned by Backend. The current public catalog contains 15 verified input-discovery names and must not be presented as complete Annex 1 coverage.

`아직 미정` is an explicit user answer, not an omitted answer. For supported numeric facts it maps to Backend UNKNOWN and must not be repeatedly presented as an unanswered requirement.

This flow is **IMPLEMENTED + USER-LOCAL BEHAVIORAL PASS** as of 2026-10-01. The verified E2E includes the 체육관 → 관람석 → 면적 → 아직 미정 sequence. 집회장 and full Rule 125 production behavior are outside this UX checkpoint.
