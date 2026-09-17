export interface ParcelReferenceGeometry {
  type: 'Polygon' | 'MultiPolygon'
  coordinates: unknown[]
}

export interface ParcelCandidate {
  candidate_pnu: string
  parcel_address: string
  road_address: string
  building_name: string
  x: number
  y: number
  crs: string
  reference_geometry?: ParcelReferenceGeometry | null
}

export interface ParcelCandidateSearchResponse {
  schema_version: 'PARCEL_CANDIDATE_SEARCH_V1'
  status: 'READY'
  query: string
  count: number
  candidates: ParcelCandidate[]
}

export interface ParcelConfirmationParcel {
  pnu: string
  sigungu_cd: string
  bjdong_cd: string
  plat_gb_cd: string
  bun: string
  ji: string
  x: number
  y: number
  crs: string
}

export interface ParcelConfirmationGeometry {
  type: 'Polygon' | 'MultiPolygon'
  coordinates: unknown[]
}

export interface ParcelConfirmationResponse {
  schema_version: 'PARCEL_CONFIRMATION_V1'
  status: 'READY'
  parcel: ParcelConfirmationParcel
  verification: {
    status: 'VERIFIED'
    resolution: 'SELECTED_PARCEL_CANDIDATE_VERIFIED'
  }
  geometry: ParcelConfirmationGeometry
}

export type CandidateSearchState =
  | 'IDLE'
  | 'SEARCHING'
  | 'SEARCH_RESULTS'
  | 'SEARCH_EMPTY'
  | 'SEARCH_ERROR'

export type ParcelVerificationState =
  | 'IDLE'
  | 'VERIFYING_PARCEL'
  | 'PARCEL_VERIFIED'
  | 'PARCEL_VERIFICATION_FAILED'
