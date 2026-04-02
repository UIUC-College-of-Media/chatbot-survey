import asyncio
from functools import lru_cache
from typing import Any

from api.config import get_settings


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
    settings = get_settings()
    endpoint = settings.azure_openai_endpoint.strip().rstrip("/")
    api_key = settings.azure_openai_api_key.strip()
    deployment = settings.azure_openai_deployment.strip()

    if not endpoint or not api_key or not deployment:
        if settings.app_env == "production":
            raise RuntimeError("Azure OpenAI configuration is required in production")

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
