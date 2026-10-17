import { expect, test } from '@playwright/test'
import { loginAs, noOverflow, resetDemo, shot } from './helpers'

test.beforeEach(async ({ page }) => { await resetDemo(page) })

test('лестница в профиле → курс → уроки → тест → «все условия выполнены»', async ({ page }) => {
  await loginAs(page, 'aigerim', '/profile')
  const ladder = page.getByTestId('ladder')
  await expect(ladder).toContainText('Сортировщик')
  await expect(ladder).toContainText('Старший сортировщик')
  await expect(page.getByTestId('ladder-remaining')).toContainText('Осталось: 1 курс → +35 000 ₸')
  await expect(ladder).not.toContainText('{actual}')
  await shot(page, 'profile-ladder-1440')
  await ladder.getByRole('link', { name: 'Перейти к курсу' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Техника безопасности')
  await expect(page.getByTestId('grade-tag')).toContainText('SORT-2')
  await shot(page, 'academy-course-1440')
  await page.getByTestId('course-lessons').getByRole('link', { name: 'Продолжить' }).click()
  for (let i = 0; i < 3; i++) {
    await expect(page.getByTestId('lesson-content')).toBeVisible()
    if (i === 0) await shot(page, 'academy-lesson-1440')
    await page.getByRole('button', { name: /Урок изучен/ }).click()
  }
  await expect(page.getByTestId('test-form')).toBeVisible()
  await expect(page.locator('body')).not.toContainText('correct')
  const answers = [1, 1, 1, 0]
  const sets = page.locator('.ext-question')
  for (let i = 0; i < answers.length; i++) await sets.nth(i).locator('input').nth(answers[i]).check()
  await shot(page, 'academy-test-1440')
  await page.getByRole('button', { name: 'Отправить ответы' }).click()
  await expect(page.getByTestId('test-result')).toContainText('Тест сдан: 100%')
  await page.goto('/profile')
  await expect(page.getByTestId('ladder-remaining')).toContainText('Все условия выполнены')
})

test('Academy: мои курсы, бейдж грейда, 375 px', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 })
  await loginAs(page, 'aigerim', '/academy')
  await expect(page.getByTestId('academy-my')).toContainText('Работа с возвратами')
  await expect(page.getByTestId('grade-tag').first()).toContainText('SORT-2')
  await noOverflow(page)
  await shot(page, 'academy-375')
  await page.goto('/profile')
  await expect(page.getByTestId('ladder')).toBeVisible()
  await noOverflow(page)
  await shot(page, 'profile-ladder-375')
})

test('Academy 1440 и обучение для HR и руководителя', async ({ page }) => {
  await loginAs(page, 'aigerim', '/academy')
  await shot(page, 'academy-1440')
  await loginAs(page, 'daniyar', '/hr/learning')
  await expect(page.getByTestId('learning-progress')).toContainText('Айгерим Сейткали')
  await shot(page, 'hr-learning-1440')
  await loginAs(page, 'gulnara', '/manager/learning')
  await page.locator('select').nth(0).selectOption('emp-asel')
  await page.locator('select').nth(1).selectOption('course-safety')
  await page.getByRole('button', { name: 'Назначить курс' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Курс назначен' })).toBeVisible()
})
