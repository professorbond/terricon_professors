import { expect, type Page } from '@playwright/test'

export const API = process.env.EXT_API_URL ?? 'http://localhost:8000'
export const SHOTS = 'docs/screenshots'

export async function resetDemo(page: Page) {
  await page.request.post(`${API}/api/demo/reset`)
}

/** Вход за персонажа seed через API + токен в сессию вкладки (как делает демо-панель). */
export async function loginAs(page: Page, login: string, path = '/dashboard') {
  const r = await page.request.post(`${API}/api/demo/login-as`, { data: { login } })
  const { accessToken, user } = await r.json()
  await page.goto('/login')
  await page.evaluate(([token, role]) => { sessionStorage.setItem('jana.api-token.v1', token); sessionStorage.setItem('jana.demo-role.v1', role) }, [accessToken, user.role])
  await page.goto(path)
  await expect(page.locator('.app-shell')).toBeVisible()
}

export async function shot(page: Page, name: string) {
  await page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur(); return document.fonts.ready })
  await page.waitForTimeout(400)
  await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true })
}

export async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true)
}
