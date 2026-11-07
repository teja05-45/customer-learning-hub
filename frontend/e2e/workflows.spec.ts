import { expect, test } from '@playwright/test'

import { API_URL, enterAs, expectNoHorizontalOverflow, resetDemoData, signInApi } from './helpers'

/**
 * The workflows added in this pass: the project journey board and timeline,
 * feedback history on a customer profile, outcome measurement, and consent
 * withdrawal. Each test drives the real screen and then checks the server state.
 */

test.beforeEach(async ({ request }) => {
  await resetDemoData(request)
})

test('the learning journey board and timeline show real project records', async ({ page }) => {
  await enterAs(page, 'Priya Menon')
  await page.goto('/projects')
  await page.getByRole('link', { name: 'Why are shampoo buyers not purchasing again?' }).click()

  await expect(page.getByRole('heading', { level: 1 })).toContainText('Why are shampoo buyers')
  await expect(page.getByRole('button', { name: /Learning journey/ })).toHaveClass(/active/)
  for (const stage of ['Discovery', 'Recruitment', 'Sessions', 'Feedback', 'Evidence', 'Insights', 'Decisions', 'Actions', 'Outcomes']) {
    await expect(page.getByRole('listitem', { name: stage })).toBeVisible()
  }

  // A card is a link to the real record, not decorative text.
  const evidenceCard = page.getByRole('listitem', { name: 'Evidence' }).locator('.journey-card').first()
  await expect(evidenceCard).toBeVisible()
  const href = await evidenceCard.getAttribute('href')
  expect(href).toMatch(/^\/evidence\//)

  await page.getByRole('button', { name: 'Timeline' }).click()
  await expect(page.locator('.journey-timeline-item').first()).toBeVisible()
  await expect(page.getByText('Project started')).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('a customer profile shows cross-project feedback history', async ({ page }) => {
  await enterAs(page, 'Priya Menon')
  await page.goto('/participants')
  await page.getByRole('row').filter({ hasText: 'Ananya Rao' }).click()

  await expect(page.getByRole('heading', { level: 1, name: 'Ananya Rao' })).toBeVisible()
  const feedback = page.getByRole('region', { name: 'Feedback history' })
  await expect(feedback).toBeVisible()
  await expect(feedback.getByText('It lathered differently at home')).toBeVisible()
  await expect(feedback.getByText('Deep depth')).toBeVisible()
  await expect(feedback.getByText('Researcher interpretation')).toBeVisible()
  // The insight count is derived from evidence links, not hard-coded to zero.
  await expect(page.getByRole('region', { name: 'Participation history' })).toContainText('Insights')
})

test('an outcome can be planned, then measured against its target', async ({ page, request }) => {
  // Rohan owns this outcome but has no grant on the shampoo study, so his list
  // correctly omits it. Use the administrator, who is an implicit project owner
  // and can therefore see and change every study.
  await enterAs(page, 'Arjun Desai')
  await signInApi(request, 'admin')
  await page.goto('/outcomes')

  await expect(page.getByRole('heading', { level: 1, name: 'Outcome measurement' })).toBeVisible()
  const card = page.locator('article').filter({ hasText: 'Second purchase within 60 days' })
  await expect(card.getByText('Measurement pending')).toBeVisible()

  await card.getByRole('button', { name: 'Record result' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel(/Actual result/).fill('30')
  await dialog.getByRole('button', { name: 'Record result' }).click()
  await expect(page.getByText(/Result recorded: Achieved/)).toBeVisible()
  await expect(card.getByText('Achieved', { exact: true })).toBeVisible()
  await expect(card.getByText('30 %')).toBeVisible()

  // The server, not the UI, is the source of truth.
  const listed = await (await request.get(`${API_URL}/outcomes`)).json()
  const measured = listed.items.find((item: { name: string }) => item.name.includes('Second purchase'))
  expect(measured.status).toBe('achieved')
  expect(measured.actual_value).toBe(30)
  expect(measured.recorded_at).toBeTruthy()

  // Planning a new outcome without a result must not claim one.
  await page.getByRole('button', { name: 'Plan an outcome' }).click()
  const create = page.getByRole('dialog')
  await create.getByLabel(/Outcome name/).fill('E2E trial conversion')
  await create.getByLabel(/Decision this outcome belongs to/).selectOption({ index: 1 })
  await create.getByLabel(/Metric definition/).fill('Share of trial participants who place a second order.')
  await create.getByLabel(/^Target/).fill('25')
  await create.getByLabel(/^Unit/).fill('%')
  await create.getByRole('button', { name: 'Plan outcome' }).click()
  await expect(page.getByText('Outcome planned')).toBeVisible()
  const created = page.locator('article').filter({ hasText: 'E2E trial conversion' })
  await expect(created.getByText('Planned', { exact: true })).toBeVisible()
})

test('consent withdrawal is recorded and stops future contact', async ({ page, request }) => {
  await enterAs(page, 'Priya Menon')
  await signInApi(request, 'researcher')
  const interviews = await (await request.get(`${API_URL}/interviews?status=scheduled`)).json()
  const target = interviews.items[0]
  expect(target).toBeTruthy()

  await page.goto(`/interviews/${target.id}`)
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()

  await page.getByRole('region', { name: 'Consent' }).first().getByRole('button', { name: 'Record' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Decision').selectOption('withdrawn')
  await dialog.getByLabel('Note').fill('Participant asked to stop research contact (E2E).')
  await dialog.getByRole('button', { name: 'Record consent' }).click()
  await expect(page.getByText('Consent recorded')).toBeVisible()

  await page.reload()
  await expect(page.getByText('Consent: Withdrawn').first()).toBeVisible()
  await expect(page.getByText('Cancelled').first()).toBeVisible()
  await expect(page.getByText('Recording consent has not been granted')).toBeVisible()

  const detail = await (await request.get(`${API_URL}/interviews/${target.id}`)).json()
  expect(detail.consent_status).toBe('withdrawn')
  expect(detail.status).toBe('cancelled')
  expect(detail.consent_records.some((record: { status: string }) => record.status === 'withdrawn')).toBe(true)

  const participant = await (await request.get(`${API_URL}/participants/${target.participant_id}`)).json()
  expect(participant.contact_consent).toBe('withdrawn')

  // The server blocks a new booking for this participant.
  const blocked = await request.post(`${API_URL}/interviews`, {
    data: {
      project_id: target.project_id,
      participant_id: target.participant_id,
      title: 'E2E booking after withdrawal',
      status: 'planned',
    },
  })
  expect(blocked.status()).toBe(400)
})
