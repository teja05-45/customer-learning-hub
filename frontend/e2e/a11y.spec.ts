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
  { path: '/insights', name: 'Insights' },
  { path: '/decisions', name: 'Decisions' },
  { path: '/actions', name: 'Actions' },
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
