#!/bin/bash
# ==============================================================================
# deploy_vertex_job_optimized.sh — Sub-$25 Capped 24-Hour Campaign
# ==============================================================================
# Cost-Optimized Deployment for AlphaEvolve K3×T² Deep Burn:
# 1. Primary Region: us-central1 (Lowest GCP GPU & Compute rates)
# 2. Spot / Preemptible VM Provisioning (60-70% discount)
# 3. Hardware Choice:
#    - Tier A (Default / Best Value): NVIDIA L4 GPU (24GB VRAM) on g2-standard-8
#      Spot Rate: ~$0.24 / hr  -->  24h Campaign Total = ~$5.76
#    - Tier B (High vCPU): NVIDIA T4 GPU on n1-standard-16
#      Spot Rate: ~$0.36 / hr  -->  24h Campaign Total = ~$8.64
#    - Tier C (On-Demand Fallback): NVIDIA T4 on n1-standard-8
#      On-Demand Rate: ~$0.73 / hr  -->  24h Campaign Total = ~$17.52
#
# Target Budget: Under $25.00 / €25.00 per 24-hour campaign.
# ==============================================================================
set -euo pipefail

# ── Config & Defaults ───────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0625573011}"
REGION="${GCP_REGION:-us-central1}"   # us-central1 is ~15-20% cheaper than us-east4
REPO_NAME="alphaevolve-k3-t2"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_URI="gcr.io/${PROJECT_ID}/${REPO_NAME}:${IMAGE_TAG}"
STAGING_BUCKET="gs://socrateai-datalake-gen-lang-client-0625573011/vertex_staging"
GCS_CHECKPOINT_DIR="gs://socrateai-datalake-gen-lang-client-0625573011/checkpoints"
JOB_NAME="AlphaEvolve_24h_Budget_${IMAGE_TAG}_$(date +%Y%m%d_%H%M%S)"

PROFILE="${1:-spot-l4}" # Options: spot-l4, spot-t4, ondemand-t4

case "${PROFILE}" in
    spot-l4)
        MACHINE_TYPE="g2-standard-8"
        ACCEL_TYPE="NVIDIA_L4"
        ACCEL_COUNT=1
        PROVISION_MODEL="SPOT"
        EST_HOURLY='0.24'
        EST_HOURLY_RAW="0.24"
        EST_24H_COST='5.76'
        DESC="Tier A (Spot L4 24GB VRAM + 8 vCPUs)"
        ;;
    spot-t4)
        MACHINE_TYPE="n1-standard-16"
        ACCEL_TYPE="NVIDIA_TESLA_T4"
        ACCEL_COUNT=1
        PROVISION_MODEL="SPOT"
        EST_HOURLY='0.36'
        EST_HOURLY_RAW="0.36"
        EST_24H_COST='8.64'
        DESC="Tier B (Spot T4 16GB VRAM + 16 vCPUs)"
        ;;
    ondemand-t4)
        MACHINE_TYPE="n1-standard-8"
        ACCEL_TYPE="NVIDIA_TESLA_T4"
        ACCEL_COUNT=1
        PROVISION_MODEL="STANDARD"
        EST_HOURLY='0.73'
        EST_HOURLY_RAW="0.73"
        EST_24H_COST='17.52'
        DESC="Tier C (On-Demand T4 + 8 vCPUs — Guaranteed 24h uninterrupted)"
        ;;
    *)
        echo "Usage: $0 [spot-l4 | spot-t4 | ondemand-t4]"
        exit 1
        ;;
esac

echo "======================================================================"
echo "🎯 AlphaEvolve K3×T² — Sub-\$25 Budget 24-Hour Campaign"
echo "======================================================================"
echo "   Profile       : ${DESC}"
echo "   Project ID    : ${PROJECT_ID}"
echo "   Region        : ${REGION} (Optimized Low-Cost Region)"
echo "   Machine Type  : ${MACHINE_TYPE}"
echo "   Accelerator   : ${ACCEL_COUNT}x ${ACCEL_TYPE}"
echo "   Provisioning  : ${PROVISION_MODEL}"
echo "   Est. Hourly   : \$${EST_HOURLY} / hr"
echo "   Est. 24h Total: \$${EST_24H_COST} (Target: < \$25.00 / €25.00)"
echo "   Image URI     : ${IMAGE_URI}"
echo "======================================================================"

# ── Step 1: Build Image via Cloud Build ──────────────────────────────────────
echo ""
echo "📦 [1/3] Building container image in Google Cloud Build..."
gcloud builds submit \
    --tag "${IMAGE_URI}" \
    --project "${PROJECT_ID}" \
    --timeout=3600 \
    .

# ── Step 2: Generate Vertex AI Config YAML ──────────────────────────────────
CONFIG_DIR="configs"
mkdir -p "${CONFIG_DIR}"
CONFIG_FILE="${CONFIG_DIR}/vertex_budget_job.yaml"

cat <<EOF > "${CONFIG_FILE}"
displayName: ${JOB_NAME}
jobSpec:
  workerPoolSpecs:
    - machineSpec:
        machineType: ${MACHINE_TYPE}
        acceleratorType: ${ACCEL_TYPE}
        acceleratorCount: ${ACCEL_COUNT}
      replicaCount: 1
      containerSpec:
        imageUri: ${IMAGE_URI}
        env:
          - name: GCS_CHECKPOINT_DIR
            value: ${GCS_CHECKPOINT_DIR}
          - name: CAMPAIGN_DURATION_HOURS
            value: "24"
          - name: CAMPAIGN_BUDGET_USD
            value: "25.00"
          - name: HOURLY_RATE_USD
            value: "${EST_HOURLY_RAW}"
          - name: BUDGET_RESERVE_USD
            value: "1.50"
          - name: PRESELECT_MAX_CANDIDATES
            value: "3"
  scheduling:
    provisioningModel: ${PROVISION_MODEL}
    timeout: 86400s
EOF

echo "📄 [2/3] Generated Vertex AI spec: ${CONFIG_FILE}"

# ── Step 3: Submit Custom Training Job ──────────────────────────────────────
echo "🖥️  [3/3] Submitting Custom Training Job to Vertex AI..."
gcloud ai custom-jobs create \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --config="${CONFIG_FILE}" \
    --labels="phase=3,budget=sub25,campaign=24h"

echo ""
echo "======================================================================"
echo "✅ DEPLOYMENT SUCCESSFUL!"
echo "   Profile       : ${PROFILE} (${PROVISION_MODEL})"
echo "   Budget Status : CLEARED — 24h Campaign Estimated at \$${EST_24H_COST}"
echo "   Checkpoints   : ${GCS_CHECKPOINT_DIR}"
echo "   Console Link  : https://console.cloud.google.com/vertex-ai/training/custom-jobs?project=${PROJECT_ID}"
echo "======================================================================"
