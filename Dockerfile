# ── Stage 1: Build DSL engine (PyO3 wheel + WASM bundle) ─────────────────────
FROM python:3.13-slim-trixie AS dsl-builder

RUN apt-get update \
    && apt-get install -y curl build-essential \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.cargo/bin:${PATH}"

# Install build tools and WASM target
RUN pip install maturin \
    && rustup target add wasm32-unknown-unknown \
    && curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh

WORKDIR /build
COPY ./crates/dsl-engine ./crates/dsl-engine

# Build PyO3 wheel for server-side DSL evaluation
RUN cd crates/dsl-engine \
    && maturin build --features python --release --out /wheels

# Build WASM bundle for frontend DSL validation
RUN cd crates/dsl-engine \
    && wasm-pack build --target web --out-dir /wasm-pkg --release

# ── Stage 2: Download Tailwind CSS standalone CLI ─────────────────────────────
FROM alpine AS tailwind
ARG TARGETARCH
RUN apk add --no-cache curl && \
    case "$TARGETARCH" in amd64) ARCH=x64 ;; arm64) ARCH=arm64 ;; esac && \
    curl -fsSL "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-${ARCH}" -o /tailwindcss && \
    chmod +x /tailwindcss

# ── Stage 3: Runtime image (slim, no Rust) ────────────────────────────────────
FROM python:3.13-slim-trixie

# Only git needed (for fastapi-webpage git source)
RUN apt-get update \
    && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.
WORKDIR /app

COPY ./pyproject.toml .
COPY ./uv.lock .

# Install Python dependencies.
RUN uv sync --frozen --no-cache

# Install pre-built DSL engine wheel from builder stage.
COPY --from=dsl-builder /wheels/*.whl /tmp/wheels/
RUN uv pip install /tmp/wheels/*.whl && rm -rf /tmp/wheels

# ── Build Tailwind CSS ──────────────────────────────────────────────────────
COPY --from=tailwind /tailwindcss /tmp/tailwindcss
COPY ./src/static/css/input.css ./src/static/css/input.css
COPY ./src/templates ./src/templates
RUN /tmp/tailwindcss --input ./src/static/css/input.css --output ./src/static/css/tailwind.css --minify && \
    rm /tmp/tailwindcss

# WASM bundle for frontend DSL editor (built in dsl-builder stage)
COPY --from=dsl-builder /wasm-pkg ./crates/dsl-engine/pkg

COPY ./src ./src
COPY ./scripts ./scripts

# Reduce system loading
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ASGI settings
ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000

## Uvicorn parameter `--forwarded-allow-ips` default value is point to $FORWARDED_ALLOW_IPS
## Default is empty (no trusted proxies). Override at runtime: docker run -e FORWARDED_ALLOW_IPS=127.0.0.1
ENV FORWARDED_ALLOW_IPS=""

# Use entrypoint script to handle environment-based startup
RUN chmod +x ./scripts/docker-entrypoint.sh

ENTRYPOINT ["./scripts/docker-entrypoint.sh"]

EXPOSE ${UVICORN_PORT:-8000}
