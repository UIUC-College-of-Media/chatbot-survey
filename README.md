# Chatbot Survey Local MVP

This repo now contains:
- Survey 1 backend endpoint support
- Survey 2 chat backend (`/api/v1/chat/*`), and a simple frontend chat UI (`frontend/index.html`)
- Mongo-backed chat history and participant validation

## Survey 1

Current survey feature endpoints (baseline survey):
- `POST /api/v1/survey1`
- `GET /health`
- `GET /`

## Survey 2

Current chat service (local MVP):
- `POST /api/v1/chat/send`
- `GET /api/v1/chat/history/{participant_id}`
- `POST /api/v1/chat/reset/{participant_id}` (development helper)

Rules:
- One chat session per `participant_id`
- `participant_id` must exist in `participants`
- Chat history persists in MongoDB `chat_messages`
- The frontend disables input while a reply is being generated

## Survey 3

No endpoints/services are implemented yet in this repo.

## Local Run (No Kubernetes)

1. Start MongoDB (Docker example)
```bash
docker run --name chatbot-survey-mongo -p 27017:27017 -d mongo:7
```

2. Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Seed participants (This is to put fake participant test data in local MongoDB)
```bash
python3 scripts/seed_participants.py
```

4. Run the API
```bash
MONGODB_URL=mongodb://localhost:27017 uvicorn api.main:app --reload
```

5. Serve the frontend (in another terminal)
```bash
python3 -m http.server 8080 -d frontend
```

6. Open the chat UI
```text
http://localhost:8080/index.html?participant_id=participant-123
```
