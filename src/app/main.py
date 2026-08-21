import uvicorn
from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.catalog import router as catalog_router
from app.api.routes.orders import router as orders_router
from app.api.routes.owner_catalog import router as owner_catalog_router
from app.api.routes.owner_analytics import router as owner_analytics_router
from app.api.routes.owner_notifications import router as owner_notifications_router
from app.api.routes.owner_orders import router as owner_orders_router
from app.api.routes.owner_users import router as owner_users_router
from app.api.routes.stripe_webhooks import router as stripe_webhooks_router
from app.api.routes.user import router as user_router

from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(title="Tony Shrimp API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(catalog_router)
    app.include_router(orders_router)
    app.include_router(owner_catalog_router)
    app.include_router(owner_analytics_router)
    app.include_router(owner_notifications_router)
    app.include_router(owner_orders_router)
    app.include_router(owner_users_router)
    app.include_router(stripe_webhooks_router)
    app.include_router(user_router)

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
