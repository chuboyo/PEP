from fastapi import APIRouter

from app.api.v1 import (
    assignments,
    auth,
    health,
    organizations,
    player,
    players,
    questionnaires,
    routines,
    teams,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(teams.router)
api_router.include_router(questionnaires.router)
api_router.include_router(assignments.router)
api_router.include_router(routines.router)
api_router.include_router(player.router)
api_router.include_router(players.router)
