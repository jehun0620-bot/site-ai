import type {
  SiteAnalysisRuleApplicability,
  SiteAnalysisRuleDetail,
} from '../types/siteAnalysis'

type Props = {
  items: SiteAnalysisRuleDetail[]
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '정보 없음'
  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return String(value)
  }
  return '상세 확인 필요'
}

function displayRuleApplicability(
  value: SiteAnalysisRuleApplicability,
): string {
  if (value === 'APPLICABLE') return '적용'
  if (value === 'NOT_APPLICABLE') return '비적용'
  if (value === 'CONDITIONAL') return '조건부'
  return '확인 필요'
}

function displayRuleLocation(rule: SiteAnalysisRuleDetail): string {
  return (
    [rule.paragraph, rule.item, rule.subitem].filter(Boolean).join(' · ') ||
    '세부 위치 정보 없음'
  )
}

function RuleDetailItem({ rule }: { rule: SiteAnalysisRuleDetail }) {
  return (
    <li className="rule-detail-item">
      <div className="rule-detail-heading">
        <div>
          <strong>{displayValue(rule.law_name)}</strong>
          <span>{displayValue(rule.rule_title)}</span>
        </div>
        <span
          className={`rule-status rule-status-${rule.applicability
            .toLowerCase()
            .replace('_', '-')}`}
        >
          {displayRuleApplicability(rule.applicability)}
        </span>
      </div>

      <div className="rule-detail-meta">
        <span>{displayRuleLocation(rule)}</span>
        {rule.category && <span>{rule.category}</span>}
      </div>

      <dl className="rule-detail-facts">
        <div>
          <dt>판정 이유</dt>
          <dd>{displayValue(rule.reason)}</dd>
        </div>

        {rule.required_inputs.length > 0 && (
          <div>
            <dt>추가 입력</dt>
            <dd>{rule.required_inputs.join(', ')}</dd>
          </div>
        )}

        {rule.unresolved_conditions.length > 0 && (
          <div>
            <dt>미확정 조건</dt>
            <dd>{rule.unresolved_conditions.join(', ')}</dd>
          </div>
        )}

        {rule.blocking_conditions.length > 0 && (
          <div>
            <dt>비적용 조건</dt>
            <dd>{rule.blocking_conditions.join(', ')}</dd>
          </div>
        )}
      </dl>

      {rule.text && (
        <details className="rule-text-disclosure">
          <summary>규정 내용 보기</summary>
          <p>{rule.text}</p>
        </details>
      )}
    </li>
  )
}

function RuleDetailGroup({
  items,
  applicability,
  label,
  open = false,
}: {
  items: SiteAnalysisRuleDetail[]
  applicability: SiteAnalysisRuleApplicability
  label: string
  open?: boolean
}) {
  const filteredItems = items.filter(
    (item) => item.applicability === applicability,
  )

  return (
    <details
      className={`rule-detail-group rule-detail-group-${applicability
        .toLowerCase()
        .replace('_', '-')}`}
      open={open}
    >
      <summary>
        <span>{label}</span>
        <strong>{filteredItems.length}개</strong>
      </summary>

      {filteredItems.length === 0 ? (
        <p className="analysis-empty">해당 상태의 규정이 없습니다.</p>
      ) : (
        <ul>
          {filteredItems.map((rule) => (
            <RuleDetailItem
              key={`rule-${rule.clause_index}-${rule.applicability}`}
              rule={rule}
            />
          ))}
        </ul>
      )}
    </details>
  )
}

export default function RuleDetails({ items }: Props) {
  return (
    <div className="rule-detail-groups" aria-label="법규 상세 결과">
      <RuleDetailGroup
        items={items}
        applicability="UNKNOWN"
        label="확인 필요"
        open
      />
      <RuleDetailGroup
        items={items}
        applicability="CONDITIONAL"
        label="조건부"
      />
      <RuleDetailGroup
        items={items}
        applicability="APPLICABLE"
        label="적용"
      />
      <RuleDetailGroup
        items={items}
        applicability="NOT_APPLICABLE"
        label="비적용"
      />
    </div>
  )
}
