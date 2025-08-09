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
RUN python -m unidic download

# Now bring in the actual application code
COPY . .

RUN pip install -e .

RUN python melo/init_downloads.py

# Remove unneeded model formats from Hugging Face cache
RUN find /root/.cache/huggingface/hub/models--* \
    -type f \
    \( -name "*.h5" -o -name "*.tflite" -o -name "tf_model*" -o -name "*.onnx" -o -name "rust_model*" -o -name "*.msgpack" \) \
    -exec rm -f {} +

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
