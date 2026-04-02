from datetime import UTC, datetime

from beanie import Document
from pydantic import BaseModel, Field

from api.schema.survey import (
    BlockResponses,
    Demographics,
    Survey1Request,
)


class SurveyPreBlock(BaseModel):
    block_id: str | None = None
    topic: str | None = None
    personalization: str | None = None
    is_control: bool | None = None
    responses: BlockResponses | None = None


class Survey1Document(Document):
    participant_id: str
    prolific_id: str | None = None
    qualtrics_response_id: str | None = None
    topic_condition: str

    topic_usage: str | None = None
    topic_behavior: str | None = None

    demographics: Demographics | None = None
    survey_comment: str | None = None

    pre_block: SurveyPreBlock | None = None

    survey_completion_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ip_address: str | None = None
    user_agent: str | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    survey_type: str = "survey1_baseline"
    week: int = 0

    class Settings:
        name = "survey1_responses"
        indexes = ["prolific_id", "participant_id"]

    @classmethod
    def from_request(cls, survey_data: Survey1Request) -> "Survey1Document":
        pre_block = None
        if (
            survey_data.pre_block_id is not None
            or survey_data.pre_topic is not None
            or survey_data.pre_personalization is not None
            or survey_data.pre_is_control is not None
            or survey_data.block_responses is not None
        ):
            pre_block = SurveyPreBlock(
                block_id=survey_data.pre_block_id,
                topic=survey_data.pre_topic,
                personalization=survey_data.pre_personalization,
                is_control=survey_data.pre_is_control,
                responses=survey_data.block_responses,
            )

        return cls(
            participant_id=survey_data.participant_id,
            prolific_id=survey_data.prolific_id,
            qualtrics_response_id=survey_data.qualtrics_response_id,
            topic_condition=survey_data.topic_condition,
            topic_usage=survey_data.topic_usage,
            topic_behavior=survey_data.topic_behavior,
            demographics=survey_data.demographics,
            survey_comment=survey_data.survey_comment,
            pre_block=pre_block,
            survey_completion_time=survey_data.survey_completion_time or datetime.now(UTC),
            ip_address=survey_data.ip_address,
            user_agent=survey_data.user_agent,
        )
