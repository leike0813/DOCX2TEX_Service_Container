FROM debian:bookworm-slim

# Configure Debian mirrors (CN-friendly) and install base packages
ARG DEBIAN_MIRROR=mirrors.ustc.edu.cn
ARG DEBIAN_SECURITY_MIRROR=mirrors.ustc.edu.cn
ARG PIP_INDEX_URL=https://pypi.org/simple

ENV DEBIAN_FRONTEND=noninteractive \
    WORK_ROOT=/work \
    DATA_ROOT=/data \
    LOG_DIR=/var/log/docx2tex \
    DOCX2TEX_HOME=/svc/src/engines/docx2tex_engine/vendor/docx2tex \
    XML_CATALOG_FILES= \
    PYTHONUNBUFFERED=1 \
    UVICORN_WORKERS=2 \
    STATE_DB=/data/state.db \
    TTL_DAYS=7 \
    LOCK_SWEEP_INTERVAL_SEC=120 \
    LOCK_MAX_AGE_SEC=1800 \
    MAX_UPLOAD_BYTES=

ENV PATH=/opt/venv/bin:$PATH

RUN set -eux; \
    rm -f /etc/apt/sources.list.d/debian.sources || true; \
    printf 'deb http://%s/debian bookworm main contrib non-free non-free-firmware\n' "$DEBIAN_MIRROR" > /etc/apt/sources.list; \
    printf 'deb http://%s/debian bookworm-updates main contrib non-free non-free-firmware\n' "$DEBIAN_MIRROR" >> /etc/apt/sources.list; \
    printf 'deb http://%s/debian-security bookworm-security main contrib non-free non-free-firmware\n' "$DEBIAN_SECURITY_MIRROR" >> /etc/apt/sources.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      openjdk-17-jre-headless inkscape pandoc python3 python3-pip python3-venv \
      sqlite3 \
      fonts-noto-cjk zip unzip locales curl wget; \
    sed -i 's/# zh_CN.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' /etc/locale.gen && locale-gen; \
    rm -rf /var/lib/apt/lists/*

# Configure pip index before installing Python libraries.
RUN printf "[global]\nindex-url = %s\n" "$PIP_INDEX_URL" > /etc/pip.conf

# Install Python deps early for better build cache reuse.
WORKDIR /svc
COPY pyproject.toml README.md /svc/
COPY src/ /svc/src/
COPY scripts/ /svc/scripts/
RUN set -eux; \
    python3 -m venv /opt/venv; \
    python -m pip install --no-cache-dir --upgrade pip setuptools wheel; \
    python -m pip install --no-cache-dir /svc

RUN set -eux; \
    test -f "$DOCX2TEX_HOME/xpl/docx2tex.xpl"; \
    python -c "from engines.docx2tex_engine.assets import resolve_catalog_template; print(resolve_catalog_template())"; \
    command -v java; \
    command -v inkscape; \
    command -v pandoc; \
    command -v pandoc-tex-numbering; \
    python -u -m document_conversion.interfaces.cli check-system

RUN chmod +x /svc/scripts/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/svc/scripts/entrypoint.sh"]

# Simple container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8000/healthz || exit 1

# Declare common mount points (optional but recommended)
VOLUME ["/data", "/work"]
