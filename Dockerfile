FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copying dependency files and source code
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

RUN uv sync --frozen --no-dev

# Creating a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -m appuser
RUN mkdir -p /home/appuser/.cache/uv && chown -R appuser:appuser /app /home/appuser


EXPOSE 5000

# Setting environment variables
ENV PYTHONPATH=/app/src
ENV FLASK_APP=where_it_went.app:app
ENV FLASK_ENV=production

USER appuser

# This is a Health check URL for Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=5)" || exit 1

# This is to run the application
CMD ["uv", "run", "where-it-went"]
