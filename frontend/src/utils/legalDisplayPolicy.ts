/**
 * Presentation-only protection against a known, unverified internal condition.
 * Descriptive review messages here are NOT official legal area/zone names.
 * This function does not authenticate other names, legal provisions, or sources.
 * Never use it to construct input keys, rule identities, API requests, or decisions.
 */
const INTERNAL_HISTORY_CONDITION = '도시지역편입해제구역'
const HISTORY_REVIEW_MESSAGE = '과거 토지이용계획 변경 이력 확인 필요'

export function containsUnverifiedInternalCondition(value: string): boolean {
  return value.includes(INTERNAL_HISTORY_CONDITION)
}

/** Keep non-target text unchanged; no legal meaning is inferred. */
export function displayLegalReviewText(value: string): string {
  return value.replaceAll(INTERNAL_HISTORY_CONDITION, HISTORY_REVIEW_MESSAGE)
}

/** Never rewrite quoted regulation text; withhold suspect text for source review. */
export function displayLegalProvisionText(value: string): string {
  return containsUnverifiedInternalCondition(value)
    ? '규정 원문은 공식 출처 확인 후 표시합니다.'
    : value
}

/** Public status description only; source state remains untouched. */
export function displayExternalReviewStatus(value: unknown): string {
  if (value === 'UNKNOWN' || value === 'HISTORICAL_SOURCE_PENDING') return '확인 필요'
  if (typeof value === 'string' && /^[A-Z][A-Z0-9_]*$/.test(value)) return '상태 확인 필요'
  if (typeof value === 'string') return displayLegalReviewText(value)
  return '정보 없음'
}
