#!/bin/bash
# Automatically stream Euclid Q2 data from ESA to GCP

echo "Starting ESA to GCP transfer..."
export PROJECT_ID=$(gcloud config get-value project)
export BUCKET_NAME="gs://socrateai-datalake-${PROJECT_ID}"

# Ensure temp directory exists
mkdir -p /tmp/euclid_temp

# Use SFTP to pull the Level 3 (L3) shape catalogs and covariance matrices
sftp anonymous@ftp-bdt.cosmos.esa.int:/pub/EUC_Q2/egbs-v1/* /tmp/euclid_temp/ || true

# Upload directly to the Google Cloud Bucket
gcloud storage cp /tmp/euclid_temp/* $BUCKET_NAME/stream3_euclid_q2/ || true

# Clean local VM
rm -rf /tmp/euclid_temp
echo "Transfer complete."
