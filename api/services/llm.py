import asyncio
import os
from functools import lru_cache
from typing import Any


# One OpenAI client instance per process
@lru_cache(maxsize=1)
def _get_client(base_url: str, api_key: str) -> Any:
    from openai import OpenAI

    return OpenAI(base_url=base_url, api_key=api_key)


def _create_completion(
    client: Any,
    deployment: str,
    system_prompt: str,
    messages: list[dict],
):
    return client.chat.completions.create(
        model=deployment,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        temperature=0.7,
    )


async def generate_chat_reply(
    participant_id: str,
    system_prompt: str,
    messages: list[dict],
) -> str:
    """Generate a chat reply using Azure OpenAI when configured, otherwise return a local mock reply."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip()

    if not endpoint or not api_key or not deployment:
        latest_user_message = next(
            (msg["content"] for msg in reversed(messages) if msg.get("role") == "user"),
            "",
        )
        return f"[mock-reply for {participant_id}] You said: {latest_user_message}"

    client = _get_client(endpoint, api_key)

    completion = await asyncio.to_thread(
        _create_completion, client, deployment, system_prompt, messages
    )
    if not completion.choices:
        raise RuntimeError("Azure OpenAI returned no choices")

    content = completion.choices[0].message.content or ""
    if not content:
        raise RuntimeError("Azure OpenAI returned empty assistant content")

    return content
