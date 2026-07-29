#!/bin/bash
# ==============================================================================
# deploy_vertex_job.sh — Phase 3 AlphaEvolve K3×T² Deep Burn (Stream 5)
# ==============================================================================
# Builds the hybrid Lean 4 + Python Docker image via Google Cloud Build,
# then submits a Vertex AI Custom Training Job on an NVIDIA T4 GPU node.
#
# Usage:
#   chmod +x scripts/deploy_vertex_job.sh
#   ./scripts/deploy_vertex_job.sh
#
# Prerequisites:
#   - gcloud CLI authenticated:  gcloud auth login
#   - Application Default Creds: gcloud auth application-default login
#   - Project set:               gcloud config set project socrateai-gen-lang-client
# ==============================================================================
set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0625573011}"
REGION="${GCP_REGION:-us-central1}" # Optimized low-cost region
REPO_NAME="alphaevolve-k3-t2"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_URI="gcr.io/${PROJECT_ID}/${REPO_NAME}:${IMAGE_TAG}"
STAGING_BUCKET="gs://socrateai-datalake-gen-lang-client-0625573011/vertex_staging"
GCS_CHECKPOINT_DIR="gs://socrateai-datalake-gen-lang-client-0625573011/checkpoints"
JOB_NAME="Phase3_AlphaEvolve_K3_T2_DeepBurn_$(date +%Y%m%d_%H%M%S)"

echo "======================================================================"
echo "🚀 AlphaEvolve K3×T² — Phase 3 Deep Burn (Sub-$25 Capped)"
echo "   Project  : ${PROJECT_ID}"
echo "   Region   : ${REGION} (Low-Cost Region)"
echo "   Image    : ${IMAGE_URI}"
echo "   Job Name : ${JOB_NAME}"
echo "======================================================================"

# ── Step 1: Build hybrid Lean/Python Docker image via Cloud Build ───────────
echo ""
echo "📦 [1/3] Building Docker image in Google Cloud Build..."
gcloud builds submit \
    --tag "${IMAGE_URI}" \
    --project "${PROJECT_ID}" \
    --timeout=3600 \
    .

echo "✅ Docker image built: ${IMAGE_URI}"

# ── Step 2: Submit Vertex AI Custom Training Job ────────────────────────────
echo ""
echo "🖥️  [2/3] Submitting Custom Training Job to Vertex AI..."
# Note: For strict sub-$25 budget optimization, use: ./scripts/deploy_vertex_job_optimized.sh spot-l4
gcloud ai custom-jobs create \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --display-name="${JOB_NAME}" \
    --worker-pool-spec="\
machine-type=g2-standard-8,\
accelerator-type=NVIDIA_L4,\
accelerator-count=1,\
replica-count=1,\
container-image-uri=${IMAGE_URI}" \
    --staging-bucket="${STAGING_BUCKET}" \
    --labels="phase=3,model=k3_t2,framework=nsga2"

echo ""
echo "======================================================================"
echo "✅ [3/3] Deployment Successful!"
echo "   GCS Checkpoints : ${GCS_CHECKPOINT_DIR}"
echo "   Vertex AI Console: https://console.cloud.google.com/vertex-ai/training/custom-jobs?project=${PROJECT_ID}"
echo "======================================================================"
echo ""
echo "📡 To monitor live logs:"
echo "   gcloud ai custom-jobs stream-logs --region=${REGION} --project=${PROJECT_ID} <JOB_ID>"
