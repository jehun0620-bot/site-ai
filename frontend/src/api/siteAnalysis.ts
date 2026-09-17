import type { ParcelCandidate } from '../types/parcel'
import type { SiteAnalysisResponse } from '../types/siteAnalysis'

export class SiteAnalysisApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'SiteAnalysisApiError'
  }
}

export async function analyzeSelectedParcelCandidate(
  candidate: ParcelCandidate,
  signal?: AbortSignal,
): Promise<SiteAnalysisResponse> {
  const response = await fetch('/v1/site-analysis/selected-candidate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      candidate_pnu: candidate.candidate_pnu,
      x: candidate.x,
      y: candidate.y,
      project_profile: {},
      procedure_profile: {},
      include_debug: false,
    }),
    signal,
  })

  if (!response.ok) throw new SiteAnalysisApiError(`SITE 분석 요청에 실패했습니다. (${response.status})`)

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

function isSiteAnalysisResponse(value: unknown): value is SiteAnalysisResponse {
  if (!isRecord(value)) return false
  const body = value
  if (body.schema_version !== 'SITE_ANALYSIS_API_V1') return false
  if (!isRecord(body.site) || !isRecord(body.requirements)) return false
  if (!isRecord(body.land_area) || !isRecord(body.regulation)) return false
  if (!isRecord(body.rule_evaluation) || !isRecord(body.external_dependencies)) return false
  if (!('spatial' in body)) return false

  const site = body.site
  const requirements = body.requirements
  const landArea = body.land_area
  const regulation = body.regulation
  const ruleEvaluation = body.rule_evaluation
  const externalDependencies = body.external_dependencies
  const nullableString = (item: unknown) => item === null || typeof item === 'string'

  const siteValid = nullableString(site.site_id) && nullableString(site.address) && nullableString(site.road_address) && nullableString(site.pnu) && nullableString(site.sigungu_code) && nullableString(site.bjdong_code) && nullableString(site.main_no) && nullableString(site.sub_no)
  const requirementsValid = Array.isArray(requirements.project) && Array.isArray(requirements.procedure) && typeof requirements.project_count === 'number' && typeof requirements.procedure_count === 'number' && typeof requirements.requires_additional_input === 'boolean'

  const official = landArea.official
  const spatial = landArea.spatial
  const difference = landArea.difference
  const landAreaValid = isRecord(official) && isRecord(spatial) && isRecord(difference) && isNullableNumber(official.value) && isNullableNumber(spatial.value) && isNullableNumber(difference.value) && isNullableNumber(difference.ratio_percent)

  const bcr = regulation.building_coverage_ratio
  const far = regulation.floor_area_ratio
  const regulationValid = isRecord(bcr) && isRecord(far) && isNullableNumber(bcr.value) && isNullableNumber(far.value)

  const ruleEvaluationValid = typeof ruleEvaluation.total === 'number' && typeof ruleEvaluation.applicable === 'number' && typeof ruleEvaluation.not_applicable === 'number' && typeof ruleEvaluation.conditional === 'number' && typeof ruleEvaluation.unknown === 'number'
  const externalDependenciesValid = typeof externalDependencies.count === 'number' && Array.isArray(externalDependencies.items)

  if (!siteValid || !requirementsValid || !landAreaValid || !regulationValid || !ruleEvaluationValid || !externalDependenciesValid) return false

  const expectedRuleTotal = Number(ruleEvaluation.applicable) + Number(ruleEvaluation.not_applicable) + Number(ruleEvaluation.conditional) + Number(ruleEvaluation.unknown)
  if (Number(ruleEvaluation.total) !== expectedRuleTotal) return false
  if (Number(requirements.project_count) !== requirements.project.length) return false
  if (Number(requirements.procedure_count) !== requirements.procedure.length) return false
  if (Number(externalDependencies.count) !== externalDependencies.items.length) return false

  return true
}
