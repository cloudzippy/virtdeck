from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth, health, vms
from app.core.db import init_db
from app.core.logging import configure_logging

configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Dev convenience only; production schema changes go through Alembic migrations.
    init_db()
    yield


app = FastAPI(title="VirtDeck API", lifespan=lifespan)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router)
app.include_router(vms.router)
