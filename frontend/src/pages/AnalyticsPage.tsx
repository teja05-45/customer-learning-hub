import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AlertTriangle, Info, Ruler } from 'lucide-react'
import { api } from '../services/api'
import type { Analytics, AnalyticsMetric } from '../types'
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
  ACTION_TONE,
  DECISION_TONE,
  SEGMENT_LABELS,
  formatDateTime,
  titleCase,
} from '../utils/format'

const BASIS_LABEL: Record<AnalyticsMetric['basis'], string> = {
  observed: 'Observed',
  calculated: 'Calculated',
  illustrative: 'Illustrative',
  pending_baseline: 'Pending baseline',
}

const BASIS_TONE: Record<AnalyticsMetric['basis'], 'green' | 'blue' | 'purple' | 'amber'> = {
  observed: 'green',
  calculated: 'blue',
  illustrative: 'purple',
  pending_baseline: 'amber',
}

export function AnalyticsPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => api.get<Analytics>('/analytics'),
  })

  if (isLoading) {
    return (
      <div className="page">
        <PageHeader title="Analytics" description="Loading measured signals…" />
        <SectionCard>
          <LoadingBlock rows={8} />
        </SectionCard>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="page">
        <PageHeader title="Analytics" />
        <ErrorState message={(error as Error)?.message ?? 'Analytics could not be loaded.'} onRetry={() => refetch()} />
      </div>
    )
  }

  const calculated = data.metrics.filter((metric) => metric.basis === 'calculated')
  const observed = data.metrics.filter((metric) => metric.basis === 'observed')
  const pending = data.metrics.filter((metric) => metric.basis === 'pending_baseline')

  return (
    <div className="page">
      <PageHeader
        title="Analytics"
        description="Whether customer learning is becoming easier to reuse and more likely to inform a decision — not whether more interviews happened."
        meta={<span className="definition">Generated {formatDateTime(data.generated_at)}</span>}
      />

      <div className="notice notice-warning mb-3">
        <span className="notice-icon">
          <Info size={15} />
        </span>
        <div>
          <strong>How to read this page.</strong> {data.honesty_note}
        </div>
      </div>

      <div className="section-grid grid-3">
        {calculated.map((metric) => (
          <div className="stat-card" key={metric.key} style={{ gap: 8 }}>
            <div className="row-between">
              <span className="stat-label">{metric.label}</span>
              <Pill tone={BASIS_TONE[metric.basis]}>{BASIS_LABEL[metric.basis]}</Pill>
            </div>
            <div className="stat-value" style={{ fontSize: 21 }}>
              {metric.display}
            </div>
            <div className="stat-meta">{metric.definition}</div>
            {metric.note && <div className="definition">{metric.note}</div>}
          </div>
        ))}
      </div>

      <div className="section-grid grid-2 mt-3">
        <SectionCard title="Research by customer segment" subtitle="Who has been heard from, not how many interviews happened">
          {data.segment_distribution.length === 0 ? (
            <EmptyState title="No participants yet" />
          ) : (
            <div style={{ height: 250 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.segment_distribution.map((segment) => ({
                    name: SEGMENT_LABELS[segment.segment],
                    participants: segment.participants,
                    interviews: segment.interviews,
                    evidence: segment.evidence,
                  }))}
                  margin={{ top: 8, right: 8, bottom: 0, left: -18 }}
                >
                  <CartesianGrid stroke="#eef2f7" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 10.5, fill: '#94a3b8' }} axisLine={false} tickLine={false} interval={0} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                  <Bar dataKey="participants" name="Participants" fill="#c7d7fb" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="interviews" name="Interviews" fill="#2563eb" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="evidence" name="Evidence" fill="#0284c7" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="definition mt-2">
            A wide gap between participants and interviews means people were recruited but never spoke. A gap between
            interviews and evidence means conversations happened and nothing usable was captured.
          </div>
        </SectionCard>

        <SectionCard title="Where decisions and actions sit" subtitle="Movement, not volume">
          <div className="stack stack-3">
            <div>
              <div className="meta-label mb-2">Decisions</div>
              <div className="tag-row">
                {data.decision_funnel.length === 0 && <span className="definition">No decisions recorded.</span>}
                {data.decision_funnel.map((row) => (
                  <Pill key={row.status} tone={DECISION_TONE[row.status as keyof typeof DECISION_TONE] ?? 'neutral'}>
                    {titleCase(row.status)} · {row.count}
                  </Pill>
                ))}
              </div>
            </div>
            <div>
              <div className="meta-label mb-2">Actions</div>
              <div className="tag-row">
                {data.action_completion.length === 0 && <span className="definition">No actions recorded.</span>}
                {data.action_completion.map((row) => (
                  <Pill key={row.status} tone={ACTION_TONE[row.status as keyof typeof ACTION_TONE] ?? 'neutral'}>
                    {titleCase(row.status)} · {row.count}
                  </Pill>
                ))}
              </div>
            </div>
            <hr className="divider" />
            {observed.map((metric) => (
              <div key={metric.key}>
                <div className="row-between">
                  <span style={{ fontSize: 12.5, fontWeight: 600 }}>{metric.label}</span>
                  <span className="mono" style={{ fontSize: 12.5 }}>
                    {metric.display}
                  </span>
                </div>
                <div className="definition">{metric.definition}</div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <div className="section-grid grid-2 mt-3">
        <SectionCard title="Unresolved research questions" subtitle="Questions nobody has answered or closed">
          {data.unresolved_questions.length === 0 ? (
            <EmptyState title="Nothing unresolved" description="Every question has a written resolution." />
          ) : (
            <div className="stack stack-2">
              {data.unresolved_questions.map((question) => (
                <div key={question.id} className="card-surface" style={{ padding: 11, boxShadow: 'none' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 550 }}>{question.text}</div>
                  <div className="row-between mt-1">
                    <Link to={`/projects/${question.project_id}`} className="link-quiet">
                      {question.project_name}
                    </Link>
                    <Pill tone="amber">Open</Pill>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Insight reuse" subtitle="Which findings were picked up again after they were written">
          {data.reuse_detail.length === 0 ? (
            <EmptyState title="No insights yet" />
          ) : (
            <div className="table-wrap">
              <table className="clh-table">
                <thead>
                  <tr>
                    <th>Insight</th>
                    <th>Decisions</th>
                    <th>Reused</th>
                  </tr>
                </thead>
                <tbody>
                  {data.reuse_detail.map((row) => (
                    <tr key={row.insight_id}>
                      <td>
                        <Link to={`/insights/${row.insight_id}`} className="table-link">
                          {row.title}
                        </Link>
                        <div className="cell-sub">{row.code}</div>
                      </td>
                      <td className="mono">{row.decisions}</td>
                      <td>
                        <Pill tone={row.reused ? 'green' : 'outline'}>{row.reused ? 'Yes' : 'Not yet'}</Pill>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="definition mt-2">
            Reused means linked to two or more decisions, or linked to a decision at least 14 days after the insight was
            written. The definition travels with the metric so it cannot be quietly reinterpreted.
          </div>
        </SectionCard>
      </div>

      <div className="mt-3">
        <SectionCard
          title="Measurement gaps"
          subtitle="What the business still needs before these numbers mean anything strategic"
          icon={<Ruler size={14} />}
        >
          <div className="stack stack-3">
            {data.measurement_gaps.map((gap) => (
              <div key={gap.key} className="card-surface" style={{ padding: 12, boxShadow: 'none' }}>
                <div className="row-between">
                  <span style={{ fontSize: 13, fontWeight: 620 }}>{gap.label}</span>
                  <Pill tone="amber">No baseline</Pill>
                </div>
                <div className="definition mt-1">{gap.why}</div>
                <div className="definition mt-1">
                  <strong>How to collect it:</strong> {gap.how_to_collect}
                </div>
              </div>
            ))}
          </div>

          {pending.length > 0 && (
            <div className="mt-3">
              <Notice tone="neutral" icon={<AlertTriangle size={15} />}>
                {pending.map((metric) => metric.label).join(', ')} are deliberately shown without a value. Displaying a
                number there would be invention, not measurement.
              </Notice>
            </div>
          )}
        </SectionCard>
      </div>

      <div className="section-grid grid-3 mt-3">
        {pending.map((metric) => (
          <div className="card-surface" key={metric.key} style={{ padding: 14 }}>
            <div className="row-between">
              <span className="stat-label">{metric.label}</span>
              <Pill tone="amber">Pending baseline</Pill>
            </div>
            <div style={{ fontSize: 16, fontWeight: 620, marginTop: 8 }}>{metric.display}</div>
            <div className="definition mt-1">{metric.definition}</div>
            {metric.target && (
              <div className="definition mt-2">
                <strong>Next step:</strong> {metric.target}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-3">
        <Notice tone="neutral" icon={<Info size={15} />}>
          This page does not attribute changes in repeat purchase or revenue to research activity. Those outcomes have
          multiple causes, and claiming otherwise would make the whole practice less credible.
        </Notice>
      </div>
    </div>
  )
}
