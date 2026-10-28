from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.seed import ensure_questionnaire_templates, ensure_superadmin

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Uses SessionLocal (database_url), not get_db — so dependency overrides
    # cannot redirect this. Tests disable superadmin seed and seed pep_test
    # via fixtures; templates are seeded into the app DB on startup.
    db = SessionLocal()
    try:
        if get_settings().seed_superadmin_on_startup:
            ensure_superadmin(db)
        ensure_questionnaire_templates(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Pep API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")
