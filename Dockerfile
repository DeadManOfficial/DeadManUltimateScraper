# DEADMAN ULTIMATE SCRAPER
# ========================
# Multi-stage build for minimal image size

FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/* \
    && playwright install chromium --with-deps 2>/dev/null || true

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY deadman_scraper/ ./deadman_scraper/
COPY central_scraper.py .
COPY armory.py .
COPY cli/ ./cli/
COPY config/ ./config/

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TOR_METHOD=docker
ENV TOR_SOCKS_HOST=tor
ENV TOR_SOCKS_PORT=9050

# Create data directories
RUN mkdir -p /app/data /app/output /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from deadman_scraper.core.config import Config; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "cli.main"]
