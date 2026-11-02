import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from 'react-bootstrap'
import { AlertTriangle, Plus, Scale, Search } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useToast } from '../app/ToastProvider'
import { useSession } from '../app/SessionProvider'
import type {
  BusinessFunction,
  DecisionDetail,
  DecisionListResponse,
  DecisionStatus,
  InsightListResponse,
  ProjectListResponse,
} from '../types'
import {
  EmptyState,
  ErrorState,
  Notice,
  PageHeader,
  Pill,
  SectionCard,
  TableSkeleton,
} from '../components/ui'
import {
  BUSINESS_FUNCTION_LABELS,
  DECISION_TONE,
  formatDate,
  titleCase,
} from '../utils/format'

const STATUSES: DecisionStatus[] = ['proposed', 'under_review', 'accepted', 'rejected', 'deferred']
const FUNCTIONS: BusinessFunction[] = [
  'growth',
  'brand_marketing',
  'product_category',
  'customer_experience',
  'operations',
  'executive',
]

export function DecisionsPage() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const { users } = useSession()
  const [search, setSearch] = useState('')
  const [statuses, setStatuses] = useState<DecisionStatus[]>([])
  const [fn, setFn] = useState<BusinessFunction | ''>('')
  const [hasEvidence, setHasEvidence] = useState<'' | 'true' | 'false'>('')
  const [createOpen, setCreateOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [form, setForm] = useState({
    title: '',
    business_function: 'growth' as BusinessFunction,
    problem_statement: '',
    description: '',
    rationale: '',
    limitations: '',
    project_id: '',
    owner_id: '',
    decision_date: new Date().toISOString().slice(0, 10),
    status: 'proposed' as DecisionStatus,
  })
  const [selectedInsights, setSelectedInsights] = useState<string[]>([])

  const params = useMemo(
    () => ({
      q: search || undefined,
      status: statuses.length ? statuses : undefined,
      business_function: fn || undefined,
      has_evidence: hasEvidence === '' ? undefined : hasEvidence === 'true',
    }),
    [search, statuses, fn, hasEvidence],
  )

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['decisions', params],
    queryFn: () => api.get<DecisionListResponse>(`/decisions${toQuery(params)}`),
  })

  const projects = useQuery({
    queryKey: ['projects', 'decision-picker'],
    queryFn: () => api.get<ProjectListResponse>(`/projects${toQuery({ page_size: 50 })}`),
    staleTime: 60_000,
  })

  const insights = useQuery({
    queryKey: ['insights', 'decision-picker', form.project_id],
    queryFn: () => api.get<InsightListResponse>(`/insights${toQuery({ project_id: form.project_id || undefined })}`),
    enabled: createOpen,
  })

  const createDecision = useMutation({
    mutationFn: () =>
      api.post<DecisionDetail>('/decisions', {
        ...form,
        project_id: form.project_id || null,
        owner_id: form.owner_id || null,
        insight_ids: selectedInsights,
      }),
    onSuccess: (decision) => {
      void queryClient.invalidateQueries({ queryKey: ['decisions'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setCreateOpen(false)
      setSelectedInsights([])
      toast.push({
        title: 'Decision recorded',
        message:
          decision.insight_count + decision.evidence_count > 0
            ? `${decision.code} links to ${decision.insight_count} insight(s).`
            : 'It is labelled as an internal judgement because no customer source is linked.',
        variant: 'success',
      })
    },
    onError: (error) => setFormError((error as Error).message),
  })

  const unevidenced = data?.unevidenced ?? 0

  return (
    <div className="page">
      <PageHeader
        title="Decisions & actions"
        description="The point of the whole system: a decision, the evidence behind it, and the person who owns what happens next."
        actions={
          <>
            <Link to="/actions" className="btn btn-outline-secondary">
              Action tracker
            </Link>
            <button type="button" className="btn btn-primary" onClick={() => setCreateOpen(true)}>
              <Plus size={14} /> Record a decision
            </button>
          </>
        }
      />

      <div className="section-grid grid-4 mb-3">
        <div className="stat-card">
          <div className="stat-label">Decisions recorded</div>
          <div className="stat-value">{data?.total ?? 0}</div>
          <div className="stat-meta">all business functions</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Accepted</div>
          <div className="stat-value">{data?.status_counts.accepted ?? 0}</div>
          <div className="stat-meta">agreed and in motion</div>
        </div>
        <div className={`stat-card${unevidenced > 0 ? ' is-warning' : ''}`}>
          <div className="stat-label">Without customer evidence</div>
          <div className="stat-value">{unevidenced}</div>
          <div className="stat-meta">labelled as internal judgement</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Awaiting review</div>
          <div className="stat-value">{(data?.status_counts.under_review ?? 0) + (data?.status_counts.proposed ?? 0)}</div>
          <div className="stat-meta">proposed or under review</div>
        </div>
      </div>

      <SectionCard padded={false}>
        <div className="filter-bar">
          <div className="filter-input">
            <Search size={14} className="search-icon" />
            <input
              className="form-control"
              placeholder="Search decisions"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search decisions"
            />
          </div>
          <div className="inline" style={{ flexWrap: 'wrap', gap: 6 }}>
            {STATUSES.map((status) => (
              <button
                key={status}
                type="button"
                className={`filter-chip${statuses.includes(status) ? ' active' : ''}`}
                onClick={() =>
                  setStatuses((current) =>
                    current.includes(status) ? current.filter((entry) => entry !== status) : [...current, status],
                  )
                }
              >
                {titleCase(status)}
              </button>
            ))}
          </div>
          <select
            className="form-select"
            style={{ width: 190 }}
            value={fn}
            onChange={(event) => setFn(event.target.value as BusinessFunction | '')}
            aria-label="Filter by business function"
          >
            <option value="">All functions</option>
            {FUNCTIONS.map((entry) => (
              <option key={entry} value={entry}>
                {BUSINESS_FUNCTION_LABELS[entry]}
              </option>
            ))}
          </select>
          <select
            className="form-select"
            style={{ width: 190 }}
            value={hasEvidence}
            onChange={(event) => setHasEvidence(event.target.value as '' | 'true' | 'false')}
            aria-label="Filter by evidence"
          >
            <option value="">Any evidence state</option>
            <option value="true">Linked to customer evidence</option>
            <option value="false">No customer evidence</option>
          </select>
        </div>

        {isLoading && <TableSkeleton rows={5} columns={6} />}
        {error && (
          <div style={{ padding: 16 }}>
            <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
          </div>
        )}
        {data && data.items.length === 0 && (
          <EmptyState
            icon={<Scale size={18} />}
            title="No decisions match this view"
            description="Record what the team decided, why, and which customer evidence it rests on. Internal judgement is allowed — pretending it is research is not."
          />
        )}

        {data && data.items.length > 0 && (
          <div className="table-wrap">
            <table className="clh-table">
              <thead>
                <tr>
                  <th>Decision</th>
                  <th>Function</th>
                  <th>Status</th>
                  <th>Evidence</th>
                  <th>Owner</th>
                  <th>Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((decision) => (
                  <tr key={decision.id}>
                    <td style={{ maxWidth: 360 }}>
                      <Link to={`/decisions/${decision.id}`} className="table-link">
                        {decision.title}
                      </Link>
                      <div className="cell-sub">{decision.code}</div>
                      {decision.insight_count + decision.evidence_count === 0 && (
                        <div className="inline mt-1" style={{ color: 'var(--clh-warning-ink)', fontSize: 11.5 }}>
                          <AlertTriangle size={12} /> No customer evidence linked
                        </div>
                      )}
                    </td>
                    <td className="text-secondary-clh">{BUSINESS_FUNCTION_LABELS[decision.business_function]}</td>
                    <td>
                      <Pill tone={DECISION_TONE[decision.status]}>{titleCase(decision.status)}</Pill>
                    </td>
                    <td>
                      <span className="mono">{decision.insight_count}</span> insight(s)
                      <div className="cell-sub">
                        {decision.evidence_count} direct · {decision.contradicting_count} contrary
                      </div>
                    </td>
                    <td className="text-secondary-clh">{decision.owner?.label ?? 'Unassigned'}</td>
                    <td>{formatDate(decision.decision_date)}</td>
                    <td>
                      {decision.open_action_count > 0 ? (
                        <Pill tone="amber">{decision.open_action_count} open</Pill>
                      ) : (
                        <span className="definition">{decision.action_count} total</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <div className="mt-3">
        <Notice tone="neutral">
          A decision with no linked evidence is not hidden — it is labelled. Some decisions are genuinely internal
          judgement, and the register should say so rather than borrowing credibility from research.
        </Notice>
      </div>

      <Modal show={createOpen} onHide={() => setCreateOpen(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Record a decision</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="section-grid grid-2" style={{ gap: 12 }}>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="decisionspage-field-1">
                Decision title<span className="required-mark">*</span>
              </label>
              <input id="decisionspage-field-1"
                className="form-control"
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
                placeholder="What was decided, in one line"
              />
            </div>
            <div>
              <label className="form-label" htmlFor="decisionspage-field-2">Business function</label>
              <select id="decisionspage-field-2"
                className="form-select"
                value={form.business_function}
                onChange={(event) => setForm({ ...form, business_function: event.target.value as BusinessFunction })}
              >
                {FUNCTIONS.map((entry) => (
                  <option key={entry} value={entry}>
                    {BUSINESS_FUNCTION_LABELS[entry]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="form-label" htmlFor="decisionspage-field-3">Status</label>
              <select id="decisionspage-field-3"
                className="form-select"
                value={form.status}
                onChange={(event) => setForm({ ...form, status: event.target.value as DecisionStatus })}
              >
                {STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {titleCase(status)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="form-label" htmlFor="decisionspage-field-4">Project</label>
              <select id="decisionspage-field-4"
                className="form-select"
                value={form.project_id}
                onChange={(event) => {
                  setForm({ ...form, project_id: event.target.value })
                  setSelectedInsights([])
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
              <label className="form-label" htmlFor="decisionspage-field-5">Decision owner</label>
              <select id="decisionspage-field-5"
                className="form-select"
                value={form.owner_id}
                onChange={(event) => setForm({ ...form, owner_id: event.target.value })}
              >
                <option value="">Assign to me</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.name}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="decisionspage-field-6">
                Problem statement<span className="required-mark">*</span>
              </label>
              <textarea id="decisionspage-field-6"
                className="form-control"
                rows={2}
                value={form.problem_statement}
                onChange={(event) => setForm({ ...form, problem_statement: event.target.value })}
                placeholder="What problem does this decision address?"
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="decisionspage-field-7">
                Decision and description<span className="required-mark">*</span>
              </label>
              <textarea id="decisionspage-field-7"
                className="form-control"
                rows={3}
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
                placeholder="What will happen, who does it, and what would make it reversible?"
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="decisionspage-field-8">Rationale</label>
              <textarea id="decisionspage-field-8"
                className="form-control"
                rows={2}
                value={form.rationale}
                onChange={(event) => setForm({ ...form, rationale: event.target.value })}
                placeholder="Why this decision, given the evidence?"
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="decisionspage-field-9">Known limitations</label>
              <textarea id="decisionspage-field-9"
                className="form-control"
                rows={2}
                value={form.limitations}
                onChange={(event) => setForm({ ...form, limitations: event.target.value })}
                placeholder="What this decision cannot rely on because the evidence does not cover it?"
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <div className="form-label" id="link-insights-label">
                Link insights ({selectedInsights.length} selected)
              </div>
              <div className="stack stack-2" style={{ maxHeight: 200, overflowY: 'auto' }}>
                {insights.data?.items.map((insight) => (
                  <label
                    key={insight.id}
                    className="card-surface"
                    style={{ padding: 9, boxShadow: 'none', display: 'flex', gap: 9, alignItems: 'flex-start' }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedInsights.includes(insight.id)}
                      onChange={(event) =>
                        setSelectedInsights((current) =>
                          event.target.checked ? [...current, insight.id] : current.filter((id) => id !== insight.id),
                        )
                      }
                    />
                    <span style={{ flex: 1 }}>
                      <span style={{ fontSize: 12.5, fontWeight: 600 }}>{insight.title}</span>
                      <span className="cell-sub d-block">
                        {insight.code} · {insight.evidence_count} evidence item(s) ·{' '}
                        {titleCase(insight.status)}
                      </span>
                    </span>
                  </label>
                ))}
                {insights.data && insights.data.items.length === 0 && (
                  <div className="definition">No insights available. You can still record the decision and label it honestly.</div>
                )}
              </div>
            </div>
          </div>
          <div className="mt-3">
            <Notice tone="warning">
              Leave the links empty and the decision will be marked as an internal judgement. That is allowed — but it
              will not be presented as evidence-backed.
            </Notice>
          </div>
          {formError && (
            <div className="mt-3">
              <Notice tone="danger">{formError}</Notice>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setCreateOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={
              form.title.length < 5 ||
              form.problem_statement.length < 10 ||
              form.description.length < 10 ||
              createDecision.isPending
            }
            onClick={() => {
              setFormError(null)
              createDecision.mutate()
            }}
          >
            {createDecision.isPending ? 'Saving…' : 'Record decision'}
          </button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
