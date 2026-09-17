# AI 대지분석 자동화 시스템 — PRODUCT / UX DESIGN

최종 업데이트: 2026-09-17
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
