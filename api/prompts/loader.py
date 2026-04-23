from __future__ import annotations

from pathlib import Path


def _prompts_root() -> Path:
    # backend/api/prompts/loader.py -> backend/api/prompts
    return Path(__file__).resolve().parent


def render_prompt(*, version: str, template_name: str, **kwargs: object) -> str:
    """
    Load `backend/api/prompts/{version}/{template_name}.md` and substitute placeholders.

    Placeholders use Python's `str.format`, e.g. {topic}, {statement}, {user_answer}, {argument}.
    """
    path = _prompts_root() / version / f"{template_name}.md"
    template = path.read_text(encoding="utf-8")
    try:
        rendered = template.format(**kwargs)
    except KeyError as exc:
        raise KeyError(f"Missing placeholder for prompt template {path}: {exc}") from exc
    return rendered.strip() + "\n"

