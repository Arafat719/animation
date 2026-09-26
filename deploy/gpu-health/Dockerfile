# Supply a verified Python 3.12 Debian-compatible base as repository@sha256:digest.
# No mutable default. Build via scripts/package_gpu_health.py's validated context.
ARG WORKER_BASE_IMAGE
FROM ${WORKER_BASE_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=all NVIDIA_DRIVER_CAPABILITIES=utility
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt
COPY animation_studio /app/animation_studio
USER 65532:65532
EXPOSE 8091
# Loopback default; use explicit --host 0.0.0.0 only for an approved container deployment.
CMD ["python", "-m", "uvicorn", "animation_studio.workers.gpu_health:create_app", "--factory", "--host", "127.0.0.1", "--port", "8091"]
