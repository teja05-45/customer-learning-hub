import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

import { enterAs, resetDemoData } from './helpers'

/**
 * Automated accessibility scan of every primary screen, plus the command
 * palette. Fails on WCAG 2.1 A/AA violations at serious or critical impact —
 * the threshold a reviewer would reasonably expect for a demo.
 */
const SCREENS = [
  { path: '/overview', name: 'Overview' },
  { path: '/projects', name: 'Projects' },
  { path: '/participants', name: 'Participants' },
  { path: '/recruitment', name: 'Recruitment' },
  { path: '/interviews', name: 'Interviews' },
  { path: '/evidence', name: 'Evidence' },
  { path: '/feedback', name: 'Feedback sources' },
  { path: '/insights', name: 'Insights' },
  { path: '/decisions', name: 'Decisions' },
  { path: '/actions', name: 'Actions' },
  { path: '/outcomes', name: 'Outcome measurement' },
  { path: '/analytics', name: 'Analytics' },
  { path: '/settings', name: 'Settings' },
]

test('no serious accessibility violations on any primary screen', async ({ page }) => {
  await resetDemoData(page.request)
  await enterAs(page, 'Priya Menon')

  const problems: string[] = []

  for (const screen of SCREENS) {
    await page.goto(screen.path)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()

    for (const violation of results.violations) {
      if (violation.impact !== 'serious' && violation.impact !== 'critical') continue
      const targets = violation.nodes.map((node) => node.target.join(' ')).slice(0, 3)
      problems.push(`${screen.name}: ${violation.id} (${violation.impact}) → ${targets.join(', ')}`)
    }
  }

  expect(problems, `accessibility violations:\n${problems.join('\n')}`).toEqual([])
})

test('the traceability screens and the add-evidence dialog are accessible', async ({ page }) => {
  await resetDemoData(page.request)
  await enterAs(page, 'Priya Menon')

  const serious = (results: {
    violations: { id: string; impact?: string | null; nodes: { target: Array<string | string[]> }[] }[]
  }): string[] =>
    results.violations
      .filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')
      .map(
        (violation) =>
          `${violation.id}: ${violation.nodes.map((node) => node.target.join(' ')).join(', ')}`,
      )

  const insights = await (await page.request.get('/api/v1/insights')).json()
  await page.goto(`/insights/${insights.items[0].id}`)
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  const insightScan = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  expect(serious(insightScan)).toEqual([])

  await page.getByRole('button', { name: 'Add evidence' }).first().click()
  await expect(page.getByRole('dialog')).toBeVisible()
  const dialogScan = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  expect(serious(dialogScan)).toEqual([])
  await page.keyboard.press('Escape')

  const evidence = await (await page.request.get('/api/v1/evidence')).json()
  await page.goto(`/evidence/${evidence.items[0].id}`)
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  const evidenceScan = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  expect(serious(evidenceScan)).toEqual([])
})

test('the command palette is dialogs-compliant', async ({ page }) => {
  await enterAs(page, 'Priya Menon')
  await page.getByRole('button', { name: /^Search/ }).click()
  await expect(page.getByRole('dialog')).toBeVisible()

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()

  const serious = results.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  )
  expect(
    serious.map((violation) => `${violation.id}: ${violation.nodes.map((n) => n.target.join(' ')).join(', ')}`),
  ).toEqual([])
})
