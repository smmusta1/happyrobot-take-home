FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn happyrobot_api.main:app --host 0.0.0.0 --port 8000"]
