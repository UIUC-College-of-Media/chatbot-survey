# Production Overlay (Private Cluster + GHCR)

This overlay targets a private Kubernetes cluster with:
- ingress-nginx style ingress routing (`ingressClassName: nginx`)
- TLS handled by a standard Kubernetes TLS secret
- backend/frontend images pulled from GitHub Container Registry (GHCR)

## 1) Create env files from examples

```bash
cp k8s/overlays/production/config/backend.production.example.env \
  k8s/overlays/production/config/backend.production.env
cp k8s/overlays/production/secrets/backend.production.example.env \
  k8s/overlays/production/secrets/backend.production.env
```

## 2) Fill required values

- `k8s/overlays/production/config/backend.production.env`
  - `APP_ENV=production`
  - `DATABASE_NAME=...`
  - `AZURE_OPENAI_ENDPOINT=...`
  - `AZURE_OPENAI_DEPLOYMENT=...`
  - `ALLOWED_ORIGINS=https://<your-domain>`
- `k8s/overlays/production/secrets/backend.production.env`
  - `AZURE_OPENAI_API_KEY=...`
  - `MONGODB_URL=...` (expected to point to your externally managed MongoDB)

## 3) Set image tags

Update image tags in:
- `k8s/overlays/production/backend-deployment-patch.yaml`
- `k8s/overlays/production/frontend-deployment-patch.yaml`

Default placeholders:
- `ghcr.io/uiuc-college-of-media/chatbot-survey-backend:latest`
- `ghcr.io/uiuc-college-of-media/chatbot-survey-frontend:latest`

## 4) Set ingress host and TLS secret

Update in `k8s/overlays/production/ingress.yaml`:
- `spec.rules[0].host`
- `spec.tls[0].hosts[0]`
- `spec.tls[0].secretName`

Create the TLS secret in cluster:

```bash
kubectl -n chatbot-survey create secret tls chatbot-survey-tls \
  --cert=/path/to/fullchain.pem \
  --key=/path/to/privkey.pem
```

## 5) Create GHCR pull secret (if images are private)

```bash
kubectl -n chatbot-survey create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<github-token-with-read:packages> \
  --docker-email=<email>
```

## 6) Render and validate

```bash
kubectl kustomize k8s/overlays/production
kubectl apply --dry-run=client -k k8s/overlays/production
```

## 7) Deploy

```bash
kubectl apply -k k8s/overlays/production
kubectl -n chatbot-survey rollout status deploy/backend
kubectl -n chatbot-survey rollout status deploy/frontend
```

## 8) Smoke test

- `GET https://<your-domain>/readyz` -> 200
- `GET https://<your-domain>/api/v1/chat/conditions` -> 200
- Load `https://<your-domain>/?prolific_id=<id>` in browser

## GitHub Actions (Recommended)

Use workflow `.github/workflows/deploy-production.yml`.

Required GitHub **Variables**:
- `K8S_NAMESPACE`: `chatbot-survey` (already set)
- `K8S_OVERLAY`: `k8s/overlays/production` (already set)
- `K8S_INGRESS_HOST`: **(not yet set)**
- `GHCR_BACKEND_IMAGE`: `ghcr.io/uiuc-college-of-media/chatbot-survey-backend` (already set)
- `GHCR_FRONTEND_IMAGE`: `ghcr.io/uiuc-college-of-media/chatbot-survey-frontend` (already set)
- `APP_DATABASE_NAME`: `persuasive_ai_study` (already set)
- `APP_ALLOWED_ORIGINS`: `*` (already set) (will modify to restrict Qualtrics domain only later)
- `AZURE_OPENAI_ENDPOINT`: `https://llm.ncsa.illinois.edu/v1` (already set)
- `AZURE_OPENAI_DEPLOYMENT`: `qwen3-coder-next` (already set)

Required GitHub **Secrets**:
- `KUBE_CONFIG` (kubeconfig content for target cluster) **(not yet set)**
- `MONGODB_URL` **(not yet set)**
- `AZURE_OPENAI_API_KEY` (already set)
- `GHCR_PULL_USERNAME` (already set)
- `GHCR_PULL_TOKEN` (PAT with `read:packages`) (already set)
- `TLS_CERT` (PEM certificate for ingress host) **(not yet set)**
- `TLS_KEY` (PEM private key for ingress host) **(not yet set)**
