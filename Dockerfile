FROM python:3.12-slim

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv==0.12.5

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project

COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
COPY tests ./tests

RUN uv sync --locked

CMD ["uvicorn", "sea_battle.main:app", "--host", "0.0.0.0", "--port", "8000"]
