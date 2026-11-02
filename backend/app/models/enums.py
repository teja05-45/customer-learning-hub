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


def values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]
