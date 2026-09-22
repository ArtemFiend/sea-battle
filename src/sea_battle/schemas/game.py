import uuid
from typing import Literal

from pydantic import BaseModel


class ShipResponse(BaseModel):
    coordinates: list[str]


class CreateGameResponse(BaseModel):
    session_id: uuid.UUID
    ships: list[ShipResponse]


class CoordinateRequest(BaseModel):
    coordinate: str


class ShotResultResponse(BaseModel):
    result: Literal["miss", "hit", "killed"]
