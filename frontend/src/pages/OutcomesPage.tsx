import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from 'react-bootstrap'
import { ArrowUpRight, CircleDashed, Target, TrendingDown, TrendingUp } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useToast } from '../app/ToastProvider'
import type { DecisionListResponse, Outcome, OutcomeListResponse, OutcomeStatus } from '../types'
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
  Notice,
  PageHeader,
  Pill,
  SectionCard,
  StatCard,
} from '../components/ui'
import { formatDate, formatDateTime } from '../utils/format'

const STATUS_TONE: Record<OutcomeStatus, 'green' | 'amber' | 'red' | 'purple' | 'outline'> = {
  planned: 'outline',
  measurement_pending: 'amber',
  achieved: 'green',
  not_achieved: 'red',
  inconclusive: 'purple',
}

const STATUS_LABEL: Record<OutcomeStatus, string> = {
  planned: 'Planned',
  measurement_pending: 'Measurement pending',
  achieved: 'Achieved',
  not_achieved: 'Not achieved',
  inconclusive: 'Inconclusive',
}

function valueWithUnit(value: number | null, unit: string) {
  if (value === null || value === undefined) return 'Not recorded'
  return `${value}${unit ? ` ${unit}` : ''}`
}

export function OutcomesPage() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [params] = useSearchParams()
  const focus = params.get('focus')
  const [statusFilter, setStatusFilter] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [recordFor, setRecordFor] = useState<Outcome | null>(null)
  const [form, setForm] = useState({
    name: '',
    decision_id: '',
    metric_definition: '',
    baseline_value: '',
    target_value: '',
    unit: '',
    direction: 'increase' as 'increase' | 'decrease',
    measurement_start: '',
    measurement_end: '',
    data_source: '',
    notes: '',
  })
  const [recordForm, setRecordForm] = useState({ actual_value: '', notes: '' })
  const [formError, setFormError] = useState<string | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['outcomes', statusFilter],
    queryFn: () =>
      api.get<OutcomeListResponse>(`/outcomes${toQuery({ status: statusFilter })}`),
  })

  const decisions = useQuery({
    queryKey: ['decisions', 'for-outcome'],
    queryFn: () => api.get<DecisionListResponse>('/decisions'),
    enabled: createOpen,
  })

  useEffect(() => {
    if (focus && data) {
      const item = data.items.find((outcome) => outcome.id === focus)
      if (item) setRecordFor(item)
    }
  }, [focus, data])

  const createOutcome = useMutation({
    mutationFn: () =>
      api.post<Outcome>('/outcomes', {
        name: form.name,
        decision_id: form.decision_id,
        metric_definition: form.metric_definition,
        baseline_value: form.baseline_value === '' ? null : Number(form.baseline_value),
        target_value: form.target_value === '' ? null : Number(form.target_value),
        unit: form.unit,
        direction: form.direction,
        measurement_start: form.measurement_start || null,
        measurement_end: form.measurement_end || null,
        data_source: form.data_source,
        notes: form.notes,
      }),
    onSuccess: () => {
      setCreateOpen(false)
      setForm({
        name: '',
        decision_id: '',
        metric_definition: '',
        baseline_value: '',
        target_value: '',
        unit: '',
        direction: 'increase',
        measurement_start: '',
        measurement_end: '',
        data_source: '',
        notes: '',
      })
      void queryClient.invalidateQueries({ queryKey: ['outcomes'] })
      toast.push({
        title: 'Outcome planned',
        message: 'No result is claimed until an actual measurement is recorded.',
        variant: 'success',
      })
    },
    onError: (error) => setFormError((error as Error).message),
  })

  const recordOutcome = useMutation({
    mutationFn: () =>
      api.patch<Outcome>(`/outcomes/${recordFor?.id}`, {
        actual_value: Number(recordForm.actual_value),
        notes: recordForm.notes,
      }),
    onSuccess: (outcome) => {
      setRecordFor(null)
      setRecordForm({ actual_value: '', notes: '' })
      void queryClient.invalidateQueries({ queryKey: ['outcomes'] })
      void queryClient.invalidateQueries({ queryKey: ['journey'] })
      toast.push({
        title: `Result recorded: ${STATUS_LABEL[outcome.status]}`,
        message: outcome.status_reason,
        variant: outcome.status === 'not_achieved' ? 'error' : 'success',
      })
    },
    onError: (error) => toast.push({ title: 'Could not record result', message: (error as Error).message, variant: 'error' }),
  })

  const stats = useMemo(() => {
    const items = data?.items ?? []
    return {
      total: items.length,
      measured: items.filter((item) => ['achieved', 'not_achieved', 'inconclusive'].includes(item.status)).length,
      pending: items.filter((item) => ['planned', 'measurement_pending'].includes(item.status)).length,
      overdue: items.filter((item) => item.is_overdue).length,
      achieved: items.filter((item) => item.status === 'achieved').length,
    }
  }, [data])

  return (
    <div className="page">
      <PageHeader
        title="Outcome measurement"
        description="Close the loop: record what a decision was expected to change, then record what actually happened. A result is never claimed before it is measured."
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            <Target size={14} /> Plan an outcome
          </button>
        }
      />

      <div className="section-grid grid-4 mb-3">
        <StatCard label="Outcomes" value={stats.total} meta="Planned and measured across decisions" />
        <StatCard label="Measured" value={stats.measured} meta="A result has been recorded" />
        <StatCard label="Awaiting result" value={stats.pending} meta="Planned or inside the measurement window" />
        <StatCard
          label="Measurement overdue"
          value={stats.overdue}
          meta="The window closed without a result"
          warning={stats.overdue > 0}
        />
      </div>

      <SectionCard
        title="Measurement register"
        subtitle="Achieved and not achieved are calculated from the target and direction, not typed in by hand."
        actions={
          <select
            className="form-select"
            style={{ width: 190 }}
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            aria-label="Filter by outcome status"
          >
            <option value="">All statuses</option>
            {Object.entries(STATUS_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        }
      >
        {isLoading && <LoadingBlock rows={5} />}
        {error && <ErrorState message={(error as Error).message} onRetry={() => refetch()} />}
        {data && data.items.length === 0 && (
          <EmptyState
            title="No outcomes recorded"
            description="Plan an outcome against a decision so the team can judge whether the work changed anything."
          />
        )}
        {data && data.items.length > 0 && (
          <div className="stack stack-3">
            {data.items.map((outcome) => (
              <article key={outcome.id} className="card-surface" style={{ padding: '14px 16px' }}>
                <div className="row-between" style={{ alignItems: 'flex-start', flexWrap: 'wrap', gap: 8 }}>
                  <div style={{ minWidth: 0 }}>
                    <div className="inline" style={{ gap: 8, flexWrap: 'wrap' }}>
                      <span className="mono" style={{ fontSize: 11.5, color: 'var(--clh-text-tertiary)' }}>
                        {outcome.code}
                      </span>
                      <Pill tone={STATUS_TONE[outcome.status]}>{STATUS_LABEL[outcome.status]}</Pill>
                      {outcome.is_overdue && <Pill tone="red">Measurement overdue</Pill>}
                    </div>
                    <h3 style={{ fontSize: 14.5, marginTop: 5 }}>{outcome.name}</h3>
                    <div className="definition" style={{ marginTop: 3 }}>
                      {outcome.metric_definition}
                    </div>
                  </div>
                  <div className="d-flex gap-2">
                    {outcome.decision && (
                      <Link to={`/decisions/${outcome.decision.id}`} className="btn btn-outline-secondary btn-sm">
                        {outcome.decision.sublabel} <ArrowUpRight size={12} />
                      </Link>
                    )}
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => {
                        setFormError(null)
                        setRecordFor(outcome)
                        setRecordForm({ actual_value: '', notes: outcome.notes })
                      }}
                    >
                      {outcome.actual_value === null ? 'Record result' : 'Update result'}
                    </button>
                  </div>
                </div>

                <div className="outcome-measures">
                  <div>
                    <div className="meta-label">Baseline</div>
                    <div className="meta-value">{valueWithUnit(outcome.baseline_value, outcome.unit)}</div>
                  </div>
                  <div>
                    <div className="meta-label">Target</div>
                    <div className="meta-value">
                      {outcome.direction === 'increase' ? <TrendingUp size={12} /> : <TrendingDown size={12} />}{' '}
                      {valueWithUnit(outcome.target_value, outcome.unit)}
                    </div>
                  </div>
                  <div>
                    <div className="meta-label">Actual</div>
                    <div className="meta-value">{valueWithUnit(outcome.actual_value, outcome.unit)}</div>
                  </div>
                  <div>
                    <div className="meta-label">Measurement window</div>
                    <div className="meta-value">
                      {formatDate(outcome.measurement_start)} → {formatDate(outcome.measurement_end)}
                    </div>
                  </div>
                  <div>
                    <div className="meta-label">Owner</div>
                    <div className="meta-value">{outcome.owner?.label ?? 'Unassigned'}</div>
                  </div>
                  <div>
                    <div className="meta-label">Data source</div>
                    <div className="meta-value">{outcome.data_source || 'Not recorded'}</div>
                  </div>
                </div>

                <div className="definition" style={{ marginTop: 8 }}>
                  <CircleDashed size={11} /> {outcome.status_reason}
                  {outcome.recorded_at ? ` Recorded ${formatDateTime(outcome.recorded_at)}.` : ''}
                </div>
              </article>
            ))}
          </div>
        )}
      </SectionCard>

      <div className="mt-3">
        <Notice tone="neutral">
          A result without a target is stored as <strong>inconclusive</strong>, never as achieved. Baselines and
          targets are recorded before the measurement window, so a result cannot be judged against a target invented
          afterwards.
        </Notice>
      </div>

      <Modal show={createOpen} onHide={() => setCreateOpen(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Plan an outcome</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="section-grid grid-2" style={{ gap: 12 }}>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="outcome-name">
                Outcome name<span className="required-mark">*</span>
              </label>
              <input
                id="outcome-name"
                className="form-control"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                placeholder="e.g. Second purchase within 60 days"
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="outcome-decision">
                Decision this outcome belongs to<span className="required-mark">*</span>
              </label>
              <select
                id="outcome-decision"
                className="form-select"
                value={form.decision_id}
                onChange={(event) => setForm({ ...form, decision_id: event.target.value })}
              >
                <option value="">Select a decision…</option>
                {decisions.data?.items.map((decision) => (
                  <option key={decision.id} value={decision.id}>
                    {decision.code} · {decision.title}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="outcome-metric">
                Metric definition<span className="required-mark">*</span>
              </label>
              <textarea
                id="outcome-metric"
                className="form-control"
                rows={2}
                value={form.metric_definition}
                onChange={(event) => setForm({ ...form, metric_definition: event.target.value })}
                placeholder="Exactly what is counted, over which population and window."
              />
            </div>
            <div>
              <label className="form-label" htmlFor="outcome-baseline">Baseline</label>
              <input
                id="outcome-baseline"
                type="number"
                step="any"
                className="form-control"
                value={form.baseline_value}
                onChange={(event) => setForm({ ...form, baseline_value: event.target.value })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="outcome-target">Target</label>
              <input
                id="outcome-target"
                type="number"
                step="any"
                className="form-control"
                value={form.target_value}
                onChange={(event) => setForm({ ...form, target_value: event.target.value })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="outcome-unit">Unit</label>
              <input
                id="outcome-unit"
                className="form-control"
                value={form.unit}
                onChange={(event) => setForm({ ...form, unit: event.target.value })}
                placeholder="%, days, orders…"
              />
            </div>
            <div>
              <label className="form-label" htmlFor="outcome-direction">Success direction</label>
              <select
                id="outcome-direction"
                className="form-select"
                value={form.direction}
                onChange={(event) => setForm({ ...form, direction: event.target.value as 'increase' | 'decrease' })}
              >
                <option value="increase">Higher is better</option>
                <option value="decrease">Lower is better</option>
              </select>
            </div>
            <div>
              <label className="form-label" htmlFor="outcome-start">Measurement starts</label>
              <input
                id="outcome-start"
                type="date"
                className="form-control"
                value={form.measurement_start}
                onChange={(event) => setForm({ ...form, measurement_start: event.target.value })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="outcome-end">Measurement ends</label>
              <input
                id="outcome-end"
                type="date"
                className="form-control"
                value={form.measurement_end}
                onChange={(event) => setForm({ ...form, measurement_end: event.target.value })}
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="outcome-source">Data source</label>
              <input
                id="outcome-source"
                className="form-control"
                value={form.data_source}
                onChange={(event) => setForm({ ...form, data_source: event.target.value })}
                placeholder="Where the actual result will come from"
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="outcome-notes">Notes</label>
              <textarea
                id="outcome-notes"
                className="form-control"
                rows={2}
                value={form.notes}
                onChange={(event) => setForm({ ...form, notes: event.target.value })}
              />
            </div>
            {formError && (
              <div style={{ gridColumn: '1 / -1' }}>
                <Notice tone="danger">{formError}</Notice>
              </div>
            )}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setCreateOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={
              form.name.trim().length < 5 ||
              !form.decision_id ||
              form.metric_definition.trim().length < 5 ||
              createOutcome.isPending
            }
            onClick={() => {
              setFormError(null)
              createOutcome.mutate()
            }}
          >
            {createOutcome.isPending ? 'Saving…' : 'Plan outcome'}
          </button>
        </Modal.Footer>
      </Modal>

      <Modal show={Boolean(recordFor)} onHide={() => setRecordFor(null)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Record the actual result</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {recordFor && (
            <div className="stack stack-3">
              <div>
                <div className="meta-label">Outcome</div>
                <div style={{ fontWeight: 600 }}>{recordFor.name}</div>
                <div className="definition">{recordFor.metric_definition}</div>
              </div>
              <div className="section-grid grid-3" style={{ gap: 10 }}>
                <div>
                  <div className="meta-label">Baseline</div>
                  <div>{valueWithUnit(recordFor.baseline_value, recordFor.unit)}</div>
                </div>
                <div>
                  <div className="meta-label">Target</div>
                  <div>{valueWithUnit(recordFor.target_value, recordFor.unit)}</div>
                </div>
                <div>
                  <div className="meta-label">Direction</div>
                  <div>{recordFor.direction === 'increase' ? 'Higher is better' : 'Lower is better'}</div>
                </div>
              </div>
              <div>
                <label className="form-label" htmlFor="outcome-actual">
                  Actual result<span className="required-mark">*</span>
                </label>
                <input
                  id="outcome-actual"
                  type="number"
                  step="any"
                  className="form-control"
                  value={recordForm.actual_value}
                  onChange={(event) => setRecordForm({ ...recordForm, actual_value: event.target.value })}
                />
                <div className="form-text">
                  The status is calculated from this value. A missing target makes the result inconclusive.
                </div>
              </div>
              <div>
                <label className="form-label" htmlFor="outcome-result-notes">Notes</label>
                <textarea
                  id="outcome-result-notes"
                  className="form-control"
                  rows={2}
                  value={recordForm.notes}
                  onChange={(event) => setRecordForm({ ...recordForm, notes: event.target.value })}
                />
              </div>
              <Notice tone="warning">
                Recording a result is permanent history. Updating the value later changes the judgement, and both
                the old and new value remain visible in the audit trail.
              </Notice>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setRecordFor(null)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={recordForm.actual_value === '' || recordOutcome.isPending}
            onClick={() => recordOutcome.mutate()}
          >
            {recordOutcome.isPending ? 'Recording…' : 'Record result'}
          </button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
