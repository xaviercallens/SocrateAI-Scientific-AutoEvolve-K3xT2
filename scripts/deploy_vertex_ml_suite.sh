#!/bin/bash
# ==============================================================================
# deploy_vertex_ml_suite.sh — Deploy Advanced Parallel ML Suite
# ==============================================================================
# Builds the Docker image and submits a Vertex AI Custom Training Job
# running the Parallel ML Suite (GNN + Symbolic Regression + Neural ODEs)
#
# Usage:
#   chmod +x scripts/deploy_vertex_ml_suite.sh
#   ./scripts/deploy_vertex_ml_suite.sh
# ==============================================================================
set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0625573011}"
REGION="${GCP_REGION:-us-central1}"
REPO_NAME="alphaevolve-k3-t2"
IMAGE_TAG="ml-suite-latest"
IMAGE_URI="gcr.io/${PROJECT_ID}/${REPO_NAME}:${IMAGE_TAG}"
STAGING_BUCKET="gs://socrateai-datalake-gen-lang-client-0625573011/vertex_staging"
JOB_NAME="AlphaEvolve_ML_Suite_$(date +%Y%m%d_%H%M%S)"

echo "======================================================================"
echo "🚀 AlphaEvolve Advanced Parallel ML Suite Deployment"
echo "   Project  : ${PROJECT_ID}"
echo "   Region   : ${REGION}"
echo "   Image    : ${IMAGE_URI}"
echo "   Job Name : ${JOB_NAME}"
echo "======================================================================"

# ── Step 1: Build Image ───────────
echo ""
echo "📦 [1/3] Building Docker image..."
gcloud builds submit \
    --tag "${IMAGE_URI}" \
    --project "${PROJECT_ID}" \
    --timeout=3600 \
    .

echo "✅ Docker image built: ${IMAGE_URI}"

# ── Step 2: Submit Vertex AI Job ────────────────────────────
echo ""
echo "🖥️  [2/3] Submitting Custom Training Job to Vertex AI..."

# By default Dockerfile ENTRYPOINT points to run_phase4_mcmc.py. We override it:
gcloud ai custom-jobs create \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --display-name="${JOB_NAME}" \
    --args="scripts/run_parallel_ml_suite.py" \
    --worker-pool-spec="\
machine-type=g2-standard-8,\
accelerator-type=NVIDIA_L4,\
accelerator-count=1,\
replica-count=1,\
container-image-uri=${IMAGE_URI}" \
    --staging-bucket="${STAGING_BUCKET}" \
    --labels="module=ml_suite,framework=hybrid"

echo ""
echo "======================================================================"
echo "✅ [3/3] Deployment Successful!"
echo "   Vertex AI Console: https://console.cloud.google.com/vertex-ai/training/custom-jobs?project=${PROJECT_ID}"
echo "======================================================================"
