# Chatbot Survey Demo

This repo includes:
- Survey 1 backend API (`/api/v1/survey1`)
- A condition-based chat app with 7 prompt setups, for survey 2
- Frontend served by FastAPI at `/`

**Note:** The chat app is only for demoing, and is subject to change anytime.

## Requirements

- Python 3.12+
- MongoDB

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables
Export env variables, or create a .env file locally.

Optional for real Azure OpenAI chat. If not set, chat uses a mock reply.

```bash
export AZURE_OPENAI_ENDPOINT="https://<your-resource>.openai.azure.com/openai/v1"
export AZURE_OPENAI_API_KEY="<your-api-key>"
export AZURE_OPENAI_DEPLOYMENT="<your-chat-deployment-name>"
```

MongoDB settings:

```bash
export MONGODB_URL="mongodb://localhost:27017"
export DATABASE_NAME="persuasive_ai_study"
```

## Run

```bash
python3 -m uvicorn api.main:app --reload
```

Open:
- Setup page: `http://localhost:8000/`
- Chat page format: `http://localhost:8000/?participant_id=participant-123`

## Demo Flow

1. Visit `/` without `participant_id`.
2. Choose one of 7 conditions, provide required inputs, and initialize.
3. App redirects to `?participant_id=participant-123&condition_key=<selected>`.
4. In chat mode, initialize additional conditions, switch between them, and clear per-condition history.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```
