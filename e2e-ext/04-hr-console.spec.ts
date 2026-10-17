import { expect, test } from '@playwright/test'
import { loginAs, noOverflow, resetDemo, shot } from './helpers'

test.beforeEach(async ({ page }) => { await resetDemo(page) })

test('HR-пульт: радар, «Предложить пересмотр», «Сотрудник остался» → 10,8 млн ₸', async ({ page }) => {
  await loginAs(page, 'daniyar', '/hr')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('HR-пульт')
  await expect(page.getByTestId('hr-savings')).toContainText('9 900 000 ₸')
  const aigerim = page.locator('.ext-risk[data-employee="emp-aigerim"]')
  await expect(aigerim).toContainText('14 мес без пересмотра')
  await expect(page.locator('.ext-risk[data-employee="emp-nurlan"]')).toContainText('отказа')
  await shot(page, 'hr-radar-1440')
  await aigerim.locator('li[data-kind="no_review"]').getByRole('button', { name: 'Предложить пересмотр' }).click()
  await expect(aigerim).toContainText('Пересмотр назначен на')
  await aigerim.locator('li[data-kind="no_review"]').getByRole('button', { name: 'Сотрудник остался' }).click()
  await expect(page.getByTestId('hr-savings')).toContainText('10 800 000 ₸')
})

test('Рентген: Ерлан наверху; KG — Айбек', async ({ page }) => {
  await loginAs(page, 'daniyar', '/hr')
  await page.getByRole('radio', { name: 'Рентген' }).check({ force: true })
  const rows = page.getByTestId('xray-table').locator('tbody tr')
  await expect(rows.first()).toContainText('Ерлан Мухамедов')
  await shot(page, 'hr-xray-1440')
  await page.getByRole('radio', { name: 'KG' }).check({ force: true })
  await expect(rows).toHaveCount(1)
  await expect(rows.first()).toContainText('Айбек')
})

test('Руководитель видит только себя', async ({ page }) => {
  await loginAs(page, 'erlan', '/manager/xray')
  await expect(page.getByTestId('xray-me')).toContainText('медленнее 100% коллег')
  await expect(page.locator('body')).not.toContainText('Гульнара')
  await shot(page, 'manager-xray-1440')
})

test('375 px: радар без переполнения', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 })
  await loginAs(page, 'daniyar', '/hr')
  await expect(page.getByTestId('hr-risks')).toBeVisible()
  await noOverflow(page)
  await shot(page, 'hr-radar-375')
})
