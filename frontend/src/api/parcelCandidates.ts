import type { ParcelCandidateSearchResponse } from '../types/parcel'

export class ParcelCandidateApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ParcelCandidateApiError'
  }
}

export async function searchParcelCandidates(
  query: string,
  signal?: AbortSignal,
): Promise<ParcelCandidateSearchResponse> {
  const response = await fetch('/v1/parcel-candidates/address', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query }),
    signal,
  })

  if (!response.ok) {
    throw new ParcelCandidateApiError(`필지 후보 검색 요청에 실패했습니다. (${response.status})`)
  }

  const body: unknown = await response.json()
  if (!isParcelCandidateSearchResponse(body)) {
    throw new ParcelCandidateApiError('필지 후보 검색 응답 형식이 올바르지 않습니다.')
  }

  return body
}

function isParcelCandidateSearchResponse(value: unknown): value is ParcelCandidateSearchResponse {
  if (!value || typeof value !== 'object') return false

  const body = value as Record<string, unknown>
  if (body.schema_version !== 'PARCEL_CANDIDATE_SEARCH_V1' || body.status !== 'READY') return false
  if (typeof body.query !== 'string' || typeof body.count !== 'number' || !Array.isArray(body.candidates)) return false

  return body.candidates.every((candidate) => {
    if (!candidate || typeof candidate !== 'object') return false
    const item = candidate as Record<string, unknown>
    return (
      typeof item.candidate_pnu === 'string' &&
      typeof item.parcel_address === 'string' &&
      typeof item.road_address === 'string' &&
      typeof item.building_name === 'string' &&
      typeof item.x === 'number' &&
      typeof item.y === 'number' &&
      typeof item.crs === 'string'
    )
  })
}
