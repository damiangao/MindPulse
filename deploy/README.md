# MindPulse Deployment Guide

## Prerequisites

- Docker & Docker Compose v2+
- Kubernetes v1.28+ (for K8s deployment)
- kubectl configured for your cluster

## Local Development with Docker

```bash
# Copy and configure environment
cp deploy/.env.docker .env
# Edit .env with your API keys

# Start services (production-like)
docker compose -f deploy/docker-compose.yml up --build

# Or start with hot-reload for development
docker compose -f deploy/docker-compose.dev.yml up --build
```

Access the app at http://localhost:8080

## Production Docker Deployment

```bash
# Build images
docker compose -f deploy/docker-compose.yml build

# Run services
docker compose -f deploy/docker-compose.yml up -d

# Check logs
docker compose -f deploy/docker-compose.yml logs -f

# Stop services
docker compose -f deploy/docker-compose.yml down
```

## Kubernetes Deployment

### Prerequisites

- A Kubernetes cluster (minikube, kind, EKS, GKE, etc.)
- nginx-ingress controller installed
- kubectl configured

### Deploy

```bash
# Navigate to k8s directory
cd deploy/k8s

# Edit secret.yaml with your actual credentials
# Replace ${ANTHROPIC_API_KEY} and ${JWT_SECRET} with real values

# Apply all resources
kubectl apply -k .

# Or apply individually
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml  # After editing with real values
kubectl apply -f backend-deployment.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f ingress.yaml

# Check status
kubectl get pods -n mindpulse
kubectl get services -n mindpulse
kubectl get ingress -n mindpulse
```

### Build and Push Images

```bash
# Build server image
docker build -t mindpulse-server:latest -f deploy/Dockerfile.server .

# Build client image
docker build -t mindpulse-client:latest -f deploy/Dockerfile.client .

# Tag for registry (example)
docker tag mindpulse-server:latest your-registry/mindpulse-server:latest
docker tag mindpulse-client:latest your-registry/mindpulse-client:latest

# Push to registry
docker push your-registry/mindpulse-server:latest
docker push your-registry/mindpulse-client:latest

# Update deployment files with your registry
```

### Update Images in K8s

```bash
# After pushing new images
kubectl set image deployment/mindpulse-server server=mindpulse-server:latest -n mindpulse
kubectl set image deployment/mindpulse-client client=mindpulse-client:latest -n mindpulse

# Check rollout
kubectl rollout status deployment/mindpulse-server -n mindpulse
kubectl rollout status deployment/mindpulse-client -n mindpulse
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| ANTHROPIC_API_KEY | Yes | - | Anthropic API key |
| ANTHROPIC_BASE_URL | No | https://api.minimax.io | API base URL |
| MODEL | No | MiniMax-M2.7 | Model to use |
| PORT | No | 3001 | Backend server port |
| JWT_SECRET | Yes | - | JWT signing secret (min 32 bytes) |
| JWT_EXPIRE_HOURS | No | 24 | Token expiry time |

### Resource Limits

The default resource limits are set for small-to-medium deployments:
- **Server**: 256Mi-512Mi memory, 250m-500m CPU
- **Client**: 64Mi-128Mi memory, 50m-100m CPU

Adjust these based on your workload.

## Troubleshooting

### Server won't start

```bash
# Check logs
docker compose logs server

# Verify environment variables
docker compose exec server env
```

### WebSocket connection issues

Ensure the ingress is configured for WebSocket (included in the provided ingress.yaml)

### Database issues

SQLite database is stored in `/app/data` inside the container. For production, consider:
1. Using a persistent volume
2. Migrating to PostgreSQL

```yaml
# Example: Adding persistent volume to docker-compose
volumes:
  server-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/local/data
```
