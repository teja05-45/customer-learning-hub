import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, FolderKanban, Plus, Search } from 'lucide-react'
import { api, toQuery } from '../services/api'
import { useSession } from '../app/SessionProvider'
import type { ProjectListResponse, ProjectStatus } from '../types'
import {
  EmptyState,
  ErrorState,
  PageHeader,
  Pill,
  SectionCard,
  TableSkeleton,
} from '../components/ui'
import { PROJECT_STATUS_TONE, PRIORITY_TONE, SEGMENT_LABELS, formatDate, titleCase } from '../utils/format'

const STATUS_FILTERS: { value: ProjectStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'planning', label: 'Planning' },
  { value: 'recruiting', label: 'Recruiting' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'analysis', label: 'Analysis' },
  { value: 'completed', label: 'Completed' },
  { value: 'archived', label: 'Archived' },
]

export function ProjectsPage() {
  const { user } = useSession()
  // Only researchers and administrators may create a project; the API enforces
  // this too, but hiding the action avoids offering a guaranteed failure.
  const canCreate = user?.role === 'researcher' || user?.role === 'admin'
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | 'all'>('all')

  const params = useMemo(
    () => ({
      q: search || undefined,
      status: statusFilter === 'all' ? undefined : statusFilter,
    }),
    [search, statusFilter],
  )

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['projects', params],
    queryFn: () => api.get<ProjectListResponse>(`/projects${toQuery(params)}`),
  })

  return (
    <div className="page">
      <PageHeader
        title="Research projects"
        description="Each project starts from a written question, not a task to book interviews. Status shows where the work actually is."
        actions={
          canCreate ? (
            <Link to="/projects/new" className="btn btn-primary">
              <Plus size={14} /> New project
            </Link>
          ) : undefined
        }
      />

      <SectionCard padded={false}>
        <div className="filter-bar">
          <div className="filter-input">
            <Search size={14} className="search-icon" />
            <input
              className="form-control"
              placeholder="Search project name or objective"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search projects"
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
          </div>
          <div style={{ marginLeft: 'auto' }} className="definition">
            {isFetching ? 'Refreshing…' : `${data?.total ?? 0} project(s)`}
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
            icon={<FolderKanban size={18} />}
            title={search || statusFilter !== 'all' ? 'No projects match those filters' : 'No research projects yet'}
            description={
              search || statusFilter !== 'all'
                ? 'Clear the filters, or start a new project if this question is genuinely new.'
                : 'Start from a template so the team agrees on the question, the segments and the decision this research should inform.'
            }
            action={
              search || statusFilter !== 'all' ? (
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={() => {
                    setSearch('')
                    setStatusFilter('all')
                  }}
                >
                  Clear filters
                </button>
              ) : canCreate ? (
                <Link to="/projects/new" className="btn btn-primary btn-sm">
                  <Plus size={13} /> Create the first project
                </Link>
              ) : undefined
            }
          />
        )}

        {data && data.items.length > 0 && (
          <div className="table-wrap">
            <table className="clh-table">
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Owner</th>
                  <th>Participants</th>
                  <th>Evidence</th>
                  <th>Deadline</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((project) => (
                  <tr key={project.id}>
                    <td style={{ maxWidth: 380 }}>
                      <Link to={`/projects/${project.id}`} className="table-link">
                        {project.name}
                      </Link>
                      <div className="cell-sub">
                        {project.methodology || 'Method not set'} ·{' '}
                        {project.target_segments.map((segment) => SEGMENT_LABELS[segment]).join(', ') || 'No segments set'}
                      </div>
                      {project.segment_gap && (
                        <div className="inline mt-1" style={{ color: 'var(--clh-warning-ink)', fontSize: 11.5 }}>
                          <AlertTriangle size={12} /> Target segment has no participants yet
                        </div>
                      )}
                    </td>
                    <td>
                      <Pill tone={PROJECT_STATUS_TONE[project.status]}>{titleCase(project.status)}</Pill>
                      {project.unresolved_questions > 0 && (
                        <div className="cell-sub">{project.unresolved_questions} open question(s)</div>
                      )}
                    </td>
                    <td>
                      <Pill tone={PRIORITY_TONE[project.priority]}>{titleCase(project.priority)}</Pill>
                    </td>
                    <td className="text-secondary-clh">{project.owner?.label ?? 'Unassigned'}</td>
                    <td>
                      <span className="mono">{project.counts.participants}</span>
                      <div className="cell-sub">{project.counts.interviews_completed} completed</div>
                    </td>
                    <td>
                      <span className="mono">{project.counts.evidence}</span>
                      <div className="cell-sub">{project.counts.insights} insight(s)</div>
                    </td>
                    <td>{formatDate(project.deadline)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <div className="definition mt-3">
        Archived projects stay in the library so evidence can be reused. Nothing is deleted when a project closes.
      </div>
    </div>
  )
}
