from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sea_battle.api.games import router as games_router
from sea_battle.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sea Battle API",
        version="0.1.0",
    )

    app.include_router(health_router)
    app.include_router(games_router)

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        _request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": error.errors()},
        )

    return app


app = create_app()
