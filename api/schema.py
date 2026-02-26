from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AttitudeItem(BaseModel):
    """Individual attitude item response"""

    item_id: str = Field(..., description="Identifier for the attitude item")
    response: int = Field(..., ge=1, le=7, description="Response value (1-7 scale)")


class OpinionStatementItem(BaseModel):
    """Individual opinion statement response (6-point Likert scale)"""

    statement_id: str = Field(..., description="Identifier for the opinion statement")
    response: int = Field(
        ...,
        ge=1,
        le=6,
        description="Response value (1-6 scale: completely disagree to completely agree)",
    )


class Demographics(BaseModel):
    """Demographics information"""

    age: Optional[int] = Field(None, ge=18, description="Participant age (input field)")
    gender: Optional[str] = Field(
        None,
        description="Gender identity (5 options: 4 predefined + 1 self-describe option)",
    )
    gender_self_describe: Optional[str] = Field(
        None,
        description="Self-described gender (if 'self-describe' option was selected)",
    )
    education: Optional[str] = Field(
        None, description="Highest level of education (6 options)"
    )
    kids_in_school: Optional[str] = Field(
        None, description="Do you have kids in school? (3 options)"
    )
    political_belief: Optional[str] = Field(
        None, description="Political belief (6 options)"
    )


class Survey1Request(BaseModel):
    """Survey 1 (Baseline) response model"""

    participant_id: str = Field(
        ..., description="Unique participant identifier from Qualtrics"
    )
    prolific_id: Optional[str] = Field(None, description="Prolific participant ID")
    qualtrics_response_id: Optional[str] = Field(
        None, description="Qualtrics response ID"
    )

    topic_condition: str = Field(
        ..., description="Topic condition: 'teams', 'plastic_ban', or 'pe_mandatory'"
    )

    # Opinion question (first question - 6 choices: completely agree to completely disagree)
    opinion_question: Optional[int] = Field(
        None,
        ge=1,
        le=6,
        description="Opinion response (1-6 scale: completely agree to completely disagree)",
    )
    opinion_reason: Optional[str] = Field(
        None, description="Reason/explanation for the opinion response"
    )

    # Opinion statements (7 statements with 6-point Likert scale each)
    opinion_statements: List[OpinionStatementItem] = Field(
        ...,
        min_items=7,
        max_items=7,
        description="7 opinion statements about the topic",
    )

    # Feeling and importance questions (6-point scale each)
    feeling_strength: Optional[int] = Field(
        None,
        ge=1,
        le=6,
        description="How strongly do you feel about the topic? (1=Not at all, 6=Very strongly)",
    )
    topic_importance_feeling: Optional[int] = Field(
        None,
        ge=1,
        le=6,
        description="How important is the topic to you? (1=Not at all, 6=Very important)",
    )

    # Topic usage question (topic-dependent, e.g., "How do you use MS Teams?")
    topic_usage: Optional[List[str]] = Field(
        None,
        description="How do you use the topic? (multiple choice, 6 options total with 1 self-describe option)",
    )
    topic_usage_self_describe: Optional[str] = Field(
        None,
        description="Self-described topic usage (if 'self-describe' option was selected)",
    )

    # Topic behavior question (topic-dependent, e.g., "How often do you drink water in plastic bottles?")
    topic_behavior: Optional[str] = Field(
        None,
        description="Topic-specific behavior question (3 options, e.g., frequency of plastic bottle usage)",
    )

    attitudes: List[AttitudeItem] = Field(
        ..., min_items=8, max_items=8, description="8 attitude items"
    )

    demographics: Optional[Demographics] = Field(
        None, description="Demographics information"
    )

    # End of survey optional comment
    survey_comment: Optional[str] = Field(
        None, description="Optional comment at the end of the survey"
    )

    survey_completion_time: Optional[datetime] = Field(
        None, description="Survey completion timestamp"
    )
    ip_address: Optional[str] = Field(None, description="IP address of participant")
    user_agent: Optional[str] = Field(None, description="User agent string")


class Survey1Response(BaseModel):
    """Response model for Survey 1 submission"""

    success: bool
    message: str
    participant_id: str
    survey_id: str
    timestamp: datetime


class Survey3Item(BaseModel):
    """Individual Survey 3 item response (6-point Likert scale)"""

    question_id: str = Field(
        ..., description="Identifier for the Survey 3 question"
    )
    response: int = Field(
        ...,
        ge=1,
        le=6,
        description="Response value (1-6 scale: completely disagree to completely agree)",
    )


class Survey3Request(BaseModel):
    """Survey 3 (Follow-Up) response model

    This survey consists of two blocks of 8 compulsory Likert questions
    (1–6 scale, completely disagree to completely agree):
    - 8 items about the original topic (e.g., MS Teams)
    - 8 items about their opinion of the chatbot from Survey 2
    Each item allows exactly one response in Qualtrics.
    """

    participant_id: str = Field(
        ..., description="Unique participant identifier from Qualtrics"
    )
    prolific_id: Optional[str] = Field(
        None,
        description="Prolific participant ID (if already available via embedded data / earlier surveys)",
    )
    prolific_id_text_entry: Optional[str] = Field(
        None,
        description="Prolific ID entered by participant in Survey 3 (text entry); stored separately",
    )
    qualtrics_response_id: Optional[str] = Field(
        None, description="Qualtrics response ID"
    )

    topic_condition: Optional[str] = Field(
        None,
        description="Topic condition (e.g., 'teams', 'plastic_ban', 'pe_mandatory') if applicable",
    )

    topic_items: List[Survey3Item] = Field(
        ...,
        min_items=8,
        max_items=8,
        description="8 compulsory Likert questions about the topic (1–6 scale)",
    )

    chatbot_items: List[Survey3Item] = Field(
        ...,
        min_items=8,
        max_items=8,
        description="8 compulsory Likert questions about the chatbot from Survey 2 (1–6 scale)",
    )

    survey_completion_time: Optional[datetime] = Field(
        None, description="Survey completion timestamp"
    )
    ip_address: Optional[str] = Field(None, description="IP address of participant")
    user_agent: Optional[str] = Field(None, description="User agent string")

    study_comment_or_withdrawal: Optional[str] = Field(
        None,
        description=(
            "Optional free-text field: comments about the study or request to withdraw "
            "from the study (as shown in the final Survey 3 question)"
        ),
    )


class Survey3Response(BaseModel):
    """Response model for Survey 3 submission"""

    success: bool
    message: str
    participant_id: str
    survey_id: str
    timestamp: datetime
