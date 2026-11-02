/**
 * Types mirroring the FastAPI response models.
 *
 * Kept hand-written rather than generated so the contract stays readable; the
 * backend tests cover the schema, and `npm run typecheck` catches drift in the
 * UI.
 */

export type ProjectStatus = 'draft' | 'planning' | 'recruiting' | 'in_progress' | 'analysis' | 'completed' | 'archived'
export type Priority = 'low' | 'medium' | 'high' | 'critical'
export type Segment = 'first_time_buyer' | 'repeat_buyer' | 'lapsed_buyer' | 'household_buyer' | 'unknown'
export type Eligibility = 'eligible' | 'limited' | 'ineligible'
export type RecruitmentStage =
  | 'identified'
  | 'selected'
  | 'invited'
  | 'responded'
  | 'scheduled'
  | 'completed'
  | 'declined'
  | 'no_response'
  | 'cancelled'
  | 'withdrawn'
export type InterviewStatus = 'planned' | 'scheduled' | 'in_progress' | 'completed' | 'cancelled'
export type ConsentStatus = 'pending' | 'granted' | 'declined' | 'withdrawn'
export type ConsentType = 'participation' | 'recording' | 'quoting' | 'sharing_internal'
export type EvidenceType =
  | 'verbatim_quote'
  | 'observation'
  | 'researcher_interpretation'
  | 'contradictory_evidence'
  | 'open_question'
export type Confidence = 'low' | 'medium' | 'high'
export type ReviewStatus = 'unreviewed' | 'reviewed' | 'flagged'
export type ProvenanceStatus = 'recorded' | 'partial' | 'missing'
export type InsightStatus = 'draft' | 'under_review' | 'validated_internal' | 'needs_more_research' | 'archived'
export type DecisionStatus = 'proposed' | 'under_review' | 'accepted' | 'rejected' | 'deferred'
export type ActionStatus = 'not_started' | 'in_progress' | 'completed' | 'blocked'
export type BusinessFunction =
  | 'brand_marketing'
  | 'product_category'
  | 'growth'
  | 'customer_experience'
  | 'operations'
  | 'executive'
export type EvidenceRole = 'supporting' | 'contradictory'
export type UserRole = 'ceo' | 'researcher' | 'business_owner' | 'cx' | 'admin'

export interface Ref {
  id: string
  label: string
  sublabel?: string | null
}

export interface DemoUser {
  id: string
  name: string
  role: UserRole
  job_title: string
  initials: string
  can_view: string[]
  description: string
}

export interface Session {
  demo_mode: boolean
  current_user: DemoUser | null
  users: DemoUser[]
  notice: string
}

export interface ProjectCounts {
  participants: number
  interviews: number
  interviews_completed: number
  evidence: number
  insights: number
  decisions: number
  open_actions: number
}

export interface ResearchQuestion {
  id: string
  text: string
  order_index: number
  is_resolved: boolean
  resolution_note: string
}

export interface ProjectSummary {
  id: string
  name: string
  objective: string
  description: string
  status: ProjectStatus
  priority: Priority
  methodology: string
  owner_id: string | null
  business_functions: BusinessFunction[]
  target_segments: Segment[]
  start_date: string | null
  deadline: string | null
  archived_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
  owner?: Ref | null
  counts: ProjectCounts
  unresolved_questions: number
  segment_gap: boolean
}

export interface ProjectDetail extends ProjectSummary {
  questions: ResearchQuestion[]
}

export interface ProjectListResponse {
  items: ProjectSummary[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface ProjectTemplate {
  key: string
  name: string
  description: string
  objective: string
  methodology: string
  priority: Priority
  business_functions: BusinessFunction[]
  target_segments: Segment[]
  questions: string[]
}

export interface Participant {
  id: string
  code: string
  display_name: string
  segment: Segment
  purchase_frequency: string
  orders_count: number
  last_purchase_at: string | null
  product_category: string
  eligibility: Eligibility
  eligibility_note: string
  contact_route: string | null
  contact_consent: string
  notes: string
  is_synthetic: boolean
  last_research_contact_at: string | null
  created_at: string
  updated_at: string
}

export interface ParticipationHistoryItem {
  interview_id: string | null
  interview_code: string | null
  project_id: string
  project_name: string
  status: string
  scheduled_at: string | null
  evidence_count: number
  insight_count: number
}

export interface ParticipantDetail extends Participant {
  recruitment: RecruitmentRecord[]
  participation_history: ParticipationHistoryItem[]
  evidence_count: number
}

export interface ParticipantListResponse {
  items: Participant[]
  total: number
  page: number
  page_size: number
  pages: number
  segment_counts: Record<string, number>
}

export interface RecruitmentEvent {
  id: string
  from_stage: string | null
  to_stage: string
  note: string
  created_at: string
  actor?: Ref | null
}

export interface RecruitmentRecord {
  id: string
  project_id: string
  participant_id: string
  stage: RecruitmentStage
  next_action: string
  notes: string
  invited_at: string | null
  responded_at: string | null
  scheduled_at: string | null
  updated_at: string
  participant?: Participant | null
  project?: Ref | null
  updated_by?: Ref | null
  days_in_stage: number | null
  events: RecruitmentEvent[]
}

export interface RecruitmentListResponse {
  items: RecruitmentRecord[]
  total: number
  stage_counts: Record<string, number>
  segment_coverage: Record<string, number>
  warnings: string[]
}

export interface GuideQuestion {
  id: string
  text: string
  purpose: string
  order_index: number
  is_leading: boolean
}

export interface ConsentRecord {
  id: string
  consent_type: ConsentType
  status: ConsentStatus
  note: string
  recorded_at: string
  recorded_by?: Ref | null
}

export interface Evidence {
  id: string
  code: string
  interview_id: string | null
  project_id: string
  participant_id: string | null
  evidence_type: EvidenceType
  content: string
  interpretation: string
  customer_context: string
  segment: Segment
  provenance: string
  provenance_status: ProvenanceStatus
  confidence: Confidence
  review_status: ReviewStatus
  captured_at: string
  captured_by_id: string | null
  is_verified_source: boolean
  provenance_warning: string | null
  participant?: Ref | null
  captured_by?: Ref | null
  interview?: Ref | null
  project?: Ref | null
  insight_links: { insight_id: string; insight_code: string; insight_title: string; role: EvidenceRole }[]
}

export interface EvidenceListResponse {
  items: Evidence[]
  total: number
  type_counts: Record<string, number>
  unverified_count: number
}

export interface InterviewSummary {
  id: string
  code: string
  project_id: string
  participant_id: string
  recruitment_id: string | null
  title: string
  objective: string
  scheduled_at: string | null
  duration_minutes: number
  interviewer_id: string | null
  status: InterviewStatus
  channel: string
  consent_status: ConsentStatus
  recording_enabled: boolean
  notes: string
  summary: string
  follow_up_questions: string[]
  completed_at: string | null
  created_at: string
  updated_at: string
  participant?: Participant | null
  project?: Ref | null
  interviewer?: Ref | null
  evidence_count: number
  evidence_pending_review: number
}

export interface InterviewDetail extends InterviewSummary {
  guide: GuideQuestion[]
  consent_records: ConsentRecord[]
  evidence: Evidence[]
}

export interface InterviewListResponse {
  items: InterviewSummary[]
  total: number
  status_counts: Record<string, number>
}

export interface InsightSummary {
  id: string
  code: string
  title: string
  summary: string
  interpretation: string
  research_question: string
  project_id: string | null
  status: InsightStatus
  confidence: Confidence
  owner_id: string | null
  limitations: string
  segments: Segment[]
  validated_at: string | null
  created_at: string
  updated_at: string
  owner?: Ref | null
  project?: Ref | null
  supporting_count: number
  contradictory_count: number
  evidence_count: number
  decision_count: number
  reuse_flag: boolean
}

export interface InsightDetail extends InsightSummary {
  evidence: Evidence[]
  decisions: {
    id: string
    code: string
    title: string
    status: DecisionStatus
    business_function: BusinessFunction
    decision_date: string | null
  }[]
  evidence_warning: string | null
}

export interface InsightListResponse {
  items: InsightSummary[]
  total: number
  status_counts: Record<string, number>
}

export interface DecisionSummary {
  id: string
  code: string
  title: string
  business_function: BusinessFunction
  problem_statement: string
  description: string
  rationale: string
  limitations: string
  project_id: string | null
  owner_id: string | null
  decision_date: string | null
  status: DecisionStatus
  evidence_sufficient: boolean | null
  created_at: string
  updated_at: string
  owner?: Ref | null
  project?: Ref | null
  insight_count: number
  evidence_count: number
  action_count: number
  open_action_count: number
  evidence_warning: string | null
  contradicting_count: number
}

export interface ActionRef {
  id: string
  code: string
  title: string
  status: ActionStatus
  owner?: Ref | null
  due_date: string | null
  is_overdue: boolean
}

export interface DecisionDetail extends DecisionSummary {
  insights: InsightSummary[]
  evidence: Evidence[]
  actions: ActionRef[]
  history: { at: string; summary: string; actor: string | null; verb: string }[]
}

export interface DecisionListResponse {
  items: DecisionSummary[]
  total: number
  status_counts: Record<string, number>
  unevidenced: number
}

export interface BusinessAction {
  id: string
  code: string
  title: string
  description: string
  owner_id: string | null
  due_date: string | null
  priority: Priority
  status: ActionStatus
  decision_id: string | null
  insight_id: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
  owner?: Ref | null
  decision?: Ref | null
  insight?: Ref | null
  is_overdue: boolean
  days_until_due: number | null
}

export interface ActionListResponse {
  items: BusinessAction[]
  total: number
  status_counts: Record<string, number>
  overdue: number
}

export interface ResponseRate {
  value: number | null
  display: string
  numerator: number
  denominator: number
  definition: string
  sample_warning: string | null
}

export interface LearningSignals {
  findings_with_evidence: number
  findings_total: number
  findings_coverage_display: string
  decisions_supported: number
  decisions_total: number
  insights_reused: number
  insights_reuse_display: string
  unresolved_questions: number
  overdue_actions: number
  unevidenced_decisions: number
}

export interface ActivityItem {
  id: string
  entity_type: string
  entity_id: string | null
  entity_label: string
  summary: string
  verb: string
  actor?: Ref | null
  created_at: string
  project_id: string | null
}

export interface Dashboard {
  generated_at: string
  active_projects: number
  interviews_completed: number
  interviews_upcoming: number
  participants_contacted: number
  response_rate: ResponseRate
  insights_awaiting_review: number
  decisions_with_evidence: number
  decisions_total: number
  open_actions: number
  overdue_actions: number
  learning: LearningSignals
  timeline: { month: string; label: string; interviews: number; evidence: number; insights: number }[]
  segments: { segment: Segment; participants: number; interviews: number; evidence: number }[]
  decision_status: { status: string; count: number }[]
  action_status: { status: string; count: number }[]
  recent_insights: InsightSummary[]
  upcoming_interviews: InterviewSummary[]
  recent_activity: ActivityItem[]
  outstanding_actions: BusinessAction[]
  projects: ProjectSummary[]
  data_note: string
}

export interface SearchResult {
  id: string
  entity_type: 'project' | 'participant' | 'interview' | 'evidence' | 'insight' | 'decision' | 'action'
  title: string
  subtitle: string
  snippet: string
  href: string
  badges: string[]
  project_id: string | null
}

export interface SearchResponse {
  query: string
  total: number
  groups: { entity_type: string; label: string; items: SearchResult[] }[]
  suggestions: SearchResult[]
  suggestion_reason: string | null
  contacts_excluded_note: string
}

export interface AnalyticsMetric {
  key: string
  label: string
  display: string
  basis: 'observed' | 'calculated' | 'illustrative' | 'pending_baseline'
  definition: string
  note: string | null
  target: string | null
}

export interface Analytics {
  generated_at: string
  metrics: AnalyticsMetric[]
  segment_distribution: { segment: Segment; participants: number; interviews: number; evidence: number }[]
  decision_funnel: { status: string; count: number }[]
  action_completion: { status: string; count: number }[]
  unresolved_questions: {
    id: string
    project_id: string
    project_name: string
    text: string
    is_resolved: boolean
    resolution_note: string
  }[]
  reuse_detail: {
    insight_id: string
    code: string
    title: string
    decisions: number
    reused: boolean
    decision_titles: string[]
  }[]
  measurement_gaps: { key: string; label: string; why: string; how_to_collect: string }[]
  honesty_note: string
}

export interface OrgSettings {
  id: string
  name: string
  recording_default: boolean
  retention_months: number
  show_demo_banner: boolean
  updated_at: string
}

export interface Health {
  status: string
  version: string
  environment: string
  database: string
  demo_mode: boolean
  seeded: boolean
  checked_at: string
}
