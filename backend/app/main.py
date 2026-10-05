from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.academy.api import router as academy_router
from app.config import get_settings
from app.curriculum.api import router as curriculum_router
from app.db import engine
from app.errors import AppError, app_error_handler
from app.evidence.api import router as evidence_router
from app.identity.api import router as identity_router
from app.learning.api import router as learning_router
from app.mission_design.api import router as mission_design_router
from app.mission_runtime.api import router as mission_runtime_router
from app.observability import configure_observability
from app.read_models.api import router as read_models_router

settings = get_settings()
app = FastAPI(title="Parcham OS API", version="0.3.0")
app.add_exception_handler(AppError, app_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(identity_router)
app.include_router(evidence_router)
app.include_router(curriculum_router)
app.include_router(academy_router)
app.include_router(learning_router)
app.include_router(mission_design_router)
app.include_router(mission_runtime_router)
app.include_router(read_models_router)
configure_observability(app)


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
