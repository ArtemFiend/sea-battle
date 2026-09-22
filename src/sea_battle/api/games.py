import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from sea_battle.db.models import GameSession
from sea_battle.db.session import get_db_session
from sea_battle.domain.battle import resolve_opponent_shot
from sea_battle.domain.fleet import FleetValidationError, generate_fleet
from sea_battle.schemas.game import (
    CoordinateRequest,
    CreateGameResponse,
    ShipResponse,
    ShotResultResponse,
)

router = APIRouter(prefix="/game", tags=["game"])


async def _get_active_game(
    session_id: uuid.UUID,
    session: AsyncSession,
) -> GameSession:
    game = await session.get(GameSession, session_id)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game session not found",
        )
    if game.status != "active":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Game session is finished",
        )
    return game


async def _commit(session: AsyncSession) -> None:
    try:
        await session.commit()
    except SQLAlchemyError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        ) from error


@router.post("", response_model=CreateGameResponse, status_code=status.HTTP_201_CREATED)
async def create_game(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CreateGameResponse:
    fleet = generate_fleet()
    ships = [
        ShipResponse(coordinates=list(coordinates)) for coordinates in fleet
    ]
    game = GameSession(fleet=[ship.model_dump() for ship in ships])
    session.add(game)

    await _commit(session)

    return CreateGameResponse(session_id=game.id, ships=ships)


@router.post(
    "/{session_id}/opponent-shot",
    response_model=ShotResultResponse,
)
async def process_opponent_shot(
    session_id: uuid.UUID,
    request: CoordinateRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ShotResultResponse:
    game = await _get_active_game(session_id, session)
    fleet = [ship["coordinates"] for ship in game.fleet]

    try:
        result = resolve_opponent_shot(
            fleet,
            game.received_shots,
            request.coordinate,
        )
    except FleetValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    if request.coordinate not in game.received_shots:
        game.received_shots = [*game.received_shots, request.coordinate]
        await _commit(session)

    return ShotResultResponse(result=result)
