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

[!IMPORTANT]
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


[!NOTE]
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

## 📌 Next Steps

- Add Slack/email alerting via webhook
- Scan commits in real-time via TruffleHog
- Integrate CI/CD for auto-scaling and deployment
- Add Helm charts for full Helm-based deployment

