import { test, expect, type Page } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import { todayDate } from '../src/features/leave/dates'

interface Frame { time: number; offset: number; opacity: number; transform: string | null }
declare global { interface Window { janaMotionProbe?: { frames: Frame[]; done: boolean } } }

function dateAfter(days: number) { return new Date(Date.parse(`${todayDate()}T00:00:00Z`) + days * 86_400_000).toISOString().slice(0, 10) }
function captureErrors(page: Page) {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()) })
  return errors
}
async function login(page: Page, role = 'Сотрудник') {
  await page.goto('/login')
  await page.getByRole('radio', { name: new RegExp(`^${role}`) }).check()
  await page.getByRole('button', { name: 'Войти в пространство' }).click()
  await expect(page.locator('.app-shell')).toBeVisible()
}
async function changeRole(page: Page, role: string) {
  await page.getByRole('button', { name: 'Меню демо-профиля' }).click()
  await page.getByRole('button', { name: 'Сменить демо-роль' }).click()
  await page.getByRole('radio', { name: new RegExp(`^${role}`) }).check()
  await page.getByRole('button', { name: 'Войти в пространство' }).click()
  await expect(page.locator('.app-shell')).toBeVisible()
}
async function prepareRequest(page: Page) {
  await page.goto('/requests/new/leave')
  await page.getByLabel('Первый день', { exact: true }).fill(dateAfter(10))
  await page.getByLabel('Последний день', { exact: true }).fill(dateAfter(14))
  await page.getByRole('button', { name: 'Проверить заявку' }).click()
}
async function send(page: Page) {
  await page.getByRole('dialog').getByRole('button', { name: 'Отправить заявку', exact: true }).click()
  await expect(page.locator('.creation-confirmation')).toBeVisible()
  return (await page.locator('.creation-confirmation strong').textContent())!
}
const route = (page: Page) => page.getByRole('region', { name: 'Jana Flow Map' })

async function startProbe(page: Page, status: string) {
  await page.evaluate((target) => {
    const probe = { frames: [] as Frame[], done: false }
    window.janaMotionProbe = probe
    const deadline = performance.now() + 10000
    function frame(time: number) {
      const map = [...document.querySelectorAll<HTMLElement>('.living-route')].find((element) => element.dataset.status === target && !element.closest('[inert]'))
      if (map?.dataset.motion === 'running' || (probe.frames.length && map?.dataset.motion === 'settled')) {
        const svg = [...map.querySelectorAll('svg[data-layout]')].find((element) => element.getClientRects().length)
        const path = svg?.querySelector('.js-route-segment[data-active="true"]')
        const signal = svg?.querySelector('.js-route-signal')
        if (path && signal) probe.frames.push({ time, offset: Number.parseFloat(getComputedStyle(path).strokeDashoffset), opacity: Number.parseFloat(getComputedStyle(signal).opacity), transform: signal.getAttribute('transform') })
        if (map.dataset.motion === 'settled') { probe.done = true; return }
      }
      if (time < deadline) requestAnimationFrame(frame)
      else probe.done = true
    }
    requestAnimationFrame(frame)
  }, status)
}
async function finishProbe(page: Page) {
  await expect.poll(() => page.evaluate(() => window.janaMotionProbe?.done)).toBe(true)
  const frames = await page.evaluate(() => window.janaMotionProbe!.frames)
  expect(frames.length).toBeGreaterThan(4)
  expect(Math.max(...frames.map((frame) => frame.offset))).toBeGreaterThan(5)
  expect(frames.at(-1)!.offset).toBe(0)
  expect(frames.at(-1)!.opacity).toBe(0)
  expect(new Set(frames.filter((frame) => frame.opacity > 0).map((frame) => frame.transform)).size).toBeGreaterThan(2)
  return frames
}
async function noOverflow(page: Page) {
  const result = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: document.documentElement.clientWidth }))
  expect(result.scroll, JSON.stringify(result)).toBeLessThanOrEqual(result.width)
}

test('Living Route draws confirmed paths, moves one signal, and does not replay on navigation', async ({ page }) => {
  const errors = captureErrors(page)
  await login(page)
  await prepareRequest(page)
  await startProbe(page, 'Submitted')
  const number = await send(page)
  await route(page).locator('.route-graphic').scrollIntoViewIfNeeded()
  await expect(route(page)).toHaveAttribute('data-motion', 'running')
  // Controls remain usable while GSAP runs.
  const station = route(page).getByRole('button', { name: /01.*Отправлено/ })
  await station.click()
  await expect(station).toHaveAttribute('aria-pressed', 'true')
  const frames = await finishProbe(page)
  await expect(route(page).locator('.route-card-copy h3')).toHaveText('Отправлено')
  const intervals = frames.slice(1).map((frame, index) => frame.time - frames[index]!.time).sort((a, b) => a - b)
  await mkdir('artifacts/performance', { recursive: true })
  await writeFile('artifacts/performance/living-route.json', JSON.stringify({ environment: 'Instrumented headless Chrome; rAF sampling, not a 60 FPS guarantee', samples: frames.length, durationMs: frames.at(-1)!.time - frames[0]!.time, medianFrameMs: intervals[Math.floor(intervals.length / 2)], p95FrameMs: intervals[Math.floor(intervals.length * .95)], maxFrameMs: intervals.at(-1), frames }, null, 2))
  await route(page).getByRole('button', { name: /02.*У руководителя/ }).click()
  await expect(route(page).locator('.route-card-copy h3')).toHaveText('У руководителя')
  await page.screenshot({ path: 'artifacts/screenshots/signal-submitted-1440.png', fullPage: true })
  const sidebar = await page.locator('.app-sidebar').elementHandle()
  await page.getByRole('navigation', { name: 'Основная навигация' }).getByRole('link', { name: 'Мой день', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Личный кабинет.' })).toBeVisible()
  await expect(route(page)).toHaveAttribute('data-motion', 'settled')
  expect(await sidebar!.evaluate((element) => element === document.querySelector('.app-sidebar'))).toBe(true)
  await page.getByRole('link', { name: number }).click()
  await expect(route(page)).toHaveAttribute('data-motion', 'settled')
  await expect(page.locator('.route-frame')).toHaveCount(1)
  await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
  expect(errors).toEqual([])
})

for (const decision of ['Approved', 'Rejected'] as const) {
  test(`confirmed ${decision} has its own animated route and notification`, async ({ page }) => {
    const errors = captureErrors(page)
    await login(page)
    await prepareRequest(page)
    const number = await send(page)
    await changeRole(page, 'Руководитель')
    await page.getByRole('link', { name: number }).click()
    await route(page).locator('.route-graphic').scrollIntoViewIfNeeded()
    await expect(route(page)).toHaveAttribute('data-motion', 'settled')
    await startProbe(page, decision)
    if (decision === 'Rejected') {
      await page.getByRole('radio', { name: 'Отклонить', exact: true }).check()
      await page.getByLabel('Причина отклонения').fill('Нужен другой период для передачи задач.')
    }
    await page.getByRole('button', { name: decision === 'Approved' ? 'Подтвердить согласование' : 'Подтвердить отклонение' }).click()
    await route(page).locator('.route-graphic').scrollIntoViewIfNeeded()
    await expect(route(page)).toHaveAttribute('data-status', decision)
    await finishProbe(page)
    await expect(route(page)).toHaveAttribute('data-tone', decision === 'Rejected' ? 'warm' : 'normal')
    const scene = route(page).locator('svg[data-layout="horizontal"]')
    await expect(scene.locator('.route-segment--outcome')).toHaveAttribute('data-confirmed', 'true')
    if (decision === 'Rejected') {
      await expect(scene.locator('.route-segment--outcome')).toHaveCSS('stroke', 'rgb(217, 135, 85)')
      await expect(page.locator('.decision-complete')).toHaveAttribute('data-tone', 'warm')
      await expect(route(page).locator('.route-card-copy')).toContainText('Нужен другой период')
    }
    await expect(page.locator('.request-history li')).toHaveCount(2)
    await page.evaluate(() => window.scrollTo(0, 0))
    await page.screenshot({ path: `artifacts/screenshots/signal-${decision.toLowerCase()}-1440.png`, fullPage: true })
    await page.setViewportSize({ width: 390, height: 844 })
    await route(page).locator('.route-graphic').scrollIntoViewIfNeeded()
    await noOverflow(page)
    await page.evaluate(() => window.scrollTo(0, 0))
    await page.screenshot({ path: `artifacts/screenshots/signal-${decision.toLowerCase()}-390.png`, fullPage: true })
    await page.setViewportSize({ width: 1440, height: 1000 })
    await changeRole(page, 'Сотрудник')
    await expect(page.getByRole('complementary', { name: 'Новое уведомление' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Уведомления — 1 новых' })).toBeVisible()
    await expect(page.getByRole('heading', { level: 1, name: 'Личный кабинет.' })).toBeVisible()
    await expect(page.getByRole('complementary', { name: 'Новое уведомление' })).toHaveCSS('opacity', '1')
    await expect(route(page)).toHaveAttribute('data-motion', 'settled')
    await page.screenshot({ path: `artifacts/screenshots/signal-notification-${decision.toLowerCase()}.png` })
    await page.getByRole('button', { name: 'Закрыть уведомление' }).click()
    await expect(page.getByRole('complementary', { name: 'Новое уведомление' })).toHaveCount(0)
    await page.getByRole('link', { name: 'Уведомления — 1 новых' }).click()
    await page.getByRole('radio', { name: 'Непрочитанные' }).focus()
    await page.keyboard.press('Space')
    await expect(page.getByRole('radio', { name: 'Непрочитанные' })).toBeChecked()
    await page.getByRole('button', { name: 'Отметить прочитанным' }).click()
    await expect(page.getByRole('heading', { name: 'Всё прочитано' })).toBeVisible()
    await page.getByRole('radio', { name: 'Все', exact: true }).check()
    await expect(page.getByText('Прочитано', { exact: true })).toBeVisible()
    expect(errors).toEqual([])
  })
}

test('reduced motion, mobile vertical geometry, breakpoint changes and fast navigation settle cleanly', async ({ page }) => {
  const errors = captureErrors(page)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await login(page)
  await prepareRequest(page)
  const number = await send(page)
  await expect(route(page)).toHaveAttribute('data-motion', 'settled')
  for (const width of [1440, 320, 768, 390, 320, 1440, 390]) {
    await page.setViewportSize({ width, height: 900 })
    const paintedWidths = await page.evaluate(async () => {
      const samples: { width: number; scroll: number }[] = []
      for (let frame = 0; frame < 3; frame++) {
        await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
        samples.push({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth })
      }
      return samples
    })
    for (const sample of paintedWidths) expect(sample.scroll, JSON.stringify(paintedWidths)).toBeLessThanOrEqual(sample.width)
    await noOverflow(page)
    await expect(route(page).locator(`svg[data-layout="${width < 768 ? 'vertical' : 'horizontal'}"]`)).toBeVisible()
    await expect(route(page)).toHaveAttribute('data-motion', 'settled')
    await expect(route(page).locator('.js-route-signal').first()).toHaveCSS('opacity', '0')
  }
  await route(page).locator('.route-graphic').scrollIntoViewIfNeeded()
  await page.screenshot({ path: 'artifacts/screenshots/signal-mobile-390.png', fullPage: true })
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await expect(route(page)).toHaveAttribute('data-motion', 'settled')
  await page.setViewportSize({ width: 1440, height: 1000 })
  const nav = page.getByRole('navigation', { name: 'Основная навигация' })
  // Programmatic activation of actual links exercises changes before exit completes.
  await nav.getByRole('link', { name: 'Мои заявки', exact: true }).evaluate((element: HTMLAnchorElement) => element.click())
  await nav.getByRole('link', { name: 'Мой день', exact: true }).evaluate((element: HTMLAnchorElement) => element.click())
  await nav.getByRole('link', { name: 'Мои заявки', exact: true }).evaluate((element: HTMLAnchorElement) => element.click())
  await expect(page).toHaveURL('/requests')
  await expect(page.locator('.route-frame')).toHaveCount(1)
  await expect(page.getByRole('heading', { level: 1, name: 'Мои заявки.' })).toBeVisible()
  await expect(page.getByRole('link', { name: number })).toBeVisible()
  await expect.poll(() => page.evaluate(async (modulePath) => { const { gsap } = await import(modulePath); return gsap.globalTimeline.getChildren(true, true, true).filter((animation: { isActive(): boolean }) => animation.isActive()).length }, '/src/lib/gsap.ts')).toBe(0)
  expect(errors).toEqual([])
})

test('failed persistence cannot trigger a success route or notification', async ({ page }) => {
  await login(page)
  await prepareRequest(page)
  await page.evaluate(() => {
    const write = Storage.prototype.setItem
    Storage.prototype.setItem = function (key, value) { if (key === 'jana.mock-state.v1') throw new DOMException('Test quota', 'QuotaExceededError'); write.call(this, key, value) }
  })
  await page.getByRole('dialog').getByRole('button', { name: 'Отправить заявку', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Не удалось сохранить демо-данные')
  await expect(page.locator('.creation-confirmation, .living-route, .notification-signal')).toHaveCount(0)
  expect(await page.evaluate(() => localStorage.getItem('jana.mock-state.v1'))).toBeNull()
})

test('turning on reduced motion cancels a running mobile signal and settles final geometry', async ({ page }) => {
  const errors = captureErrors(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page)
  await prepareRequest(page)
  await send(page)
  await route(page).locator('.route-graphic').scrollIntoViewIfNeeded()
  await expect(route(page)).toHaveAttribute('data-motion', 'running')
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await expect(route(page)).toHaveAttribute('data-motion', 'settled')
  await expect(route(page).locator('svg[data-layout="vertical"] .route-segment[data-active="true"]')).toHaveCSS('stroke-dashoffset', '0px')
  await expect(route(page).locator('svg[data-layout="vertical"] .js-route-signal')).toHaveCSS('opacity', '0')
  const station = route(page).getByRole('button', { name: /01.*Отправлено/ })
  await station.focus()
  await page.keyboard.press('Enter')
  await expect(route(page).locator('.route-card-copy h3')).toHaveText('Отправлено')
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await expect(route(page)).toHaveAttribute('data-motion', 'settled')
  await noOverflow(page)
  expect(errors).toEqual([])
})
