import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from 'react-bootstrap'
import { CalendarDays, CalendarPlus, Search } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useToast } from '../app/ToastProvider'
import { useSession } from '../app/SessionProvider'
import type {
  InterviewDetail,
  InterviewListResponse,
  InterviewStatus,
  ParticipantListResponse,
  ProjectListResponse,
  RecruitmentListResponse,
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
  INTERVIEW_TONE,
  SEGMENT_LABELS,
  formatDateTime,
  relativeTime,
  titleCase,
} from '../utils/format'

const STATUS_FILTERS: { value: InterviewStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'planned', label: 'Planned' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
]

export function InterviewsPage() {
  const [searchParams] = useSearchParams()
  const toast = useToast()
  const queryClient = useQueryClient()
  const { users } = useSession()
  const [statusFilter, setStatusFilter] = useState<InterviewStatus | 'all'>('all')
  const [upcomingOnly, setUpcomingOnly] = useState(false)
  const [search, setSearch] = useState('')
  const [scheduleOpen, setScheduleOpen] = useState(Boolean(searchParams.get('project')))

  const [form, setForm] = useState({
    project_id: searchParams.get('project') ?? '',
    participant_id: '',
    title: 'Research conversation',
    scheduled_at: '',
    duration_minutes: 30,
    interviewer_id: '',
  })
  const [formError, setFormError] = useState<string | null>(null)

  const params = useMemo(
    () => ({
      status: statusFilter === 'all' ? undefined : statusFilter,
      upcoming_only: upcomingOnly || undefined,
      q: search || undefined,
      project_id: searchParams.get('project') ?? undefined,
    }),
    [statusFilter, upcomingOnly, search, searchParams],
  )

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['interviews', params],
    queryFn: () => api.get<InterviewListResponse>(`/interviews${toQuery(params)}`),
  })

  const projects = useQuery({
    queryKey: ['projects', 'interview-picker'],
    queryFn: () => api.get<ProjectListResponse>(`/projects${toQuery({ page_size: 50 })}`),
    enabled: scheduleOpen,
  })

  const recruitment = useQuery({
    queryKey: ['recruitment', 'interview-picker', form.project_id],
    queryFn: () => api.get<RecruitmentListResponse>(`/recruitment${toQuery({ project_id: form.project_id })}`),
    enabled: scheduleOpen && Boolean(form.project_id),
  })

  const participants = useQuery({
    queryKey: ['participants', 'interview-picker'],
    queryFn: () => api.get<ParticipantListResponse>(`/participants${toQuery({ page_size: 100 })}`),
    enabled: scheduleOpen && !form.project_id,
  })

  const schedule = useMutation({
    mutationFn: () =>
      api.post<InterviewDetail>('/interviews', {
        project_id: form.project_id,
        participant_id: form.participant_id,
        title: form.title,
        scheduled_at: form.scheduled_at ? new Date(form.scheduled_at).toISOString() : null,
        duration_minutes: form.duration_minutes,
        interviewer_id: form.interviewer_id || null,
        status: form.scheduled_at ? 'scheduled' : 'planned',
        use_default_guide: true,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['interviews'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      void queryClient.invalidateQueries({ queryKey: ['recruitment'] })
      setScheduleOpen(false)
      toast.push({ title: 'Interview scheduled', message: 'A neutral guide was attached.', variant: 'success' })
    },
    onError: (error) => setFormError((error as Error).message),
  })

  const eligibleParticipants = useMemo(() => {
    if (form.project_id && recruitment.data) {
      return recruitment.data.items
        .filter((record) => !['completed', 'declined', 'withdrawn'].includes(record.stage))
        .map((record) => ({
          id: record.participant_id,
          name: record.participant?.display_name ?? 'Participant',
          detail: `${SEGMENT_LABELS[record.participant?.segment ?? 'unknown']} · ${titleCase(record.stage)}`,
        }))
    }
    return (participants.data?.items ?? []).map((participant) => ({
      id: participant.id,
      name: participant.display_name,
      detail: `${SEGMENT_LABELS[participant.segment]} · ${participant.code}`,
    }))
  }, [form.project_id, recruitment.data, participants.data])

  return (
    <div className="page">
      <PageHeader
        title="Interviews"
        description="Conversations with an owner, a consent state and a guide. Recording is off by default and no audio is captured in this prototype."
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setScheduleOpen(true)}>
            <CalendarPlus size={14} /> Schedule interview
          </button>
        }
      />

      <SectionCard padded={false}>
        <div className="filter-bar">
          <div className="filter-input">
            <Search size={14} className="search-icon" />
            <input
              className="form-control"
              placeholder="Search interview title or code"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search interviews"
            />
          </div>
          <div className="inline" style={{ flexWrap: 'wrap', gap: 6 }}>
            {STATUS_FILTERS.map((filter) => (
              <button
                key={filter.value}
                type="button"
                className={`filter-chip${statusFilter === filter.value ? ' active' : ''}`}
                onClick={() => setStatusFilter(filter.value)}
              >
                {filter.label}
              </button>
            ))}
            <button
              type="button"
              className={`filter-chip${upcomingOnly ? ' active' : ''}`}
              onClick={() => setUpcomingOnly((value) => !value)}
            >
              Upcoming only
            </button>
          </div>
          <div style={{ marginLeft: 'auto' }} className="definition">
            {isFetching ? 'Refreshing…' : `${data?.total ?? 0} interview(s)`}
          </div>
        </div>

        {isLoading && <TableSkeleton rows={5} columns={5} />}
        {error && (
          <div style={{ padding: 16 }}>
            <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
          </div>
        )}
        {data && data.items.length === 0 && (
          <EmptyState
            icon={<CalendarDays size={18} />}
            title="No interviews match this view"
            description="Schedule a conversation with someone who has agreed to take part. Evidence can only be captured inside an interview, so its source is never lost."
            action={
              <button type="button" className="btn btn-primary btn-sm" onClick={() => setScheduleOpen(true)}>
                Schedule the first interview
              </button>
            }
          />
        )}

        {data && data.items.length > 0 && (
          <div className="table-wrap">
            <table className="clh-table">
              <thead>
                <tr>
                  <th>Interview</th>
                  <th>Participant</th>
                  <th>Project</th>
                  <th>Status</th>
                  <th>When</th>
                  <th>Consent</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((interview) => (
                  <tr key={interview.id}>
                    <td style={{ maxWidth: 260 }}>
                      <Link to={`/interviews/${interview.id}`} className="table-link">
                        {interview.title}
                      </Link>
                      <div className="cell-sub">
                        {interview.code} · {interview.interviewer?.label ?? 'Unassigned'}
                      </div>
                    </td>
                    <td className="text-secondary-clh">
                      {interview.participant?.display_name}
                      <div className="cell-sub">
                        {interview.participant ? SEGMENT_LABELS[interview.participant.segment] : '—'}
                      </div>
                    </td>
                    <td style={{ maxWidth: 200 }}>
                      <Link to={`/projects/${interview.project_id}`} className="link-quiet">
                        {interview.project?.label}
                      </Link>
                    </td>
                    <td>
                      <Pill tone={INTERVIEW_TONE[interview.status]}>{titleCase(interview.status)}</Pill>
                    </td>
                    <td className="text-secondary-clh">
                      {formatDateTime(interview.scheduled_at)}
                      <div className="cell-sub">{relativeTime(interview.scheduled_at)}</div>
                    </td>
                    <td>
                      <Pill tone={interview.consent_status === 'granted' ? 'green' : interview.consent_status === 'declined' ? 'red' : 'amber'}>
                        {titleCase(interview.consent_status)}
                      </Pill>
                    </td>
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
      </SectionCard>

      <div className="mt-3">
        <Notice tone="warning" title="Recording is disabled by default">
          The recording flag exists to demonstrate a consent gate: it cannot be switched on server-side without a
          recorded, granted recording consent. No audio is captured anywhere in this prototype.
        </Notice>
      </div>

      <Modal show={scheduleOpen} onHide={() => setScheduleOpen(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Schedule an interview</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="section-grid grid-2" style={{ gap: 12 }}>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="interviewspage-field-1">
                Research project<span className="required-mark">*</span>
              </label>
              <select id="interviewspage-field-1"
                className="form-select"
                value={form.project_id}
                onChange={(event) => setForm({ ...form, project_id: event.target.value, participant_id: '' })}
              >
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
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="interviewspage-field-2">
                Participant<span className="required-mark">*</span>
              </label>
              <select id="interviewspage-field-2"
                className="form-select"
                value={form.participant_id}
                onChange={(event) => setForm({ ...form, participant_id: event.target.value })}
              >
                <option value="">Select a participant…</option>
                {eligibleParticipants.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name} — {option.detail}
                  </option>
                ))}
              </select>
              {form.project_id && eligibleParticipants.length === 0 && (
                <div className="form-text">Nobody on this project's recruitment list is available yet.</div>
              )}
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="interviewspage-field-3">Title</label>
              <input id="interviewspage-field-3"
                className="form-control"
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="interviewspage-field-4">Date and time</label>
              <input id="interviewspage-field-4"
                type="datetime-local"
                className="form-control"
                value={form.scheduled_at}
                onChange={(event) => setForm({ ...form, scheduled_at: event.target.value })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="interviewspage-field-5">Duration (minutes)</label>
              <input id="interviewspage-field-5"
                type="number"
                className="form-control"
                min={10}
                max={180}
                value={form.duration_minutes}
                onChange={(event) => setForm({ ...form, duration_minutes: Number(event.target.value) })}
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="interviewspage-field-6">Interviewer</label>
              <select id="interviewspage-field-6"
                className="form-select"
                value={form.interviewer_id}
                onChange={(event) => setForm({ ...form, interviewer_id: event.target.value })}
              >
                <option value="">Assign to me</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.name} · {user.job_title}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="mt-3">
            <Notice tone="info">
              A neutral starter guide is attached automatically. Leave the date empty to save the interview as planned.
            </Notice>
          </div>
          {formError && (
            <div className="mt-3">
              <Notice tone="danger">{formError}</Notice>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setScheduleOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!form.project_id || !form.participant_id || schedule.isPending}
            onClick={() => {
              setFormError(null)
              schedule.mutate()
            }}
          >
            {schedule.isPending ? 'Scheduling…' : 'Schedule interview'}
          </button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
