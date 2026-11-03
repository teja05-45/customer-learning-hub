import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from 'react-bootstrap'
import { BadgeCheck, FilePlus2, MessageSquareQuote, Pencil, Plus, Search, Trash2 } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useToast } from '../app/ToastProvider'
import type {
  CollectionMethod,
  Evidence,
  FeedbackListResponse,
  FeedbackSource,
  FeedbackSourceType,
  InterviewListResponse,
  ParticipantListResponse,
  ProjectListResponse,
  VerificationStatus,
} from '../types'
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
  Notice,
  PageHeader,
  Pill,
  SectionCard,
} from '../components/ui'
import { ConfirmDialog } from '../components/ConfirmDialog'
import {
  COLLECTION_METHOD_LABELS,
  DEPTH_LABELS,
  DEPTH_TONE,
  FEEDBACK_SOURCE_LABELS,
  VERIFICATION_LABELS,
  VERIFICATION_TONE,
  formatDate,
  pluralise,
} from '../utils/format'

const SOURCE_TYPES: FeedbackSourceType[] = [
  'interview',
  'written_feedback',
  'structured_form',
  'short_survey',
  'customer_support',
  'product_review',
  'manual_entry',
  'csv_import',
]

const METHODS: CollectionMethod[] = [
  'in_person_interview',
  'video_interview',
  'phone_interview',
  'written_feedback',
  'structured_form',
  'short_survey',
  'support_feedback',
  'product_review',
  'imported_feedback',
  'manual_entry',
]

const METHOD_FOR_SOURCE: Record<FeedbackSourceType, CollectionMethod> = {
  interview: 'video_interview',
  written_feedback: 'written_feedback',
  structured_form: 'structured_form',
  short_survey: 'short_survey',
  customer_support: 'support_feedback',
  product_review: 'product_review',
  manual_entry: 'manual_entry',
  csv_import: 'imported_feedback',
}

interface FormState {
  project_id: string
  participant_id: string
  interview_id: string
  source_type: FeedbackSourceType
  collection_method: CollectionMethod
  source_reference: string
  collected_at: string
  contributor: string
  content: string
  interpretation: string
  context: string
  verification_status: VerificationStatus
}

const blankForm = (): FormState => ({
  project_id: '',
  participant_id: '',
  interview_id: '',
  source_type: 'short_survey',
  collection_method: 'short_survey',
  source_reference: '',
  collected_at: new Date().toISOString().slice(0, 10),
  contributor: '',
  content: '',
  interpretation: '',
  context: '',
  verification_status: 'unverified',
})

export function FeedbackPage() {
  const toast = useToast()
  const queryClient = useQueryClient()

  const [search, setSearch] = useState('')
  const [sourceTypes, setSourceTypes] = useState<FeedbackSourceType[]>([])
  const [verification, setVerification] = useState<VerificationStatus | ''>('')
  const [projectId, setProjectId] = useState('')
  const [attributed, setAttributed] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<FeedbackSource | null>(null)
  const [form, setForm] = useState<FormState>(blankForm)
  const [formError, setFormError] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<FeedbackSource | null>(null)

  const params = useMemo(
    () => ({
      q: search || undefined,
      source_type: sourceTypes.length ? sourceTypes : undefined,
      verification_status: verification || undefined,
      project_id: projectId || undefined,
      unattributed_only: attributed || undefined,
    }),
    [search, sourceTypes, verification, projectId, attributed],
  )

  const feedback = useQuery({
    queryKey: ['feedback', params],
    queryFn: () => api.get<FeedbackListResponse>(`/feedback${toQuery(params)}`),
  })

  const projects = useQuery({
    queryKey: ['projects', 'feedback-filter'],
    queryFn: () => api.get<ProjectListResponse>(`/projects${toQuery({ page_size: 50 })}`),
    staleTime: 60_000,
  })

  const participants = useQuery({
    queryKey: ['participants', 'feedback-form'],
    queryFn: () => api.get<ParticipantListResponse>(`/participants${toQuery({ page_size: 100 })}`),
    enabled: modalOpen,
    staleTime: 60_000,
  })

  const interviews = useQuery({
    queryKey: ['interviews', 'feedback-form', form.project_id],
    queryFn: () =>
      api.get<InterviewListResponse>(`/interviews${toQuery({ project_id: form.project_id })}`),
    enabled: modalOpen && form.source_type === 'interview' && Boolean(form.project_id),
  })

  const save = useMutation({
    mutationFn: () => {
      const payload = {
        project_id: form.project_id,
        participant_id: form.participant_id || null,
        interview_id: form.source_type === 'interview' ? form.interview_id : null,
        source_type: form.source_type,
        collection_method: form.collection_method,
        source_reference: form.source_reference,
        collected_at: new Date(`${form.collected_at}T12:00:00.000Z`).toISOString(),
        contributor: form.contributor,
        content: form.content,
        interpretation: form.interpretation,
        context: form.context,
        verification_status: form.verification_status,
      }
      return editing
        ? api.patch<FeedbackSource>(`/feedback/${editing.id}`, payload)
        : api.post<FeedbackSource>('/feedback', payload)
    },
    onSuccess: (saved) => {
      void queryClient.invalidateQueries({ queryKey: ['feedback'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setModalOpen(false)
      setEditing(null)
      setForm(blankForm())
      toast.push({
        title: editing ? 'Feedback source updated' : 'Feedback recorded',
        message: `${saved.code} · ${FEEDBACK_SOURCE_LABELS[saved.source_type]} · ${DEPTH_LABELS[saved.research_depth]} depth.`,
        variant: 'success',
      })
    },
    onError: (error) => setFormError((error as Error).message),
  })

  const verify = useMutation({
    mutationFn: (item: FeedbackSource) =>
      api.patch<FeedbackSource>(`/feedback/${item.id}`, { verification_status: 'verified' }),
    onSuccess: (saved) => {
      void queryClient.invalidateQueries({ queryKey: ['feedback'] })
      toast.push({ title: 'Source verified', message: `${saved.code} is now marked as verified.`, variant: 'success' })
    },
    onError: (error) =>
      toast.push({ title: 'Could not verify the source', message: (error as Error).message, variant: 'error' }),
  })

  const createEvidence = useMutation({
    mutationFn: (item: FeedbackSource) => api.post<Evidence>(`/feedback/${item.id}/evidence`),
    onSuccess: (evidence) => {
      void queryClient.invalidateQueries({ queryKey: ['feedback'] })
      void queryClient.invalidateQueries({ queryKey: ['evidence'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.push({
        title: `Evidence ${evidence.code} created`,
        message: 'The customer statement was copied unchanged. Open an insight to link it.',
        variant: 'success',
      })
    },
    onError: (error) =>
      toast.push({
        title: 'Could not create evidence',
        message: (error as Error).message,
        variant: 'error',
      }),
  })

  const remove = useMutation({
    mutationFn: (item: FeedbackSource) => api.delete<{ message: string }>(`/feedback/${item.id}`),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ['feedback'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setDeleteTarget(null)
      toast.push({ title: 'Feedback source deleted', message: result.message, variant: 'success' })
    },
    onError: (error) => {
      setDeleteTarget(null)
      toast.push({ title: 'Could not delete the source', message: (error as Error).message, variant: 'error' })
    },
  })

  const openCreate = () => {
    const next = blankForm()
    next.project_id = projects.data?.items[0]?.id ?? ''
    setEditing(null)
    setForm(next)
    setFormError(null)
    setModalOpen(true)
  }

  const openEdit = (item: FeedbackSource) => {
    setEditing(item)
    setForm({
      project_id: item.project_id,
      participant_id: item.participant_id ?? '',
      interview_id: item.interview_id ?? '',
      source_type: item.source_type,
      collection_method: item.collection_method,
      source_reference: item.source_reference,
      collected_at: item.collected_at.slice(0, 10),
      contributor: item.contributor,
      content: item.content,
      interpretation: item.interpretation,
      context: item.context,
      verification_status: item.verification_status,
    })
    setFormError(null)
    setModalOpen(true)
  }

  const changeSourceType = (next: FeedbackSourceType) => {
    setForm((current) => ({
      ...current,
      source_type: next,
      collection_method: METHOD_FOR_SOURCE[next],
      interview_id: next === 'interview' ? current.interview_id : '',
    }))
  }

  const toggleSource = (type: FeedbackSourceType) => {
    setSourceTypes((current) =>
      current.includes(type) ? current.filter((entry) => entry !== type) : [...current, type],
    )
  }

  const data = feedback.data
  const interviewCount = data?.source_counts.interview ?? 0
  const asynchronousCount = Math.max(0, (data?.total ?? 0) - interviewCount)

  return (
    <div className="page">
      <PageHeader
        title="Feedback sources"
        description="One record of what customers told us, however they told us. Interviews, written feedback, surveys, support notes, reviews and approved imports keep their source, date and original words."
        actions={
          <button type="button" className="btn btn-primary" onClick={openCreate}>
            <Plus size={14} /> Add feedback
          </button>
        }
      />

      <div className="section-grid grid-4 mb-3">
        <div className="stat-card">
          <div className="stat-label">Sources in view</div>
          <div className="stat-value">{data?.total ?? 0}</div>
          <div className="stat-meta">across every collection method</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Interview sources</div>
          <div className="stat-value">{interviewCount}</div>
          <div className="stat-meta">{pluralise(asynchronousCount, 'asynchronous source')}</div>
        </div>
        <div className={`stat-card${(data?.unverified_count ?? 0) > 0 ? ' is-warning' : ''}`}>
          <div className="stat-label">Not verified</div>
          <div className="stat-value">{data?.unverified_count ?? 0}</div>
          <div className="stat-meta">provenance needs a source reference</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Unattributed</div>
          <div className="stat-value">{data?.unattributed_count ?? 0}</div>
          <div className="stat-meta">kept, but labelled — never presented as representative</div>
        </div>
      </div>

      <SectionCard padded={false}>
        <div className="filter-bar">
          <div className="filter-input">
            <Search size={14} className="search-icon" />
            <input
              className="form-control"
              placeholder="Search content, source or contributor"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search feedback sources"
            />
          </div>
          <div className="inline" style={{ flexWrap: 'wrap', gap: 6 }}>
            {SOURCE_TYPES.map((type) => (
              <button
                key={type}
                type="button"
                className={`filter-chip${sourceTypes.includes(type) ? ' active' : ''}`}
                onClick={() => toggleSource(type)}
              >
                {FEEDBACK_SOURCE_LABELS[type]}
              </button>
            ))}
            <button
              type="button"
              className={`filter-chip${attributed ? ' active' : ''}`}
              onClick={() => setAttributed((value) => !value)}
            >
              Unattributed only
            </button>
          </div>
          <select
            className="form-select"
            style={{ width: 160 }}
            value={verification}
            onChange={(event) => setVerification(event.target.value as VerificationStatus | '')}
            aria-label="Filter by verification status"
          >
            <option value="">Any verification</option>
            <option value="unverified">Unverified</option>
            <option value="needs_review">Needs review</option>
            <option value="verified">Source verified</option>
          </select>
          <select
            className="form-select"
            style={{ width: 230 }}
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
            aria-label="Filter by project"
          >
            <option value="">All projects</option>
            {projects.data?.items.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </div>

        <div className="card-section">
          {feedback.isLoading && <LoadingBlock rows={6} label="Loading feedback sources…" />}
          {feedback.error && (
            <ErrorState message={(feedback.error as Error).message} onRetry={() => feedback.refetch()} />
          )}

          {data && data.items.length === 0 && (
            <EmptyState
              icon={<MessageSquareQuote size={18} />}
              title="No feedback matches this view"
              description="Not every customer can attend an interview. Add a survey answer, an approved support export or a written response, and it will sit alongside the conversations with its own provenance."
              action={
                <button type="button" className="btn btn-primary btn-sm" onClick={openCreate}>
                  <Plus size={13} /> Add the first feedback source
                </button>
              }
            />
          )}

          {data && data.items.length > 0 && (
            <div className="stack stack-3">
              {data.items.map((item) => (
                <article key={item.id} className={`feedback-card source-${item.source_type}`}>
                  <div className="row-between" style={{ alignItems: 'flex-start' }}>
                    <div className="inline" style={{ flexWrap: 'wrap', gap: 6 }}>
                      <Pill tone="outline">{FEEDBACK_SOURCE_LABELS[item.source_type]}</Pill>
                      <Pill tone={VERIFICATION_TONE[item.verification_status]}>
                        {VERIFICATION_LABELS[item.verification_status]}
                      </Pill>
                      <Pill tone={DEPTH_TONE[item.research_depth]}>{DEPTH_LABELS[item.research_depth]} depth</Pill>
                      {!item.is_attributed && <Pill tone="amber">Unattributed</Pill>}
                    </div>
                    <span className="definition mono">{item.code}</span>
                  </div>

                  <div className="feedback-source-line">
                    <span>
                      <strong>{COLLECTION_METHOD_LABELS[item.collection_method]}</strong>
                    </span>
                    {item.project && (
                      <span>
                        Project:{' '}
                        <Link to={`/projects/${item.project.id}`} className="link-quiet">
                          {item.project.label}
                        </Link>
                      </span>
                    )}
                    <span>
                      Participant:{' '}
                      {item.participant ? (
                        <Link to={`/participants/${item.participant.id}`} className="link-quiet">
                          {item.participant.label}
                        </Link>
                      ) : (
                        'Not known'
                      )}
                    </span>
                    <span>Collected {formatDate(item.collected_at)}</span>
                    <span>Contributor: {item.contributor || 'Not recorded'}</span>
                    {item.interview && (
                      <span>
                        Interview:{' '}
                        <Link to={`/interviews/${item.interview.id}`} className="link-quiet">
                          {item.interview.label}
                        </Link>
                      </span>
                    )}
                  </div>

                  <blockquote className="feedback-quote">“{item.content}”</blockquote>

                  {item.interpretation && (
                    <div className="interpretation-block">
                      <span className="label">Researcher interpretation — not the customer's words</span>
                      {item.interpretation}
                    </div>
                  )}

                  <div className="provenance-block">
                    <span className="label">Source reference</span>
                    {item.source_reference || 'No source reference recorded — this cannot be treated as verified.'}
                    {item.context && <div className="mt-2">{item.context}</div>}
                  </div>

                  <div className="row-between" style={{ alignItems: 'flex-end' }}>
                    <div className="definition" style={{ maxWidth: '62ch' }}>
                      {item.depth_note}
                    </div>
                    <div className="inline" style={{ gap: 6 }}>
                      <button
                        type="button"
                        className="btn btn-outline-secondary btn-sm"
                        disabled={createEvidence.isPending}
                        onClick={() => createEvidence.mutate(item)}
                      >
                        <FilePlus2 size={12} /> Create evidence
                      </button>
                      <button
                        type="button"
                        className="btn btn-outline-secondary btn-sm"
                        onClick={() => openEdit(item)}
                      >
                        <Pencil size={12} /> Edit
                      </button>
                      {item.verification_status !== 'verified' && (
                        <button
                          type="button"
                          className="btn btn-outline-secondary btn-sm"
                          disabled={verify.isPending}
                          onClick={() => verify.mutate(item)}
                        >
                          <BadgeCheck size={12} /> Mark verified
                        </button>
                      )}
                      <button
                        type="button"
                        className="btn btn-danger-soft btn-sm"
                        onClick={() => setDeleteTarget(item)}
                      >
                        <Trash2 size={12} /> Delete
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </SectionCard>

      <div className="mt-3">
        <Notice tone="warning" title="These sources are not equally deep">
          A moderated interview allows follow-up questions; a short survey does not. Each record states its
          collection method and depth, and the API will not mark a source verified without a source reference. No
          external system is connected: support notes, reviews and CSV imports are only present when someone with
          permission records or imports them.
        </Notice>
      </div>

      <Modal
        show={modalOpen}
        onHide={() => {
          if (!save.isPending) setModalOpen(false)
        }}
        centered
        size="lg"
        backdrop="static"
        keyboard={!save.isPending}
      >
        <Modal.Header closeButton={!save.isPending}>
          <Modal.Title>{editing ? `Edit ${editing.code}` : 'Record a feedback source'}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {formError && (
            <div className="notice notice-danger mb-3" role="alert">
              <span className="notice-icon">!</span>
              <div>{formError}</div>
            </div>
          )}

          <div className="section-grid grid-2" style={{ gap: 12 }}>
            <div>
              <label className="form-label" htmlFor="feedback-project">
                Project<span className="required-mark">*</span>
              </label>
              <select
                id="feedback-project"
                className="form-select"
                value={form.project_id}
                disabled={Boolean(editing)}
                onChange={(event) => setForm({ ...form, project_id: event.target.value, interview_id: '' })}
              >
                <option value="">Choose a project</option>
                {projects.data?.items.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
              {editing && <div className="form-text">Project links are immutable to preserve provenance.</div>}
            </div>
            <div>
              <label className="form-label" htmlFor="feedback-participant">
                Participant (optional)
              </label>
              <select
                id="feedback-participant"
                className="form-select"
                value={form.participant_id}
                onChange={(event) => setForm({ ...form, participant_id: event.target.value })}
              >
                <option value="">Unattributed / not known</option>
                {participants.data?.items.map((participant) => (
                  <option key={participant.id} value={participant.id}>
                    {participant.display_name} · {participant.code}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="form-label" htmlFor="feedback-source-type">
                Source type<span className="required-mark">*</span>
              </label>
              <select
                id="feedback-source-type"
                className="form-select"
                value={form.source_type}
                onChange={(event) => changeSourceType(event.target.value as FeedbackSourceType)}
              >
                {SOURCE_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {FEEDBACK_SOURCE_LABELS[type]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="form-label" htmlFor="feedback-method">
                Collection method<span className="required-mark">*</span>
              </label>
              <select
                id="feedback-method"
                className="form-select"
                value={form.collection_method}
                onChange={(event) =>
                  setForm({ ...form, collection_method: event.target.value as CollectionMethod })
                }
              >
                {METHODS.map((method) => (
                  <option key={method} value={method}>
                    {COLLECTION_METHOD_LABELS[method]}
                  </option>
                ))}
              </select>
            </div>

            {form.source_type === 'interview' && (
              <div>
                <label className="form-label" htmlFor="feedback-interview">
                  Interview<span className="required-mark">*</span>
                </label>
                <select
                  id="feedback-interview"
                  className="form-select"
                  value={form.interview_id}
                  onChange={(event) => setForm({ ...form, interview_id: event.target.value })}
                >
                  <option value="">Choose the interview</option>
                  {interviews.data?.items.map((interview) => (
                    <option key={interview.id} value={interview.id}>
                      {interview.code} · {interview.title}
                    </option>
                  ))}
                </select>
                <div className="form-text">An interview source must link to the conversation it came from.</div>
              </div>
            )}

            <div>
              <label className="form-label" htmlFor="feedback-collected">
                Collection date<span className="required-mark">*</span>
              </label>
              <input
                id="feedback-collected"
                type="date"
                className="form-control"
                value={form.collected_at}
                onChange={(event) => setForm({ ...form, collected_at: event.target.value })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="feedback-contributor">
                Contributor
              </label>
              <input
                id="feedback-contributor"
                className="form-control"
                placeholder="Who captured or imported this?"
                value={form.contributor}
                onChange={(event) => setForm({ ...form, contributor: event.target.value })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="feedback-verification">
                Verification
              </label>
              <select
                id="feedback-verification"
                className="form-select"
                value={form.verification_status}
                onChange={(event) =>
                  setForm({ ...form, verification_status: event.target.value as VerificationStatus })
                }
              >
                <option value="unverified">Unverified</option>
                <option value="needs_review">Needs review</option>
                <option value="verified">Source verified</option>
              </select>
            </div>
          </div>

          <div className="mt-3">
            <label className="form-label" htmlFor="feedback-reference">
              Source reference
            </label>
            <input
              id="feedback-reference"
              className="form-control"
              placeholder="Ticket ID, survey wave, file name or transcript timestamp"
              value={form.source_reference}
              onChange={(event) => setForm({ ...form, source_reference: event.target.value })}
            />
            <div className="form-text">Required before a source can be marked verified.</div>
          </div>

          <div className="mt-3">
            <label className="form-label" htmlFor="feedback-content">
              Original customer words<span className="required-mark">*</span>
            </label>
            <textarea
              id="feedback-content"
              className="form-control"
              rows={4}
              placeholder="Preserve what the customer actually said or wrote. Do not summarise it here."
              value={form.content}
              onChange={(event) => setForm({ ...form, content: event.target.value })}
            />
          </div>

          <div className="mt-3">
            <label className="form-label" htmlFor="feedback-interpretation">
              Researcher interpretation — separate from the statement
            </label>
            <textarea
              id="feedback-interpretation"
              className="form-control"
              rows={2}
              placeholder="What you think it might mean. This is stored separately and labelled as interpretation."
              value={form.interpretation}
              onChange={(event) => setForm({ ...form, interpretation: event.target.value })}
            />
          </div>

          <div className="mt-3">
            <label className="form-label" htmlFor="feedback-context">
              Context
            </label>
            <textarea
              id="feedback-context"
              className="form-control"
              rows={2}
              placeholder="Where and why was this collected?"
              value={form.context}
              onChange={(event) => setForm({ ...form, context: event.target.value })}
            />
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button
            type="button"
            className="btn btn-outline-secondary"
            disabled={save.isPending}
            onClick={() => setModalOpen(false)}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={save.isPending || !form.project_id || !form.content.trim() || !form.collected_at}
            onClick={() => {
              setFormError(null)
              save.mutate()
            }}
          >
            {save.isPending ? 'Saving…' : editing ? 'Save changes' : 'Save feedback'}
          </button>
        </Modal.Footer>
      </Modal>

      <ConfirmDialog
        show={deleteTarget !== null}
        title={`Delete ${deleteTarget?.code ?? 'feedback source'}?`}
        destructive
        confirmLabel="Delete feedback source"
        busy={remove.isPending}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) remove.mutate(deleteTarget)
        }}
      >
        <p style={{ marginBottom: 8 }}>
          The original statement and its source reference will be removed permanently. The deletion is recorded in the
          audit trail.
        </p>
        <div className="definition">This does not delete the project, the participant or the interview.</div>
      </ConfirmDialog>
    </div>
  )
}
