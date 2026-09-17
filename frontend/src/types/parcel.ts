export interface ParcelCandidate {
  candidate_pnu: string
  parcel_address: string
  road_address: string
  building_name: string
  x: number
  y: number
  crs: string
}

export interface ParcelCandidateSearchResponse {
  schema_version: 'PARCEL_CANDIDATE_SEARCH_V1'
  status: 'READY'
  query: string
  count: number
  candidates: ParcelCandidate[]
}

export type CandidateSearchState =
  | 'IDLE'
  | 'SEARCHING'
  | 'SEARCH_RESULTS'
  | 'SEARCH_EMPTY'
  | 'SEARCH_ERROR'
