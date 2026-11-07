import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CalendarClock, CircleDot, Columns3, ListTree } from 'lucide-react'
import { api } from '../services/api'
import type { ProjectJourney } from '../types'
import { EmptyState, ErrorState, LoadingBlock, Notice, Pill } from './ui'
import { formatDate, titleCase } from '../utils/format'

const STAGE_TONE: Record<string, 'green' | 'amber' | 'blue' | 'outline'> = {
  complete: 'green',
  in_progress: 'blue',
  waiting: 'amber',
  not_started: 'outline',
}

const STATUS_TONE: Record<string, 'green' | 'amber' | 'blue' | 'red' | 'outline' | 'purple'> = {
  complete: 'green',
  completed: 'green',
  reviewed: 'green',
  verified: 'green',
  achieved: 'green',
  accepted: 'green',
  validated_internal: 'green',
  in_progress: 'blue',
  scheduled: 'blue',
  supporting: 'blue',
  measurement_pending: 'amber',
  planned: 'outline',
  waiting: 'amber',
  open: 'amber',
  proposed: 'amber',
  under_review: 'amber',
  blocked: 'red',
  not_achieved: 'red',
  withdrawn: 'red',
  cancelled: 'red',
  declined: 'red',
  overdue: 'red',
  inconclusive: 'purple',
}

function tone(status: string) {
  return STATUS_TONE[status] ?? 'outline'
}

export function JourneyBoard({ projectId }: { projectId: string }) {
  const [view, setView] = useState<'board' | 'timeline'>('board')
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['journey', projectId],
    queryFn: () => api.get<ProjectJourney>(`/projects/${projectId}/journey`),
    enabled: Boolean(projectId),
  })

  if (isLoading) return <LoadingBlock rows={6} />
  if (error || !data) {
    return <ErrorState message={(error as Error)?.message ?? 'The journey could not be loaded.'} onRetry={() => refetch()} />
  }

  const completed = data.stages.filter((stage) => stage.status === 'complete').length

  return (
    <div className="stack stack-3">
      <div className="row-between" style={{ flexWrap: 'wrap' }}>
        <div>
          <div className="card-title">
            <Columns3 size={14} /> Learning journey
          </div>
          <div className="card-subtitle">
            {completed} of {data.stages.length} stages complete · every card is derived from a real record
          </div>
        </div>
        <div className="d-flex gap-2" role="group" aria-label="Journey view">
          <button
            type="button"
            className={`filter-chip${view === 'board' ? ' active' : ''}`}
            onClick={() => setView('board')}
            aria-pressed={view === 'board'}
          >
            <Columns3 size={12} /> Board
          </button>
          <button
            type="button"
            className={`filter-chip${view === 'timeline' ? ' active' : ''}`}
            onClick={() => setView('timeline')}
            aria-pressed={view === 'timeline'}
          >
            <ListTree size={12} /> Timeline
          </button>
        </div>
      </div>

      {data.warnings.length > 0 && (
        <Notice tone="warning" title="Gaps in the loop">
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {data.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </Notice>
      )}

      {view === 'board' && (
        <>
        <p className="definition" style={{ marginBottom: 8 }}>
          Nine stages. Scroll the board sideways to see them all; each card opens the record it describes.
        </p>
        <div className="journey-board" role="list" aria-label="Learning journey stages">
          {data.stages.map((stage) => (
            <section className="journey-column" key={stage.key} role="listitem" aria-label={stage.label}>
              <header className="journey-column-header">
                <div className="row-between" style={{ gap: 6 }}>
                  <span className="journey-stage-label">{stage.label}</span>
                  <Pill tone={STAGE_TONE[stage.status] ?? 'outline'}>{titleCase(stage.status)}</Pill>
                </div>
                <div className="definition">{stage.description}</div>
              </header>
              <div className="journey-column-body">
                {stage.items.length === 0 ? (
                  <div className="journey-empty">
                    <CircleDot size={13} /> Nothing recorded yet
                  </div>
                ) : (
                  stage.items.map((card) => (
                    <Link
                      key={card.id}
                      to={card.href}
                      className={`journey-card${card.overdue ? ' is-overdue' : ''}`}
                    >
                      <div className="row-between" style={{ gap: 6 }}>
                        <span className="journey-code">{card.code}</span>
                        <Pill tone={card.overdue ? 'red' : tone(card.status)}>
                          {card.overdue ? 'Overdue' : titleCase(card.status)}
                        </Pill>
                      </div>
                      <div className="journey-card-title">{card.title}</div>
                      {card.subtitle && <div className="journey-card-sub">{card.subtitle}</div>}
                      {card.at && (
                        <div className="journey-card-date">
                          <CalendarClock size={11} /> {formatDate(card.at)}
                        </div>
                      )}
                    </Link>
                  ))
                )}
                {stage.count > stage.items.length && (
                  <div className="definition">+{stage.count - stage.items.length} more in the full list</div>
                )}
              </div>
            </section>
          ))}
        </div>
        </>
      )}

      {view === 'timeline' && (
        <div>
          {data.timeline.length === 0 ? (
            <EmptyState
              title="No dated activity yet"
              description="Scheduling a session, capturing evidence or recording a decision will place a real date on this timeline."
            />
          ) : (
            <ol className="journey-timeline">
              {data.timeline.map((item, index) => (
                <li
                  key={`${item.at}-${item.kind}-${index}`}
                  className={`journey-timeline-item state-${item.state}`}
                >
                  <span className="journey-timeline-dot" aria-hidden="true" />
                  <div className="journey-timeline-body">
                    <div className="row-between" style={{ gap: 8, flexWrap: 'wrap' }}>
                      <span className="journey-timeline-title">
                        {item.href ? <Link to={item.href}>{item.title}</Link> : item.title}
                      </span>
                      <span className={`pill pill-${tone(item.state)}`}>{titleCase(item.state)}</span>
                    </div>
                    <div className="definition">
                      {formatDate(item.at)} · {titleCase(item.kind)}
                      {item.detail ? ` · ${item.detail}` : ''}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      <div className="honesty-note">
        Status changes are made on the record's own page, so the same validation and role rules apply. This view
        never edits a record directly.
      </div>
    </div>
  )
}
