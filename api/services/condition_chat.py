from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException, status

from api.config import get_settings
from api.prompts.loader import render_prompt
from api.services.llm import generate_chat_reply

ConditionKey = Literal[
    "teams_personalized",
    "teams_non_personalized",
    "plastic_personalized",
    "plastic_non_personalized",
    "pe_personalized",
    "pe_non_personalized",
    "control",
]


@dataclass(frozen=True)
class ConditionDefinition:
    key: ConditionKey
    label: str
    topic: str
    statement: str
    personalized: bool
    is_control: bool


CONDITIONS: dict[ConditionKey, ConditionDefinition] = {
    "teams_personalized": ConditionDefinition(
        key="teams_personalized",
        label="MS Teams (Personalized)",
        topic="MS Teams",
        statement="MS Teams is the most effective collaboration app on the market",
        personalized=True,
        is_control=False,
    ),
    "teams_non_personalized": ConditionDefinition(
        key="teams_non_personalized",
        label="MS Teams (Non-personalized)",
        topic="MS Teams",
        statement="MS Teams is the most effective collaboration app on the market",
        personalized=False,
        is_control=False,
    ),
    "plastic_personalized": ConditionDefinition(
        key="plastic_personalized",
        label="Plastic Water Bottle Ban (Personalized)",
        topic="ban on plastic water bottles",
        statement="Plastic water bottles should be banned",
        personalized=True,
        is_control=False,
    ),
    "plastic_non_personalized": ConditionDefinition(
        key="plastic_non_personalized",
        label="Plastic Water Bottle Ban (Non-personalized)",
        topic="ban on plastic water bottles",
        statement="Plastic water bottles should be banned",
        personalized=False,
        is_control=False,
    ),
    "pe_personalized": ConditionDefinition(
        key="pe_personalized",
        label="Mandatory Physical Education (Personalized)",
        topic="mandatory physical education in schools",
        statement="Physical education should be mandatory in schools",
        personalized=True,
        is_control=False,
    ),
    "pe_non_personalized": ConditionDefinition(
        key="pe_non_personalized",
        label="Mandatory Physical Education (Non-personalized)",
        topic="mandatory physical education in schools",
        statement="Physical education should be mandatory in schools",
        personalized=False,
        is_control=False,
    ),
    "control": ConditionDefinition(
        key="control",
        label="Control",
        topic="quick and easy dishes",
        statement="quick and easy dishes",
        personalized=False,
        is_control=True,
    ),
}


@dataclass
class ChatSession:
    prolific_id: str
    condition_key: ConditionKey
    condition_label: str
    topic: str
    statement: str
    system_prompt: str
    messages: list[dict]
    created_at: datetime
    updated_at: datetime


def condition_metadata() -> list[dict]:
    items = []
    for definition in CONDITIONS.values():
        items.append(
            {
                "key": definition.key,
                "label": definition.label,
                "topic": definition.topic,
                "statement": definition.statement,
                "personalized": definition.personalized,
                "is_control": definition.is_control,
                "requires_user_answer": not definition.is_control,
                "requires_argument": definition.personalized,
            }
        )
    return items


def _require_condition(condition_key: str) -> ConditionDefinition:
    try:
        return CONDITIONS[condition_key]  # type: ignore[index]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown condition_key: {condition_key}",
        ) from exc


def _build_prompt(
    definition: ConditionDefinition,
    user_answer: int | None,
    argument: str | None,
) -> str:
    settings = get_settings()
    version = settings.prompt_version.strip() or "v1"

    if definition.is_control:
        return render_prompt(
            version=version,
            template_name="control",
        )

    if user_answer is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="user_answer is required for this condition",
        )

    if definition.personalized:
        if not argument or not argument.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="argument is required for personalized conditions",
            )
        return render_prompt(
            version=version,
            template_name="persuasion_personalized",
            topic=definition.topic,
            statement=definition.statement,
            user_answer=user_answer,
            argument=argument.strip(),
        )

    return render_prompt(
        version=version,
        template_name="persuasion_non_personalized",
        statement=definition.statement,
        user_answer=user_answer,
    )


def _initial_greeting(definition: ConditionDefinition) -> str:
    if definition.is_control:
        return "Hello. We will discuss quick and easy dishes you can prepare for dinner."
    return f"Hello. We will discuss: {definition.statement}"


def initialize_chat_session(
    prolific_id: str,
    condition_key: str,
    user_answer: int | None,
    argument: str | None,
) -> ChatSession:
    definition = _require_condition(condition_key)
    prompt = _build_prompt(definition, user_answer, argument)
    now = datetime.now(UTC)
    return ChatSession(
        prolific_id=prolific_id,
        condition_key=definition.key,
        condition_label=definition.label,
        topic=definition.topic,
        statement=definition.statement,
        system_prompt=prompt,
        messages=[
            {
                "role": "assistant",
                "content": _initial_greeting(definition),
                "created_at": now,
            }
        ],
        created_at=now,
        updated_at=now,
    )


def clear_chat_session(session: ChatSession) -> ChatSession:
    now = datetime.now(UTC)
    session.messages = [
        {
            "role": "assistant",
            "content": _initial_greeting(CONDITIONS[session.condition_key]),
            "created_at": now,
        }
    ]
    session.updated_at = now
    return session


async def append_and_generate(session: ChatSession, message: str) -> ChatSession:
    now = datetime.now(UTC)
    session.messages.append({"role": "user", "content": message, "created_at": now})

    assistant_reply = await generate_chat_reply(
        participant_id=session.prolific_id,
        system_prompt=session.system_prompt,
        messages=[
            {"role": msg["role"], "content": msg["content"]}
            for msg in session.messages
        ],
    )

    session.messages.append(
        {
            "role": "assistant",
            "content": assistant_reply,
            "created_at": datetime.now(UTC),
        }
    )
    session.updated_at = datetime.now(UTC)
    return session
