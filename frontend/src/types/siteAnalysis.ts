export type SiteAnalysisState = 'IDLE' | 'ANALYZING' | 'ANALYSIS_READY' | 'ANALYSIS_FAILED'

export interface SiteAnalysisSite {
  site_id: string | null
  address: string | null
  road_address: string | null
  pnu: string | null
  sigungu_code: string | null
  bjdong_code: string | null
  main_no: string | null
  sub_no: string | null
  zone: unknown
  coordinate: unknown
  identity_status: unknown
}

export interface SiteAnalysisRequirements {
  project: unknown[]
  procedure: unknown[]
  project_count: number
  procedure_count: number
  requires_additional_input: boolean
}

export interface SiteAnalysisResponse {
  schema_version: 'SITE_ANALYSIS_API_V1'
  status: unknown
  site: SiteAnalysisSite
  land_area: unknown
  spatial: unknown
  regulation: unknown
  rule_evaluation: unknown
  requirements: SiteAnalysisRequirements
  external_dependencies: unknown
  service?: {
    building_count?: number | null
    building_total_count?: number | null
    building_api_status?: string | null
  }
}
