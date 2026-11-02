import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, BadgeCheck } from 'lucide-react'
import type { Evidence } from '../types'
import { Pill } from './ui'
import {
  CONFIDENCE_TONE,
  EVIDENCE_TONE,
  EVIDENCE_TYPE_LABELS,
  SEGMENT_LABELS,
  formatDate,
  titleCase,
} from '../utils/format'

export function EvidenceCard({
  evidence,
  showContext = true,
  actions,
}: {
  evidence: Evidence
  showContext?: boolean
  actions?: ReactNode
}) {
  const isQuote = evidence.evidence_type === 'verbatim_quote' || evidence.evidence_type === 'contradictory_evidence'
  const isInterpretation = evidence.evidence_type === 'researcher_interpretation'

  return (
    <article className={`evidence-card type-${evidence.evidence_type}`}>
      <div className="row-between">
        <div className="inline" style={{ gap: 6 }}>
          <Pill tone={EVIDENCE_TONE[evidence.evidence_type]}>{EVIDENCE_TYPE_LABELS[evidence.evidence_type]}</Pill>
          <span className="mono" style={{ fontSize: 11, color: 'var(--clh-text-tertiary)' }}>
            {evidence.code}
          </span>
        </div>
        <div className="inline" style={{ gap: 5 }}>
          <Pill tone={CONFIDENCE_TONE[evidence.confidence]}>{titleCase(evidence.confidence)} confidence</Pill>
          {evidence.review_status === 'flagged' && <Pill tone="red">Flagged</Pill>}
          {evidence.review_status === 'reviewed' && <Pill tone="outline">Reviewed</Pill>}
        </div>
      </div>

      {isInterpretation ? (
        <div>
          <div className="interpretation-block">
            <span className="label">Researcher interpretation — not a customer quote</span>
            <span style={{ fontSize: 13 }}>{evidence.content}</span>
          </div>
        </div>
      ) : (
        <div className="quote-text">
          {isQuote && <span className="quote-mark">“</span>}
          {evidence.content}
          {isQuote && <span className="quote-mark">”</span>}
        </div>
      )}

      {evidence.interpretation && !isInterpretation && (
        <div className="interpretation-block">
          <span className="label">Researcher interpretation</span>
          <span style={{ fontSize: 12.5 }}>{evidence.interpretation}</span>
        </div>
      )}

      {showContext && evidence.customer_context && (
        <div style={{ fontSize: 12, color: 'var(--clh-text-secondary)' }}>
          <span className="meta-label" style={{ display: 'block' }}>
            Customer context
          </span>
          {evidence.customer_context}
        </div>
      )}

      {evidence.provenance_warning ? (
        <div className="provenance-warning">
          <AlertTriangle size={12} style={{ marginRight: 5 }} />
          {evidence.provenance_warning}
        </div>
      ) : (
        <div className="provenance-block">
          <span className="label">
            <BadgeCheck size={11} style={{ marginRight: 3 }} /> Provenance
          </span>
          {evidence.provenance}
          {evidence.interview && (
            <>
              {' · '}
              <Link to={`/interviews/${evidence.interview.id}`}>{evidence.interview.label}</Link>
              {evidence.interview.sublabel ? ` — ${evidence.interview.sublabel}` : ''}
            </>
          )}
        </div>
      )}

      <div className="row-between" style={{ gap: 10 }}>
        <div className="definition">
          {evidence.participant ? (
            <>
              <Link to={`/participants/${evidence.participant.id}`}>{evidence.participant.label}</Link>
              {` · ${SEGMENT_LABELS[evidence.segment]}`}
            </>
          ) : (
            'No participant attribution recorded'
          )}
          {` · captured ${formatDate(evidence.captured_at)}`}
          {evidence.captured_by ? ` by ${evidence.captured_by.label}` : ''}
        </div>
        {actions}
      </div>

      {evidence.insight_links.length > 0 && (
        <div className="tag-row">
          {evidence.insight_links.map((link) => (
            <Link key={link.insight_id} to={`/insights/${link.insight_id}`} className="pill pill-outline">
              Used in {link.insight_code} · {link.role}
            </Link>
          ))}
        </div>
      )}
    </article>
  )
}
