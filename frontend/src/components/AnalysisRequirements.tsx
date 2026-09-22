import { useState } from 'react'
import type {
  SiteAnalysisInputProfile,
  SiteAnalysisInputState,
  SiteAnalysisRequirement,
  SiteAnalysisRequirements,
  SiteAnalysisState,
} from '../types/siteAnalysis'

const INPUT_OPTIONS: Array<{
  state: Exclude<SiteAnalysisInputState, 'UNSET'>
  label: string
}> = [
  { state: 'TRUE', label: '해당함' },
  { state: 'FALSE', label: '해당하지 않음' },
  { state: 'UNKNOWN', label: '잘 모르겠음' },
]

type ProfileType = 'project' | 'procedure'

type Props = {
  requirements: SiteAnalysisRequirements
  projectProfile: SiteAnalysisInputProfile
  procedureProfile: SiteAnalysisInputProfile
  analysisState: SiteAnalysisState
  onRequirementChange: (
    profileType: ProfileType,
    name: string,
    nextState: Exclude<SiteAnalysisInputState, 'UNSET'>,
  ) => void
  onReanalysis: () => void
}

function RequirementItem({
  item,
  profileType,
  profile,
  analysisState,
  onRequirementChange,
}: {
  item: SiteAnalysisRequirement
  profileType: ProfileType
  profile: SiteAnalysisInputProfile
  analysisState: SiteAnalysisState
  onRequirementChange: Props['onRequirementChange']
}) {
  const selected = profile[item.name]

  return (
    <li className="requirement-item">
      <div className="requirement-item-copy">
        <div className="requirement-item-heading">
          <strong>{item.name}</strong>
          <span
            className={
              selected
                ? 'requirement-item-status requirement-item-status-complete'
                : 'requirement-item-status'
            }
          >
            {selected ? '입력 완료' : '미입력'}
          </span>
        </div>
        <small>
          관련 법규 {item.affected_clause_count}개 조항의 판단에 필요한 정보
        </small>
      </div>

      <div
        className="requirement-options"
        role="group"
        aria-label={`${item.name} 선택`}
      >
        {INPUT_OPTIONS.map((option) => (
          <button
            key={option.state}
            type="button"
            className={
              selected === option.state
                ? 'requirement-option requirement-option-selected'
                : 'requirement-option'
            }
            aria-pressed={selected === option.state}
            onClick={() =>
              onRequirementChange(profileType, item.name, option.state)
            }
            disabled={analysisState === 'ANALYZING'}
          >
            {option.label}
          </button>
        ))}
      </div>
    </li>
  )
}

export default function AnalysisRequirements({
  requirements,
  projectProfile,
  procedureProfile,
  analysisState,
  onRequirementChange,
  onReanalysis,
}: Props) {
  const [projectOpen, setProjectOpen] = useState(true)
  const [procedureOpen, setProcedureOpen] = useState(true)

  const selectedProjectCount = Object.keys(projectProfile).length
  const selectedProcedureCount = Object.keys(procedureProfile).length
  const selectedCount = selectedProjectCount + selectedProcedureCount
  const remainingProjectCount = Math.max(
    requirements.project_count - selectedProjectCount,
    0,
  )
  const remainingProcedureCount = Math.max(
    requirements.procedure_count - selectedProcedureCount,
    0,
  )
  const totalCount = requirements.project_count + requirements.procedure_count
  const remainingCount = Math.max(totalCount - selectedCount, 0)

  return (
    <section className="analysis-detail-section" id="analysis-requirements">
      <h2>추가 입력 필요사항</h2>

      {!requirements.requires_additional_input ? (
        <p className="analysis-empty">
          현재 응답 기준 추가 입력 항목이 없습니다.
        </p>
      ) : (
        <>
          <div
            className="requirement-progress"
            aria-label="추가 입력 진행상태"
          >
            <div>
              <span>사업 정보</span>
              <strong>
                {requirements.project_count}개 중 {selectedProjectCount}개 입력
              </strong>
              <small>
                {remainingProjectCount === 0
                  ? '입력 완료'
                  : `${remainingProjectCount}개 미입력`}
              </small>
            </div>

            <div>
              <span>절차 정보</span>
              <strong>
                {requirements.procedure_count}개 중 {selectedProcedureCount}개 입력
              </strong>
              <small>
                {remainingProcedureCount === 0
                  ? '입력 완료'
                  : `${remainingProcedureCount}개 미입력`}
              </small>
            </div>
          </div>

          <div
            className={`requirement-columns${
              projectOpen === procedureOpen
                ? ''
                : projectOpen
                  ? ' requirement-columns-project-open'
                  : ' requirement-columns-procedure-open'
            }`}
          >
            <details
              className="requirement-group"
              open={projectOpen}
              onToggle={(event) => setProjectOpen(event.currentTarget.open)}
            >
              <summary>
                <span>사업 정보</span>
                <strong>{requirements.project_count}개</strong>
                <small>각 항목의 현재 상황을 선택해 주세요.</small>
              </summary>
              <ul>
                {requirements.project.map((item) => (
                  <RequirementItem
                    key={`project-${item.name}`}
                    item={item}
                    profileType="project"
                    profile={projectProfile}
                    analysisState={analysisState}
                    onRequirementChange={onRequirementChange}
                  />
                ))}
              </ul>
            </details>

            <details
              className="requirement-group"
              open={procedureOpen}
              onToggle={(event) => setProcedureOpen(event.currentTarget.open)}
            >
              <summary>
                <span>절차 정보</span>
                <strong>{requirements.procedure_count}개</strong>
                <small>각 항목의 현재 상황을 선택해 주세요.</small>
              </summary>
              <ul>
                {requirements.procedure.map((item) => (
                  <RequirementItem
                    key={`procedure-${item.name}`}
                    item={item}
                    profileType="procedure"
                    profile={procedureProfile}
                    analysisState={analysisState}
                    onRequirementChange={onRequirementChange}
                  />
                ))}
              </ul>
            </details>
          </div>

          <div className="requirement-reanalysis">
            <span>
              {selectedCount === 0
                ? `전체 ${totalCount}개 중 선택한 추가 정보가 없습니다.`
                : remainingCount === 0
                  ? `전체 ${totalCount}개 입력 완료`
                  : `전체 ${totalCount}개 중 ${selectedCount}개 입력 · ${remainingCount}개 미입력`}
            </span>
            <button
              type="button"
              onClick={onReanalysis}
              disabled={selectedCount === 0 || analysisState === 'ANALYZING'}
            >
              {analysisState === 'ANALYZING'
                ? '다시 분석 중…'
                : '입력 내용으로 다시 분석'}
            </button>
          </div>
        </>
      )}
    </section>
  )
}
