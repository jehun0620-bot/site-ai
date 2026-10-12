import { expect, test } from '@playwright/test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer, type ViteDevServer } from 'vite'
import type { SiteAnalysisRequirement, SiteAnalysisRuleDetail } from '../src/types/siteAnalysis'
import {
  containsUnverifiedInternalCondition,
  displayExternalReviewStatus,
  displayLegalProvisionText,
  displayLegalReviewText,
} from '../src/utils/legalDisplayPolicy'

const INTERNAL = '도시지역편입해제구역'
const REVIEW = '과거 토지이용계획 변경 이력 확인 필요'


// Playwright's test transform may produce __pw_type JSX descriptors for TSX
// imports. Vite SSR transforms app components to actual React elements.
// The Vite server runs in middleware mode: no browser/backend server needed.
let viteServer: ViteDevServer | undefined

async function loadReactComponent<T>(moduleName: string): Promise<T> {
  if (!viteServer) {
    viteServer = await createServer({
      root: process.cwd(),
      server: { middlewareMode: true },
      appType: 'custom',
    })
  }
  const module = await viteServer.ssrLoadModule(`/src/components/${moduleName}.tsx`)
  if (typeof module.default !== 'function') {
    throw new Error(`Invalid React component export: ${moduleName}`)
  }
  return module.default as T
}

test.afterAll(async () => {
  await viteServer?.close()
})

test('내부 조건명은 법정 구역명으로 승격되지 않고 확인 안내로만 표시된다', () => {
  expect(containsUnverifiedInternalCondition(INTERNAL)).toBe(true)
  expect(containsUnverifiedInternalCondition('지구단위계획')).toBe(false)
  expect(displayLegalReviewText(INTERNAL)).toBe(REVIEW)
  expect(displayLegalReviewText(`필수조건 미확정: ${INTERNAL}`)).toBe(`필수조건 미확정: ${REVIEW}`)
  expect(displayLegalReviewText(`${INTERNAL} / ${INTERNAL}`)).toBe(`${REVIEW} / ${REVIEW}`)
  expect(displayLegalReviewText('지구단위계획')).toBe('지구단위계획')
  expect(displayLegalProvisionText(`규정 텍스트 ${INTERNAL}`)).toBe('규정 원문은 공식 출처 확인 후 표시합니다.')
  expect(displayLegalProvisionText('가상 원문')).toBe('가상 원문')
  expect(displayExternalReviewStatus('UNKNOWN')).toBe('확인 필요')
  expect(displayExternalReviewStatus('HISTORICAL_SOURCE_PENDING')).toBe('확인 필요')
  expect(displayExternalReviewStatus('UNRECOGNIZED_INTERNAL_STATUS')).toBe('상태 확인 필요')
})

test('법규 상세는 원본 UNKNOWN 판정을 바꾸지 않고 내부명칭을 화면에서 배제한다', async () => {
  const RuleDetails = await loadReactComponent<typeof import('../src/components/RuleDetails').default>('RuleDetails')
  const item: SiteAnalysisRuleDetail = Object.freeze({
    clause_index: 47,
    law_name: '국토의 계획 및 이용에 관한 법률 시행령',
    rule_title: '가상 법규 적용 확인',
    paragraph: INTERNAL,
    item: null,
    subitem: null,
    category: INTERNAL,
    applicability: 'UNKNOWN',
    reason: `필수조건 미확정: ${INTERNAL}`,
    text: `가상 문장 ${INTERNAL}`,
    effect_targets: [],
    required_inputs: [INTERNAL],
    unresolved_conditions: [INTERNAL],
    blocking_conditions: [INTERNAL],
    numeric_effect: null,
  })
  const html = renderToStaticMarkup(createElement(RuleDetails, { items: [item] }))
  expect(html).not.toContain(INTERNAL)
  expect(html).toContain(REVIEW)
  expect(html).toContain('미확정 조건')
  expect(html).toContain('규정 원문은 공식 출처 확인 후 표시합니다.')
  expect(html).not.toContain(`가상 문장 ${REVIEW}`)
  expect(html).toContain('rule-status-unknown')
  expect(item.applicability).toBe('UNKNOWN')
  expect(item.unresolved_conditions).toEqual([INTERNAL])
})

test('외부 이력은 내부 코드 없이 미확정 상태로 표시되고 원본은 변경되지 않는다', async () => {
  const ExternalDependenciesSection = await loadReactComponent<typeof import('../src/components/ExternalDependenciesSection').default>('ExternalDependenciesSection')
  const dependency = Object.freeze({
    category: 'SITE_HISTORY',
    condition: INTERNAL,
    status: 'UNKNOWN',
    blocking_analysis: false,
  })
  const html = renderToStaticMarkup(createElement(ExternalDependenciesSection, {
    dependencies: { count: 1, items: [dependency] },
  }))
  expect(html).not.toContain(INTERNAL)
  expect(html).not.toContain('SITE_HISTORY')
  expect(html).not.toContain('UNKNOWN')
  expect(html).toContain(REVIEW)
  expect(html).toContain('과거 이력 확인')
  expect(html).toContain('확인 필요')
  expect(html).toContain('계속 가능')
  expect(dependency.condition).toBe(INTERNAL)
  expect(dependency.status).toBe('UNKNOWN')
})

test('추가 입력은 표시명만 변환하고 원본 키와 상태는 유지한다', async () => {
  const AnalysisRequirements = await loadReactComponent<typeof import('../src/components/AnalysisRequirements').default>('AnalysisRequirements')
  const requirement: SiteAnalysisRequirement = Object.freeze({
    name: INTERNAL, affected_clause_count: 3, state: 'UNKNOWN',
  })
  const changes: string[] = []
  const html = renderToStaticMarkup(createElement(AnalysisRequirements, {
    requirements: {
      project: [requirement], procedure: [], building_use: [], state_facts: [], numeric_facts: [],
      project_count: 1, procedure_count: 0, building_use_count: 0,
      state_fact_count: 0, numeric_fact_count: 0, requires_additional_input: true,
    },
    buildingUseCatalog: [], buildingUseCatalogError: '',
    projectProfile: { [INTERNAL]: 'UNKNOWN' }, procedureProfile: {},
    buildingUseName: '', numericFacts: {}, stateFacts: {},
    analysisState: 'ANALYSIS_READY',
    onRequirementChange: (_type, name) => { changes.push(name) },
    onBuildingUseChange: () => {},
    onStateFactChange: () => {},
    onNumericFactChange: () => {},
    onNumericFactUndecided: () => {},
    onReanalysis: () => {},
  }))
  expect(html).not.toContain(INTERNAL)
  expect(html).toContain(REVIEW)
  expect(html).toContain(`${REVIEW} 선택`)
  expect(html).toContain('입력 완료')
  expect(requirement.name).toBe(INTERNAL)
  expect(requirement.state).toBe('UNKNOWN')
  expect(changes).toEqual([]) // Rendering is read-only; event handlers remain in the component.
})
