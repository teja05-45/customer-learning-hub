import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from 'react-bootstrap'
import { ArrowLeft, Link2, Plus } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useToast } from '../app/ToastProvider'
import { useSession } from '../app/SessionProvider'
import type {
  ActionStatus,
  BusinessAction,
  DecisionDetail,
  DecisionStatus,
  DecisionTraceability,
  EvidenceListResponse,
  InsightListResponse,
  InsightStatus,
  Priority,
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
} from '../components/ui'
import { EvidenceCard } from '../components/EvidenceCard'
import {
  ACTION_TONE,
  BUSINESS_FUNCTION_LABELS,
  CONFIDENCE_TONE,
  DECISION_TONE,
  DECISION_TRANSITIONS,
  INSIGHT_TONE,
  formatDate,
  formatDateTime,
  relativeTime,
  titleCase,
  truncate,
} from '../utils/format'

const ACTION_STATUSES: ActionStatus[] = ['not_started', 'in_progress', 'completed', 'blocked']

export function DecisionDetailPage() {
  const { decisionId = '' } = useParams()
  const toast = useToast()
  const queryClient = useQueryClient()
  const { users } = useSession()
  const [actionOpen, setActionOpen] = useState(false)
  const [linkOpen, setLinkOpen] = useState(false)
  const [selectedInsights, setSelectedInsights] = useState<string[]>([])
  const [selectedEvidence, setSelectedEvidence] = useState<string[]>([])

  const [actionForm, setActionForm] = useState({
    title: '',
    description: '',
    owner_id: '',
    due_date: '',
    priority: 'medium' as Priority,
  })
  const [actionError, setActionError] = useState<string | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['decision', decisionId],
    queryFn: () => api.get<DecisionDetail>(`/decisions/${decisionId}`),
    enabled: Boolean(decisionId),
  })

  const insights = useQuery({
    queryKey: ['insights', 'link-picker', data?.project_id],
    queryFn: () => api.get<InsightListResponse>(`/insights${toQuery({ project_id: data?.project_id ?? undefined })}`),
    enabled: linkOpen,
  })
  const evidence = useQuery({
    queryKey: ['evidence', 'link-picker', data?.project_id],
    queryFn: () => api.get<EvidenceListResponse>(`/evidence${toQuery({ project_id: data?.project_id ?? undefined })}`),
    enabled: linkOpen,
  })

  const traceability = useQuery({
    queryKey: ['decision-traceability', decisionId],
    queryFn: () => api.get<DecisionTraceability>(`/decisions/${decisionId}/traceability`),
    enabled: Boolean(decisionId),
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['decision', decisionId] })
    void queryClient.invalidateQueries({ queryKey: ['decision-traceability', decisionId] })
    void queryClient.invalidateQueries({ queryKey: ['decisions'] })
    void queryClient.invalidateQueries({ queryKey: ['actions'] })
    void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  const changeStatus = useMutation({
    mutationFn: (status: DecisionStatus) => api.patch(`/decisions/${decisionId}`, { status }),
    onSuccess: (_data, status) => {
      invalidate()
      toast.push({ title: `Decision marked ${titleCase(status).toLowerCase()}`, variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Status change rejected', message: (error as Error).message, variant: 'error' }),
  })

  const createAction = useMutation({
    mutationFn: () =>
      api.post<BusinessAction>(`/decisions/${decisionId}/actions`, {
        ...actionForm,
        owner_id: actionForm.owner_id || null,
        due_date: actionForm.due_date || null,
      }),
    onSuccess: () => {
      setActionOpen(false)
      setActionForm({ title: '', description: '', owner_id: '', due_date: '', priority: 'medium' })
      invalidate()
      toast.push({ title: 'Follow-up action created', message: 'It now has an owner and a due date.', variant: 'success' })
    },
    onError: (error) => setActionError((error as Error).message),
  })

  const updateAction = useMutation({
    mutationFn: ({ id, status }: { id: string; status: ActionStatus }) =>
      api.patch(`/actions/${id}`, { status }),
    onSuccess: () => {
      invalidate()
      toast.push({ title: 'Action updated', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not update action', message: (error as Error).message, variant: 'error' }),
  })

  const linkSources = useMutation({
    mutationFn: () =>
      api.post(`/decisions/${decisionId}/links`, {
        insight_ids: selectedInsights,
        evidence_ids: selectedEvidence,
        role: 'supporting',
      }),
    onSuccess: () => {
      setLinkOpen(false)
      setSelectedInsights([])
      setSelectedEvidence([])
      invalidate()
      toast.push({ title: 'Sources linked to the decision', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not link sources', message: (error as Error).message, variant: 'error' }),
  })

  const unlink = useMutation({
    mutationFn: ({ kind, id }: { kind: 'insight' | 'evidence'; id: string }) =>
      api.delete(`/decisions/${decisionId}/links/${kind}/${id}`),
    onSuccess: () => {
      invalidate()
      toast.push({ title: 'Link removed', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not remove link', message: (error as Error).message, variant: 'error' }),
  })

  if (isLoading) {
    return (
      <div className="page">
        <SectionCard>
          <LoadingBlock rows={7} />
        </SectionCard>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="page">
        <PageHeader title="Decision not found" />
        <ErrorState message={(error as Error)?.message ?? 'That decision does not exist.'} onRetry={() => refetch()} />
      </div>
    )
  }

  const allowed = DECISION_TRANSITIONS[data.status].filter((status) => status !== data.status)
  const unlinkedInsights = (insights.data?.items ?? []).filter(
    (insight) => !data.insights.some((linked) => linked.id === insight.id),
  )
  const unlinkedEvidence = (evidence.data?.items ?? []).filter(
    (item) => !data.evidence.some((linked) => linked.id === item.id),
  )

  return (
    <div className="page">
      <Link to="/decisions" className="link-quiet inline mb-3">
        <ArrowLeft size={13} /> Back to decision register
      </Link>

      <PageHeader
        title={data.title}
        description={data.problem_statement}
        meta={
          <div className="d-flex flex-wrap gap-2 align-items-center">
            <span className="mono" style={{ fontSize: 11, color: 'var(--clh-text-tertiary)' }}>
              {data.code}
            </span>
            <Pill tone={DECISION_TONE[data.status]}>{titleCase(data.status)}</Pill>
            <Pill tone="outline">{BUSINESS_FUNCTION_LABELS[data.business_function]}</Pill>
            <Pill tone={data.insight_count + data.evidence_count > 0 ? 'green' : 'amber'}>
              {data.insight_count + data.evidence_count > 0
                ? `${data.insight_count} insight(s) · ${data.evidence_count} evidence`
                : 'No customer evidence'}
            </Pill>
          </div>
        }
        actions={
          <>
            {allowed.map((status) => (
              <button
                key={status}
                type="button"
                className={status === 'accepted' ? 'btn btn-primary' : 'btn btn-outline-secondary'}
                onClick={() => changeStatus.mutate(status)}
                disabled={changeStatus.isPending}
              >
                Mark {titleCase(status).toLowerCase()}
              </button>
            ))}
            <button type="button" className="btn btn-primary" onClick={() => setActionOpen(true)}>
              <Plus size={14} /> Add action
            </button>
          </>
        }
      />

      {data.evidence_warning && (
        <div className="mb-3">
          <Notice tone="warning" title="Evidence check">
            {data.evidence_warning}
          </Notice>
        </div>
      )}

      <div className="section-grid grid-sidebar">
        <div className="stack stack-3">
          <SectionCard title="The decision">
            <p style={{ fontSize: 13, whiteSpace: 'pre-wrap', marginBottom: 14 }}>{data.description}</p>
            <div className="section-grid grid-2">
              <div>
                <div className="meta-label">Rationale</div>
                <div style={{ fontSize: 12.5 }}>{data.rationale || 'No rationale recorded.'}</div>
              </div>
              <div>
                <div className="meta-label">Known limitations</div>
                <div style={{ fontSize: 12.5 }}>{data.limitations || 'No limitations recorded.'}</div>
              </div>
            </div>
          </SectionCard>

          <SectionCard
            title="Linked insights"
            subtitle="The findings this decision rests on"
            actions={
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setLinkOpen(true)}>
                <Link2 size={13} /> Link sources
              </button>
            }
          >
            {data.insights.length === 0 ? (
              <EmptyState
                title="No insights linked"
                description="This decision is currently an internal judgement. That is acceptable if it is labelled honestly."
              />
            ) : (
              <div className="stack stack-2">
                {data.insights.map((insight) => (
                  <div key={insight.id} className="card-surface" style={{ padding: 12, boxShadow: 'none' }}>
                    <div className="row-between" style={{ alignItems: 'flex-start' }}>
                      <Link to={`/insights/${insight.id}`} className="table-link">
                        {insight.title}
                      </Link>
                      <Pill tone={INSIGHT_TONE[insight.status as InsightStatus]}>{titleCase(insight.status)}</Pill>
                    </div>
                    <div className="definition mt-1">
                      {insight.code} · {insight.evidence_count} evidence item(s) ·{' '}
                      <span style={{ color: 'var(--clh-text)' }}>{titleCase(insight.confidence)} confidence</span>
                      {insight.limitations ? ` · Limitation: ${insight.limitations}` : ''}
                    </div>
                    <div className="row-between mt-2">
                      <Pill tone={CONFIDENCE_TONE[insight.confidence]}>{titleCase(insight.confidence)}</Pill>
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => unlink.mutate({ kind: 'insight', id: insight.id })}
                      >
                        Unlink
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard
            title="Reasoning chain back to the customer"
            subtitle="Walk backwards from this decision to the words that informed it"
          >
            {traceability.isLoading && <LoadingBlock rows={3} label="Loading traceability…" />}
            {traceability.error && (
              <ErrorState
                message={(traceability.error as Error).message}
                onRetry={() => traceability.refetch()}
              />
            )}
            {traceability.data && (
              <div className="stack stack-3">
                <ol className="timeline" style={{ margin: 0, paddingLeft: 0, listStyle: 'none' }}>
                  {traceability.data.chain.map((step, index) => (
                    <li className="timeline-item" key={`${step}-${index}`}>
                      <span className={`timeline-dot${index === 0 ? ' current' : ''}`} />
                      <div style={{ fontSize: 12.5 }}>{step}</div>
                    </li>
                  ))}
                </ol>

                {traceability.data.insights.map((item) => (
                  <div key={item.insight.id} className="card-surface" style={{ padding: 11, boxShadow: 'none' }}>
                    <Link to={`/insights/${item.insight.id}`} className="table-link">
                      {item.insight.title}
                    </Link>
                    <div className="definition mt-1">
                      {item.support_count} supporting · {item.contradiction_count} contradictory ·{' '}
                      {item.context_count} contextual
                    </div>
                    <div className="tag-row mt-2">
                      {item.evidence.map((evidenceItem) => (
                        <Link
                          key={evidenceItem.id}
                          to={`/evidence/${evidenceItem.id}`}
                          className="pill pill-outline"
                        >
                          {evidenceItem.code} · “{truncate(evidenceItem.content, 60)}”
                        </Link>
                      ))}
                    </div>
                  </div>
                ))}

                {traceability.data.direct_evidence.length > 0 && (
                  <div>
                    <div className="meta-label mb-1">Evidence linked directly to this decision</div>
                    <div className="tag-row">
                      {traceability.data.direct_evidence.map((item) => (
                        <Link key={item.id} to={`/evidence/${item.id}`} className="pill pill-outline">
                          {item.code}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

                {traceability.data.escalated_contradictions.length > 0 && (
                  <div>
                    <div className="meta-label mb-1">Contradictory evidence carried through</div>
                    <div className="stack stack-2">
                      {traceability.data.escalated_contradictions.map((item) => (
                        <EvidenceCard key={item.id} evidence={item} />
                      ))}
                    </div>
                  </div>
                )}

                {traceability.data.gaps.length > 0 ? (
                  <Notice tone="warning" title="Gaps in the chain">
                    <ul style={{ margin: '4px 0 0 18px', padding: 0 }}>
                      {traceability.data.gaps.map((gap) => (
                        <li key={gap}>{gap}</li>
                      ))}
                    </ul>
                  </Notice>
                ) : (
                  <Notice tone="success">Every step in the chain is populated for this decision.</Notice>
                )}
              </div>
            )}
          </SectionCard>

          {data.evidence.length > 0 && (
            <SectionCard title="Evidence linked directly" subtitle="Used where no insight existed yet">
              <div className="stack stack-2">
                {data.evidence.map((item) => (
                  <EvidenceCard
                    key={item.id}
                    evidence={item}
                    actions={
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => unlink.mutate({ kind: 'evidence', id: item.id })}
                      >
                        Unlink
                      </button>
                    }
                  />
                ))}
              </div>
            </SectionCard>
          )}

          <SectionCard
            title="Follow-up actions"
            subtitle="A decision without an owner and a date is a sentiment"
            actions={
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setActionOpen(true)}>
                <Plus size={13} /> Add action
              </button>
            }
          >
            {data.actions.length === 0 ? (
              <EmptyState title="No actions yet" description="Decide who does what next, and by when." />
            ) : (
              <div className="table-wrap">
                <table className="clh-table">
                  <thead>
                    <tr>
                      <th>Action</th>
                      <th>Owner</th>
                      <th>Due</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.actions.map((action) => (
                      <tr key={action.id}>
                        <td>
                          <span style={{ fontWeight: 600 }}>{action.title}</span>
                          <div className="cell-sub">{action.code}</div>
                        </td>
                        <td className="text-secondary-clh">{action.owner?.label ?? 'Unassigned'}</td>
                        <td style={{ color: action.is_overdue ? 'var(--clh-danger)' : undefined }}>
                          {formatDate(action.due_date)}
                          {action.is_overdue && <div className="cell-sub">overdue</div>}
                        </td>
                        <td>
                          <select
                            className="form-select"
                            style={{ width: 140, fontSize: 12, padding: '3px 8px' }}
                            value={action.status}
                            onChange={(event) =>
                              updateAction.mutate({ id: action.id, status: event.target.value as ActionStatus })
                            }
                          >
                            {ACTION_STATUSES.map((status) => (
                              <option key={status} value={status}>
                                {titleCase(status)}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </div>

        <div className="stack stack-3">
          <SectionCard title="Ownership">
            <div className="stack stack-3">
              <MetaItem label="Decision owner" value={data.owner?.label ?? 'Unassigned'} />
              <MetaItem
                label="Project"
                value={data.project ? <Link to={`/projects/${data.project.id}`}>{data.project.label}</Link> : 'No project'}
              />
              <MetaItem label="Decision date" value={formatDate(data.decision_date)} />
              <MetaItem label="Recorded" value={formatDateTime(data.created_at)} />
              <MetaItem
                label="Evidence sufficient?"
                value={
                  data.evidence_sufficient === null
                    ? 'Not assessed'
                    : data.evidence_sufficient
                      ? 'Judged sufficient for this decision'
                      : 'Judged insufficient — recorded anyway'
                }
              />
            </div>
          </SectionCard>

          <SectionCard title="Decision history" subtitle="Every change is attributable">
            <div className="timeline">
              {data.history.length === 0 && <div className="definition">No history recorded.</div>}
              {data.history.map((entry, index) => (
                <div className="timeline-item" key={`${entry.at}-${index}`}>
                  <span className={`timeline-dot${index === 0 ? ' current' : ''}`} />
                  <div>
                    <div style={{ fontSize: 12.5 }}>{entry.summary}</div>
                    <div className="definition mt-1">
                      {entry.actor ?? 'System'} · {relativeTime(entry.at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Why this page matters">
            <HonestyNote>
              Six months from now, nobody will remember the conversation that prompted this decision. The link between
              the customer's words and the business action is the only thing that survives.
            </HonestyNote>
            <div className="mt-2">
              <Pill tone="outline">{ACTION_TONE[data.actions[0]?.status ?? 'not_started']} action tracking enabled</Pill>
            </div>
          </SectionCard>
        </div>
      </div>

      <Modal show={actionOpen} onHide={() => setActionOpen(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Add a follow-up action</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="stack stack-3">
            <div>
              <label className="form-label" htmlFor="decisiondetailpage-field-1">
                Action<span className="required-mark">*</span>
              </label>
              <input id="decisiondetailpage-field-1"
                className="form-control"
                value={actionForm.title}
                onChange={(event) => setActionForm({ ...actionForm, title: event.target.value })}
                placeholder="What has to happen next?"
              />
            </div>
            <div>
              <label className="form-label" htmlFor="decisiondetailpage-field-2">Description</label>
              <textarea id="decisiondetailpage-field-2"
                className="form-control"
                rows={2}
                value={actionForm.description}
                onChange={(event) => setActionForm({ ...actionForm, description: event.target.value })}
              />
            </div>
            <div className="section-grid grid-2" style={{ gap: 10 }}>
              <div>
                <label className="form-label" htmlFor="decisiondetailpage-field-3">Owner</label>
                <select id="decisiondetailpage-field-3"
                  className="form-select"
                  value={actionForm.owner_id}
                  onChange={(event) => setActionForm({ ...actionForm, owner_id: event.target.value })}
                >
                  <option value="">Assign to me</option>
                  {users.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="form-label" htmlFor="decisiondetailpage-field-4">Due date</label>
                <input id="decisiondetailpage-field-4"
                  type="date"
                  className="form-control"
                  value={actionForm.due_date}
                  onChange={(event) => setActionForm({ ...actionForm, due_date: event.target.value })}
                />
              </div>
              <div>
                <label className="form-label" htmlFor="decisiondetailpage-field-5">Priority</label>
                <select id="decisiondetailpage-field-5"
                  className="form-select"
                  value={actionForm.priority}
                  onChange={(event) => setActionForm({ ...actionForm, priority: event.target.value as Priority })}
                >
                  {['low', 'medium', 'high', 'critical'].map((priority) => (
                    <option key={priority} value={priority}>
                      {titleCase(priority)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            {actionError && <Notice tone="danger">{actionError}</Notice>}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setActionOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={actionForm.title.trim().length < 3 || createAction.isPending}
            onClick={() => {
              setActionError(null)
              createAction.mutate()
            }}
          >
            {createAction.isPending ? 'Saving…' : 'Create action'}
          </button>
        </Modal.Footer>
      </Modal>

      <Modal show={linkOpen} onHide={() => setLinkOpen(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Link insights and evidence</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="meta-label mb-2">Insights</div>
          <div className="stack stack-2" style={{ maxHeight: 190, overflowY: 'auto' }}>
            {unlinkedInsights.map((insight) => (
              <label key={insight.id} className="card-surface" style={{ padding: 9, boxShadow: 'none', display: 'flex', gap: 9 }}>
                <input
                  type="checkbox"
                  checked={selectedInsights.includes(insight.id)}
                  onChange={(event) =>
                    setSelectedInsights((current) =>
                      event.target.checked ? [...current, insight.id] : current.filter((id) => id !== insight.id),
                    )
                  }
                />
                <span>
                  <span style={{ fontSize: 12.5, fontWeight: 600 }}>{insight.title}</span>
                  <span className="cell-sub d-block">
                    {insight.code} · {insight.evidence_count} evidence · {titleCase(insight.status)}
                  </span>
                </span>
              </label>
            ))}
            {unlinkedInsights.length === 0 && <div className="definition">No further insights to link.</div>}
          </div>

          <div className="meta-label mb-2 mt-3">Evidence</div>
          <div className="stack stack-2" style={{ maxHeight: 190, overflowY: 'auto' }}>
            {unlinkedEvidence.map((item) => (
              <label key={item.id} className="card-surface" style={{ padding: 9, boxShadow: 'none', display: 'flex', gap: 9 }}>
                <input
                  type="checkbox"
                  checked={selectedEvidence.includes(item.id)}
                  onChange={(event) =>
                    setSelectedEvidence((current) =>
                      event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id),
                    )
                  }
                />
                <span>
                  <span className="mono" style={{ fontSize: 10.5 }}>
                    {item.code}
                  </span>
                  <span className="d-block" style={{ fontSize: 12.5 }}>
                    {item.content.slice(0, 140)}
                  </span>
                </span>
              </label>
            ))}
            {unlinkedEvidence.length === 0 && <div className="definition">No further evidence to link.</div>}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setLinkOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={selectedInsights.length + selectedEvidence.length === 0 || linkSources.isPending}
            onClick={() => linkSources.mutate()}
          >
            {linkSources.isPending
              ? 'Linking…'
              : `Link ${selectedInsights.length + selectedEvidence.length} source(s)`}
          </button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
