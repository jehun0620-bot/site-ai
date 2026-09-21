import type { ParcelCandidate } from '../types/parcel'
import type { SiteAnalysisInputProfile, SiteAnalysisInputState, SiteAnalysisResponse } from '../types/siteAnalysis'
import { ProductApiError, readApiError, type ProductErrorDetail } from './productError'

export class SiteAnalysisApiError extends ProductApiError {
  constructor(message: string, httpStatus = 0, detail: ProductErrorDetail | null = null) {
    super(message, httpStatus, detail)
    this.name = 'SiteAnalysisApiError'
  }
}

export interface SiteAnalysisInputProfiles {
  project_profile?: SiteAnalysisInputProfile
  procedure_profile?: SiteAnalysisInputProfile
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

function isNullableNumber(value: unknown): boolean {
  return value === null || typeof value === 'number'
}

function isSiteAnalysisInputState(value: unknown): value is SiteAnalysisInputState {
  return value === 'TRUE' || value === 'FALSE' || value === 'UNKNOWN' || value === 'UNSET'
}

function isSiteAnalysisRequirement(value: unknown): boolean {
  return isRecord(value) && typeof value.name === 'string' && typeof value.affected_clause_count === 'number' && isSiteAnalysisInputState(value.state)
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
    && isNullableNumber(value.land_area)
    && isNullableNumber(value.building_area)
    && isNullableNumber(value.total_floor_area)
    && isNullableNumber(value.building_coverage_ratio)
    && isNullableNumber(value.floor_area_ratio)
    && isNullableNumber(value.ground_floor_count)
    && isNullableNumber(value.underground_floor_count)
    && isNullableNumber(value.household_count)
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
  const externalDependencyItems = externalDependencies.items
  if (!isRecord(siteFacts.land) || !isRecord(siteFacts.buildings) || !isRecord(siteFacts.sources)) return false
  const factLand = siteFacts.land
  const factBuildings = siteFacts.buildings
  const factSources = siteFacts.sources
  const factBuildingItems = factBuildings.items

  const siteValid = nullableString(site.site_id) && nullableString(site.address) && nullableString(site.road_address) && nullableString(site.pnu) && nullableString(site.sigungu_code) && nullableString(site.bjdong_code) && nullableString(site.main_no) && nullableString(site.sub_no)
  const requirementsValid = Array.isArray(projectRequirements) && projectRequirements.every(isSiteAnalysisRequirement) && Array.isArray(procedureRequirements) && procedureRequirements.every(isSiteAnalysisRequirement) && typeof requirements.project_count === 'number' && typeof requirements.procedure_count === 'number' && typeof requirements.requires_additional_input === 'boolean'

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
    && isNullableString(factSources.land_reference_year)
    && isNullableString(factSources.land_last_updated_at)
    && isNullableString(factSources.buildings)

  if (!siteValid || !requirementsValid || !landAreaValid || !regulationValid || !ruleEvaluationValid || !externalDependenciesValid || !siteFactsValid) return false

  const expectedRuleTotal = Number(ruleEvaluation.applicable) + Number(ruleEvaluation.not_applicable) + Number(ruleEvaluation.conditional) + Number(ruleEvaluation.unknown)
  if (Number(ruleEvaluation.total) !== expectedRuleTotal) return false
  if (Number(requirements.project_count) !== projectRequirements.length) return false
  if (Number(requirements.procedure_count) !== procedureRequirements.length) return false
  if (Number(externalDependencies.count) !== externalDependencyItems.length) return false
  if (Number(factBuildings.count) !== factBuildingItems.length) return false

  return true
}
