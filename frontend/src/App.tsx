import { FormEvent, useEffect, useRef, useState } from 'react'
import { confirmParcelCandidate, searchParcelCandidates } from './api/parcelCandidates'
import { analyzeSelectedParcelCandidate } from './api/siteAnalysis'
import KakaoMap from './map/KakaoMap'
import type { CandidateSearchState, ParcelCandidate, ParcelConfirmationResponse, ParcelVerificationState } from './types/parcel'
import type { SiteAnalysisInputProfile, SiteAnalysisInputState, SiteAnalysisRequirement, SiteAnalysisResponse, SiteAnalysisState } from './types/siteAnalysis'

const INITIAL_GUIDE = '현재 검증된 범위에서는 지번주소로 검색하는 것을 권장합니다.'
const INPUT_OPTIONS: Array<{ state: Exclude<SiteAnalysisInputState, 'UNSET'>; label: string }> = [
  { state: 'TRUE', label: '해당함' },
  { state: 'FALSE', label: '해당하지 않음' },
  { state: 'UNKNOWN', label: '잘 모르겠음' },
]

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
function displayRegulationStatus(value: unknown): string {
  if (value === 'CONFIRMED') return '확인된 기준'
  if (value === 'PENDING') return '추가 확인 필요'
  return displayValue(value)
}
function displayExternalCategory(value: unknown): string {
  if (value === 'SITE_HISTORY') return '과거 이력 확인'
  return displayValue(value)
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
  const [previousAnalysis, setPreviousAnalysis] = useState<SiteAnalysisResponse | null>(null)
  const [analysisMessage, setAnalysisMessage] = useState('')
  const [projectProfile, setProjectProfile] = useState<SiteAnalysisInputProfile>({})
  const [procedureProfile, setProcedureProfile] = useState<SiteAnalysisInputProfile>({})
  const candidateListRef = useRef<HTMLDivElement | null>(null)
  const selectedCandidateCardRef = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    const list = candidateListRef.current
    const selectedCard = selectedCandidateCardRef.current
    if (!list || !selectedCard || !selectedCandidate) return
    const cardTop = selectedCard.offsetTop
    const cardBottom = cardTop + selectedCard.offsetHeight
    const visibleTop = list.scrollTop
    const visibleBottom = visibleTop + list.clientHeight
    if (cardTop < visibleTop) list.scrollTo({ top: cardTop, behavior: 'smooth' })
    else if (cardBottom > visibleBottom) list.scrollTo({ top: cardBottom - list.clientHeight, behavior: 'smooth' })
  }, [selectedCandidate, candidates])

  function clearInputProfiles() { setProjectProfile({}); setProcedureProfile({}) }
  function clearAnalysis() { setAnalysisState('IDLE'); setAnalysis(null); setPreviousAnalysis(null); setAnalysisMessage('') }
  function clearParcelVerification() { setSelectedCandidate(null); setVerificationState('IDLE'); setConfirmation(null); setVerificationMessage(''); clearInputProfiles(); clearAnalysis() }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const normalizedQuery = query.trim(); clearParcelVerification()
    if (!normalizedQuery) { setCandidates([]); setState('SEARCH_EMPTY'); setMessage('검색할 지번주소를 입력해 주세요.'); return }
    setState('SEARCHING'); setCandidates([]); setMessage('필지 후보를 찾고 있습니다.')
    try {
      const result = await searchParcelCandidates(normalizedQuery); setCandidates(result.candidates)
      if (result.candidates.length === 0) { setState('SEARCH_EMPTY'); setMessage('검색은 완료됐지만 일치하는 필지 후보가 없습니다. 지번주소를 확인하거나 검색어를 조금 넓혀 주세요.'); return }
      setState('SEARCH_RESULTS'); setMessage(`${result.count}개의 필지 후보를 찾았습니다.`)
    } catch (error) { setState('SEARCH_ERROR'); setMessage(error instanceof Error ? error.message : '필지 후보 검색 중 오류가 발생했습니다.') }
  }

  async function handleCandidateSelection(candidate: ParcelCandidate) {
    if (verificationState === 'VERIFYING_PARCEL' || analysisState === 'ANALYZING') return
    clearInputProfiles(); clearAnalysis(); setSelectedCandidate(candidate); setConfirmation(null); setVerificationState('VERIFYING_PARCEL'); setVerificationMessage('선택한 필지의 실제 경계를 Backend에서 확인하고 있습니다.')
    try {
      const result = await confirmParcelCandidate(candidate)
      if (result.parcel.pnu !== candidate.candidate_pnu) throw new Error('검증된 필지와 선택한 필지의 PNU가 일치하지 않습니다.')
      setConfirmation(result); setVerificationState('PARCEL_VERIFIED'); setVerificationMessage('Backend가 선택한 필지와 실제 필지 경계의 일치를 확인했습니다.')
    } catch (error) { setConfirmation(null); setVerificationState('PARCEL_VERIFICATION_FAILED'); setVerificationMessage(error instanceof Error ? error.message : '선택한 필지를 확인하지 못했습니다. 다른 필지를 선택하거나 다시 검색해 주세요.') }
  }

  async function runAnalysis(project: SiteAnalysisInputProfile = {}, procedure: SiteAnalysisInputProfile = {}, preserveCurrent = false) {
    if (!selectedCandidate || !confirmation || verificationState !== 'PARCEL_VERIFIED') return
    if (!preserveCurrent) clearAnalysis()
    setAnalysisState('ANALYZING'); setAnalysisMessage(preserveCurrent ? '입력한 정보를 반영해 SITE 분석을 다시 실행하고 있습니다.' : 'Backend가 필지를 다시 검증한 뒤 SITE 분석을 실행하고 있습니다.')
    try {
      const result = await analyzeSelectedParcelCandidate(selectedCandidate, { project_profile: project, procedure_profile: procedure })
      if (result.site.pnu !== confirmation.parcel.pnu) throw new Error('분석 결과의 PNU가 확인된 필지와 일치하지 않습니다.')
      setPreviousAnalysis(preserveCurrent ? analysis : null); setAnalysis(result); setAnalysisState('ANALYSIS_READY'); setAnalysisMessage(preserveCurrent ? '입력한 정보를 반영한 SITE 분석 결과를 받았습니다.' : '실제 SITE 분석 결과를 받았습니다.')
    } catch (error) {
      if (!preserveCurrent) setAnalysis(null)
      setAnalysisState(preserveCurrent && analysis ? 'ANALYSIS_READY' : 'ANALYSIS_FAILED')
      setAnalysisMessage(error instanceof Error ? error.message : 'SITE 분석을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.')
    }
  }

  async function handleAnalysis() { await runAnalysis() }
  async function handleReanalysis() { await runAnalysis(projectProfile, procedureProfile, true) }

  function updateRequirement(profileType: 'project' | 'procedure', name: string, nextState: Exclude<SiteAnalysisInputState, 'UNSET'>) {
    const setter = profileType === 'project' ? setProjectProfile : setProcedureProfile
    setter((current) => ({ ...current, [name]: nextState }))
  }

  function renderRequirementItem(item: SiteAnalysisRequirement, profileType: 'project' | 'procedure') {
    const profile = profileType === 'project' ? projectProfile : procedureProfile
    const selected = profile[item.name]
    return <li className="requirement-item" key={`${profileType}-${item.name}`}><div className="requirement-item-copy"><strong>{item.name}</strong><small>관련 법규 {item.affected_clause_count}개 조항의 판단에 필요한 정보</small></div><div className="requirement-options" role="group" aria-label={`${item.name} 선택`}>{INPUT_OPTIONS.map((option) => <button key={option.state} type="button" className={selected === option.state ? 'requirement-option requirement-option-selected' : 'requirement-option'} aria-pressed={selected === option.state} onClick={() => updateRequirement(profileType, item.name, option.state)} disabled={analysisState === 'ANALYZING'}>{option.label}</button>)}</div></li>
  }

  const resultReady = analysisState === 'ANALYSIS_READY' && analysis !== null
  const selectedInputCount = Object.keys(projectProfile).length + Object.keys(procedureProfile).length
  const selectedProjectInputCount = Object.keys(projectProfile).length
  const selectedProcedureInputCount = Object.keys(procedureProfile).length
  const remainingProjectInputCount = analysis ? Math.max(analysis.requirements.project_count - selectedProjectInputCount, 0) : 0
  const remainingProcedureInputCount = analysis ? Math.max(analysis.requirements.procedure_count - selectedProcedureInputCount, 0) : 0
  const totalRequirementCount = analysis ? analysis.requirements.project_count + analysis.requirements.procedure_count : 0
  const remainingInputCount = Math.max(totalRequirementCount - selectedInputCount, 0)
  function renderRuleDelta(current: number, previous: number | undefined) {
    if (previous === undefined) return null
    const delta = current - previous
    return <small className={delta === 0 ? 'rule-delta rule-delta-zero' : 'rule-delta'}>{delta > 0 ? `+${delta}` : String(delta)}</small>
  }

  return (
    <main className={`app-shell${resultReady ? ' app-shell-result-ready' : ''}`}>
      <section className={`search-panel${resultReady ? ' search-panel-result-ready' : ''}`} aria-labelledby="page-title">
        <header className={`search-intro${resultReady ? ' search-intro-compact' : ''}`}><div className="brand">SITE AI</div><h1 id="page-title">{resultReady ? '대지 분석 결과' : '분석할 대지를 찾아보세요'}</h1><p className="lead">{resultReady ? '확인된 필지의 분석 결과입니다. 지도에서 검증된 필지 경계를 함께 확인할 수 있습니다.' : '주소를 입력하면 분석 가능한 필지 후보를 찾습니다.'}</p></header>
        <div className={`pre-analysis-controls${resultReady ? ' pre-analysis-controls-compact' : ''}`}>
          <form className="search-form" onSubmit={handleSubmit}><label htmlFor="parcel-address">지번주소</label><div className="search-row"><input id="parcel-address" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="예: 서울특별시 강남구 개포동 12" autoComplete="street-address" /><button type="submit" disabled={state === 'SEARCHING'}>{state === 'SEARCHING' ? '검색 중' : resultReady ? '다른 필지 찾기' : '필지 찾기'}</button></div></form>
          <p className={`status status-${state.toLowerCase()}`} role="status">{message}</p>
          {state === 'SEARCH_RESULTS' && <div className="candidate-list" ref={candidateListRef} aria-label="필지 후보 목록">{candidates.map((candidate) => { const isSelected = selectedCandidate?.candidate_pnu === candidate.candidate_pnu; const isVerifying = isSelected && verificationState === 'VERIFYING_PARCEL'; return <button ref={isSelected ? selectedCandidateCardRef : null} className={`candidate-card${isSelected ? ' candidate-card-selected' : ''}`} key={`${candidate.candidate_pnu}-${candidate.x}-${candidate.y}`} type="button" onClick={() => handleCandidateSelection(candidate)} disabled={verificationState === 'VERIFYING_PARCEL' || analysisState === 'ANALYZING'} aria-pressed={isSelected}><span className="candidate-heading"><strong>{candidate.parcel_address || '지번주소 정보 없음'}</strong>{candidate.building_name && <span>{candidate.building_name}</span>}</span>{candidate.road_address && <span className="candidate-road-address">{candidate.road_address}</span>}<small>{isVerifying ? '필지 확인 중…' : `후보 위치 · ${candidate.crs}`}</small></button> })}</div>}
          {selectedCandidate && verificationState !== 'IDLE' && <section className={`verification-panel verification-${verificationState.toLowerCase()}${resultReady ? ' verification-panel-compact' : ''}`} aria-live="polite"><div className="verification-title-row"><strong>{verificationState === 'PARCEL_VERIFIED' ? '필지 확인 완료' : verificationState === 'PARCEL_VERIFICATION_FAILED' ? '필지 확인 실패' : '필지 확인 중'}</strong>{verificationState === 'PARCEL_VERIFIED' && <span className="verified-badge">VERIFIED</span>}</div>{!resultReady && <p>{verificationMessage}</p>}{confirmation && <><dl className={resultReady ? 'verified-details verified-details-result-ready' : 'verified-details'}><div><dt>지번주소</dt><dd>{selectedCandidate.parcel_address || '정보 없음'}</dd></div><div><dt>PNU</dt><dd>{confirmation.parcel.pnu}</dd></div>{!resultReady && <><div><dt>경계 형식</dt><dd>{confirmation.geometry.type}</dd></div><div><dt>좌표계</dt><dd>{confirmation.parcel.crs}</dd></div></>}</dl>{!resultReady && <button className="analysis-button" type="button" onClick={handleAnalysis} disabled={analysisState === 'ANALYZING'}>{analysisState === 'ANALYZING' ? '분석 중…' : '이 필지 분석'}</button>}</>}</section>}
        </div>
        {analysisState !== 'IDLE' && <section className={`analysis-panel analysis-${analysisState.toLowerCase()}${resultReady ? ' analysis-panel-result-ready' : ''}`} aria-live="polite"><div className="analysis-title-row"><strong>{analysisState === 'ANALYSIS_READY' ? 'SITE 분석 결과' : analysisState === 'ANALYSIS_FAILED' ? 'SITE 분석 실패' : 'SITE 분석 중'}</strong>{analysisState === 'ANALYSIS_READY' && <span className="analysis-ready-badge">분석 완료</span>}</div>{!resultReady && <p>{analysisMessage}</p>}{analysis && <><nav className="analysis-section-nav" aria-label="분석 결과 바로가기"><span>결과 바로가기</span><div><a href="#analysis-basic">기본정보</a><a href="#analysis-area">대지면적</a><a href="#analysis-scale">건축규모</a><a href="#analysis-rules">법규평가</a><a href="#analysis-requirements">추가입력</a><a href="#analysis-external">외부확인</a></div></nav><div className="analysis-details">
          <section className="analysis-detail-section" id="analysis-basic"><h2>필지 기본정보</h2><dl className="analysis-summary"><div><dt>지번주소</dt><dd>{displayValue(analysis.site.address)}</dd></div><div><dt>도로명주소</dt><dd>{displayValue(analysis.site.road_address)}</dd></div><div><dt>PNU</dt><dd>{displayValue(analysis.site.pnu)}</dd></div><div><dt>용도지역</dt><dd>{displayValue(analysis.site.zone)}</dd></div><div><dt>분석 상태</dt><dd>{displayAnalysisStatus(analysis.status)}</dd></div><div><dt>건축물 조회 건수</dt><dd>{analysis.service?.building_total_count === null || analysis.service?.building_total_count === undefined ? '정보 없음' : `${analysis.service.building_total_count}건`}</dd></div><div><dt>건축HUB 상태</dt><dd>{analysis.service?.building_api_status === '00' ? '정상 (00)' : displayValue(analysis.service?.building_api_status)}</dd></div><div><dt>추가 입력</dt><dd>{analysis.requirements.requires_additional_input ? '필요' : '현재 응답 기준 없음'}</dd></div></dl></section>
          <section className="analysis-detail-section" id="analysis-area"><h2>대지면적</h2><div className="analysis-metric-grid analysis-area-metric-grid"><article className="analysis-metric analysis-metric-primary"><span>공식 대지면적</span><strong>{displayNumber(analysis.land_area.official.value, '㎡')}</strong><small>공식/속성 면적 · 주 기준</small></article><article className="analysis-metric analysis-metric-supporting"><span>공간 면적</span><strong>{displayNumber(analysis.land_area.spatial.value)}</strong><small>{analysis.land_area.spatial.value === null ? 'Backend 응답에 값이 없어 계산하지 않음' : displayValue(analysis.land_area.spatial.unit)}</small></article><article className="analysis-metric analysis-metric-supporting"><span>면적 차이</span><strong>{displayNumber(analysis.land_area.difference.value, '㎡')}</strong><small>{analysis.land_area.difference.value === null ? '비교할 공간 면적이 없어 계산하지 않음' : `차이율 ${displayNumber(analysis.land_area.difference.ratio_percent, '%')}`}</small></article></div></section>
          <section className="analysis-detail-section" id="analysis-scale"><h2>건축 규모 기준</h2><div className="analysis-metric-grid analysis-metric-grid-two"><article className="analysis-metric"><span>건폐율</span><strong>{displayNumber(analysis.regulation.building_coverage_ratio.value, '%')}</strong><small>{displayRegulationStatus(analysis.regulation.building_coverage_ratio.status)}</small></article><article className="analysis-metric"><span>용적률</span><strong>{displayNumber(analysis.regulation.floor_area_ratio.value, '%')}</strong><small>{displayRegulationStatus(analysis.regulation.floor_area_ratio.status)}</small></article></div></section>
          <section className="analysis-detail-section" id="analysis-rules"><h2>법규 평가 집계</h2><p className="analysis-note">Backend Rule Engine의 집계 결과이며 Frontend에서 적용 여부를 다시 판단하지 않습니다.</p><div className="rule-summary-grid"><article><span>전체</span><strong>{analysis.rule_evaluation.total}</strong>{renderRuleDelta(analysis.rule_evaluation.total, previousAnalysis?.rule_evaluation.total)}</article><article><span>적용</span><strong>{analysis.rule_evaluation.applicable}</strong>{renderRuleDelta(analysis.rule_evaluation.applicable, previousAnalysis?.rule_evaluation.applicable)}</article><article><span>비적용</span><strong>{analysis.rule_evaluation.not_applicable}</strong>{renderRuleDelta(analysis.rule_evaluation.not_applicable, previousAnalysis?.rule_evaluation.not_applicable)}</article><article><span>조건부</span><strong>{analysis.rule_evaluation.conditional}</strong>{renderRuleDelta(analysis.rule_evaluation.conditional, previousAnalysis?.rule_evaluation.conditional)}</article><article className="rule-unknown"><span>확인 필요</span><strong>{analysis.rule_evaluation.unknown}</strong>{renderRuleDelta(analysis.rule_evaluation.unknown, previousAnalysis?.rule_evaluation.unknown)}</article></div>{previousAnalysis && <p className="rule-delta-explanation">변화량은 직전 Backend 분석 결과와 비교한 조항 수 차이입니다.</p>}<p className="unknown-explanation">확인 필요는 오류나 비적용이 아닙니다. 현재 정보만으로 적용 여부를 확정할 수 없는 규칙입니다.</p></section>
          <section className="analysis-detail-section" id="analysis-requirements"><h2>추가 입력 필요사항</h2>{!analysis.requirements.requires_additional_input ? <p className="analysis-empty">현재 응답 기준 추가 입력 항목이 없습니다.</p> : <><div className="requirement-progress" aria-label="추가 입력 진행상태"><div><span>사업 정보</span><strong>{analysis.requirements.project_count}개 중 {selectedProjectInputCount}개 입력</strong><small>{remainingProjectInputCount === 0 ? '입력 완료' : `${remainingProjectInputCount}개 미입력`}</small></div><div><span>절차 정보</span><strong>{analysis.requirements.procedure_count}개 중 {selectedProcedureInputCount}개 입력</strong><small>{remainingProcedureInputCount === 0 ? '입력 완료' : `${remainingProcedureInputCount}개 미입력`}</small></div></div><div className="requirement-columns"><details className="requirement-group" open><summary><span>사업 정보</span><strong>{analysis.requirements.project_count}개</strong><small>각 항목의 현재 상황을 선택해 주세요.</small></summary><ul>{analysis.requirements.project.map((item) => renderRequirementItem(item, 'project'))}</ul></details><details className="requirement-group" open><summary><span>절차 정보</span><strong>{analysis.requirements.procedure_count}개</strong><small>각 항목의 현재 상황을 선택해 주세요.</small></summary><ul>{analysis.requirements.procedure.map((item) => renderRequirementItem(item, 'procedure'))}</ul></details></div><div className="requirement-reanalysis"><span>{selectedInputCount === 0 ? `전체 ${totalRequirementCount}개 중 선택한 추가 정보가 없습니다.` : remainingInputCount === 0 ? `전체 ${totalRequirementCount}개 입력 완료` : `전체 ${totalRequirementCount}개 중 ${selectedInputCount}개 입력 · ${remainingInputCount}개 미입력`}</span><button type="button" onClick={handleReanalysis} disabled={selectedInputCount === 0 || analysisState === 'ANALYZING'}>{analysisState === 'ANALYZING' ? '다시 분석 중…' : '입력 내용으로 다시 분석'}</button></div></>}</section>
          <section className="analysis-detail-section" id="analysis-external"><h2>외부 확인 정보</h2>{analysis.external_dependencies.count === 0 ? <p className="analysis-empty">현재 응답 기준 별도 외부 확인 항목이 없습니다.</p> : <ul className="dependency-list">{analysis.external_dependencies.items.map((item, index) => <li key={`dependency-${index}`}><div className="dependency-heading"><strong>{displayExternalCategory(item.category)}</strong>{item.category === 'SITE_HISTORY' && <small>원본 분류 SITE_HISTORY</small>}</div><dl className="dependency-facts"><div><dt>확인 조건</dt><dd>{displayValue(item.condition)}</dd></div><div><dt>현재 상태</dt><dd>{displayValue(item.status)}</dd></div><div><dt>분석 차단</dt><dd>{item.blocking_analysis ? '예' : '아니오'}</dd></div></dl></li>)}</ul>}</section>
        </div></>}</section>}
      </section>
      <KakaoMap candidates={candidates} selectedCandidate={selectedCandidate} confirmation={confirmation} onCandidateSelect={handleCandidateSelection} />
    </main>
  )
}
