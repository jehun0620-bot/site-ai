import { expect, test } from '@playwright/test'

const ADDRESS = '서울특별시 강남구 개포동 12-2'
const PNU = '1168010300100120002'

test.describe('실제 Backend 연동 대상지 현황 E2E', () => {
  test('검증된 필지의 SITE facts를 Backend 응답과 동일하게 표시한다', async ({ page }) => {
    await page.goto('/')

    await page.getByLabel('지번주소').fill(ADDRESS)
    await page.getByRole('button', { name: '필지 찾기' }).click()
    await expect(page.getByLabel('필지 후보 목록')).toBeVisible()
    await expect(page.getByRole('status')).toContainText('개의 필지 후보를 찾았습니다.')

    const candidate = page
      .getByLabel('필지 후보 목록')
      .locator('.candidate-card')
      .filter({ hasText: ADDRESS })
      .first()

    await expect(candidate).toBeVisible()
    await candidate.click()

    await expect(page.getByText('필지 확인 완료', { exact: true })).toBeVisible()
    await expect(page.getByText('VERIFIED', { exact: true })).toBeVisible()

    const verifiedPanel = page.locator('.verification-panel')
    await expect(verifiedPanel.locator('dt', { hasText: 'PNU' }).locator('..').locator('dd')).toHaveText(PNU)

    const analysisResponsePromise = page.waitForResponse(
      (response) =>
        response.url().includes('/v1/site-analysis/selected-candidate')
        && response.request().method() === 'POST',
    )

    await page.getByRole('button', { name: '이 필지 분석' }).click()

    const analysisResponse = await analysisResponsePromise
    expect(analysisResponse.ok()).toBeTruthy()

    const body = await analysisResponse.json()
    expect(body.schema_version).toBe('SITE_ANALYSIS_API_V1')
    expect(body.status).toBe('READY')
    expect(body.site?.pnu).toBe(PNU)
    expect(body.site_facts).toBeTruthy()

    await expect(page.getByText('SITE 분석 결과', { exact: true })).toBeVisible({ timeout: 120_000 })
    await expect(page.locator('.analysis-ready-badge')).toHaveText('분석 완료')

    const factsSection = page.locator('#analysis-basic')
    await expect(factsSection.getByRole('heading', { name: '대상지 현황' })).toBeVisible()

    const land = body.site_facts.land
    const buildings = body.site_facts.buildings
    const sources = body.site_facts.sources

    await expect(factsSection.locator('dt', { hasText: '지목' }).locator('..').locator('dd')).toHaveText(String(land.land_category))
    await expect(factsSection.locator('dt', { hasText: '대지면적' }).locator('..').locator('dd')).toHaveText(
      land.land_area === null ? '정보 없음' : `${Number(land.land_area).toLocaleString('ko-KR')}㎡`,
    )
    await expect(factsSection.locator('dt', { hasText: '용도지역' }).locator('..').locator('dd')).toHaveText(String(land.zoning))
    await expect(factsSection.locator('dt', { hasText: '건축물' }).first().locator('..').locator('dd')).toHaveText(
      `${buildings.count}건`,
    )

    if (buildings.items.length > 0) {
      await expect(factsSection.locator('.building-facts-disclosure > summary')).toHaveText(
        `건축물 상세 ${buildings.items.length}건 보기`,
      )
    } else {
      await expect(factsSection.getByText('현재 조회된 건축물대장 항목이 없습니다.', { exact: true })).toBeVisible()
    }

    await expect(factsSection.locator('dt', { hasText: '토지' }).locator('..').locator('dd')).toHaveText(
      sources.land === 'VWORLD_LAND_CHARACTERISTICS' ? 'VWorld 토지특성정보' : String(sources.land ?? '정보 없음'),
    )
    await expect(factsSection.locator('dt', { hasText: '건축물' }).last().locator('..').locator('dd')).toHaveText(
      sources.buildings === 'BUILDING_HUB_TITLE' ? '건축HUB 표제부' : String(sources.buildings ?? '정보 없음'),
    )
  })
})
