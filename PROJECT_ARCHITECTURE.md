# AI 대지분석 자동화 시스템 — PROJECT ARCHITECTURE

최종 reconciliation: 2026-09-17
Architecture Baseline: v1.2

## 1. 프로젝트 목표

주소 또는 필지를 입력하면 canonical SITE/PNU와 공식 데이터·법적 근거를 추적하여 규제 TRUE/FALSE/UNKNOWN, 적용 법령과 고시, 계산 가능한 규제값, 조건부 결과, provenance와 검증 가능한 최종 대지분석을 생성한다.

## 2. 최상위 원칙

```text
OFFICIAL FACT
→ SITE FACT
→ REGULATION RESOLUTION
→ LEGAL RULE
→ DETERMINISTIC ENGINE
→ AI ANALYSIS
→ VERIFICATION
```

불변조건:
- 검색 결과 ≠ 법적 사실
- 주소 검색 결과 ≠ canonical parcel truth
- 사용자 UI 선택 ≠ canonical parcel truth
- 문서 발견 ≠ 규제 TRUE
- 고시 발견 ≠ 현재 유효
- point 포함 ≠ parcel 포함
- source 미발견 ≠ FALSE
- resolver result ≠ parcel applicability
- SITE-decision eligibility ≠ SITE truth
- SITE applicability admission ≠ production/runtime registration authority
- promotion authorization ≠ second SITE truth store
- verified envelope ≠ new Rule Engine
- 다른 PNU의 identity/address/zone/coordinate/geometry/evidence 재사용 금지

## 3. 전체 레이어

```text
USER / PROJECT INPUT
→ PARCEL IDENTITY & OFFICIAL LAND DATA
→ SITE FACT MODEL
→ REGULATION RESOLUTION
→ LEGAL KNOWLEDGE
→ RULE NORMALIZATION
→ DETERMINISTIC EVALUATION
→ RETRIEVAL & LEGAL CONTEXT
→ AI ANALYSIS
→ VERIFICATION & PROVENANCE
→ PRODUCT / API / REPORT
```

SITE CONDITION과 PROJECT CONDITION을 분리한다. PROJECT 조건을 SITE 사실로 자동 승격하지 않는다.

## 4. Canonical SITE / PNU

모든 후속 판정은 동일한 실제 필지를 바라봐야 한다. 다른 PNU의 snapshot, geometry, evidence, admission, promotion input을 재사용하지 않는다.

```text
Public API / Building HUB plat_gb_cd=0 (일반) → PNU land-register digit 1
Public API / Building HUB plat_gb_cd=1 (산)   → PNU land-register digit 2
```

Building HUB status `00` + 건축물 0건도 canonical parcel identity가 유효하면 parcel-only Site를 구성할 수 있다. 건축물 존재 여부를 필지 존재 여부와 동일시하지 않는다.

Parcel-only enrichment는 현재 canonical PNU와 정확히 같은 공식 토지특성 record에만 의존한다.

### 4A. Address → verified canonical parcel identity

```text
USER PARCEL ADDRESS
→ safe parcel-address normalization
→ VWorld parcel address search
→ exact address.parcel match
→ search item.id PNU
→ item coordinate
→ live LP_PA_CBND_BUBUN polygon query
→ polygon PNU
→ address PNU == polygon PNU
→ PNU component decomposition
→ create_pnu() regeneration == original PNU
→ VERIFIED canonical parcel identity
```

일반 지번의 말미 `번지` 표기는 검색 호환을 위해 안전하게 정규화할 수 있다. 검색이 `12`, `12-1`, `12-10` 등을 함께 반환하더라도 exact parcel-address match 전에는 어느 후보도 canonical identity가 아니다.

Empty search, no exact match, address/polygon PNU mismatch, multiple distinct verified PNUs, invalid PNU, missing key, unresolved live parcel은 fail-closed다.

### 4B. Verified address → existing parcel analysis

Address identity는 별도 분석 lane을 만들지 않는다. VERIFIED identity만 기존 parcel component pipeline으로 변환한다.

```text
VERIFIED ADDRESS PARCEL IDENTITY
→ sigungu_cd
→ bjdong_cd
→ plat_gb_cd
→ bun
→ ji
→ existing analyze_site_by_parcel()
→ existing SITE / regulation / Rule Engine pipeline
```

`analyze_site_by_address()`는 identity front door / adapter 역할만 한다. Address resolver가 VERIFIED가 아니면 기존 분석 pipeline에 진입하지 못한다.

User-local behavioral validation at HEAD `b9d204cc6c6d128a46ed33ee38071a3c4f545065` confirmed both full real-data paths:
- ordinary `서울특별시 강남구 개포동 12번지` → PNU `1168010300100120000` → Building HUB 34 → 제3종일반주거지역 → identity COMPLETE
- mountain `서울특별시 동작구 동작동 산 29-3` → PNU `1159010600200290003` → Building HUB 0 parcel-only path → 자연녹지지역 → identity COMPLETE

Thus address → verified identity → existing full analysis internal E2E is validated for ordinary and mountain parcels.

## 5. Runtime spatial SITE fact

Runtime spatial condition은 parcel geometry, target PNU, CRS, regulation geometry intersection을 검증한다. Spatial query 실패를 FALSE로 바꾸지 않는다. Historical provenance는 spatial runtime condition channel과 별도로 유지한다.

Parcel-only 경로에서는 동일-PNU 공식 지번주소가 확보되면 address search를 통해 좌표를 구하고, VWorld parcel dataset의 live polygon feature PNU가 requested canonical PNU와 정확히 일치할 때만 geometry를 채택한다.

EPSG:4326 live geometry는 공간 판정용으로 유지하며 면적을 임의 계산하지 않는다. 공식 토지면적은 VWorld Land Characteristics 값을 별도 보존한다.

## 6. Regulation resolution / numbered chain

표준 상태는 `TRUE / FALSE / UNKNOWN`이다.

```text
STEP98 Evidence→Seed admission
→ STEP101 verified classification→profile admission
→ STEP103 registry classification compatibility
→ STEP104 resolver-family eligibility
→ STEP106 dispatch plan
→ STEP108 input admission
→ STEP110 resolver execution
→ STEP112 resolver result verification
→ STEP114 SITE-decision eligibility
```

STEP114 이후 구현 경계에는 새 STEP 번호를 부여하지 않는다.

## 7. Historical / district-unit production

Historical and district-unit paths keep family-specific verification but converge at the common verified SITE registry / existing Rule Engine lane. Promotion does not create a second SITE truth store or Rule Engine.

Raw historical injection, malformed envelope, cross-PNU handoff, UNKNOWN applicability, unauthorized promotion and simultaneous historical + district-unit input remain fail-closed where no explicit policy authorizes them.

Public historical input remains NOT AUTHORIZED.

## 8. Hybrid / UQQ700

### UQQ700 개발밀도관리구역
- family: `HYBRID_SPATIAL_NOTICE`
- standard code: `UQQ700`
- legal-source resolution: UNKNOWN
- negative-evidence / legal-absence inference disabled
- SITE TRUE/FALSE promotion blocked
- production/runtime registration blocked

## 9. Public API / runtime exposure

Current validated public parcel-component endpoint:

```text
POST /v1/site-analysis
→ sigungu_cd / bjdong_cd / plat_gb_cd / bun / ji
→ analyze_site_by_parcel()
```

Ordinary and mountain parcel-component HTTP E2E are already user-local validated.

The internal address path is now validated, but public address HTTP exposure is not yet implemented/validated. The correct public boundary is deliberately thin:

```text
POST /v1/site-analysis/address
→ address request validation
→ analyze_site_by_address()
→ VERIFIED address identity
→ existing analyze_site_by_parcel()
→ existing response
```

The HTTP layer must not independently parse PNU, query VWorld, select parcel candidates, or duplicate analysis logic.

Candidate-list/map-assisted selection remains a separate future product API/UX boundary. It must not be mixed into the first exact-address analysis endpoint.

## 10. Legal / provenance / deterministic evaluation

Legal delegation/version chains and provenance remain preserved. AI may explain but does not invent regulation TRUE/FALSE, PNU, legal source or numeric limit. Calculable results belong to deterministic evaluation; unresolved conditions remain unresolved.

## 11. Test / fail-safe policy

```text
잘못된 TRUE보다 UNKNOWN이 낫다.
잘못된 FALSE보다 UNKNOWN이 낫다.
```

Test categories include UNIT, BEHAVIORAL REGRESSION, INTEGRATION, END-TO-END and POLICY ASSERTION. User-local execution PASS is final behavioral validation.

## 12. Product UX separation

- `PROJECT_ARCHITECTURE.md`: validated system boundaries and invariants
- `PROJECT_STATUS.md`: implementation / validation checkpoint
- `PROJECT_PRODUCT_UX.md`: product-facing ideas, candidate workflows, map interactions and backlog

A UX idea does not become architecture truth merely by documentation. UI convenience never bypasses canonical PNU verification.

## 13. Security / repository policy

- API keys in `.env`; secrets Git 저장 금지
- runtime raw/cache와 Git source 분리
- `law_data/output/*` 보호
- explicit WRITE approval before repository mutation
- user-local behavioral PASS is final validation

## 14. Numbering policy

Architecture STEP98…STEP114와 legal-source investigation S-numbering은 별개다. 새 architecture STEP은 repository design/documentation에서 명시적으로 확립할 때만 부여한다.

## 15. Current validated architecture position

```text
USER PARCEL COMPONENTS
→ canonical PNU
→ existing parcel analysis pipeline

USER PARCEL ADDRESS
→ normalized/exact parcel search
→ address PNU + coordinate
→ live parcel polygon PNU verification
→ reconstructed canonical parcel identity
→ VERIFIED
→ analyze_site_by_address()
→ canonical parcel components
→ existing analyze_site_by_parcel()
→ ordinary Building HUB OR parcel-only path
→ same-PNU SITE / spatial / regulation pipeline
```

No second SITE truth store, Rule Engine, or address-specific analysis engine is created.

## 16. Next design question

Internal address-to-full-analysis E2E is validated. The next boundary is public HTTP exposure through the existing thin FastAPI layer.

Preserve:
- verified identity only
- no raw address candidate admitted to analysis
- ordinary/mountain distinction
- same-PNU evidence
- existing analyze-by-parcel path
- one SITE truth / Rule Engine lane
- public historical non-exposure
- UQQ700 UNKNOWN/BLOCKED
- no invented architecture STEP number

After public HTTP address E2E validation, candidate-search/list/map product APIs can be designed separately under `PROJECT_PRODUCT_UX.md`.
