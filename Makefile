SHELL := /bin/sh

CLUSTER_NAME ?= chatbot-survey-cluster
NAMESPACE ?= chatbot-survey-local
LOCAL_PROLIFIC_ID ?= prolific-001
ROLLOUT_TIMEOUT ?= 120s

.PHONY: help kind-up kind-down kind-build kind-load kind-build-backend kind-build-frontend kind-load-backend kind-load-frontend kind-deploy kind-apply kind-wait kind-wait-backend kind-wait-frontend kind-restart-backend kind-restart-frontend kind-refresh-backend kind-refresh-frontend kind-refresh kind-seed kind-status kind-bootstrap local-url cloudrun-render cloudrun-build-backend cloudrun-build-frontend cloudrun-deploy

help:
	@echo "Available targets:"
	@echo "  make kind-up         # Create local kind cluster"
	@echo "  make kind-build      # Build backend/frontend local images"
	@echo "  make kind-load       # Load local images into kind cluster"
	@echo "  make kind-refresh    # Rebuild+load+restart backend/frontend and wait"
	@echo "  make kind-refresh-backend   # Rebuild+load+restart backend and wait"
	@echo "  make kind-refresh-frontend  # Rebuild+load+restart frontend and wait"
	@echo "  make kind-deploy     # Apply local-kind kustomize overlay"
	@echo "  make kind-apply      # Re-apply overlay (for env/config updates) and wait"
	@echo "  make kind-restart-backend   # Restart backend deployment and wait"
	@echo "  make kind-restart-frontend  # Restart frontend deployment and wait"
	@echo "  make kind-wait       # Wait for backend/frontend/mongodb rollout"
	@echo "  make kind-seed       # Submit a sample Survey1 payload"
	@echo "  make kind-status     # Show pods/services in local namespace"
	@echo "  make kind-bootstrap  # Run full local bootstrap (up+build+load+deploy+wait+seed)"
	@echo "  make local-url       # Print browser URL"
	@echo "  make kind-down       # Delete kind cluster"
	@echo "  make cloudrun-render # Render Cloud Run YAML from cloudrun/deploy.env"
	@echo "  make cloudrun-build-backend  # Build+push backend image with Cloud Build"
	@echo "  make cloudrun-build-frontend # Build+push frontend image with Cloud Build"
	@echo "  make cloudrun-deploy # Deploy rendered Cloud Run service"

kind-up:
	kind create cluster --name $(CLUSTER_NAME) --config k8s/kind/cluster.yaml

kind-down:
	kind delete cluster --name $(CLUSTER_NAME)

kind-build:
	$(MAKE) kind-build-backend
	$(MAKE) kind-build-frontend

kind-build-backend:
	docker build -t chatbot-survey-api:local -f docker/api.Dockerfile .

kind-build-frontend:
	docker build -t chatbot-survey-frontend:local -f docker/frontend.Dockerfile .

kind-load:
	$(MAKE) kind-load-backend
	$(MAKE) kind-load-frontend

kind-load-backend:
	kind load docker-image chatbot-survey-api:local --name $(CLUSTER_NAME)

kind-load-frontend:
	kind load docker-image chatbot-survey-frontend:local --name $(CLUSTER_NAME)

kind-deploy:
	kubectl apply -k k8s/overlays/local-kind

kind-apply:
	kubectl apply -k k8s/overlays/local-kind
	$(MAKE) kind-wait

kind-wait:
	$(MAKE) kind-wait-backend
	$(MAKE) kind-wait-frontend
	kubectl -n $(NAMESPACE) rollout status statefulset/mongodb --timeout=$(ROLLOUT_TIMEOUT)

kind-wait-backend:
	kubectl -n $(NAMESPACE) rollout status deploy/backend --timeout=$(ROLLOUT_TIMEOUT)

kind-wait-frontend:
	kubectl -n $(NAMESPACE) rollout status deploy/frontend --timeout=$(ROLLOUT_TIMEOUT)

kind-restart-backend:
	kubectl -n $(NAMESPACE) rollout restart deploy/backend
	$(MAKE) kind-wait-backend

kind-restart-frontend:
	kubectl -n $(NAMESPACE) rollout restart deploy/frontend
	$(MAKE) kind-wait-frontend

kind-refresh-backend:
	$(MAKE) kind-build-backend
	$(MAKE) kind-load-backend
	$(MAKE) kind-restart-backend

kind-refresh-frontend:
	$(MAKE) kind-build-frontend
	$(MAKE) kind-load-frontend
	$(MAKE) kind-restart-frontend

kind-refresh:
	$(MAKE) kind-refresh-backend
	$(MAKE) kind-refresh-frontend
	$(MAKE) kind-status

kind-seed:
	curl -X POST http://localhost:30081/api/v1/survey1 \
	  -H "Content-Type: application/json" \
	  -d '{"participant_id":"participant-001","prolific_id":"$(LOCAL_PROLIFIC_ID)","qualtrics_response_id":"R_TEST_001","topic_condition":"teams","topic_usage":"daily","topic_behavior":"often","pre_block_id":"PERS_TEAMS","pre_topic":"teams","pre_personalization":"personalized","pre_is_control":false,"block_responses":{"opinion":2,"opinion_reason":"I do not like using Teams.","statements":[{"statement_id":"stmt1","response":3},{"statement_id":"stmt2","response":3},{"statement_id":"stmt3","response":3},{"statement_id":"stmt4","response":3},{"statement_id":"stmt5","response":3},{"statement_id":"stmt6","response":3},{"statement_id":"stmt7","response":3}],"feeling_strength":4,"topic_importance":4}}'

kind-status:
	kubectl -n $(NAMESPACE) get pods
	kubectl -n $(NAMESPACE) get svc

kind-bootstrap: kind-up kind-build kind-load kind-deploy kind-wait kind-seed
	@echo "Local setup ready."

local-url:
	@echo "http://localhost:30080/?prolific_id=$(LOCAL_PROLIFIC_ID)"

cloudrun-render:
	@test -f cloudrun/deploy.env || (echo "Missing cloudrun/deploy.env; copy cloudrun/deploy.example.env first." && exit 1)
	@set -a; while IFS= read -r line; do case "$$line" in ''|\#*) continue ;; esac; key=$${line%%=*}; value=$${line#*=}; export "$$key=$$value"; done < cloudrun/deploy.env; envsubst < cloudrun/service.template.yaml > cloudrun/service.yaml
	@echo "Rendered cloudrun/service.yaml"

cloudrun-build-backend:
	@test -f cloudrun/deploy.env || (echo "Missing cloudrun/deploy.env; copy cloudrun/deploy.example.env first." && exit 1)
	@set -a; while IFS= read -r line; do case "$$line" in ''|\#*) continue ;; esac; key=$${line%%=*}; value=$${line#*=}; export "$$key=$$value"; done < cloudrun/deploy.env; IMAGE=$$CLOUDRUN_REGION-docker.pkg.dev/$$GCP_PROJECT/$$ARTIFACT_REGISTRY_REPOSITORY/chatbot-survey-api:$$BACKEND_IMAGE_TAG; gcloud builds submit --config cloudrun/cloudbuild.backend.yaml --substitutions=_IMAGE=$$IMAGE .

cloudrun-build-frontend:
	@test -f cloudrun/deploy.env || (echo "Missing cloudrun/deploy.env; copy cloudrun/deploy.example.env first." && exit 1)
	@set -a; while IFS= read -r line; do case "$$line" in ''|\#*) continue ;; esac; key=$${line%%=*}; value=$${line#*=}; export "$$key=$$value"; done < cloudrun/deploy.env; IMAGE=$$CLOUDRUN_REGION-docker.pkg.dev/$$GCP_PROJECT/$$ARTIFACT_REGISTRY_REPOSITORY/chatbot-survey-frontend:$$FRONTEND_IMAGE_TAG; gcloud builds submit --config cloudrun/cloudbuild.frontend.yaml --substitutions=_IMAGE=$$IMAGE .

cloudrun-deploy: cloudrun-render
	@test -f cloudrun/deploy.env || (echo "Missing cloudrun/deploy.env; copy cloudrun/deploy.example.env first." && exit 1)
	@set -a; while IFS= read -r line; do case "$$line" in ''|\#*) continue ;; esac; key=$${line%%=*}; value=$${line#*=}; export "$$key=$$value"; done < cloudrun/deploy.env; gcloud run services replace cloudrun/service.yaml --region $$CLOUDRUN_REGION --project $$GCP_PROJECT
