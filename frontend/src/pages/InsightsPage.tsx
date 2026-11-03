import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from 'react-bootstrap'
import { Lightbulb, Plus, Search } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useToast } from '../app/ToastProvider'
import type {
  Confidence,
  EvidenceListResponse,
  InsightDetail,
  InsightListResponse,
  InsightStatus,
  ProjectListResponse,
  Segment,
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
import {
  CONFIDENCE_TONE,
  INSIGHT_TONE,
  SEGMENT_FILTER_LABELS,
  SEGMENT_LABELS,
  formatDate,
  titleCase,
} from '../utils/format'

const STATUSES: InsightStatus[] = ['draft', 'under_review', 'validated_internal', 'needs_more_research', 'archived']
const SEGMENTS: Segment[] = ['first_time_buyer', 'repeat_buyer', 'lapsed_buyer', 'household_buyer']

export function InsightsPage() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [statuses, setStatuses] = useState<InsightStatus[]>([])
  const [segments, setSegments] = useState<Segment[]>([])
  const [sort, setSort] = useState('recent')
  const [projectId, setProjectId] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [form, setForm] = useState({
    title: '',
    summary: '',
    research_question: '',
    project_id: '',
    status: 'draft' as InsightStatus,
    confidence: 'low' as Confidence,
    limitations: '',
  })
  const [selectedEvidence, setSelectedEvidence] = useState<string[]>([])

  const params = useMemo(
    () => ({
      q: search || undefined,
      status: statuses.length ? statuses : undefined,
      segment: segments.length ? segments : undefined,
      project_id: projectId || undefined,
      sort,
    }),
    [search, statuses, segments, projectId, sort],
  )

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['insights', params],
    queryFn: () => api.get<InsightListResponse>(`/insights${toQuery(params)}`),
  })

  const projects = useQuery({
    queryKey: ['projects', 'insight-filter'],
    queryFn: () => api.get<ProjectListResponse>(`/projects${toQuery({ page_size: 50 })}`),
    staleTime: 60_000,
  })

  const evidence = useQuery({
    queryKey: ['evidence', 'insight-picker', form.project_id],
    queryFn: () => api.get<EvidenceListResponse>(`/evidence${toQuery({ project_id: form.project_id })}`),
    enabled: createOpen && Boolean(form.project_id),
  })

  const createInsight = useMutation({
    mutationFn: () =>
      api.post<InsightDetail>('/insights', {
        ...form,
        project_id: form.project_id || null,
        evidence_ids: selectedEvidence,
      }),
    onSuccess: (insight) => {
      void queryClient.invalidateQueries({ queryKey: ['insights'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setCreateOpen(false)
      toast.push({
        title: 'Insight drafted',
        message: `${insight.code} links ${insight.evidence_count} evidence item(s).`,
        variant: 'success',
      })
    },
    onError: (error) => setFormError((error as Error).message),
  })

  const toggleStatus = (status: InsightStatus) => {
    setStatuses((current) => (current.includes(status) ? current.filter((entry) => entry !== status) : [...current, status]))
  }
  const toggleSegment = (segment: Segment) => {
    setSegments((current) => (current.includes(segment) ? current.filter((entry) => entry !== segment) : [...current, segment]))
  }

  return (
    <div className="page">
      <PageHeader
        title="Insights library"
        description="Findings that keep their evidence, their limitations and the project that produced them — so the team does not commission the same research twice."
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            <Plus size={14} /> Draft an insight
          </button>
        }
      />

      <div className="notice notice-info mb-3">
        <span className="notice-icon">i</span>
        <div>
          <strong>“Validated for internal use” means the team reviewed the evidence and context.</strong> It does not
          mean the finding is representative of the customer base. Sample size and limitations stay visible on every
          insight.
        </div>
      </div>

      <SectionCard padded={false}>
        <div className="filter-bar">
          <div className="filter-input">
            <Search size={14} className="search-icon" />
            <input
              className="form-control"
              placeholder="Search insight title, summary or research question"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search insights"
            />
          </div>
          <select
            className="form-select"
            style={{ width: 210 }}
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
          <select
            className="form-select"
            style={{ width: 170 }}
            value={sort}
            onChange={(event) => setSort(event.target.value)}
            aria-label="Sort insights"
          >
            <option value="recent">Newest first</option>
            <option value="evidence">Most evidence</option>
            <option value="confidence">Highest confidence</option>
            <option value="title">Title A–Z</option>
          </select>
        </div>
        <div className="filter-bar" style={{ paddingTop: 0, borderBottom: '1px solid var(--clh-border)' }}>
          <div className="inline" style={{ flexWrap: 'wrap', gap: 6 }}>
            {STATUSES.map((status) => (
              <button
                key={status}
                type="button"
                className={`filter-chip${statuses.includes(status) ? ' active' : ''}`}
                onClick={() => toggleStatus(status)}
              >
                {titleCase(status)}
              </button>
            ))}
          </div>
          <div className="inline" style={{ flexWrap: 'wrap', gap: 6, marginLeft: 'auto' }}>
            {SEGMENTS.map((segment) => (
              <button
                key={segment}
                type="button"
                className={`filter-chip${segments.includes(segment) ? ' active' : ''}`}
                onClick={() => toggleSegment(segment)}
              >
                {SEGMENT_FILTER_LABELS[segment]}
              </button>
            ))}
          </div>
        </div>

        <div className="card-section">
          {isLoading && <LoadingBlock rows={6} />}
          {error && <ErrorState message={(error as Error).message} onRetry={() => refetch()} />}
          {data && data.items.length === 0 && (
            <EmptyState
              icon={<Lightbulb size={18} />}
              title="No insights match this view"
              description="Insights are drafted from captured evidence. If nothing exists yet, start with a conversation, not a hypothesis."
              action={
                <Link to="/evidence" className="btn btn-outline-secondary btn-sm">
                  Review captured evidence
                </Link>
              }
            />
          )}

          {data && data.items.length > 0 && (
            <div className="stack stack-3">
              {data.items.map((insight) => (
                <article key={insight.id} className="card-surface" style={{ padding: 14 }}>
                  <div className="row-between" style={{ alignItems: 'flex-start' }}>
                    <div style={{ minWidth: 0 }}>
                      <div className="inline" style={{ gap: 7 }}>
                        <span className="mono" style={{ fontSize: 11, color: 'var(--clh-text-tertiary)' }}>
                          {insight.code}
                        </span>
                        <Pill tone={INSIGHT_TONE[insight.status]}>{titleCase(insight.status)}</Pill>
                        <Pill tone={CONFIDENCE_TONE[insight.confidence]}>{titleCase(insight.confidence)} confidence</Pill>
                        {insight.reuse_flag && <Pill tone="purple">Reused</Pill>}
                      </div>
                      <Link
                        to={`/insights/${insight.id}`}
                        style={{ display: 'block', marginTop: 8, fontSize: 14.5, fontWeight: 640, color: 'var(--clh-text)' }}
                      >
                        {insight.title}
                      </Link>
                      <p style={{ fontSize: 13, color: 'var(--clh-text-secondary)', margin: '6px 0 0' }}>
                        {insight.summary}
                      </p>
                    </div>
                    <Link to={`/insights/${insight.id}`} className="btn btn-outline-secondary btn-sm">
                      Open
                    </Link>
                  </div>

                  <div className="tag-row mt-3">
                    {insight.segments.map((segment) => (
                      <Pill key={segment} tone="outline">
                        {SEGMENT_LABELS[segment]}
                      </Pill>
                    ))}
                  </div>

                  <div
                    className="row-between mt-3"
                    style={{ borderTop: '1px solid var(--clh-border)', paddingTop: 10, fontSize: 11.5, color: 'var(--clh-text-secondary)' }}
                  >
                    <div className="inline" style={{ gap: 14 }}>
                      <span>
                        <strong style={{ color: 'var(--clh-text)' }}>{insight.evidence_count}</strong> evidence item(s)
                        {insight.contradictory_count > 0 && ` · ${insight.contradictory_count} contradictory`}
                      </span>
                      <span>
                        <strong style={{ color: 'var(--clh-text)' }}>{insight.decision_count}</strong> decision(s)
                      </span>
                      <span>{insight.project?.label ?? 'No project'}</span>
                    </div>
                    <span>
                      {insight.owner?.label ?? 'Unassigned'} · {formatDate(insight.created_at)}
                    </span>
                  </div>

                  {insight.evidence_count === 0 && (
                    <div className="mt-2">
                      <Notice tone="danger" title="No evidence linked">
                        This is a hypothesis, not a finding. It cannot be validated until evidence is attached.
                      </Notice>
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
        </div>
      </SectionCard>

      <Modal show={createOpen} onHide={() => setCreateOpen(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Draft an insight from evidence</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="stack stack-3">
            <div>
              <label className="form-label" htmlFor="insightspage-field-1">
                Title<span className="required-mark">*</span>
              </label>
              <input id="insightspage-field-1"
                className="form-control"
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
                placeholder="A claim the evidence has to carry"
              />
            </div>
            <div>
              <label className="form-label" htmlFor="insightspage-field-2">
                Summary<span className="required-mark">*</span>
              </label>
              <textarea id="insightspage-field-2"
                className="form-control"
                rows={3}
                value={form.summary}
                onChange={(event) => setForm({ ...form, summary: event.target.value })}
                placeholder="What the evidence shows, in language a busy colleague can check."
              />
            </div>
            <div className="section-grid grid-2" style={{ gap: 10 }}>
              <div>
                <label className="form-label" htmlFor="insightspage-field-3">Project</label>
                <select id="insightspage-field-3"
                  className="form-select"
                  value={form.project_id}
                  onChange={(event) => {
                    setForm({ ...form, project_id: event.target.value })
                    setSelectedEvidence([])
                  }}
                >
                  <option value="">No project</option>
                  {projects.data?.items.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="form-label" htmlFor="insightspage-field-4">Confidence</label>
                <select id="insightspage-field-4"
                  className="form-select"
                  value={form.confidence}
                  onChange={(event) => setForm({ ...form, confidence: event.target.value as Confidence })}
                >
                  <option value="low">Low — thin or mixed evidence</option>
                  <option value="medium">Medium — several consistent accounts</option>
                  <option value="high">High — consistent and context-rich</option>
                </select>
              </div>
            </div>
            <div>
              <label className="form-label" htmlFor="insightspage-field-5">Research question this answers</label>
              <input id="insightspage-field-5"
                className="form-control"
                value={form.research_question}
                onChange={(event) => setForm({ ...form, research_question: event.target.value })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="insightspage-field-6">Limitations</label>
              <textarea id="insightspage-field-6"
                className="form-control"
                rows={2}
                value={form.limitations}
                onChange={(event) => setForm({ ...form, limitations: event.target.value })}
                placeholder="Who is missing from this evidence, and what can it not tell you?"
              />
            </div>
            <div>
              <div className="form-label" id="link-evidence-label">
                Link evidence ({selectedEvidence.length} selected)
              </div>
              {!form.project_id && <div className="definition">Choose a project to see its evidence.</div>}
              {evidence.isLoading && <div className="skeleton" style={{ height: 40 }} />}
              <div className="stack stack-2" style={{ maxHeight: 220, overflowY: 'auto' }}>
                {evidence.data?.items.map((item) => (
                  <label
                    key={item.id}
                    className="card-surface"
                    style={{ padding: 9, boxShadow: 'none', display: 'flex', gap: 9, alignItems: 'flex-start' }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedEvidence.includes(item.id)}
                      onChange={(event) =>
                        setSelectedEvidence((current) =>
                          event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id),
                        )
                      }
                    />
                    <span style={{ flex: 1 }}>
                      <span className="mono" style={{ fontSize: 10.5 }}>
                        {item.code} · {titleCase(item.evidence_type)}
                      </span>
                      <span className="d-block" style={{ fontSize: 12.5 }}>
                        {item.content.slice(0, 150)}
                        {item.content.length > 150 ? '…' : ''}
                      </span>
                    </span>
                  </label>
                ))}
                {evidence.data && evidence.data.items.length === 0 && (
                  <div className="definition">No evidence on that project yet.</div>
                )}
              </div>
            </div>
            <Notice tone="warning">
              Validating an insight requires at least one linked evidence item. The API enforces that end of the rule.
            </Notice>
            {formError && <Notice tone="danger">{formError}</Notice>}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setCreateOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={form.title.length < 5 || form.summary.length < 20 || createInsight.isPending}
            onClick={() => {
              setFormError(null)
              createInsight.mutate()
            }}
          >
            {createInsight.isPending ? 'Saving…' : 'Save draft insight'}
          </button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
