"""API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import actions, decisions, evidence, insights, interviews, participants, projects, recruitment, system

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(projects.router)
api_router.include_router(participants.router)
api_router.include_router(recruitment.router)
api_router.include_router(interviews.router)
api_router.include_router(evidence.router)
api_router.include_router(insights.router)
api_router.include_router(decisions.router)
api_router.include_router(actions.router)
