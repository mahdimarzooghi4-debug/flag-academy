from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from sqlalchemy import text

from app.academy.api import router as academy_router
from app.curriculum.api import router as curriculum_router
from app.db import engine
from app.errors import AppError, app_error_handler
from app.identity.api import router as identity_router
from app.read_models.api import router as read_models_router

app = FastAPI(title="Parcham OS API", version="0.1.0")
app.add_exception_handler(AppError, app_error_handler)

app.include_router(identity_router)
app.include_router(curriculum_router)
app.include_router(academy_router)
app.include_router(read_models_router)


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.get("/health", tags=["platform"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["platform"])
async def ready() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ready"}
