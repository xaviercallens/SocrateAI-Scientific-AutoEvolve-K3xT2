FROM python:3.10-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    git curl build-essential wget \
    && rm -rf /var/lib/apt/lists/*

# Install elan / Lean 4
RUN curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y
ENV PATH="$HOME/.elan/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["/bin/bash"]
