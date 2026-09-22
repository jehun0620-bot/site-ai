import type { SiteAnalysisLandArea } from '../types/siteAnalysis'

function displayNumber(value: number | null, suffix = ''): string {
  if (value === null) return '정보 없음'
  return `${value.toLocaleString('ko-KR')}${suffix}`
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '정보 없음'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
  return '상세 확인 필요'
}

export default function LandAreaSection({ landArea }: { landArea: SiteAnalysisLandArea }) {
  return (
    <section className="analysis-detail-section" id="analysis-area">
      <h2>대지면적</h2>
      <div className="analysis-metric-grid analysis-area-metric-grid">
        <article className="analysis-metric analysis-metric-primary"><span>공식 대지면적</span><strong>{displayNumber(landArea.official.value, '㎡')}</strong><small>공식/속성 면적 · 주 기준</small></article>
        <article className="analysis-metric analysis-metric-supporting"><span>공간 면적</span><strong>{displayNumber(landArea.spatial.value)}</strong><small>{landArea.spatial.value === null ? 'Backend 응답에 값이 없어 계산하지 않음' : displayValue(landArea.spatial.unit)}</small></article>
        <article className="analysis-metric analysis-metric-supporting"><span>면적 차이</span><strong>{displayNumber(landArea.difference.value, '㎡')}</strong><small>{landArea.difference.value === null ? '비교할 공간 면적이 없어 계산하지 않음' : `차이율 ${displayNumber(landArea.difference.ratio_percent, '%')}`}</small></article>
      </div>
    </section>
  )
}
