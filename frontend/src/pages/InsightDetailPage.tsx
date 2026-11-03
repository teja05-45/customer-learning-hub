import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from 'react-bootstrap'
import { ArrowLeft, CheckCircle2, Link2, Pencil, Plus, Trash2 } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useToast } from '../app/ToastProvider'
import type {
  Confidence,
  Evidence,
  EvidenceListResponse,
  EvidenceRole,
  InsightEvidenceLink,
  FeedbackSourceType,
  InsightStatus,
  InsightTraceability,
  SearchResult,
} from '../types'
import {
  EmptyState,
  ErrorState,
  HonestyNote,
  LoadingBlock,
  MetaItem,
  Notice,
  PageHeader,
  Pill,
  SectionCard,
  StatCard,
} from '../components/ui'
import { EvidenceCard } from '../components/EvidenceCard'
import {
  CLASSIFICATION_LABELS,
  CLASSIFICATION_TONE,
  CONFIDENCE_TONE,
  DECISION_TONE,
  DEPTH_LABELS,
  FEEDBACK_SOURCE_LABELS,
  INSIGHT_TONE,
  SEGMENT_LABELS,
  VERIFICATION_LABELS,
  formatDate,
  formatDateTime,
  titleCase,
} from '../utils/format'

const STATUS_ACTIONS: { status: InsightStatus; label: string }[] = [
  { status: 'under_review', label: 'Send for review' },
  { status: 'validated_internal', label: 'Validate for internal use' },
  { status: 'needs_more_research', label: 'Needs more research' },
  { status: 'archived', label: 'Archive' },
]

const SOURCE_FILTERS: (FeedbackSourceType | 'interview')[] = [
  'interview',
  'written_feedback',
  'structured_form',
  'short_survey',
  'customer_support',
  'product_review',
  'manual_entry',
  'csv_import',
]

const CLASSIFICATIONS: EvidenceRole[] = ['supporting', 'contradictory', 'contextual']

interface LinkDraft {
  classification: EvidenceRole
  rationale: string
  confidence: '' | Confidence
  tags: string
}

const blankDraft = (): LinkDraft => ({
  classification: 'supporting',
  rationale: '',
  confidence: '',
  tags: '',
})

const splitTags = (value: string): string[] =>
  value
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
    .slice(0, 8)

function RelationshipBlock({
  link,
  onEdit,
  onRemove,
  busy,
}: {
  link: InsightEvidenceLink
  onEdit: () => void
  onRemove: () => void
  busy: boolean
}) {
  return (
    <div className="card-surface" style={{ padding: 10, boxShadow: 'none' }}>
      <div className="row-between" style={{ alignItems: 'flex-start' }}>
        <div className="inline" style={{ gap: 6, flexWrap: 'wrap' }}>
          <Pill tone={CLASSIFICATION_TONE[link.classification]}>
            {CLASSIFICATION_LABELS[link.classification]} evidence
          </Pill>
          {link.confidence && (
            <Pill tone={CONFIDENCE_TONE[link.confidence]}>
              Researcher confidence: {titleCase(link.confidence)}
            </Pill>
          )}
          {link.tags.map((tag) => (
            <Pill key={tag} tone="outline">
              {tag}
            </Pill>
          ))}
        </div>
        <div className="inline" style={{ gap: 4 }}>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onEdit}>
            <Pencil size={12} /> Edit
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onRemove} disabled={busy}>
            <Trash2 size={12} /> Remove
          </button>
        </div>
      </div>
      <div className="mt-1">
        <span className="meta-label">Why this classification</span>
        <div style={{ fontSize: 12.5 }}>{link.rationale || 'No rationale recorded.'}</div>
      </div>
      <div className="definition mt-1">
        Judged by {link.created_by?.label ?? 'an unknown researcher'} · recorded{' '}
        {formatDateTime(link.created_at)}
        {link.updated_at !== link.created_at ? ` · updated ${formatDateTime(link.updated_at)}` : ''}
      </div>
    </div>
  )
}

export function InsightDetailPage() {
  const { insightId = '' } = useParams()
  const toast = useToast()
  const queryClient = useQueryClient()

  const [linkOpen, setLinkOpen] = useState(false)
  const [selected, setSelected] = useState<string[]>([])
  const [draft, setDraft] = useState<LinkDraft>(blankDraft)
  const [linkError, setLinkError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [sourceFilter, setSourceFilter] = useState<(FeedbackSourceType | 'interview')[]>([])
  const [verificationFilter, setVerificationFilter] = useState('')

  const [editingLink, setEditingLink] = useState<InsightEvidenceLink | null>(null)
  const [editDraft, setEditDraft] = useState<LinkDraft>(blankDraft)

  const [editOpen, setEditOpen] = useState(false)
  const [form, setForm] = useState({
    title: '',
    summary: '',
    interpretation: '',
    limitations: '',
    confidence: 'low' as Confidence,
  })

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['insight-traceability', insightId],
    queryFn: () => api.get<InsightTraceability>(`/insights/${insightId}/traceability`),
    enabled: Boolean(insightId),
  })

  const insight = data?.insight

  const available = useQuery({
    queryKey: ['evidence', 'insight-link', insight?.project_id, search],
    queryFn: () =>
      api.get<EvidenceListResponse>(
        `/evidence${toQuery({ project_id: insight?.project_id ?? undefined, q: search || undefined })}`,
      ),
    enabled: linkOpen && Boolean(insight?.project_id),
  })

  const related = useQuery({
    queryKey: ['insight-related', insightId],
    queryFn: () => api.get<SearchResult[]>(`/insights/${insightId}/related`),
    enabled: Boolean(insightId),
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['insight-traceability', insightId] })
    void queryClient.invalidateQueries({ queryKey: ['insight', insightId] })
    void queryClient.invalidateQueries({ queryKey: ['insights'] })
    void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    void queryClient.invalidateQueries({ queryKey: ['evidence'] })
    void queryClient.invalidateQueries({ queryKey: ['decision'] })
  }

  const updateStatus = useMutation({
    mutationFn: (status: InsightStatus) => api.patch(`/insights/${insightId}`, { status }),
    onSuccess: (_data, status) => {
      invalidate()
      toast.push({
        title: status === 'validated_internal' ? 'Validated for internal use' : `Status set to ${titleCase(status)}`,
        message:
          status === 'validated_internal'
            ? 'A person reviewed the evidence. This is not a claim of statistical representativeness.'
            : undefined,
        variant: 'success',
      })
    },
    onError: (mutationError) =>
      toast.push({ title: 'Status change rejected', message: (mutationError as Error).message, variant: 'error' }),
  })

  const openEdit = () => {
    if (!insight) return
    setForm({
      title: insight.title,
      summary: insight.summary,
      interpretation: insight.interpretation,
      limitations: insight.limitations,
      confidence: insight.confidence,
    })
    setEditOpen(true)
  }

  const updateInsight = useMutation({
    mutationFn: () =>
      api.patch(`/insights/${insightId}`, {
        title: form.title.trim(),
        summary: form.summary.trim(),
        interpretation: form.interpretation.trim(),
        limitations: form.limitations.trim(),
        confidence: form.confidence,
      }),
    onSuccess: () => {
      invalidate()
      setEditOpen(false)
      toast.push({ title: 'Insight updated', variant: 'success' })
    },
    onError: (mutationError) =>
      toast.push({ title: 'Could not save insight', message: (mutationError as Error).message, variant: 'error' }),
  })

  const linkEvidence = useMutation({
    mutationFn: async () => {
      for (const evidenceId of selected) {
        await api.post(`/insights/${insightId}/evidence`, {
          evidence_id: evidenceId,
          role: draft.classification,
          rationale: draft.rationale.trim(),
          confidence: draft.confidence || null,
          tags: splitTags(draft.tags),
        })
      }
    },
    onSuccess: () => {
      const count = selected.length
      setLinkOpen(false)
      setSelected([])
      setDraft(blankDraft())
      setSearch('')
      setSourceFilter([])
      setVerificationFilter('')
      setLinkError(null)
      invalidate()
      toast.push({
        title: `${count} evidence item(s) linked`,
        message: `Recorded as ${CLASSIFICATION_LABELS[draft.classification].toLowerCase()}. The customer statements were not changed.`,
        variant: 'success',
      })
    },
    onError: (mutationError) => setLinkError((mutationError as Error).message),
  })

  const updateRelationship = useMutation({
    mutationFn: () =>
      api.patch(`/insights/${insightId}/evidence/${editingLink?.relationship_id}`, {
        role: editDraft.classification,
        rationale: editDraft.rationale.trim(),
        confidence: editDraft.confidence || null,
        tags: splitTags(editDraft.tags),
      }),
    onSuccess: () => {
      invalidate()
      setEditingLink(null)
      toast.push({
        title: 'Relationship updated',
        message: 'Only the classification changed. The original statement is untouched.',
        variant: 'success',
      })
    },
    onError: (mutationError) =>
      toast.push({ title: 'Could not update', message: (mutationError as Error).message, variant: 'error' }),
  })

  const unlink = useMutation({
    mutationFn: (relationshipId: string) =>
      api.delete(`/insights/${insightId}/evidence/${relationshipId}`),
    onSuccess: () => {
      invalidate()
      toast.push({
        title: 'Evidence unlinked',
        message: 'The link was removed and logged. The evidence record itself is unchanged.',
        variant: 'success',
      })
    },
    onError: (mutationError) =>
      toast.push({ title: 'Could not unlink', message: (mutationError as Error).message, variant: 'error' }),
  })

  const linkedIds = useMemo(
    () =>
      new Set(
        data
          ? [
              ...data.evidence.supporting.items,
              ...data.evidence.contradictory.items,
              ...data.evidence.contextual.items,
            ].map((link) => link.evidence.id)
          : [],
      ),
    [data],
  )

  const candidates = useMemo(() => {
    return (available.data?.items ?? []).filter((item: Evidence) => {
      if (linkedIds.has(item.id)) return false
      if (sourceFilter.length) {
        const key = item.source_type ?? 'interview'
        if (!sourceFilter.includes(key as FeedbackSourceType)) return false
      }
      if (verificationFilter) {
        const state = item.verification_state ?? 'unverified'
        if (state !== verificationFilter) return false
      }
      return true
    })
  }, [available.data, linkedIds, sourceFilter, verificationFilter])

  if (isLoading) {
    return (
      <div className="page">
        <SectionCard>
          <LoadingBlock rows={7} />
        </SectionCard>
      </div>
    )
  }

  if (error || !data || !insight) {
    return (
      <div className="page">
        <PageHeader title="Insight not found" />
        <ErrorState
          message={(error as Error)?.message ?? 'That insight does not exist.'}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const { quality, evidence } = data
  const groups = [
    {
      key: 'supporting' as const,
      title: 'Supporting evidence',
      subtitle: 'Items a researcher judged to support this finding. Count is not proof.',
      group: evidence.supporting,
      empty: 'No supporting evidence. The finding rests on nothing yet.',
    },
    {
      key: 'contradictory' as const,
      title: 'Contradictory evidence',
      subtitle: 'Items that push against the finding. Kept visible on purpose.',
      group: evidence.contradictory,
      empty: 'No contradictory evidence has been recorded. That may mean none exists, or that nobody has looked.',
    },
    {
      key: 'contextual' as const,
      title: 'Contextual evidence',
      subtitle: 'Items that explain the setting without confirming or denying the finding.',
      group: evidence.contextual,
      empty: 'No contextual evidence linked.',
    },
  ]

  return (
    <div className="page">
      <Link to="/insights" className="link-quiet inline mb-3">
        <ArrowLeft size={13} /> Back to insights library
      </Link>

      <PageHeader
        title={insight.title}
        description={insight.summary}
        meta={
          <div className="d-flex flex-wrap gap-2 align-items-center">
            <span className="mono" style={{ fontSize: 11, color: 'var(--clh-text-tertiary)' }}>
              {insight.code}
            </span>
            <Pill tone={INSIGHT_TONE[insight.status]}>{titleCase(insight.status)}</Pill>
            <Pill tone={CONFIDENCE_TONE[insight.confidence]}>{titleCase(insight.confidence)} confidence</Pill>
            {insight.reuse_flag && <Pill tone="purple">Reused in later decisions</Pill>}
            {insight.segments.map((segment) => (
              <Pill key={segment} tone="outline">
                {SEGMENT_LABELS[segment]}
              </Pill>
            ))}
          </div>
        }
        actions={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={openEdit}>
              <Pencil size={13} /> Edit insight
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                setLinkError(null)
                setLinkOpen(true)
              }}
            >
              <Plus size={13} /> Add evidence
            </button>
            {STATUS_ACTIONS.filter((action) => action.status !== insight.status).map((action) => (
              <button
                key={action.status}
                type="button"
                className={action.status === 'validated_internal' ? 'btn btn-outline-secondary' : 'btn btn-outline-secondary'}
                disabled={action.status === 'validated_internal' && insight.evidence_count === 0}
                title={
                  action.status === 'validated_internal' && insight.evidence_count === 0
                    ? 'Link at least one evidence item first'
                    : undefined
                }
                onClick={() => updateStatus.mutate(action.status)}
              >
                {action.status === 'validated_internal' && <CheckCircle2 size={13} />}
                {action.label}
              </button>
            ))}
          </>
        }
      />

      <div className="section-grid grid-4 mb-3">
        <StatCard
          label="Evidence items"
          value={quality.total}
          meta={quality.unsubstantiated ? 'unsubstantiated' : `${quality.distinct_source_types} distinct source type(s)`}
          warning={quality.unsubstantiated}
          hint="Quantity of evidence, not quality of evidence."
        />
        <StatCard label="Supporting" value={quality.supporting} meta="judged to support the finding" />
        <StatCard
          label="Contradictory"
          value={quality.contradictory}
          meta={quality.has_conflict ? 'conflict is visible' : 'no contradiction recorded'}
          warning={quality.has_conflict}
        />
        <StatCard label="Contextual" value={quality.contextual} meta="setting, not support" />
        <StatCard label="Source verified" value={quality.verified} meta={`${quality.unverified} without a source`} />
        <StatCard
          label="Unattributed"
          value={quality.unattributed}
          meta="cannot be tied to a participant"
          warning={quality.unattributed > 0}
        />
        <StatCard
          label="Decisions using this"
          value={insight.decision_count}
          meta={insight.decision_count === 0 ? 'not yet used' : 'downstream of this finding'}
        />
        <StatCard
          label="Confidence"
          value={titleCase(insight.confidence)}
          meta="a researcher judgement, not a probability"
        />
      </div>

      {quality.unsubstantiated && (
        <div className="mb-3">
          <Notice tone="warning" title="Unsubstantiated">
            This insight has no linked evidence. It is a hypothesis. Anything it is used to justify should say so
            explicitly.
          </Notice>
        </div>
      )}

      {data.warnings.length > 0 && (
        <div className="mb-3">
          <Notice tone="info" title="Read this before using the insight">
            <ul style={{ margin: '4px 0 0 18px', padding: 0 }}>
              {data.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </Notice>
        </div>
      )}

      <div className="section-grid grid-sidebar">
        <div className="stack stack-3">
          {groups.map((group) => (
            <SectionCard
              key={group.key}
              title={group.title}
              subtitle={group.subtitle}
              actions={<Pill tone={CLASSIFICATION_TONE[group.key]}>{group.group.count}</Pill>}
            >
              {group.group.items.length === 0 ? (
                <EmptyState
                  title={`No ${CLASSIFICATION_LABELS[group.key].toLowerCase()} evidence`}
                  description={group.empty}
                  action={
                    group.key === 'supporting' ? (
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={() => {
                          setDraft({ ...blankDraft(), classification: 'supporting' })
                          setLinkOpen(true)
                        }}
                      >
                        <Link2 size={13} /> Add evidence
                      </button>
                    ) : undefined
                  }
                />
              ) : (
                <div className="stack stack-3">
                  {group.group.items.map((link) => (
                    <EvidenceCard
                      key={link.relationship_id}
                      evidence={link.evidence}
                      footer={
                        <RelationshipBlock
                          link={link}
                          busy={unlink.isPending}
                          onEdit={() => {
                            setEditingLink(link)
                            setEditDraft({
                              classification: link.classification,
                              rationale: link.rationale,
                              confidence: link.confidence ?? '',
                              tags: link.tags.join(', '),
                            })
                          }}
                          onRemove={() => {
                            if (window.confirm('Remove this link? The evidence and the customer statement are kept.')) {
                              unlink.mutate(link.relationship_id)
                            }
                          }}
                        />
                      }
                    />
                  ))}
                </div>
              )}
            </SectionCard>
          ))}

          <SectionCard title="Interpretation" subtitle="Explicitly the team's reading, not the customer's words">
            <div className="interpretation-block">
              <span className="label">Researcher interpretation</span>
              <span style={{ fontSize: 13 }}>{insight.interpretation || 'No separate interpretation was written.'}</span>
            </div>
          </SectionCard>

          <SectionCard title="Decisions that used this insight">
            {data.decisions.length === 0 ? (
              <EmptyState
                title="Not used in a decision yet"
                description="An insight that never reaches a decision is interesting, not useful. Record one, or deliberately close the question."
                action={
                  <Link to="/decisions" className="btn btn-outline-secondary btn-sm">
                    Go to decision register
                  </Link>
                }
              />
            ) : (
              <div className="stack stack-2">
                {data.decisions.map((decision) => (
                  <Link
                    key={decision.id}
                    to={`/decisions/${decision.id}`}
                    className="card-surface"
                    style={{ padding: 11, boxShadow: 'none', display: 'block' }}
                  >
                    <div className="row-between">
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{decision.title}</span>
                      <Pill tone={DECISION_TONE[decision.status]}>{titleCase(decision.status)}</Pill>
                    </div>
                    <div className="definition mt-1">
                      {decision.code} · {titleCase(decision.business_function)} ·{' '}
                      {formatDate(decision.decision_date)}
                      {decision.actions.length
                        ? ` · ${decision.actions.length} action(s)`
                        : ' · no action recorded'}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </SectionCard>
        </div>

        <div className="stack stack-3">
          <SectionCard title="Provenance">
            <div className="stack stack-3">
              <MetaItem
                label="Project"
                value={
                  insight.project ? (
                    <Link to={`/projects/${insight.project.id}`}>{insight.project.label}</Link>
                  ) : (
                    'No project'
                  )
                }
              />
              <MetaItem label="Owner" value={insight.owner?.label ?? 'Unassigned'} />
              <MetaItem label="Created" value={formatDate(insight.created_at)} />
              <MetaItem
                label="Validated"
                value={insight.validated_at ? formatDateTime(insight.validated_at) : 'Not validated'}
              />
              <hr className="divider" />
              <div className="definition">{data.chain_note}</div>
            </div>
          </SectionCard>

          <SectionCard title="What confidence means here">
            <div className="stack stack-2">
              <div className="definition">{quality.confidence_definition}</div>
              <HonestyNote>
                “Validated for internal use” means a person reviewed the evidence and context. It is not a
                representativeness claim, and adding more supporting quotes does not automatically validate an
                insight.
              </HonestyNote>
            </div>
          </SectionCard>

          <SectionCard title="Limitations" subtitle="Shown wherever the insight is reused">
            <div className="stack stack-2">
              <div className="notice notice-warning">
                <span className="notice-icon">!</span>
                <span>{insight.limitations || 'No limitations recorded. That is itself a warning sign.'}</span>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Related research already in the library" subtitle="Check before commissioning new outreach">
            {related.isLoading && <div className="skeleton" style={{ height: 40 }} />}
            {related.data && related.data.length === 0 && (
              <div className="definition">No overlapping keywords with other work. This may genuinely be new.</div>
            )}
            <div className="stack stack-2">
              {related.data?.map((item) => (
                <Link key={item.id} to={item.href} className="card-surface" style={{ padding: 10, boxShadow: 'none' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600 }}>{item.title}</div>
                  <div className="definition">{item.snippet}</div>
                </Link>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Research question">
            <div className="definition" style={{ fontSize: 12.5, color: 'var(--clh-text)' }}>
              {insight.research_question || 'No research question recorded.'}
            </div>
          </SectionCard>
        </div>
      </div>

      {/* ------------------------------------------------------ edit insight */}
      <Modal show={editOpen} onHide={() => setEditOpen(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Edit insight</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="stack stack-3">
            <div>
              <label className="form-label" htmlFor="insight-edit-title">
                Title<span className="required-mark">*</span>
              </label>
              <input
                id="insight-edit-title"
                className="form-control"
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="insight-edit-summary">
                What the evidence shows<span className="required-mark">*</span>
              </label>
              <textarea
                id="insight-edit-summary"
                className="form-control"
                rows={4}
                value={form.summary}
                onChange={(event) => setForm({ ...form, summary: event.target.value })}
              />
              <div className="form-text">Describe the observation, not the recommendation.</div>
            </div>
            <div>
              <label className="form-label" htmlFor="insight-edit-interpretation">
                Researcher interpretation
              </label>
              <textarea
                id="insight-edit-interpretation"
                className="form-control"
                rows={3}
                value={form.interpretation}
                onChange={(event) => setForm({ ...form, interpretation: event.target.value })}
              />
              <div className="form-text">Kept separate from the customer's words everywhere it appears.</div>
            </div>
            <div className="section-grid grid-2" style={{ gap: 12 }}>
              <div>
                <label className="form-label" htmlFor="insight-edit-confidence">
                  Confidence
                </label>
                <select
                  id="insight-edit-confidence"
                  className="form-select"
                  value={form.confidence}
                  onChange={(event) => setForm({ ...form, confidence: event.target.value as Confidence })}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <div className="definition" style={{ alignSelf: 'end' }}>
                Changing confidence is a judgement, not a recalculation.
              </div>
            </div>
            <div>
              <label className="form-label" htmlFor="insight-edit-limitations">
                Limitations
              </label>
              <textarea
                id="insight-edit-limitations"
                className="form-control"
                rows={3}
                value={form.limitations}
                onChange={(event) => setForm({ ...form, limitations: event.target.value })}
              />
              <div className="form-text">
                Sample size and what this study cannot tell you. Shown wherever the insight is reused.
              </div>
            </div>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setEditOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={form.title.trim().length < 5 || form.summary.trim().length < 20 || updateInsight.isPending}
            onClick={() => updateInsight.mutate()}
          >
            {updateInsight.isPending ? 'Saving…' : 'Save changes'}
          </button>
        </Modal.Footer>
      </Modal>

      {/* -------------------------------------------------------- add evidence */}
      <Modal
        show={linkOpen}
        onHide={() => setLinkOpen(false)}
        centered
        size="xl"
        backdrop="static"
        keyboard={!linkEvidence.isPending}
        aria-labelledby="add-evidence-title"
      >
        <Modal.Header closeButton={!linkEvidence.isPending}>
          <Modal.Title id="add-evidence-title">Add evidence to this insight</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {linkError && (
            <div className="notice notice-danger mb-3" role="alert">
              <span className="notice-icon">!</span>
              <div>{linkError}</div>
            </div>
          )}

          {!insight.project_id && (
            <Notice tone="warning">
              This insight has no project, so project evidence cannot be listed. Assign it to a project first.
            </Notice>
          )}

          <div className="filter-bar" style={{ padding: 0 }}>
            <div className="filter-input">
              <input
                className="form-control"
                placeholder="Search customer statements"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                aria-label="Search evidence by statement"
              />
            </div>
            <div className="inline" style={{ flexWrap: 'wrap', gap: 6 }}>
              {SOURCE_FILTERS.map((source) => (
                <button
                  key={source}
                  type="button"
                  className={`filter-chip${sourceFilter.includes(source) ? ' active' : ''}`}
                  onClick={() =>
                    setSourceFilter((current) =>
                      current.includes(source)
                        ? current.filter((entry) => entry !== source)
                        : [...current, source],
                    )
                  }
                >
                  {source === 'interview' ? 'Interview' : FEEDBACK_SOURCE_LABELS[source]}
                </button>
              ))}
            </div>
            <select
              className="form-select"
              style={{ width: 170 }}
              value={verificationFilter}
              onChange={(event) => setVerificationFilter(event.target.value)}
              aria-label="Filter by verification"
            >
              <option value="">Any verification</option>
              <option value="verified">Source verified</option>
              <option value="needs_review">Needs review</option>
              <option value="unverified">Unverified</option>
            </select>
          </div>

          <div className="stack stack-2 mt-3" style={{ maxHeight: 280, overflowY: 'auto' }}>
            {available.isLoading && <LoadingBlock rows={3} label="Loading evidence…" />}
            {available.error && (
              <ErrorState message={(available.error as Error).message} onRetry={() => available.refetch()} />
            )}
            {!available.isLoading && candidates.length === 0 && (
              <div className="definition">
                No unlinked evidence matches these filters. Record feedback first, then derive evidence from it.
              </div>
            )}
            {candidates.map((item) => (
              <label
                key={item.id}
                className="card-surface"
                style={{ padding: 10, boxShadow: 'none', display: 'flex', gap: 9, alignItems: 'flex-start' }}
              >
                <input
                  type="checkbox"
                  checked={selected.includes(item.id)}
                  onChange={(event) =>
                    setSelected((current) =>
                      event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id),
                    )
                  }
                  aria-label={`Select evidence ${item.code}`}
                />
                <span style={{ flex: 1 }}>
                  <span className="mono" style={{ fontSize: 10.5 }}>
                    {item.code} ·{' '}
                    {item.source_type === 'interview'
                      ? 'Interview'
                      : item.source_type
                        ? FEEDBACK_SOURCE_LABELS[item.source_type]
                        : titleCase(item.evidence_type)}
                  </span>
                  <span className="d-block" style={{ fontSize: 12.5 }}>
                    “{item.content}”
                  </span>
                  <span className="definition">
                    {item.participant?.label ?? 'Unattributed'} ·{' '}
                    {item.research_depth ? `${DEPTH_LABELS[item.research_depth]} depth` : 'depth not recorded'} ·{' '}
                    {item.verification_state
                      ? VERIFICATION_LABELS[item.verification_state]
                      : 'verification not recorded'}{' '}
                    · collected {formatDate(item.collected_at)}
                  </span>
                  {item.provenance_warning && (
                    <span className="d-block" style={{ fontSize: 11.5, color: 'var(--clh-danger)' }}>
                      {item.provenance_warning}
                    </span>
                  )}
                </span>
              </label>
            ))}
          </div>

          <div className="section-grid grid-2 mt-3" style={{ gap: 12 }}>
            <div>
              <span className="form-label" id="classification-label">
                How is this evidence used?<span className="required-mark">*</span>
              </span>
              <div role="radiogroup" aria-labelledby="classification-label" className="inline" style={{ gap: 6 }}>
                {CLASSIFICATIONS.map((classification) => (
                  <button
                    key={classification}
                    type="button"
                    role="radio"
                    aria-checked={draft.classification === classification}
                    className={`filter-chip${draft.classification === classification ? ' active' : ''}`}
                    onClick={() => setDraft({ ...draft, classification })}
                  >
                    {CLASSIFICATION_LABELS[classification]}
                  </button>
                ))}
              </div>
              <div className="form-text">
                Supporting, contradictory or contextual are separate assessments. Nothing is supporting by default.
              </div>
            </div>
            <div>
              <label className="form-label" htmlFor="link-confidence">
                Researcher confidence (optional)
              </label>
              <select
                id="link-confidence"
                className="form-select"
                value={draft.confidence}
                onChange={(event) => setDraft({ ...draft, confidence: event.target.value as '' | Confidence })}
              >
                <option value="">Not assessed</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
              <div className="form-text">A judgement about relevance, not a probability.</div>
            </div>
          </div>

          <div className="mt-2">
            <label className="form-label" htmlFor="link-rationale">
              Why this classification?<span className="required-mark">*</span>
            </label>
            <textarea
              id="link-rationale"
              className="form-control"
              rows={2}
              value={draft.rationale}
              onChange={(event) => setDraft({ ...draft, rationale: event.target.value })}
              placeholder="e.g. Repeats across three segments; the customer describes the same moment."
            />
          </div>

          <div className="mt-2">
            <label className="form-label" htmlFor="link-tags">
              Tags (optional, comma separated)
            </label>
            <input
              id="link-tags"
              className="form-control"
              value={draft.tags}
              onChange={(event) => setDraft({ ...draft, tags: event.target.value })}
              placeholder="packaging, accessibility"
            />
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={() => setLinkOpen(false)}
            disabled={linkEvidence.isPending}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={
              selected.length === 0 ||
              draft.rationale.trim().length < 3 ||
              linkEvidence.isPending ||
              !insight.project_id
            }
            onClick={() => {
              setLinkError(null)
              linkEvidence.mutate()
            }}
          >
            {linkEvidence.isPending
              ? 'Linking…'
              : `Link ${selected.length} item(s) as ${CLASSIFICATION_LABELS[draft.classification].toLowerCase()}`}
          </button>
        </Modal.Footer>
      </Modal>

      {/* ------------------------------------------------- edit relationship */}
      <Modal
        show={editingLink !== null}
        onHide={() => setEditingLink(null)}
        centered
        aria-labelledby="edit-relationship-title"
      >
        <Modal.Header closeButton>
          <Modal.Title id="edit-relationship-title">Edit relationship</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="stack stack-3">
            <div className="provenance-block">
              <span className="label">Original customer statement — unchanged</span>
              <div style={{ fontSize: 12.5 }}>“{editingLink?.evidence.content}”</div>
            </div>
            <div>
              <span className="form-label" id="edit-classification-label">
                Classification
              </span>
              <div role="radiogroup" aria-labelledby="edit-classification-label" className="inline" style={{ gap: 6 }}>
                {CLASSIFICATIONS.map((classification) => (
                  <button
                    key={classification}
                    type="button"
                    role="radio"
                    aria-checked={editDraft.classification === classification}
                    className={`filter-chip${editDraft.classification === classification ? ' active' : ''}`}
                    onClick={() => setEditDraft({ ...editDraft, classification })}
                  >
                    {CLASSIFICATION_LABELS[classification]}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="form-label" htmlFor="edit-rationale">
                Why this classification?
              </label>
              <textarea
                id="edit-rationale"
                className="form-control"
                rows={3}
                value={editDraft.rationale}
                onChange={(event) => setEditDraft({ ...editDraft, rationale: event.target.value })}
              />
            </div>
            <div className="section-grid grid-2" style={{ gap: 10 }}>
              <div>
                <label className="form-label" htmlFor="edit-confidence">
                  Confidence
                </label>
                <select
                  id="edit-confidence"
                  className="form-select"
                  value={editDraft.confidence}
                  onChange={(event) =>
                    setEditDraft({ ...editDraft, confidence: event.target.value as '' | Confidence })
                  }
                >
                  <option value="">Not assessed</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <div>
                <label className="form-label" htmlFor="edit-tags">
                  Tags
                </label>
                <input
                  id="edit-tags"
                  className="form-control"
                  value={editDraft.tags}
                  onChange={(event) => setEditDraft({ ...editDraft, tags: event.target.value })}
                />
              </div>
            </div>
            <div className="definition">
              Changing the classification never edits the evidence. The original statement and its source remain as
              collected.
            </div>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setEditingLink(null)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={editDraft.rationale.trim().length < 3 || updateRelationship.isPending}
            onClick={() => updateRelationship.mutate()}
          >
            {updateRelationship.isPending ? 'Saving…' : 'Save relationship'}
          </button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
