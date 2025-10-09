"""Health check route(s)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
async def healthz():
    """Simple readiness probe returning status JSON."""
    return {"status": "ok"}
