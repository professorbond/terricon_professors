import { expect, test } from '@playwright/test'
import { API, loginAs, noOverflow, resetDemo, shot } from './helpers'

test.beforeEach(async ({ page }) => { await resetDemo(page) })

test('бейдж «Ответ до …» в списке и карточке; после «+2 дня» — «Одобрено по сроку»', async ({ page }) => {
  await loginAs(page, 'aigerim', '/requests')
  const row = page.locator('.request-table tbody tr', { has: page.locator('.request-status', { hasText: 'На согласовании' }) })
  await expect(row.getByTestId('guarantee-badge')).toContainText('Ответ до')
  await shot(page, 'requests-badge-1440')
  await row.locator('.request-number').click()
  await expect(page.locator('.request-status-line').getByTestId('guarantee-badge')).toContainText('Ответ до')
  await page.request.post(`${API}/api/demo/advance-time`, { data: { hours: 48 } })
  await page.reload()
  await expect(page.locator('.request-status-line').getByTestId('guarantee-badge')).toContainText('Одобрено по сроку')
  await expect(page.locator('.request-status').first()).toContainText('Согласовано')
})

test('отказ: без причины кнопка неактивна, с причиной — сохраняется', async ({ page }) => {
  await loginAs(page, 'erlan', '/manager/approvals')
  await page.locator('.request-number').first().click()
  await page.getByRole('radio', { name: 'Отклонить' }).check({ force: true })
  const submit = page.getByRole('button', { name: 'Подтвердить отклонение' })
  await expect(submit).toBeDisabled()
  await page.locator('.decision-panel textarea').fill('В эти даты в смене никого не остаётся')
  await expect(submit).toBeDisabled()
  await page.locator('.ext-reason select').selectOption('STAFFING')
  await expect(submit).toBeEnabled()
  await shot(page, 'decision-reason-1440')
  await submit.click()
  await expect(page.locator('.decision-complete')).toBeVisible()
  await expect(page.locator('.request-status').first()).toContainText('Отклонено')
})

test('передано HR по сроку — статус и бейдж', async ({ page }) => {
  const hr = await (await page.request.post(`${API}/api/demo/login-as`, { data: { login: 'daniyar' } })).json()
  const auth = { Authorization: `Bearer ${hr.accessToken}` }
  const policies = await (await page.request.get(`${API}/api/ext/policies`, { headers: auth })).json()
  const vac = policies.find((p: { requestType: string }) => p.requestType === 'vacation')
  await page.request.put(`${API}/api/ext/policies/${vac.id}`, { headers: auth, data: { onTimeout: 'escalate_hr' } })
  await page.request.post(`${API}/api/demo/advance-time`, { data: { hours: 48 } })
  await loginAs(page, 'aigerim', '/requests')
  const row = page.locator('.request-table tbody tr', { has: page.locator('.request-status', { hasText: 'Передано HR' }) })
  await expect(row).toHaveCount(1)
  await expect(row.getByTestId('guarantee-badge')).toContainText('Передано HR')
})

test('375 px: карточка с бейджем без переполнения', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 })
  await loginAs(page, 'aigerim', '/requests')
  await expect(page.getByTestId('guarantee-badge').first()).toBeVisible()
  await noOverflow(page)
  await shot(page, 'requests-badge-375')
})
