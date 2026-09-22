import { expect, test, type Page } from '@playwright/test'

const MOBILE_VIEWPORT = { width: 390, height: 844 }
const DEFAULT_ADDRESS = '서울특별시 강남구 개포로109길 21'

async function selectVerifiedCandidate(page: Page) {
  const cards = page.getByLabel('필지 후보 목록').locator('.candidate-card')
  const count = await cards.count()
  expect(count).toBeGreaterThan(0)

  for (let index = 0; index < count; index += 1) {
    await cards.nth(index).click()

    const verifiedHeading = page.getByText('필지 확인 완료', { exact: true })
    const rejectedHeading = page.getByText('필지 확인 실패', { exact: true })
    await expect(verifiedHeading.or(rejectedHeading)).toBeVisible()

    if (await verifiedHeading.isVisible()) {
      await expect(page.getByText('VERIFIED', { exact: true })).toBeVisible()
      return
    }
  }

  throw new Error('모바일 검증에 사용할 VERIFIED 필지 후보가 없습니다.')
}

test.describe('Mobile responsive Backend-connected validation', () => {
  test.use({ viewport: MOBILE_VIEWPORT })

  test('검색부터 재분석까지 모바일 레이아웃과 핵심 흐름을 검증한다', async ({ page }) => {
    await page.goto('/')

    await expect(page.locator('body')).toHaveCSS('min-width', '320px')
    await page.getByLabel('주소', { exact: true }).fill(DEFAULT_ADDRESS)
    await page.getByRole('button', { name: '필지 찾기' }).click()

    await expect(page.getByLabel('필지 후보 목록')).toBeVisible()
    await expect(page.getByRole('status')).toContainText('개의 필지 후보를 찾았습니다.')
    await selectVerifiedCandidate(page)

    const verifiedPanel = page.locator('.verification-panel')
    const verifiedPnu = (await verifiedPanel.locator('dd').nth(1).textContent())?.trim() ?? ''
    expect(verifiedPnu).toMatch(/^\d{19}$/)

    await page.getByRole('button', { name: '이 필지 분석' }).click()
    await expect(page.getByText('SITE 분석 결과', { exact: true })).toBeVisible({ timeout: 120_000 })
    await expect(page.locator('.analysis-ready-badge')).toHaveText('분석 완료')

    const analysisPanel = page.locator('.analysis-panel')
    await expect(analysisPanel.locator('dt', { hasText: 'PNU' }).locator('..').locator('dd')).toHaveText(verifiedPnu)
    await expect(page.locator('.analysis-section-nav')).toBeVisible()

    await expect
      .poll(async () => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth))
      .toBe(true)

    const detailColumns = await page.locator('.analysis-details').evaluate(
      (element) => getComputedStyle(element).gridTemplateColumns.split(' ').filter(Boolean).length,
    )
    expect(detailColumns).toBe(1)

    const siteFactsColumns = await page.locator('.site-facts-grid').evaluate(
      (element) => getComputedStyle(element).gridTemplateColumns.split(' ').filter(Boolean).length,
    )
    expect(siteFactsColumns).toBe(1)

    const searchDirection = await page.locator('.search-row').evaluate(
      (element) => getComputedStyle(element).flexDirection,
    )
    expect(searchDirection).toBe('column')

    await page.locator('.analysis-section-nav a[href="#analysis-requirements"]').click()
    await expect(page.locator('#analysis-requirements')).toBeInViewport()

    const requirementItems = page.locator('.requirement-item')
    const requirementCount = await requirementItems.count()
    expect(requirementCount).toBeGreaterThan(0)

    await requirementItems.first().getByRole('button', { name: '해당함', exact: true }).click()
    await expect(requirementItems.first().locator('.requirement-option-selected')).toHaveText('해당함')

    await page.getByRole('button', { name: '입력 내용으로 다시 분석' }).click()
    await expect(page.locator('.analysis-ready-badge')).toHaveText('분석 완료', { timeout: 120_000 })
    await expect(analysisPanel.locator('dt', { hasText: 'PNU' }).locator('..').locator('dd')).toHaveText(verifiedPnu)

    await expect
      .poll(async () => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth))
      .toBe(true)
  })
})
