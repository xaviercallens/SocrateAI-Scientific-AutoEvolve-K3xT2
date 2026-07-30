#!/bin/bash
# Hourly Vertex AI Job Monitor

JOB_NAME="projects/1003063861791/locations/us-central1/customJobs/8210525298559549440"
LOG_FILE="outputs/vertex_hourly_monitor.log"
REGION="us-central1"
PROJECT="gen-lang-client-0625573011"

mkdir -p outputs/

echo "=====================================================" >> "${LOG_FILE}"
echo "🚀 Starting Hourly Vertex AI Monitoring" >> "${LOG_FILE}"
echo "   Job: ${JOB_NAME}" >> "${LOG_FILE}"
echo "   Start Time: $(date)" >> "${LOG_FILE}"
echo "=====================================================" >> "${LOG_FILE}"

while true; do
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$TIMESTAMP] Checking Vertex AI Job Status..." >> "${LOG_FILE}"
    
    STATUS=$(gcloud ai custom-jobs describe "${JOB_NAME}" \
        --region="${REGION}" --project="${PROJECT}" \
        --format="value(state)" 2>>"${LOG_FILE}")
    
    echo "[$TIMESTAMP] Status: ${STATUS}" >> "${LOG_FILE}"
    
    if [[ "$STATUS" == "JOB_STATE_SUCCEEDED" || "$STATUS" == "JOB_STATE_FAILED" || "$STATUS" == "JOB_STATE_CANCELLED" ]]; then
        echo "[$TIMESTAMP] Job has terminated with status ${STATUS}. Exiting monitor." >> "${LOG_FILE}"
        break
    fi
    
    # Sleep for 1 hour
    sleep 3600
done
