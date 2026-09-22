import type { SiteAnalysisExternalDependencies } from '../types/siteAnalysis'

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '정보 없음'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
  return '상세 확인 필요'
}

function displayExternalCategory(value: unknown): string {
  if (value === 'SITE_HISTORY') return '과거 이력 확인'
  return displayValue(value)
}

export default function ExternalDependenciesSection({ dependencies }: { dependencies: SiteAnalysisExternalDependencies }) {
  return (
    <section className="analysis-detail-section" id="analysis-external">
      <h2>외부 확인 정보</h2>
      {dependencies.count === 0 ? <p className="analysis-empty">현재 응답 기준 별도 외부 확인 항목이 없습니다.</p> : (
        <ul className="dependency-list">
          {dependencies.items.map((item, index) => (
            <li key={`dependency-${index}`}>
              <div className="dependency-heading"><strong>{displayExternalCategory(item.category)}</strong>{item.category === 'SITE_HISTORY' && <small>원본 분류 SITE_HISTORY</small>}</div>
              <dl className="dependency-facts">
                <div><dt>확인 조건</dt><dd>{displayValue(item.condition)}</dd></div>
                <div><dt>현재 상태</dt><dd>{displayValue(item.status)}</dd></div>
                <div><dt>분석 진행</dt><dd>{item.blocking_analysis === true ? '차단' : item.blocking_analysis === false ? '계속 가능' : '정보 없음'}</dd></div>
              </dl>
              <p className="dependency-blocking-note">{item.blocking_analysis === true ? '이 외부 확인 항목은 현재 분석 진행을 차단합니다.' : item.blocking_analysis === false ? '외부 확인이 남아 있어도 현재 분석 자체를 차단하지 않는 항목입니다.' : '분석 차단 여부가 Backend 응답에 없습니다.'}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
