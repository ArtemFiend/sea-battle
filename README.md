# Sea Battle

REST service for a networked Battleship game with persistent game sessions and
a shooting strategy.

## Status

The service can create and close games, process shots against its fleet, choose
its own shots, and accept their results. The arena can conduct full matches,
detect invalid fleets and dishonest responses, enforce a one-second response
timeout, and run a round-robin tournament.

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
- [`tests/test_arena_match.py`](tests/test_arena_match.py) — complete matches, rule enforcement, timeouts, and round-robin tournament
- [`tests/test_arena_http.py`](tests/test_arena_http.py) — malformed and non-contract HTTP responses
- [`tests/test_arena_integration.py`](tests/test_arena_integration.py) — full match through FastAPI and PostgreSQL

## Tournament arena

Start each participant service on its own localhost port, then pass their names
and base URLs to the arena:

```bash
uv run python -m sea_battle.arena \
  --service alpha=http://localhost:8001 \
  --service bravo=http://localhost:8002 \
  --service charlie=http://localhost:8003
```

Every service plays every other service once. A win is worth one point. The
arena verifies the fleet and every shot result against the announced fleet,
awards a match to the opponent after an invalid response or timeout, and prints
all match results followed by the standings.
