# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

# uv handles dependency resolution/install (see uv.lock)
COPY --from=ghcr.io/astral-sh/uv:0.5.14 /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install dependencies first so this layer is cached while only app code changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

RUN uv sync --frozen

EXPOSE 9000

# --no-reload: uvicorn's reloader/file-watcher is meant for local dev, not containers.
# For local dev with live reload, override the command and bind-mount the source tree.
CMD ["python", "-m", "chatvoice.main", "server", "--no-reload"]
