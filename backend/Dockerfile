FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including Tesseract OCR & Poppler for PDF/image processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies list
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-cache low-memory all-MiniLM-L6-v2 ONNX model weights and tokenizer during image build
RUN python -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='sentence-transformers/all-MiniLM-L6-v2', filename='onnx/model.onnx'); hf_hub_download(repo_id='sentence-transformers/all-MiniLM-L6-v2', filename='tokenizer.json')"

# Enforce strict offline execution for all runtime workers
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1

# Copy backend source code
COPY . .

# Expose FastAPI default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Launch FastAPI app using uvicorn (binds dynamically to $PORT supplied by host or 8000 default)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
