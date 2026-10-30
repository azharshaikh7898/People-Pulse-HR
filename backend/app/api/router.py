from fastapi import APIRouter

from app.api import analytics, auth, employees, leaves, onboarding

api_router = APIRouter(prefix="/api")
for module in (auth, employees, leaves, onboarding, analytics):
    api_router.include_router(module.router)
