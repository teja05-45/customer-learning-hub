import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileSearch, Search, X } from 'lucide-react'
import { api, errorMessage, toQuery } from '../services/api'
import type { SearchResponse, SearchResult } from '../types'

const ENTITY_ICON_COLOUR: Record<string, string> = {
  project: 'var(--clh-primary)',
  participant: 'var(--clh-info)',
  interview: 'var(--clh-purple)',
  evidence: 'var(--clh-warning)',
  insight: '#0891b2',
  decision: 'var(--clh-success)',
  action: 'var(--clh-text-secondary)',
}

export function GlobalSearch({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [term, setTerm] = useState('')
  const [debounced, setDebounced] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const restoreFocusRef = useRef<HTMLElement | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (open) {
      // Remember what had focus so it can be handed back when the dialog closes.
      restoreFocusRef.current = document.activeElement as HTMLElement | null
      setTerm('')
      setDebounced('')
      window.setTimeout(() => inputRef.current?.focus(), 40)
      return () => {
        const previous = restoreFocusRef.current
        if (previous) window.setTimeout(() => previous.focus(), 0)
      }
    }
  }, [open])

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(term.trim()), 220)
    return () => window.clearTimeout(timer)
  }, [term])

  useEffect(() => {
    if (!open) return
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
      if (event.key !== 'Tab' || !dialogRef.current) return
      // Keep Tab inside the dialog: a modal that leaks focus to the page behind it is
      // worse than no modal for keyboard and screen-reader users.
      const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
        'input, button, [href], select, textarea, [tabindex]:not([tabindex="-1"])',
      )
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  const { data, isFetching, error } = useQuery({
    queryKey: ['search', debounced],
    queryFn: () => api.get<SearchResponse>(`/search${toQuery({ q: debounced })}`),
    enabled: open && debounced.length >= 2,
    staleTime: 10_000,
  })

  const flat: SearchResult[] = useMemo(
    () => (data?.groups ?? []).flatMap((group) => group.items),
    [data],
  )

  if (!open) return null

  const go = (result: SearchResult) => {
    onClose()
    navigate(result.href)
  }

  return (
    <div
      className="overlay-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Search the research record"
      ref={dialogRef}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className="command-palette">
        <div className="command-input">
          <Search size={16} color="var(--clh-text-tertiary)" />
          <input
            ref={inputRef}
            value={term}
            onChange={(event) => setTerm(event.target.value)}
            placeholder="Search projects, participants, evidence, insights, decisions…"
            aria-label="Search"
            onKeyDown={(event) => {
              if (event.key === 'Enter' && flat[0]) go(flat[0])
            }}
          />
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close search">
            <X size={14} />
          </button>
        </div>

        <div className="command-results">
          {debounced.length < 2 && (
            <div style={{ padding: '18px 14px' }}>
              <div className="definition">
                Type at least two characters. Search covers research projects, synthetic participants, interviews,
                evidence, insights, decisions and actions.
              </div>
              <div className="definition mt-2">
                Participant contact details are never stored, so they can never appear here.
              </div>
            </div>
          )}

          {debounced.length >= 2 && isFetching && !data && (
            <div style={{ padding: 14 }} className="stack stack-2">
              <div className="skeleton" style={{ width: '70%' }} />
              <div className="skeleton" style={{ width: '55%' }} />
              <div className="skeleton" style={{ width: '62%' }} />
            </div>
          )}

          {error && (
            <div style={{ padding: 14 }}>
              <div className="notice notice-danger">
                <span className="notice-icon">!</span>
                <div>{errorMessage(error)}</div>
              </div>
            </div>
          )}

          {debounced.length >= 2 && data && data.total === 0 && !isFetching && (
            <div style={{ padding: '18px 14px' }}>
              <div className="d-flex align-items-center gap-2" style={{ fontWeight: 600 }}>
                <FileSearch size={15} /> No matches for “{data.query}”
              </div>
              <div className="definition mt-1">
                Try a customer segment, a product, a research question or an insight title. Related work in the
                library is suggested below when keywords overlap.
              </div>
              {data.suggestions.length > 0 && (
                <>
                  <div className="command-group-label">Related work already in the library</div>
                  {data.suggestions.map((suggestion) => (
                    <button
                      key={suggestion.id}
                      type="button"
                      className="command-result"
                      onClick={() => go(suggestion)}
                    >
                      <div className="command-result-title">{suggestion.title}</div>
                      <div className="command-result-sub">{suggestion.snippet}</div>
                    </button>
                  ))}
                </>
              )}
            </div>
          )}

          {data?.groups.map((group) => (
            <div key={group.entity_type}>
              <div className="command-group-label">{group.label}</div>
              {group.items.map((result) => (
                <button key={`${result.entity_type}-${result.id}`} type="button" className="command-result" onClick={() => go(result)}>
                  <div className="d-flex align-items-center gap-2">
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: 99,
                        background: ENTITY_ICON_COLOUR[result.entity_type] ?? '#94a3b8',
                        flex: 'none',
                      }}
                    />
                    <div className="command-result-title">{result.title}</div>
                  </div>
                  <div className="command-result-sub">{result.subtitle}</div>
                  {result.snippet && <div className="command-result-sub mt-1">{result.snippet}</div>}
                </button>
              ))}
            </div>
          ))}

          {data && data.total > 0 && data.suggestions.length > 0 && (
            <div>
              <div className="command-group-label">Related research</div>
              {data.suggestions.map((suggestion) => (
                <button key={`s-${suggestion.id}`} type="button" className="command-result" onClick={() => go(suggestion)}>
                  <div className="command-result-title">{suggestion.title}</div>
                  <div className="command-result-sub">{suggestion.snippet}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div
          style={{
            borderTop: '1px solid var(--clh-border)',
            padding: '8px 12px',
            display: 'flex',
            justifyContent: 'space-between',
            gap: 12,
          }}
        >
          <span className="definition">Enter opens the first result · Esc closes</span>
          {data && <span className="definition">{data.total} result(s)</span>}
        </div>
      </div>
    </div>
  )
}
