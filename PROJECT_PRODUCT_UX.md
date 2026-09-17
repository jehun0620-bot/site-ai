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

## 3. 주소 검색 후보 리스트 — BACKEND VALIDATED / PUBLIC API NEXT

Candidate discovery backend is implemented and user-local real-data validated at code HEAD `644420035690d8e3281fad4c564789d01d6469b0`.

Real query:
```text
서울특별시 강남구 개포동 12
```

returned multiple real candidates such as:
```text
개포동 12    / 대청아파트302동
개포동 12-1
개포동 12-10
개포동 12-2  / 개포자이
개포동 12-4  / 석탑프라자
```

Candidate backend payload:
- candidate PNU
- parcel address
- road address when available
- building name when available
- EPSG:4326 x/y

The backend candidate-search function deliberately does not return VERIFIED identity and does not start analysis.

Next product/API task: expose this validated discovery function through a thin public HTTP endpoint.

## 4. Candidate list UI — PROPOSED

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

## 5. Map candidate display — PROPOSED

Current real candidate x/y coordinates are sufficient to center the map and place candidate markers. They are not sufficient to prove parcel geometry.

Initial map behavior:
1. show candidate markers
2. list click centers/highlights candidate marker
3. show parcel/road/building labels
4. do not start analysis on marker click

Parcel polygon highlight comes only after selected candidate is backend re-verified against live parcel geometry.

## 6. Selection → backend verification — DESIGNED NEXT BOUNDARY

Recommended contract:

```text
selected candidate
├─ candidate_pnu
├─ parcel_address
├─ x / y
└─ crs
       ↓
backend live LP_PA_CBND_BUBUN lookup
       ↓
selected candidate PNU == polygon PNU
       ↓
PNU decomposition / regeneration
       ↓
VERIFIED canonical parcel identity
       ↓
confirmation UI / analysis
```

Never trust a PNU sent back by a browser merely because it originated from an earlier search response. Backend must re-verify it.

## 7. Exact-address fast path — VALIDATED

Exact-address public analysis is already validated for ordinary and mountain parcels:

```text
exact address
→ backend VERIFIED identity
→ existing full analysis
```

Candidate selection is an additional UX path, not a replacement for the exact-address path.

## 8. Road-name address support — IDEA

Current real-data validation centers on parcel-address search. Road-name address behavior needs separate provider investigation. Any road→parcel conversion must still end in same-PNU verification.

## 9. Analysis confirmation UX — IDEA

Before expensive/full analysis, consider a confirmation card showing selected parcel address, road/building label, ordinary/mountain type, verified parcel polygon and basic official land information. Action: `이 필지 분석`.

## 10. Result UX — IDEA

Future result screen should prioritize parcel basics, regulation status TRUE/FALSE/UNKNOWN, numeric limits, conditional/unresolved items, map overlays, legal/official provenance, AI explanation, and data/verification date.

UNKNOWN must be explained rather than hidden.

## 11. Updated backlog

```text
1. exact address → full analysis                     VALIDATED
2. public exact-address HTTP                         VALIDATED
3. candidate discovery backend                       VALIDATED
4. public candidate-search HTTP                      NEXT
5. candidate list UI                                 PROPOSED
6. candidate markers / map                           PROPOSED
7. selected candidate → backend PNU/polygon verify   DESIGNED NEXT BOUNDARY
8. verified parcel polygon highlight                 PROPOSED
9. list ↔ map synchronization                        PROPOSED
10. road-name address strategy                       IDEA
11. mobile refinement                                IDEA
12. result/provenance visualization                  IDEA
```

## 12. 관리 규칙

- Architecture invariant: `PROJECT_ARCHITECTURE.md`
- Behavioral PASS/current checkpoint: `PROJECT_STATUS.md`
- Product ideas/UI/backlog: this document
- UI convenience never bypasses backend canonical PNU verification.
- Architecture-changing UX requires architecture review first.
- Implementation requires exact WRITE scope and focused validation.
