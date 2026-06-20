from functools import lru_cache
from typing import Any, AsyncGenerator

from api.services.llm_config_cache import get_llm_config


@lru_cache(maxsize=4)
def _get_async_client(base_url: str, api_key: str) -> Any:
    from openai import AsyncOpenAI

    return AsyncOpenAI(base_url=base_url, api_key=api_key)


async def stream_chat_reply(
    system_prompt: str,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Stream tokens from the LLM using AsyncOpenAI."""
    config = await get_llm_config()
    endpoint = config.llm_model_endpoint.strip().rstrip("/")
    api_key = config.llm_model_api_key.strip()
    deployment = config.llm_model_deployment.strip()

    if not all([endpoint, api_key, deployment]):
        raise RuntimeError("LLM config is incomplete")

    client = _get_async_client(endpoint, api_key)
    stream = await client.chat.completions.create(
        model=deployment,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        temperature=0.7,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            yield delta.content
