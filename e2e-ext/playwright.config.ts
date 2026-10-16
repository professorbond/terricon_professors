import { defineConfig, devices } from '@playwright/test'

/** E2E экранов ext-фич в HTTP-режиме: против запущенного `docker compose up` (фронт :5173, API :8000).
 * Конфиг тестов напарника (playwright.config.ts, моки) не затрагивается. */
export default defineConfig({
  testDir: '.',
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: { baseURL: process.env.EXT_BASE_URL ?? 'http://localhost:5173', trace: 'retain-on-failure', ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}) },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : { channel: undefined }) } }],
})
