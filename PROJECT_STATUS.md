# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-17
기준 branch: `cleanup/repository-organization-20260916`
기준 behavioral PASS HEAD: `52f7b65e268fe4384553f84293d56ff5d129eb3e`
보존 checkpoint branch: `checkpoint/c12-fastapi-20260821`
보존 STEP114 HEAD: `ad06db07cf22138e5324eb263ae666814520eb53`
Architecture Baseline: v1.2

## 1. 현재 단계

STEP114 이후 historical SITE applicability, production forwarding, SITE-truth promotion 검증/실행/bridge, verified historical Rule Input envelope, district-unit common production lane, parcel-register identity, parcel-only production, public ordinary/mountain HTTP E2E, 그리고 주소 기반 verified parcel identity resolver까지 구현·사용자 로컬 검증했다.

STEP114 이후 기능 경계에는 새 architecture STEP 번호를 부여하지 않는다.

핵심 최신 user-local PASS:
- `HISTORICAL_SITE_EVENT_SITE_TRUTH_PROMOTION_RULE_INPUT_BRIDGE_CONTRACT_PASS`
- `HISTORICAL_SITE_TRUTH_PROMOTION_END_TO_END_REGRESSION_PASS`
- `SITE_ANALYSIS_ORCHESTRATOR_PROMOTION_RULE_INPUT_WIRING_CONTRACT_PASS`
- `HISTORICAL_RULE_ENGINE_VERIFIED_ENVELOPE_HANDOFF_PASS`
- `HISTORICAL_PRODUCTION_VERIFIED_ENVELOPE_EXPOSURE_PASS`
- `PARCEL_REGISTER_IDENTITY_PNU_CONTRACT_PASS`
- `PARCEL_ONLY_SITE_ORCHESTRATOR_CONTRACT_PASS`
- `SITE_IDENTITY_CROSS_PNU_FALLBACK_GUARD_CONTRACT_PASS`
- `PARCEL_ONLY_LAND_ENRICHMENT_CONTRACT_PASS`
- `PUBLIC_API_PARCEL_REGISTER_IDENTITY_CONTRACT_PASS`
- `PARCEL_ONLY_ADDRESS_ENRICHMENT_CONTRACT_PASS`
- `DISTRICT_UNIT_PLAN_SITE_TRUTH_PROMOTION_END_TO_END_REGRESSION_PASS`
- `ADDRESS_PARCEL_IDENTITY_RESOLVER_CONTRACT_PASS`

### Address → verified parcel identity validation

Behavioral PASS HEAD `52f7b65e268fe4384553f84293d56ff5d129eb3e` additionally validates the address parcel identity resolver without creating a new architecture STEP.

Validated resolver boundary:

```text
USER PARCEL ADDRESS
→ safe parcel-address normalization
→ VWorld parcel address search
→ exact address.parcel match
→ address-search item.id PNU
→ item coordinate
→ live LP_PA_CBND_BUBUN polygon query
→ polygon PNU
→ address PNU == polygon PNU
→ PNU component decomposition
→ create_pnu() exact regeneration
→ VERIFIED canonical parcel identity
```

Fail-closed behavior remains mandatory for empty search, no exact parcel match, address/polygon PNU mismatch, multiple distinct verified PNUs, invalid PNU, missing key, or unresolved parcel polygon.

User-local real-data validation confirmed both code-system branches:
- ordinary `서울특별시 강남구 개포동 12번지` → normalized search `서울특별시 강남구 개포동 12` → PNU `1168010300100120000` → `plat_gb_cd=0` → VERIFIED
- mountain `서울특별시 동작구 동작동 산 29-3` → PNU `1159010600200290003` → `plat_gb_cd=1` → VERIFIED

The ordinary search may return nearby lexical candidates such as `12-1` or `12-10`; these are not accepted for input `12`. Exact parcel-address matching occurs before live polygon verification.

The current resolver is an internal verified identity boundary. It is not yet wired as a public address-analysis endpoint and does not yet implement user-selectable candidate UX.

### Parcel register identity / parcel-only production validation

Code-system mapping remains explicit:

```text
Public API / Building HUB plat_gb_cd=0 (ordinary) → PNU land-register digit 1
Public API / Building HUB plat_gb_cd=1 (mountain) → PNU land-register digit 2
```

Building HUB status `00` with zero items can produce a parcel-only Site from canonical parcel identity. Same-PNU VWorld Land Characteristics may enrich land category, zoning, official land area, and parcel address. Cross-PNU persisted identity fallback remains blocked.

Previously user-local validated public HTTP E2E:
- ordinary `11680/10300/0/0012/0000` → PNU `1168010300100120000`, Building HUB 34 items, official land area `121040.4 square_meter`, identity COMPLETE
- mountain `11590/10600/1/0029/0003` → PNU `1159010600200290003`, parcel-only enrichment, official land area `16704.0 square_meter`, identity COMPLETE

Live EPSG:4326 parcel geometry area remains intentionally uncalculated. Official VWorld Land Characteristics area remains the primary land-area value; geometry is retained for spatial use and exact-PNU verification.

## 2. Current safety boundary

```text
address search result ≠ canonical parcel truth
user parcel selection ≠ canonical parcel truth
resolver result ≠ parcel applicability
SITE-decision eligibility ≠ SITE truth
SITE applicability admission ≠ production/runtime registration authority
promotion authorization ≠ second SITE truth store
verified envelope ≠ new Rule Engine
```

No identity/address/zone/coordinate/geometry/evidence may be reused across a different PNU. Address-derived identity must be rebound to live same-PNU parcel geometry before VERIFIED status.

Historical production remains PNU-bound and fail-closed. Raw historical production injection, malformed envelopes, cross-PNU handoff, UNKNOWN applicability, unauthorized promotion, spatial/historical conflicts, public historical input, historical spatial runtime registration, and cross-PNU identity fallback remain blocked.

## 3. Promotion / production reconciliation

Promotion does not create a second Rule Engine or SITE truth store.

```text
verified historical candidate
→ same-fact binding
→ canonical PNU binding
→ final promotion authorization
→ isolated executor
→ promotion Rule Input bridge
→ Orchestrator actual-SITE PNU recheck
→ verified envelope
→ Service / Builder PNU recheck
→ existing production consumption architecture
```

Historical and district-unit paths keep family-specific verification boundaries but converge at the common verified SITE registry / existing Rule Engine lane. Simultaneous historical + district-unit production input remains fail-closed because no cross-family merge policy is authorized.

## 4. Historical / hybrid locks

Public API historical exposure remains NOT AUTHORIZED. Historical data remains excluded from the spatial runtime condition channel.

### 도시지역편입해제구역
- family: `HISTORICAL_SITE_EVENT`
- standard code: None / UNVERIFIED / DO NOT GUESS
- unresolved real-condition evidence remains fail-closed

### 개발밀도관리구역 / UQQ700
- family: `HYBRID_SPATIAL_NOTICE`
- standard code: `UQQ700`
- legal-source resolution: UNKNOWN
- negative-evidence / legal-absence inference disabled
- SITE TRUE/FALSE promotion blocked
- production/runtime registration blocked

Legal-source S-numbering remains separate from architecture STEP numbering.

## 5. Documentation / product design state

Architecture Baseline remains v1.2. Address parcel identity verification is now part of the validated architecture, but public address-to-analysis wiring is not yet validated.

Product/UI ideas are tracked separately in `PROJECT_PRODUCT_UX.md`. Product ideas do not become architecture truth or implementation status merely by being documented there.

## 6. Repository / local rules

Repository: `jehun0620-bot/site-ai`
Current branch: `cleanup/repository-organization-20260916`
Preserved checkpoint: `checkpoint/c12-fastapi-20260821`
Local root: `D:\site-ai`

Never modify/commit `.env`, `law_data/output/*`, or unrelated files without explicit approved scope. Never use broad staging commands.

Protected local-only modified file:
`law_data/output/urban_area_conversion_history_final_resolution.json`

Expected state:
```text
 M law_data/output/urban_area_conversion_history_final_resolution.json
```

Never modify, restore, checkout, reset, delete, stage, commit, or clean this protected file. User-local execution PASS remains final behavioral validation.

## 7. Standard development process

```text
READ-ONLY audit
→ exact WRITE scope approval when needed
→ IMPLEMENT
→ remote HEAD confirm
→ local protected-file check
→ git pull --ff-only
→ py_compile / focused contracts / necessary regressions
→ final protected-file check
→ user-local PASS
→ next READ-ONLY audit
```

## 8. Next action

Next architecture/product work should begin with READ-ONLY inspection for safe wiring of:

```text
VERIFIED ADDRESS PARCEL IDENTITY
→ canonical component input
→ existing analyze_site_by_parcel pipeline
```

Do not wire raw/unverified address-search results directly into analysis. Preserve canonical PNU binding, same-PNU evidence, ordinary/mountain distinction, one SITE truth / Rule Engine lane, verified-envelope fail-closed behavior, public historical non-exposure, spatial/historical separation, UQQ700 UNKNOWN/BLOCKED, and no invented architecture STEP number.

Candidate-list + map-assisted parcel selection is a future product UX boundary and is tracked separately in `PROJECT_PRODUCT_UX.md`.

## 9. Handoff policy

In a new chat, reconstruct actual branch HEAD and current files from GitHub READ-ONLY first. Current GitHub code plus user-local execution results override stale summaries/documents.
