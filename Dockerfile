# syntax=docker/dockerfile:1

# ---- base: shared layer with runtime dependencies ----
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Install runtime deps first so this layer is cached unless requirements change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source.
COPY . .

# ---- test: adds dev tooling and runs the pytest suite inside the container ----
FROM base AS test
RUN pip install --no-cache-dir -r requirements-dev.txt
CMD ["pytest", "-q"]

# ---- production: lean image, runs as a non-root user via gunicorn ----
FROM base AS production
ARG APP_VERSION=dev
LABEL org.opencontainers.image.title="ACEest Fitness & Gym API" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.source="https://github.com/2025tm93238/devops-aceest-fitness"
RUN useradd --create-home appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app/data
USER appuser
ENV DATABASE=/app/data/aceest_fitness.db
EXPOSE 5000
# Docker-level health check (Kubernetes uses its own probes on the same endpoint).
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2)"
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
