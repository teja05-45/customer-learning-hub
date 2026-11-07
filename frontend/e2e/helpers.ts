import { expect, type Page, type Request } from '@playwright/test'

export const API_URL = process.env.E2E_API_URL ?? 'http://127.0.0.1:8000/api/v1'

/**
 * Restore the synthetic dataset. The reset endpoint is authenticated, so this
 * signs in first and signs out afterwards: the UI tests then start from the
 * entry screen exactly as a reviewer would.
 */
export async function resetDemoData(request: Request): Promise<void> {
  const session = await (await request.get(`${API_URL}/session`)).json()
  const researcher = session.users.find((user: { role: string }) => user.role === 'researcher')
  const login = await request.post(`${API_URL}/auth/demo`, { data: { user_id: researcher.id } })
  expect(login.ok(), `demo sign-in failed: ${login.status()}`).toBeTruthy()

  const response = await request.post(`${API_URL}/demo/reset`, {
    data: { confirm: true, phrase: 'RESET' },
  })
  expect(response.ok(), `demo reset failed: ${response.status()} ${await response.text()}`).toBeTruthy()

  const logout = await request.post(`${API_URL}/auth/logout`)
  expect(logout.ok(), 'sign-out after reset failed').toBeTruthy()
}

/** Sign the API request context in as a demonstration role (separate cookie jar). */
export async function signInApi(request: Request, role: string): Promise<void> {
  const session = await (await request.get(`${API_URL}/session`)).json()
  const user = session.users.find((candidate: { role: string }) => candidate.role === role)
  expect(user, `no demonstration user with role ${role}`).toBeTruthy()
  const login = await request.post(`${API_URL}/auth/demo`, { data: { user_id: user.id } })
  expect(login.ok(), `API sign-in as ${role} failed: ${login.status()}`).toBeTruthy()
}

/** Sign in through the demonstration entry. This creates a real session. */
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
