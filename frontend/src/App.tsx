import { FormEvent, useState } from 'react'
import { confirmParcelCandidate, searchParcelCandidates } from './api/parcelCandidates'
import { analyzeSelectedParcelCandidate } from './api/siteAnalysis'
import KakaoMap from './map/KakaoMap'
import type {
  CandidateSearchState,
  ParcelCandidate,
  ParcelConfirmationResponse,
  ParcelVerificationState,
} from './types/parcel'
import type { SiteAnalysisResponse, SiteAnalysisState } from './types/siteAnalysis'

const INITIAL_GUIDE = '현재 검증된 범위에서는 지번주소로 검색하는 것을 권장합니다.'

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '정보 없음'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
  return '상세 확인 필요'
}

function displayNumber(value: number | null, suffix = ''): string {
  if (value === null) return '정보 없음'
  return `${value.toLocaleString('ko-KR')}${suffix}`
}

function displayRequirement(value: unknown): string {
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  if (value && typeof value === 'object') {
    const item = value as Record<string, unknown>
    for (const key of ['label', 'name', 'field', 'key', 'condition']) {
      const candidate = item[key]
      if (typeof candidate === 'string' && candidate.trim()) return candidate
    }
  }
  return '추가 입력 항목'
}

export default function App() {
  const [query, setQuery] = useState('')
  const [state, setState] = useState<CandidateSearchState>('IDLE')
  const [candidates, setCandidates] = useState<ParcelCandidate[]>([])
  const [message, setMessage] = useState(INITIAL_GUIDE)
  const [selectedCandidate, setSelectedCandidate] = useState<ParcelCandidate | null>(null)
  const [verificationState, setVerificationState] = useState<ParcelVerificationState>('IDLE')
  const [confirmation, setConfirmation] = useState<ParcelConfirmationResponse | null>(null)
  const [verificationMessage, setVerificationMessage] = useState('')
  const [analysisState, setAnalysisState] = useState<SiteAnalysisState>('IDLE')
  const [analysis, setAnalysis] = useState<SiteAnalysisResponse | null>(null)
  const [analysisMessage, setAnalysisMessage] = useState('')

  function clearAnalysis() {
    setAnalysisState('IDLE')
    setAnalysis(null)
    setAnalysisMessage('')
  }

  function clearParcelVerification() {
    setSelectedCandidate(null)
    setVerificationState('IDLE')
    setConfirmation(null)
    setVerificationMessage('')
    clearAnalysis()
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedQuery = query.trim()
    clearParcelVerification()

    if (!normalizedQuery) {
      setCandidates([])
      setState('SEARCH_ERROR')
      setMessage('검색할 지번주소를 입력해 주세요.')
      return
    }

    setState('SEARCHING')
    setCandidates([])
    setMessage('필지 후보를 찾고 있습니다.')

    try {
      const result = await searchParcelCandidates(normalizedQuery)
      setCandidates(result.candidates)
      if (result.candidates.length === 0) {
        setState('SEARCH_EMPTY')
        setMessage('일치하는 필지 후보를 찾지 못했습니다. 지번주소를 확인해 주세요.')
        return
      }

      setState('SEARCH_RESULTS')
      setMessage(`${result.count}개의 필지 후보를 찾았습니다.`)
    } catch (error) {
      setState('SEARCH_ERROR')
      setMessage(error instanceof Error ? error.message : '필지 후보 검색 중 오류가 발생했습니다.')
    }
  }

  async function handleCandidateSelection(candidate: ParcelCandidate) {
    clearAnalysis()
    setSelectedCandidate(candidate)
    setConfirmation(null)
    setVerificationState('VERIFYING_PARCEL')
    setVerificationMessage('선택한 필지의 실제 경계를 Backend에서 확인하고 있습니다.')

    try {
      const result = await confirmParcelCandidate(candidate)
      if (result.parcel.pnu !== candidate.candidate_pnu) {
        throw new Error('검증된 필지와 선택한 필지의 PNU가 일치하지 않습니다.')
      }

      setConfirmation(result)
      setVerificationState('PARCEL_VERIFIED')
      setVerificationMessage('Backend가 선택한 필지와 실제 필지 경계의 일치를 확인했습니다.')
    } catch (error) {
      setConfirmation(null)
      setVerificationState('PARCEL_VERIFICATION_FAILED')
      setVerificationMessage(error instanceof Error ? error.message : '선택한 필지를 확인하지 못했습니다.')
    }
  }

  async function handleAnalysis() {
    if (!selectedCandidate || !confirmation || verificationState !== 'PARCEL_VERIFIED') return

    clearAnalysis()
    setAnalysisState('ANALYZING')
    setAnalysisMessage('Backend가 필지를 다시 검증한 뒤 SITE 분석을 실행하고 있습니다.')

    try {
      const result = await analyzeSelectedParcelCandidate(selectedCandidate)
      if (result.site.pnu !== confirmation.parcel.pnu) {
        throw new Error('분석 결과의 PNU가 확인된 필지와 일치하지 않습니다.')
      }

      setAnalysis(result)
      setAnalysisState('ANALYSIS_READY')
      setAnalysisMessage('실제 SITE 분석 결과를 받았습니다.')
    } catch (error) {
      setAnalysis(null)
      setAnalysisState('ANALYSIS_FAILED')
      setAnalysisMessage(error instanceof Error ? error.message : 'SITE 분석을 완료하지 못했습니다.')
    }
  }

  return (
    <main className="app-shell">
      <section className="search-panel" aria-labelledby="page-title">
        <div className="brand">SITE AI</div>
        <h1 id="page-title">분석할 대지를 찾아보세요</h1>
        <p className="lead">주소를 입력하면 분석 가능한 필지 후보를 찾습니다.</p>

        <form className="search-form" onSubmit={handleSubmit}>
          <label htmlFor="parcel-address">지번주소</label>
          <div className="search-row">
            <input id="parcel-address" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="예: 서울특별시 강남구 개포동 12" autoComplete="street-address" />
            <button type="submit" disabled={state === 'SEARCHING'}>{state === 'SEARCHING' ? '검색 중' : '필지 찾기'}</button>
          </div>
        </form>

        <p className={`status status-${state.toLowerCase()}`} role="status">{message}</p>

        {state === 'SEARCH_RESULTS' && (
          <div className="candidate-list" aria-label="필지 후보 목록">
            {candidates.map((candidate) => {
              const isSelected = selectedCandidate?.candidate_pnu === candidate.candidate_pnu
              const isVerifying = isSelected && verificationState === 'VERIFYING_PARCEL'
              return (
                <button className={`candidate-card${isSelected ? ' candidate-card-selected' : ''}`} key={`${candidate.candidate_pnu}-${candidate.x}-${candidate.y}`} type="button" onClick={() => handleCandidateSelection(candidate)} disabled={verificationState === 'VERIFYING_PARCEL' || analysisState === 'ANALYZING'} aria-pressed={isSelected}>
                  <span className="candidate-heading"><strong>{candidate.parcel_address || '지번주소 정보 없음'}</strong>{candidate.building_name && <span>{candidate.building_name}</span>}</span>
                  {candidate.road_address && <span className="candidate-road-address">{candidate.road_address}</span>}
                  <small>{isVerifying ? '필지 확인 중…' : `후보 위치 · ${candidate.crs}`}</small>
                </button>
              )
            })}
          </div>
        )}

        {selectedCandidate && verificationState !== 'IDLE' && (
          <section className={`verification-panel verification-${verificationState.toLowerCase()}`} aria-live="polite">
            <div className="verification-title-row"><strong>{verificationState === 'PARCEL_VERIFIED' ? '필지 확인 완료' : verificationState === 'PARCEL_VERIFICATION_FAILED' ? '필지 확인 실패' : '필지 확인 중'}</strong>{verificationState === 'PARCEL_VERIFIED' && <span className="verified-badge">VERIFIED</span>}</div>
            <p>{verificationMessage}</p>
            {confirmation && (
              <>
                <dl className="verified-details">
                  <div><dt>지번주소</dt><dd>{selectedCandidate.parcel_address || '정보 없음'}</dd></div>
                  <div><dt>PNU</dt><dd>{confirmation.parcel.pnu}</dd></div>
                  <div><dt>경계 형식</dt><dd>{confirmation.geometry.type}</dd></div>
                  <div><dt>좌표계</dt><dd>{confirmation.parcel.crs}</dd></div>
                </dl>
                <button className="analysis-button" type="button" onClick={handleAnalysis} disabled={analysisState === 'ANALYZING'}>{analysisState === 'ANALYZING' ? '분석 중…' : '이 필지 분석'}</button>
              </>
            )}
          </section>
        )}

        {analysisState !== 'IDLE' && (
          <section className={`analysis-panel analysis-${analysisState.toLowerCase()}`} aria-live="polite">
            <div className="analysis-title-row"><strong>{analysisState === 'ANALYSIS_READY' ? 'SITE 분석 결과' : analysisState === 'ANALYSIS_FAILED' ? 'SITE 분석 실패' : 'SITE 분석 중'}</strong>{analysisState === 'ANALYSIS_READY' && <span className="analysis-ready-badge">READY</span>}</div>
            <p>{analysisMessage}</p>

            {analysis && (
              <div className="analysis-details">
                <section className="analysis-detail-section">
                  <h2>필지 기본정보</h2>
                  <dl className="analysis-summary">
                    <div><dt>지번주소</dt><dd>{displayValue(analysis.site.address)}</dd></div>
                    <div><dt>도로명주소</dt><dd>{displayValue(analysis.site.road_address)}</dd></div>
                    <div><dt>PNU</dt><dd>{displayValue(analysis.site.pnu)}</dd></div>
                    <div><dt>용도지역</dt><dd>{displayValue(analysis.site.zone)}</dd></div>
                    <div><dt>분석 상태</dt><dd>{displayValue(analysis.status)}</dd></div>
                    <div><dt>추가 입력</dt><dd>{analysis.requirements.requires_additional_input ? '필요' : '현재 응답 기준 없음'}</dd></div>
                  </dl>
                </section>

                <section className="analysis-detail-section">
                  <h2>대지면적</h2>
                  <div className="analysis-metric-grid">
                    <article className="analysis-metric"><span>공식 대지면적</span><strong>{displayNumber(analysis.land_area.official.value, '㎡')}</strong><small>공식/속성 면적 · 주 기준</small></article>
                    <article className="analysis-metric"><span>공간 면적</span><strong>{displayNumber(analysis.land_area.spatial.value)}</strong><small>{displayValue(analysis.land_area.spatial.unit)}</small></article>
                    <article className="analysis-metric"><span>면적 차이</span><strong>{displayNumber(analysis.land_area.difference.value, '㎡')}</strong><small>차이율 {displayNumber(analysis.land_area.difference.ratio_percent, '%')}</small></article>
                  </div>
                </section>

                <section className="analysis-detail-section">
                  <h2>건축 규모 기준</h2>
                  <div className="analysis-metric-grid analysis-metric-grid-two">
                    <article className="analysis-metric"><span>건폐율</span><strong>{displayNumber(analysis.regulation.building_coverage_ratio.value, '%')}</strong><small>{displayValue(analysis.regulation.building_coverage_ratio.status)}</small></article>
                    <article className="analysis-metric"><span>용적률</span><strong>{displayNumber(analysis.regulation.floor_area_ratio.value, '%')}</strong><small>{displayValue(analysis.regulation.floor_area_ratio.status)}</small></article>
                  </div>
                </section>

                <section className="analysis-detail-section">
                  <h2>법규 평가 집계</h2>
                  <p className="analysis-note">Backend Rule Engine의 집계 결과입니다. Frontend에서 적용 여부를 다시 판단하지 않습니다.</p>
                  <div className="rule-summary-grid">
                    <article><span>전체</span><strong>{analysis.rule_evaluation.total}</strong></article>
                    <article><span>적용</span><strong>{analysis.rule_evaluation.applicable}</strong></article>
                    <article><span>비적용</span><strong>{analysis.rule_evaluation.not_applicable}</strong></article>
                    <article><span>조건부</span><strong>{analysis.rule_evaluation.conditional}</strong></article>
                    <article><span>확인 필요</span><strong>{analysis.rule_evaluation.unknown}</strong></article>
                  </div>
                </section>

                <section className="analysis-detail-section">
                  <h2>추가 입력 필요사항</h2>
                  {!analysis.requirements.requires_additional_input ? (
                    <p className="analysis-empty">현재 응답 기준 추가 입력 항목이 없습니다.</p>
                  ) : (
                    <div className="requirement-columns">
                      <div><h3>사업 정보 · {analysis.requirements.project_count}</h3><ul>{analysis.requirements.project.map((item, index) => <li key={`project-${index}`}>{displayRequirement(item)}</li>)}</ul></div>
                      <div><h3>절차 정보 · {analysis.requirements.procedure_count}</h3><ul>{analysis.requirements.procedure.map((item, index) => <li key={`procedure-${index}`}>{displayRequirement(item)}</li>)}</ul></div>
                    </div>
                  )}
                </section>

                <section className="analysis-detail-section">
                  <h2>외부 확인 정보</h2>
                  {analysis.external_dependencies.count === 0 ? (
                    <p className="analysis-empty">현재 응답 기준 별도 외부 확인 항목이 없습니다.</p>
                  ) : (
                    <ul className="dependency-list">
                      {analysis.external_dependencies.items.map((item, index) => (
                        <li key={`dependency-${index}`}><strong>{displayValue(item.category)}</strong><span>{displayValue(item.condition)}</span><small>상태 {displayValue(item.status)} · 분석 차단 {item.blocking_analysis ? '예' : '아니오'}</small></li>
                      ))}
                    </ul>
                  )}
                </section>
              </div>
            )}
          </section>
        )}
      </section>

      <KakaoMap candidates={candidates} selectedCandidate={selectedCandidate} confirmation={confirmation} />
    </main>
  )
}
