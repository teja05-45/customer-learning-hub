import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from 'react-bootstrap'
import { Plus, Search, Users } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useToast } from '../app/ToastProvider'
import type { Eligibility, Participant, ParticipantListResponse, Segment } from '../types'
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
import { ELIGIBILITY_LABELS, SEGMENT_FILTER_LABELS, SEGMENT_LABELS, formatDate, relativeTime } from '../utils/format'

const SEGMENTS: Segment[] = ['first_time_buyer', 'repeat_buyer', 'lapsed_buyer', 'household_buyer']

const ELIGIBILITY_TONE: Record<Eligibility, 'green' | 'amber' | 'red'> = {
  eligible: 'green',
  limited: 'amber',
  ineligible: 'red',
}

export function ParticipantsPage() {
  const [search, setSearch] = useState('')
  const [segments, setSegments] = useState<Segment[]>([])
  const [eligibility, setEligibility] = useState<Eligibility | ''>('')
  const [addOpen, setAddOpen] = useState(false)
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()

  const [form, setForm] = useState({
    display_name: '',
    segment: 'lapsed_buyer' as Segment,
    purchase_frequency: '',
    orders_count: 1,
    product_category: 'Shampoo',
    eligibility: 'eligible' as Eligibility,
    eligibility_note: '',
    contact_route: '',
  })
  const [formError, setFormError] = useState<string | null>(null)

  const params = useMemo(
    () => ({ q: search || undefined, segment: segments.length ? segments : undefined, eligibility: eligibility || undefined }),
    [search, segments, eligibility],
  )

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['participants', params],
    queryFn: () => api.get<ParticipantListResponse>(`/participants${toQuery(params)}`),
  })

  const createParticipant = useMutation({
    mutationFn: () => api.post<Participant>('/participants', form),
    onSuccess: (participant) => {
      void queryClient.invalidateQueries({ queryKey: ['participants'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setAddOpen(false)
      setForm({
        display_name: '',
        segment: 'lapsed_buyer',
        purchase_frequency: '',
        orders_count: 1,
        product_category: 'Shampoo',
        eligibility: 'eligible',
        eligibility_note: '',
        contact_route: '',
      })
      toast.push({
        title: 'Synthetic participant added',
        message: `${participant.display_name} (${participant.code}) is available to recruit.`,
        variant: 'success',
      })
    },
    onError: (error) => setFormError((error as Error).message),
  })

  const toggleSegment = (segment: Segment) => {
    setSegments((current) =>
      current.includes(segment) ? current.filter((entry) => entry !== segment) : [...current, segment],
    )
  }

  const totalInView = data?.total ?? 0

  return (
    <div className="page">
      <PageHeader
        title="Participants"
        description="A synthetic participant directory. Purchase context is kept so sampling decisions are visible; contact details are never stored here."
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setAddOpen(true)}>
            <Plus size={14} /> Add participant
          </button>
        }
      />

      <div className="notice notice-neutral mb-3">
        <span className="notice-icon">i</span>
        <div>
          <strong>Data minimisation is deliberate.</strong> This directory holds a synthetic ID, a display name, a
          segment and purchase context. No email address, phone number or address is accepted by the API, so no export
          or search result can leak one.
        </div>
      </div>

      <div className="section-grid grid-4 mb-3">
        {SEGMENTS.map((segment) => (
          <div className="stat-card" key={segment} style={{ minHeight: 76 }}>
            <div className="stat-label">{SEGMENT_LABELS[segment]}</div>
            <div className="stat-value" style={{ fontSize: 20 }}>
              {data?.segment_counts[segment] ?? 0}
            </div>
            <div className="stat-meta">in directory</div>
          </div>
        ))}
      </div>

      <SectionCard padded={false}>
        <div className="filter-bar">
          <div className="filter-input">
            <Search size={14} className="search-icon" />
            <input
              className="form-control"
              placeholder="Search by name, ID or eligibility note"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search participants"
            />
          </div>
          <div className="inline" style={{ flexWrap: 'wrap', gap: 6 }}>
            {SEGMENTS.map((segment) => (
              <button
                key={segment}
                type="button"
                className={`filter-chip${segments.includes(segment) ? ' active' : ''}`}
                onClick={() => toggleSegment(segment)}
              >
                {SEGMENT_FILTER_LABELS[segment]}
              </button>
            ))}
          </div>
          <select
            className="form-select"
            style={{ width: 150 }}
            value={eligibility}
            onChange={(event) => setEligibility(event.target.value as Eligibility | '')}
            aria-label="Filter by eligibility"
          >
            <option value="">All eligibility</option>
            <option value="eligible">Eligible</option>
            <option value="limited">Limited contact</option>
            <option value="ineligible">Not eligible</option>
          </select>
          <div style={{ marginLeft: 'auto' }} className="definition">
            {isFetching ? 'Refreshing…' : `${totalInView} participant(s)`}
          </div>
        </div>

        {isLoading && <TableSkeleton rows={6} columns={6} />}
        {error && (
          <div style={{ padding: 16 }}>
            <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
          </div>
        )}

        {data && data.items.length === 0 && (
          <EmptyState
            icon={<Users size={18} />}
            title="No participants match those filters"
            description="Try a different segment, or add a synthetic participant to demonstrate a new research scenario."
            action={
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => { setSearch(''); setSegments([]); setEligibility('') }}>
                Clear filters
              </button>
            }
          />
        )}

        {data && data.items.length > 0 && (
          <div className="table-wrap">
            <table className="clh-table">
              <thead>
                <tr>
                  <th>Participant</th>
                  <th>Segment</th>
                  <th>Purchase context</th>
                  <th>Eligibility</th>
                  <th>Research contact</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.items.map((participant) => (
                  <tr key={participant.id} className="is-clickable" onClick={() => navigate(`/participants/${participant.id}`)}>
                    <td>
                      <span className="table-link">{participant.display_name}</span>
                      <div className="cell-sub mono">{participant.code}</div>
                    </td>
                    <td>
                      <Pill tone="outline">{SEGMENT_LABELS[participant.segment]}</Pill>
                    </td>
                    <td className="text-secondary-clh">
                      {participant.purchase_frequency || 'Not recorded'}
                      <div className="cell-sub">
                        {participant.orders_count} order(s) · {participant.product_category || 'category unknown'}
                      </div>
                    </td>
                    <td>
                      <Pill tone={ELIGIBILITY_TONE[participant.eligibility]}>
                        {ELIGIBILITY_LABELS[participant.eligibility]}
                      </Pill>
                    </td>
                    <td className="text-secondary-clh">
                      {participant.last_research_contact_at ? relativeTime(participant.last_research_contact_at) : 'Never contacted'}
                      <div className="cell-sub">last purchase {formatDate(participant.last_purchase_at)}</div>
                    </td>
                    <td>
                      <Link to={`/participants/${participant.id}`} className="link-quiet" onClick={(event) => event.stopPropagation()}>
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <div className="mt-3">
        <Notice tone="warning" title="Sampling is the easiest place to go wrong">
          The people who reply fastest are usually engaged repeat buyers. A directory that only contains those voices
          will produce confident-sounding conclusions about everyone else.
        </Notice>
      </div>

      <Modal show={addOpen} onHide={() => setAddOpen(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Add a synthetic participant</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="notice notice-neutral mb-3">
            <span className="notice-icon">i</span>
            <span>Fictional record only. Do not enter real customer details; the form does not collect contact data.</span>
          </div>
          <div className="section-grid grid-2" style={{ gap: 12 }}>
            <div>
              <label className="form-label" htmlFor="participantspage-field-1">
                Display name<span className="required-mark">*</span>
              </label>
              <input id="participantspage-field-1"
                className="form-control"
                value={form.display_name}
                onChange={(event) => setForm({ ...form, display_name: event.target.value })}
                placeholder="e.g. Priya Sharma"
              />
            </div>
            <div>
              <label className="form-label" htmlFor="participantspage-field-2">Customer segment</label>
              <select id="participantspage-field-2"
                className="form-select"
                value={form.segment}
                onChange={(event) => setForm({ ...form, segment: event.target.value as Segment })}
              >
                {SEGMENTS.map((segment) => (
                  <option key={segment} value={segment}>
                    {SEGMENT_LABELS[segment]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="form-label" htmlFor="participantspage-field-3">Purchase frequency</label>
              <input id="participantspage-field-3"
                className="form-control"
                value={form.purchase_frequency}
                onChange={(event) => setForm({ ...form, purchase_frequency: event.target.value })}
                placeholder="e.g. Every 6–8 weeks"
              />
            </div>
            <div>
              <label className="form-label" htmlFor="participantspage-field-4">Orders placed</label>
              <input id="participantspage-field-4"
                type="number"
                min={0}
                max={500}
                className="form-control"
                value={form.orders_count}
                onChange={(event) => setForm({ ...form, orders_count: Number(event.target.value) })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="participantspage-field-5">Product category</label>
              <input id="participantspage-field-5"
                className="form-control"
                value={form.product_category}
                onChange={(event) => setForm({ ...form, product_category: event.target.value })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="participantspage-field-6">Research eligibility</label>
              <select id="participantspage-field-6"
                className="form-select"
                value={form.eligibility}
                onChange={(event) => setForm({ ...form, eligibility: event.target.value as Eligibility })}
              >
                <option value="eligible">Eligible</option>
                <option value="limited">Limited contact</option>
                <option value="ineligible">Not eligible</option>
              </select>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="participantspage-field-7">Eligibility note</label>
              <input id="participantspage-field-7"
                className="form-control"
                value={form.eligibility_note}
                onChange={(event) => setForm({ ...form, eligibility_note: event.target.value })}
                placeholder="Why is this person eligible, limited or excluded?"
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="participantspage-field-8">Controlled contact route (description only)</label>
              <input id="participantspage-field-8"
                className="form-control"
                value={form.contact_route}
                onChange={(event) => setForm({ ...form, contact_route: event.target.value })}
                placeholder="e.g. Controlled export batch #12, handled by Operations"
              />
              <div className="form-text">
                Describe how Operations would reach this person. Never paste an email address or phone number.
              </div>
            </div>
          </div>
          {formError && (
            <div className="mt-3">
              <Notice tone="danger">{formError}</Notice>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setAddOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={createParticipant.isPending}
            onClick={() => {
              if (form.display_name.trim().length < 2) {
                setFormError('Give the participant a display name of at least 2 characters.')
                return
              }
              setFormError(null)
              createParticipant.mutate()
            }}
          >
            {createParticipant.isPending ? 'Adding…' : 'Add participant'}
          </button>
        </Modal.Footer>
      </Modal>

      <div className="mt-3 section-grid grid-3">
        <MetaItem label="Total participants" value={String(data?.total ?? 0)} />
        <MetaItem label="Eligible for research" value={String(data?.items.filter((item) => item.eligibility === 'eligible').length ?? 0)} />
        <MetaItem label="Directory source" value="Synthetic demo dataset" />
      </div>
    </div>
  )
}
