# Sea Battle

REST service for a networked Battleship game with persistent game sessions and
a shooting strategy.

## Status

Under active development. The service can create and close games, process shots
against its fleet, choose its own shots, and accept their results. The
tournament arena is not implemented yet.

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

Implemented endpoints:

- `GET /health`
- `POST /game`
- `POST /game/{session_id}/opponent-shot`
- `POST /game/{session_id}/shot`
- `POST /game/{session_id}/shot/result`
- `POST /game/{session_id}/close`

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

Test modules:

- [`tests/test_fleet.py`](tests/test_fleet.py) — fleet geometry and generation
- [`tests/test_battle.py`](tests/test_battle.py) — results of opponent shots
- [`tests/test_strategy.py`](tests/test_strategy.py) — shooting strategy
- [`tests/test_health.py`](tests/test_health.py) — readiness endpoint
- [`tests/test_database.py`](tests/test_database.py) — PostgreSQL persistence
- [`tests/test_games.py`](tests/test_games.py) — game API integration
- [`tests/test_concurrency.py`](tests/test_concurrency.py) — parallel session isolation and timing
