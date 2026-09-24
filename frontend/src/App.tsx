import { FormEvent, useEffect, useRef, useState } from 'react'
import { confirmParcelCandidate, ParcelCandidateApiError, searchParcelCandidates } from './api/parcelCandidates'
import { analyzeSelectedParcelCandidate, SiteAnalysisApiError } from './api/siteAnalysis'
import KakaoMap from './map/KakaoMap'
import RuleEvaluationSection from './components/RuleEvaluationSection'
import AnalysisRequirements from './components/AnalysisRequirements'
import SiteFactsSection from './components/SiteFactsSection'
import LandAreaSection from './components/LandAreaSection'
import BuildingScaleSection from './components/BuildingScaleSection'
import ExternalDependenciesSection from './components/ExternalDependenciesSection'
import type { CandidateSearchState, ParcelCandidate, ParcelConfirmationResponse, ParcelVerificationState } from './types/parcel'
import type { SiteAnalysisInputProfile, SiteAnalysisResponse, SiteAnalysisState } from './types/siteAnalysis'

const INITIAL_GUIDE = '지번주소 또는 도로명주소로 필지를 검색할 수 있습니다.'
function displayParcelApiError(error: unknown, fallback: string): string {
  if (!(error instanceof ParcelCandidateApiError)) return error instanceof Error ? error.message : fallback
  if (error.code === 'PARCEL_VERIFICATION_FAILED') return `${error.message} 다른 필지를 선택하거나 다시 검색해 주세요.`
  if (error.code === 'PARCEL_GEOMETRY_UNRESOLVED') return `${error.message} 다른 필지를 선택하거나 다시 검색해 주세요.`
  if (error.category === 'PROVIDER') return `외부 데이터 조회에 실패했습니다. ${error.message}${error.retryable === true ? ' 다시 시도할 수 있습니다.' : ''}`
  return error.message || fallback
}
function displaySiteAnalysisApiError(error: unknown, fallback: string): string {
  if (!(error instanceof SiteAnalysisApiError)) return error instanceof Error ? error.message : fallback
  if (error.category === 'PROVIDER') return `외부 데이터 조회에 실패해 SITE 분석을 완료하지 못했습니다. ${error.message}${error.retryable === true ? ' 다시 시도할 수 있습니다.' : ''}`
  if (error.category === 'PARCEL') return `${error.message} 필지를 다시 확인해 주세요.`
  return error.message || fallback
}

export default function App() {
  const [query, setQuery] = useState('')
  const [state, setState] = useState<CandidateSearchState>('IDLE')
  const [candidates, setCandidates] = useState<ParcelCandidate[]>([])
  const [showResultCandidates, setShowResultCandidates] = useState(false)
  const [message, setMessage] = useState(INITIAL_GUIDE)
  const [selectedCandidate, setSelectedCandidate] = useState<ParcelCandidate | null>(null)
  const [verificationState, setVerificationState] = useState<ParcelVerificationState>('IDLE')
  const [confirmation, setConfirmation] = useState<ParcelConfirmationResponse | null>(null)
  const [verificationMessage, setVerificationMessage] = useState('')
  const [analysisState, setAnalysisState] = useState<SiteAnalysisState>('IDLE')
  const [analysis, setAnalysis] = useState<SiteAnalysisResponse | null>(null)
  const [previousAnalysis, setPreviousAnalysis] = useState<SiteAnalysisResponse | null>(null)
  const [analysisMessage, setAnalysisMessage] = useState('')
  const [reanalysisError, setReanalysisError] = useState('')
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
  function clearAnalysis() { setAnalysisState('IDLE'); setAnalysis(null); setPreviousAnalysis(null); setAnalysisMessage(''); setReanalysisError('') }
  function clearParcelVerification() { setSelectedCandidate(null); setVerificationState('IDLE'); setConfirmation(null); setVerificationMessage(''); clearInputProfiles(); clearAnalysis() }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const normalizedQuery = query.trim(); clearParcelVerification()
    if (!normalizedQuery) { setCandidates([]); setState('SEARCH_EMPTY'); setMessage('검색할 주소를 입력해 주세요.'); return }
    setShowResultCandidates(false);     setState('SEARCHING'); setCandidates([]); setMessage('필지 후보를 찾고 있습니다.')
    try {
      const result = await searchParcelCandidates(normalizedQuery); setCandidates(result.candidates)
      if (result.candidates.length === 0) { setState('SEARCH_EMPTY'); setMessage('검색은 완료됐지만 일치하는 필지 후보가 없습니다. 주소를 확인하거나 검색어를 조금 넓혀 주세요.'); return }
      setState('SEARCH_RESULTS'); setMessage(`${result.count}개의 필지 후보를 찾았습니다.`)
    } catch (error) { setState('SEARCH_ERROR'); setMessage(displayParcelApiError(error, '필지 후보 검색 중 오류가 발생했습니다.')) }
  }

  async function handleCandidateSelection(candidate: ParcelCandidate) {
    if (verificationState === 'VERIFYING_PARCEL' || analysisState === 'ANALYZING') return
    clearInputProfiles(); clearAnalysis(); setSelectedCandidate(candidate); setConfirmation(null); setVerificationState('VERIFYING_PARCEL'); setVerificationMessage('선택한 필지의 실제 경계를 Backend에서 확인하고 있습니다.')
    try {
      const result = await confirmParcelCandidate(candidate)
      if (result.parcel.pnu !== candidate.candidate_pnu) throw new Error('검증된 필지와 선택한 필지의 PNU가 일치하지 않습니다.')
      setConfirmation(result); setVerificationState('PARCEL_VERIFIED'); setVerificationMessage('Backend가 선택한 필지와 실제 필지 경계의 일치를 확인했습니다.')
    } catch (error) { setConfirmation(null); setVerificationState('PARCEL_VERIFICATION_FAILED'); setVerificationMessage(displayParcelApiError(error, '선택한 필지를 확인하지 못했습니다. 다른 필지를 선택하거나 다시 검색해 주세요.')) }
  }

  async function runAnalysis(project: SiteAnalysisInputProfile = {}, procedure: SiteAnalysisInputProfile = {}, preserveCurrent = false) {
    if (!selectedCandidate || !confirmation || verificationState !== 'PARCEL_VERIFIED') return
    if (!preserveCurrent) clearAnalysis()
    setReanalysisError(''); setAnalysisState('ANALYZING'); setAnalysisMessage(preserveCurrent ? '입력한 정보를 반영해 SITE 분석을 다시 실행하고 있습니다.' : 'Backend가 필지를 다시 검증한 뒤 SITE 분석을 실행하고 있습니다.')
    try {
      const result = await analyzeSelectedParcelCandidate(selectedCandidate, { project_profile: project, procedure_profile: procedure })
      if (result.site.pnu !== confirmation.parcel.pnu) throw new Error('분석 결과의 PNU가 확인된 필지와 일치하지 않습니다.')
      setPreviousAnalysis(preserveCurrent ? analysis : null); setAnalysis(result); setAnalysisState('ANALYSIS_READY'); setAnalysisMessage(preserveCurrent ? '입력한 정보를 반영한 SITE 분석 결과를 받았습니다.' : '실제 SITE 분석 결과를 받았습니다.')
    } catch (error) {
      if (!preserveCurrent) setAnalysis(null)
      setAnalysisState(preserveCurrent && analysis ? 'ANALYSIS_READY' : 'ANALYSIS_FAILED')
      const failureMessage = displaySiteAnalysisApiError(error, 'SITE 분석을 완료하지 못했습니다.')
      setAnalysisMessage(failureMessage)
      if (preserveCurrent && analysis) setReanalysisError(failureMessage)
    }
  }

  async function handleAnalysis() { await runAnalysis() }
  async function handleReanalysis() { await runAnalysis(projectProfile, procedureProfile, true) }

  function updateRequirement(
    profileType: 'project' | 'procedure',
    name: string,
    nextState: SiteAnalysisInputProfile[string],
  ) {
    if (!nextState) return
    const setter = profileType === 'project' ? setProjectProfile : setProcedureProfile
    setter((current) => {
      if (current[name] !== nextState) return { ...current, [name]: nextState }
      const next = { ...current }
      delete next[name]
      return next
    })
  }

  const resultReady = analysis !== null
  const reanalysisInProgress = analysisState === 'ANALYZING' && analysis !== null

  return (
    <main className={`app-shell${resultReady ? ' app-shell-result-ready' : ''}`}>
      <section className={`search-panel${resultReady ? ' search-panel-result-ready' : ''}`} aria-labelledby="page-title">
        <header className={`search-intro${resultReady ? ' search-intro-compact' : ''}`}><div className="brand">SITE AI</div><h1 id="page-title">{resultReady ? '대지 분석 결과' : '분석할 대지를 찾아보세요'}</h1><p className="lead">{resultReady ? '확인된 필지의 분석 결과입니다. 지도에서 검증된 필지 경계를 함께 확인할 수 있습니다.' : '주소를 입력하면 분석 가능한 필지 후보를 찾습니다.'}</p></header>
        <div className={`pre-analysis-controls${resultReady ? ' pre-analysis-controls-compact' : ''}`}>
          <form className="search-form" onSubmit={handleSubmit}><label htmlFor="parcel-address">주소</label><div className="search-row"><input id="parcel-address" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="예: 서울특별시 강남구 개포동 12 또는 개포로109길 21" autoComplete="street-address" /><button type="submit" disabled={state === 'SEARCHING'}>{state === 'SEARCHING' ? '검색 중' : resultReady ? '다른 필지 찾기' : '필지 찾기'}</button></div></form>
          <p className={`status status-${state.toLowerCase()}`} role="status">{message}</p>
          {state === 'SEARCH_RESULTS' && resultReady && <div className="candidate-list-toggle"><span>같은 검색의 후보 {candidates.length}개</span><button type="button" onClick={() => setShowResultCandidates((current) => !current)} aria-expanded={showResultCandidates}>{showResultCandidates ? '후보 접기' : '후보 다시 보기'}</button></div>}
          {state === 'SEARCH_RESULTS' && (!resultReady || showResultCandidates) && <div className="candidate-list" ref={candidateListRef} aria-label="필지 후보 목록">{candidates.map((candidate) => { const isSelected = selectedCandidate?.candidate_pnu === candidate.candidate_pnu; const isVerifying = isSelected && verificationState === 'VERIFYING_PARCEL'; return <button ref={isSelected ? selectedCandidateCardRef : null} className={`candidate-card${isSelected ? ' candidate-card-selected' : ''}`} key={`${candidate.candidate_pnu}-${candidate.x}-${candidate.y}`} type="button" onClick={() => handleCandidateSelection(candidate)} disabled={verificationState === 'VERIFYING_PARCEL' || analysisState === 'ANALYZING'} aria-pressed={isSelected}><span className="candidate-heading"><strong>{candidate.parcel_address || '지번주소 정보 없음'}</strong>{candidate.building_name && <span>{candidate.building_name}</span>}</span>{candidate.road_address && <span className="candidate-road-address">{candidate.road_address}</span>}<small>{isVerifying ? '필지 확인 중…' : `후보 위치 · ${candidate.crs}`}</small></button> })}</div>}
          {selectedCandidate && verificationState !== 'IDLE' && !resultReady && <section className={`verification-panel verification-${verificationState.toLowerCase()}`} aria-live="polite"><div className="verification-title-row"><strong>{verificationState === 'PARCEL_VERIFIED' ? '필지 확인 완료' : verificationState === 'PARCEL_VERIFICATION_FAILED' ? '필지 확인 실패' : '필지 확인 중'}</strong>{verificationState === 'PARCEL_VERIFIED' && <span className="verified-badge">VERIFIED</span>}</div>{!resultReady && <p>{verificationMessage}</p>}{confirmation && <><dl className={resultReady ? 'verified-details verified-details-result-ready' : 'verified-details'}><div><dt>지번주소</dt><dd>{selectedCandidate.parcel_address || '정보 없음'}</dd></div><div><dt>PNU</dt><dd>{confirmation.parcel.pnu}</dd></div>{!resultReady && <><div><dt>경계 형식</dt><dd>{confirmation.geometry.type}</dd></div><div><dt>좌표계</dt><dd>{confirmation.parcel.crs}</dd></div></>}</dl>{!resultReady && <button className="analysis-button" type="button" onClick={handleAnalysis} disabled={analysisState === 'ANALYZING'}>{analysisState === 'ANALYZING' ? '분석 중…' : '이 필지 분석'}</button>}</>}</section>}
        </div>
        {analysisState !== 'IDLE' && <section className={`analysis-panel analysis-${analysisState.toLowerCase()}${resultReady ? ' analysis-panel-result-ready' : ''}`} aria-live="polite"><div className="analysis-title-row"><strong>{analysisState === 'ANALYSIS_READY' ? 'SITE 분석 결과' : analysisState === 'ANALYSIS_FAILED' ? 'SITE 분석 실패' : 'SITE 분석 중'}</strong>{analysisState === 'ANALYSIS_READY' && <span className="analysis-ready-badge">분석 완료</span>}</div>{!resultReady && <p>{analysisMessage}</p>}{reanalysisInProgress && <div className="reanalysis-progress" role="status"><strong>입력 정보를 반영해 재분석하고 있습니다.</strong><small>아래에는 재분석이 완료되기 전까지 직전 성공 분석 결과가 표시됩니다.</small></div>}{resultReady && reanalysisError && <div className="reanalysis-error" role="alert"><strong>입력 정보를 반영한 재분석을 완료하지 못했습니다.</strong><span>{reanalysisError}</span><small>아래에는 직전 성공 분석 결과가 계속 표시됩니다.</small></div>}{analysis && <><nav className="analysis-section-nav" aria-label="분석 결과 바로가기"><span>결과 바로가기</span><div><a href="#analysis-basic">대상지 현황</a><a href="#analysis-area">대지면적</a><a href="#analysis-scale">건축규모</a><a href="#analysis-rules">법규평가</a><a href="#analysis-requirements">추가입력</a><a href="#analysis-external">외부확인</a></div></nav><div className="analysis-details">
          <SiteFactsSection analysis={analysis} />
          <LandAreaSection landArea={analysis.land_area} />
          <BuildingScaleSection regulation={analysis.regulation} />
          <RuleEvaluationSection
            evaluation={analysis.rule_evaluation}
            previousEvaluation={previousAnalysis?.rule_evaluation}
            ruleDetails={analysis.rule_details.items}
          />
          <AnalysisRequirements
            requirements={analysis.requirements}
            projectProfile={projectProfile}
            procedureProfile={procedureProfile}
            analysisState={analysisState}
            onRequirementChange={updateRequirement}
            onReanalysis={handleReanalysis}
          />
          <ExternalDependenciesSection dependencies={analysis.external_dependencies} />
        </div></>}</section>}
      </section>
      <KakaoMap candidates={candidates} selectedCandidate={selectedCandidate} confirmation={confirmation} onCandidateSelect={handleCandidateSelection} />
    </main>
  )
}
