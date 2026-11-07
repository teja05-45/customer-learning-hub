import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from 'react-bootstrap'
import { ArrowLeft, ShieldCheck } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useToast } from '../app/ToastProvider'
import type { ParticipantDetail, ProjectListResponse } from '../types'
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
  MetaItem,
  Notice,
  PageHeader,
  Pill,
  SectionCard,
} from '../components/ui'
import {
  ELIGIBILITY_LABELS,
  SEGMENT_LABELS,
  STAGE_TONE,
  formatDate,
  formatDateTime,
  relativeTime,
  titleCase,
} from '../utils/format'

export function ParticipantDetailPage() {
  const { participantId = '' } = useParams()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [assignOpen, setAssignOpen] = useState(false)
  const [projectId, setProjectId] = useState('')
  const [nextAction, setNextAction] = useState('Confirm eligibility, then invite through the controlled Ops process')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['participant', participantId],
    queryFn: () => api.get<ParticipantDetail>(`/participants/${participantId}`),
    enabled: Boolean(participantId),
  })

  const projects = useQuery({
    queryKey: ['projects', 'for-assign'],
    queryFn: () => api.get<ProjectListResponse>(`/projects${toQuery({ page_size: 50 })}`),
    enabled: assignOpen,
  })

  const assign = useMutation({
    mutationFn: () =>
      api.post(`/participants/${participantId}/assign`, { project_id: projectId, next_action: nextAction }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['participant', participantId] })
      void queryClient.invalidateQueries({ queryKey: ['recruitment'] })
      setAssignOpen(false)
      toast.push({ title: 'Added to the recruitment pipeline', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not assign', message: (error as Error).message, variant: 'error' }),
  })

  const updateEligibility = useMutation({
    mutationFn: (eligibility: string) =>
      api.patch(`/participants/${participantId}`, {
        eligibility,
        eligibility_note:
          eligibility === 'ineligible'
            ? 'Marked ineligible after a review of contact history.'
            : 'Eligibility reviewed and confirmed.',
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['participant', participantId] })
      toast.push({ title: 'Eligibility updated', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Update failed', message: (error as Error).message, variant: 'error' }),
  })

  if (isLoading) {
    return (
      <div className="page">
        <SectionCard>
          <LoadingBlock rows={6} />
        </SectionCard>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="page">
        <PageHeader title="Participant not found" />
        <ErrorState
          message={(error as Error)?.message ?? 'That participant does not exist.'}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  return (
    <div className="page">
      <Link to="/participants" className="link-quiet inline mb-3">
        <ArrowLeft size={13} /> Back to participants
      </Link>

      <PageHeader
        title={data.display_name}
        description={`${data.code} · ${SEGMENT_LABELS[data.segment]} · synthetic participant record`}
        meta={
          <div className="d-flex flex-wrap gap-2 align-items-center">
            <Pill tone={data.eligibility === 'eligible' ? 'green' : data.eligibility === 'limited' ? 'amber' : 'red'}>
              {ELIGIBILITY_LABELS[data.eligibility]}
            </Pill>
            <Pill tone="outline">{data.product_category || 'Category unknown'}</Pill>
            <Pill tone="outline">{data.orders_count} order(s)</Pill>
          </div>
        }
        actions={
          <>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setAssignOpen(true)}
              disabled={data.eligibility === 'ineligible'}
            >
              Add to a project
            </button>
            {data.eligibility !== 'ineligible' ? (
              <button type="button" className="btn btn-outline-secondary" onClick={() => updateEligibility.mutate('ineligible')}>
                Mark ineligible
              </button>
            ) : (
              <button type="button" className="btn btn-outline-secondary" onClick={() => updateEligibility.mutate('eligible')}>
                Restore eligibility
              </button>
            )}
          </>
        }
      />

      <div className="section-grid grid-sidebar">
        <div className="stack stack-3">
          <SectionCard title="Participation history" subtitle="Every conversation this person has taken part in">
            {data.participation_history.length === 0 ? (
              <EmptyState
                title="No interviews yet"
                description="Participation history appears here once a conversation is scheduled."
              />
            ) : (
              <div className="table-wrap">
                <table className="clh-table">
                  <thead>
                    <tr>
                      <th>Interview</th>
                      <th>Project</th>
                      <th>Status</th>
                      <th>Scheduled</th>
                      <th>Evidence</th>
                      <th>Insights</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.participation_history.map((item) => (
                      <tr key={item.interview_id ?? `${item.project_id}-${item.scheduled_at}`}>
                        <td>
                          {item.interview_id ? (
                            <Link to={`/interviews/${item.interview_id}`} className="table-link">
                              {item.interview_code}
                            </Link>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td>
                          <Link to={`/projects/${item.project_id}`} className="table-link">
                            {item.project_name}
                          </Link>
                        </td>
                        <td>
                          <Pill tone="blue">{titleCase(item.status)}</Pill>
                        </td>
                        <td>{formatDateTime(item.scheduled_at)}</td>
                        <td className="mono">{item.evidence_count}</td>
                        <td className="mono">{item.insight_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>

          <SectionCard
            title="Feedback history"
            subtitle="Every source this person contributed to, across projects and channels"
            actions={<Pill tone="outline">{data.feedback_history.length} source(s)</Pill>}
          >
            {data.feedback_history.length === 0 ? (
              <EmptyState
                title="No feedback on file"
                description="Written feedback, survey answers, support notes and imported sources appear here when they are attributed to this participant."
              />
            ) : (
              <div className="stack stack-2">
                {data.feedback_history.map((item) => (
                  <article key={item.id} className="feedback-card">
                    <div className="row-between" style={{ flexWrap: 'wrap', gap: 6 }}>
                      <div className="d-flex gap-2 align-items-center flex-wrap">
                        <span className="mono" style={{ fontSize: 11 }}>{item.code}</span>
                        <Pill tone="outline">{titleCase(item.source_type)}</Pill>
                        <Pill tone={item.verification_status === 'verified' ? 'green' : 'amber'}>
                          {titleCase(item.verification_status)}
                        </Pill>
                        <Pill tone="blue">{titleCase(item.research_depth)} depth</Pill>
                      </div>
                      <span className="definition">{formatDate(item.collected_at)}</span>
                    </div>
                    <blockquote className="feedback-quote">{item.content}</blockquote>
                    {item.interpretation && (
                      <div className="interpretation-block">
                        <span className="label">Researcher interpretation</span>
                        {item.interpretation}
                      </div>
                    )}
                    <div className="feedback-source-line">
                      <Link to={`/projects/${item.project_id}`}>{item.project_name}</Link>
                      {item.interview_id && item.interview_code && (
                        <Link to={`/interviews/${item.interview_id}`}>{item.interview_code}</Link>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard title="Recruitment records" subtitle="Where this person sits in each project pipeline">
            {data.recruitment.length === 0 ? (
              <EmptyState title="Not on any recruitment list" description="Add this participant to a project to start tracking outreach." />
            ) : (
              <div className="stack stack-2">
                {data.recruitment.map((record) => (
                  <div key={record.id} className="card-surface" style={{ padding: 12, boxShadow: 'none' }}>
                    <div className="row-between">
                      <Link to={`/projects/${record.project_id}`} className="table-link">
                        {record.project?.label ?? 'Project'}
                      </Link>
                      <Pill tone={STAGE_TONE[record.stage]}>{titleCase(record.stage)}</Pill>
                    </div>
                    <div className="definition mt-1">
                      Next: {record.next_action || 'not set'} · updated {relativeTime(record.updated_at)}
                    </div>
                    {record.invited_at && (
                      <div className="definition">
                        Invited {formatDate(record.invited_at)}
                        {record.responded_at ? ` · replied ${formatDate(record.responded_at)}` : ' · no reply recorded'}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>

        <div className="stack stack-3">
          <SectionCard title="Profile">
            <div className="stack stack-3">
              <MetaItem label="Participant ID" value={<span className="mono">{data.code}</span>} />
              <MetaItem label="Segment" value={SEGMENT_LABELS[data.segment]} />
              <MetaItem label="Purchase frequency" value={data.purchase_frequency || 'Not recorded'} />
              <MetaItem label="Last purchase" value={formatDate(data.last_purchase_at)} />
              <MetaItem label="Eligibility note" value={data.eligibility_note || 'No note recorded'} />
              <MetaItem label="Consent on file" value={titleCase(data.contact_consent)} />
              <MetaItem label="Evidence captured" value={String(data.evidence_count)} />
            </div>
          </SectionCard>

          <SectionCard title="Contact handling" icon={<ShieldCheck size={14} />}>
            <div className="stack stack-2">
              <div className="definition">
                Contact route: {data.contact_route ?? 'Not recorded'}
              </div>
              <Notice tone="neutral">
                This record holds no email address or phone number. Any outreach is performed by Operations through a
                controlled process and recorded here as a status, not a message.
              </Notice>
            </div>
          </SectionCard>
        </div>
      </div>

      <Modal show={assignOpen} onHide={() => setAssignOpen(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Add {data.display_name} to a project</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="stack stack-3">
            <div>
              <label className="form-label" htmlFor="participantdetailpage-field-1">Research project</label>
              <select id="participantdetailpage-field-1" className="form-select" value={projectId} onChange={(event) => setProjectId(event.target.value)}>
                <option value="">Select a project…</option>
                {projects.data?.items
                  .filter((project) => project.status !== 'archived')
                  .map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
              </select>
            </div>
            <div>
              <label className="form-label" htmlFor="participantdetailpage-field-2">Next action</label>
              <input id="participantdetailpage-field-2" className="form-control" value={nextAction} onChange={(event) => setNextAction(event.target.value)} />
            </div>
            <Notice tone="neutral">
              Adding someone to the pipeline does not contact them. The invitation step is recorded manually and marked
              as simulated.
            </Notice>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setAssignOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!projectId || assign.isPending}
            onClick={() => assign.mutate()}
          >
            {assign.isPending ? 'Adding…' : 'Add to pipeline'}
          </button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
