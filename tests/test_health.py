from collections.abc import AsyncGenerator
from typing import Any

from fastapi.testclient import TestClient

from sea_battle.db.session import get_db_session
from sea_battle.main import app


client = TestClient(app)


class FakeSession:
    def __init__(self) -> None:
        self.executed_query: str | None = None

    async def execute(self, statement: Any) -> None:
        self.executed_query = str(statement)


def test_health_check_queries_database() -> None:
    fake_session = FakeSession()

    async def override_db_session() -> AsyncGenerator[FakeSession, None]:
        yield fake_session

    app.dependency_overrides[get_db_session] = override_db_session
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert fake_session.executed_query == "SELECT 1"
