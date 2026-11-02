import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal, Button } from 'react-bootstrap'
import { Archive, ArrowLeft, CheckCircle2, Circle, Pencil } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useToast } from '../app/ToastProvider'
import { useSession } from '../app/SessionProvider'
import type {
  DecisionListResponse,
  EvidenceListResponse,
  InsightListResponse,
  InterviewListResponse,
  ProjectDetail,
  RecruitmentListResponse,
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
  TableSkeleton,
} from '../components/ui'
import { ConfirmDialog } from '../components/ConfirmDialog'
import {
  CONFIDENCE_TONE,
  DECISION_TONE,
  INSIGHT_TONE,
  INTERVIEW_TONE,
  PRIORITY_TONE,
  PROJECT_STATUS_TONE,
  SEGMENT_LABELS,
  formatDate,
  formatDateTime,
  titleCase,
} from '../utils/format'

export function ProjectDetailPage() {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()
  const { users } = useSession()
  const [tab, setTab] = useState('questions')
  const [editing, setEditing] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)

  const projectQuery = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.get<ProjectDetail>(`/projects/${projectId}`),
    enabled: Boolean(projectId),
  })

  const project = projectQuery.data

  const interviews = useQuery({
    queryKey: ['interviews', { projectId }],
    queryFn: () => api.get<InterviewListResponse>(`/interviews${toQuery({ project_id: projectId })}`),
    enabled: Boolean(projectId),
  })
  const evidence = useQuery({
    queryKey: ['evidence', { projectId }],
    queryFn: () => api.get<EvidenceListResponse>(`/evidence${toQuery({ project_id: projectId })}`),
    enabled: Boolean(projectId),
  })
  const insights = useQuery({
    queryKey: ['insights', { projectId }],
    queryFn: () => api.get<InsightListResponse>(`/insights${toQuery({ project_id: projectId })}`),
    enabled: Boolean(projectId),
  })
  const decisions = useQuery({
    queryKey: ['decisions', { projectId }],
    queryFn: () => api.get<DecisionListResponse>(`/decisions${toQuery({ project_id: projectId })}`),
    enabled: Boolean(projectId),
  })
  const recruitment = useQuery({
    queryKey: ['recruitment', { projectId }],
    queryFn: () => api.get<RecruitmentListResponse>(`/recruitment${toQuery({ project_id: projectId })}`),
    enabled: Boolean(projectId),
  })

  const [form, setForm] = useState({
    name: '',
    objective: '',
    status: 'planning',
    priority: 'medium',
    deadline: '',
    owner_id: '',
  })

  useEffect(() => {
    if (project) {
      setForm({
        name: project.name,
        objective: project.objective,
        status: project.status,
        priority: project.priority,
        deadline: project.deadline ?? '',
        owner_id: project.owner_id ?? '',
      })
    }
  }, [project])

  const updateProject = useMutation({
    mutationFn: () =>
      api.patch<ProjectDetail>(`/projects/${projectId}`, {
        ...form,
        deadline: form.deadline || null,
        owner_id: form.owner_id || null,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setEditing(false)
      toast.push({ title: 'Project updated', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Update failed', message: (error as Error).message, variant: 'error' }),
  })

  const archiveProject = useMutation({
    mutationFn: () => api.post(`/projects/${projectId}/archive`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
      setArchiveOpen(false)
      toast.push({
        title: 'Project archived',
        message: 'Evidence and insights remain available in the library.',
        variant: 'success',
      })
    },
    onError: (error) => toast.push({ title: 'Could not archive', message: (error as Error).message, variant: 'error' }),
  })

  const toggleQuestion = useMutation({
    mutationFn: ({ id, resolved, note }: { id: string; resolved: boolean; note: string }) =>
      api.patch(`/projects/${projectId}/questions/${id}`, {
        text: project?.questions.find((question) => question.id === id)?.text ?? '',
        is_resolved: resolved,
        resolution_note: note,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      toast.push({ title: 'Research question updated', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not update question', message: (error as Error).message, variant: 'error' }),
  })

  if (projectQuery.isLoading) {
    return (
      <div className="page">
        <div className="skeleton mb-3" style={{ width: 220, height: 24 }} />
        <SectionCard>
          <LoadingBlock rows={6} />
        </SectionCard>
      </div>
    )
  }

  if (projectQuery.error || !project) {
    return (
      <div className="page">
        <PageHeader title="Project not found" description="The project may have been removed." />
        <ErrorState
          message={(projectQuery.error as Error)?.message ?? 'That research project does not exist.'}
          onRetry={() => projectQuery.refetch()}
        />
      </div>
    )
  }

  const tabs = [
    { key: 'questions', label: 'Questions & context', count: project.questions.length },
    { key: 'recruitment', label: 'Recruitment', count: recruitment.data?.total ?? 0 },
    { key: 'interviews', label: 'Interviews', count: interviews.data?.total ?? 0 },
    { key: 'evidence', label: 'Evidence', count: evidence.data?.total ?? 0 },
    { key: 'insights', label: 'Insights', count: insights.data?.total ?? 0 },
    { key: 'decisions', label: 'Decisions', count: decisions.data?.total ?? 0 },
  ]

  return (
    <div className="page">
      <Link to="/projects" className="link-quiet inline mb-3">
        <ArrowLeft size={13} /> Back to research projects
      </Link>

      <PageHeader
        title={project.name}
        description={project.objective}
        meta={
          <div className="d-flex flex-wrap gap-2 align-items-center">
            <Pill tone={PROJECT_STATUS_TONE[project.status]}>{titleCase(project.status)}</Pill>
            <Pill tone={PRIORITY_TONE[project.priority]}>{titleCase(project.priority)} priority</Pill>
            {project.business_functions.map((fn) => (
              <Pill key={fn} tone="outline">
                {titleCase(fn)}
              </Pill>
            ))}
          </div>
        }
        actions={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setEditing(true)}>
              <Pencil size={13} /> Edit project
            </button>
            {project.status !== 'archived' && (
              <button type="button" className="btn btn-outline-secondary" onClick={() => setArchiveOpen(true)}>
                <Archive size={13} /> Archive
              </button>
            )}
          </>
        }
      />

      <div className="section-grid grid-sidebar">
        <div className="stack stack-3">
          <div className="card-surface">
            <div className="filter-bar" style={{ borderBottom: '1px solid var(--clh-border)', borderRadius: 10 }}>
              {tabs.map((entry) => (
                <button
                  key={entry.key}
                  type="button"
                  className={`filter-chip${tab === entry.key ? ' active' : ''}`}
                  onClick={() => setTab(entry.key)}
                >
                  {entry.label} · {entry.count}
                </button>
              ))}
            </div>

            <div className="card-section">
              {tab === 'questions' && (
                <div className="stack stack-3">
                  <div>
                    <div className="meta-label mb-2">Research questions</div>
                    {project.questions.length === 0 ? (
                      <EmptyState title="No research questions" description="Add the uncertainties this project should reduce." />
                    ) : (
                      <div className="stack stack-2">
                        {project.questions.map((question) => (
                          <div
                            key={question.id}
                            className="card-surface"
                            style={{ padding: '10px 12px', boxShadow: 'none' }}
                          >
                            <div className="d-flex gap-2 align-items-start">
                              <button
                                type="button"
                                className="btn btn-ghost btn-sm"
                                style={{ padding: 0, marginTop: 1 }}
                                aria-label={question.is_resolved ? 'Mark unresolved' : 'Mark resolved'}
                                onClick={() =>
                                  toggleQuestion.mutate({
                                    id: question.id,
                                    resolved: !question.is_resolved,
                                    note: question.resolution_note,
                                  })
                                }
                              >
                                {question.is_resolved ? (
                                  <CheckCircle2 size={16} color="var(--clh-success)" />
                                ) : (
                                  <Circle size={16} color="var(--clh-text-tertiary)" />
                                )}
                              </button>
                              <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 13, fontWeight: 550 }}>{question.text}</div>
                                {question.is_resolved ? (
                                  <div className="definition mt-1">
                                    Resolved — {question.resolution_note || 'no note recorded'}
                                  </div>
                                ) : (
                                  <div className="definition mt-1">Unresolved</div>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <hr className="divider" />
                  <div>
                    <div className="meta-label mb-1">Why this project exists</div>
                    <p style={{ fontSize: 13, color: 'var(--clh-text-secondary)', whiteSpace: 'pre-wrap' }}>
                      {project.description || 'No additional context was recorded.'}
                    </p>
                  </div>

                  <div className="section-grid grid-2">
                    <MetaItem label="Method" value={project.methodology || 'Not set'} />
                    <MetaItem label="Owner" value={project.owner?.label ?? 'Unassigned'} />
                    <MetaItem label="Start" value={formatDate(project.start_date)} />
                    <MetaItem label="Deadline" value={formatDate(project.deadline)} />
                    <MetaItem
                      label="Target segments"
                      value={
                        project.target_segments.length
                          ? project.target_segments.map((segment) => SEGMENT_LABELS[segment]).join(', ')
                          : 'None set'
                      }
                    />
                    <MetaItem label="Last updated" value={formatDateTime(project.updated_at)} />
                  </div>
                </div>
              )}

              {tab === 'recruitment' && (
                <>
                  {recruitment.isLoading && <TableSkeleton rows={4} columns={4} />}
                  {recruitment.error && <ErrorState message={(recruitment.error as Error).message} onRetry={() => recruitment.refetch()} />}
                  {recruitment.data && recruitment.data.items.length === 0 && (
                    <EmptyState
                      title="Nobody on the recruitment list"
                      description="Add synthetic participants and record who was invited, who replied and who declined."
                      action={
                        <Link to="/recruitment" className="btn btn-primary btn-sm">
                          Open recruitment pipeline
                        </Link>
                      }
                    />
                  )}
                  {recruitment.data && recruitment.data.items.length > 0 && (
                    <div className="table-wrap">
                      <table className="clh-table">
                        <thead>
                          <tr>
                            <th>Participant</th>
                            <th>Segment</th>
                            <th>Stage</th>
                            <th>Next action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {recruitment.data.items.map((record) => (
                            <tr key={record.id}>
                              <td>
                                <Link to={`/participants/${record.participant_id}`} className="table-link">
                                  {record.participant?.display_name}
                                </Link>
                                <div className="cell-sub">{record.participant?.code}</div>
                              </td>
                              <td className="text-secondary-clh">
                                {record.participant ? SEGMENT_LABELS[record.participant.segment] : '—'}
                              </td>
                              <td>
                                <Pill tone="blue">{titleCase(record.stage)}</Pill>
                              </td>
                              <td style={{ maxWidth: 280 }} className="text-secondary-clh">
                                {record.next_action || '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {recruitment.data?.warnings.map((warning) => (
                    <div key={warning} className="mt-2">
                      <Notice tone="warning">{warning}</Notice>
                    </div>
                  ))}
                </>
              )}

              {tab === 'interviews' && (
                <>
                  {interviews.isLoading && <TableSkeleton rows={4} columns={4} />}
                  {interviews.data && interviews.data.items.length === 0 && (
                    <EmptyState title="No interviews yet" description="Schedule a conversation with a recruit who has agreed to take part." />
                  )}
                  {interviews.data && interviews.data.items.length > 0 && (
                    <div className="table-wrap">
                      <table className="clh-table">
                        <thead>
                          <tr>
                            <th>Interview</th>
                            <th>Participant</th>
                            <th>Status</th>
                            <th>Scheduled</th>
                            <th>Evidence</th>
                          </tr>
                        </thead>
                        <tbody>
                          {interviews.data.items.map((interview) => (
                            <tr key={interview.id}>
                              <td>
                                <Link to={`/interviews/${interview.id}`} className="table-link">
                                  {interview.title}
                                </Link>
                                <div className="cell-sub">{interview.code}</div>
                              </td>
                              <td className="text-secondary-clh">{interview.participant?.display_name}</td>
                              <td>
                                <Pill tone={INTERVIEW_TONE[interview.status]}>{titleCase(interview.status)}</Pill>
                              </td>
                              <td>{formatDateTime(interview.scheduled_at)}</td>
                              <td>
                                <span className="mono">{interview.evidence_count}</span>
                                {interview.evidence_pending_review > 0 && (
                                  <div className="cell-sub">{interview.evidence_pending_review} unreviewed</div>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}

              {tab === 'evidence' && (
                <>
                  {evidence.isLoading && <LoadingBlock rows={5} />}
                  {evidence.data && evidence.data.items.length === 0 && (
                    <EmptyState title="No evidence captured" description="Evidence is captured inside an interview workspace so it keeps its source." />
                  )}
                  <div className="stack stack-2">
                    {evidence.data?.items.map((item) => (
                      <Link
                        key={item.id}
                        to={`/evidence/${item.id}`}
                        className="card-surface"
                        style={{ padding: 11, boxShadow: 'none' }}
                      >
                        <div className="row-between">
                          <span className="mono" style={{ fontSize: 11 }}>
                            {item.code} · {titleCase(item.evidence_type)}
                          </span>
                          <Pill tone={CONFIDENCE_TONE[item.confidence]}>{titleCase(item.confidence)} confidence</Pill>
                        </div>
                        <div className="mt-1" style={{ fontSize: 13 }}>
                          “{item.content}”
                        </div>
                        <div className="definition mt-1">
                          {item.participant?.label ?? 'Unattributed'} · {formatDate(item.captured_at)} ·{' '}
                          {item.provenance_status === 'recorded' ? 'provenance recorded' : 'provenance missing'}
                        </div>
                      </Link>
                    ))}
                  </div>
                </>
              )}

              {tab === 'insights' && (
                <>
                  {insights.isLoading && <LoadingBlock rows={4} />}
                  {insights.data && insights.data.items.length === 0 && (
                    <EmptyState title="No insights yet" description="Draft an insight from the evidence captured in this project." />
                  )}
                  <div className="stack stack-2">
                    {insights.data?.items.map((insight) => (
                      <Link key={insight.id} to={`/insights/${insight.id}`} className="card-surface" style={{ padding: 12, boxShadow: 'none' }}>
                        <div className="row-between">
                          <span style={{ fontWeight: 620, fontSize: 13 }}>{insight.title}</span>
                          <Pill tone={INSIGHT_TONE[insight.status]}>{titleCase(insight.status)}</Pill>
                        </div>
                        <div className="definition mt-1">
                          {insight.evidence_count} evidence item(s) · {insight.decision_count} decision(s) ·{' '}
                          {titleCase(insight.confidence)} confidence
                        </div>
                      </Link>
                    ))}
                  </div>
                </>
              )}

              {tab === 'decisions' && (
                <>
                  {decisions.isLoading && <LoadingBlock rows={4} />}
                  {decisions.data && decisions.data.items.length === 0 && (
                    <EmptyState title="No decisions linked" description="Research that cannot be found later is expensive note-taking." />
                  )}
                  <div className="stack stack-2">
                    {decisions.data?.items.map((decision) => (
                      <Link key={decision.id} to={`/decisions/${decision.id}`} className="card-surface" style={{ padding: 12, boxShadow: 'none' }}>
                        <div className="row-between">
                          <span style={{ fontWeight: 620, fontSize: 13 }}>{decision.title}</span>
                          <Pill tone={DECISION_TONE[decision.status]}>{titleCase(decision.status)}</Pill>
                        </div>
                        <div className="definition mt-1">
                          {titleCase(decision.business_function)} · {decision.insight_count} insight(s) ·{' '}
                          {decision.open_action_count} open action(s)
                        </div>
                      </Link>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="stack stack-3">
          <SectionCard title="Evidence depth" subtitle="Where this project actually is">
            <div className="stack stack-3">
              <div className="row-between" style={{ fontSize: 12.5 }}>
                <span>Participants recruited</span>
                <span className="mono">{project.counts.participants}</span>
              </div>
              <div className="row-between" style={{ fontSize: 12.5 }}>
                <span>Interviews completed</span>
                <span className="mono">
                  {project.counts.interviews_completed}/{project.counts.interviews}
                </span>
              </div>
              <div className="row-between" style={{ fontSize: 12.5 }}>
                <span>Evidence items</span>
                <span className="mono">{project.counts.evidence}</span>
              </div>
              <div className="row-between" style={{ fontSize: 12.5 }}>
                <span>Insights</span>
                <span className="mono">{project.counts.insights}</span>
              </div>
              <div className="row-between" style={{ fontSize: 12.5 }}>
                <span>Decisions</span>
                <span className="mono">{project.counts.decisions}</span>
              </div>
              <hr className="divider" />
              <HonestyNote>
                Counts describe effort. They do not tell you whether the sample represents anyone beyond the people
                who took part.
              </HonestyNote>
            </div>
          </SectionCard>

          {project.segment_gap && (
            <Notice tone="warning" title="Segment coverage gap">
              At least one target segment has no participants on the recruitment list. Any conclusion is about the
              people who were reachable, not the whole customer base.
            </Notice>
          )}

          <SectionCard title="Quick actions">
            <div className="stack stack-2">
              <Link to={`/interviews?project=${project.id}`} className="btn btn-outline-secondary btn-sm">
                Schedule an interview
              </Link>
              <Link to={`/evidence?project=${project.id}`} className="btn btn-outline-secondary btn-sm">
                Review captured evidence
              </Link>
              <Link to="/recruitment" className="btn btn-outline-secondary btn-sm">
                Manage recruitment
              </Link>
              <Link to={`/decisions?project=${project.id}`} className="btn btn-outline-secondary btn-sm">
                See linked decisions
              </Link>
            </div>
          </SectionCard>
        </div>
      </div>

      <Modal show={editing} onHide={() => setEditing(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Edit research project</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="stack stack-3">
            <div>
              <label className="form-label" htmlFor="projectdetailpage-field-1">Name</label>
              <input id="projectdetailpage-field-1"
                className="form-control"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="projectdetailpage-field-2">Objective</label>
              <textarea id="projectdetailpage-field-2"
                className="form-control"
                rows={3}
                value={form.objective}
                onChange={(event) => setForm({ ...form, objective: event.target.value })}
              />
            </div>
            <div className="section-grid grid-2" style={{ gap: 10 }}>
              <div>
                <label className="form-label" htmlFor="projectdetailpage-field-3">Status</label>
                <select id="projectdetailpage-field-3"
                  className="form-select"
                  value={form.status}
                  onChange={(event) => setForm({ ...form, status: event.target.value })}
                >
                  {['draft', 'planning', 'recruiting', 'in_progress', 'analysis', 'completed', 'archived'].map((status) => (
                    <option key={status} value={status}>
                      {titleCase(status)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="form-label" htmlFor="projectdetailpage-field-4">Priority</label>
                <select id="projectdetailpage-field-4"
                  className="form-select"
                  value={form.priority}
                  onChange={(event) => setForm({ ...form, priority: event.target.value })}
                >
                  {['low', 'medium', 'high', 'critical'].map((priority) => (
                    <option key={priority} value={priority}>
                      {titleCase(priority)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="form-label" htmlFor="projectdetailpage-field-5">Deadline</label>
                <input id="projectdetailpage-field-5"
                  type="date"
                  className="form-control"
                  value={form.deadline}
                  onChange={(event) => setForm({ ...form, deadline: event.target.value })}
                />
              </div>
              <div>
                <label className="form-label" htmlFor="projectdetailpage-field-6">Owner</label>
                <select id="projectdetailpage-field-6"
                  className="form-select"
                  value={form.owner_id}
                  onChange={(event) => setForm({ ...form, owner_id: event.target.value })}
                >
                  <option value="">Unassigned</option>
                  {users.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={() => setEditing(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={() => updateProject.mutate()} disabled={updateProject.isPending}>
            {updateProject.isPending ? 'Saving…' : 'Save changes'}
          </Button>
        </Modal.Footer>
      </Modal>

      <ConfirmDialog
        show={archiveOpen}
        title="Archive this project?"
        destructive
        confirmLabel="Archive project"
        busy={archiveProject.isPending}
        onCancel={() => setArchiveOpen(false)}
        onConfirm={() => archiveProject.mutate()}
      >
        <p style={{ marginBottom: 8 }}>
          The project will leave the active list. Its interviews, evidence and insights stay searchable, because the
          point of the library is that old learning can be found again.
        </p>
        <div className="definition">You can restore it later by editing the status.</div>
      </ConfirmDialog>

      <div className="mt-3">
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => navigate('/overview')}>
          Back to overview
        </button>
      </div>
    </div>
  )
}
