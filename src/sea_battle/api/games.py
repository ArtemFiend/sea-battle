from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from sea_battle.db.models import GameSession
from sea_battle.db.session import get_db_session
from sea_battle.domain.fleet import generate_fleet
from sea_battle.schemas.game import CreateGameResponse, ShipResponse

router = APIRouter(prefix="/game", tags=["game"])


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

    try:
        await session.commit()
    except SQLAlchemyError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create game session",
        ) from error

    return CreateGameResponse(session_id=game.id, ships=ships)
