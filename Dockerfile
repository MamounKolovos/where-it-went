FROM ghcr.io/astral-sh/uv:0.8.22-python3.13-trixie-slim

RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

ENV UV_LINK_MODE=copy

ENV UV_TOOL_BIN_DIR=/usr/local/bin

USER root

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Give ownership of .venv and app to nonroot
RUN chown -R nonroot:nonroot /app/.venv /app

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT []

USER nonroot

# Allows stdout/stderr to be shown in logs
ENV PYTHONUNBUFFERED=1

# Tells python where to look for imports
ENV PYTHONPATH=/app/src