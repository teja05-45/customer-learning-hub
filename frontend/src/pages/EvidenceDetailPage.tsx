import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ExternalLink, Pencil, Trash2 } from 'lucide-react'
import { Modal } from 'react-bootstrap'
import { api } from '../services/api'
import { useToast } from '../app/ToastProvider'
import type { Evidence, EvidenceInsightsResponse } from '../types'
import {
  ErrorState,
  LoadingBlock,
  MetaItem,
  Notice,
  PageHeader,
  Pill,
  SectionCard,
} from '../components/ui'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { EvidenceCard } from '../components/EvidenceCard'
import {
  CLASSIFICATION_LABELS,
  CLASSIFICATION_TONE,
  CONFIDENCE_TONE,
  SEGMENT_LABELS,
  formatDateTime,
  titleCase,
} from '../utils/format'

export function EvidenceDetailPage() {
  const { evidenceId = '' } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [provenanceOpen, setProvenanceOpen] = useState(false)
  const [provenanceDraft, setProvenanceDraft] = useState('')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['evidence-item', evidenceId],
    queryFn: () => api.get<Evidence>(`/evidence/${evidenceId}`),
    enabled: Boolean(evidenceId),
  })

  const insightLinks = useQuery({
    queryKey: ['evidence-insights', evidenceId],
    queryFn: () => api.get<EvidenceInsightsResponse>(`/evidence/${evidenceId}/insights`),
    enabled: Boolean(evidenceId),
  })

  const remove = useMutation({
    mutationFn: () => api.delete(`/evidence/${evidenceId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['evidence'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.push({ title: 'Evidence deleted', variant: 'success' })
      navigate('/evidence')
    },
    onError: (error) => toast.push({ title: 'Could not delete', message: (error as Error).message, variant: 'error' }),
  })

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['evidence-item', evidenceId] })
    void queryClient.invalidateQueries({ queryKey: ['evidence'] })
    void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  const setReview = useMutation({
    mutationFn: (review_status: 'unreviewed' | 'reviewed' | 'flagged') =>
      api.patch<Evidence>(`/evidence/${evidenceId}`, { review_status }),
    onSuccess: (_body, review_status) => {
      refresh()
      toast.push({ title: `Review status set to ${titleCase(review_status)}`, variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not update review', message: (error as Error).message, variant: 'error' }),
  })

  const saveProvenance = useMutation({
    mutationFn: () => api.patch<Evidence>(`/evidence/${evidenceId}`, { provenance: provenanceDraft.trim() }),
    onSuccess: () => {
      refresh()
      setProvenanceOpen(false)
      toast.push({
        title: 'Provenance saved',
        message: provenanceDraft.trim()
          ? 'The source is recorded, so this can now be checked.'
          : 'The record is unverified again and flagged for review.',
        variant: 'success',
      })
    },
    onError: (error) => toast.push({ title: 'Could not save provenance', message: (error as Error).message, variant: 'error' }),
  })

  if (isLoading) {
    return (
      <div className="page">
        <SectionCard>
          <LoadingBlock rows={6} />
        </SectionCard>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="page">
        <PageHeader title="Evidence not found" />
        <ErrorState message={(error as Error)?.message ?? 'That evidence record does not exist.'} onRetry={() => refetch()} />
      </div>
    )
  }

  return (
    <div className="page" style={{ maxWidth: 1000 }}>
      <Link to="/evidence" className="link-quiet inline mb-3">
        <ArrowLeft size={13} /> Back to evidence
      </Link>

      <PageHeader
        title={`Evidence ${data.code}`}
        description="One captured item, with its source context. If the provenance is missing, the record cannot be presented as verified."
        meta={
          <div className="d-flex flex-wrap gap-2">
            <Pill tone={data.is_verified_source ? 'green' : 'red'}>
              {data.is_verified_source ? 'Source verified' : 'Unverified source'}
            </Pill>
            <Pill tone="outline">{SEGMENT_LABELS[data.segment]}</Pill>
            {data.review_status === 'flagged' && <Pill tone="amber">Flagged for review</Pill>}
          </div>
        }
        actions={
          <>
            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={() => {
                setProvenanceDraft(data.provenance)
                setProvenanceOpen(true)
              }}
            >
              <Pencil size={13} /> Correct provenance
            </button>
            <button type="button" className="btn btn-danger-soft" onClick={() => setDeleteOpen(true)}>
              <Trash2 size={13} /> Delete evidence
            </button>
          </>
        }
      />

      <div className="section-grid grid-sidebar">
        <div className="stack stack-3">
          <EvidenceCard evidence={data} />

          <SectionCard
            title="Insights that use this evidence"
            subtitle="One quote can support one finding, contradict another and only add context to a third. The classification belongs to each relationship, not to the quote."
          >
            {insightLinks.isLoading && <LoadingBlock rows={3} label="Loading linked insights…" />}
            {insightLinks.error && (
              <ErrorState
                message={(insightLinks.error as Error).message}
                onRetry={() => insightLinks.refetch()}
              />
            )}
            {insightLinks.data && insightLinks.data.total === 0 && (
              <Notice tone="warning">
                This evidence is not linked to any insight yet. That is fine while you are still collecting, but an
                unlinked quote will not reach a decision on its own.
              </Notice>
            )}
            {insightLinks.data && insightLinks.data.total > 0 && (
              <div className="stack stack-3">
                {(['supporting', 'contradictory', 'contextual'] as const).map((classification) => {
                  const items = insightLinks.data?.[classification] ?? []
                  if (items.length === 0) return null
                  return (
                    <div key={classification}>
                      <div className="inline mb-2" style={{ gap: 6 }}>
                        <Pill tone={CLASSIFICATION_TONE[classification]}>
                          {CLASSIFICATION_LABELS[classification]}
                        </Pill>
                        <span className="definition">{items.length} insight(s)</span>
                      </div>
                      <div className="stack stack-2">
                        {items.map((link) => (
                          <div
                            key={link.relationship_id}
                            className="card-surface"
                            style={{ padding: 11, boxShadow: 'none' }}
                          >
                            <div className="row-between" style={{ alignItems: 'flex-start' }}>
                              <Link to={`/insights/${link.insight.id}`} className="table-link">
                                {link.insight.title}
                              </Link>
                              {link.confidence && (
                                <Pill tone={CONFIDENCE_TONE[link.confidence]}>
                                  Researcher confidence: {titleCase(link.confidence)}
                                </Pill>
                              )}
                            </div>
                            <div className="definition mt-1">
                              {link.insight.code} · {link.insight.evidence_count} evidence item(s) ·{' '}
                              {titleCase(link.insight.status)}
                            </div>
                            <div className="mt-2">
                              <span className="meta-label">Why this classification</span>
                              <div style={{ fontSize: 12.5 }}>{link.rationale || 'No rationale recorded.'}</div>
                            </div>
                            <div className="definition mt-1">
                              Judged by {link.created_by?.label ?? 'an unknown researcher'} ·{' '}
                              {formatDateTime(link.created_at)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </SectionCard>

          <SectionCard title="What this item does and does not support">
            <div className="stack stack-2">
              <div className="definition">
                {data.is_verified_source
                  ? 'The source and context are recorded, so a reader can go back to the interview and check the quote.'
                  : 'Source context is unavailable. Do not treat this as verified evidence, and do not build a decision on it.'}
              </div>
              <div className="definition">
                Confidence is a judgement about this item, not a statistical statement. A single high-confidence quote
                is still one person's account.
              </div>
              <div className="definition">
                {insightLinks.data
                  ? `Linked to ${insightLinks.data.total} insight(s): ${insightLinks.data.supporting.length} supporting, ${insightLinks.data.contradictory.length} contradictory, ${insightLinks.data.contextual.length} contextual.`
                  : 'Checking which insights use this item…'}
              </div>
              <div className="definition">{insightLinks.data?.statement_note}</div>
            </div>
          </SectionCard>
        </div>

        <div className="stack stack-3">
          <SectionCard title="Source">
            <div className="stack stack-3">
              <MetaItem
                label="Interview"
                value={
                  data.interview ? (
                    <Link to={`/interviews/${data.interview.id}`} className="inline" style={{ gap: 4 }}>
                      {data.interview.label} <ExternalLink size={11} />
                    </Link>
                  ) : (
                    'Not linked'
                  )
                }
              />
              <MetaItem
                label="Project"
                value={data.project ? <Link to={`/projects/${data.project.id}`}>{data.project.label}</Link> : '—'}
              />
              <MetaItem
                label="Participant"
                value={
                  data.participant ? (
                    <Link to={`/participants/${data.participant.id}`}>{data.participant.label}</Link>
                  ) : (
                    'Not recorded'
                  )
                }
              />
              <MetaItem label="Captured" value={formatDateTime(data.captured_at)} />
              <MetaItem label="Captured by" value={data.captured_by?.label ?? 'Unknown'} />
              <MetaItem label="Review status" value={titleCase(data.review_status)} />
            </div>
          </SectionCard>

          <SectionCard title="Review this evidence" subtitle="Reviewing is a team action, not a quality guarantee">
            <div className="stack stack-2">
              <div className="tag-row">
                {(['unreviewed', 'reviewed', 'flagged'] as const).map((status) => (
                  <button
                    key={status}
                    type="button"
                    className={`filter-chip${data.review_status === status ? ' active' : ''}`}
                    disabled={setReview.isPending}
                    onClick={() => setReview.mutate(status)}
                  >
                    {titleCase(status)}
                  </button>
                ))}
              </div>
              <div className="definition">
                Flagging keeps the record in place. A source can be corrected without pretending the original capture was
                complete.
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Provenance statement">
            {data.provenance ? (
              <div className="provenance-block">
                <span className="label">Recorded source</span>
                {data.provenance}
              </div>
            ) : (
              <div className="provenance-warning">
                Source context unavailable — do not treat this as verified evidence.
              </div>
            )}
          </SectionCard>
        </div>
      </div>

      <Modal show={provenanceOpen} onHide={() => setProvenanceOpen(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Correct the provenance</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <label className="form-label" htmlFor="evidence-provenance">
            Where did this come from?
          </label>
          <textarea
            id="evidence-provenance"
            className="form-control"
            rows={3}
            value={provenanceDraft}
            onChange={(event) => setProvenanceDraft(event.target.value)}
            placeholder="e.g. INT-0004 · 00:12:30, follow-up question about fragrance"
          />
          <div className="definition mt-2">
            Leaving this empty marks the record unverified again and flags it for review. Clearing a source never makes
            the claim stronger.
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setProvenanceOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={saveProvenance.isPending}
            onClick={() => saveProvenance.mutate()}
          >
            {saveProvenance.isPending ? 'Saving…' : 'Save provenance'}
          </button>
        </Modal.Footer>
      </Modal>

      <ConfirmDialog
        show={deleteOpen}
        title="Delete this evidence?"
        destructive
        confirmLabel="Delete evidence"
        busy={remove.isPending}
        onCancel={() => setDeleteOpen(false)}
        onConfirm={() => remove.mutate()}
      >
        <p style={{ marginBottom: 8 }}>
          The record is removed permanently. Any insight that used it will lose that support, and its evidence count
          will drop — which is visible to whoever reads it next.
        </p>
        <div className="definition">Prefer keeping contradictory evidence in place. Deleting it makes a finding look stronger than it is.</div>
      </ConfirmDialog>
    </div>
  )
}
