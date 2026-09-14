import uuid

from pydantic import BaseModel


class ShipResponse(BaseModel):
    coordinates: list[str]


class CreateGameResponse(BaseModel):
    session_id: uuid.UUID
    ships: list[ShipResponse]
