# Sea Battle

Production-ready REST service for a networked Battleship game with persistent game sessions, pluggable shooting strategies, and a tournament arena.

## Status

Under active development.

## Tech Stack

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- pytest
- Docker

## Local startup

Docker Compose starts PostgreSQL, applies all Alembic migrations, and then
starts the API:

```bash
docker compose up --build
```

The API is available at <http://localhost:8000>. Its readiness endpoint at
<http://localhost:8000/health> also verifies the database connection.

To override local ports or database credentials, copy the example settings:

```bash
cp .env.example .env
```

Edit `.env` as needed. The file is ignored by Git.

## Tests

Run the complete test suite, including a real PostgreSQL persistence test:

```bash
docker compose --profile test run --rm test
```

Run only tests that do not require PostgreSQL:

```bash
uv run pytest -q tests/test_health.py tests/test_fleet.py
```
