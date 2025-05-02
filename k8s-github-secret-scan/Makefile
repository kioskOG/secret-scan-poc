# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

WEBHOOK_PORT=8080
LOCAL_PORT=30080
NAMESPACE=secret-scan
WEBHOOK_SERVICE=webhook-service
GITHUB_REPO=https://github.com/kioskOG/secret-scan-poc.git
GITHUB_SECRET=mygithubsecret
DOCKER_REGISTRY=jatin560
BRANCH=main

# ------------------------------------------------------------------------------
# Targets
# ------------------------------------------------------------------------------

.PHONY: all webhook-server-port-forward kafka-ui-port-forward apply delete build help webhook-logs trufflehog-consumer get-pods

apply: ## Apply all K8s manifests from manifests/
	kubectl apply -f manifests/

delete: ## Delete all K8s manifests from manifests/
	kubectl delete -f manifests/

get-pods: ## List pods
	kubectl get po -n $(NAMESPACE)

webhook-server-port-forward: ## Forward localhost:30080 -> webhook service port 8080
	kubectl port-forward svc/$(WEBHOOK_SERVICE) $(LOCAL_PORT):$(WEBHOOK_PORT) -n $(NAMESPACE)

kafka-ui-port-forward: ## Port forward Kafka UI to localhost:8001
	kubectl port-forward svc/kafka-ui 8001:8001 -n $(NAMESPACE)

webhook-logs: ## Show logs for webhook-server deployment
	kubectl logs deploy/webhook-server -n $(NAMESPACE) -f

trufflehog-consumer: ## Show logs for trufflehog-consumer deployment
	kubectl logs deploy/trufflehog-consumer -n $(NAMESPACE) -f

build: ## Build and push Docker images to registry
	docker build -t $(DOCKER_REGISTRY)/webhook-server:latest docker/webhook-server
	docker build -t $(DOCKER_REGISTRY)/trufflehog-consumer:latest docker/consumer
	docker push $(DOCKER_REGISTRY)/webhook-server:latest
	docker push $(DOCKER_REGISTRY)/trufflehog-consumer:latest

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf " \033[36m%-20s\033[0m %s\n", $$1, $$2}'
