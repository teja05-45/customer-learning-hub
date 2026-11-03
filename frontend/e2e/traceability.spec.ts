import { readFileSync } from 'node:fs'

import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

import { enterAs, expectNoHorizontalOverflow, resetDemoData } from './helpers'

/**
 * Evidence-to-insight traceability journeys.
 *
 * The API tests prove the rules. These tests drive the screens a researcher
 * actually uses: deriving evidence from a survey (no interview needed), linking
 * it as supporting or contradictory, walking the chain in both directions, and
 * exporting it. Each test resets the synthetic dataset first.
 */

interface FeedbackEvidence {
  feedback: { id: string; code: string; content: string }
  evidence: { id: string; code: string; content: string }
}

async function createFeedbackAndEvidence(
  request: APIRequestContext,
  projectId: string,
  content: string,
  interpretation: string,
  sourceType = 'short_survey',
): Promise<FeedbackEvidence> {
  const feedbackResponse = await request.post('/api/v1/feedback', {
    data: {
      project_id: projectId,
      source_type: sourceType,
      collection_method: sourceType === 'short_survey' ? 'short_survey' : 'written_feedback',
      source_reference: 'E2E survey wave · free text',
      content,
      interpretation,
      context: 'Collected asynchronously; nobody could probe the answer.',
      verification_status: 'verified',
    },
  })
  expect(feedbackResponse.status(), await feedbackResponse.text()).toBe(201)
  const feedback = await feedbackResponse.json()

  const evidenceResponse = await request.post(`/api/v1/feedback/${feedback.id}/evidence`)
  expect(evidenceResponse.status(), await evidenceResponse.text()).toBe(201)
  const evidence = await evidenceResponse.json()
  return { feedback, evidence }
}

/** Sign out, then enter as another role through the real login screen. */
async function switchUser(page: Page, name: string): Promise<void> {
  await page.request.post('/api/v1/auth/logout')
  await page.goto('/')
  await expect(page.getByRole('button', { name: new RegExp(name) })).toBeVisible()
  await page.getByRole('button', { name: new RegExp(name) }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Overview' })).toBeVisible()
}

async function firstProjectId(request: APIRequestContext): Promise<string> {
  const projects = await (await request.get('/api/v1/projects?page_size=50')).json()
  return projects.items[0].id
}

async function newInsight(request: APIRequestContext, projectId: string, title: string) {
  const response = await request.post('/api/v1/insights', {
    data: {
      title,
      summary:
        'Customers describe the same friction in their own words. This insight exists to test that the statement survives unchanged.',
      project_id: projectId,
      confidence: 'low',
    },
  })
  expect(response.status(), await response.text()).toBe(201)
  return response.json()
}

async function linkViaApi(
  request: APIRequestContext,
  insightId: string,
  evidenceId: string,
  role: string,
  rationale: string,
) {
  const response = await request.post(`/api/v1/insights/${insightId}/evidence`, {
    data: { evidence_id: evidenceId, role, rationale },
  })
  expect(response.status(), await response.text()).toBe(201)
}

async function createDecision(request: APIRequestContext, projectId: string, insightId: string) {
  const response = await request.post('/api/v1/decisions', {
    data: {
      title: 'E2E: change the cap design',
      business_function: 'product_category',
      problem_statement: 'Shower use is blocked by a cap that is hard to open wet.',
      description: 'Commission a packaging review before changing the product.',
      rationale: 'The pattern recurs, although one customer disagreed.',
      project_id: projectId,
      insight_ids: [insightId],
      evidence_sufficient: true,
    },
  })
  expect(response.status(), await response.text()).toBe(201)
  return response.json()
}

test('a survey answer becomes traceable evidence without an interview', async ({ page }) => {
  await resetDemoData(page.request)
  await enterAs(page, 'Priya Menon')

  const projectId = await firstProjectId(page.request)
  const statement =
    'The cap is hard to open with wet hands, so I stopped using it in the shower.'
  const interpretation = 'Possibly a packaging accessibility issue, not a product-quality complaint.'

  const feedbackResponse = await page.request.post('/api/v1/feedback', {
    data: {
      project_id: projectId,
      source_type: 'short_survey',
      collection_method: 'short_survey',
      source_reference: 'E2E survey wave 7',
      content: statement,
      interpretation,
      verification_status: 'verified',
    },
  })
  expect(feedbackResponse.status(), await feedbackResponse.text()).toBe(201)
  const feedback = await feedbackResponse.json()

  // Derive evidence through the real button on the feedback screen.
  await page.goto('/feedback')
  const card = page.locator('.feedback-card').filter({ hasText: statement })
  await expect(card).toBeVisible()
  await card.getByRole('button', { name: 'Create evidence' }).click()
  await expect(page.getByText(`Evidence EV-`).first()).toBeVisible()

  const derived = await (
    await page.request.get(`/api/v1/feedback/${feedback.id}/evidence`)
  ).json()
  expect(derived).toHaveLength(1)
  expect(derived[0].content, 'the customer statement is copied verbatim').toBe(statement)
  expect(derived[0].research_depth).toBe('limited')
  expect(derived[0].source_type).toBe('short_survey')
  const evidence = derived[0]

  const insight = await newInsight(page.request, projectId, 'E2E: cap blocks shower use')

  await page.goto(`/insights/${insight.id}`)
  await expect(page.getByText('Unsubstantiated').first()).toBeVisible()

  await page.getByRole('button', { name: 'Add evidence' }).first().click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText('Add evidence to this insight')).toBeVisible()

  await dialog.getByLabel('Search evidence by statement').fill('hard to open')
  await dialog.getByRole('checkbox', { name: `Select evidence ${evidence.code}` }).check()
  await dialog.getByRole('radio', { name: 'Supporting' }).click()
  await dialog.getByLabel(/Why this classification/).fill('Recurring complaint across survey responses.')
  await dialog.getByRole('button', { name: /Link 1 item\(s\) as supporting/ }).click()

  await expect(page.getByText('1 evidence item(s) linked')).toBeVisible()
  // The statement is displayed unchanged, inside the supporting group.
  await expect(page.getByText('Supporting evidence', { exact: true }).first()).toBeVisible()
  await expect(page.getByText(statement).first()).toBeVisible()
  await expect(page.getByText('Recurring complaint across survey responses.')).toBeVisible()
  await expect(page.getByText('Unsubstantiated', { exact: true })).toHaveCount(0)

  // Now a conflicting opinion about the same product, linked as contradictory.
  const conflictStatement = 'I open the cap one-handed every morning without any trouble.'
  const conflict = await createFeedbackAndEvidence(
    page.request,
    projectId,
    conflictStatement,
    'Directly disagrees with the packaging complaint.',
  )
  await page.reload()
  await page.getByRole('button', { name: 'Add evidence' }).first().click()
  const conflictDialog = page.getByRole('dialog')
  await conflictDialog.getByLabel('Search evidence by statement').fill('one-handed')
  await conflictDialog
    .getByRole('checkbox', { name: `Select evidence ${conflict.evidence.code}` })
    .check()
  await conflictDialog.getByRole('radio', { name: 'Contradictory' }).click()
  await conflictDialog
    .getByLabel(/Why this classification/)
    .fill('One participant reports no difficulty at all.')
  await conflictDialog.getByRole('button', { name: /Link 1 item\(s\) as contradictory/ }).click()
  await expect(page.getByText('1 evidence item(s) linked')).toBeVisible()

  // Both positions remain visible; the contradiction was not hidden.
  await expect(page.getByText('Contradictory evidence', { exact: true }).first()).toBeVisible()
  await expect(page.getByText(conflictStatement).first()).toBeVisible()
  await expect(page.getByText(statement).first()).toBeVisible()
})

test('the chain can be walked from evidence to insight to decision', async ({ page }) => {
  await resetDemoData(page.request)
  await enterAs(page, 'Priya Menon')

  const projectId = await firstProjectId(page.request)
  const support = await createFeedbackAndEvidence(
    page.request,
    projectId,
    'The cap is hard to open with wet hands.',
    'Same friction described independently.',
  )
  const against = await createFeedbackAndEvidence(
    page.request,
    projectId,
    'No problem at all: the cap opens easily.',
    'A genuine counter-example.',
  )
  const insight = await newInsight(page.request, projectId, 'E2E: cap friction')
  await linkViaApi(page.request, insight.id, support.evidence.id, 'supporting', 'Recurs in surveys.')
  await linkViaApi(page.request, insight.id, against.evidence.id, 'contradictory', 'One clear disagreement.')

  // Evidence → every insight that uses it, with the classification and reason.
  await page.goto(`/evidence/${support.evidence.id}`)
  await expect(page.getByText('Insights that use this evidence', { exact: true }).first()).toBeVisible()
  await expect(page.getByText(insight.title)).toBeVisible()
  await expect(page.getByText('Recurs in surveys.')).toBeVisible()

  await page.getByRole('link', { name: insight.title }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText(insight.title)
  await expect(page.getByText('The cap is hard to open with wet hands.').first()).toBeVisible()

  // Switch to the business owner to record a decision, then walk back down.
  const session = await (await page.request.get('/api/v1/session')).json()
  const owner = session.users.find((user: { role: string }) => user.role === 'business_owner')
  await switchUser(page, owner.name)

  const decision = await createDecision(page.request, projectId, insight.id)
  await page.goto(`/decisions/${decision.id}`)
  await expect(page.getByText('Reasoning chain back to the customer', { exact: true }).first()).toBeVisible()
  await expect(page.getByText(`Insight ${insight.code}`)).toBeVisible()
  await expect(page.getByText('Contradictory evidence carried through')).toBeVisible()
  await expect(page.getByText('No problem at all: the cap opens easily.').first()).toBeVisible()
  await expect(page.getByText('Gaps in the chain')).toBeVisible()
})

test('cross-project links and unauthorised writes are refused by the server', async ({ page }) => {
  await resetDemoData(page.request)
  await enterAs(page, 'Priya Menon')

  const projects = await (await page.request.get('/api/v1/projects?page_size=50')).json()
  expect(projects.items.length).toBeGreaterThan(1)
  const [projectA, projectB] = projects.items

  const foreign = await createFeedbackAndEvidence(
    page.request,
    projectB.id,
    'A survey answer from a different study entirely.',
    'Belongs to another project.',
  )
  const insight = await newInsight(page.request, projectA.id, 'E2E: cross-project guard')

  const rejected = await page.request.post(`/api/v1/insights/${insight.id}/evidence`, {
    data: { evidence_id: foreign.evidence.id, role: 'supporting', rationale: 'Attempted cross-project link.' },
  })
  expect(rejected.status()).toBe(400)
  expect((await rejected.json()).error.code).toBe('rule_violation')

  // The UI only offers evidence from the insight's own project.
  await page.goto(`/insights/${insight.id}`)
  await page.getByRole('button', { name: 'Add evidence' }).first().click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText('No unlinked evidence matches these filters.')).toBeVisible()

  // A CX user may read but must not write, and the refusal comes from the API.
  const session = await (await page.request.get('/api/v1/session')).json()
  const cx = session.users.find((user: { role: string }) => user.role === 'cx')
  const cxLogin = await page.request.post('/api/v1/auth/demo', { data: { user_id: cx.id } })
  expect(cxLogin.status()).toBe(200)

  const forbidden = await page.request.post(`/api/v1/insights/${insight.id}/evidence`, {
    data: { evidence_id: foreign.evidence.id, role: 'supporting' },
  })
  expect(forbidden.status()).toBe(403)
  expect((await forbidden.json()).error.code).toBe('forbidden')
})

test('traceability exports, and removing a link keeps the records and the audit trail', async ({
  page,
}) => {
  await resetDemoData(page.request)
  await enterAs(page, 'Priya Menon')

  const projectId = await firstProjectId(page.request)
  const created = await createFeedbackAndEvidence(
    page.request,
    projectId,
    'The pump stopped working after two weeks, so I threw the bottle away.',
    'Describes a mechanical failure rather than a preference.',
  )
  const insight = await newInsight(page.request, projectId, 'E2E: pump failure')
  await linkViaApi(
    page.request,
    insight.id,
    created.evidence.id,
    'supporting',
    'Direct statement about the failure.',
  )

  await page.goto('/settings')
  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 20_000 }),
    page.getByRole('button', { name: 'Evidence traceability', exact: true }).click(),
  ])
  expect(download.suggestedFilename()).toMatch(/^everyday-goods-traceability-(synthetic|live)\.csv$/)

  const path = await download.path()
  const raw = readFileSync(path as string, 'utf8')
  expect(raw.charCodeAt(0), 'the UTF-8 BOM is preserved').toBe(0xfeff)

  const lines = raw.replace(/^\uFEFF/, '').split(/\r?\n/).filter(Boolean)
  const header = lines[0].split(',')
  expect(header).toContain('customer_statement')
  expect(header).toContain('relationship_classification')
  expect(header).toContain('researcher_rationale')
  expect(header).toContain('verification_state')
  expect(header).not.toContain('email')

  const row = lines.find((line) => line.includes('pump stopped working'))
  expect(row, 'the exported row keeps the original statement').toBeTruthy()
  expect(row).toContain('supporting')
  expect(row).toContain('limited')
  expect(row).toContain('Direct statement about the failure.')

  // Remove the relationship through the screen; accept the confirmation.
  page.on('dialog', (dialog) => void dialog.accept())
  await page.goto(`/insights/${insight.id}`)
  await page.getByRole('button', { name: 'Remove' }).first().click()
  await expect(page.getByText('Evidence unlinked')).toBeVisible()
  await expect(page.getByText('Unsubstantiated').first()).toBeVisible()

  // The evidence record and the customer statement survive.
  await page.goto(`/evidence/${created.evidence.id}`)
  await expect(page.getByText('pump stopped working after two weeks').first()).toBeVisible()
  await expect(page.getByText('This evidence is not linked to any insight yet.')).toBeVisible()

  // The removal is attributable in the audit trail.
  await page.goto('/overview')
  await expect(page.getByText('removed as supporting evidence').first()).toBeVisible()

  // The layout holds at every supported width, with real data loaded.
  await page.goto(`/insights/${insight.id}`)
  for (const width of [375, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await expectNoHorizontalOverflow(page)
  }
})

test('an insight with only contextual evidence is not presented as supported', async ({ page }) => {
  await resetDemoData(page.request)
  await enterAs(page, 'Priya Menon')

  const projectId = await firstProjectId(page.request)
  const context = await createFeedbackAndEvidence(
    page.request,
    projectId,
    'I only use the product at the gym, so the bottle stays upright in my bag.',
    'Explains usage context; says nothing about the cap.',
  )
  const insight = await newInsight(page.request, projectId, 'E2E: context only')
  await linkViaApi(
    page.request,
    insight.id,
    context.evidence.id,
    'contextual',
    'Describes the setting, not the finding.',
  )

  await page.goto(`/insights/${insight.id}`)
  await expect(page.getByText('Contextual evidence', { exact: true }).first()).toBeVisible()
  await expect(
    page.getByText('No evidence is classified as supporting.').first(),
    'context alone must not read as support',
  ).toBeVisible()
  await expect(page.getByText('No supporting evidence. The finding rests on nothing yet.')).toBeVisible()
})
