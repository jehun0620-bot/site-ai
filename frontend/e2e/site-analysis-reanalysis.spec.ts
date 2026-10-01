import { expect, test, type Page } from '@playwright/test'

const DEFAULT_ADDRESS_SEEDS = ['서울특별시 강남구 개포동 12', '서울특별시 강남구 개포로109길 21', '서울특별시 동작구 동작동 산 29-3']
const INPUT_LABELS = ['해당함', '해당하지 않음', '잘 모르겠음'] as const

function parseAddressSeeds(): string[] {
  const raw = process.env.SITE_AI_E2E_ADDRESSES
  if (!raw) return DEFAULT_ADDRESS_SEEDS
  const values = raw.split('|').map((value) => value.trim()).filter(Boolean)
  return values.length > 0 ? values : DEFAULT_ADDRESS_SEEDS
}

function parseSeed(): number {
  const raw = Number(process.env.SITE_AI_E2E_RANDOM_SEED ?? '20260918')
  return Number.isFinite(raw) ? Math.trunc(raw) >>> 0 : 20260918
}

function createRandom(seed: number) {
  let state = seed >>> 0
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0
    return state / 0x100000000
  }
}

async function search(page: Page, address: string) {
  await page.getByLabel('주소', { exact: true }).fill(address)
  await page.getByRole('button', { name: /필지 찾기|다른 필지 찾기/ }).click()
  await expect(page.getByLabel('필지 후보 목록')).toBeVisible()
  await expect(page.getByRole('status')).toContainText('개의 필지 후보를 찾았습니다.')
}

test.describe('실제 Backend 연동 필지 재분석 E2E', () => {
  test('여러 주소/필지에서 추가 입력 재분석과 필지 전환 상태 격리를 검증한다', async ({ page }) => {
    const addresses = parseAddressSeeds()
    const randomSeed = parseSeed()
    const random = createRandom(randomSeed)

    test.info().annotations.push({ type: 'random-seed', description: String(randomSeed) })
    test.info().annotations.push({ type: 'address-seeds', description: addresses.join(' | ') })

    await page.goto('/')

    let previousPnu: string | null = null
    let exercisedParcels = 0

    for (const address of addresses) {
      await search(page, address)

      const cards = page.getByLabel('필지 후보 목록').locator('.candidate-card')
      const candidateCount = await cards.count()
      expect(candidateCount, `검색 결과가 없습니다: ${address}`).toBeGreaterThan(0)

      const maxVerifiedParcelsPerAddress = Math.min(candidateCount, 2)
      const startIndex = Math.floor(random() * candidateCount)
      const candidateIndexes = Array.from({ length: candidateCount }, (_, offset) => (startIndex + offset) % candidateCount)
      let verifiedParcelsForAddress = 0

      for (const index of candidateIndexes) {
        await cards.nth(index).click()

        const verifiedHeading = page.getByText('필지 확인 완료', { exact: true })
        const rejectedHeading = page.getByText('필지 확인 실패', { exact: true })
        await expect(verifiedHeading.or(rejectedHeading)).toBeVisible()

        if (await rejectedHeading.isVisible()) {
          continue
        }

        await expect(page.getByText('VERIFIED', { exact: true })).toBeVisible()
        verifiedParcelsForAddress += 1

        const verifiedPanel = page.locator('.verification-panel')
        const pnu = (await verifiedPanel.locator('dd').nth(1).textContent())?.trim() ?? ''
        expect(pnu).toMatch(/^\d{19}$/)

        await page.getByRole('button', { name: '이 필지 분석' }).click()
        await expect(page.getByText('SITE 분석 결과', { exact: true })).toBeVisible({ timeout: 120_000 })
        await expect(page.locator('.analysis-ready-badge')).toHaveText('분석 완료')

        const analysisPanel = page.locator('.analysis-panel')
        await expect(analysisPanel.locator('dt', { hasText: 'PNU' }).locator('..').locator('dd')).toHaveText(pnu)
        await expect(analysisPanel.locator('dt', { hasText: '토지 조회 상태' }).locator('..').locator('dd')).toHaveText('정상 조회')

        for (const label of ['지구단위계획', '개발진흥지구', '취락지구', '방재지구']) {
          const value = analysisPanel.locator('dt', { hasText: label }).locator('..').locator('dd')
          await expect(value).toHaveText(/^(해당|비해당|확인 필요)$/)
        }

        const buildingDisclosure = analysisPanel.locator('.building-facts-disclosure')
        if (await buildingDisclosure.count()) {
          if (!(await buildingDisclosure.evaluate((details) => (details as HTMLDetailsElement).open))) {
            await buildingDisclosure.locator('summary').click()
          }
          await expect(buildingDisclosure).toHaveAttribute('open', '')
          const firstBuilding = buildingDisclosure.locator('.building-facts-list article').first()
          await expect(firstBuilding.locator('dt', { hasText: '관리번호' }).locator('..').locator('dd')).not.toHaveText('정보 없음')
          await expect(firstBuilding.locator('dt', { hasText: '구조' }).locator('..').locator('dd')).toBeVisible()
          await expect(firstBuilding.locator('dt', { hasText: '지붕' }).locator('..').locator('dd')).toBeVisible()
          await expect(firstBuilding.locator('dt', { hasText: '허가일' }).locator('..').locator('dd')).toBeVisible()
        }

        const ruleDetails = analysisPanel.locator('.rule-detail-groups')
        await expect(ruleDetails).toBeVisible()
        const unknownRuleGroup = ruleDetails.locator('.rule-detail-group-unknown')
        await expect(unknownRuleGroup).toBeVisible()
        const unknownRuleCount = Number((await unknownRuleGroup.locator('summary strong').textContent())?.replace(/\D/g, '') ?? '0')
        expect(unknownRuleCount).toBeGreaterThan(0)
        await expect(unknownRuleGroup.locator('.rule-detail-item')).toHaveCount(unknownRuleCount)
        await expect(unknownRuleGroup.locator('.rule-detail-item').first()).toContainText('판정 이유')
        await expect(unknownRuleGroup.locator('.rule-detail-item').first()).toContainText('미확정 조건')

        const requirementItems = page.locator('.requirement-group').filter({ has: page.getByRole('button', { name: '해당함', exact: true }) }).locator('.requirement-item')
        const requirementCount = await requirementItems.count()

        if (requirementCount > 0) {
          const pickCount = Math.min(requirementCount, 3)
          for (let itemIndex = 0; itemIndex < pickCount; itemIndex += 1) {
            const optionLabel = INPUT_LABELS[Math.floor(random() * INPUT_LABELS.length)]
            await requirementItems.nth(itemIndex).getByRole('button', { name: optionLabel, exact: true }).click()
          }

          await expect(page.locator('.requirement-reanalysis')).toContainText(`전체 ${requirementCount}개 중 ${pickCount}개 입력 · ${requirementCount - pickCount}개 미입력`)
          await page.getByRole('button', { name: '입력 내용으로 다시 분석' }).click()

          await expect(page.locator('.analysis-ready-badge')).toHaveText('분석 완료', { timeout: 120_000 })
          await expect(analysisPanel.locator('dt', { hasText: 'PNU' }).locator('..').locator('dd')).toHaveText(pnu)

          const currentRequirementItems = page.locator('.requirement-group').filter({ has: page.getByRole('button', { name: '해당함', exact: true }) }).locator('.requirement-item')
          const currentRequirementCount = await currentRequirementItems.count()
          await expect(page.locator('.requirement-reanalysis')).toContainText(`전체 ${currentRequirementCount}개`)

          if (currentRequirementCount > 0) {
            const firstCurrentItem = currentRequirementItems.first()
            const firstCurrentSelected = firstCurrentItem.locator('.requirement-option-selected')
            if (await firstCurrentSelected.count()) {
              const selectedLabel = (await firstCurrentSelected.textContent())?.trim() ?? ''
              await firstCurrentItem.getByRole('button', { name: selectedLabel, exact: true }).click()
              await expect(firstCurrentItem.locator('.requirement-option-selected')).toHaveCount(0)
              await expect(firstCurrentItem).toContainText('미입력')
            }
          }
        }

        previousPnu = pnu
        exercisedParcels += 1

        if (verifiedParcelsForAddress >= maxVerifiedParcelsPerAddress) break

        await search(page, address)
        if (previousPnu) {
          await expect(page.locator('.requirement-option-selected')).toHaveCount(0)
        }
      }

      expect(verifiedParcelsForAddress, `검증 가능한 필지 후보가 없습니다: ${address}`).toBeGreaterThan(0)
    }


    await search(page, '서울특별시 강남구 개포동 12-6')

    const buildinglessCard = page
      .getByLabel('필지 후보 목록')
      .locator('.candidate-card')
      .filter({ hasText: '서울특별시 강남구 개포동 12-6' })
      .first()
    await expect(buildinglessCard).toBeVisible()
    await buildinglessCard.click()

    await expect(page.getByText('필지 확인 완료', { exact: true })).toBeVisible()
    await expect(page.getByText('VERIFIED', { exact: true })).toBeVisible()

    const buildinglessVerifiedPanel = page.locator('.verification-panel')
    const buildinglessPnu = (await buildinglessVerifiedPanel.locator('dd').nth(1).textContent())?.trim() ?? ''
    expect(buildinglessPnu).toBe('1168010300100120006')

    await page.getByRole('button', { name: '이 필지 분석' }).click()
    await expect(page.getByText('SITE 분석 결과', { exact: true })).toBeVisible({ timeout: 120_000 })
    await expect(page.locator('.analysis-ready-badge')).toHaveText('분석 완료')

    const buildinglessAnalysisPanel = page.locator('.analysis-panel')
    await expect(
      buildinglessAnalysisPanel.locator('dt', { hasText: 'PNU' }).locator('..').locator('dd'),
    ).toHaveText(buildinglessPnu)

    const buildinglessRequirements = page.locator('.requirement-group').filter({ has: page.getByRole('button', { name: '해당함', exact: true }) }).locator('.requirement-item')
    const buildinglessRequirementCount = await buildinglessRequirements.count()
    if (buildinglessRequirementCount > 0) {
      const optionLabel = INPUT_LABELS[Math.floor(random() * INPUT_LABELS.length)]
      await buildinglessRequirements.first().getByRole('button', { name: optionLabel, exact: true }).click()
      await page.getByRole('button', { name: '입력 내용으로 다시 분석' }).click()
      await expect(page.locator('.analysis-ready-badge')).toHaveText('분석 완료', { timeout: 120_000 })
      await expect(
        buildinglessAnalysisPanel.locator('dt', { hasText: 'PNU' }).locator('..').locator('dd'),
      ).toHaveText(buildinglessPnu)
    }

    expect(exercisedParcels).toBeGreaterThan(0)
  })
  test('계획용도 체육관의 관람석 질문과 미정 수치 입력을 Backend requirements로 진행한다', async ({ page }) => {
    await page.goto('/')
    await search(page, '서울특별시 강남구 개포동 12')

    const targetCard = page.getByLabel('필지 후보 목록')
      .locator('.candidate-card')
      .filter({ hasText: '서울특별시 강남구 개포동 12-6' })
      .first()
    await expect(targetCard).toBeVisible()
    await targetCard.click()
    await expect(page.getByText('필지 확인 완료', { exact: true })).toBeVisible()
    await expect(page.getByText('VERIFIED', { exact: true })).toBeVisible()

    await page.getByRole('button', { name: '이 필지 분석' }).click()
    await expect(page.getByText('SITE 분석 결과', { exact: true })).toBeVisible({ timeout: 120_000 })
    await expect(page.locator('.analysis-ready-badge')).toHaveText('분석 완료')

    const plannedUse = page.getByLabel('계획 건축물 용도')
    await expect(plannedUse.locator('option')).toHaveCount(16)
    await expect(plannedUse.locator('option[value="집회장"]')).toHaveCount(0)
    await expect(plannedUse.locator('option[value="관람장"]')).toHaveCount(0)
    await plannedUse.selectOption({ label: '체육관' })
    await page.getByRole('button', { name: /계획 용도로 다시 분석|입력 내용으로 다시 분석/ }).click()
    await expect(page.locator('.analysis-ready-badge')).toHaveText('분석 완료', { timeout: 120_000 })

    const seatingQuestion = page.getByRole('group', { name: '관람석이 있습니까? 선택' })
    await expect(seatingQuestion).toBeVisible()
    await seatingQuestion.getByRole('button', { name: '예', exact: true }).click()
    await page.getByRole('button', { name: '입력 내용으로 다시 분석' }).click()
    await expect(page.locator('.analysis-ready-badge')).toHaveText('분석 완료', { timeout: 120_000 })

    const spectatorArea = page.getByLabel('관람석 바닥면적의 합계')
    await expect(spectatorArea).toBeVisible()
    const numericItem = spectatorArea.locator('..').locator('..')
    await numericItem.getByRole('button', { name: '아직 미정', exact: true }).click()
    await page.getByRole('button', { name: '입력 내용으로 다시 분석' }).click()
    await expect(page.locator('.analysis-ready-badge')).toHaveText('분석 완료', { timeout: 120_000 })
    await expect(page.getByLabel('계획 건축물 용도')).toHaveValue('체육관')
    await expect(page.getByRole('group', { name: '관람석이 있습니까? 선택' })).toHaveCount(0)
    await expect(page.getByLabel('관람석 바닥면적의 합계')).toHaveCount(0)
  })

})
