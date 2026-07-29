#!/bin/bash
# ==============================================================================
# deploy_vertex_job_budget.sh — Budget Phase 3 (K3×T² Deep Burn)
# ==============================================================================
# Correctly provisions Spot instances via --config YAML (the only way to
# set scheduling.strategy: SPOT in gcloud CLI).
#
# Fallback cascade: Spot L4 → Spot T4 → On-Demand T4
# Target: < $15 for 24 Hours (Spot) / < $25 (On-Demand fallback)
# ==============================================================================
set -e

PROJECT_ID="gen-lang-client-0625573011"
REGION="us-central1"
REPO_NAME="alphaevolve-k3-t2"
IMAGE_URI="gcr.io/${PROJECT_ID}/${REPO_NAME}:latest"
CONFIG_DIR="configs"
mkdir -p "${CONFIG_DIR}"

echo "======================================================"
echo "🚀 Deploying BUDGET Phase 3 (K3×T² Deep Burn) to Vertex AI"
echo "   Fallback cascade: Spot L4 → Spot T4 → On-Demand T4"
echo "   Target Cost: < \$15 for 24 Hours"
echo "======================================================"

# ── Step 1: Build Docker image (skip if already built) ───────────────────────
SKIP_BUILD="${SKIP_BUILD:-false}"

if [ "${SKIP_BUILD}" = "true" ]; then
    echo "⏭️  Skipping Docker build (SKIP_BUILD=true). Using existing image."
else
    echo ""
    echo "📦 [1/2] Building Docker Image in Google Cloud Build..."
    gcloud builds submit \
        --tag "${IMAGE_URI}" \
        --project "${PROJECT_ID}" \
        --timeout=3600 \
        .
    echo "✅ Docker image built: ${IMAGE_URI}"
fi

# ── Helper: Generate config YAML ─────────────────────────────────────────────
generate_config() {
    local machine_type=$1
    local accel_type=$2
    local strategy=$3
    local config_file=$4

    cat <<EOF > "${config_file}"
workerPoolSpecs:
  - machineSpec:
      machineType: ${machine_type}
      acceleratorType: ${accel_type}
      acceleratorCount: 1
    replicaCount: 1
    containerSpec:
      imageUri: ${IMAGE_URI}
      env:
        - name: GCS_CHECKPOINT_DIR
          value: gs://socrateai-datalake-${PROJECT_ID}/checkpoints
        - name: CAMPAIGN_DURATION_HOURS
          value: "24"
        - name: CAMPAIGN_BUDGET_USD
          value: "25.00"
        - name: HOURLY_RATE_USD
          value: "0.36"
        - name: BUDGET_RESERVE_USD
          value: "1.50"
scheduling:
  strategy: ${strategy}
  timeout: 86400s
EOF
}

# ── Step 2: Submit with fallback cascade ─────────────────────────────────────
echo ""
echo "🖥️  [2/2] Submitting Custom Job to Vertex AI..."

# Attempt 1: Spot L4
echo "   🔹 Attempt 1: Spot L4 (g2-standard-8 + NVIDIA_L4)..."
CONFIG_FILE="${CONFIG_DIR}/vertex_spot_l4.yaml"
generate_config "g2-standard-8" "NVIDIA_L4" "SPOT" "${CONFIG_FILE}"

if gcloud ai custom-jobs create \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --display-name="Phase3_K3T2_SpotL4_$(date +%Y%m%d_%H%M%S)" \
    --config="${CONFIG_FILE}" \
    2>&1; then
    echo ""
    echo "======================================================"
    echo "✅ Budget Deployment Successful! (Spot L4)"
    echo "   Est. 24h cost: ~\$5.76"
    echo "   Region: ${REGION}"
    echo "   Console: https://console.cloud.google.com/vertex-ai/training/custom-jobs?project=${PROJECT_ID}"
    echo "======================================================"
    exit 0
fi

# Attempt 2: Spot T4
echo ""
echo "   🔸 Attempt 2: Spot T4 (n1-standard-8 + NVIDIA_TESLA_T4)..."
CONFIG_FILE="${CONFIG_DIR}/vertex_spot_t4.yaml"
generate_config "n1-standard-8" "NVIDIA_TESLA_T4" "SPOT" "${CONFIG_FILE}"

if gcloud ai custom-jobs create \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --display-name="Phase3_K3T2_SpotT4_$(date +%Y%m%d_%H%M%S)" \
    --config="${CONFIG_FILE}" \
    2>&1; then
    echo ""
    echo "======================================================"
    echo "✅ Budget Deployment Successful! (Spot T4 Fallback)"
    echo "   Est. 24h cost: ~\$8.64"
    echo "   Region: ${REGION}"
    echo "   Console: https://console.cloud.google.com/vertex-ai/training/custom-jobs?project=${PROJECT_ID}"
    echo "======================================================"
    exit 0
fi

# Attempt 3: On-Demand T4 (guaranteed, still under $25)
echo ""
echo "   🔻 Attempt 3: On-Demand T4 (n1-standard-8 + NVIDIA_TESLA_T4)..."
gcloud ai custom-jobs create \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --display-name="Phase3_K3T2_OnDemandT4_$(date +%Y%m%d_%H%M%S)" \
    --worker-pool-spec=machine-type=n1-standard-8,accelerator-type=NVIDIA_TESLA_T4,accelerator-count=1,replica-count=1,container-image-uri="${IMAGE_URI}"

echo ""
echo "======================================================"
echo "✅ Budget Deployment Successful! (On-Demand T4)"
echo "   Est. 24h cost: ~\$17.52"
echo "   Region: ${REGION}"
echo "   Console: https://console.cloud.google.com/vertex-ai/training/custom-jobs?project=${PROJECT_ID}"
echo "======================================================"
