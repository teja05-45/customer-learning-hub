import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Quote, Search } from 'lucide-react'
import { api, toQuery } from '../services/api'
import type { EvidenceListResponse, EvidenceType, ProjectListResponse } from '../types'
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
  Notice,
  PageHeader,
  SectionCard,
} from '../components/ui'
import { EvidenceCard } from '../components/EvidenceCard'
import { EVIDENCE_TYPE_LABELS, titleCase } from '../utils/format'

const TYPES: EvidenceType[] = [
  'verbatim_quote',
  'observation',
  'researcher_interpretation',
  'contradictory_evidence',
  'open_question',
]

export function EvidencePage() {
  const [searchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [types, setTypes] = useState<EvidenceType[]>([])
  const [unverifiedOnly, setUnverifiedOnly] = useState(false)
  const [projectId, setProjectId] = useState(searchParams.get('project') ?? '')

  const params = useMemo(
    () => ({
      q: search || undefined,
      evidence_type: types.length ? types : undefined,
      unverified_only: unverifiedOnly || undefined,
      project_id: projectId || undefined,
    }),
    [search, types, unverifiedOnly, projectId],
  )

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['evidence', params],
    queryFn: () => api.get<EvidenceListResponse>(`/evidence${toQuery(params)}`),
  })

  const projects = useQuery({
    queryKey: ['projects', 'evidence-filter'],
    queryFn: () => api.get<ProjectListResponse>(`/projects${toQuery({ page_size: 50 })}`),
    staleTime: 60_000,
  })

  const toggleType = (type: EvidenceType) => {
    setTypes((current) => (current.includes(type) ? current.filter((entry) => entry !== type) : [...current, type]))
  }

  return (
    <div className="page">
      <PageHeader
        title="Evidence library"
        description="Every captured quote, observation and open question, with the interview it came from. This is the raw material behind every insight."
      />

      <div className="section-grid grid-4 mb-3">
        <div className="stat-card">
          <div className="stat-label">Evidence in view</div>
          <div className="stat-value">{data?.total ?? 0}</div>
          <div className="stat-meta">across {Object.keys(data?.type_counts ?? {}).length} type(s)</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Verbatim quotes</div>
          <div className="stat-value">{data?.type_counts.verbatim_quote ?? 0}</div>
          <div className="stat-meta">customer words, unedited</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Interpretations</div>
          <div className="stat-value">{data?.type_counts.researcher_interpretation ?? 0}</div>
          <div className="stat-meta">clearly marked as not a quote</div>
        </div>
        <div className={`stat-card${(data?.unverified_count ?? 0) > 0 ? ' is-warning' : ''}`}>
          <div className="stat-label">Missing provenance</div>
          <div className="stat-value">{data?.unverified_count ?? 0}</div>
          <div className="stat-meta">cannot be treated as verified</div>
        </div>
      </div>

      <SectionCard padded={false}>
        <div className="filter-bar">
          <div className="filter-input">
            <Search size={14} className="search-icon" />
            <input
              className="form-control"
              placeholder="Search quotes and interpretations"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search evidence"
            />
          </div>
          <div className="inline" style={{ flexWrap: 'wrap', gap: 6 }}>
            {TYPES.map((type) => (
              <button
                key={type}
                type="button"
                className={`filter-chip${types.includes(type) ? ' active' : ''}`}
                onClick={() => toggleType(type)}
              >
                {EVIDENCE_TYPE_LABELS[type]}
              </button>
            ))}
            <button
              type="button"
              className={`filter-chip${unverifiedOnly ? ' active' : ''}`}
              onClick={() => setUnverifiedOnly((value) => !value)}
            >
              Missing provenance
            </button>
          </div>
          <select
            className="form-select"
            style={{ width: 250 }}
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
            aria-label="Filter by project"
          >
            <option value="">All projects</option>
            {projects.data?.items.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </div>

        <div className="card-section">
          {isLoading && <LoadingBlock rows={6} label="Loading evidence…" />}
          {error && <ErrorState message={(error as Error).message} onRetry={() => refetch()} />}
          {data && data.items.length === 0 && (
            <EmptyState
              icon={<Quote size={18} />}
              title="No evidence matches this view"
              description="Evidence is captured inside an interview so it always keeps its source. Open an interview to add the first item."
              action={
                <Link to="/interviews" className="btn btn-primary btn-sm">
                  Go to interviews
                </Link>
              }
            />
          )}

          {data && data.items.length > 0 && (
            <div className="stack stack-3">
              {data.items.map((item) => (
                <EvidenceCard
                  key={item.id}
                  evidence={item}
                  actions={
                    <Link to={`/evidence/${item.id}`} className="link-quiet">
                      Open detail
                    </Link>
                  }
                />
              ))}
            </div>
          )}
        </div>
      </SectionCard>

      <div className="mt-3">
        <Notice tone="neutral" icon={<AlertTriangle size={15} />}>
          Sorted newest first. {data ? `${titleCase('verbatim_quote')}s are shown with quotation marks; interpretations are tinted and labelled, so the two can never be confused.` : ''}
        </Notice>
      </div>
    </div>
  )
}
