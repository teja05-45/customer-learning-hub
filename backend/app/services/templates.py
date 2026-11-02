"""Project templates.

Templates exist to reduce the blank-page problem that makes research feel like
extra work. They pre-fill the shape of a project, never the conclusion.
"""

from app.models.enums import BusinessFunction, Priority, Segment
from app.schemas.project import ProjectTemplate

# Neutral, non-leading guide used when a project has no bespoke guide yet.
DEFAULT_INTERVIEW_GUIDE: list[tuple[str, str]] = [
    ("Can you tell me about the last time you purchased this product?", "Open without assuming a reason."),
    ("How has the product fitted into your routine since then?", "Explore actual use, not stated preference."),
    ("What happened after you finished the bottle, or stopped using it?", "Surface the real decision point."),
    ("Did anything make you consider another product?", "Let alternatives emerge in the participant's words."),
    ("What else influenced your decision?", "Catch factors the team has not thought of."),
    ("Is there anything I should have asked but did not?", "Hands control back to the participant."),
]

GUIDE_QUALITY_RULES = [
    "Ask about a specific occasion, not a general opinion.",
    "Never offer a cause the participant has not raised.",
    "Ask 'what happened next' rather than 'why did you not buy again'.",
    "Leave silence after an answer; the second sentence is often the useful one.",
]

PROJECT_TEMPLATES: list[ProjectTemplate] = [
    ProjectTemplate(
        key="repeat_purchase",
        name="Repeat purchase investigation",
        description="Understand why some customers buy once and do not return.",
        objective=(
            "Understand what happened after a first purchase, and identify which explanations recur across "
            "customer segments rather than assuming a single cause."
        ),
        methodology="Moderated 30-minute interviews (simulated)",
        priority=Priority.HIGH,
        business_functions=[BusinessFunction.GROWTH, BusinessFunction.PRODUCT_CATEGORY],
        target_segments=[Segment.FIRST_TIME, Segment.LAPSED, Segment.HOUSEHOLD],
        questions=[
            "What happened after the product was finished?",
            "What else was going on when the customer decided not to repurchase?",
            "Do household buyers judge the product differently from individual buyers?",
        ],
    ),
    ProjectTemplate(
        key="product_experience",
        name="Product experience research",
        description="Find out how a product actually fits into someone's day, not how it is meant to.",
        objective=(
            "Explore how the product fits into real routines, what disappoints customers and which alternatives "
            "they compare it against."
        ),
        methodology="Moderated 30-minute interviews (simulated)",
        priority=Priority.MEDIUM,
        business_functions=[BusinessFunction.PRODUCT_CATEGORY],
        target_segments=[Segment.REPEAT, Segment.HOUSEHOLD],
        questions=[
            "How does the product fit into your day?",
            "What would make you stop using it?",
            "What do you compare it against?",
        ],
    ),
    ProjectTemplate(
        key="campaign_perception",
        name="Campaign perception research",
        description="Test whether the words the team uses match the words customers use.",
        objective=(
            "Check whether campaign language matches customer vocabulary before creative is produced, and capture "
            "quotable language with consent."
        ),
        methodology="Moderated 25-minute interviews (simulated)",
        priority=Priority.MEDIUM,
        business_functions=[BusinessFunction.BRAND_MARKETING],
        target_segments=[Segment.REPEAT, Segment.FIRST_TIME],
        questions=[
            "How would you describe this part of your day to a friend?",
            "Which words would feel false to you?",
            "Where did you first hear about us?",
        ],
    ),
    ProjectTemplate(
        key="customer_journey",
        name="Customer journey research",
        description="Map the moments between first order and second order.",
        objective=(
            "Map what happens between a first order and a second order, and identify the moments the team can "
            "influence without assuming the answer."
        ),
        methodology="Diary study plus short interviews (simulated)",
        priority=Priority.HIGH,
        business_functions=[BusinessFunction.GROWTH, BusinessFunction.CUSTOMER_EXPERIENCE],
        target_segments=[Segment.FIRST_TIME, Segment.LAPSED],
        questions=[
            "What triggered the second purchase?",
            "Which interactions changed your decision?",
            "Where did you nearly give up?",
        ],
    ),
]
