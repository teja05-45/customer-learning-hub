import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, BadgeCheck } from 'lucide-react'
import type { Evidence } from '../types'
import { Pill } from './ui'
import {
  COLLECTION_METHOD_LABELS,
  CONFIDENCE_TONE,
  DEPTH_LABELS,
  DEPTH_TONE,
  EVIDENCE_TONE,
  EVIDENCE_TYPE_LABELS,
  FEEDBACK_SOURCE_LABELS,
  SEGMENT_LABELS,
  VERIFICATION_LABELS,
  VERIFICATION_TONE,
  formatDate,
  titleCase,
} from '../utils/format'

/** The source of an evidence item, kept separate from the customer's words. */
export function EvidenceSource({ evidence }: { evidence: Evidence }) {
  const sourceLabel = evidence.source_type
    ? evidence.source_type === 'interview'
      ? 'Interview'
      : FEEDBACK_SOURCE_LABELS[evidence.source_type] ?? titleCase(evidence.source_type)
    : 'Source type not recorded'

  return (
    <div className="provenance-block">
      <span className="label">
        <BadgeCheck size={11} style={{ marginRight: 3 }} /> Provenance
      </span>
      <div className="section-grid grid-2" style={{ gap: 6, rowGap: 2 }}>
        <span>
          Source: <strong>{sourceLabel}</strong>
        </span>
        <span>
          Method:{' '}
          {evidence.collection_method
            ? COLLECTION_METHOD_LABELS[evidence.collection_method]
            : 'Not recorded'}
        </span>
        <span>
          Depth:{' '}
          {evidence.research_depth ? (
            <Pill tone={DEPTH_TONE[evidence.research_depth]}>
              {DEPTH_LABELS[evidence.research_depth]}
            </Pill>
          ) : (
            'Not recorded'
          )}
        </span>
        <span>
          Verification:{' '}
          {evidence.verification_state ? (
            <Pill tone={VERIFICATION_TONE[evidence.verification_state]}>
              {VERIFICATION_LABELS[evidence.verification_state]}
            </Pill>
          ) : (
            'Not recorded'
          )}
        </span>
        <span>Collected: {formatDate(evidence.collected_at)}</span>
        <span>
          Reference:{' '}
          {evidence.source_reference || evidence.provenance || 'No source reference recorded'}
        </span>
      </div>
      <div className="mt-1">
        {evidence.interview && (
          <>
            Interview:{' '}
            <Link to={`/interviews/${evidence.interview.id}`}>
              {evidence.interview.label}
            </Link>
            {evidence.interview.sublabel ? ` — ${evidence.interview.sublabel}` : ''}
          </>
        )}
        {!evidence.interview && evidence.feedback_record && (
          <>Feedback source: <Link to="/feedback">{evidence.feedback_record.label}</Link></>
        )}
      </div>
    </div>
  )
}

export function EvidenceCard({
  evidence,
  showContext = true,
  actions,
  footer,
}: {
  evidence: Evidence
  showContext?: boolean
  actions?: ReactNode
  footer?: ReactNode
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
          <span className="label">Researcher interpretation — separate from the quote</span>
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
        <EvidenceSource evidence={evidence} />
      )}

      <div className="row-between" style={{ gap: 10 }}>
        <div className="definition">
          {evidence.participant ? (
            <>
              <Link to={`/participants/${evidence.participant.id}`}>{evidence.participant.label}</Link>
              {` · ${SEGMENT_LABELS[evidence.segment]}`}
            </>
          ) : (
            'Unattributed'
          )}
          {` · captured ${formatDate(evidence.captured_at)}`}
          {evidence.captured_by ? ` by ${evidence.captured_by.label}` : ''}
        </div>
        {actions}
      </div>

      {footer}

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
