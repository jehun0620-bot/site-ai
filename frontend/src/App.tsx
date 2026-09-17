import { FormEvent, useState } from 'react'
import { confirmParcelCandidate, searchParcelCandidates } from './api/parcelCandidates'
import KakaoMap from './map/KakaoMap'
import type {
  CandidateSearchState,
  ParcelCandidate,
  ParcelConfirmationResponse,
  ParcelVerificationState,
} from './types/parcel'

const INITIAL_GUIDE = '현재 검증된 범위에서는 지번주소로 검색하는 것을 권장합니다.'

export default function App() {
  const [query, setQuery] = useState('')
  const [state, setState] = useState<CandidateSearchState>('IDLE')
  const [candidates, setCandidates] = useState<ParcelCandidate[]>([])
  const [message, setMessage] = useState(INITIAL_GUIDE)
  const [selectedCandidate, setSelectedCandidate] = useState<ParcelCandidate | null>(null)
  const [verificationState, setVerificationState] = useState<ParcelVerificationState>('IDLE')
  const [confirmation, setConfirmation] = useState<ParcelConfirmationResponse | null>(null)
  const [verificationMessage, setVerificationMessage] = useState('')

  function clearParcelVerification() {
    setSelectedCandidate(null)
    setVerificationState('IDLE')
    setConfirmation(null)
    setVerificationMessage('')
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

  return (
    <main className="app-shell">
      <section className="search-panel" aria-labelledby="page-title">
        <div className="brand">SITE AI</div>
        <h1 id="page-title">분석할 대지를 찾아보세요</h1>
        <p className="lead">주소를 입력하면 분석 가능한 필지 후보를 찾습니다.</p>

        <form className="search-form" onSubmit={handleSubmit}>
          <label htmlFor="parcel-address">지번주소</label>
          <div className="search-row">
            <input
              id="parcel-address"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="예: 서울특별시 강남구 개포동 12"
              autoComplete="street-address"
            />
            <button type="submit" disabled={state === 'SEARCHING'}>
              {state === 'SEARCHING' ? '검색 중' : '필지 찾기'}
            </button>
          </div>
        </form>

        <p className={`status status-${state.toLowerCase()}`} role="status">
          {message}
        </p>

        {state === 'SEARCH_RESULTS' && (
          <div className="candidate-list" aria-label="필지 후보 목록">
            {candidates.map((candidate) => {
              const isSelected = selectedCandidate?.candidate_pnu === candidate.candidate_pnu
              const isVerifying = isSelected && verificationState === 'VERIFYING_PARCEL'

              return (
                <button
                  className={`candidate-card${isSelected ? ' candidate-card-selected' : ''}`}
                  key={`${candidate.candidate_pnu}-${candidate.x}-${candidate.y}`}
                  type="button"
                  onClick={() => handleCandidateSelection(candidate)}
                  disabled={verificationState === 'VERIFYING_PARCEL'}
                  aria-pressed={isSelected}
                >
                  <span className="candidate-heading">
                    <strong>{candidate.parcel_address || '지번주소 정보 없음'}</strong>
                    {candidate.building_name && <span>{candidate.building_name}</span>}
                  </span>
                  {candidate.road_address && <span className="candidate-road-address">{candidate.road_address}</span>}
                  <small>{isVerifying ? '필지 확인 중…' : `후보 위치 · ${candidate.crs}`}</small>
                </button>
              )
            })}
          </div>
        )}

        {selectedCandidate && verificationState !== 'IDLE' && (
          <section className={`verification-panel verification-${verificationState.toLowerCase()}`} aria-live="polite">
            <div className="verification-title-row">
              <strong>
                {verificationState === 'PARCEL_VERIFIED'
                  ? '필지 확인 완료'
                  : verificationState === 'PARCEL_VERIFICATION_FAILED'
                    ? '필지 확인 실패'
                    : '필지 확인 중'}
              </strong>
              {verificationState === 'PARCEL_VERIFIED' && <span className="verified-badge">VERIFIED</span>}
            </div>
            <p>{verificationMessage}</p>

            {confirmation && (
              <dl className="verified-details">
                <div>
                  <dt>지번주소</dt>
                  <dd>{selectedCandidate.parcel_address || '정보 없음'}</dd>
                </div>
                <div>
                  <dt>PNU</dt>
                  <dd>{confirmation.parcel.pnu}</dd>
                </div>
                <div>
                  <dt>경계 형식</dt>
                  <dd>{confirmation.geometry.type}</dd>
                </div>
                <div>
                  <dt>좌표계</dt>
                  <dd>{confirmation.parcel.crs}</dd>
                </div>
              </dl>
            )}
          </section>
        )}
      </section>

      <KakaoMap candidates={candidates} selectedCandidate={selectedCandidate} confirmation={confirmation} />
    </main>
  )
}
