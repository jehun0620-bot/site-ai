import type { ParcelCandidate } from '../types/parcel'
import type { BuildingUseCatalogResponse, SiteAnalysisInputProfile, SiteAnalysisInputState, SiteAnalysisNumericFactProfile, SiteAnalysisResponse, SiteAnalysisStateFactProfile } from '../types/siteAnalysis'
import { ProductApiError, readApiError, type ProductErrorDetail } from './productError'

export class SiteAnalysisApiError extends ProductApiError {
  constructor(message: string, httpStatus = 0, detail: ProductErrorDetail | null = null) {
    super(message, httpStatus, detail)
    this.name = 'SiteAnalysisApiError'
  }
}

export async function fetchBuildingUseCatalog(signal?: AbortSignal): Promise<BuildingUseCatalogResponse> {
  const response = await fetch('/v1/building-uses', { signal })
  if (!response.ok) throw new SiteAnalysisApiError('계획 건축물 용도 목록을 불러오지 못했습니다.', response.status)

  const body: unknown = await response.json()
  if (!isBuildingUseCatalogResponse(body)) throw new SiteAnalysisApiError('계획 건축물 용도 목록 응답 형식이 올바르지 않습니다.')
  return body
}

export interface SiteAnalysisInputProfiles {
  project_profile?: SiteAnalysisInputProfile
  procedure_profile?: SiteAnalysisInputProfile
  building_use_name?: string
  numeric_facts?: SiteAnalysisNumericFactProfile
  state_facts?: SiteAnalysisStateFactProfile
}

export async function analyzeSelectedParcelCandidate(
  candidate: ParcelCandidate,
  profiles: SiteAnalysisInputProfiles = {},
  signal?: AbortSignal,
): Promise<SiteAnalysisResponse> {
  const response = await fetch('/v1/site-analysis/selected-candidate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      candidate_pnu: candidate.candidate_pnu,
      x: candidate.x,
      y: candidate.y,
      project_profile: profiles.project_profile ?? {},
      procedure_profile: profiles.procedure_profile ?? {},
      building_use_name: profiles.building_use_name,
      numeric_facts: profiles.numeric_facts ?? {},
      has_spectator_seating: profiles.state_facts?.has_spectator_seating,
      include_debug: false,
    }),
    signal,
  })

  if (!response.ok) {
    const error = await readApiError(response)
    const message = error.detail?.message ?? error.legacyMessage ?? 'SITE 분석을 완료하지 못했습니다.'
    throw new SiteAnalysisApiError(message, response.status, error.detail)
  }

  const body: unknown = await response.json()
  if (!isSiteAnalysisResponse(body)) throw new SiteAnalysisApiError('SITE 분석 응답 형식이 올바르지 않습니다.')
  return body
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

function isBuildingUseCatalogResponse(value: unknown): value is BuildingUseCatalogResponse {
  if (!isRecord(value) || value.schema_version !== 'BUILDING_USE_CATALOG_V1' || value.status !== 'READY') return false
  if (typeof value.count !== 'number' || !Array.isArray(value.building_uses)) return false
  if (value.count !== value.building_uses.length) return false
  return value.building_uses.every((item) => isRecord(item) && typeof item.canonical_name === 'string' && typeof item.input_scope === 'string')
}

function isNullableNumber(value: unknown): boolean {
  return value === null || typeof value === 'number'
}

function isSiteAnalysisInputState(value: unknown): value is SiteAnalysisInputState {
  return value === 'TRUE' || value === 'FALSE' || value === 'UNKNOWN' || value === 'UNSET'
}

function isSiteAnalysisRequirement(value: unknown): boolean {
  return isRecord(value) && typeof value.name === 'string' && typeof value.affected_clause_count === 'number' && isSiteAnalysisInputState(value.state)
}

function isBuildingUseRequirement(value: unknown): boolean {
  if (!isSiteAnalysisRequirement(value) || !isRecord(value)) return false
  if (value.identity !== 'canonical' && value.identity !== 'source_path' && value.identity !== 'major') return false
  if (value.allowed_values === undefined) return true
  return Array.isArray(value.allowed_values)
    && value.allowed_values.length > 0
    && value.allowed_values.every((item) => typeof item === 'string' && item.trim().length > 0)
}

function isStateFactRequirement(value: unknown): boolean {
  return isRecord(value)
    && typeof value.name === 'string'
    && isSiteAnalysisInputState(value.state)
    && value.source === 'BUILDING_USE_CLASSIFICATION'
}

function isNumericFactRequirement(value: unknown): boolean {
  return isSiteAnalysisRequirement(value) && isRecord(value) && typeof value.unit === 'string'
}

function isNullableString(value: unknown): boolean {
  return value === null || typeof value === 'string'
}

function isSiteAnalysisBuildingFact(value: unknown): boolean {
  if (!isRecord(value)) return false
  return (value.management_id === null || typeof value.management_id === 'string' || typeof value.management_id === 'number')
    && typeof value.dong_name === 'string'
    && typeof value.building_name === 'string'
    && typeof value.main_use === 'string'
    && typeof value.structure === 'string'
    && typeof value.roof === 'string'
    && isNullableNumber(value.land_area)
    && isNullableNumber(value.building_area)
    && isNullableNumber(value.total_floor_area)
    && isNullableNumber(value.building_coverage_ratio)
    && isNullableNumber(value.floor_area_ratio)
    && isNullableNumber(value.ground_floor_count)
    && isNullableNumber(value.underground_floor_count)
    && isNullableNumber(value.household_count)
    && typeof value.permit_date === 'string'
    && typeof value.approval_date === 'string'
}

function isSiteAnalysisResponse(value: unknown): value is SiteAnalysisResponse {
  if (!isRecord(value)) return false
  const body = value
  if (body.schema_version !== 'SITE_ANALYSIS_API_V1') return false
  if (!isRecord(body.site) || !isRecord(body.requirements)) return false
  if (!isRecord(body.land_area) || !isRecord(body.regulation) || !isRecord(body.site_facts)) return false
  if (!isRecord(body.rule_evaluation) || !isRecord(body.external_dependencies)) return false
  if (!('spatial' in body)) return false

  const site = body.site
  const requirements = body.requirements
  const landArea = body.land_area
  const regulation = body.regulation
  const ruleEvaluation = body.rule_evaluation
  const externalDependencies = body.external_dependencies
  const siteFacts = body.site_facts
  const nullableString = (item: unknown) => item === null || typeof item === 'string'

  const projectRequirements = requirements.project
  const procedureRequirements = requirements.procedure
  const buildingUseRequirements = requirements.building_use
  const stateFactRequirements = requirements.state_facts
  const numericFactRequirements = requirements.numeric_facts
  const externalDependencyItems = externalDependencies.items
  if (!isRecord(siteFacts.land) || !isRecord(siteFacts.buildings) || !isRecord(siteFacts.sources)) return false
  const factLand = siteFacts.land
  const factBuildings = siteFacts.buildings
  const factSources = siteFacts.sources
  const factBuildingItems = factBuildings.items

  const siteValid = nullableString(site.site_id) && nullableString(site.address) && nullableString(site.road_address) && nullableString(site.pnu) && nullableString(site.sigungu_code) && nullableString(site.bjdong_code) && nullableString(site.main_no) && nullableString(site.sub_no)
  const requirementsValid = Array.isArray(projectRequirements) && projectRequirements.every(isSiteAnalysisRequirement)
    && Array.isArray(procedureRequirements) && procedureRequirements.every(isSiteAnalysisRequirement)
    && Array.isArray(buildingUseRequirements) && buildingUseRequirements.every(isBuildingUseRequirement)
    && Array.isArray(stateFactRequirements) && stateFactRequirements.every(isStateFactRequirement)
    && Array.isArray(numericFactRequirements) && numericFactRequirements.every(isNumericFactRequirement)
    && typeof requirements.project_count === 'number' && typeof requirements.procedure_count === 'number'
    && typeof requirements.building_use_count === 'number' && typeof requirements.state_fact_count === 'number' && typeof requirements.numeric_fact_count === 'number'
    && typeof requirements.requires_additional_input === 'boolean'

  const official = landArea.official
  const spatial = landArea.spatial
  const difference = landArea.difference
  const landAreaValid = isRecord(official) && isRecord(spatial) && isRecord(difference) && isNullableNumber(official.value) && isNullableNumber(spatial.value) && isNullableNumber(difference.value) && isNullableNumber(difference.ratio_percent)

  const bcr = regulation.building_coverage_ratio
  const far = regulation.floor_area_ratio
  const regulationValid = isRecord(bcr) && isRecord(far) && isNullableNumber(bcr.value) && isNullableNumber(far.value)

  const ruleEvaluationValid = typeof ruleEvaluation.total === 'number' && typeof ruleEvaluation.applicable === 'number' && typeof ruleEvaluation.not_applicable === 'number' && typeof ruleEvaluation.conditional === 'number' && typeof ruleEvaluation.unknown === 'number'
  const externalDependenciesValid = typeof externalDependencies.count === 'number' && Array.isArray(externalDependencyItems)
  const siteFactsValid = typeof factLand.land_category === 'string'
    && isNullableNumber(factLand.land_area)
    && typeof factLand.zoning === 'string'
    && typeof factBuildings.count === 'number'
    && Array.isArray(factBuildingItems)
    && factBuildingItems.every(isSiteAnalysisBuildingFact)
    && isNullableString(factSources.land)
    && (factSources.land_status === null || factSources.land_status === 'AVAILABLE' || factSources.land_status === 'NO_DATA' || factSources.land_status === 'PROVIDER_FAILED')
    && typeof factSources.land_retryable === 'boolean'
    && isNullableString(factSources.land_reference_year)
    && isNullableString(factSources.land_last_updated_at)
    && isNullableString(factSources.buildings)

  if (!siteValid || !requirementsValid || !landAreaValid || !regulationValid || !ruleEvaluationValid || !externalDependenciesValid || !siteFactsValid) return false

  const expectedRuleTotal = Number(ruleEvaluation.applicable) + Number(ruleEvaluation.not_applicable) + Number(ruleEvaluation.conditional) + Number(ruleEvaluation.unknown)
  if (Number(ruleEvaluation.total) !== expectedRuleTotal) return false
  if (Number(requirements.project_count) !== projectRequirements.length) return false
  if (Number(requirements.procedure_count) !== procedureRequirements.length) return false
  if (Number(requirements.building_use_count) !== buildingUseRequirements.length) return false
  if (Number(requirements.state_fact_count) !== stateFactRequirements.length) return false
  if (Number(requirements.numeric_fact_count) !== numericFactRequirements.length) return false
  if (Number(externalDependencies.count) !== externalDependencyItems.length) return false
  if (Number(factBuildings.count) !== factBuildingItems.length) return false

  return true
}
