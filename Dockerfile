# Using multi-stage build for production

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder 

# Precompiling Python files into .pyc for faster startup 
# And copying dependencies into the venv for portability.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy 

# Disabling python downloads to use the one already in the image.
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Caching dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app

# Installing dependencies including the app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


# ===== Stage 2: Runtime ===== 
FROM python:3.13-slim-bookworm



RUN groupadd --system --gid 999 appuser \
 && useradd --system --gid 999 --uid 999 --create-home appuser

WORKDIR /app 
 
 # Copying from builder 
 COPY --from=builder --chown=appuser:appuser /app /app


ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src
ENV FLASK_APP=where_it_went.app:app
ENV FLASK_ENV=production
ENV FLASK_DEBUG=1


USER appuser
EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
