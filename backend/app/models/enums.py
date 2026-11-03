"""Controlled vocabularies.

Stored as plain strings so the schema stays portable across SQLite and
PostgreSQL, and so adding a value never requires a destructive migration.
Validation lives in Pydantic schemas.
"""

from enum import Enum


class UserRole(str, Enum):
    CEO = "ceo"
    RESEARCHER = "researcher"
    BUSINESS_OWNER = "business_owner"
    CX = "cx"
    ADMIN = "admin"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    PLANNING = "planning"
    RECRUITING = "recruiting"
    IN_PROGRESS = "in_progress"
    ANALYSIS = "analysis"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Segment(str, Enum):
    FIRST_TIME = "first_time_buyer"
    REPEAT = "repeat_buyer"
    LAPSED = "lapsed_buyer"
    HOUSEHOLD = "household_buyer"
    UNKNOWN = "unknown"


class Eligibility(str, Enum):
    ELIGIBLE = "eligible"
    LIMITED = "limited"
    INELIGIBLE = "ineligible"


class RecruitmentStage(str, Enum):
    IDENTIFIED = "identified"
    SELECTED = "selected"
    INVITED = "invited"
    RESPONDED = "responded"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    DECLINED = "declined"
    NO_RESPONSE = "no_response"
    CANCELLED = "cancelled"
    WITHDRAWN = "withdrawn"


class InterviewStatus(str, Enum):
    PLANNED = "planned"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ConsentType(str, Enum):
    PARTICIPATION = "participation"
    RECORDING = "recording"
    QUOTING = "quoting"
    SHARING_INTERNAL = "sharing_internal"


class ConsentStatus(str, Enum):
    PENDING = "pending"
    GRANTED = "granted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class EvidenceType(str, Enum):
    VERBATIM_QUOTE = "verbatim_quote"
    OBSERVATION = "observation"
    RESEARCHER_INTERPRETATION = "researcher_interpretation"
    CONTRADICTORY = "contradictory_evidence"
    OPEN_QUESTION = "open_question"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    REVIEWED = "reviewed"
    FLAGGED = "flagged"


class ProvenanceStatus(str, Enum):
    RECORDED = "recorded"
    PARTIAL = "partial"
    MISSING = "missing"


class InsightStatus(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    VALIDATED = "validated_internal"
    NEEDS_RESEARCH = "needs_more_research"
    ARCHIVED = "archived"


class EvidenceRole(str, Enum):
    SUPPORTING = "supporting"
    CONTRADICTORY = "contradictory"


class DecisionStatus(str, Enum):
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class ActionStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class BusinessFunction(str, Enum):
    BRAND_MARKETING = "brand_marketing"
    PRODUCT_CATEGORY = "product_category"
    GROWTH = "growth"
    CUSTOMER_EXPERIENCE = "customer_experience"
    OPERATIONS = "operations"
    EXECUTIVE = "executive"


# Allowed forward transitions for the recruitment pipeline. Terminal states can
# be re-opened explicitly because participants change their minds.
RECRUITMENT_TRANSITIONS: dict[str, set[str]] = {
    RecruitmentStage.IDENTIFIED: {RecruitmentStage.SELECTED, RecruitmentStage.CANCELLED},
    RecruitmentStage.SELECTED: {RecruitmentStage.INVITED, RecruitmentStage.CANCELLED},
    RecruitmentStage.INVITED: {
        RecruitmentStage.RESPONDED,
        RecruitmentStage.DECLINED,
        RecruitmentStage.NO_RESPONSE,
        RecruitmentStage.CANCELLED,
    },
    RecruitmentStage.RESPONDED: {RecruitmentStage.SCHEDULED, RecruitmentStage.DECLINED, RecruitmentStage.WITHDRAWN},
    RecruitmentStage.SCHEDULED: {
        RecruitmentStage.COMPLETED,
        RecruitmentStage.CANCELLED,
        RecruitmentStage.WITHDRAWN,
        RecruitmentStage.NO_RESPONSE,
    },
    RecruitmentStage.COMPLETED: {RecruitmentStage.WITHDRAWN},
    RecruitmentStage.DECLINED: {RecruitmentStage.SELECTED},
    RecruitmentStage.NO_RESPONSE: {RecruitmentStage.INVITED, RecruitmentStage.SELECTED},
    RecruitmentStage.CANCELLED: {RecruitmentStage.SELECTED},
    RecruitmentStage.WITHDRAWN: {RecruitmentStage.SELECTED},
}

INTERVIEW_TRANSITIONS: dict[str, set[str]] = {
    InterviewStatus.PLANNED: {InterviewStatus.SCHEDULED, InterviewStatus.CANCELLED},
    InterviewStatus.SCHEDULED: {
        InterviewStatus.IN_PROGRESS,
        InterviewStatus.COMPLETED,
        InterviewStatus.CANCELLED,
    },
    InterviewStatus.IN_PROGRESS: {InterviewStatus.COMPLETED, InterviewStatus.CANCELLED},
    InterviewStatus.COMPLETED: set(),
    InterviewStatus.CANCELLED: {InterviewStatus.SCHEDULED},
}

DECISION_TRANSITIONS: dict[str, set[str]] = {
    DecisionStatus.PROPOSED: {DecisionStatus.UNDER_REVIEW, DecisionStatus.ACCEPTED, DecisionStatus.REJECTED, DecisionStatus.DEFERRED},
    DecisionStatus.UNDER_REVIEW: {DecisionStatus.ACCEPTED, DecisionStatus.REJECTED, DecisionStatus.DEFERRED, DecisionStatus.PROPOSED},
    DecisionStatus.ACCEPTED: {DecisionStatus.DEFERRED, DecisionStatus.PROPOSED},
    DecisionStatus.REJECTED: {DecisionStatus.PROPOSED},
    DecisionStatus.DEFERRED: {DecisionStatus.PROPOSED, DecisionStatus.UNDER_REVIEW},
}


class FeedbackSourceType(str, Enum):
    INTERVIEW = "interview"
    WRITTEN_FEEDBACK = "written_feedback"
    STRUCTURED_FORM = "structured_form"
    SHORT_SURVEY = "short_survey"
    CUSTOMER_SUPPORT = "customer_support"
    PRODUCT_REVIEW = "product_review"
    MANUAL_ENTRY = "manual_entry"
    CSV_IMPORT = "csv_import"


class CollectionMethod(str, Enum):
    IN_PERSON_INTERVIEW = "in_person_interview"
    VIDEO_INTERVIEW = "video_interview"
    PHONE_INTERVIEW = "phone_interview"
    WRITTEN_FEEDBACK = "written_feedback"
    STRUCTURED_FORM = "structured_form"
    SHORT_SURVEY = "short_survey"
    SUPPORT_FEEDBACK = "support_feedback"
    PRODUCT_REVIEW = "product_review"
    IMPORTED_FEEDBACK = "imported_feedback"
    MANUAL_ENTRY = "manual_entry"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    NEEDS_REVIEW = "needs_review"
    VERIFIED = "verified"


# Collection depth is deliberately explicit: a survey answer and a moderated
# interview are both useful, but they are not equal evidence.
FEEDBACK_DEPTH: dict[str, tuple[str, str]] = {
    CollectionMethod.IN_PERSON_INTERVIEW.value: (
        "deep",
        "Moderated in-person conversation with room to probe and clarify.",
    ),
    CollectionMethod.VIDEO_INTERVIEW.value: (
        "deep",
        "Moderated video conversation with room to probe and clarify.",
    ),
    CollectionMethod.PHONE_INTERVIEW.value: (
        "deep",
        "Moderated phone conversation; tone and context are partly lost.",
    ),
    CollectionMethod.WRITTEN_FEEDBACK.value: (
        "medium",
        "Written in the customer's own words, but nobody could probe the answer.",
    ),
    CollectionMethod.STRUCTURED_FORM.value: (
        "medium",
        "Structured prompts answered without a moderator; follow-up is impossible.",
    ),
    CollectionMethod.SHORT_SURVEY.value: (
        "limited",
        "Closed or short answers. Useful for coverage, not for explaining why.",
    ),
    CollectionMethod.SUPPORT_FEEDBACK.value: (
        "context",
        "Recorded while resolving a support issue, not collected for research.",
    ),
    CollectionMethod.PRODUCT_REVIEW.value: (
        "context",
        "Public review with no sampling control and no ability to probe.",
    ),
    CollectionMethod.IMPORTED_FEEDBACK.value: (
        "context",
        "Bulk import. Depth depends on the originating system.",
    ),
    CollectionMethod.MANUAL_ENTRY.value: (
        "context",
        "Manually transcribed. Provenance depends on the recorded source reference.",
    ),
}


def feedback_depth(method: str) -> tuple[str, str]:
    return FEEDBACK_DEPTH.get(method, ("context", "No depth classification is defined for this method."))


def values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]
