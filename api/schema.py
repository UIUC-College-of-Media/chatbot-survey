from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BlockStatementItem(BaseModel):
    """One row from the 7-statement opinion matrix (1-6 Likert)"""

    statement_id: str = Field(
        ..., description="Identifier for the statement row (e.g., stmt1–stmt7)"
    )
    statement_text: Optional[str] = Field(
        None,
        description="Text for the statement row (if available from Qualtrics piped text)",
    )
    response: int = Field(
        ...,
        ge=1,
        le=6,
        description="Response value (1-6: completely disagree to completely agree)",
    )
    response_label: Optional[str] = Field(
        None,
        description="Human-readable label for response (same 6-point agree–disagree wording as the matrix)",
    )


class BlockResponses(BaseModel):
    """All responses from the randomized 5-question block.

    Each block contains:
    - 1 opinion item (single Likert 1-6)
    - 1 open-text reason
    - 7 opinion statement matrix rows (each 1-6)
    - 1 feeling strength item (1-6)
    - 1 topic importance item (1-6)
    """

    opinion: Optional[int] = Field(
        None,
        ge=1,
        le=6,
        description="Opinion on the main statement (1-6: completely disagree to completely agree)",
    )
    opinion_label: Optional[str] = Field(
        None,
        description="Human-readable label for opinion (same 6-point agree–disagree scale)",
    )
    opinion_reason: Optional[str] = Field(
        None,
        description="Open-text explanation for why they agree/disagree",
    )
    statements: Optional[List[BlockStatementItem]] = Field(
        None,
        min_length=7,
        max_length=7,
        description="7 opinion statement responses from the matrix (each 1-6)",
    )
    feeling_strength: Optional[int] = Field(
        None,
        ge=1,
        le=6,
        description="How strongly do you feel about the topic? (1=Not at all, 6=Very strongly)",
    )
    topic_importance: Optional[int] = Field(
        None,
        ge=1,
        le=6,
        description="How important is the topic to you? (1=Not at all, 6=Very important)",
    )


class Demographics(BaseModel):
    """Demographics information"""

    age: Optional[int] = Field(None, ge=18, description="Participant age")
    gender: Optional[str] = Field(None, description="Gender identity")
    education: Optional[str] = Field(
        None, description="Highest level of education"
    )
    kids_in_school: Optional[str] = Field(
        None, description="Do you have kids in school?"
    )
    political_belief: Optional[str] = Field(
        None,
        description=(
            "Raw piped value from Qualtrics (may include ||QBipolarDelim|| between left and right pole labels)"
        ),
    )
    political_belief_left_label: Optional[str] = Field(
        None,
        description="Left pole label when Qualtrics exports bipolar endpoints (split on ||QBipolarDelim||)",
    )
    political_belief_right_label: Optional[str] = Field(
        None,
        description="Right pole label when Qualtrics exports bipolar endpoints",
    )
    political_belief_display: Optional[str] = Field(
        None,
        description="Short display of both poles, e.g. 'Conservative — Progressive'",
    )
    political_belief_scale_position: Optional[int] = Field(
        None,
        ge=1,
        le=6,
        description="Selected position on the bipolar scale (1 toward left pole, 6 toward right); from SelectedAnswerRecode when available",
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

    topic_usage: Optional[str] = Field(
        None,
        description="Topic usage response (e.g., 'How would you describe your use of MS Teams?')",
    )
    topic_behavior: Optional[str] = Field(
        None,
        description="Topic behavior response (e.g., 'How often do you drink water in plastic bottles?')",
    )

    # Randomized block metadata
    pre_block_id: Optional[str] = Field(
        None,
        description="Identifier for the randomized block (e.g., NP_TEAMS, PERS_PLASTIC, CTRL_PE)",
    )
    pre_topic: Optional[str] = Field(
        None,
        description="Topic for the block: 'teams', 'plastic_ban', or 'pe_mandatory'",
    )
    pre_personalization: Optional[str] = Field(
        None,
        description="Personalization condition: 'non_personalized', 'personalized', or 'control'",
    )
    pre_is_control: Optional[bool] = Field(
        None,
        description="Whether the participant is in the control condition",
    )

    # Randomized block responses (opinion + reason + 7 statements + feeling + importance)
    block_responses: Optional[BlockResponses] = Field(
        None,
        description="All responses from the randomized block",
    )

    demographics: Optional[Demographics] = Field(
        None, description="Demographics information"
    )

    survey_comment: Optional[str] = Field(
        None, description="Optional comment at the end of the survey or withdrawal request"
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
    (1-6 scale, completely disagree to completely agree):
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
        min_length=8,
        max_length=8,
        description="8 compulsory Likert questions about the topic (1-6 scale)",
    )

    chatbot_items: List[Survey3Item] = Field(
        ...,
        min_length=8,
        max_length=8,
        description="8 compulsory Likert questions about the chatbot from Survey 2 (1-6 scale)",
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
