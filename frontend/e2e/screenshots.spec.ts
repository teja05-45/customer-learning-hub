import { test, expect } from '@playwright/test'
import { resetDemoData, enterAs } from './helpers'

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

    await page.getByRole('link', { name: 'Settings' }).click()
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
    await page.screenshot({ path: `${OUT}/16-settings.png`, fullPage: true })

    // Search palette
    await page.keyboard.press('Control+k')
    await page.getByRole('textbox', { name: 'Search' }).fill('shampoo')
    await expect(page.getByText('Research projects', { exact: false }).first()).toBeVisible()
    await page.waitForTimeout(600)
    await page.screenshot({ path: `${OUT}/17-global-search.png`, fullPage: false })

    // Mobile layout
    await page.keyboard.press('Escape')
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/overview')
    await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible()
    await page.waitForTimeout(700)
    await page.screenshot({ path: `${OUT}/18-mobile-overview.png`, fullPage: false })
  })
})
