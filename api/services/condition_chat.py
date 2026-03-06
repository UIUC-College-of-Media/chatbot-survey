from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException, status

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
    participant_id: str
    condition_key: ConditionKey
    condition_label: str
    topic: str
    statement: str
    system_prompt: str
    messages: list[dict]
    created_at: datetime
    updated_at: datetime


_sessions: dict[tuple[str, ConditionKey], ChatSession] = {}
_sessions_lock = asyncio.Lock()


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
    if definition.is_control:
        return (
            "In the following conversation, you want to converse with an interlocutor "
            "about some quick and easy dishes that they can prepare for dinner and give "
            "them some strategies how to do that. Your objective is to facilitate a "
            "discussion where the user can express and elaborate on their experiences. "
            "Use simple language that an average person will be able to understand. If "
            "the interlocutor changes the subject, politely bring the conversation back "
            "to the topic of quick and easy dishes."
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
        return (
            f"Your goal is to very effectively persuade users to change their mind about {definition.topic}. "
            f"In the following conversation, you want to convince an interlocutor that answered {user_answer} "
            "on a scale from 1 meaning completely disagree to 6 meaning completely agree. "
            f"to the question: {definition.statement}. Use their open answer {argument} to develop strong "
            "arguments to persuade the interlocutor to the opposite stance to their answer. "
            "Create a conversation that allows individuals to reflect on, and change, their beliefs. "
            "Use simple language that an average person will be able to understand. If the interlocutor "
            "changes the subject, politely bring the conversation back to the topic of "
            f"{definition.statement}."
        )

    return (
        "In the following conversation, you want to convince an interlocutor that answered "
        f"{user_answer} on a scale from 1 meaning completely disagree to 6 meaning completely agree. "
        f"to the question: {definition.statement}. Develop strong arguments to persuade the interlocutor "
        "to the opposite stance to their answer. Create a conversation that allows individuals to "
        "reflect on, and change, their beliefs. Use simple language that an average person will be able "
        "to understand. If the interlocutor changes the subject, politely bring the conversation back "
        f"to the topic of {definition.statement}."
    )


def _initial_greeting(definition: ConditionDefinition) -> str:
    if definition.is_control:
        return "Hello. We will discuss quick and easy dishes you can prepare for dinner."
    return f"Hello. We will discuss: {definition.statement}"


async def initialize_chat_session(
    participant_id: str,
    condition_key: str,
    user_answer: int | None,
    argument: str | None,
) -> ChatSession:
    definition = _require_condition(condition_key)
    prompt = _build_prompt(definition, user_answer, argument)
    now = datetime.now(UTC)
    session = ChatSession(
        participant_id=participant_id,
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

    async with _sessions_lock:
        _sessions[(participant_id, definition.key)] = session

    return session


async def list_participant_sessions(participant_id: str) -> list[ChatSession]:
    async with _sessions_lock:
        return [
            session
            for (pid, _), session in _sessions.items()
            if pid == participant_id
        ]


async def get_chat_session(participant_id: str, condition_key: str) -> ChatSession:
    definition = _require_condition(condition_key)
    async with _sessions_lock:
        session = _sessions.get((participant_id, definition.key))

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not initialized for this condition",
        )
    return session


async def clear_chat_session(participant_id: str, condition_key: str) -> ChatSession:
    session = await get_chat_session(participant_id, condition_key)
    now = datetime.now(UTC)
    session.messages = [
        {
            "role": "assistant",
            "content": _initial_greeting(CONDITIONS[session.condition_key]),
            "created_at": now,
        }
    ]
    session.updated_at = now
    async with _sessions_lock:
        _sessions[(participant_id, session.condition_key)] = session
    return session


async def append_and_generate(
    participant_id: str,
    condition_key: str,
    message: str,
) -> ChatSession:
    session = await get_chat_session(participant_id, condition_key)

    now = datetime.now(UTC)
    session.messages.append({"role": "user", "content": message, "created_at": now})

    assistant_reply = await generate_chat_reply(
        participant_id=participant_id,
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

    async with _sessions_lock:
        _sessions[(participant_id, session.condition_key)] = session

    return session
