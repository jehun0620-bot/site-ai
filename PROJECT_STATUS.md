# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-17
기준 branch: `cleanup/repository-organization-20260916`
기준 behavioral PASS HEAD: `e29d676b84f99cc220c52a18196af575631d60b3`
보존 checkpoint branch: `checkpoint/c12-fastapi-20260821`
보존 STEP114 HEAD: `ad06db07cf22138e5324eb263ae666814520eb53`
Architecture Baseline: v1.2

## 1. 현재 단계

STEP114 이후 historical SITE applicability, production forwarding, SITE-truth promotion 전 검증, isolated promotion execution, promotion Rule Input bridge, production orchestrator wiring, verified historical Rule Input envelope까지 구현·사용자 로컬 검증했다.

STEP114 이후 기능 경계에는 아직 새 architecture STEP 번호를 부여하지 않는다.

현재 locally validated 흐름:

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
→ historical parcel applicability evidence
→ PNU-bound SITE applicability admission
→ actual SITE PNU rebinding
→ candidate↔repair consistency authorization
→ candidate↔condition binding authorization
→ admitted historical rule-input adapter
→ pre-promotion same-fact binding authorization
→ PNU-scoped pre-promotion authorization
→ final non-executing promotion authorization
→ isolated promotion executor
→ promotion Rule Input bridge
→ production orchestrator PNU rebinding
→ verified historical Rule Input envelope
→ service
→ builder envelope/PNU recheck
→ historical registry / collision / live-consumption authorization
→ existing Rule Engine
```

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

이전 applicability/state/condition binding 계약과 STEP74 reconciliation도 이미 user-local PASS 상태다.

### Parcel register identity / parcel-only production validation

Behavioral PASS HEAD `e29d676b84f99cc220c52a18196af575631d60b3` additionally validates ordinary/mountain parcel identity and vacant/unbuilt parcel analysis without creating a new architecture STEP.

Code-system mapping is explicit:

```text
Public API / Building HUB plat_gb_cd=0 (ordinary) → PNU land-register digit 1
Public API / Building HUB plat_gb_cd=1 (mountain) → PNU land-register digit 2
```

When Building HUB returns status `00` with zero items, the Orchestrator can create a parcel-only Site from canonical parcel identity. Same-PNU VWorld Land Characteristics may enrich land category, zoning, official land area, and parcel address. Cross-PNU persisted identity fallback remains blocked.

Real-data mountain validation for `서울특별시 동작구 동작동 산 29-3` confirmed:
- canonical PNU `1159010600200290003`
- Building HUB zero-item response handled without failure
- same-PNU address `서울특별시 동작구 동작동 산 29-3`
- zoning `자연녹지지역`
- official land area `16704.0 square_meter` from `VWORLD_LAND_CHARACTERISTICS`
- address-search coordinate confirmed in `EPSG:4326`
- VWorld `LP_PA_CBND_BUBUN` MultiPolygon loaded
- live feature PNU exactly matched requested PNU
- `PNU_POLYGON_VERIFIED`
- `identity_status=COMPLETE`
- mismatched stored snapshot PNU was not reused

Public FastAPI HTTP E2E also validated both branches:
- ordinary `11680/10300/0/0012/0000` → PNU `1168010300100120000`, Building HUB 34 items, official land area `121040.4 square_meter`, identity COMPLETE
- mountain `11590/10600/1/0029/0003` → PNU `1159010600200290003`, parcel-only enrichment, official land area `16704.0 square_meter`, identity COMPLETE

Live EPSG:4326 parcel geometry area remains intentionally uncalculated. Official VWorld Land Characteristics area is preserved separately as the primary land-area value; geometry is retained for spatial use and exact-PNU verification.

## 2. Current safety boundary

```text
resolver result ≠ parcel applicability
SITE-decision eligibility ≠ SITE truth
SITE applicability admission ≠ production/runtime registration authority
promotion authorization ≠ second SITE truth store
verified envelope ≠ new Rule Engine
```

Current parcel identity safety additionally requires no identity/address/zone/coordinate evidence reuse across a different PNU. Parcel-only enrichment must remain bound to the current canonical PNU and fail closed when required identity evidence is missing or mismatched.

현재 historical production 경로는 Orchestrator에서 실제 Site PNU를 검증한 뒤에만 historical Rule Input을 PNU-bound verified envelope로 봉인한다. Service와 Builder는 raw historical dict를 production historical input으로 허용하지 않는다. Builder는 envelope canonical PNU와 현재 `site_input` PNU를 다시 비교한 뒤에만 기존 historical registry adapter → collision policy → live-consumption authorization → 기존 Rule Engine 경로를 사용한다.

Fail-closed 차단:
- raw `historical_rule_input` orchestrator 직접 주입
- raw historical dict의 service 직접 주입
- raw historical dict의 builder 직접 주입
- malformed/not-ready verified envelope
- envelope PNU와 실제 Site/builder PNU 불일치
- handoff/applicability 한쪽만 존재
- UNKNOWN/unverified parcel applicability
- candidate와 repair state 불일치
- 서로 다른 historical condition identity 혼재
- unauthorized/forged handoff
- spatial/historical registry conflict
- public API historical input
- historical spatial runtime registration
- cross-PNU identity/address/zone/coordinate fallback

## 3. Promotion reconciliation

Promotion 계층은 별도 Rule Engine 또는 별도 SITE truth store를 만들지 않는다.

```text
verified historical candidate
→ same-fact binding
→ current canonical PNU binding
→ final promotion authorization
→ isolated executor
→ promotion Rule Input bridge
→ Orchestrator actual-SITE PNU recheck
→ verified envelope
→ existing production consumption architecture
```

Promotion bridge는 executor가 이미 만든 promoted SITE condition의 type/state/confidence/source/PNU 정합성을 fail-closed로 검증한다. Bridge 자체는 global registry를 쓰거나 Rule Engine을 호출하거나 public API를 노출하지 않는다.

## 4. Historical safety / real condition locks

Public API historical exposure remains NOT AUTHORIZED.
Historical data remains excluded from the spatial runtime condition channel.

### 도시지역편입해제구역
- resolution family: `HISTORICAL_SITE_EVENT`
- standard code: None / UNVERIFIED / DO NOT GUESS
- unresolved real-condition evidence remains fail-closed
- production/runtime registration remains BLOCKED unless later evidence and authorization explicitly support it

### 개발밀도관리구역 / UQQ700
- resolution family: `HYBRID_SPATIAL_NOTICE`
- standard code: `UQQ700`
- current legal-source resolution remains UNKNOWN
- negative evidence / legal absence inference disabled
- SITE TRUE/FALSE promotion remains blocked without required verified evidence
- production/runtime registration remains blocked
- minimum gate: official designation identity + current validity + SITE spatial inclusion verification
- historical production reconciliation does not activate UQQ700 or move it to `HISTORICAL_SITE_EVENT`

Legal-source investigation numbering (`S206`…`S216`/future S217) is separate from architecture STEP numbering.

## 5. Production wiring state

`site_data/site_analysis_orchestrator.py` owns the production sealing point. Legacy typed historical applicability/handoff and the newer promotion bridge remain mutually exclusive entry modes; both must pass their own gates and actual-SITE PNU rebinding before a verified envelope is sent downstream.

`site_data/site_analysis_service.py` and `law_data/site_analysis_builder.py` now require `HistoricalVerifiedRuleInputEnvelope` for historical production consumption. The builder independently checks envelope PNU against current site input PNU.

Downstream remains the existing single consumption lane:

```text
historical registry adapter
→ spatial/historical collision policy
→ merged-registry live-consumption authorization
→ existing Rule Engine
```

Repository-wide local grep at behavioral PASS HEAD found no production raw-historical bypass caller. Remaining direct raw calls are fail-closed tests or isolated adapter/bridge tests.

## 6. Repository cleanup checkpoint

Cleanup branch: `cleanup/repository-organization-20260916`
Cleanup started from STEP114 checkpoint: `ad06db07cf22138e5324eb263ae666814520eb53`

Validated cleanup remains unchanged. Do not mechanically move/delete `law_data/*` or `site_data/*` for cosmetic cleanup without dependency/path audit and separate approval.

## 7. Documentation / architecture state

Architecture Baseline remains v1.2. No new architecture STEP number is assigned. Current documentation records the post-STEP114 functional boundaries through promotion wiring, verified-envelope production hardening, and parcel-register identity / parcel-only production validation.

## 8. Git / local rules

Repository: `jehun0620-bot/site-ai`
Current branch: `cleanup/repository-organization-20260916`
Preserved checkpoint: `checkpoint/c12-fastapi-20260821`
Local root: `D:\site-ai`

GitHub/local write requires explicit scope/purpose/non-target approval.
Never modify/commit `.env`, `law_data/output/*`, or unrelated files.
Never use `git add .`, `git add -A`, or `git add --all`.

Protected local-only modified file:
`law_data/output/urban_area_conversion_history_final_resolution.json`

Expected state:
```text
 M law_data/output/urban_area_conversion_history_final_resolution.json
```

Never modify, restore, checkout, reset, delete, stage, commit, or clean this protected file.
User local execution PASS remains final behavioral validation.

## 9. Standard development process

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

## 9A. District-unit / common production reconciliation

District-unit verified production transport remains user-local validated.

District-unit verified input follows:

```text
verified district-unit envelope
→ Orchestrator actual-SITE PNU recheck
→ Service typed-envelope / PNU recheck
→ Builder typed-envelope / PNU recheck
→ district spatial collision / live authorization
→ common verified SITE registry
→ existing Rule Engine
```

Historical and district-unit paths keep their family-specific verification and authorization boundaries, but converge at the common verified SITE registry / existing Rule Engine lane.

Historical + district-unit simultaneous production input remains fail-closed because no cross-family merge policy is authorized.

User-local PASS includes the district-unit Orchestrator E2E, Service handoff, Builder handoff, collision/live authorization, common registry, common Rule Engine, and historical regressions.

This does not authorize UQQ700, public historical injection, a second SITE truth store, or a second Rule Engine. UQQ700 remains UNKNOWN/BLOCKED.

## 10. Next action

Ordinary and mountain parcel identity, parcel-only enrichment, cross-PNU identity protection, real VWorld spatial recovery, and Public FastAPI HTTP E2E are validated at behavioral PASS HEAD `e29d676b84f99cc220c52a18196af575631d60b3`.

The next work should start with a READ-ONLY architecture/product gap audit rather than assuming a new STEP. Preserve:
- one SITE truth / Rule Engine consumption architecture
- canonical PNU binding
- same-PNU identity/spatial evidence boundary
- verified-envelope fail-closed boundary
- public API historical non-exposure
- spatial-runtime historical separation
- UQQ700 UNKNOWN/BLOCKED policy
- no invented architecture STEP number

## 11. Handoff policy

In a new chat, reconstruct actual branch HEAD and current files from GitHub READ-ONLY first. Current GitHub code plus user-local execution results override stale summaries/documents.
