FROM python:3.12-slim

WORKDIR /app

COPY dashboard/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only tracked source files
COPY data/desi_dr1/ ./data/desi_dr1/
COPY data/nanograv/input.json ./data/nanograv/input.json
COPY data/euclid_q1/s8_joint_means.txt ./data/euclid_q1/
COPY data/euclid_q1/s8_joint_covariance.txt ./data/euclid_q1/
COPY lean_oracle/PROOF_MANIFEST.md ./lean_oracle/
COPY lean_oracle/GeneratedK3.lean ./lean_oracle/
COPY dashboard/backend/main.py .
COPY dashboard/frontend/ ./dashboard/frontend/

# Pre-bake WS outputs by fetching from GCS at build time
ARG GCS_BUCKET=socrateai-datalake-gen-lang-client-0625573011
RUN apt-get update -qq && apt-get install -y -qq curl && \
    mkdir -p outputs/ws1 outputs/ws2 outputs/ws3 outputs/ws5 outputs/ws6 outputs/ws7

COPY dashboard/baked_outputs/ ./outputs/

ENV PORT=8080
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
