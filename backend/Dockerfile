FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libmagic1 libsndfile1 ca-certificates && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 app && mkdir -p /data/uploads /models && chown -R app:app /data /models
WORKDIR /app
COPY requirements*.txt requirements*.lock ./
RUN pip install -r requirements.lock
COPY --chown=app:app app ./app
ENV UPLOAD_DIR=/data/uploads DATABASE_URL=sqlite:////data/voz.db HF_HOME=/models PYANNOTE_METRICS_ENABLED=0 HF_HUB_DISABLE_TELEMETRY=1
USER app

FROM base AS api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

FROM base AS worker
USER root
RUN pip install torch==2.8.0+cpu torchaudio==2.8.0+cpu --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements-ml-cpu.lock
USER app
CMD ["python", "-m", "app.workers.run"]

FROM base AS worker-cuda
USER root
RUN pip install -r requirements-ml.lock
# CTranslate2 loads CUDA libraries dynamically, independently of torch.
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.12/site-packages/nvidia/cublas/lib:/usr/local/lib/python3.12/site-packages/nvidia/cudnn/lib:/usr/local/lib/python3.12/site-packages/nvidia/cuda_runtime/lib
USER app
CMD ["python", "-m", "app.workers.run"]
