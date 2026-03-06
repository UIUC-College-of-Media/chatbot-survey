import asyncio


async def generate_chat_reply(participant_id: str, messages: list[dict]) -> str:
    """
    Local mock LLM reply used until the real provider API is configured.

    The signature is intentionally provider-agnostic so it can be swapped later.
    """
    await asyncio.sleep(0.05)
    latest_user_message = next(
        (msg["content"] for msg in reversed(messages) if msg.get("role") == "user"),
        "",
    )
    return f"[mock-reply for {participant_id}] You said: {latest_user_message}"
