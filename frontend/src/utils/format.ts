import type {
  ActionStatus,
  BusinessFunction,
  CollectionMethod,
  Confidence,
  DecisionStatus,
  Eligibility,
  EvidenceType,
  FeedbackSourceType,
  InsightStatus,
  InterviewStatus,
  Priority,
  ProjectStatus,
  RecruitmentStage,
  ResearchDepth,
  Segment,
  VerificationStatus,
} from '../types'

export type Tone = 'neutral' | 'blue' | 'green' | 'amber' | 'red' | 'purple' | 'outline'

const dateFormatter = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
const dateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return dateFormatter.format(date)
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return dateTimeFormatter.format(date)
}

export function formatDateInput(value: Date): string {
  return value.toISOString().slice(0, 10)
}

export function relativeTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const diffMs = date.getTime() - Date.now()
  const diffDays = Math.round(diffMs / 86_400_000)
  const formatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
  if (Math.abs(diffDays) < 1) {
    const diffHours = Math.round(diffMs / 3_600_000)
    if (Math.abs(diffHours) < 1) return 'just now'
    return formatter.format(diffHours, 'hour')
  }
  if (Math.abs(diffDays) < 30) return formatter.format(diffDays, 'day')
  const diffMonths = Math.round(diffDays / 30)
  if (Math.abs(diffMonths) < 12) return formatter.format(diffMonths, 'month')
  return formatter.format(Math.round(diffMonths / 12), 'year')
}

export function titleCase(value: string | null | undefined): string {
  if (!value) return '—'
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

export const SEGMENT_LABELS: Record<Segment, string> = {
  first_time_buyer: 'First-time buyer',
  repeat_buyer: 'Repeat buyer',
  lapsed_buyer: 'Lapsed buyer',
  household_buyer: 'Household buyer',
  unknown: 'Unclassified',
}

export const SEGMENT_FILTER_LABELS: Record<Segment, string> = {
  first_time_buyer: 'First-time',
  repeat_buyer: 'Repeat',
  lapsed_buyer: 'Lapsed',
  household_buyer: 'Household',
  unknown: 'Unclassified',
}

export const ELIGIBILITY_LABELS: Record<Eligibility, string> = {
  eligible: 'Eligible',
  limited: 'Limited contact',
  ineligible: 'Not eligible',
}

export const BUSINESS_FUNCTION_LABELS: Record<BusinessFunction, string> = {
  brand_marketing: 'Brand & Marketing',
  product_category: 'Product & Category',
  growth: 'Growth',
  customer_experience: 'Customer Experience',
  operations: 'Operations',
  executive: 'Executive',
}

export const EVIDENCE_TYPE_LABELS: Record<EvidenceType, string> = {
  verbatim_quote: 'Verbatim quote',
  observation: 'Observation',
  researcher_interpretation: 'Researcher interpretation',
  contradictory_evidence: 'Contradictory evidence',
  open_question: 'Open question',
}

export const STAGE_LABELS: Record<RecruitmentStage, string> = {
  identified: 'Identified',
  selected: 'Selected',
  invited: 'Invited',
  responded: 'Responded',
  scheduled: 'Scheduled',
  completed: 'Completed',
  declined: 'Declined',
  no_response: 'No response',
  cancelled: 'Cancelled',
  withdrawn: 'Withdrawn',
}

// Every stage is visible, including the terminal ones. Hiding declines and
// no-responses would make the pipeline look more successful than it is.
export const PIPELINE_STAGES: RecruitmentStage[] = [
  'identified',
  'selected',
  'invited',
  'responded',
  'scheduled',
  'completed',
  'declined',
  'no_response',
  'cancelled',
  'withdrawn',
]

export const RECRUITMENT_TRANSITIONS: Record<RecruitmentStage, RecruitmentStage[]> = {
  identified: ['selected', 'cancelled'],
  selected: ['invited', 'cancelled'],
  invited: ['responded', 'declined', 'no_response', 'cancelled'],
  responded: ['scheduled', 'declined', 'withdrawn'],
  scheduled: ['completed', 'cancelled', 'withdrawn', 'no_response'],
  completed: ['withdrawn'],
  declined: ['selected'],
  no_response: ['invited', 'selected'],
  cancelled: ['selected'],
  withdrawn: ['selected'],
}

export const INTERVIEW_TRANSITIONS: Record<InterviewStatus, InterviewStatus[]> = {
  planned: ['scheduled', 'cancelled'],
  scheduled: ['in_progress', 'completed', 'cancelled'],
  in_progress: ['completed', 'cancelled'],
  completed: [],
  cancelled: ['scheduled'],
}

export const DECISION_TRANSITIONS: Record<DecisionStatus, DecisionStatus[]> = {
  proposed: ['under_review', 'accepted', 'rejected', 'deferred'],
  under_review: ['accepted', 'rejected', 'deferred', 'proposed'],
  accepted: ['deferred', 'proposed'],
  rejected: ['proposed'],
  deferred: ['proposed', 'under_review'],
}

export const PROJECT_STATUS_TONE: Record<ProjectStatus, Tone> = {
  draft: 'neutral',
  planning: 'blue',
  recruiting: 'amber',
  in_progress: 'green',
  analysis: 'purple',
  completed: 'green',
  archived: 'outline',
}

export const PRIORITY_TONE: Record<Priority, Tone> = {
  low: 'outline',
  medium: 'blue',
  high: 'amber',
  critical: 'red',
}

export const STAGE_TONE: Record<RecruitmentStage, Tone> = {
  identified: 'neutral',
  selected: 'blue',
  invited: 'amber',
  responded: 'purple',
  scheduled: 'blue',
  completed: 'green',
  declined: 'red',
  no_response: 'amber',
  cancelled: 'outline',
  withdrawn: 'outline',
}

export const INTERVIEW_TONE: Record<InterviewStatus, Tone> = {
  planned: 'neutral',
  scheduled: 'blue',
  in_progress: 'amber',
  completed: 'green',
  cancelled: 'outline',
}

export const INSIGHT_TONE: Record<InsightStatus, Tone> = {
  draft: 'neutral',
  under_review: 'amber',
  validated_internal: 'green',
  needs_more_research: 'blue',
  archived: 'outline',
}

export const DECISION_TONE: Record<DecisionStatus, Tone> = {
  proposed: 'neutral',
  under_review: 'amber',
  accepted: 'green',
  rejected: 'red',
  deferred: 'blue',
}

export const ACTION_TONE: Record<ActionStatus, Tone> = {
  not_started: 'neutral',
  in_progress: 'blue',
  completed: 'green',
  blocked: 'red',
}

export const CONFIDENCE_TONE: Record<Confidence, Tone> = {
  low: 'amber',
  medium: 'blue',
  high: 'green',
}

export const EVIDENCE_TONE: Record<EvidenceType, Tone> = {
  verbatim_quote: 'blue',
  observation: 'blue',
  researcher_interpretation: 'purple',
  contradictory_evidence: 'amber',
  open_question: 'outline',
}

export const FEEDBACK_SOURCE_LABELS: Record<FeedbackSourceType, string> = {
  interview: 'Interview',
  written_feedback: 'Written feedback',
  structured_form: 'Structured form',
  short_survey: 'Short survey',
  customer_support: 'Support feedback',
  product_review: 'Product review',
  manual_entry: 'Manual entry',
  csv_import: 'CSV import',
}

export const COLLECTION_METHOD_LABELS: Record<CollectionMethod, string> = {
  in_person_interview: 'In-person interview',
  video_interview: 'Video interview',
  phone_interview: 'Phone interview',
  written_feedback: 'Written feedback',
  structured_form: 'Structured form',
  short_survey: 'Short survey',
  support_feedback: 'Support feedback',
  product_review: 'Product review',
  imported_feedback: 'Imported feedback',
  manual_entry: 'Manual entry',
}

export const VERIFICATION_LABELS: Record<VerificationStatus, string> = {
  unverified: 'Unverified',
  needs_review: 'Needs review',
  verified: 'Source verified',
}

export const VERIFICATION_TONE: Record<VerificationStatus, Tone> = {
  unverified: 'amber',
  needs_review: 'amber',
  verified: 'green',
}

export const DEPTH_LABELS: Record<ResearchDepth, string> = {
  deep: 'Deep',
  medium: 'Medium',
  limited: 'Limited',
  context: 'Context only',
}

export const DEPTH_TONE: Record<ResearchDepth, Tone> = {
  deep: 'green',
  medium: 'blue',
  limited: 'amber',
  context: 'outline',
}

export function initialsOf(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

export function pluralise(count: number, singular: string, plural?: string): string {
  return `${count} ${count === 1 ? singular : plural ?? `${singular}s`}`
}

export function truncate(text: string, length = 160): string {
  if (text.length <= length) return text
  return `${text.slice(0, length).trimEnd()}…`
}
