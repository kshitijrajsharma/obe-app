#!/bin/bash
set -e

NAMESPACE="obe-app"

echo "Applying Kubernetes manifests..."

kubectl apply -f k8s/namespace.yaml

echo "Update secrets in k8s/configmap.yaml before applying"
echo "Run: echo -n 'your-secret-key' | base64"
echo "Run: echo -n 'your-postgres-password' | base64"
read -p "Press enter when secrets are updated..."

kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/storage.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml

echo "Waiting for database to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s

echo "Running migrations..."
kubectl run --rm -i --tty migrate --image=ghcr.io/kshitijrajsharma/obe-app:latest --restart=Never -n $NAMESPACE \
  --env="SECRET_KEY=$(kubectl get secret obe-app-secrets -n $NAMESPACE -o jsonpath='{.data.SECRET_KEY}' | base64 -d)" \
  --env="DATABASE_URL=postgis://postgres:$(kubectl get secret obe-app-secrets -n $NAMESPACE -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d)@postgres:5432/obe_app" \
  --env="DEBUG=false" \
  -- python manage.py migrate

kubectl apply -f k8s/web.yaml
kubectl apply -f k8s/worker.yaml

echo "Update domain in k8s/ingress.yaml"
read -p "Press enter when domain is updated..."
kubectl apply -f k8s/ingress.yaml

echo "Deployment complete!"
echo "Check status: kubectl get pods -n $NAMESPACE"
