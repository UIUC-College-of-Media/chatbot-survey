from datetime import UTC, datetime

from api.models.llm_config import LLMConfigDocument

TTL_SECONDS = 3600

_cached: LLMConfigDocument | None = None
_cached_at: datetime | None = None


async def get_llm_config() -> LLMConfigDocument:
    global _cached, _cached_at
    now = datetime.now(UTC)
    if (
        _cached is None
        or _cached_at is None
        or (now - _cached_at).total_seconds() > TTL_SECONDS
    ):
        config = await LLMConfigDocument.find_one()
        if config is None:
            raise RuntimeError("LLM config not found in database")
        _cached = config
        _cached_at = now
    return _cached
