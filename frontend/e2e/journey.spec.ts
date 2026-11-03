import { expect, test } from '@playwright/test'

import { API_URL, enterAs, resetDemoData } from './helpers'

/**
 * End-to-end journey: question → project → participant → recruitment →
 * interview → evidence → insight → decision → action, then find it again in
 * the UI.
 *
 * The records are created through the public API so the test is deterministic
 * and fails on data problems rather than on form layout. The assertions then
 * run through the real screens: the project list, the insight editor, the
 * evidence review controls, the decision page and global search.
 */
test('a complete research-to-decision journey is visible and editable in the UI', async ({
  page,
  request,
}) => {
  await resetDemoData(request)
  await enterAs(page, 'Priya Menon')

  const session = await (await request.get(`${API_URL}/session`)).json()
  const researcher = session.users.find((user: { role: string }) => user.role === 'researcher')
  const owner = session.users.find((user: { role: string }) => user.role === 'business_owner')
  const asResearcher = { 'X-Demo-User-Id': researcher.id }
  const asOwner = { 'X-Demo-User-Id': owner.id }

  // The API context is separate from the browser cookie jar, so it signs in on
  // its own. The identity header is ignored by the server and grants nothing.
  const researcherLogin = await request.post(`${API_URL}/auth/demo`, {
    data: { user_id: researcher.id },
  })
  expect(researcherLogin.status(), 'researcher API sign-in').toBe(200)

  // 1. A project with a written business question and four target segments.
  const projectResponse = await request.post(`${API_URL}/projects`, {
    headers: asResearcher,
    data: {
      name: 'E2E: why shampoo buyers do not return',
      objective: 'Understand what stops a first shampoo purchase becoming a repeat purchase.',
      status: 'planning',
      priority: 'high',
      methodology: 'Moderated interviews',
      business_functions: ['product_category'],
      target_segments: ['first_time_buyer', 'repeat_buyer', 'household_buyer', 'lapsed_buyer'],
      questions: [{ text: 'What did buyers expect the first time they used the shampoo?' }],
    },
  })
  expect(projectResponse.status()).toBe(201)
  const project = await projectResponse.json()

  // 2-3. Synthetic participant and recruitment record.
  const participantResponse = await request.post(`${API_URL}/participants`, {
    headers: asResearcher,
    data: {
      display_name: 'E2E Synthetic Buyer',
      segment: 'first_time_buyer',
      purchase_frequency: 'One order',
      product_category: 'Hair care',
      eligibility: 'eligible',
      contact_route: 'Controlled Ops outreach (simulated)',
    },
  })
  const participant = await participantResponse.json()

  const recruitmentResponse = await request.post(`${API_URL}/recruitment`, {
    headers: asResearcher,
    data: { project_id: project.id, participant_ids: [participant.id] },
  })
  expect(recruitmentResponse.status()).toBe(201)
  const record = (await recruitmentResponse.json()).created[0]

  // 4. Invitation, response, then a scheduled interview.
  await request.patch(`${API_URL}/recruitment/${record.id}`, {
    headers: asResearcher,
    data: { stage: 'invited' },
  })
  await request.patch(`${API_URL}/recruitment/${record.id}`, {
    headers: asResearcher,
    data: { stage: 'responded' },
  })

  const interviewResponse = await request.post(`${API_URL}/interviews`, {
    headers: asResearcher,
    data: {
      project_id: project.id,
      participant_id: participant.id,
      title: 'E2E first purchase follow-up',
      scheduled_at: new Date(Date.now() - 3_600_000).toISOString(),
      status: 'scheduled',
      use_default_guide: true,
    },
  })
  expect(interviewResponse.status()).toBe(201)
  const interview = await interviewResponse.json()

  await request.post(`${API_URL}/interviews/${interview.id}/consent`, {
    headers: asResearcher,
    data: { consent_type: 'participation', status: 'granted', note: 'Synthetic consent.' },
  })
  await request.patch(`${API_URL}/interviews/${interview.id}`, {
    headers: asResearcher,
    data: { status: 'completed', summary: 'Scent expectation gap described.' },
  })

  // 5-6. Customer statement and researcher interpretation stay separate.
  const quoteResponse = await request.post(`${API_URL}/evidence`, {
    headers: asResearcher,
    data: {
      interview_id: interview.id,
      evidence_type: 'verbatim_quote',
      content: 'It smelled different from the bottle in the shop, so I did not buy it again.',
      provenance: `${interview.code} · 00:12:04`,
      customer_context: 'Answering the second-purchase question.',
    },
  })
  const quote = await quoteResponse.json()

  // 7-8. Insight with supporting and contradictory evidence.
  const contradictory = await (
    await request.post(`${API_URL}/evidence`, {
      headers: asResearcher,
      data: {
        interview_id: interview.id,
        evidence_type: 'contradictory_evidence',
        content: 'I did repurchase because the scent lasted longer than my previous brand.',
        provenance: `${interview.code} · follow-up`,
      },
    })
  ).json()

  const insightResponse = await request.post(`${API_URL}/insights`, {
    headers: asResearcher,
    data: {
      title: 'E2E: in-store scent does not survive home use',
      summary:
        'First-time buyers describe a gap between the fragrance tested in store and the product used at home.',
      interpretation: 'The team reads this as an expectation problem rather than a product defect.',
      project_id: project.id,
      confidence: 'medium',
      limitations: 'One synthetic conversation. Not representative.',
      segments: ['first_time_buyer'],
      evidence_ids: [quote.id],
    },
  })
  expect(insightResponse.status()).toBe(201)
  const insight = await insightResponse.json()

  await request.post(`${API_URL}/insights/${insight.id}/evidence`, {
    headers: asResearcher,
    data: { evidence_id: contradictory.id, role: 'contradictory' },
  })

  // 9-10. Decision plus a follow-up action with an owner. Decisions need the
  // business-owner role, so this context signs in as that user now that every
  // researcher write is complete.
  const ownerLogin = await request.post(`${API_URL}/auth/demo`, {
    data: { user_id: owner.id },
  })
  expect(ownerLogin.status(), 'owner API sign-in').toBe(200)

  const decisionResponse = await request.post(`${API_URL}/decisions`, {
    headers: asOwner,
    data: {
      title: 'E2E: test retail fragrance before reformulating',
      business_function: 'product_category',
      problem_statement: 'First-time shampoo buyers are not repurchasing as expected.',
      description: 'Run a matched in-store and at-home fragrance trial before any reformulation.',
      rationale: 'The strongest explanation is an expectation gap, not efficacy.',
      limitations: 'One synthetic conversation.',
      project_id: project.id,
      owner_id: owner.id,
      decision_date: new Date().toISOString().slice(0, 10),
      insight_ids: [insight.id],
      evidence_sufficient: true,
    },
  })
  expect(decisionResponse.status()).toBe(201)
  const decision = await decisionResponse.json()

  await request.post(`${API_URL}/decisions/${decision.id}/actions`, {
    headers: asOwner,
    data: {
      title: 'E2E: run the matched fragrance trial',
      owner_id: owner.id,
      due_date: new Date(Date.now() + 86_400_000).toISOString().slice(0, 10),
      priority: 'high',
    },
  })

  // ---- UI assertions ----------------------------------------------------
  await page.goto('/projects')
  await expect(page.getByRole('link', { name: project.name })).toBeVisible()

  await page.goto(`/projects/${project.id}`)
  await expect(page.getByRole('heading', { level: 1 })).toContainText(project.name)

  await page.goto(`/interviews/${interview.id}`)
  await expect(page.getByText('Scent expectation gap described.')).toBeVisible()

  await page.goto(`/insights/${insight.id}`)
  await expect(page.getByRole('heading', { level: 1 })).toContainText(insight.title)
  await expect(page.getByText(quote.content)).toBeVisible()

  // The insight can be edited, and the change persists.
  await page.getByRole('button', { name: 'Edit insight' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel(/^Title/).fill('E2E: edited insight title')
  await dialog.getByLabel(/^Limitations/).fill('Two synthetic conversations. Still not representative.')
  await dialog.getByRole('button', { name: 'Save changes' }).click()
  await expect(page.getByText('Insight updated')).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('E2E: edited insight title')
  await expect(page.getByText('Still not representative.')).toBeVisible()

  // Evidence review and provenance correction are available on the record.
  await page.goto(`/evidence/${quote.id}`)
  await expect(page.getByText('Source verified')).toBeVisible()
  await page.getByRole('button', { name: 'Reviewed', exact: true }).click()
  await expect(page.getByText('Review status set to Reviewed')).toBeVisible()
  await page.getByRole('button', { name: 'Correct provenance' }).click()
  const provenanceDialog = page.getByRole('dialog')
  await provenanceDialog.getByLabel('Where did this come from?').fill('')
  await provenanceDialog.getByRole('button', { name: 'Save provenance' }).click()
  await expect(page.getByText('Unverified source')).toBeVisible()

  // The decision shows the insight, the evidence and the owner's action.
  await page.goto(`/decisions/${decision.id}`)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('test retail fragrance')
  await expect(page.getByText('E2E: run the matched fragrance trial')).toBeVisible()

  // Search finds the insight and links to its evidence.
  await page.goto('/overview')
  await expect(page.getByText('Decisions with evidence')).toBeVisible()
  await page.getByRole('button', { name: /^Search/ }).click()
  const searchDialog = page.getByRole('dialog', { name: 'Search the research record' })
  await searchDialog.getByLabel('Search', { exact: true }).fill('edited insight')
  await expect(searchDialog.getByText('E2E: edited insight title').first()).toBeVisible()
})
