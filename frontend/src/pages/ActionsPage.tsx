import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from 'react-bootstrap'
import { CalendarClock, Plus, Search } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useToast } from '../app/ToastProvider'
import { useSession } from '../app/SessionProvider'
import type { ActionListResponse, ActionStatus, BusinessAction, Priority } from '../types'
import {
  EmptyState,
  ErrorState,
  Notice,
  PageHeader,
  Pill,
  SectionCard,
  TableSkeleton,
} from '../components/ui'
import { ACTION_TONE, PRIORITY_TONE, formatDate, relativeTime, titleCase } from '../utils/format'

const STATUSES: ActionStatus[] = ['not_started', 'in_progress', 'completed', 'blocked']

export function ActionsPage() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const { users } = useSession()
  const [statuses, setStatuses] = useState<ActionStatus[]>([])
  const [ownerId, setOwnerId] = useState('')
  const [search, setSearch] = useState('')
  const [overdueOnly, setOverdueOnly] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [form, setForm] = useState({
    title: '',
    description: '',
    owner_id: '',
    due_date: '',
    priority: 'medium' as Priority,
  })
  const [formError, setFormError] = useState<string | null>(null)

  const params = useMemo(
    () => ({
      status: statuses.length ? statuses : undefined,
      owner_id: ownerId || undefined,
      q: search || undefined,
      overdue_only: overdueOnly || undefined,
    }),
    [statuses, ownerId, search, overdueOnly],
  )

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['actions', params],
    queryFn: () => api.get<ActionListResponse>(`/actions${toQuery(params)}`),
  })

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: ActionStatus }) => api.patch(`/actions/${id}`, { status }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['actions'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.push({ title: 'Action updated', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not update action', message: (error as Error).message, variant: 'error' }),
  })

  const createAction = useMutation({
    mutationFn: () =>
      api.post<BusinessAction>('/actions', {
        ...form,
        owner_id: form.owner_id || null,
        due_date: form.due_date || null,
      }),
    onSuccess: () => {
      setCreateOpen(false)
      setForm({ title: '', description: '', owner_id: '', due_date: '', priority: 'medium' })
      void queryClient.invalidateQueries({ queryKey: ['actions'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.push({ title: 'Action created', message: 'It has an owner and a due date.', variant: 'success' })
    },
    onError: (error) => setFormError((error as Error).message),
  })

  return (
    <div className="page">
      <PageHeader
        title="Actions"
        description="Every follow-up from a decision, with an owner, a due date and an honest status. Blocked work is visible rather than quietly late."
        actions={
          <>
            <Link to="/decisions" className="btn btn-outline-secondary">
              Decision register
            </Link>
            <button type="button" className="btn btn-primary" onClick={() => setCreateOpen(true)}>
              <Plus size={14} /> New action
            </button>
          </>
        }
      />

      <div className="section-grid grid-4 mb-3">
        {STATUSES.map((status) => (
          <button
            key={status}
            type="button"
            className="stat-card"
            style={{
              textAlign: 'left',
              cursor: 'pointer',
              borderColor: statuses.includes(status) ? 'var(--clh-primary)' : undefined,
              background: statuses.includes(status) ? 'var(--clh-primary-soft)' : undefined,
            }}
            onClick={() =>
              setStatuses((current) =>
                current.includes(status) ? current.filter((entry) => entry !== status) : [...current, status],
              )
            }
          >
            <div className="stat-label">{titleCase(status)}</div>
            <div className="stat-value">{data?.status_counts[status] ?? 0}</div>
            <div className="stat-meta">{statuses.includes(status) ? 'filtering' : 'click to filter'}</div>
          </button>
        ))}
      </div>

      {(data?.overdue ?? 0) > 0 && (
        <div className="mb-3">
          <Notice tone="danger" icon={<CalendarClock size={15} />} title={`${data?.overdue} action(s) are overdue`}>
            An overdue action is usually a sign that the owner changed or the decision was quietly dropped. Decide
            which it is.
          </Notice>
        </div>
      )}

      <SectionCard padded={false}>
        <div className="filter-bar">
          <div className="filter-input">
            <Search size={14} className="search-icon" />
            <input
              className="form-control"
              placeholder="Search actions"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search actions"
            />
          </div>
          <select
            className="form-select"
            style={{ width: 190 }}
            value={ownerId}
            onChange={(event) => setOwnerId(event.target.value)}
            aria-label="Filter by owner"
          >
            <option value="">All owners</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            className={`filter-chip${overdueOnly ? ' active' : ''}`}
            onClick={() => setOverdueOnly((value) => !value)}
          >
            Overdue only
          </button>
          <div style={{ marginLeft: 'auto' }} className="definition">
            {data?.total ?? 0} action(s)
          </div>
        </div>

        {isLoading && <TableSkeleton rows={5} columns={6} />}
        {error && (
          <div style={{ padding: 16 }}>
            <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
          </div>
        )}
        {data && data.items.length === 0 && (
          <EmptyState
            icon={<CalendarClock size={18} />}
            title="Nothing in this view"
            description="Open actions appear here. Clearing the filters may reveal completed work."
          />
        )}

        {data && data.items.length > 0 && (
          <div className="table-wrap">
            <table className="clh-table">
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Decision</th>
                  <th>Owner</th>
                  <th>Priority</th>
                  <th>Due</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((action) => (
                  <tr key={action.id}>
                    <td style={{ maxWidth: 320 }}>
                      <span style={{ fontWeight: 600 }}>{action.title}</span>
                      <div className="cell-sub">{action.code}</div>
                    </td>
                    <td style={{ maxWidth: 220 }}>
                      {action.decision ? (
                        <Link to={`/decisions/${action.decision.id}`} className="link-quiet">
                          {action.decision.label}
                        </Link>
                      ) : (
                        <span className="definition">Standalone</span>
                      )}
                    </td>
                    <td className="text-secondary-clh">{action.owner?.label ?? 'Unassigned'}</td>
                    <td>
                      <Pill tone={PRIORITY_TONE[action.priority]}>{titleCase(action.priority)}</Pill>
                    </td>
                    <td style={{ color: action.is_overdue ? 'var(--clh-danger)' : undefined }}>
                      {formatDate(action.due_date)}
                      <div className="cell-sub">
                        {action.is_overdue
                          ? `overdue · ${relativeTime(action.due_date)}`
                          : action.days_until_due !== null
                            ? `${action.days_until_due} day(s) left`
                            : 'no date'}
                      </div>
                    </td>
                    <td>
                      <select
                        className="form-select"
                        style={{ width: 140, fontSize: 12, padding: '3px 8px' }}
                        value={action.status}
                        onChange={(event) =>
                          updateStatus.mutate({ id: action.id, status: event.target.value as ActionStatus })
                        }
                        aria-label={`Status for ${action.title}`}
                      >
                        {STATUSES.map((status) => (
                          <option key={status} value={status}>
                            {titleCase(status)}
                          </option>
                        ))}
                      </select>
                      <div className="mt-1">
                        <Pill tone={ACTION_TONE[action.status]}>{titleCase(action.status)}</Pill>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <Modal show={createOpen} onHide={() => setCreateOpen(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>New action</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="stack stack-3">
            <div>
              <label className="form-label" htmlFor="actionspage-field-1">
                Action<span className="required-mark">*</span>
              </label>
              <input id="actionspage-field-1"
                className="form-control"
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="actionspage-field-2">Description</label>
              <textarea id="actionspage-field-2"
                className="form-control"
                rows={2}
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
              />
            </div>
            <div className="section-grid grid-2" style={{ gap: 10 }}>
              <div>
                <label className="form-label" htmlFor="actionspage-field-3">Owner</label>
                <select id="actionspage-field-3"
                  className="form-select"
                  value={form.owner_id}
                  onChange={(event) => setForm({ ...form, owner_id: event.target.value })}
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
                <label className="form-label" htmlFor="actionspage-field-4">Due date</label>
                <input id="actionspage-field-4"
                  type="date"
                  className="form-control"
                  value={form.due_date}
                  onChange={(event) => setForm({ ...form, due_date: event.target.value })}
                />
              </div>
              <div>
                <label className="form-label" htmlFor="actionspage-field-5">Priority</label>
                <select id="actionspage-field-5"
                  className="form-select"
                  value={form.priority}
                  onChange={(event) => setForm({ ...form, priority: event.target.value as Priority })}
                >
                  {['low', 'medium', 'high', 'critical'].map((priority) => (
                    <option key={priority} value={priority}>
                      {titleCase(priority)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <Notice tone="neutral">
              Standalone actions are allowed for coordination work, but they will not appear as evidence of research
              impact anywhere in analytics.
            </Notice>
            {formError && <Notice tone="danger">{formError}</Notice>}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setCreateOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={form.title.trim().length < 3 || createAction.isPending}
            onClick={() => {
              setFormError(null)
              createAction.mutate()
            }}
          >
            {createAction.isPending ? 'Saving…' : 'Create action'}
          </button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
