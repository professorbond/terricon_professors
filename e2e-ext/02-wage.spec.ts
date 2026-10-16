import { expect, test } from '@playwright/test'
import { loginAs, noOverflow, resetDemo, shot } from './helpers'

test.beforeEach(async ({ page }) => { await resetDemo(page) })

test('«Зарплата по факту»: 3 нажатия от главной до «Деньги отправлены»', async ({ page }) => {
  await loginAs(page, 'aigerim')
  const widget = page.getByTestId('wage-widget')
  await expect(widget.getByTestId('wage-available')).toHaveText('84 000 ₸')
  await widget.getByRole('link', { name: 'Получить' }).click()                     // 1
  await expect(page).toHaveURL(/\/wage$/)
  await page.getByLabel('Сумма').fill('60000')
  await page.getByRole('button', { name: /^Получить 60 000 ₸/ }).click()          // 2
  await expect(page.getByRole('dialog')).toContainText('Получить 60 000 ₸?')
  await page.getByRole('dialog').getByRole('button', { name: 'Подтвердить' }).click() // 3
  await expect(page.getByTestId('wage-sent')).toContainText('Деньги отправлены')
  await expect(page.getByTestId('wage-sent')).toContainText('60 000 ₸')
  await page.getByRole('button', { name: 'Готово' }).click()
  await expect(page.getByTestId('wage-available')).toHaveText('24 000 ₸')
})

test('сумма больше доступной — подсказка, без запроса', async ({ page }) => {
  await loginAs(page, 'aigerim', '/wage')
  await page.getByLabel('Сумма').fill('100000')
  await page.getByRole('button', { name: /^Получить/ }).click()
  await expect(page.getByRole('alert')).toContainText('можно до 84 000 ₸')
  await expect(page.getByRole('dialog')).toBeHidden()
})

for (const width of [1440, 375]) {
  test(`экраны «Зарплаты по факту» — ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 1000 })
    await loginAs(page, 'aigerim', '/wage')
    await expect(page.getByTestId('wage-available')).toBeVisible()
    await noOverflow(page)
    await shot(page, `wage-${width}`)
    await page.getByRole('radio', { name: 'Почему столько' }).check({ force: true })
    await expect(page.getByTestId('wage-why')).toContainText('ОПВ')
    await noOverflow(page)
    await shot(page, `wage-why-${width}`)
    await page.getByRole('radio', { name: 'Получить' }).check({ force: true })
    await page.getByLabel('Сумма').fill('60000')
    await page.getByRole('button', { name: /^Получить 60 000/ }).click()
    await shot(page, `wage-confirm-${width}`)
    await page.getByRole('dialog').getByRole('button', { name: 'Подтвердить' }).click()
    await expect(page.getByTestId('wage-sent')).toBeVisible()
    await shot(page, `wage-sent-${width}`)
  })
}

test('казахский интерфейс', async ({ page }) => {
  await loginAs(page, 'aigerim', '/wage')
  await page.getByRole('radio', { name: 'KZ' }).check({ force: true })
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Нақты жалақы')
  await expect(page.getByText('Қазір қолжетімді')).toBeVisible()
  await shot(page, 'wage-kk-1440')
  await page.getByRole('radio', { name: 'RU' }).check({ force: true })
})
