import uvicorn
from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router


def create_app() -> FastAPI:
    app = FastAPI(title="Tony Shrimp API", version="0.1.0")

    app.include_router(health_router)
    app.include_router(auth_router)

    return app


app = create_app()


def run() -> None:
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        app_dir="src",
    )
