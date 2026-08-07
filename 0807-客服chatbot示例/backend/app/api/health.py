"""GET /api/health"""
from __future__ import annotations

from fastapi import APIRouter

from app.models import HealthResponse

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
