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
    headers: {
      'Content-Type': 'application/json',
    },
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

  if (!response.ok) {
    throw new SiteAnalysisApiError(`SITE 분석 요청에 실패했습니다. (${response.status})`)
  }

  const body: unknown = await response.json()
  if (!isSiteAnalysisResponse(body)) {
    throw new SiteAnalysisApiError('SITE 분석 응답 형식이 올바르지 않습니다.')
  }

  return body
}

function isSiteAnalysisResponse(value: unknown): value is SiteAnalysisResponse {
  if (!value || typeof value !== 'object') return false

  const body = value as Record<string, unknown>
  if (body.schema_version !== 'SITE_ANALYSIS_API_V1') return false
  if (!body.site || typeof body.site !== 'object') return false
  if (!body.requirements || typeof body.requirements !== 'object') return false
  if (!('land_area' in body) || !('spatial' in body) || !('regulation' in body)) return false
  if (!('rule_evaluation' in body) || !('external_dependencies' in body)) return false

  const site = body.site as Record<string, unknown>
  const requirements = body.requirements as Record<string, unknown>

  const nullableString = (item: unknown) => item === null || typeof item === 'string'
  const siteValid =
    nullableString(site.site_id) &&
    nullableString(site.address) &&
    nullableString(site.road_address) &&
    nullableString(site.pnu) &&
    nullableString(site.sigungu_code) &&
    nullableString(site.bjdong_code) &&
    nullableString(site.main_no) &&
    nullableString(site.sub_no)

  const requirementsValid =
    Array.isArray(requirements.project) &&
    Array.isArray(requirements.procedure) &&
    typeof requirements.project_count === 'number' &&
    typeof requirements.procedure_count === 'number' &&
    typeof requirements.requires_additional_input === 'boolean'

  return siteValid && requirementsValid
}
