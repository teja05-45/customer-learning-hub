import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from 'react-bootstrap'
import { ArrowLeft, Lock, Mic, MicOff, Plus, Save, ShieldCheck } from 'lucide-react'
import { api } from '../services/api'
import { useToast } from '../app/ToastProvider'
import type {
  Confidence,
  ConsentStatus,
  ConsentType,
  Evidence,
  EvidenceType,
  InterviewDetail,
  InterviewStatus,
} from '../types'
import {
  EmptyState,
  ErrorState,
  HonestyNote,
  LoadingBlock,
  MetaItem,
  Notice,
  PageHeader,
  Pill,
  SectionCard,
} from '../components/ui'
import { EvidenceCard } from '../components/EvidenceCard'
import {
  EVIDENCE_TYPE_LABELS,
  INTERVIEW_TONE,
  INTERVIEW_TRANSITIONS,
  SEGMENT_LABELS,
  formatDateTime,
  relativeTime,
  titleCase,
} from '../utils/format'

const EVIDENCE_TYPES: EvidenceType[] = [
  'verbatim_quote',
  'observation',
  'researcher_interpretation',
  'contradictory_evidence',
  'open_question',
]

const CONSENT_TYPES: { value: ConsentType; label: string; description: string }[] = [
  { value: 'participation', label: 'Participation', description: 'Agreed to take part in the conversation.' },
  { value: 'recording', label: 'Recording', description: 'Agreed to audio being captured (no audio is captured here).' },
  { value: 'quoting', label: 'Quoting', description: 'Agreed that anonymised words may be quoted internally.' },
  { value: 'sharing_internal', label: 'Internal sharing', description: 'Agreed that the material can be shared inside the company.' },
]

export function InterviewDetailPage() {
  const { interviewId = '' } = useParams()
  const toast = useToast()
  const queryClient = useQueryClient()

  const [notes, setNotes] = useState('')
  const [notesDirty, setNotesDirty] = useState(false)
  const [consentOpen, setConsentOpen] = useState(false)
  const [captureOpen, setCaptureOpen] = useState(false)
  const [followUp, setFollowUp] = useState('')
  const [consentForm, setConsentForm] = useState<{ type: ConsentType; status: ConsentStatus; note: string }>({
    type: 'participation',
    status: 'granted',
    note: 'Simulated verbal consent recorded at the start of the conversation.',
  })
  const [evidenceForm, setEvidenceForm] = useState({
    evidence_type: 'verbatim_quote' as EvidenceType,
    content: '',
    interpretation: '',
    customer_context: '',
    provenance: '',
    confidence: 'medium' as Confidence,
  })
  const [formError, setFormError] = useState<string | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['interview', interviewId],
    queryFn: () => api.get<InterviewDetail>(`/interviews/${interviewId}`),
    enabled: Boolean(interviewId),
  })

  useEffect(() => {
    if (data && !notesDirty) {
      setNotes(data.notes)
      setEvidenceForm((current) => ({
        ...current,
        provenance: current.provenance || `Interview ${data.code} · note 1 · synthetic transcript`,
        customer_context: current.customer_context || `${data.participant?.display_name ?? 'Participant'} — ${data.title}`,
      }))
    }
  }, [data, notesDirty])

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['interview', interviewId] })
    void queryClient.invalidateQueries({ queryKey: ['interviews'] })
    void queryClient.invalidateQueries({ queryKey: ['evidence'] })
    void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  const changeStatus = useMutation({
    mutationFn: (status: InterviewStatus) =>
      api.patch(`/interviews/${interviewId}`, {
        status,
        change_note: `Status changed to ${status.replace('_', ' ')} from the interview workspace.`,
      }),
    onSuccess: () => {
      invalidate()
      toast.push({ title: 'Interview status updated', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Status change rejected', message: (error as Error).message, variant: 'error' }),
  })

  const saveNotes = useMutation({
    mutationFn: () => api.patch(`/interviews/${interviewId}`, { notes }),
    onSuccess: () => {
      setNotesDirty(false)
      invalidate()
      toast.push({ title: 'Notes saved', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not save notes', message: (error as Error).message, variant: 'error' }),
  })

  const recordConsent = useMutation({
    mutationFn: () =>
      api.post(`/interviews/${interviewId}/consent`, {
        consent_type: consentForm.type,
        status: consentForm.status,
        note: consentForm.note,
      }),
    onSuccess: () => {
      setConsentOpen(false)
      invalidate()
      toast.push({ title: 'Consent recorded', message: 'The decision is stored with a timestamp.', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not record consent', message: (error as Error).message, variant: 'error' }),
  })

  const toggleRecording = useMutation({
    mutationFn: (enabled: boolean) => api.post(`/interviews/${interviewId}/recording`, { enabled }),
    onSuccess: (_result, enabled) => {
      invalidate()
      toast.push({
        title: enabled ? 'Recording flag set' : 'Recording flag cleared',
        message: 'No audio is captured; this only demonstrates the consent gate.',
        variant: 'success',
      })
    },
    onError: (error) =>
      toast.push({ title: 'Recording blocked', message: (error as Error).message, variant: 'error' }),
  })

  const addEvidence = useMutation({
    mutationFn: () => api.post<Evidence>('/evidence', { ...evidenceForm, interview_id: interviewId }),
    onSuccess: (evidence) => {
      setCaptureOpen(false)
      setEvidenceForm((current) => ({
        ...current,
        content: '',
        interpretation: '',
        confidence: 'medium',
        evidence_type: 'verbatim_quote',
      }))
      invalidate()
      toast.push({
        title: 'Evidence captured',
        message: `${evidence.code} keeps its interview context and provenance.`,
        variant: 'success',
      })
    },
    onError: (error) => setFormError((error as Error).message),
  })

  const saveFollowUp = useMutation({
    mutationFn: (questions: string[]) => api.patch(`/interviews/${interviewId}`, { follow_up_questions: questions }),
    onSuccess: () => {
      setFollowUp('')
      invalidate()
      toast.push({ title: 'Follow-up question added', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not add question', message: (error as Error).message, variant: 'error' }),
  })

  const recordingConsent = useMemo(
    () => data?.consent_records.some((record) => record.consent_type === 'recording' && record.status === 'granted'),
    [data],
  )

  if (isLoading) {
    return (
      <div className="page">
        <SectionCard>
          <LoadingBlock rows={8} />
        </SectionCard>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="page">
        <PageHeader title="Interview not found" />
        <ErrorState message={(error as Error)?.message ?? 'That interview does not exist.'} onRetry={() => refetch()} />
      </div>
    )
  }

  const allowedTransitions = INTERVIEW_TRANSITIONS[data.status].filter((status) => status !== 'cancelled')

  return (
    <div className="page">
      <Link to="/interviews" className="link-quiet inline mb-3">
        <ArrowLeft size={13} /> Back to interviews
      </Link>

      <PageHeader
        title={data.title}
        description={`${data.code} · ${data.project?.label ?? 'No project'} · ${data.duration_minutes} minutes · ${data.channel}`}
        meta={
          <div className="d-flex flex-wrap gap-2 align-items-center">
            <Pill tone={INTERVIEW_TONE[data.status]}>{titleCase(data.status)}</Pill>
            <Pill tone={data.consent_status === 'granted' ? 'green' : data.consent_status === 'declined' ? 'red' : 'amber'}>
              Consent: {titleCase(data.consent_status)}
            </Pill>
            <Pill tone={data.recording_enabled ? 'red' : 'outline'}>
              {data.recording_enabled ? 'Recording flag on' : 'Recording off'}
            </Pill>
            <span className="definition">Scheduled {formatDateTime(data.scheduled_at)}</span>
          </div>
        }
        actions={
          <>
            {allowedTransitions.map((status) => (
              <button
                key={status}
                type="button"
                className={status === 'completed' ? 'btn btn-primary' : 'btn btn-outline-secondary'}
                onClick={() => changeStatus.mutate(status)}
                disabled={changeStatus.isPending}
              >
                Mark {titleCase(status).toLowerCase()}
              </button>
            ))}
            <button type="button" className="btn btn-primary" onClick={() => setCaptureOpen(true)}>
              <Plus size={14} /> Capture evidence
            </button>
          </>
        }
      />

      {data.status === 'completed' && data.evidence.length === 0 && (
        <div className="mb-3">
          <Notice tone="warning" title="Completed with no evidence captured">
            A completed interview without evidence is a conversation nobody else can use. Capture the customer's words
            and your interpretation separately.
          </Notice>
        </div>
      )}

      <div className="section-grid grid-sidebar">
        <div className="stack stack-3">
          <SectionCard
            title="Evidence captured in this conversation"
            subtitle="Customer words and researcher interpretation are stored separately, with provenance."
            actions={
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setCaptureOpen(true)}>
                <Plus size={13} /> Add
              </button>
            }
          >
            {data.evidence.length === 0 ? (
              <EmptyState
                title="No evidence yet"
                description="Capture a verbatim quote, an observation or an open question while the conversation is fresh."
                action={
                  <button type="button" className="btn btn-primary btn-sm" onClick={() => setCaptureOpen(true)}>
                    Capture the first item
                  </button>
                }
              />
            ) : (
              <div className="stack stack-2">
                {data.evidence.map((item) => (
                  <EvidenceCard key={item.id} evidence={item} />
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard
            title="Interview guide"
            subtitle="Neutral prompts. The second sentence after a pause is usually the useful one."
            actions={<Pill tone="outline">{data.guide.length} questions</Pill>}
          >
            <ol className="stack stack-2" style={{ paddingLeft: 18, margin: 0 }}>
              {data.guide.map((question) => (
                <li key={question.id} style={{ fontSize: 13 }}>
                  <div style={{ fontWeight: 550 }}>{question.text}</div>
                  {question.purpose && <div className="definition">{question.purpose}</div>}
                </li>
              ))}
            </ol>
            <div className="mt-3">
              <Notice tone="neutral">
                Avoid leading prompts such as “Was it too expensive?”. If the participant raises price themselves, follow
                it; otherwise leave the cause open.
              </Notice>
            </div>
          </SectionCard>

          <SectionCard
            title="Interview notes"
            subtitle="Raw notes stay private to the workspace; evidence is the part that becomes shareable."
            actions={
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                onClick={() => saveNotes.mutate()}
                disabled={!notesDirty || saveNotes.isPending}
              >
                <Save size={13} /> {saveNotes.isPending ? 'Saving…' : notesDirty ? 'Save notes' : 'Saved'}
              </button>
            }
          >
            <textarea
              className="form-control"
              rows={7}
              value={notes}
              placeholder="What happened, in order? Note what surprised you before you interpret it."
              onChange={(event) => {
                setNotes(event.target.value)
                setNotesDirty(true)
              }}
            />
          </SectionCard>

          <SectionCard title="Follow-up questions" subtitle="What this conversation opened up rather than closed">
            <div className="d-flex gap-2">
              <input
                className="form-control"
                placeholder="e.g. Does bottle size change the decision for low-frequency users?"
                value={followUp}
                onChange={(event) => setFollowUp(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && followUp.trim().length > 4) {
                    saveFollowUp.mutate([...data.follow_up_questions, followUp.trim()])
                  }
                }}
              />
              <button
                type="button"
                className="btn btn-outline-secondary"
                disabled={followUp.trim().length < 5 || saveFollowUp.isPending}
                onClick={() => saveFollowUp.mutate([...data.follow_up_questions, followUp.trim()])}
              >
                Add
              </button>
            </div>
            <div className="stack stack-2 mt-3">
              {data.follow_up_questions.length === 0 && (
                <div className="definition">No follow-up questions recorded yet.</div>
              )}
              {data.follow_up_questions.map((question, index) => (
                <div key={`${question}-${index}`} className="inline" style={{ gap: 8, fontSize: 12.5 }}>
                  <span className="pill pill-outline">Q{index + 1}</span>
                  {question}
                </div>
              ))}
            </div>
          </SectionCard>
        </div>

        <div className="stack stack-3">
          <SectionCard title="Participant context">
            <div className="stack stack-3">
              <MetaItem
                label="Participant"
                value={
                  data.participant ? (
                    <Link to={`/participants/${data.participant.id}`}>{data.participant.display_name}</Link>
                  ) : (
                    '—'
                  )
                }
              />
              <MetaItem
                label="Segment"
                value={data.participant ? SEGMENT_LABELS[data.participant.segment] : '—'}
              />
              <MetaItem label="Purchases" value={data.participant ? `${data.participant.orders_count} order(s)` : '—'} />
              <MetaItem label="Purchase frequency" value={data.participant?.purchase_frequency || '—'} />
              <MetaItem label="Interviewer" value={data.interviewer?.label ?? 'Unassigned'} />
              <MetaItem
                label="Project"
                value={
                  data.project ? <Link to={`/projects/${data.project.id}`}>{data.project.label}</Link> : '—'
                }
              />
            </div>
          </SectionCard>

          <SectionCard
            title="Consent"
            subtitle="Recorded separately from the interview so it can be audited"
            icon={<ShieldCheck size={14} />}
            actions={
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setConsentOpen(true)}>
                Record
              </button>
            }
          >
            <div className="stack stack-2">
              {data.consent_records.length === 0 && (
                <div className="definition">No consent recorded. Treat anything captured as unverified.</div>
              )}
              {data.consent_records.map((record) => (
                <div key={record.id} className="row-between" style={{ fontSize: 12.5 }}>
                  <span>{titleCase(record.consent_type)}</span>
                  <Pill tone={record.status === 'granted' ? 'green' : record.status === 'declined' ? 'red' : 'amber'}>
                    {titleCase(record.status)}
                  </Pill>
                </div>
              ))}
              <hr className="divider" />
              <div className="row-between">
                <span className="definition">Recording</span>
                <button
                  type="button"
                  className={`btn btn-sm ${data.recording_enabled ? 'btn-danger-soft' : 'btn-outline-secondary'}`}
                  onClick={() => toggleRecording.mutate(!data.recording_enabled)}
                  disabled={toggleRecording.isPending}
                  title={recordingConsent ? 'Consent recorded' : 'Requires a granted recording consent'}
                >
                  {data.recording_enabled ? <Mic size={12} /> : <MicOff size={12} />}
                  {data.recording_enabled ? 'Disable flag' : 'Enable flag'}
                </button>
              </div>
              {!recordingConsent && (
                <div className="definition">
                  Recording consent has not been granted, so the API will refuse to switch the flag on.
                </div>
              )}
              <Notice tone="warning">
                No audio is recorded by this prototype. The flag exists to demonstrate the consent gate.
              </Notice>
            </div>
          </SectionCard>

          <SectionCard title="Evidence discipline">
            <div className="stack stack-2">
              <div className="definition">
                <strong>Customer words</strong> belong in the quote field. What you think it means belongs in the
                interpretation field.
              </div>
              <div className="definition">
                <strong>Provenance</strong> should point to the note or timestamp so a reader can check you.
              </div>
              <HonestyNote>
                If you cannot say where a statement came from, the API stores it as unverified and flags it. It will
                never be silently upgraded.
              </HonestyNote>
            </div>
          </SectionCard>
        </div>
      </div>

      <Modal show={captureOpen} onHide={() => setCaptureOpen(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Capture evidence · {data.code}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="section-grid grid-2" style={{ gap: 12 }}>
            <div style={{ gridColumn: '1 / -1' }}>
              <div className="form-label" id="evidence-type-label">
                Evidence type
              </div>
              <div className="d-flex flex-wrap gap-2" role="group" aria-labelledby="evidence-type-label">
                {EVIDENCE_TYPES.map((type) => (
                  <button
                    key={type}
                    type="button"
                    className={`filter-chip${evidenceForm.evidence_type === type ? ' active' : ''}`}
                    onClick={() => setEvidenceForm({ ...evidenceForm, evidence_type: type })}
                  >
                    {EVIDENCE_TYPE_LABELS[type]}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="evidence-content">
                Customer words or observation<span className="required-mark">*</span>
              </label>
              <textarea
                id="evidence-content"
                className="form-control"
                rows={3}
                value={evidenceForm.content}
                onChange={(event) => setEvidenceForm({ ...evidenceForm, content: event.target.value })}
                placeholder="What did they actually say? Keep their phrasing."
              />
              {formError && (
                <div className="field-error" role="alert">
                  {formError}
                </div>
              )}
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="interviewdetailpage-field-2">Your interpretation (clearly separated)</label>
              <textarea id="interviewdetailpage-field-2"
                className="form-control"
                rows={2}
                value={evidenceForm.interpretation}
                onChange={(event) => setEvidenceForm({ ...evidenceForm, interpretation: event.target.value })}
                placeholder="What you think it means, and what it does not prove."
              />
            </div>
            <div>
              <label className="form-label" htmlFor="interviewdetailpage-field-3">Customer context</label>
              <input id="interviewdetailpage-field-3"
                className="form-control"
                value={evidenceForm.customer_context}
                onChange={(event) => setEvidenceForm({ ...evidenceForm, customer_context: event.target.value })}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="interviewdetailpage-field-4">Confidence</label>
              <select id="interviewdetailpage-field-4"
                className="form-select"
                value={evidenceForm.confidence}
                onChange={(event) => setEvidenceForm({ ...evidenceForm, confidence: event.target.value as Confidence })}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" htmlFor="interviewdetailpage-field-5">Provenance</label>
              <input id="interviewdetailpage-field-5"
                className="form-control"
                value={evidenceForm.provenance}
                onChange={(event) => setEvidenceForm({ ...evidenceForm, provenance: event.target.value })}
                placeholder="Interview note and timestamp"
              />
              <div className="form-text">
                Clear this field to see what happens: the record is stored as unverified, flagged, and its confidence is
                forced to low.
              </div>
            </div>
          </div>
          <div className="mt-3">
            <Notice tone="neutral">
              Nothing is saved until you confirm. An LLM is deliberately not used here: generated summaries would blur
              the line between what the customer said and what the team concluded.
            </Notice>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setCaptureOpen(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={evidenceForm.content.trim().length < 3 || addEvidence.isPending}
            onClick={() => {
              setFormError(null)
              addEvidence.mutate()
            }}
          >
            {addEvidence.isPending ? 'Saving…' : 'Save evidence'}
          </button>
        </Modal.Footer>
      </Modal>

      <Modal show={consentOpen} onHide={() => setConsentOpen(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Record consent decision</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="stack stack-3">
            <div>
              <label className="form-label" htmlFor="interviewdetailpage-field-6">Consent type</label>
              <select id="interviewdetailpage-field-6"
                className="form-select"
                value={consentForm.type}
                onChange={(event) => setConsentForm({ ...consentForm, type: event.target.value as ConsentType })}
              >
                {CONSENT_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
              <div className="form-text">{CONSENT_TYPES.find((type) => type.value === consentForm.type)?.description}</div>
            </div>
            <div>
              <label className="form-label" htmlFor="interviewdetailpage-field-7">Decision</label>
              <select id="interviewdetailpage-field-7"
                className="form-select"
                value={consentForm.status}
                onChange={(event) => setConsentForm({ ...consentForm, status: event.target.value as ConsentStatus })}
              >
                <option value="granted">Granted</option>
                <option value="declined">Declined</option>
                <option value="withdrawn">Withdrawn</option>
                <option value="pending">Pending</option>
              </select>
            </div>
            <div>
              <label className="form-label" htmlFor="interviewdetailpage-field-8">Note</label>
              <input id="interviewdetailpage-field-8"
                className="form-control"
                value={consentForm.note}
                onChange={(event) => setConsentForm({ ...consentForm, note: event.target.value })}
              />
            </div>
            <Notice tone="warning">
              This prototype simulates consent capture. A production build must record consent through an approved
              process and retain evidence of it.
            </Notice>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-outline-secondary" onClick={() => setConsentOpen(false)}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary" onClick={() => recordConsent.mutate()} disabled={recordConsent.isPending}>
            <Lock size={13} /> {recordConsent.isPending ? 'Saving…' : 'Record consent'}
          </button>
        </Modal.Footer>
      </Modal>

      <div className="mt-3 definition">
        Last updated {relativeTime(data.updated_at)}
        {data.completed_at ? ` · completed ${formatDateTime(data.completed_at)}` : ''}
      </div>
    </div>
  )
}
