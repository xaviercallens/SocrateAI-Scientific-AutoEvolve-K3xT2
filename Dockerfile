# AlphaEvolve-K3-T2 — Vertex AI Custom Training Container
# =========================================================
# Hybrid Lean 4 + Python container for GCP TPU/GPU deployment.
# Embeds the Lean 4 formal oracle binary alongside the full Python
# AlphaEvolve stack for neuro-symbolic K3×T² evolution.

FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# ── System packages ──────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    python3.10 python3-pip python3.10-venv \
    curl git wget build-essential \
    && rm -rf /var/lib/apt/lists/*

# Make python3.10 the default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 \
 && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# ── Lean 4 via Elan ──────────────────────────────────────────────────
ENV ELAN_HOME=/root/.elan
ENV PATH="${ELAN_HOME}/bin:${PATH}"
RUN curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    | sh -s -- -y --default-toolchain stable

# ── Workspace ────────────────────────────────────────────────────────
WORKDIR /workspace
COPY . /workspace/

# ── Python dependencies ───────────────────────────────────────────────
RUN pip install --no-cache-dir \
    gcsfs \
    numpy \
    scipy \
    pandas \
    psutil \
    "jax[cuda11_cudnn86]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html \
    cobaya \
    pyyaml \
    deap

# ── Compile Lean 4 Oracle binary ─────────────────────────────────────
RUN if [ -d "test_lean_oracle" ]; then \
        cd test_lean_oracle && lake build; \
    elif [ -d "lean_oracle" ]; then \
        cd lean_oracle && lake build; \
    fi

# ── Entrypoint: Phase 3 NSGA-II orchestrator ─────────────────────────
ENTRYPOINT ["python3", "scripts/run_phase3_nsga2_k3_t2.py"]
