import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  AlertTriangle,
  ArrowUpRight,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  FolderKanban,
  Lightbulb,
  MessagesSquare,
  Plus,
  Quote,
  Users,
} from 'lucide-react'
import { api } from '../services/api'
import type { Dashboard } from '../types'
import {
  EmptyState,
  ErrorState,
  HonestyNote,
  LoadingBlock,
  PageHeader,
  Pill,
  ProgressBar,
  SectionCard,
  StatCard,
} from '../components/ui'
import {
  ACTION_TONE,
  DECISION_TONE,
  SEGMENT_LABELS,
  formatDate,
  formatDateTime,
  relativeTime,
  titleCase,
} from '../utils/format'

const CHART_COLOURS = ['#176b52', '#2f6b7a', '#b08028', '#b44a32', '#6b4e7a']

export function DashboardPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get<Dashboard>('/dashboard'),
  })

  if (isLoading) {
    return (
      <div className="page">
        <PageHeader title="Overview" description="Loading the research workspace…" />
        <div className="section-grid grid-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <div className="stat-card" key={index}>
              <div className="skeleton" style={{ width: '55%' }} />
              <div className="skeleton" style={{ width: '35%', height: 22 }} />
              <div className="skeleton" style={{ width: '70%', height: 10 }} />
            </div>
          ))}
        </div>
        <div className="mt-3">
          <SectionCard>
            <LoadingBlock rows={5} label="Calculating learning signals from the evidence record…" />
          </SectionCard>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="page">
        <PageHeader title="Overview" description="A single view of what the team is learning." />
        <ErrorState message={(error as Error)?.message ?? 'The dashboard could not be loaded.'} onRetry={() => refetch()} />
      </div>
    )
  }

  const learning = data.learning
  const coverage = learning.findings_total ? (learning.findings_with_evidence / learning.findings_total) * 100 : 0

  return (
    <div className="page">
      <PageHeader
        title="Overview"
        description="What the team is investigating, what it has learned, and whether any of it reached a decision."
        actions={
          <>
            <Link to="/projects/new" className="btn btn-primary">
              <Plus size={14} /> New research project
            </Link>
            <Link to="/analytics" className="btn btn-outline-secondary">
              Learning analytics
            </Link>
          </>
        }
        meta={
          <div className="notice notice-warning" style={{ padding: '8px 11px' }}>
            <span className="notice-icon">DEMO</span>
            <span>{data.data_note}</span>
          </div>
        }
      />

      <div className="section-grid grid-4">
        <StatCard
          label="Active research projects"
          value={data.active_projects}
          meta="Draft through analysis"
          icon={<FolderKanban size={13} />}
        />
        <StatCard
          label="Interviews completed"
          value={data.interviews_completed}
          meta={`${data.interviews_upcoming} upcoming`}
          icon={<MessagesSquare size={13} />}
          hint="A workload signal, not a measure of understanding."
        />
        <StatCard
          label="Participants contacted"
          value={data.participants_contacted}
          meta="Distinct synthetic participants"
          icon={<Users size={13} />}
        />
        <StatCard
          label="Response rate"
          value={data.response_rate.display}
          meta={`${data.response_rate.numerator} replied of ${data.response_rate.denominator} invited`}
          icon={<CheckCircle2 size={13} />}
          hint={data.response_rate.definition}
          warning={Boolean(data.response_rate.sample_warning)}
        />
        <StatCard
          label="Insights awaiting review"
          value={data.insights_awaiting_review}
          meta="Draft or under review"
          icon={<Lightbulb size={13} />}
          warning={data.insights_awaiting_review > 0}
        />
        <StatCard
          label="Decisions with evidence"
          value={`${data.decisions_with_evidence} / ${data.decisions_total}`}
          meta="Linked to an insight or evidence record"
          icon={<ClipboardList size={13} />}
        />
        <StatCard
          label="Open actions"
          value={data.open_actions}
          meta={`${data.overdue_actions} overdue`}
          icon={<CalendarClock size={13} />}
          warning={data.overdue_actions > 0}
        />
        <StatCard
          label="Evidence records"
          value={data.segments.reduce((total, segment) => total + segment.evidence, 0)}
          meta="Each one keeps its interview context"
          icon={<Quote size={13} />}
        />
      </div>

      <div className="section-grid grid-sidebar mt-3">
        <SectionCard
          title="Are we learning something useful?"
          subtitle="Deliberately not a count of conversations. These signals ask whether research is traceable and used."
          actions={<Link to="/analytics" className="link-quiet">Full metrics</Link>}
        >
          <div className="stack stack-4">
            <div>
              <div className="row-between">
                <span style={{ fontSize: 12.5, fontWeight: 600 }}>Findings traceable to source evidence</span>
                <span className="mono" style={{ fontSize: 12.5 }}>
                  {learning.findings_with_evidence}/{learning.findings_total}
                </span>
              </div>
              <div className="mt-2">
                <ProgressBar value={coverage} tone={coverage >= 80 ? 'green' : coverage > 0 ? 'amber' : 'amber'} />
              </div>
              <div className="definition mt-1">{learning.findings_coverage_display}</div>
            </div>

            <div className="section-grid grid-2">
              <div className="card-surface" style={{ padding: 12, boxShadow: 'none' }}>
                <div className="meta-label">Decisions supported by research</div>
                <div style={{ fontSize: 19, fontWeight: 660, letterSpacing: '-0.02em' }}>
                  {learning.decisions_supported}
                  <span style={{ fontSize: 12, color: 'var(--clh-text-tertiary)', fontWeight: 500 }}>
                    {' '}/ {learning.decisions_total}
                  </span>
                </div>
                <div className="definition">
                  {learning.unevidenced_decisions > 0
                    ? `${learning.unevidenced_decisions} recorded as internal judgement, not evidence-backed.`
                    : 'Every recorded decision links to a customer source.'}
                </div>
              </div>
              <div className="card-surface" style={{ padding: 12, boxShadow: 'none' }}>
                <div className="meta-label">Previous research reused</div>
                <div style={{ fontSize: 19, fontWeight: 660, letterSpacing: '-0.02em' }}>
                  {learning.insights_reused}
                  <span style={{ fontSize: 12, color: 'var(--clh-text-tertiary)', fontWeight: 500 }}>
                    {' '}/ {learning.findings_total}
                  </span>
                </div>
                <div className="definition">{learning.insights_reuse_display}</div>
              </div>
            </div>

            <div className="section-grid grid-2">
              <div className="inline" style={{ gap: 8, alignItems: 'flex-start' }}>
                <AlertTriangle size={14} color="var(--clh-warning)" style={{ marginTop: 2 }} />
                <div>
                  <div style={{ fontSize: 12.5, fontWeight: 600 }}>{learning.unresolved_questions} unresolved questions</div>
                  <div className="definition">Someone must decide whether to answer them or close them with a reason.</div>
                </div>
              </div>
              <div className="inline" style={{ gap: 8, alignItems: 'flex-start' }}>
                <AlertTriangle size={14} color="var(--clh-danger)" style={{ marginTop: 2 }} />
                <div>
                  <div style={{ fontSize: 12.5, fontWeight: 600 }}>{learning.overdue_actions} overdue actions</div>
                  <div className="definition">Ownership without a deadline is not ownership.</div>
                </div>
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Research by customer segment" subtitle="Who has actually been heard from">
          {data.segments.length === 0 ? (
            <EmptyState title="No participants yet" description="Add participants to see segment coverage." />
          ) : (
            <>
              <div
                className="stack stack-3"
                role="list"
                aria-label="Participants and evidence by customer segment"
              >
                {data.segments.map((segment, index) => {
                  const total = data.segments.reduce((sum, point) => sum + point.participants, 0) || 1
                  const share = Math.round((segment.participants / total) * 100)
                  return (
                    <div key={segment.segment} role="listitem">
                      <div className="row-between" style={{ fontSize: 12 }}>
                        <span className="inline">
                          <span
                            style={{
                              width: 7,
                              height: 7,
                              borderRadius: 99,
                              background: CHART_COLOURS[index % CHART_COLOURS.length],
                            }}
                          />
                          {SEGMENT_LABELS[segment.segment]}
                        </span>
                        <span className="text-secondary-clh">
                          {segment.participants} people · {segment.evidence} evidence · {share}%
                        </span>
                      </div>
                      <div className="mt-1">
                        <ProgressBar value={share} />
                      </div>
                    </div>
                  )
                })}
              </div>
              <HonestyNote>
                More conversations with repeat buyers will never reveal why lapsed customers left. Coverage matters
                more than volume.
              </HonestyNote>
            </>
          )}
        </SectionCard>
      </div>

      <div className="section-grid grid-sidebar mt-3">
        <SectionCard
          title="Research activity"
          subtitle="Interviews, evidence and insights by month — not a success score"
        >
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.timeline} margin={{ top: 6, right: 6, bottom: 0, left: -18 }}>
                <defs>
                  <linearGradient id="evidenceFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#176b52" stopOpacity={0.22} />
                    <stop offset="100%" stopColor="#176b52" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="interviewFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2f6b7a" stopOpacity={0.16} />
                    <stop offset="100%" stopColor="#2f6b7a" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#edeae0" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#6a6f65' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#6a6f65' }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e7e5dc' }} />
                <Area
                  type="monotone"
                  dataKey="evidence"
                  name="Evidence captured"
                  stroke="#176b52"
                  strokeWidth={2}
                  fill="url(#evidenceFill)"
                />
                <Area
                  type="monotone"
                  dataKey="interviews"
                  name="Interviews completed"
                  stroke="#2f6b7a"
                  strokeWidth={2}
                  fill="url(#interviewFill)"
                />
                <Area
                  type="monotone"
                  dataKey="insights"
                  name="Insights created"
                  stroke="#b08028"
                  strokeWidth={2}
                  fill="transparent"
                  strokeDasharray="4 3"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="inline mt-2" style={{ gap: 14, fontSize: 11.5, color: 'var(--clh-text-secondary)' }}>
            <span className="inline"><span style={{ width: 8, height: 8, background: '#176b52', borderRadius: 2 }} /> Evidence</span>
            <span className="inline"><span style={{ width: 8, height: 8, background: '#2f6b7a', borderRadius: 2 }} /> Interviews</span>
            <span className="inline"><span style={{ width: 8, height: 8, background: '#b08028', borderRadius: 2 }} /> Insights</span>
          </div>
        </SectionCard>

        <SectionCard title="Upcoming interviews" subtitle="Next conversations on the calendar">
          {data.upcoming_interviews.length === 0 ? (
            <EmptyState
              title="No interviews scheduled"
              description="Recruitment without a booked conversation is just a list."
              action={
                <Link to="/interviews" className="btn btn-outline-secondary btn-sm">
                  Schedule an interview
                </Link>
              }
            />
          ) : (
            <div className="stack stack-3">
              {data.upcoming_interviews.map((interview) => (
                <Link key={interview.id} to={`/interviews/${interview.id}`} className="card-surface" style={{ padding: 11, boxShadow: 'none' }}>
                  <div className="row-between">
                    <div style={{ fontWeight: 620, fontSize: 12.5 }}>{interview.participant?.display_name}</div>
                    <Pill tone="blue">{titleCase(interview.status)}</Pill>
                  </div>
                  <div className="definition mt-1">
                    {formatDateTime(interview.scheduled_at)} · {interview.duration_minutes} min ·{' '}
                    {interview.interviewer?.label ?? 'Unassigned'}
                  </div>
                  <div className="definition">{interview.code} · {interview.project?.label}</div>
                </Link>
              ))}
            </div>
          )}
        </SectionCard>
      </div>

      <div className="section-grid grid-2 mt-3">
        <SectionCard
          title="Recent insights"
          subtitle="Newest findings and how much evidence sits behind each"
          actions={<Link to="/insights" className="link-quiet">Open library</Link>}
          padded={false}
        >
          {data.recent_insights.length === 0 ? (
            <EmptyState title="No insights yet" description="Capture evidence, then draft an insight from it." />
          ) : (
            <div className="table-wrap">
              <table className="clh-table">
                <thead>
                  <tr>
                    <th>Insight</th>
                    <th>Status</th>
                    <th>Evidence</th>
                    <th>Owner</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_insights.map((insight) => (
                    <tr key={insight.id}>
                      <td>
                        <Link to={`/insights/${insight.id}`} className="table-link">
                          {insight.title}
                        </Link>
                        <div className="cell-sub">
                          {insight.code} · added {formatDate(insight.created_at)}
                        </div>
                      </td>
                      <td>
                        <Pill tone={insight.status === 'validated_internal' ? 'green' : insight.status === 'needs_more_research' ? 'blue' : 'amber'}>
                          {titleCase(insight.status)}
                        </Pill>
                      </td>
                      <td>
                        <span className="mono">{insight.evidence_count}</span>
                        {insight.contradictory_count > 0 && (
                          <span className="cell-sub">{insight.contradictory_count} contradictory</span>
                        )}
                      </td>
                      <td className="text-secondary-clh">{insight.owner?.label ?? 'Unassigned'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard
          title="Outstanding follow-ups"
          subtitle="Nearest due date first, including anything already late"
          actions={<Link to="/decisions" className="link-quiet">Decisions & actions</Link>}
          padded={false}
        >
          {data.outstanding_actions.length === 0 ? (
            <EmptyState title="Nothing outstanding" description="Every follow-up is closed." />
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
                  {data.outstanding_actions.map((action) => (
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
                        <Pill tone={ACTION_TONE[action.status]}>{titleCase(action.status)}</Pill>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>

      <div className="section-grid grid-sidebar mt-3">
        <SectionCard title="Recent research activity" subtitle="Audit trail across projects, evidence and decisions">
          <div className="timeline">
            {data.recent_activity.map((item) => (
              <div className="timeline-item" key={item.id}>
                <span className="timeline-dot current" />
                <div>
                  <div style={{ fontSize: 12.5 }}>
                    <span className="text-secondary-clh">{item.actor?.label ?? 'System'}</span> {item.summary}
                  </div>
                  <div className="definition mt-1">
                    {item.entity_label} · {relativeTime(item.created_at)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Decision & action status" subtitle="Where work is actually sitting">
          <div className="stack stack-3">
            <div>
              <div className="meta-label mb-2">Decisions</div>
              <div className="tag-row">
                {data.decision_status.length === 0 && <span className="definition">No decisions recorded.</span>}
                {data.decision_status.map((row) => (
                  <Pill key={row.status} tone={DECISION_TONE[row.status as keyof typeof DECISION_TONE] ?? 'neutral'}>
                    {titleCase(row.status)} · {row.count}
                  </Pill>
                ))}
              </div>
            </div>
            <div>
              <div className="meta-label mb-2">Actions</div>
              <div className="tag-row">
                {data.action_status.length === 0 && <span className="definition">No actions recorded.</span>}
                {data.action_status.map((row) => (
                  <Pill key={row.status} tone={ACTION_TONE[row.status as keyof typeof ACTION_TONE] ?? 'neutral'}>
                    {titleCase(row.status)} · {row.count}
                  </Pill>
                ))}
              </div>
            </div>
            <hr className="divider" />
            <div className="definition">{data.response_rate.definition}</div>
            {data.response_rate.sample_warning && (
              <div className="notice notice-warning" style={{ padding: '8px 10px' }}>
                <span className="notice-icon">!</span>
                <span>{data.response_rate.sample_warning}</span>
              </div>
            )}
            <Link to="/decisions" className="btn btn-outline-secondary btn-sm">
              Review decision register <ArrowUpRight size={12} />
            </Link>
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
