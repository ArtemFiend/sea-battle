import uuid
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from sea_battle.db.models import GameSession
from sea_battle.db.session import get_db_session
from sea_battle.domain.battle import ShotResult, resolve_opponent_shot
from sea_battle.domain.fleet import FleetValidationError, generate_fleet
from sea_battle.domain.strategy import (
    NoAvailableShotsError,
    choose_shot,
    update_targeting,
)
from sea_battle.schemas.game import (
    AcceptedResponse,
    CoordinateRequest,
    CreateGameResponse,
    ShipResponse,
    ShotResponse,
    ShotResultRequest,
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


@router.post("/{session_id}/shot", response_model=ShotResponse)
async def make_shot(
    session_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ShotResponse:
    game = await _get_active_game(session_id, session)
    if game.pending_shot is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Previous shot result has not been received",
        )

    fired = [shot["coordinate"] for shot in game.outgoing_shots]
    try:
        coordinate, remaining_targets = choose_shot(fired, game.target_queue)
    except NoAvailableShotsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    game.pending_shot = coordinate
    game.target_queue = remaining_targets
    game.outgoing_shots = [
        *game.outgoing_shots,
        {"coordinate": coordinate, "result": None},
    ]
    await _commit(session)
    return ShotResponse(coordinate=coordinate)


@router.post(
    "/{session_id}/shot/result",
    response_model=AcceptedResponse,
)
async def accept_shot_result(
    session_id: uuid.UUID,
    request: ShotResultRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AcceptedResponse:
    game = await _get_active_game(session_id, session)
    if request.result not in {"miss", "hit", "killed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Result must be miss, hit, or killed",
        )
    result = cast(ShotResult, request.result)
    if game.pending_shot is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is no pending shot",
        )

    pending_shot = game.pending_shot
    shot_history = [shot.copy() for shot in game.outgoing_shots]
    if (
        not shot_history
        or shot_history[-1]["coordinate"] != pending_shot
        or shot_history[-1]["result"] is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shot history is inconsistent",
        )
    shot_history[-1]["result"] = result
    fired = [shot["coordinate"] for shot in shot_history]
    target_hits, target_queue = update_targeting(
        pending_shot,
        result,
        game.target_hits,
        game.target_queue,
        fired,
    )

    game.outgoing_shots = shot_history
    game.pending_shot = None
    game.target_hits = target_hits
    game.target_queue = target_queue
    await _commit(session)
    return AcceptedResponse()
