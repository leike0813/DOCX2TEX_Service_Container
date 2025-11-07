FROM debian:bookworm-slim

# Configure Debian mirrors (CN-friendly) and install base packages
ARG DEBIAN_MIRROR=mirrors.tuna.tsinghua.edu.cn
ARG DEBIAN_SECURITY_MIRROR=mirrors.tuna.tsinghua.edu.cn

ENV DEBIAN_FRONTEND=noninteractive \
    APP_HOME=/app \
    WORK_ROOT=/work \
    DATA_ROOT=/data \
    LOG_DIR=/var/log/docx2tex \
    DOCX2TEX_HOME=/opt/docx2tex \
    XML_CATALOG_FILES=/opt/catalog/catalog.xml \
    PYTHONUNBUFFERED=1 \
    UVICORN_WORKERS=2 \
    STATE_DB=/data/state.db \
    TTL_DAYS=7 \
    LOCK_SWEEP_INTERVAL_SEC=120 \
    LOCK_MAX_AGE_SEC=1800 \
    MAX_UPLOAD_BYTES=

RUN set -eux; \
    rm -f /etc/apt/sources.list.d/debian.sources || true; \
    printf 'deb http://%s/debian bookworm main contrib non-free non-free-firmware\n' "$DEBIAN_MIRROR" > /etc/apt/sources.list; \
    printf 'deb http://%s/debian bookworm-updates main contrib non-free non-free-firmware\n' "$DEBIAN_MIRROR" >> /etc/apt/sources.list; \
    printf 'deb http://%s/debian-security bookworm-security main contrib non-free non-free-firmware\n' "$DEBIAN_SECURITY_MIRROR" >> /etc/apt/sources.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      openjdk-17-jre-headless inkscape python3 python3-pip python3-venv \
      sqlite3 \
      fonts-noto-cjk zip unzip locales curl wget git; \
    sed -i 's/# zh_CN.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' /etc/locale.gen && locale-gen; \
    rm -rf /var/lib/apt/lists/*

# Fetch docx2tex at build time (offline at runtime)
RUN git clone --recursive https://github.com/transpect/docx2tex.git /opt/docx2tex

# Create XML catalog mapping transpect URLs to local paths
RUN mkdir -p /opt/catalog

# Allow overriding catalog from build context if provided
COPY catalog/ /opt/catalog/

# Set pip to Tsinghua mirror (CN) before installing Python libraries
RUN printf "[global]\nindex-url = https://pypi.tuna.tsinghua.edu.cn/simple\n" > /etc/pip.conf

# Install Python deps early for better build cache reuse
WORKDIR /app
COPY app/requirements.txt /app/requirements.txt
RUN python3 -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy application code (changes here won't invalidate previous pip layer)
COPY app/ /app/
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]

# Simple container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8000/healthz || exit 1

# Declare common mount points (optional but recommended)
VOLUME ["/data", "/work"]
