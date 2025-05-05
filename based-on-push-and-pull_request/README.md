# 🔐 GitHub Secret Scanning Pipeline on Kubernetes

Migrating GitHub secret scanning pipeline (**TruffleHog + Kafka + Zookeeper + Webhook listener**) to **Kubernetes (K8s)** for better scalability, resilience, and observability.

---

## 📁 Folder Structure

```text
k8s-github-secret-scan/
├── manifests/
│   ├── webhook-deployment.yaml
│   ├── webhook-service.yaml
│   ├── trufflehog-consumer.yaml
│   ├── secrets.yaml          # GitHub Token, Kafka config
│   └── configmap.yaml
├── docker/
│   ├── webhook-server/       # Dockerfile + webhook_listener.py + requirements.txt
│   └── consumer/             # Dockerfile + consumer.py + requirements.txt
├── Makefile                  # Dev and ops automation
└── README.md
```

---

## 1. 🚀 Deploy Kafka & Zookeeper with Helm

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami

helm upgrade --install kafka bitnami/kafka \
  --namespace secret-scan \
  --create-namespace \
  --set service.name=kafka \
  --set controller.replicaCount=3 \
  --set listeners.client.protocol=PLAINTEXT \
  --set configurationOverrides."advertised.listeners"=PLAINTEXT://kafka.secret-scan.svc.cluster.local:9092 \
  --set configurationOverrides."listener.security.protocol.map"=PLAINTEXT:PLAINTEXT \
  --set configurationOverrides."inter.broker.listener.name"=PLAINTEXT \
  --set configurationOverrides."auto.create.topics.enable"=true

helm install zookeeper bitnami/zookeeper --namespace secret-scan
```

> ✅ Expected Pod Status

```bash
kafka-controller-0   1/1     Running   0          4m7s
kafka-controller-1   1/1     Running   0          4m7s
kafka-controller-2   1/1     Running   0          4m7s
zookeeper-0          1/1     Running   0          3m54s
```

---

## 2. 🐳 Build and Push Webhook + Consumer Images

![IMPORTANT]
> Update your `DOCKER_REGISTRY` variable in Makefile

```bash
# Example using Docker Hub or AWS ECR
make build
```

Update the image URLs in the Kubernetes manifests:

- `manifests/webhook-deployment.yaml`
- `manifests/trufflehog-consumer.yaml`

---

## 3. 🧩 Apply Kubernetes Resources

```bash
make apply
```

Verify:
```bash
make get-pods
```

---

## 4. 🧪 Test the Webhook Pipeline

Port-forward the service:
```bash
make webhook-logs
make trufflehog-consumer
```

Access kafka-ui:
```bash
make kafka-ui-port-forward
```

Watch logs:
```bash
make webhook-logs
make trufflehog-consumer
```


![NOTE]
> 
> ```bash
> make help
> ```
---

## 5. 🔍 Visualize with Kafka UI (optional)

Deploy `kafka-ui` as a sidecar service to inspect Kafka topics:

```bash
kubectl apply -f kafka-ui-deployment.yaml
kubectl apply -f kafka-ui-service.yaml
make kafka-ui-port-forward
```

Access: [http://localhost:8001](http://localhost:8001)

---


## ✅ GitHub Repository Changes for Secret Gatekeeper

### 1. 🔒 Enable Branch Protection Rules

Navigate to:
`Settings → Branches → Branch protection rules → Add rule`

**Rule Configuration:**

| Setting                                     | Value                    |
| ------------------------------------------- | ------------------------ |
| **Branch name pattern**                     | `main` (or your default) |
| ✅ Require pull request reviews before merge | ✔️                       |
| ✅ Require status checks to pass             | ✔️                       |
| ✅ Require branches to be up to date         | ✔️                       |
| ✅ Require conversation resolution           | ✔️ *(optional)*          |
| ✅ Status checks that must pass              | `secret-scan`            |
| ✅ Include administrators                    | ✔️ *(recommended)*       |

---

### 2. 🪝 Configure GitHub Webhook

Navigate to:
`Settings → Webhooks → Add webhook`

**Webhook Settings:**

| Field            | Value                                      |
| ---------------- | ------------------------------------------ |
| **Payload URL**  | `http://<your-public-webhook-url>/webhook` |
| **Content type** | `application/json`                         |
| **Secret**       | Must match `GITHUB_SECRET` used in FastAPI |
| **Events**       | ✅ `push` and ✅ `pull_request`              |
| **SSL verify**   | Enabled (or disabled for local testing)    |

---

### 3. 🔑 GitHub Personal Access Token (PAT)

Create a token with these **scopes**:

* `repo:status`
* `repo` (for private repos) or `public_repo` (for public repos)

**Then set as environment variables:**

```bash
export GITHUB_TOKEN=<your_token>
export GITHUB_USER=<your_github_username>
```

---

### 4. 📂 (Optional) Kubernetes Secret for GitHub Credentials

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: github-secret
  namespace: secret-scan
stringData:
  GITHUB_TOKEN: "<your_token>"
  GITHUB_USER: "<your_username>"
  GITHUB_SECRET: "<webhook_secret>"
```

---

✅ After applying the above setup, your GitHub PRs will be blocked from merging until the webhook verifies the PR is free from secrets using TruffleHog + Kafka pipeline.
