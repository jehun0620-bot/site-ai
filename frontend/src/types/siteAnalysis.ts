export type SiteAnalysisState = 'IDLE' | 'ANALYZING' | 'ANALYSIS_READY' | 'ANALYSIS_FAILED'
export type SiteAnalysisInputState = 'TRUE' | 'FALSE' | 'UNKNOWN' | 'UNSET'
export type SiteAnalysisInputProfile = Record<string, SiteAnalysisInputState>

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

export interface SiteAnalysisAreaValue {
  value: number | null
  unit: string | null
  source?: string | null
  role?: string | null
  crs?: string | null
  crs_status?: unknown
}

export interface SiteAnalysisLandArea {
  official: SiteAnalysisAreaValue
  spatial: SiteAnalysisAreaValue
  difference: {
    value: number | null
    ratio_percent: number | null
  }
  resolution: string | null
  primary: string | null
}

export interface SiteAnalysisNumericRegulation {
  value: number | null
  unit: string | null
  status: string | null
}

export interface SiteAnalysisRegulation {
  building_coverage_ratio: SiteAnalysisNumericRegulation
  floor_area_ratio: SiteAnalysisNumericRegulation
  numeric_resolution: unknown
  direct_relaxation_count: number
  numeric_active_before_guard: number
  numeric_excluded_count: number
  numeric_retained_count: number
}

export interface SiteAnalysisRuleEvaluation {
  total: number
  applicable: number
  not_applicable: number
  conditional: number
  unknown: number
}

export type SiteAnalysisRuleApplicability = 'APPLICABLE' | 'NOT_APPLICABLE' | 'CONDITIONAL' | 'UNKNOWN'

export interface SiteAnalysisRuleDetail {
  clause_index: number | string | null
  law_name: string | null
  rule_title: string | null
  paragraph: string | null
  item: string | null
  subitem: string | null
  category: string | null
  applicability: SiteAnalysisRuleApplicability
  reason: string | null
  text: string | null
  effect_targets: unknown[]
  required_inputs: string[]
  unresolved_conditions: string[]
  blocking_conditions: string[]
  numeric_effect: unknown
}

export interface SiteAnalysisRuleDetails {
  count: number
  items: SiteAnalysisRuleDetail[]
}

export interface SiteAnalysisRequirement {
  name: string
  affected_clause_count: number
  state: SiteAnalysisInputState
}

export interface SiteAnalysisRequirements {
  project: SiteAnalysisRequirement[]
  procedure: SiteAnalysisRequirement[]
  project_count: number
  procedure_count: number
  requires_additional_input: boolean
}

export interface SiteAnalysisExternalDependency {
  category?: unknown
  condition?: unknown
  status?: unknown
  confidence?: unknown
  automation_state?: unknown
  blocking_analysis?: boolean
}

export interface SiteAnalysisExternalDependencies {
  count: number
  items: SiteAnalysisExternalDependency[]
}

export interface SiteAnalysisBuildingFact {
  management_id: string | number | null
  dong_name: string
  building_name: string
  main_use: string
  land_area: number | null
  building_area: number | null
  total_floor_area: number | null
  building_coverage_ratio: number | null
  floor_area_ratio: number | null
  ground_floor_count: number | null
  underground_floor_count: number | null
  household_count: number | null
  approval_date: string
}

export interface SiteAnalysisSiteFacts {
  land: {
    land_category: string
    land_area: number | null
    zoning: string
  }
  buildings: {
    count: number
    items: SiteAnalysisBuildingFact[]
  }
  sources: {
    land: string | null
    buildings: string | null
  }
}

export interface SiteAnalysisResponse {
  schema_version: 'SITE_ANALYSIS_API_V1'
  status: unknown
  site: SiteAnalysisSite
  land_area: SiteAnalysisLandArea
  site_facts: SiteAnalysisSiteFacts
  spatial: unknown
  regulation: SiteAnalysisRegulation
  rule_evaluation: SiteAnalysisRuleEvaluation
  rule_details: SiteAnalysisRuleDetails
  requirements: SiteAnalysisRequirements
  external_dependencies: SiteAnalysisExternalDependencies
  service?: {
    building_count?: number | null
    building_total_count?: number | null
    building_api_status?: string | null
  }
}
