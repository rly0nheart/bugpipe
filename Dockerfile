# Build stage
FROM ghcr.io/astral-sh/uv:python3.14-alpine AS builder

WORKDIR /app

# Dependencies first for layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev --extra cli

# Install the project itself
COPY . .
RUN uv sync --frozen --no-dev --extra cli

# Runtime stage — no uv needed at runtime
FROM python:3.14-alpine

WORKDIR /app

COPY --from=builder /app .

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["bugpipe"]
