import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from 'react-bootstrap'
import { AlertTriangle, History, Plus, UserPlus } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useToast } from '../app/ToastProvider'
import type {
  Participant,
  ParticipantListResponse,
  ProjectListResponse,
  RecruitmentListResponse,
  RecruitmentRecord,
  RecruitmentStage,
} from '../types'
import {
  EmptyState,
  ErrorState,
  MetaItem,
  Notice,
  PageHeader,
  Pill,
  SectionCard,
  TableSkeleton,
} from '../components/ui'
import {
  PIPELINE_STAGES,
  RECRUITMENT_TRANSITIONS,
  SEGMENT_LABELS,
  STAGE_LABELS,
  STAGE_TONE,
  formatDate,
  formatDateTime,
  relativeTime,
  titleCase,
} from '../utils/format'

export function RecruitmentPage() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [projectId, setProjectId] = useState('')
  const [stageFilter, setStageFilter] = useState<RecruitmentStage | ''>('')
  const [addOpen, setAddOpen] = useState(false)
  const [selectedParticipants, setSelectedParticipants] = useState<string[]>([])
  const [timelineRecord, setTimelineRecord] = useState<RecruitmentRecord | null>(null)

  const projects = useQuery({
    queryKey: ['projects', 'recruitment-select'],
    queryFn: () => api.get<ProjectListResponse>(`/projects${toQuery({ page_size: 50 })}`),
  })

  const activeProjects = useMemo(
    () => (projects.data?.items ?? []).filter((project) => project.status !== 'archived'),
    [projects.data],
  )

  const params = useMemo(
    () => ({ project_id: projectId || undefined, stage: stageFilter || undefined }),
    [projectId, stageFilter],
  )

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['recruitment', params],
    queryFn: () => api.get<RecruitmentListResponse>(`/recruitment${toQuery(params)}`),
  })

  const participants = useQuery({
    queryKey: ['participants', 'recruit-picker'],
    queryFn: () => api.get<ParticipantListResponse>(`/participants${toQuery({ page_size: 100, eligibility: 'eligible' })}`),
    enabled: addOpen,
  })

  const selectedProject = activeProjects.find((project) => project.id === projectId)

  const changeStage = useMutation({
    mutationFn: ({ id, stage }: { id: string; stage: RecruitmentStage }) =>
      api.patch(`/recruitment/${id}`, {
        stage,
        note: `Stage updated to ${STAGE_LABELS[stage].toLowerCase()} from the recruitment board (simulated).`,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['recruitment'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.push({ title: 'Recruitment stage updated', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Stage change rejected', message: (error as Error).message, variant: 'error' }),
  })

  const addParticipants = useMutation({
    mutationFn: () =>
      api.post('/recruitment', {
        project_id: projectId,
        participant_ids: selectedParticipants,
        next_action: 'Confirm eligibility, then invite through the controlled Ops process',
      }),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ['recruitment'] })
      setAddOpen(false)
      setSelectedParticipants([])
      const skipped = (result as { skipped?: unknown[] })?.skipped?.length ?? 0
      toast.push({
        title: 'Participants added to the pipeline',
        message: skipped ? `${skipped} participant(s) were skipped and left unchanged.` : undefined,
        variant: 'success',
      })
    },
    onError: (error) => toast.push({ title: 'Could not add participants', message: (error as Error).message, variant: 'error' }),
  })

  const coverage = data?.segment_coverage ?? {}
  const coverageTotal = Object.values(coverage).reduce((total, value) => total + value, 0)

  return (
    <div className="page">
      <PageHeader
        title="Recruitment pipeline"
        description="Who was considered, who was contacted, who replied — and which perspectives are missing. A short list of willing repeat buyers is not a sample."
        actions={
          <>
            <select
              className="form-select"
              style={{ width: 280 }}
              value={projectId}
              onChange={(event) => setProjectId(event.target.value)}
              aria-label="Filter by project"
            >
              <option value="">All projects</option>
              {activeProjects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setAddOpen(true)}
              disabled={!projectId}
              title={projectId ? 'Add participants to this project' : 'Choose a project first'}
            >
              <Plus size={14} /> Add participants
            </button>
          </>
        }
      />

      {data?.warnings.map((warning) => (
        <div key={warning} className="mb-2">
          <Notice tone="warning" icon={<AlertTriangle size={15} />}>
            {warning}
          </Notice>
        </div>
      ))}

      <div className="section-grid grid-4 mb-3">
        {PIPELINE_STAGES.map((stage) => (
          <button
            key={stage}
            type="button"
            className="stat-card"
            style={{
              textAlign: 'left',
              borderColor: stageFilter === stage ? 'var(--clh-primary)' : undefined,
              background: stageFilter === stage ? 'var(--clh-primary-soft)' : undefined,
              cursor: 'pointer',
            }}
            onClick={() => setStageFilter(stageFilter === stage ? '' : stage)}
          >
            <div className="stat-label">{STAGE_LABELS[stage]}</div>
            <div className="stat-value" style={{ fontSize: 20 }}>
              {data?.stage_counts[stage] ?? 0}
            </div>
            <div className="stat-meta">{stageFilter === stage ? 'filtering by this stage' : 'click to filter'}</div>
          </button>
        ))}
      </div>

      <div className="section-grid grid-sidebar">
        <SectionCard
          title="Pipeline"
          subtitle={
            selectedProject
              ? `${selectedProject.name} · ${selectedProject.target_segments.map((segment) => SEGMENT_LABELS[segment]).join(', ')}`
              : 'Across every project'
          }
          padded={false}
        >
          {isLoading && <TableSkeleton rows={5} columns={5} />}
          {error && (
            <div style={{ padding: 16 }}>
              <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
            </div>
          )}
          {data && data.items.length === 0 && (
            <EmptyState
              icon={<UserPlus size={18} />}
              title="No recruitment records"
              description="Choose a project and add participants. Every person on the list keeps a visible stage and a next action."
            />
          )}
          {data && data.items.length > 0 && (
            <div className="table-wrap">
              <table className="clh-table">
                <thead>
                  <tr>
                    <th>Participant</th>
                    <th>Project</th>
                    <th>Stage</th>
                    <th>Last updated</th>
                    <th>Next action</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((record) => {
                    const options: RecruitmentStage[] = [record.stage, ...RECRUITMENT_TRANSITIONS[record.stage]]
                    return (
                      <tr key={record.id}>
                        <td>
                          <Link to={`/participants/${record.participant_id}`} className="table-link">
                            {record.participant?.display_name}
                          </Link>
                          <div className="cell-sub">
                            {record.participant ? SEGMENT_LABELS[record.participant.segment] : '—'} ·{' '}
                            {record.participant?.code}
                          </div>
                        </td>
                        <td style={{ maxWidth: 200 }}>
                          <Link to={`/projects/${record.project_id}`} className="link-quiet">
                            {record.project?.label}
                          </Link>
                        </td>
                        <td>
                          <select
                            className="form-select"
                            style={{ width: 148, fontSize: 12, padding: '3px 8px' }}
                            value={record.stage}
                            onChange={(event) =>
                              changeStage.mutate({ id: record.id, stage: event.target.value as RecruitmentStage })
                            }
                            aria-label={`Change stage for ${record.participant?.display_name}`}
                          >
                            {options.map((option) => (
                              <option key={option} value={option}>
                                {STAGE_LABELS[option]}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="text-secondary-clh">
                          {relativeTime(record.updated_at)}
                          <div className="cell-sub">{record.days_in_stage ?? 0} day(s) in stage</div>
                        </td>
                        <td style={{ maxWidth: 240 }} className="text-secondary-clh">
                          {record.next_action || '—'}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => setTimelineRecord(record)}
                            aria-label="View timeline"
                          >
                            <History size={14} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <div className="stack stack-3">
          <SectionCard title="Segment representation" subtitle="Who is actually in this pipeline">
            {coverageTotal === 0 ? (
              <div className="definition">Choose a project with participants to see segment coverage.</div>
            ) : (
              <div className="stack stack-2">
                {Object.entries(coverage).map(([segment, count]) => (
                  <div key={segment} className="row-between" style={{ fontSize: 12.5 }}>
                    <span>{SEGMENT_LABELS[segment as keyof typeof SEGMENT_LABELS] ?? titleCase(segment)}</span>
                    <span className="inline">
                      <span className="mono">{count}</span>
                      <span
                        style={{
                          display: 'inline-block',
                          width: `${Math.min(100, (count / coverageTotal) * 90) + 10}px`,
                          height: 6,
                          borderRadius: 99,
                          background: 'var(--clh-primary)',
                          opacity: 0.75,
                        }}
                      />
                    </span>
                  </div>
                ))}
                {selectedProject?.target_segments
                  .filter((segment) => !coverage[segment])
                  .map((segment) => (
                    <div key={segment} className="notice notice-danger" style={{ padding: '6px 8px' }}>
                      <span className="notice-icon">!</span>
                      <span style={{ fontSize: 11.5 }}>
                        No {SEGMENT_LABELS[segment].toLowerCase()} in the pipeline yet.
                      </span>
                    </div>
                  ))}
              </div>
            )}
            <p className="definition mt-2" style={{ marginBottom: 0 }}>
              The pipeline records who was <em>considered</em>, not only who agreed. That is what makes a gap visible
              before it becomes a finding.
            </p>
          </SectionCard>

          <SectionCard title="How the team avoids only hearing from fans">
            <ol className="definition" style={{ paddingLeft: 16, margin: 0, lineHeight: 1.6 }}>
              <li>Start from the segment the decision affects, not the people who usually reply.</li>
              <li>Record every person identified, including the ones who decline or never answer.</li>
              <li>Keep the next action named, so silence is followed up once rather than forgotten.</li>
              <li>Read the coverage warning before writing an insight from the sample.</li>
            </ol>
          </SectionCard>

          {data && (
            <SectionCard title="Pipeline totals">
              <div className="stack stack-3">
                <MetaItem label="Records in view" value={String(data.total)} />
                <MetaItem
                  label="Invited"
                  value={String(data.items.filter((item) => item.invited_at).length)}
                />
                <MetaItem
                  label="Replied"
                  value={String(data.items.filter((item) => item.responded_at).length)}
                />
                <MetaItem
                  label="Declined or withdrawn"
                  value={String(data.items.filter((item) => ['declined', 'withdrawn', 'no_response'].includes(item.stage)).length)}
                />
              </div>
            </SectionCard>
          )}
        </div>
      </div>

      <Modal show={addOpen} onHide={() => setAddOpen(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Add participants to the pipeline</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="definition mb-3">
            {selectedProject ? `Project: ${selectedProject.name}` : 'Choose a project on the page first.'}
          </div>
          {participants.isLoading && <div className="skeleton" style={{ height: 80 }} />}
          {participants.data && (
            <div className="stack stack-2" style={{ maxHeight: 340, overflowY: 'auto' }}>
              {participants.data.items.map((participant: Participant) => {
                const alreadyOnList = data?.items.some(
                  (record) => record.participant_id === participant.id && record.project_id === projectId,
                )
                return (
                  <label
                    key={participant.id}
                    className="card-surface"
                    style={{ padding: 10, boxShadow: 'none', display: 'flex', gap: 10, alignItems: 'center' }}
                  >
                    <input
                      type="checkbox"
                      disabled={alreadyOnList}
                      checked={selectedParticipants.includes(participant.id)}
                      onChange={(event) => {
                        setSelectedParticipants((current) =>
                          event.target.checked
                            ? [...current, participant.id]
                            : current.filter((id) => id !== participant.id),
                        )
                      }}
                    />
                    <span style={{ flex: 1 }}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{participant.display_name}</span>
                      <span className="cell-sub d-block">
                        {SEGMENT_LABELS[participant.segment]} · {participant.purchase_frequency || 'frequency unknown'} ·{' '}
                        {participant.code}
                      </span>
                    </span>
                    {alreadyOnList ? <Pill tone="outline">Already on list</Pill> : <Pill tone="green">Eligible</Pill>}
                  </label>
                )
              })}
            </div>
          )}
          <div className="definition mt-3">
            Ineligible participants are excluded by the API. Declines and non-responses are recorded as stages, never
            deleted.
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setAddOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={selectedParticipants.length === 0 || addParticipants.isPending}
            onClick={() => addParticipants.mutate()}
          >
            {addParticipants.isPending ? 'Adding…' : `Add ${selectedParticipants.length || ''} participant(s)`}
          </button>
        </Modal.Footer>
      </Modal>

      <Modal show={Boolean(timelineRecord)} onHide={() => setTimelineRecord(null)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Recruitment timeline</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {timelineRecord && (
            <>
              <div className="definition mb-3">
                {timelineRecord.participant?.display_name} · {timelineRecord.project?.label}
              </div>
              <div className="timeline">
                {timelineRecord.events.map((event) => (
                  <div className="timeline-item" key={event.id}>
                    <span className="timeline-dot current" />
                    <div>
                      <div style={{ fontSize: 12.5 }}>
                        {event.from_stage ? `${titleCase(event.from_stage)} → ` : ''}
                        <strong>{titleCase(event.to_stage)}</strong>
                      </div>
                      <div className="definition">{event.note}</div>
                      <div className="definition mt-1">
                        {formatDateTime(event.created_at)} · {event.actor?.label ?? 'System'}
                      </div>
                    </div>
                  </div>
                ))}
                {timelineRecord.events.length === 0 && <div className="definition">No history recorded yet.</div>}
              </div>
              <hr className="divider" />
              <div className="section-grid grid-2">
                <MetaItem label="Invited" value={formatDate(timelineRecord.invited_at)} />
                <MetaItem label="Replied" value={formatDate(timelineRecord.responded_at)} />
                <MetaItem label="Current stage" value={<Pill tone={STAGE_TONE[timelineRecord.stage]}>{STAGE_LABELS[timelineRecord.stage]}</Pill>} />
                <MetaItem label="Updated" value={relativeTime(timelineRecord.updated_at)} />
              </div>
            </>
          )}
        </Modal.Body>
      </Modal>
    </div>
  )
}
