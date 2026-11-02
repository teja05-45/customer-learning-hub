import { expect, type Page, type Request } from '@playwright/test'

export const API_URL = process.env.E2E_API_URL ?? 'http://127.0.0.1:8000/api/v1'

/** Restore the synthetic dataset so a run does not depend on earlier state. */
export async function resetDemoData(request: Request): Promise<void> {
  const response = await request.post(`${API_URL}/demo/reset`, {
    data: { confirm: true, phrase: 'RESET' },
  })
  expect(response.ok(), `demo reset failed: ${response.status()} ${await response.text()}`).toBeTruthy()
}

/** Enter the workspace with a demonstration role. This is not authentication. */
export async function enterAs(page: Page, name: string): Promise<void> {
  await page.goto('/')
  await expect(page.getByRole('button', { name: new RegExp(name) })).toBeVisible()
  await page.getByRole('button', { name: new RegExp(name) }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Overview' })).toBeVisible()
}

export async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow, 'page should not scroll horizontally at this viewport').toBeLessThanOrEqual(2)
}
