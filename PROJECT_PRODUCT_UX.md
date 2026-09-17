# AI 대지분석 자동화 시스템 — PRODUCT / UX DESIGN

최종 업데이트: 2026-09-17
문서 역할: 웹·애플리케이션 제품 UX 아이디어와 구현 backlog 관리
관련 문서: `PROJECT_ARCHITECTURE.md`, `PROJECT_STATUS.md`

## 1. 문서 목적

이 문서는 시스템 architecture truth와 분리하여 사용자 경험, 화면 흐름, 지도 상호작용, 후보 선택 방식 등 제품 아이디어를 관리한다.

상태 표기:
- `IDEA`: 아이디어 단계
- `PROPOSED`: 제품 방향으로 제안됨
- `DESIGNED`: 상세 흐름/계약 설계 완료
- `IMPLEMENTING`: 구현 중
- `VALIDATED`: 실제 구현 + 검증 완료

문서에 기록되었다는 이유만으로 구현 완료 또는 architecture authority를 의미하지 않는다.

## 2. UX 불변 원칙

```text
사용자 검색 결과 ≠ canonical parcel truth
사용자 지도 클릭 ≠ canonical parcel truth
사용자 후보 선택 ≠ canonical parcel truth
```

사용자 인터페이스는 필지를 찾고 선택하는 것을 돕는다. 최종 분석 진입 전 backend는 선택된 candidate의 PNU/geometry를 다시 검증해야 한다.

```text
SEARCH / MAP INTERACTION
→ candidate parcel
→ user selection
→ backend same-PNU verification
→ VERIFIED canonical parcel identity
→ existing analysis pipeline
```

UX 편의를 위해 fail-closed architecture를 우회하지 않는다.

## 3. 주소 검색 후보 리스트 — PROPOSED

목표: 사용자가 법정동 코드, 본번/부번, 대장구분을 직접 알지 않아도 주소로 필지를 찾는다.

예시:

```text
검색: 서울 강남구 개포동 12

후보
- 서울특별시 강남구 개포동 12
- 서울특별시 강남구 개포동 12-1
- 서울특별시 강남구 개포동 12-10
...
```

후보 데이터에는 제품 구현 시 가능한 범위에서 다음을 표시한다:
- 지번주소
- 도로명주소(공식/검증 가능한 경우)
- 건물명(있는 경우)
- 일반/산 구분
- 지도 위치
- 내부 candidate identity/PNU

PNU는 일반 사용자에게 반드시 노출할 필요는 없지만 backend identity key로 유지한다.

현재 backend exact-match resolver가 `12`와 `12-1`/`12-10`을 구분하는 검증 기반을 제공한다. 후보검색 API 자체는 아직 구현되지 않았다.

## 4. 주소 후보 + 지도 동시 표시 — PROPOSED

권장 desktop/web layout:

```text
┌──────────────────────┬──────────────────────────────┐
│ 주소 검색 / 후보 목록 │             MAP              │
│                      │                              │
│ ○ 개포동 12          │       [선택 필지 polygon]     │
│ ○ 개포동 12-1        │                              │
│ ○ 개포동 12-10       │       인접 필지 polygon       │
│                      │                              │
│ [선택 필지 분석]      │                              │
└──────────────────────┴──────────────────────────────┘
```

Mobile에서는 지도/목록을 상하 배치하거나 bottom sheet 후보 목록을 고려한다.

## 5. 목록 ↔ 지도 양방향 선택 — PROPOSED

목록에서 후보를 선택하면:
1. 지도를 해당 좌표로 이동
2. 해당 parcel polygon 강조
3. 주소/지번/일반·산 정보를 표시
4. 분석 버튼의 현재 선택 candidate를 갱신

지도에서 parcel을 선택하면 향후:
1. 클릭 위치의 parcel polygon/PNU 조회
2. backend candidate identity 조회
3. 후보 목록의 해당 항목과 동기화
4. 사용자가 확인 후 분석 요청

지도 클릭만으로 분석을 즉시 시작하지 않는다.

## 6. 필지 경계 시각화 — PROPOSED

VWorld `LP_PA_CBND_BUBUN` 등 검증된 parcel geometry를 이용할 수 있는 경우 실제 필지 경계를 지도에 표시한다.

제품적으로 유용한 상황:
- 아파트/대단지
- 하나의 도로명주소 주변에 여러 필지가 있는 경우
- 산지
- 대형 개발부지
- 지번이 유사한 인접 필지

Geometry source와 canonical PNU가 불일치하면 선택 가능 상태로 승격하지 않는다.

## 7. 자동 exact-match와 사용자 선택의 관계 — PROPOSED

명확한 지번주소가 입력되고 하나의 exact parcel이 backend 검증을 통과하면 빠른 분석 경로를 제공할 수 있다.

여러 후보가 있거나 사용자가 확인을 원하는 경우 candidate-list/map UX로 전환한다.

장기적으로 제품 정책은 다음 두 모드를 함께 지원할 수 있다:

```text
A. EXACT VERIFIED
주소 → exact verified parcel → 확인 화면 → 분석

B. CANDIDATE SELECTION
주소 → 후보 목록 + 지도 → 사용자 선택 → backend 재검증 → 분석
```

사용자 선택 모드는 backend verification을 대체하지 않는다.

## 8. 도로명주소 지원 — IDEA

현재 real-data 검증은 지번주소 resolver를 중심으로 완료됐다. 도로명주소 검색은 provider의 parcel search 특성과 별도 주소 변환 전략을 READ-ONLY 조사한 후 설계한다.

도로명주소를 지번/PNU로 변환할 때도 최종 authority는 동일-PNU parcel verification이어야 한다.

## 9. 분석 진입 UX — IDEA

필지 선택 완료 후 분석 전에 최소 확인 카드 제공을 고려한다:
- 선택 주소
- 지번
- 일반/산
- 지도 parcel highlight
- 필요한 경우 토지면적/지목 등 기본 공식정보
- `이 필지 분석` action

이 화면은 잘못된 필지 분석 비용을 줄이는 확인 boundary 역할을 한다.

## 10. 결과 화면 UX — IDEA

향후 결과 화면은 단순 AI 문장보다 다음 구조를 우선 고려한다:
- 필지 기본정보
- 핵심 규제 요약
- TRUE / FALSE / UNKNOWN 상태 구분
- 계산 가능한 건축규모/법정 상한
- 조건부/미확정 사항
- 지도 기반 규제/필지 overlay
- 근거 법령·고시·공식 데이터 provenance
- AI 설명
- 검증 상태 / 데이터 기준일

UNKNOWN을 오류처럼 숨기지 않고 왜 미확정인지 설명한다.

## 11. 향후 제품 backlog

현재 우선순위 방향:

```text
1. VERIFIED address identity → existing parcel analysis production wiring
2. public address input boundary
3. candidate search API design
4. candidate list UI
5. parcel polygon map UI
6. list ↔ map synchronization
7. user selection → backend re-verification contract
8. road-name address strategy
9. mobile interaction refinement
10. result/provenance visualization
```

각 항목은 구현 전 `PROJECT_ARCHITECTURE.md`의 safety boundary와 충돌 여부를 확인한다.

## 12. 관리 규칙

- Architecture invariant는 `PROJECT_ARCHITECTURE.md`가 authority다.
- 실제 완료/behavioral PASS는 `PROJECT_STATUS.md`가 기록한다.
- 제품 아이디어/화면 흐름/backlog는 이 문서가 관리한다.
- UX 변경이 canonical PNU, SITE truth, Rule Engine, legal authority 경계를 바꾸면 먼저 architecture review가 필요하다.
- 구현 전 exact WRITE scope와 테스트 계획을 확정한다.
