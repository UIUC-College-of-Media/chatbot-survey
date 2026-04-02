# Repository Guidelines

## Project Structure & Module Organization
- `api/` contains the FastAPI application. The main entry point is `api/main.py`, which defines models, routes, and MongoDB access.
- `frontend/` is reserved for the UI. `frontend/index.html` exists but is currently empty.
- `docker/` is reserved for container assets. `docker/api.Dockerfile` exists but is currently empty.
- `requirements.txt` pins Python dependencies for the API.

## Build, Test, and Development Commands
- `python -m venv .venv` and `source .venv/bin/activate` to create and activate a local virtual environment.
- `pip install -r requirements.txt` to install API dependencies.
- `uvicorn api.main:app --reload` to run the API locally with auto-reload.
- `MONGODB_URL=mongodb://localhost:27017 uvicorn api.main:app --reload` to point at a local MongoDB instance.

## Coding Style & Naming Conventions
- Python: 4-space indentation, PEP 8 naming (`snake_case` for functions/variables, `PascalCase` for classes).
- Pydantic models live in `api/main.py` and use explicit `Field(...)` definitions with validation.
- Prefer explicit, descriptive names for survey fields (match the survey schema).
- No formatter or linter is configured yet; keep changes small and consistent with existing patterns.

## Testing Guidelines
- No automated tests are present. If you add tests, mirror the app structure (e.g., `tests/test_api.py`) and document the command you used (e.g., `pytest`).
- Prefer validating API behavior with FastAPI’s `TestClient` when you introduce tests.

## Commit & Pull Request Guidelines
- Commit messages in history use short, imperative-style phrases (e.g., “Updated fields to completely match survey”). Follow that pattern and keep messages one line.
- PRs should describe the change, note any schema or API contract impacts, and include a brief validation note (e.g., “Ran `uvicorn api.main:app --reload` and hit `/health`”).
- Include screenshots only if you modify the UI in `frontend/`.

## Configuration & Data
- The API reads `MONGODB_URL` and `DATABASE_NAME` from environment variables. Defaults are `mongodb://localhost:27017` and `persuasive_ai_study`.
- Do not commit secrets or production connection strings. Use `.env` locally; `python-dotenv` is already in use.
