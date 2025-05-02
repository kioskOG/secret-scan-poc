# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    libffi-dev \
    libssl-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy app code and requirements
COPY consumer.py /app/consumer.py
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt --target /app/.deps

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app/consumer.py /app/consumer.py
COPY --from=builder /app/.deps /app/.deps

ENV PYTHONPATH="/app/.deps"

CMD ["python", "consumer.py"]

