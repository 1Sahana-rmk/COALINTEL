FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DOCUMENT_AI_HOST=0.0.0.0 \
    DOCUMENT_AI_DEVICE=cpu \
    DOCUMENT_AI_CPU_THREADS=2 \
    DOCUMENT_AI_DISABLE_MKLDNN=true

WORKDIR /app

# PaddleOCR/PaddleX image and native-runtime dependencies.  This image uses
# the CPU paddlepaddle wheel from requirements.txt; no CUDA packages are
# installed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libfontconfig1 \
        libfreetype6 \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libsm6 \
        libstdc++6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# The build context is the repository root so the package keeps its normal
# import path and can be started with `python -m document_ai_service.server`.
COPY document_ai_service/requirements.txt /app/document_ai_service/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/document_ai_service/requirements.txt

COPY document_ai_service /app/document_ai_service

# Informational only; the process binds to Render's PORT when supplied.
EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.environ.get('DOCUMENT_AI_PORT') or os.environ.get('PORT') or '8765'; urllib.request.urlopen('http://127.0.0.1:' + port + '/health', timeout=5)"

CMD ["python", "-m", "document_ai_service.server"]
