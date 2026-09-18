import type {
  ParcelCandidate,
  ParcelCandidateSearchResponse,
  ParcelConfirmationResponse,
} from '../types/parcel'

export class ParcelCandidateApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ParcelCandidateApiError'
  }
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json()
    if (!body || typeof body !== 'object') return null
    const detail = (body as Record<string, unknown>).detail
    return typeof detail === 'string' && detail.trim() ? detail.trim() : null
  } catch {
    return null
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
    const detail = await readErrorDetail(response)
    throw new ParcelCandidateApiError(detail ? `필지 후보 검색에 실패했습니다. ${detail} (${response.status})` : `필지 후보 검색에 실패했습니다. (${response.status})`)
  }

  const body: unknown = await response.json()
  if (!isParcelCandidateSearchResponse(body)) {
    throw new ParcelCandidateApiError('필지 후보 검색 응답 형식이 올바르지 않습니다.')
  }

  return body
}

export async function confirmParcelCandidate(
  candidate: ParcelCandidate,
  signal?: AbortSignal,
): Promise<ParcelConfirmationResponse> {
  const response = await fetch('/v1/parcel-candidates/confirm', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      candidate_pnu: candidate.candidate_pnu,
      x: candidate.x,
      y: candidate.y,
    }),
    signal,
  })

  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new ParcelCandidateApiError(detail ? `선택한 필지를 확인하지 못했습니다. ${detail} (${response.status})` : `선택한 필지를 확인하지 못했습니다. (${response.status})`)
  }

  const body: unknown = await response.json()
  if (!isParcelConfirmationResponse(body)) {
    throw new ParcelCandidateApiError('필지 확인 응답 형식이 올바르지 않습니다.')
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

function isParcelConfirmationResponse(value: unknown): value is ParcelConfirmationResponse {
  if (!value || typeof value !== 'object') return false

  const body = value as Record<string, unknown>
  if (body.schema_version !== 'PARCEL_CONFIRMATION_V1' || body.status !== 'READY') return false
  if (!body.parcel || typeof body.parcel !== 'object') return false
  if (!body.verification || typeof body.verification !== 'object') return false
  if (!body.geometry || typeof body.geometry !== 'object') return false

  const parcel = body.parcel as Record<string, unknown>
  const verification = body.verification as Record<string, unknown>
  const geometry = body.geometry as Record<string, unknown>

  const parcelValid =
    typeof parcel.pnu === 'string' &&
    typeof parcel.sigungu_cd === 'string' &&
    typeof parcel.bjdong_cd === 'string' &&
    typeof parcel.plat_gb_cd === 'string' &&
    typeof parcel.bun === 'string' &&
    typeof parcel.ji === 'string' &&
    typeof parcel.x === 'number' &&
    typeof parcel.y === 'number' &&
    typeof parcel.crs === 'string'

  const verificationValid =
    verification.status === 'VERIFIED' &&
    verification.resolution === 'SELECTED_PARCEL_CANDIDATE_VERIFIED'

  const geometryValid =
    (geometry.type === 'Polygon' || geometry.type === 'MultiPolygon') &&
    Array.isArray(geometry.coordinates)

  return parcelValid && verificationValid && geometryValid
}
