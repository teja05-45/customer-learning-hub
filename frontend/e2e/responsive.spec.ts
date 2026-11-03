import { expect, test } from '@playwright/test'

import { enterAs, expectNoHorizontalOverflow, resetDemoData } from './helpers'

/**
 * Responsive verification for the four viewport widths the design system
 * specifies. It asserts the page itself never scrolls sideways, that every
 * primary screen keeps its heading and content, and that the navigation changes
 * shape at the 992px breakpoint rather than disappearing.
 */
const SCREENS = [
  { path: '/overview', heading: 'Overview' },
  { path: '/projects', heading: 'Research projects' },
  { path: '/participants', heading: 'Participants' },
  { path: '/recruitment', heading: 'Recruitment pipeline' },
  { path: '/interviews', heading: 'Interviews' },
  { path: '/evidence', heading: 'Evidence' },
  { path: '/insights', heading: 'Insights library' },
  { path: '/decisions', heading: 'Decisions & actions' },
  { path: '/actions', heading: 'Actions' },
  { path: '/analytics', heading: 'Analytics' },
  { path: '/settings', heading: 'Settings' },
]

const WIDTHS = [375, 768, 1024, 1440]

test.describe('responsive layout', () => {
  test.beforeAll(async ({ request }) => {
    await resetDemoData(request)
  })

  for (const width of WIDTHS) {
    test(`primary screens hold together at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await enterAs(page, 'Priya Menon')

      for (const screen of SCREENS) {
        await page.goto(screen.path)
        await expect(
          page.getByRole('heading', { level: 1, name: screen.heading }),
          `${screen.path} heading at ${width}px`,
        ).toBeVisible()
        await expectNoHorizontalOverflow(page)

        // Horizontal scrolling belongs inside a table wrapper, never on the page.
        const wideTableBreaksPage = await page.evaluate(() => {
          const main = document.querySelector('main')
          if (!main) return false
          return main.scrollWidth > main.clientWidth + 2
        })
        expect(wideTableBreaksPage, `${screen.path} main column overflows at ${width}px`).toBe(false)
      }

      if (width <= 992) {
        // The rail is off-canvas; the menu control must expose it.
        const menu = page.getByRole('button', { name: 'Open navigation' })
        await expect(menu).toBeVisible()
        await menu.click()
        await expect(page.getByRole('link', { name: 'Research projects' })).toBeVisible()
        await page.getByRole('button', { name: 'Close navigation' }).click()
        await expect(menu).toBeVisible()
      } else {
        await expect(page.getByRole('link', { name: 'Research projects' })).toBeVisible()
        await expect(page.getByRole('button', { name: 'Open navigation' })).toBeHidden()
      }
    })
  }

  test('the authentication screen fits the smallest viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/')
    await expect(page.getByText('Demonstration entry', { exact: true })).toBeVisible()
    await expectNoHorizontalOverflow(page)
    await expect(page.getByRole('button', { name: /Priya Menon/ })).toBeVisible()
  })
})
