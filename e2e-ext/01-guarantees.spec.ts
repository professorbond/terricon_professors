import { expect, test } from '@playwright/test'
import { loginAs, noOverflow, resetDemo, shot } from './helpers'

test.beforeEach(async ({ page }) => { await resetDemo(page) })

for (const width of [1440, 375]) {
  test(`«Мои гарантии» на главной — ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 1000 })
    await loginAs(page, 'aigerim')
    const widget = page.getByTestId('guarantees-widget')
    await expect(widget.getByRole('heading', { name: 'Мои гарантии' })).toBeVisible()
    await expect(widget).toContainText('Ответ по заявке JL-')
    await expect(widget).toContainText('84 000 ₸')
    await noOverflow(page)
    await widget.scrollIntoViewIfNeeded()
    await shot(page, `guarantees-home-${width}`)
  })
}
