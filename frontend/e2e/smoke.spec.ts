import { expect, test } from '@playwright/test'

import { enterAs, expectNoHorizontalOverflow, resetDemoData } from './helpers'

/**
 * Broad smoke test: every primary screen must render real data from the API
 * without console errors. Runs against the Vite dev server during development
 * and against the Docker/nginx build by setting E2E_BASE_URL.
 */
const SCREENS: Array<{ path: string; heading: string }> = [
  { path: '/', heading: 'Overview' },
  { path: '/projects', heading: 'Research projects' },
  { path: '/participants', heading: 'Participants' },
  { path: '/recruitment', heading: 'Recruitment pipeline' },
  { path: '/interviews', heading: 'Interviews' },
  { path: '/feedback', heading: 'Feedback sources' },
  { path: '/insights', heading: 'Insights library' },
  { path: '/decisions', heading: 'Decisions & actions' },
  { path: '/actions', heading: 'Actions' },
  { path: '/analytics', heading: 'Analytics' },
  { path: '/settings', heading: 'Settings' },
]

test('every primary screen renders for the lead researcher', async ({ page }) => {
  await resetDemoData(page.request)
  await enterAs(page, 'Priya Menon')

  // Collect errors only once signed in: the signed-out /auth/me probe is a
  // deliberate 401 and is handled by the session provider.
  const consoleErrors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  page.on('pageerror', (error) => consoleErrors.push(String(error)))

  for (const screen of SCREENS) {
    await page.goto(screen.path)
    await expect(
      page.getByRole('heading', { level: 1, name: screen.heading }),
      `${screen.path} should show "${screen.heading}"`,
    ).toBeVisible()
    await expectNoHorizontalOverflow(page)
  }

  await page.goto('/')
  await expect(page.getByText('Active research projects').first()).toBeVisible()
  await expect(page.getByText('Are we learning something useful?')).toBeVisible()
  await expect(page.getByText('Recent research activity')).toBeVisible()

  expect(consoleErrors, `console errors:\n${consoleErrors.join('\n')}`).toEqual([])
})

test('deep links, unknown routes and the API error state behave', async ({ page }) => {
  await resetDemoData(page.request)
  await enterAs(page, 'Priya Menon')

  // Deep link straight into a seeded record (the router must not depend on clicks).
  // Relative to the web origin so the request carries the same cookie the
  // browser received through the Vite proxy.
  const projects = await page.request.get('/api/v1/projects')
  const body = await projects.json()
  const project = body.items[0]
  await page.goto(`/projects/${project.id}`)
  await expect(page.getByRole('heading', { level: 1 })).toContainText(project.name)
  await expect(page.getByText(/evidence/i).first()).toBeVisible()

  await page.goto('/this-route-does-not-exist')
  await expect(page.getByRole('heading', { name: /not found|page not found/i })).toBeVisible()

  await page.route('**/api/v1/dashboard', (route) => route.abort())
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /overview/i })).toBeVisible()
  await expect(page.getByText(/could not|went wrong|try again/i).first()).toBeVisible()
})

test('keyboard users can skip navigation and use search without a mouse', async ({ page }) => {
  await enterAs(page, 'Priya Menon')

  // First Tab lands on the skip link, and Enter moves focus into the main landmark.
  await page.keyboard.press('Tab')
  const skip = page.getByRole('link', { name: 'Skip to content' })
  await expect(skip).toBeFocused()
  await skip.press('Enter')
  await expect(page.locator('#main')).toBeFocused()

  // The command palette traps Tab and hands focus back to its trigger on Escape.
  const trigger = page.getByRole('button', { name: /^Search/ })
  await trigger.click()
  const dialog = page.getByRole('dialog', { name: 'Search the research record' })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByLabel('Search', { exact: true })).toBeFocused()
  for (let i = 0; i < 6; i += 1) await page.keyboard.press('Tab')
  const focusInside = await page.evaluate(
    () => document.activeElement?.closest('[role="dialog"]') !== null,
  )
  expect(focusInside, 'Tab must stay inside the dialog').toBe(true)

  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
  await expect(trigger).toBeFocused()
})
