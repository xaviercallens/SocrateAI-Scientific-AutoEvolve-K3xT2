#!/bin/bash
# 🎯 Launch Antigravity K3xT2 Deep Burn on GCP L4 Spot Instance
# Region: us-central1 (Iowa) is typically the most cost-effective and has high L4 availability.
# Instance: g2-standard-8 (1x L4 GPU, 8 vCPUs, 32GB RAM)
# Provisioning: SPOT (Cost is ~$0.25 - $0.35 / hour instead of ~$0.80)

# Make sure you are authenticated with gcloud before running this:
# gcloud auth login

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No default GCP project found. Run 'gcloud config set project YOUR_PROJECT_ID'"
    exit 1
fi

INSTANCE_NAME="k3-t2-deepburn-l4-spot"
ZONE="us-central1-a"

echo "🚀 Provisioning L4 Spot Instance in $ZONE for project $PROJECT_ID..."

gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=g2-standard-8 \
    --provisioning-model=SPOT \
    --instance-termination-action=STOP \
    --accelerator=type=nvidia-l4,count=1 \
    --maintenance-policy=TERMINATE \
    --image-family=common-cu121-debian-11 \
    --image-project=deeplearning-platform-release \
    --boot-disk-size=100GB \
    --boot-disk-type=pd-balanced \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --metadata=startup-script="#!/bin/bash
echo '🔥 Starting Automated Deep Burn VM Setup...'
# Configure Swap automatically to prevent OOM
fallocate -l 16G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '✅ 16GB Swap Configured.'
"

echo ""
echo "✅ VM Creation requested. (Check GCP console or CLI output above for status)"
echo "--------------------------------------------------------"
echo "To SSH into the instance once it is running:"
echo "  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "Once logged in, clone/sync this repo and run:"
echo "  tmux new -s antigravity_burn"
echo "  cd SocrateAI-Scientific-AutoEvolve-K3*T2"
echo "  .venv/bin/python scripts/run_local_deep_burn.py"
echo "--------------------------------------------------------"
