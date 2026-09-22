import type { SiteAnalysisRegulation } from '../types/siteAnalysis'

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '정보 없음'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
  return '상세 확인 필요'
}

function displayNumber(value: number | null, suffix = ''): string {
  if (value === null) return '정보 없음'
  return `${value.toLocaleString('ko-KR')}${suffix}`
}

function displayRegulationStatus(value: unknown): string {
  if (value === 'CONFIRMED') return '확인된 기준'
  if (value === 'PENDING') return '추가 확인 필요'
  return displayValue(value)
}

export default function BuildingScaleSection({ regulation }: { regulation: SiteAnalysisRegulation }) {
  return (
    <section className="analysis-detail-section" id="analysis-scale">
      <h2>건축 규모 기준</h2>
      <div className="analysis-metric-grid analysis-metric-grid-two">
        <article className="analysis-metric"><span>건폐율 기준</span><strong>{displayNumber(regulation.building_coverage_ratio.value, '%')}</strong><small>{displayRegulationStatus(regulation.building_coverage_ratio.status)}</small></article>
        <article className="analysis-metric"><span>용적률 기준</span><strong>{displayNumber(regulation.floor_area_ratio.value, '%')}</strong><small>{displayRegulationStatus(regulation.floor_area_ratio.status)}</small></article>
      </div>
      <p className="regulation-basis-note">Backend에서 확인된 규제 기준이며 현재 건축물의 실제 건폐율·용적률을 뜻하지 않습니다.</p>
    </section>
  )
}
