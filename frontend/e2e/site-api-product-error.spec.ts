import { expect, test, type Page } from '@playwright/test'

const CANDIDATE = {
  candidate_pnu: '1168010300100120002',
  parcel_address: '서울특별시 강남구 개포동 12-2',
  road_address: '서울특별시 강남구 개포로109길 69',
  building_name: '개포자이',
  x: 127.07662495509604,
  y: 37.49629354642009,
  crs: 'EPSG:4326',
}

function productError(
  code: string,
  category: 'PARCEL' | 'PROVIDER' | 'ANALYSIS' | 'INTERNAL',
  message: string,
  retryable: boolean,
) {
  return {
    detail: {
      schema_version: 'SITE_API_ERROR_V1',
      code,
      category,
      message,
      retryable,
    },
  }
}

async function mockCandidateSearchReady(page: Page) {
  await page.route('**/v1/parcel-candidates/address', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        schema_version: 'PARCEL_CANDIDATE_SEARCH_V1',
        status: 'READY',
        query: '서울특별시 강남구 개포동 12',
        count: 1,
        candidates: [CANDIDATE],
      }),
    })
  })
}

async function mockParcelConfirmationReady(page: Page) {
  await page.route('**/v1/parcel-candidates/confirm', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        schema_version: 'PARCEL_CONFIRMATION_V1',
        status: 'READY',
        parcel: {
          pnu: CANDIDATE.candidate_pnu,
          sigungu_cd: '11680',
          bjdong_cd: '10300',
          plat_gb_cd: '0',
          bun: '0012',
          ji: '0002',
          x: CANDIDATE.x,
          y: CANDIDATE.y,
          crs: CANDIDATE.crs,
        },
        verification: {
          status: 'VERIFIED',
          resolution: 'SELECTED_PARCEL_CANDIDATE_VERIFIED',
        },
        geometry: {
          type: 'Polygon',
          coordinates: [],
        },
      }),
    })
  })
}

async function searchAndSelect(page: Page) {
  await page.goto('/')
  await page.getByLabel('지번주소').fill('서울특별시 강남구 개포동 12')
  await page.getByRole('button', { name: '필지 찾기' }).click()
  await expect(page.getByLabel('필지 후보 목록')).toBeVisible()
  await page.locator('.candidate-card').first().click()
}

test.describe('SITE_API_ERROR_V1 Frontend focused validation', () => {
  test('candidate search provider error의 category와 message를 PC 사용자 메시지에 반영한다', async ({ page }) => {
    await page.route('**/v1/parcel-candidates/address', async (route) => {
      await route.fulfill({
        status: 502,
        contentType: 'application/json',
        body: JSON.stringify(
          productError(
            'CANDIDATE_SEARCH_FAILED',
            'PROVIDER',
            '테스트용 후보 검색 제공자 오류입니다.',
            true,
          ),
        ),
      })
    })

    await page.goto('/')
    await page.getByLabel('지번주소').fill('서울특별시 강남구 개포동 12')
    await page.getByRole('button', { name: '필지 찾기' }).click()

    await expect(page.locator('.status')).toHaveText(
      '외부 데이터 조회에 실패했습니다. 테스트용 후보 검색 제공자 오류입니다.',
    )
  })

  test('parcel confirmation error의 code와 message를 PC 사용자 메시지에 반영한다', async ({ page }) => {
    await mockCandidateSearchReady(page)
    await page.route('**/v1/parcel-candidates/confirm', async (route) => {
      await route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify(
          productError(
            'PARCEL_VERIFICATION_FAILED',
            'PARCEL',
            '테스트용 필지 검증 오류입니다.',
            false,
          ),
        ),
      })
    })

    await searchAndSelect(page)

    await expect(page.getByText('필지 확인 실패', { exact: true })).toBeVisible()
    await expect(page.locator('.verification-panel')).toContainText(
      '테스트용 필지 검증 오류입니다. 다른 필지를 선택하거나 다시 검색해 주세요.',
    )
  })

  test('SITE analysis provider error의 category와 message를 PC 사용자 메시지에 반영한다', async ({ page }) => {
    await mockCandidateSearchReady(page)
    await mockParcelConfirmationReady(page)
    await page.route('**/v1/site-analysis/selected-candidate', async (route) => {
      await route.fulfill({
        status: 502,
        contentType: 'application/json',
        body: JSON.stringify(
          productError(
            'BUILDING_PROVIDER_FAILED',
            'PROVIDER',
            '테스트용 건축물 제공자 오류입니다.',
            true,
          ),
        ),
      })
    })

    await searchAndSelect(page)
    await expect(page.getByText('필지 확인 완료', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: '이 필지 분석' }).click()

    await expect(page.getByText('SITE 분석 실패', { exact: true })).toBeVisible()
    await expect(page.locator('.analysis-panel')).toContainText(
      '외부 데이터 조회에 실패해 SITE 분석을 완료하지 못했습니다. 테스트용 건축물 제공자 오류입니다.',
    )
  })
})
