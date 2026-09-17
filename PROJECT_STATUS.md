# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-17
기준 branch: `cleanup/repository-organization-20260916`
기준 behavioral PASS HEAD: `f54cd84b6c91cd2f8c0e47612223133daac97a4d`
보존 checkpoint branch: `checkpoint/c12-fastapi-20260821`
보존 STEP114 HEAD: `ad06db07cf22138e5324eb263ae666814520eb53`
Architecture Baseline: v1.2

## 1. 현재 단계

STEP114 이후 historical SITE applicability/production/promotion, district-unit common production lane, parcel-register identity, parcel-only production, address-based verified parcel identity, address→existing full-analysis internal wiring, 그리고 public address HTTP endpoint까지 구현·사용자 로컬 검증했다.

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
- `ADDRESS_SITE_ANALYSIS_ORCHESTRATOR_WIRING_CONTRACT_PASS`
- `PUBLIC_API_ADDRESS_SITE_ANALYSIS_CONTRACT_PASS`

### Public address HTTP E2E — VALIDATED

Behavioral PASS HEAD `f54cd84b6c91cd2f8c0e47612223133daac97a4d` contains the thin public address endpoint and contract. User-local real HTTP execution with `python -m uvicorn api_app:app --host 127.0.0.1 --port 8000` confirmed both ordinary and mountain address paths.

```text
POST /v1/site-analysis/address
→ address request validation
→ analyze_site_by_address()
→ VERIFIED address parcel identity
→ canonical parcel components
→ existing analyze_site_by_parcel()
→ existing full SITE analysis
→ SITE_ANALYSIS_API_V1 / READY
```

Ordinary real HTTP:
```text
서울특별시 강남구 개포동 12번지
→ PNU 1168010300100120000
→ site_id 11680-10300-0012-0000
→ identity_status COMPLETE
→ building_count 34
→ status READY
```

Mountain real HTTP:
```text
서울특별시 동작구 동작동 산 29-3
→ PNU 1159010600200290003
→ site_id 11590-10600-0029-0003
→ identity_status COMPLETE
→ building_count 0
→ parcel-only path
→ status READY
```

PowerShell displayed Korean mojibake in the formatted object output, while PNU/site_id/status/counts remained correct and prior direct Python execution displayed Korean correctly. This is treated as a terminal display-encoding issue, not a parcel-identity or analysis failure.

### Address identity safety boundary

```text
USER PARCEL ADDRESS
→ normalization
→ VWorld parcel search
→ exact address.parcel match
→ address item PNU + coordinate
→ live LP_PA_CBND_BUBUN
→ polygon PNU exact match
→ PNU decomposition + create_pnu regeneration
→ VERIFIED canonical parcel identity
```

Search result, candidate item, coordinate, or user selection alone is never canonical parcel truth.

## 2. Current safety boundary

```text
address search result ≠ canonical parcel truth
candidate parcel ≠ canonical parcel truth
user parcel selection ≠ canonical parcel truth
verified address identity → existing parcel pipeline only
resolver result ≠ parcel applicability
SITE-decision eligibility ≠ SITE truth
SITE applicability admission ≠ production/runtime registration authority
promotion authorization ≠ second SITE truth store
verified envelope ≠ new Rule Engine
```

No identity/address/zone/coordinate/geometry/evidence may be reused across a different PNU. Historical production remains PNU-bound/fail-closed. Public historical input remains unauthorized. UQQ700 remains UNKNOWN/BLOCKED.

## 3. Product-facing position

The exact-address public analysis boundary is now validated. The next product-facing gap is candidate discovery for incomplete/prefix-like address input.

Current VWorld parcel search already returns candidate items containing useful product data such as:
- `id`: candidate PNU
- `address.parcel`: parcel address
- `address.road`: road address when available
- `address.bldnm`: building name when available
- `point.x / point.y`: map centering coordinate

However, the existing resolver intentionally hides these candidates and only admits an exact parcel-address match into verification. Candidate discovery therefore needs a separate read-only/search boundary rather than weakening the verified resolver.

Candidate search must not itself start analysis or mark candidates VERIFIED.

## 4. Documentation / product design

Architecture Baseline remains v1.2.

- `PROJECT_ARCHITECTURE.md`: validated architecture/invariants
- `PROJECT_STATUS.md`: current implementation and behavioral validation checkpoint
- `PROJECT_PRODUCT_UX.md`: product-facing ideas and UX backlog

## 5. Repository / local rules

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

## 6. Standard development process

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

## 7. Next action

Design a candidate-search boundary without changing the existing verified resolver semantics.

Preferred separation:

```text
DISCOVERY
user query
→ candidate search
→ candidate PNU/address/point metadata
→ UI list/map

SELECTION + VERIFICATION
user selects candidate
→ backend re-verifies selected PNU against live parcel geometry
→ VERIFIED canonical parcel identity
→ existing analysis pipeline
```

The first candidate-search implementation should remain read-only and must not perform SITE truth, regulation truth, or analysis admission.

## 8. Handoff policy

In a new chat, reconstruct actual branch HEAD and current files from GitHub READ-ONLY first. Current GitHub code plus user-local execution results override stale summaries/documents.
