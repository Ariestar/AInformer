FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY config ./config

RUN uv sync --frozen --no-dev

RUN addgroup --system ainformer \
    && adduser --system --ingroup ainformer ainformer \
    && chown -R ainformer:ainformer /app

USER ainformer

ENV PATH="/app/.venv/bin:${PATH}" \
    AINFORMER_SOURCES_CONFIG=/app/config/sources.toml \
    AINFORMER_RSSHUB_BASE_URL=http://rsshub:1200

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/v1/health', timeout=5)"

CMD ["uvicorn", "ainformer.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
