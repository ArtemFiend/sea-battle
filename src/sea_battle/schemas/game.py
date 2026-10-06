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


class ShotResponse(BaseModel):
    coordinate: str


class ShotResultRequest(BaseModel):
    result: str


class AcceptedResponse(BaseModel):
    status: Literal["accepted"] = "accepted"


class ClosedResponse(BaseModel):
    status: Literal["closed"] = "closed"
