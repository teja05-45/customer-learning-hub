import { readFileSync } from 'node:fs'

import { expect, test } from '@playwright/test'

import { enterAs, resetDemoData } from './helpers'

/**
 * Regression test for the reported "Export failed" defect.
 *
 * The API tests already prove every endpoint returns a CSV. This test drives
 * the actual Settings buttons in a browser, waits for the real download, and
 * parses the file — so a frontend fetch/credential/header regression cannot
 * pass unnoticed.
 */
const EXPORTS = [
  'Research projects',
  'Participants',
  'Recruitment records',
  'Interviews',
  'Evidence',
  'Feedback sources',
  'Insights',
  'Decisions',
  'Actions',
]

test('every Settings export downloads a parseable, labelled CSV', async ({ page }) => {
  await resetDemoData(page.request)
  await enterAs(page, 'Priya Menon')
  await page.goto('/settings')
  await expect(page.getByRole('heading', { level: 1, name: 'Settings' })).toBeVisible()

  for (const label of EXPORTS) {
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 20_000 }),
      page.getByRole('button', { name: label, exact: true }).click(),
    ])

    expect(download.suggestedFilename(), `${label} filename`).toMatch(
      /^everyday-goods-[a-z]+-(synthetic|live)\.csv$/,
    )

    const path = await download.path()
    expect(path, `${label} should have a downloaded file`).toBeTruthy()
    const raw = readFileSync(path as string, 'utf8')

    // Excel-compatible encoding: the UTF-8 BOM must survive the browser round trip.
    expect(raw.charCodeAt(0), `${label} keeps the UTF-8 BOM`).toBe(0xfeff)

    const lines = raw.replace(/^\uFEFF/, '').split(/\r?\n/)
    expect(lines.length, `${label} has a header and at least one row`).toBeGreaterThan(1)

    const header = lines[0].split(',')
    expect(header, `${label} names its columns`).toContain('data_origin')
    expect(header, `${label} records the export timestamp`).toContain('exported_at')
    expect(header).not.toContain('email')
    expect(header).not.toContain('notes')

    // The final column pair is the provenance stamp for every data row.
    for (const row of lines.slice(1).filter(Boolean)) {
      const cells = row.split(',')
      expect(cells[cells.length - 2], `${label} labels its data origin`).toMatch(/^(synthetic|live)$/)
    }
  }
})
