import { expect, test } from '@playwright/test'

import { enterAs, resetDemoData } from './helpers'

/**
 * The unified feedback module must work through the real screen, not just the
 * API: a survey answer is recorded with its source, labelled with its shallower
 * depth, verified, and then deleted.
 */
test('a feedback source can be recorded, verified and deleted', async ({ page }) => {
  await resetDemoData(page.request)
  await enterAs(page, 'Priya Menon')

  await page.goto('/feedback')
  await expect(page.getByRole('heading', { level: 1, name: 'Feedback sources' })).toBeVisible()
  await expect(page.locator('.feedback-card').first()).toBeVisible()

  const unique = `E2E survey response ${Date.now()}`
  await page.getByRole('button', { name: 'Add feedback' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText('Record a feedback source')).toBeVisible()

  await dialog.getByLabel(/^Project/).selectOption({ index: 1 })
  await dialog.getByLabel(/^Source type/).selectOption('short_survey')
  await dialog.getByLabel(/^Collection method/).selectOption('short_survey')
  await dialog.getByLabel(/^Source reference/).fill('E2E survey export · wave 9')
  await dialog.getByLabel(/^Original customer words/).fill(`${unique} — the bottle was hard to open.`)
  await dialog
    .getByLabel(/^Researcher interpretation/)
    .fill('Possibly a packaging accessibility issue, not a product-quality complaint.')
  await dialog.getByRole('button', { name: 'Save feedback' }).click()

  await expect(page.getByText('Feedback recorded')).toBeVisible()
  const card = page.locator('.feedback-card').filter({ hasText: unique })
  await expect(card).toBeVisible()
  await expect(card.getByText('Limited depth')).toBeVisible()
  await expect(card.getByText('Unattributed')).toBeVisible()
  await expect(card.getByText('Possibly a packaging accessibility issue')).toBeVisible()

  await card.getByRole('button', { name: 'Mark verified' }).click()
  await expect(card.getByText('Source verified')).toBeVisible()

  await card.getByRole('button', { name: 'Delete' }).click()
  await page.getByRole('button', { name: 'Delete feedback source' }).click()
  await expect(page.getByText('Feedback source deleted')).toBeVisible()
  await expect(card).toHaveCount(0)
})
