import uuid
from dataclasses import dataclass
from typing import Protocol, cast

from httpx2 import AsyncClient

from sea_battle.domain.battle import ShotResult
from sea_battle.domain.fleet import Fleet


class ServiceProtocolError(RuntimeError):
    """Raised when a game service violates the HTTP contract."""


@dataclass(frozen=True)
class StartedGame:
    session_id: uuid.UUID
    fleet: Fleet


class GameService(Protocol):
    async def start_game(self) -> StartedGame: ...

    async def make_shot(self, session_id: uuid.UUID) -> str: ...

    async def accept_shot_result(
        self,
        session_id: uuid.UUID,
        result: ShotResult,
    ) -> None: ...

    async def process_opponent_shot(
        self,
        session_id: uuid.UUID,
        coordinate: str,
    ) -> ShotResult: ...

    async def close_game(self, session_id: uuid.UUID) -> None: ...


class HTTPGameService:
    """HTTP adapter for a service implementing the shared game contract."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 1.0,
    ) -> None:
        self._client = AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
        )

    async def __aenter__(self) -> "HTTPGameService":
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def start_game(self) -> StartedGame:
        payload = await self._request("POST", "/game", expected_status=201)
        try:
            session_id = uuid.UUID(payload["session_id"])
            ships = payload["ships"]
            fleet = tuple(
                tuple(ship["coordinates"])
                for ship in ships
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ServiceProtocolError(
                "Invalid response from POST /game"
            ) from error
        return StartedGame(session_id=session_id, fleet=fleet)

    async def make_shot(self, session_id: uuid.UUID) -> str:
        payload = await self._request(
            "POST",
            f"/game/{session_id}/shot",
            expected_status=200,
        )
        coordinate = payload.get("coordinate")
        if not isinstance(coordinate, str):
            raise ServiceProtocolError("Shot response has no coordinate")
        return coordinate

    async def accept_shot_result(
        self,
        session_id: uuid.UUID,
        result: ShotResult,
    ) -> None:
        payload = await self._request(
            "POST",
            f"/game/{session_id}/shot/result",
            expected_status=200,
            json={"result": result},
        )
        if payload.get("status") != "accepted":
            raise ServiceProtocolError("Shot result was not accepted")

    async def process_opponent_shot(
        self,
        session_id: uuid.UUID,
        coordinate: str,
    ) -> ShotResult:
        payload = await self._request(
            "POST",
            f"/game/{session_id}/opponent-shot",
            expected_status=200,
            json={"coordinate": coordinate},
        )
        result = payload.get("result")
        if result not in {"miss", "hit", "killed"}:
            raise ServiceProtocolError("Invalid opponent-shot result")
        return cast(ShotResult, result)

    async def close_game(self, session_id: uuid.UUID) -> None:
        payload = await self._request(
            "POST",
            f"/game/{session_id}/close",
            expected_status=200,
        )
        if payload.get("status") != "closed":
            raise ServiceProtocolError("Game session was not closed")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        expected_status: int,
        **kwargs: object,
    ) -> dict[str, object]:
        try:
            response = await self._client.request(method, path, **kwargs)
        except Exception as error:
            raise ServiceProtocolError(f"Request to {path} failed") from error

        if response.status_code != expected_status:
            raise ServiceProtocolError(
                f"{method} {path} returned {response.status_code}, "
                f"expected {expected_status}"
            )
        try:
            payload = response.json()
        except ValueError as error:
            raise ServiceProtocolError(f"{path} returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise ServiceProtocolError(f"{path} returned a non-object JSON body")
        return payload
