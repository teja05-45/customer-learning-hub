import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ExternalLink, Trash2 } from 'lucide-react'
import { api } from '../services/api'
import { useToast } from '../app/ToastProvider'
import type { Evidence } from '../types'
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
import { SEGMENT_LABELS, formatDateTime, titleCase } from '../utils/format'

export function EvidenceDetailPage() {
  const { evidenceId = '' } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['evidence-item', evidenceId],
    queryFn: () => api.get<Evidence>(`/evidence/${evidenceId}`),
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
          <button type="button" className="btn btn-danger-soft" onClick={() => setDeleteOpen(true)}>
            <Trash2 size={13} /> Delete evidence
          </button>
        }
      />

      <div className="section-grid grid-sidebar">
        <div className="stack stack-3">
          <EvidenceCard evidence={data} />

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
              {data.insight_links.length > 0 ? (
                <div>
                  <div className="meta-label mb-1">Used in</div>
                  <div className="tag-row">
                    {data.insight_links.map((link) => (
                      <Link key={link.insight_id} to={`/insights/${link.insight_id}`} className="pill pill-outline">
                        {link.insight_code} · {titleCase(link.role)} — {link.insight_title}
                      </Link>
                    ))}
                  </div>
                </div>
              ) : (
                <Notice tone="warning">
                  This evidence is not linked to any insight yet. That is fine while you are still collecting, but an
                  unlinked quote will not reach a decision on its own.
                </Notice>
              )}
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
