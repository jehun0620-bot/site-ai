import RuleDetails from './RuleDetails'
import type {
  SiteAnalysisRuleDetail,
  SiteAnalysisRuleEvaluation,
} from '../types/siteAnalysis'

interface RuleEvaluationSectionProps {
  evaluation: SiteAnalysisRuleEvaluation
  previousEvaluation?: SiteAnalysisRuleEvaluation
  ruleDetails: SiteAnalysisRuleDetail[]
}

function renderRuleDelta(current: number, previous: number | undefined) {
  if (previous === undefined) return null
  const delta = current - previous
  return (
    <small className={delta === 0 ? 'rule-delta rule-delta-zero' : 'rule-delta'}>
      {delta > 0 ? `+${delta}` : String(delta)}
    </small>
  )
}

export default function RuleEvaluationSection({
  evaluation,
  previousEvaluation,
  ruleDetails,
}: RuleEvaluationSectionProps) {
  return (
    <section className="analysis-detail-section" id="analysis-rules">
      <div className="rule-summary-heading">
        <h2>법규 평가 집계</h2>
        <span>
          전체 {evaluation.total}개
          {renderRuleDelta(evaluation.total, previousEvaluation?.total)}
        </span>
      </div>
      <p className="analysis-note">
        Backend Rule Engine의 집계 결과이며 Frontend에서 적용 여부를 다시 판단하지 않습니다.
      </p>
      <div className="rule-summary-grid">
        <article>
          <span>적용</span>
          <strong>{evaluation.applicable}</strong>
          {renderRuleDelta(evaluation.applicable, previousEvaluation?.applicable)}
        </article>
        <article>
          <span>비적용</span>
          <strong>{evaluation.not_applicable}</strong>
          {renderRuleDelta(evaluation.not_applicable, previousEvaluation?.not_applicable)}
        </article>
        <article>
          <span>조건부</span>
          <strong>{evaluation.conditional}</strong>
          {renderRuleDelta(evaluation.conditional, previousEvaluation?.conditional)}
        </article>
        <article className="rule-unknown">
          <span>확인 필요</span>
          <strong>{evaluation.unknown}</strong>
          {renderRuleDelta(evaluation.unknown, previousEvaluation?.unknown)}
          <small>현재 정보로 확정 불가</small>
        </article>
      </div>
      {previousEvaluation && (
        <p className="rule-delta-explanation">
          변화량은 직전 Backend 분석 결과와 비교한 조항 수 차이입니다.
        </p>
      )}
      <p className="unknown-explanation">
        확인 필요는 오류나 비적용이 아닙니다. 현재 정보만으로 적용 여부를 확정할 수 없는 규칙입니다.
      </p>
      <RuleDetails items={ruleDetails} />
    </section>
  )
}
