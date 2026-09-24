import type { SiteAnalysisResponse } from '../types/siteAnalysis'

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '정보 없음'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
  return '상세 확인 필요'
}

function displayNumber(value: number | null, suffix = ''): string {
  if (value === null) return '정보 없음'
  return `${value.toLocaleString('ko-KR')}${suffix}`
}

function displayAnalysisStatus(value: unknown): string {
  return value === 'READY' ? '분석 완료' : displayValue(value)
}

function displayLandStatus(status: SiteAnalysisResponse['site_facts']['sources']['land_status'], retryable: boolean): string {
  if (status === 'AVAILABLE') return '정상 조회'
  if (status === 'NO_DATA') return '조회 결과 없음'
  if (status === 'PROVIDER_FAILED') return retryable ? '외부 데이터 조회 실패 · 다시 시도 가능' : '외부 데이터 조회 실패'
  return '정보 없음'
}

interface SiteFactsSectionProps {
  analysis: SiteAnalysisResponse
}

export default function SiteFactsSection({ analysis }: SiteFactsSectionProps) {
  return (
    <section className="analysis-detail-section site-facts-section" id="analysis-basic">
      <h2>대상지 현황</h2>
      <div className="site-facts-grid">
        <div>
          <h3>토지 현황</h3>
          <dl className="analysis-summary">
            <div><dt>지번주소</dt><dd>{displayValue(analysis.site.address)}</dd></div>
            <div><dt>도로명주소</dt><dd>{displayValue(analysis.site.road_address)}</dd></div>
            <div><dt>PNU</dt><dd>{displayValue(analysis.site.pnu)}</dd></div>
            <div><dt>지목</dt><dd>{displayValue(analysis.site_facts.land.land_category)}</dd></div>
            <div><dt>대지면적</dt><dd>{displayNumber(analysis.site_facts.land.land_area, '㎡')}</dd></div>
            <div><dt>용도지역</dt><dd>{displayValue(analysis.site_facts.land.zoning || analysis.site.zone)}</dd></div>
          </dl>
        </div>
        <div>
          <h3>기존 건축물</h3>
          <dl className="analysis-summary">
            <div><dt>건축물</dt><dd>{analysis.site_facts.buildings.count}건</dd></div>
            <div><dt>분석 상태</dt><dd>{displayAnalysisStatus(analysis.status)}</dd></div>
            <div><dt>추가 입력</dt><dd>{analysis.requirements.requires_additional_input ? '필요' : '현재 응답 기준 없음'}</dd></div>
          </dl>
          {analysis.site_facts.buildings.items.length > 0 ? (
            <details className="building-facts-disclosure">
              <summary>건축물 상세 {analysis.site_facts.buildings.items.length}건 보기</summary>
              <div className="building-facts-list">
                {analysis.site_facts.buildings.items.map((building, index) => (
                  <article key={`building-${building.management_id ?? index}`}>
                    <div className="building-fact-heading">
                      <strong>{building.dong_name || building.building_name || `건축물 ${index + 1}`}</strong>
                      {building.main_use && <span>{building.main_use}</span>}
                    </div>
                    <dl>
                      <div><dt>건물명</dt><dd>{displayValue(building.building_name)}</dd></div>
                      <div><dt>건축면적</dt><dd>{displayNumber(building.building_area, '㎡')}</dd></div>
                      <div><dt>연면적</dt><dd>{displayNumber(building.total_floor_area, '㎡')}</dd></div>
                      <div><dt>건폐율</dt><dd>{displayNumber(building.building_coverage_ratio, '%')}</dd></div>
                      <div><dt>용적률</dt><dd>{displayNumber(building.floor_area_ratio, '%')}</dd></div>
                      <div><dt>층수</dt><dd>지상 {displayNumber(building.ground_floor_count, '층')} · 지하 {displayNumber(building.underground_floor_count, '층')}</dd></div>
                      <div><dt>세대수</dt><dd>{displayNumber(building.household_count, '세대')}</dd></div>
                      <div><dt>사용승인일</dt><dd>{displayValue(building.approval_date)}</dd></div>
                    </dl>
                  </article>
                ))}
              </div>
            </details>
          ) : <p className="analysis-empty">현재 조회된 건축물대장 항목이 없습니다.</p>}
        </div>
      </div>
      <div className="analysis-data-status">
        <strong>공식 데이터 출처</strong>
        <dl className="analysis-summary">
          <div><dt>토지</dt><dd>{analysis.site_facts.sources.land === 'VWORLD_LAND_CHARACTERISTICS' ? 'VWorld 토지특성정보' : displayValue(analysis.site_facts.sources.land)}</dd></div>
          <div><dt>토지 조회 상태</dt><dd>{displayLandStatus(analysis.site_facts.sources.land_status, analysis.site_facts.sources.land_retryable)}</dd></div>
          <div><dt>토지 기준연도</dt><dd>{displayValue(analysis.site_facts.sources.land_reference_year)}</dd></div>
          <div><dt>토지 최종 갱신일</dt><dd>{displayValue(analysis.site_facts.sources.land_last_updated_at)}</dd></div>
          <div><dt>건축물</dt><dd>{analysis.site_facts.sources.buildings === 'BUILDING_HUB_TITLE' ? '건축HUB 표제부' : displayValue(analysis.site_facts.sources.buildings)}</dd></div>
          <div><dt>건축HUB 상태</dt><dd>{analysis.service?.building_api_status === '00' ? '정상 (00)' : displayValue(analysis.service?.building_api_status)}</dd></div>
        </dl>
      </div>
    </section>
  )
}
