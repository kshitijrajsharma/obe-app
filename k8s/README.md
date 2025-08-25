# Kubernetes Deployment on DigitalOcean

## Prerequisites
- DigitalOcean account
- `doctl` CLI installed
- `kubectl` installed

## Quick Deploy

### 1. Create Cluster
```bash
doctl kubernetes cluster create obe-app-cluster --region nyc1 --size s-2vcpu-2gb --count 3
doctl kubernetes cluster kubeconfig save obe-app-cluster
```

### 2. Install Dependencies
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/do/deploy.yaml
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.2/cert-manager.yaml
```

### 3. Configure Secrets
```bash
echo -n 'your-production-secret-key' | base64
echo -n 'your-postgres-password' | base64
```
Update these values in `k8s/configmap.yaml`

### 4. Update Domain
Edit `k8s/ingress.yaml` and replace `yourdomain.com` with your actual domain

### 5. Deploy
```bash
./k8s-deploy.sh
```

### 6. Check Status
```bash
kubectl get pods -n obe-app
kubectl get services -n obe-app
kubectl get ingress -n obe-app
```

## Scaling
```bash
kubectl scale deployment obe-app-web --replicas=4 -n obe-app
kubectl scale deployment obe-app-worker --replicas=2 -n obe-app
```

## Logs
```bash
kubectl logs -f deployment/obe-app-web -n obe-app
kubectl logs -f deployment/obe-app-worker -n obe-app
```

## Updates
```bash
kubectl set image deployment/obe-app-web web=ghcr.io/kshitijrajsharma/obe-app:new-tag -n obe-app
kubectl set image deployment/obe-app-worker worker=ghcr.io/kshitijrajsharma/obe-app:new-tag -n obe-app
```

## Cleanup
```bash
kubectl delete namespace obe-app
doctl kubernetes cluster delete obe-app-cluster
```
