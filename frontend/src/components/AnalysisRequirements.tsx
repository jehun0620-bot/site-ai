import { useState } from 'react'
import type {
  SiteAnalysisInputProfile, SiteAnalysisInputState, SiteAnalysisNumericFactProfile,
  BuildingUseCatalogOption, SiteAnalysisRequirement, SiteAnalysisRequirements, SiteAnalysisState, SiteAnalysisStateFactProfile,
} from '../types/siteAnalysis'

const INPUT_OPTIONS: Array<{ state: Exclude<SiteAnalysisInputState, 'UNSET'>; label: string }> = [
  { state: 'TRUE', label: '해당함' }, { state: 'FALSE', label: '해당하지 않음' }, { state: 'UNKNOWN', label: '잘 모르겠음' },
]
type ProfileType = 'project' | 'procedure'
type Props = {
  requirements: SiteAnalysisRequirements
  buildingUseCatalog: BuildingUseCatalogOption[]
  buildingUseCatalogError: string
  projectProfile: SiteAnalysisInputProfile
  procedureProfile: SiteAnalysisInputProfile
  buildingUseName: string
  numericFacts: SiteAnalysisNumericFactProfile
  stateFacts: SiteAnalysisStateFactProfile
  analysisState: SiteAnalysisState
  onRequirementChange: (profileType: ProfileType, name: string, nextState: Exclude<SiteAnalysisInputState, 'UNSET'>) => void
  onBuildingUseChange: (name: string) => void
  onStateFactChange: (name: string, value: boolean) => void
  onNumericFactChange: (name: string, value: string, unit: string) => void
  onNumericFactUndecided: (name: string, unit: string) => void
  onReanalysis: () => void
}

function RequirementItem({ item, profileType, profile, analysisState, onRequirementChange }: {
  item: SiteAnalysisRequirement; profileType: ProfileType; profile: SiteAnalysisInputProfile; analysisState: SiteAnalysisState; onRequirementChange: Props['onRequirementChange']
}) {
  const selected = profile[item.name]
  return <li className="requirement-item"><div className="requirement-item-copy"><div className="requirement-item-heading"><strong>{item.name}</strong><span className={selected ? 'requirement-item-status requirement-item-status-complete' : 'requirement-item-status'}>{selected ? '입력 완료' : '미입력'}</span></div><small>관련 법규 {item.affected_clause_count}개 조항의 판단에 필요한 정보</small></div><div className="requirement-options" role="group" aria-label={`${item.name} 선택`}>{INPUT_OPTIONS.map((option) => <button key={option.state} type="button" className={selected === option.state ? 'requirement-option requirement-option-selected' : 'requirement-option'} aria-pressed={selected === option.state} onClick={() => onRequirementChange(profileType, item.name, option.state)} disabled={analysisState === 'ANALYZING'}>{option.label}</button>)}</div></li>
}

function stateFactLabel(name: string) {
  if (name === 'has_spectator_seating') return '관람석이 있습니까?'
  return name
}

function numericFactLabel(name: string) {
  if (name === 'spectator_seating_area') return '관람석 바닥면적의 합계'
  return name
}

export default function AnalysisRequirements(props: Props) {
  const { requirements, buildingUseCatalog, buildingUseCatalogError, projectProfile, procedureProfile, buildingUseName, numericFacts, stateFacts, analysisState, onRequirementChange, onBuildingUseChange, onStateFactChange, onNumericFactChange, onNumericFactUndecided, onReanalysis } = props
  const [projectOpen, setProjectOpen] = useState(true)
  const [procedureOpen, setProcedureOpen] = useState(true)
  const selectedProjectCount = Object.keys(projectProfile).length
  const selectedProcedureCount = Object.keys(procedureProfile).length
  const selectedBuildingUseCount = buildingUseName ? 1 : 0
  const selectedStateCount = requirements.state_facts.filter((item) => typeof stateFacts[item.name] === 'boolean').length
  const selectedNumericCount = requirements.numeric_facts.filter((item) => numericFacts[item.name] !== undefined).length
  const selectedCount = selectedProjectCount + selectedProcedureCount + selectedBuildingUseCount + selectedStateCount + selectedNumericCount
  const totalCount = requirements.project_count + requirements.procedure_count + requirements.building_use_count + requirements.state_fact_count + requirements.numeric_fact_count
  const remainingCount = Math.max(totalCount - selectedCount, 0)

  return <section className="analysis-detail-section" id="analysis-requirements"><h2>계획 및 추가 입력</h2>
    <div className="requirement-group requirement-direct-group">
      <div className="requirement-direct-heading"><span>계획 건축물 용도</span><strong>{buildingUseName || '미선택'}</strong></div>
      <div className="requirement-item">
        <label htmlFor="planned-building-use"><strong>분석할 계획 용도</strong><small>Backend가 현재 검증한 입력 가능 용도만 표시합니다.</small></label>
        <select id="planned-building-use" aria-label="계획 건축물 용도" value={buildingUseName} onChange={(event) => onBuildingUseChange(event.target.value)} disabled={analysisState === 'ANALYZING' || buildingUseCatalog.length === 0}>
          <option value="">선택하지 않음</option>
          {buildingUseCatalog.map((option) => <option key={option.canonical_name} value={option.canonical_name}>{option.canonical_name}</option>)}
        </select>
        {buildingUseCatalogError && <small role="alert">{buildingUseCatalogError}</small>}
      </div>
    </div>
    {!requirements.requires_additional_input ? <div className="requirement-reanalysis"><span>{buildingUseName ? '선택한 계획 용도를 분석에 반영할 수 있습니다.' : '현재 응답 기준 추가 입력 항목이 없습니다.'}</span><button type="button" onClick={onReanalysis} disabled={!buildingUseName || analysisState === 'ANALYZING'}>{analysisState === 'ANALYZING' ? '다시 분석 중…' : '계획 용도로 다시 분석'}</button></div> : <>
      <div className="requirement-progress" aria-label="추가 입력 진행상태">
        <div><span>사업 정보</span><strong>{requirements.project_count}개 중 {selectedProjectCount}개 입력</strong></div>
        <div><span>절차 정보</span><strong>{requirements.procedure_count}개 중 {selectedProcedureCount}개 입력</strong></div>
        <div><span>건축물 용도</span><strong>{requirements.building_use_count}개 중 {selectedBuildingUseCount}개 입력</strong></div>
        <div><span>분류 질문</span><strong>{requirements.state_fact_count}개 중 {selectedStateCount}개 입력</strong></div>
        <div><span>수치 정보</span><strong>{requirements.numeric_fact_count}개 중 {selectedNumericCount}개 입력</strong></div>
      </div>
      <div className="requirement-columns">
        <details className="requirement-group" open={projectOpen} onToggle={(e) => setProjectOpen(e.currentTarget.open)}><summary><span>사업 정보</span><strong>{requirements.project_count}개</strong><small>각 항목의 현재 상황을 선택해 주세요.</small></summary><ul>{requirements.project.map((item) => <RequirementItem key={`project-${item.name}`} item={item} profileType="project" profile={projectProfile} analysisState={analysisState} onRequirementChange={onRequirementChange} />)}</ul></details>
        <details className="requirement-group" open={procedureOpen} onToggle={(e) => setProcedureOpen(e.currentTarget.open)}><summary><span>절차 정보</span><strong>{requirements.procedure_count}개</strong><small>각 항목의 현재 상황을 선택해 주세요.</small></summary><ul>{requirements.procedure.map((item) => <RequirementItem key={`procedure-${item.name}`} item={item} profileType="procedure" profile={procedureProfile} analysisState={analysisState} onRequirementChange={onRequirementChange} />)}</ul></details>
        {requirements.building_use_count > 0 && <div className="requirement-group requirement-direct-group"><div className="requirement-direct-heading"><span>건축물 용도</span><strong>{requirements.building_use_count}개</strong></div><ul>{requirements.building_use.map((item) => <li className="requirement-item requirement-building-use" key={`${item.identity}-${item.name}`}><div className="requirement-item-copy"><strong>{item.name}</strong><small>식별 기준: {item.identity} · 관련 {item.affected_clause_count}개 조항</small></div><button type="button" className={buildingUseName === item.name ? 'requirement-option requirement-option-selected' : 'requirement-option'} onClick={() => onBuildingUseChange(buildingUseName === item.name ? '' : item.name)} disabled={analysisState === 'ANALYZING' || item.identity !== 'canonical'}>{buildingUseName === item.name ? '선택됨' : item.identity === 'canonical' ? '이 용도 선택' : '현재 입력 미지원'}</button></li>)}</ul></div>}
        {requirements.state_fact_count > 0 && <div className="requirement-group requirement-direct-group"><div className="requirement-direct-heading"><span>건축물 분류 질문</span><strong>{requirements.state_fact_count}개</strong></div><ul>{requirements.state_facts.map((item) => { const selected = stateFacts[item.name]; return <li className="requirement-item" key={item.name}><div className="requirement-item-copy"><strong>{stateFactLabel(item.name)}</strong><small>건축물 용도 분류에 필요한 정보</small></div><div className="requirement-options" role="group" aria-label={`${stateFactLabel(item.name)} 선택`}><button type="button" className={selected === true ? 'requirement-option requirement-option-selected' : 'requirement-option'} aria-pressed={selected === true} onClick={() => onStateFactChange(item.name, true)} disabled={analysisState === 'ANALYZING'}>예</button><button type="button" className={selected === false ? 'requirement-option requirement-option-selected' : 'requirement-option'} aria-pressed={selected === false} onClick={() => onStateFactChange(item.name, false)} disabled={analysisState === 'ANALYZING'}>아니오</button></div></li> })}</ul></div>}
        {requirements.numeric_fact_count > 0 && <div className="requirement-group requirement-direct-group"><div className="requirement-direct-heading"><span>수치 정보</span><strong>{requirements.numeric_fact_count}개</strong></div><ul>{requirements.numeric_facts.map((item) => { const fact = numericFacts[item.name]; const undecided = fact?.undecided === true; return <li className="requirement-item requirement-numeric" key={`${item.name}-${item.unit}`}><label htmlFor={`numeric-${item.name}`}><strong>{numericFactLabel(item.name)}</strong><small>{item.source === 'BUILDING_USE_CLASSIFICATION' ? '건축물 용도 분류에 필요한 수치' : `관련 ${item.affected_clause_count}개 조항`} · 단위 {item.unit}</small></label><div className="requirement-numeric-input"><input id={`numeric-${item.name}`} type="number" step="any" value={fact && !undecided && 'value' in fact ? fact.value : ''} onChange={(e) => onNumericFactChange(item.name, e.target.value, item.unit)} disabled={analysisState === 'ANALYZING' || undecided} /><span>{item.unit}</span><button type="button" className={undecided ? 'requirement-option requirement-option-selected' : 'requirement-option'} aria-pressed={undecided} onClick={() => onNumericFactUndecided(item.name, item.unit)} disabled={analysisState === 'ANALYZING'}>아직 미정</button></div></li> })}</ul></div>}
      </div>
      <div className="requirement-reanalysis"><span>{selectedCount === 0 ? `전체 ${totalCount}개 중 선택한 추가 정보가 없습니다.` : remainingCount === 0 ? `전체 ${totalCount}개 입력 완료` : `전체 ${totalCount}개 중 ${selectedCount}개 입력 · ${remainingCount}개 미입력`}</span><button type="button" onClick={onReanalysis} disabled={selectedCount === 0 || analysisState === 'ANALYZING'}>{analysisState === 'ANALYZING' ? '다시 분석 중…' : '입력 내용으로 다시 분석'}</button></div>
    </>}
  </section>
}
