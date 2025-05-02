# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    ca-certificates \
    unzip \
    libffi-dev \
    libssl-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy app code and requirements
COPY webhook_listener.py /app/webhook_listener.py
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt --target /app/.deps

# Download and install TruffleHog binary
RUN curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /usr/local/bin

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install only what's needed for git HTTPS support
RUN apt-get update && apt-get install -y \
    git \
    git-lfs \
    ca-certificates \
    libcurl4-openssl-dev \
    libgnutls28-dev \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/webhook_listener.py /app/webhook_listener.py
COPY --from=builder /app/.deps /app/.deps
COPY --from=builder /usr/local/bin/trufflehog /usr/local/bin/trufflehog


ENV PYTHONPATH="/app/.deps"

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "webhook_listener:app", "--host", "0.0.0.0", "--port", "8080"]
