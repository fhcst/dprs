# ── Stage 1: Build DSL engine wheel (Rust → PyO3) ────────────────────────────
FROM python:3.13-slim-trixie AS dsl-builder

RUN apt-get update \
    && apt-get install -y curl build-essential \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.cargo/bin:${PATH}"

RUN pip install maturin

WORKDIR /build
COPY ./crates/dsl-engine ./crates/dsl-engine
RUN cd crates/dsl-engine \
    && maturin build --features python --release --out /wheels

# ── Stage 2: Runtime image (slim, no Rust) ────────────────────────────────────
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

# WASM bundle for frontend DSL editor (pre-built, checked into repo)
COPY ./crates/dsl-engine/pkg ./crates/dsl-engine/pkg

COPY ./src ./src

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
COPY ./scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]

EXPOSE ${UVICORN_PORT:-8000}
