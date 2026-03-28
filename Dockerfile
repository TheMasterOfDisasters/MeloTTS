# ============================================================
# Stage 1: Build environment with dependencies and models
# ============================================================
FROM python:3.9-slim AS builder

WORKDIR /app

# Install system-level dependencies once
RUN apt-get update && apt-get install -y \
    build-essential libsndfile1 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements and setup script to cache installs
COPY requirements.txt .
# COPY setup.py . #has find packages so breaks cache

# Install Python dependencies (PostInstall will auto-download unidic!)
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128
ARG TORCH_PACKAGES="torch==2.8.0+cu128 torchaudio==2.8.0+cu128"
RUN pip install --index-url ${TORCH_INDEX_URL} ${TORCH_PACKAGES}
RUN python -m unidic download

# Now bring in the actual application code
COPY . .

RUN pip install -e .

# Download and remove unneeded model formats from Hugging Face cache
ARG INIT_DOWNLOADS_STRICT=0
ARG INIT_DOWNLOADS_MAX_RETRIES=5
ARG INIT_DOWNLOADS_RETRY_SLEEP=5
ARG INIT_DOWNLOADS_PROFILE=FULL
RUN INIT_DOWNLOADS_STRICT=${INIT_DOWNLOADS_STRICT} \
    INIT_DOWNLOADS_MAX_RETRIES=${INIT_DOWNLOADS_MAX_RETRIES} \
    INIT_DOWNLOADS_RETRY_SLEEP=${INIT_DOWNLOADS_RETRY_SLEEP} \
    INIT_DOWNLOADS_PROFILE=${INIT_DOWNLOADS_PROFILE} \
    python melo/init_downloads.py || \
    if [ "${INIT_DOWNLOADS_STRICT}" = "1" ]; then exit 1; else echo "[WARN] init_downloads failed in non-strict mode; continuing build"; fi && \
    find /root/.cache/huggingface/hub \
        -type f \
        \( -name "*.h5" -o -name "*.tflite" -o -name "tf_model*" -o -name "*.onnx" -o -name "rust_model*" -o -name "*.msgpack" \) \
        -exec rm -f {} + 2>/dev/null || true

# ============================================================
# Stage 2: Final runtime image
# ============================================================
FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential libsndfile1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
COPY --from=builder /root/nltk_data /root/nltk_data

# Expose port and run the app
EXPOSE 8888
CMD ["python", "./melo/app.py", "--host", "0.0.0.0", "--port", "8888"]
