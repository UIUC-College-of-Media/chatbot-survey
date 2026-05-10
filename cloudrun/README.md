# Cloud Run Temporary Test Deployment

This directory is for temporary remote test deployments only.

Use this path when you want:
- local integration tests to remain on `kind`
- a temporary HTTPS URL for iframe testing
- to leave `k8s/overlays/production` for a future DevOps-owned GKE production deployment

## Deployment Shape

The Cloud Run service uses two containers:
- `frontend` as the public ingress container
- `backend` as a sidecar reachable from NGINX at `127.0.0.1:8000`

This keeps the frontend `/api/` proxy flow close to the local Kubernetes setup while giving you a single public Cloud Run URL.

## Files

- `deploy.example.env`: copy to `deploy.env` and fill in project, image tags, and runtime env vars
- `service.template.yaml`: Cloud Run multi-container service template rendered from `deploy.env`
- `cloudbuild.backend.yaml`: Cloud Build config for the backend image
- `cloudbuild.frontend.yaml`: Cloud Build config for the Cloud Run frontend image

## First-Time Setup

1. Copy the example env file:

```bash
cp cloudrun/deploy.example.env cloudrun/deploy.env
```

2. Fill in:
- `GCP_PROJECT`
- `CLOUDRUN_REGION`
- `ARTIFACT_REGISTRY_REPOSITORY`
- `CLOUDRUN_SERVICE_NAME`
- `BACKEND_IMAGE_TAG`
- `FRONTEND_IMAGE_TAG`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT`
- `MONGODB_URL`

3. Set `ALLOWED_ORIGINS`:
- for now, use `*` to allow browser access from any embedding origin during temporary testing
- later, tighten this to the actual frontend or embedding origins you want to allow

4. Ensure your MongoDB endpoint is external to `kind`.

Cloud Run cannot reach the `kind` cluster's in-cluster MongoDB service.

## Render And Deploy

```bash
make cloudrun-render
make cloudrun-deploy
```

## Build And Push Images

```bash
make cloudrun-build-backend
make cloudrun-build-frontend
```

These use Google Cloud Build to push images to Artifact Registry.

The build configs are checked in because this repo uses non-root Dockerfiles (`docker/api.Dockerfile` and `docker/frontend.cloudrun.Dockerfile`), and `gcloud builds submit` does not accept a direct `-f` Dockerfile flag.

## Notes

- This path is intentionally separate from `k8s/overlays/production`
- Do not treat this Cloud Run setup as the final production architecture
- Keep `k8s/overlays/local-kind` as the local Kubernetes test path
