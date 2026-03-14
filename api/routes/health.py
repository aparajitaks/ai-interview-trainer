from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    """Simple liveness/health endpoint."""
    return {"status": "ok"}
