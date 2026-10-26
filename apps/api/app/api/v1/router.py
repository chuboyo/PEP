from fastapi import APIRouter

from app.api.v1 import auth, health, organizations, teams

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(teams.router)
