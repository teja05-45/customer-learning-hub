import { test, expect } from '@playwright/test'
import { API_URL, resetDemoData, enterAs } from './helpers'

const OUT = '../docs/screenshots'

test.describe('documentation screenshots', () => {
  test.beforeAll(async ({ request }) => {
    await resetDemoData(request)
  })

  test('capture the workspace', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Demonstration entry', { exact: true })).toBeVisible()
    await expect(page.getByText('This prototype contains synthetic data only.')).toBeVisible()
    await page.screenshot({ path: `${OUT}/01-demo-entry.png`, fullPage: false })

    await enterAs(page, 'Asha Menon')
    await expect(page.getByText('Are we learning something useful?')).toBeVisible()
    await page.waitForTimeout(900)
    await page.screenshot({ path: `${OUT}/02-overview.png`, fullPage: true })

    await page.getByRole('link', { name: 'Research projects' }).click()
    await expect(page.getByRole('heading', { name: 'Research projects' })).toBeVisible()
    await page.screenshot({ path: `${OUT}/03-projects.png`, fullPage: true })

    await page.getByRole('link', { name: 'Why are shampoo buyers not purchasing again?' }).click()
    await expect(page.getByRole('heading', { name: 'Why are shampoo buyers not purchasing again?' })).toBeVisible()
    await page.screenshot({ path: `${OUT}/04-project-detail.png`, fullPage: true })

    await page.getByRole('button', { name: /Evidence · / }).click()
    await page.waitForTimeout(600)
    await page.screenshot({ path: `${OUT}/05-project-evidence.png`, fullPage: true })

    await page.getByRole('link', { name: 'Feedback sources' }).click()
    await expect(page.getByRole('heading', { name: 'Feedback sources' })).toBeVisible()
    await expect(page.locator('.feedback-card').first()).toBeVisible()
    await page.waitForTimeout(400)
    await page.screenshot({ path: `${OUT}/19-feedback-sources.png`, fullPage: true })

    await page.getByRole('link', { name: 'Participants' }).click()
    await expect(page.getByRole('heading', { name: 'Participants' })).toBeVisible()
    await page.screenshot({ path: `${OUT}/06-participants.png`, fullPage: true })

    await page.getByRole('link', { name: 'Recruitment' }).click()
    await expect(page.getByRole('heading', { name: 'Recruitment pipeline' })).toBeVisible()
    await page.screenshot({ path: `${OUT}/07-recruitment.png`, fullPage: true })

    await page.getByRole('link', { name: 'Interviews' }).click()
    await expect(page.getByRole('heading', { name: 'Interviews' })).toBeVisible()
    await page.screenshot({ path: `${OUT}/08-interviews.png`, fullPage: true })

    await page.getByRole('link', { name: 'First bottle, then nothing' }).click()
    await expect(page.getByRole('heading', { name: 'First bottle, then nothing' })).toBeVisible()
    await page.screenshot({ path: `${OUT}/09-interview-workspace.png`, fullPage: true })

    await page.getByRole('link', { name: 'Insights library' }).click()
    await expect(page.getByRole('heading', { name: 'Insights library' })).toBeVisible()
    await page.screenshot({ path: `${OUT}/10-insights-library.png`, fullPage: true })

    await page.getByRole('link', { name: /Multiple factors may explain the lack of repeat shampoo purchases/ }).first().click()
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Multiple factors')
    await page.screenshot({ path: `${OUT}/11-insight-traceability.png`, fullPage: true })

    await page.getByRole('link', { name: 'Decisions & actions' }).click()
    await expect(page.getByRole('heading', { name: 'Decisions & actions' })).toBeVisible()
    await page.screenshot({ path: `${OUT}/12-decision-register.png`, fullPage: true })

    await page.getByRole('link', { name: 'Run a bottle-size test before changing price' }).click()
    await expect(page.getByRole('heading', { name: 'Run a bottle-size test before changing price' })).toBeVisible()
    await page.screenshot({ path: `${OUT}/13-decision-detail.png`, fullPage: true })

    await page.goto('/actions')
    await expect(page.getByRole('heading', { name: 'Actions', exact: true })).toBeVisible()
    await page.screenshot({ path: `${OUT}/14-actions.png`, fullPage: true })

    await page.getByRole('link', { name: 'Analytics' }).click()
    await expect(page.getByRole('heading', { name: 'Analytics', exact: true })).toBeVisible()
    await page.screenshot({ path: `${OUT}/15-analytics.png`, fullPage: true })

    // Settings is administrator-only in this release, so take this screenshot
    // with an administrator session and restore the read-only CEO afterwards.
    const demoUsers = (await (await page.request.get(`${API_URL}/session`)).json()).users as Array<{
      id: string
      name: string
      role: string
    }>
    const admin = demoUsers.find((candidate) => candidate.role === 'admin')
    const asha = demoUsers.find((candidate) => candidate.name.startsWith('Asha'))
    expect(admin).toBeTruthy()
    await page.request.post(`${API_URL}/auth/demo`, { data: { user_id: admin!.id } })
    await page.goto('/settings')
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
    await page.screenshot({ path: `${OUT}/16-settings.png`, fullPage: true })
    await page.request.post(`${API_URL}/auth/demo`, { data: { user_id: asha!.id } })

    await page.goto('/evidence')
    await expect(page.getByRole('heading', { name: 'Evidence library' })).toBeVisible()
    await expect(page.locator('.evidence-card').first()).toBeVisible()
    await page.screenshot({ path: `${OUT}/20-evidence.png`, fullPage: true })

    await page.goto('/outcomes')
    await expect(page.getByRole('heading', { name: 'Outcome measurement' })).toBeVisible()
    await expect(page.locator('article').first()).toBeVisible()
    await page.screenshot({ path: `${OUT}/21-outcomes.png`, fullPage: true })

    // Learning journey: board first, then the same records on a timeline.
    await page.goto('/projects')
    await page.getByRole('link', { name: 'Why are shampoo buyers not purchasing again?' }).click()
    await expect(page.getByRole('listitem', { name: 'Evidence' })).toBeVisible()
    await page.waitForTimeout(500)
    await page.screenshot({ path: `${OUT}/22-project-journey-board.png`, fullPage: true })
    await page.getByRole('button', { name: 'Timeline' }).click()
    await expect(page.locator('.journey-timeline-item').first()).toBeVisible()
    await page.waitForTimeout(400)
    await page.screenshot({ path: `${OUT}/23-project-journey-timeline.png`, fullPage: true })

    // Customer profile with cross-project feedback history.
    await page.goto('/participants')
    await page.getByRole('row').filter({ hasText: 'Ananya Rao' }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Ananya Rao' })).toBeVisible()
    await expect(page.getByRole('region', { name: 'Feedback history' })).toBeVisible()
    await page.waitForTimeout(400)
    await page.screenshot({ path: `${OUT}/24-participant-profile.png`, fullPage: true })

    // Consent withdrawal dialog, opened on a scheduled session.
    await page.goto('/interviews')
    await page.getByRole('link', { name: 'Body wash in a shared bathroom' }).click()
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await page.getByRole('region', { name: 'Consent' }).first().getByRole('button', { name: 'Record' }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.getByLabel('Decision').selectOption('withdrawn')
    await page.waitForTimeout(300)
    await page.screenshot({ path: `${OUT}/25-consent-withdrawal.png`, fullPage: false })
    await page.keyboard.press('Escape')

    // Search palette
    await page.keyboard.press('Control+k')
    await page.getByRole('textbox', { name: 'Search' }).fill('shampoo')
    await expect(page.getByText('Research projects', { exact: false }).first()).toBeVisible()
    await page.waitForTimeout(600)
    await page.screenshot({ path: `${OUT}/17-global-search.png`, fullPage: false })

    // Mobile layout
    await page.keyboard.press('Escape')
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/overview')
    await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible()
    await page.waitForTimeout(700)
    await page.screenshot({ path: `${OUT}/18-mobile-overview.png`, fullPage: false })

    await page.goto('/outcomes')
    await expect(page.getByRole('heading', { name: 'Outcome measurement' })).toBeVisible()
    await page.waitForTimeout(500)
    await page.screenshot({ path: `${OUT}/27-mobile-outcomes.png`, fullPage: false })

    // Selected tablet screen.
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/projects')
    await expect(page.getByRole('heading', { name: 'Research projects' })).toBeVisible()
    await page.waitForTimeout(500)
    await page.screenshot({ path: `${OUT}/26-tablet-projects.png`, fullPage: false })
  })
})
