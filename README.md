# Chatbot Survey Demo

## Current Architecture
This project runs 3 services:
- `frontend` (React built and served by NGINX)
- `backend` (FastAPI)
- `mongodb` (MongoDB 7)

Core flow:
- `POST /api/v1/survey1` stores pre-survey responses.
- `GET /api/v1/chat/start?prolific_id=...` creates/reuses exactly one chat session per `prolific_id`.
- Chat sessions persist in MongoDB (`chat_sessions`).

## Kubernetes Structure (Kustomize)
- `k8s/base`: shared manifests (backend, frontend, mongodb)
- `k8s/overlays/local-kind`: local testing settings for kind
- `k8s/overlays/production`: private-cluster production overlay using ingress routing
- `k8s/kind/cluster.yaml`: kind cluster config with host port mappings

## Temporary Remote Testing On Cloud Run

Use `cloudrun/` for temporary shared deployments.

This keeps responsibilities split:
- `kind` + local Kustomize overlays stay as the developer-owned local Kubernetes path
- `cloudrun/` provides a temporary HTTPS deployment path for remote testing
- `k8s/overlays/production` is the private-cluster production path (GHCR images + ingress)

Cloud Run files:
- `cloudrun/service.template.yaml`
- `cloudrun/deploy.example.env`
- `cloudrun/README.md`

Cloud Run build/deploy commands:

```bash
cp cloudrun/deploy.example.env cloudrun/deploy.env
make cloudrun-build-backend
make cloudrun-build-frontend
make cloudrun-deploy
```

## Requirements
- Docker
- `kind`
- `kubectl`
- `make`

## Local kind Setup (Browser-testable)
0. Prepare local secret env files (kept out of git):

```bash
cp k8s/overlays/local-kind/secrets/backend.local.example.env k8s/overlays/local-kind/secrets/backend.local.env
cp k8s/overlays/local-kind/secrets/mongodb.local.example.env k8s/overlays/local-kind/secrets/mongodb.local.env
```

Important: in `*.env` files, use `KEY=value` with no surrounding quotes.

Fast path (one command):

```bash
make kind-bootstrap
```

This runs:
- cluster creation
- image build
- image load into kind
- local overlay deploy
- rollout wait
- sample Survey 1 seed request

Step-by-step (if you want manual control):

```bash
make kind-up
make kind-build
make kind-load
make kind-deploy
make kind-wait
make kind-seed
```

When local env/config changes (including secrets), run:

```bash
make kind-apply
```

No manual `rollout restart` is needed in this workflow.

When backend/frontend code changes, run:

```bash
make kind-refresh
```

For one service only:

```bash
make kind-refresh-backend
make kind-refresh-frontend
```

Open app in browser:

```text
http://localhost:30080/?prolific_id=prolific-001
```

## Local Testing Steps
1. Submit Survey 1 first (required before chat can start).

If you already ran `make kind-bootstrap`, this is already done by `make kind-seed`.

Manual command:

```bash
curl -X POST http://localhost:30081/api/v1/survey1 \
  -H "Content-Type: application/json" \
  -d '{
    "participant_id": "participant-001",
    "prolific_id": "prolific-001",
    "qualtrics_response_id": "R_TEST_001",
    "topic_condition": "teams",
    "topic_usage": "daily",
    "topic_behavior": "often",
    "pre_block_id": "PERS_TEAMS",
    "pre_topic": "teams",
    "pre_personalization": "personalized",
    "pre_is_control": false,
    "block_responses": {
      "opinion": 2,
      "opinion_reason": "I do not like using Teams.",
      "statements": [
        {"statement_id":"stmt1","response":3},
        {"statement_id":"stmt2","response":3},
        {"statement_id":"stmt3","response":3},
        {"statement_id":"stmt4","response":3},
        {"statement_id":"stmt5","response":3},
        {"statement_id":"stmt6","response":3},
        {"statement_id":"stmt7","response":3}
      ],
      "feeling_strength": 4,
      "topic_importance": 4
    }
  }'
```

2. Visit frontend with the same `prolific_id`:

```text
http://localhost:30080/?prolific_id=prolific-001
```

Expected result:
- Chat page loads.
- Backend creates/reuses session via `/api/v1/chat/start`.
- Chat send/reset flows work in UI.
- Manual `POST /api/v1/chat/send` calls must include `client_message_id` (idempotency key).

## Production Overlay

`k8s/overlays/production` is the production deployment path for private clusters.
For setup, variables/secrets, and deploy steps, follow:
- [Production Deployment Guide](k8s/overlays/production/README.md)

CI/CD option:
- GitHub Actions workflow: `.github/workflows/deploy-production.yml`
- Expected GitHub vars/secrets are documented in `k8s/overlays/production/README.md`.

## Recommended Testing Tools
- **Postman**
  - Why: fast request replay and payload management.
  - How: import `tests/chatbot_survey.postman_collection.json`.

- **MongoDB Compass**
  - Why: verify persistence and inspect chat/session docs.
  - How: first run `kubectl -n chatbot-survey-local port-forward statefulset/mongodb 27017:27017`, then connect to `mongodb://mongouser:localdevpassword@localhost:27017/?authSource=admin` and inspect `survey1_responses` + `chat_sessions`.

- **stern**
  - Why: tail logs across multiple pods/containers during rollout and runtime debugging.
  - How: run `stern . -n chatbot-survey-local` to stream logs from all local services.

## Automated Unit Tests

```bash
python3 -m unittest tests/test_api.py tests/test_chat_api.py
```

## Useful Make Targets

```bash
make help
make kind-apply
make kind-refresh
make kind-refresh-backend
make kind-refresh-frontend
make kind-status
make local-url
make kind-down
```
