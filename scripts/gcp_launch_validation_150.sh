#!/bin/bash
# 🚀 Fully Automated 150-Generation Validation on GCP L4 Spot
# Spins up an L4 Spot instance, runs the 150-generation validation job,
# syncs the results to GCS, and automatically deletes itself to save costs.

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No default GCP project found."
    exit 1
fi

INSTANCE_NAME="k3-t2-validation-l4"
ZONE="us-central1-a"
# The user's bucket for saving logs
BUCKET_NAME="socrateai-datalake-gen-lang-client-0625573011" 

echo "🚀 Provisioning Ephemeral L4 Spot Instance for 150-Gen Validation..."

gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=g2-standard-8 \
    --provisioning-model=SPOT \
    --accelerator=type=nvidia-l4,count=1 \
    --maintenance-policy=TERMINATE \
    --image-family=common-cu121-debian-11 \
    --image-project=deeplearning-platform-release \
    --boot-disk-size=100GB \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --metadata=startup-script="#!/bin/bash
exec > /var/log/validation_startup.log 2>&1
echo '🔥 Starting Automated Validation VM Setup...'

# 1. Setup swap
fallocate -l 16G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# 2. Clone repository
cd /home/jupyter
git clone https://github.com/xaviercallens/SocrateAI-Scientific-AutoEvolve-K3xT2.git repo
cd repo

# 3. Setup python env
apt-get update && apt-get install -y python3-venv
python3 -m venv .venv
.venv/bin/pip install gcsfs cobaya jax jaxlib scipy pandas psutil

# 4. Run the 150-gen validation
echo '🚀 Starting 150-generation run...'
.venv/bin/python scripts/run_gcp_validation.py

# 5. Backup logs to GCS
echo '☁️ Syncing logs to GCS...'
gsutil cp -r outputs/gcp_validation gs://${BUCKET_NAME}/validation_logs/

# 6. Self-Destruct to save money
echo '💥 Validation complete. Deleting instance...'
gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE --quiet
"

echo "✅ VM created and validation job dispatched!"
echo "The instance will automatically run the job, upload logs to gs://${BUCKET_NAME}/validation_logs/, and self-delete."
