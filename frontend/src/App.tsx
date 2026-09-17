import { FormEvent, useState } from 'react'
import { searchParcelCandidates } from './api/parcelCandidates'
import type { CandidateSearchState, ParcelCandidate } from './types/parcel'

const INITIAL_GUIDE = '현재 검증된 범위에서는 지번주소로 검색하는 것을 권장합니다.'

export default function App() {
  const [query, setQuery] = useState('')
  const [state, setState] = useState<CandidateSearchState>('IDLE')
  const [candidates, setCandidates] = useState<ParcelCandidate[]>([])
  const [message, setMessage] = useState(INITIAL_GUIDE)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedQuery = query.trim()
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
            {candidates.map((candidate) => (
              <article className="candidate-card" key={`${candidate.candidate_pnu}-${candidate.x}-${candidate.y}`}>
                <div className="candidate-heading">
                  <strong>{candidate.parcel_address || '지번주소 정보 없음'}</strong>
                  {candidate.building_name && <span>{candidate.building_name}</span>}
                </div>
                {candidate.road_address && <p>{candidate.road_address}</p>}
                <small>후보 위치 · {candidate.crs}</small>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="map-placeholder" aria-label="지도 영역 준비 중">
        <div>
          <span>MAP</span>
          <h2>지도 영역</h2>
          <p>다음 단계에서 후보 marker와 검증된 필지 경계를 연결합니다.</p>
        </div>
      </section>
    </main>
  )
}
