import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from 'react-bootstrap'
import { ArrowLeft, CheckCircle2, Link2, Plus } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useToast } from '../app/ToastProvider'
import type { EvidenceListResponse, InsightDetail, InsightStatus, SearchResult } from '../types'
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
  CONFIDENCE_TONE,
  DECISION_TONE,
  INSIGHT_TONE,
  SEGMENT_LABELS,
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

export function InsightDetailPage() {
  const { insightId = '' } = useParams()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [linkOpen, setLinkOpen] = useState(false)
  const [selected, setSelected] = useState<string[]>([])
  const [role, setRole] = useState<'supporting' | 'contradictory'>('supporting')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['insight', insightId],
    queryFn: () => api.get<InsightDetail>(`/insights/${insightId}`),
    enabled: Boolean(insightId),
  })

  const available = useQuery({
    queryKey: ['evidence', 'insight-link', data?.project_id],
    queryFn: () => api.get<EvidenceListResponse>(`/evidence${toQuery({ project_id: data?.project_id })}`),
    enabled: linkOpen && Boolean(data?.project_id),
  })

  const related = useQuery({
    queryKey: ['insight-related', insightId],
    queryFn: () => api.get<SearchResult[]>(`/insights/${insightId}/related`),
    enabled: Boolean(insightId),
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['insight', insightId] })
    void queryClient.invalidateQueries({ queryKey: ['insights'] })
    void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    void queryClient.invalidateQueries({ queryKey: ['evidence'] })
  }

  const updateStatus = useMutation({
    mutationFn: (status: InsightStatus) => api.patch(`/insights/${insightId}`, { status }),
    onSuccess: (_data, status) => {
      invalidate()
      toast.push({
        title: status === 'validated_internal' ? 'Validated for internal use' : `Status set to ${titleCase(status)}`,
        message:
          status === 'validated_internal'
            ? 'The evidence was reviewed. This is not a claim of statistical representativeness.'
            : undefined,
        variant: 'success',
      })
    },
    onError: (error) => toast.push({ title: 'Status change rejected', message: (error as Error).message, variant: 'error' }),
  })

  const linkEvidence = useMutation({
    mutationFn: async () => {
      for (const evidenceId of selected) {
        await api.post(`/insights/${insightId}/evidence`, { evidence_id: evidenceId, role })
      }
    },
    onSuccess: () => {
      setLinkOpen(false)
      setSelected([])
      invalidate()
      toast.push({ title: 'Evidence linked', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not link evidence', message: (error as Error).message, variant: 'error' }),
  })

  const unlink = useMutation({
    mutationFn: (evidenceId: string) => api.delete(`/insights/${insightId}/evidence/${evidenceId}`),
    onSuccess: () => {
      invalidate()
      toast.push({ title: 'Evidence unlinked', message: 'The evidence record itself is unchanged.', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not unlink', message: (error as Error).message, variant: 'error' }),
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
        <PageHeader title="Insight not found" />
        <ErrorState message={(error as Error)?.message ?? 'That insight does not exist.'} onRetry={() => refetch()} />
      </div>
    )
  }

  const supporting = data.evidence.filter((item) => item.insight_links.some((link) => link.role === 'supporting'))
  const contradictory = data.evidence.filter((item) => item.insight_links.some((link) => link.role === 'contradictory'))
  const unlinkedEvidence = (available.data?.items ?? []).filter(
    (item) => !data.evidence.some((linked) => linked.id === item.id),
  )

  return (
    <div className="page">
      <Link to="/insights" className="link-quiet inline mb-3">
        <ArrowLeft size={13} /> Back to insights library
      </Link>

      <PageHeader
        title={data.title}
        description={data.summary}
        meta={
          <div className="d-flex flex-wrap gap-2 align-items-center">
            <span className="mono" style={{ fontSize: 11, color: 'var(--clh-text-tertiary)' }}>
              {data.code}
            </span>
            <Pill tone={INSIGHT_TONE[data.status]}>{titleCase(data.status)}</Pill>
            <Pill tone={CONFIDENCE_TONE[data.confidence]}>{titleCase(data.confidence)} confidence</Pill>
            {data.reuse_flag && <Pill tone="purple">Reused in later decisions</Pill>}
            {data.segments.map((segment) => (
              <Pill key={segment} tone="outline">
                {SEGMENT_LABELS[segment]}
              </Pill>
            ))}
          </div>
        }
        actions={
          <>
            {STATUS_ACTIONS.filter((action) => action.status !== data.status).map((action) => (
              <button
                key={action.status}
                type="button"
                className={action.status === 'validated_internal' ? 'btn btn-primary' : 'btn btn-outline-secondary'}
                disabled={action.status === 'validated_internal' && data.evidence_count === 0}
                title={
                  action.status === 'validated_internal' && data.evidence_count === 0
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

      {data.evidence_warning && (
        <div className="mb-3">
          <Notice tone="warning" title="Read this before using the insight">
            {data.evidence_warning}
          </Notice>
        </div>
      )}

      <div className="section-grid grid-sidebar">
        <div className="stack stack-3">
          <SectionCard title="What was observed" subtitle="Customer words, kept separate from your interpretation">
            {supporting.length === 0 ? (
              <EmptyState
                title="No supporting evidence linked"
                description="Without evidence this is a hypothesis. Link the items that actually support it."
                action={
                  <button type="button" className="btn btn-primary btn-sm" onClick={() => setLinkOpen(true)}>
                    <Link2 size={13} /> Link evidence
                  </button>
                }
              />
            ) : (
              <div className="stack stack-2">
                {supporting.map((item) => (
                  <EvidenceCard
                    key={item.id}
                    evidence={item}
                    actions={
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => unlink.mutate(item.id)}
                        disabled={unlink.isPending}
                      >
                        Unlink
                      </button>
                    }
                  />
                ))}
              </div>
            )}
          </SectionCard>

          {contradictory.length > 0 && (
            <SectionCard
              title="Evidence that pushes against this finding"
              subtitle="Kept visible on purpose. Contradiction is information, not noise."
            >
              <div className="stack stack-2">
                {contradictory.map((item) => (
                  <EvidenceCard
                    key={item.id}
                    evidence={item}
                    actions={
                      <button type="button" className="btn btn-ghost btn-sm" onClick={() => unlink.mutate(item.id)}>
                        Unlink
                      </button>
                    }
                  />
                ))}
              </div>
            </SectionCard>
          )}

          <SectionCard title="Interpretation" subtitle="Explicitly the team's reading, not the customer's words">
            <div className="interpretation-block">
              <span className="label">Researcher interpretation</span>
              <span style={{ fontSize: 13 }}>{data.interpretation || 'No separate interpretation was written.'}</span>
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
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </SectionCard>
        </div>

        <div className="stack stack-3">
          <SectionCard title="Evidence summary">
            <div className="stack stack-3">
              <MetaItem label="Supporting items" value={String(supporting.length)} />
              <MetaItem label="Contradictory items" value={String(contradictory.length)} />
              <MetaItem label="Project" value={data.project ? <Link to={`/projects/${data.project.id}`}>{data.project.label}</Link> : 'No project'} />
              <MetaItem label="Owner" value={data.owner?.label ?? 'Unassigned'} />
              <MetaItem label="Created" value={formatDate(data.created_at)} />
              <MetaItem
                label="Validated"
                value={data.validated_at ? formatDateTime(data.validated_at) : 'Not validated'}
              />
              <hr className="divider" />
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setLinkOpen(true)}>
                <Plus size={13} /> Link more evidence
              </button>
            </div>
          </SectionCard>

          <SectionCard title="Limitations" subtitle="Shown wherever the insight is reused">
            <div className="stack stack-2">
              <div className="notice notice-warning">
                <span className="notice-icon">!</span>
                <span>{data.limitations || 'No limitations recorded. That is itself a warning sign.'}</span>
              </div>
              <HonestyNote>
                “Validated for internal use” means a person reviewed the evidence and context. It is not a
                representativeness claim, and it does not make a small sample bigger.
              </HonestyNote>
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
              {data.research_question || 'No research question recorded.'}
            </div>
          </SectionCard>
        </div>
      </div>

      <Modal show={linkOpen} onHide={() => setLinkOpen(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Link evidence</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="section-grid grid-2 mb-3" style={{ gap: 10 }}>
            <div>
              <label className="form-label" htmlFor="insightdetailpage-field-1">Role</label>
              <select id="insightdetailpage-field-1" className="form-select" value={role} onChange={(event) => setRole(event.target.value as typeof role)}>
                <option value="supporting">Supporting</option>
                <option value="contradictory">Contradictory</option>
              </select>
            </div>
            <div className="definition" style={{ alignSelf: 'end' }}>
              Linking evidence does not change the evidence itself — it records how it was used.
            </div>
          </div>
          {!data.project_id && <Notice tone="warning">This insight has no project, so project evidence cannot be listed.</Notice>}
          <div className="stack stack-2" style={{ maxHeight: 320, overflowY: 'auto' }}>
            {unlinkedEvidence.map((item) => (
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
                />
                <span style={{ flex: 1 }}>
                  <span className="mono" style={{ fontSize: 10.5 }}>
                    {item.code} · {titleCase(item.evidence_type)}
                  </span>
                  <span className="d-block" style={{ fontSize: 12.5 }}>
                    “{item.content}”
                  </span>
                  <span className="definition">
                    {item.participant?.label ?? 'Unattributed'} ·{' '}
                    {item.provenance_status === 'recorded' ? 'provenance recorded' : 'provenance missing'}
                  </span>
                </span>
              </label>
            ))}
            {available.data && unlinkedEvidence.length === 0 && (
              <div className="definition">Every evidence item from this project is already linked.</div>
            )}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setLinkOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={selected.length === 0 || linkEvidence.isPending}
            onClick={() => linkEvidence.mutate()}
          >
            {linkEvidence.isPending ? 'Linking…' : `Link ${selected.length} item(s)`}
          </button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
