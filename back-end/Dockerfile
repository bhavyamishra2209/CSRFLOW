# ── DocuMind AI Backend — Render deployment Dockerfile ──────────────────────
#
# Optimised for Render free tier (512MB RAM):
#   - torch CPU-only micro wheel (~200MB vs 2GB GPU default)
#   - easyocr / streamlit excluded from image (not needed for API)
#   - spaCy model downloaded at build time (no runtime network call)

FROM python:3.11-slim

# ── System dependencies ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Install torch CPU-only FIRST (before requirements.txt) ───────────────────
# Using the official CPU-only index saves ~1.5GB vs the default wheel.
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
        "torch==2.2.2+cpu" \
        "torchvision==0.17.2+cpu" \
        --index-url https://download.pytorch.org/whl/cpu

# ── Install remaining requirements (torch already satisfied above) ────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Download spaCy model at build time ───────────────────────────────────────
RUN python -m spacy download en_core_web_sm \
    || echo "spaCy download failed — KG will use regex fallback"

# ── Copy application source ───────────────────────────────────────────────────
COPY . .

# ── Runtime ───────────────────────────────────────────────────────────────────
ENV PORT=8000
EXPOSE $PORT

# Single worker — free tier has 1 vCPU
CMD uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
