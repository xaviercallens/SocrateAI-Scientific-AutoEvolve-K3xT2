#!/bin/bash
# Deploy AlphaEvolve to GKE with Redis Ledger & HPA
set -e

echo "=========================================================="
echo " Deploying AlphaEvolve K3xT2 Distributed Scale (GKE)"
echo "=========================================================="

kubectl create namespace alpha-evolve --dry-run=client -o yaml | kubectl apply -f -

echo "Deploying Redis Ledger StatefulSet..."
kubectl apply -f gcp_infrastructure/k8s/redis-ledger.yaml

echo "Deploying AlphaEvolve Worker & HPA..."
kubectl apply -f gcp_infrastructure/k8s/alpha-evolve-worker.yaml

echo "Deploying Prometheus ServiceMonitors..."
kubectl apply -f gcp_infrastructure/k8s/prometheus-servicemonitor.yaml

echo "=========================================================="
echo "Deployment initiated."
echo "To monitor autoscaling, run: kubectl get hpa -n alpha-evolve"
echo "To check pod status, run: kubectl get pods -n alpha-evolve"
echo "=========================================================="
