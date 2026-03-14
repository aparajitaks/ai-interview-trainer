from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
def health_check():
    """Simple liveness/health endpoint."""
    return {"status": "ok"}


@router.get("/models/status")
def models_status(request: Request):
    """Return the preload/load status of models (emotion, pose, gaze).

    The startup event in `api.main` populates `app.state.model_status` when
    `AIIT_PRELOAD_MODELS` is enabled. If not present, return an informative
    default.
    """
    status = getattr(request.app.state, "model_status", None)
    if status is None:
        return {"emotion": "unknown", "pose": "unknown", "gaze": "unknown"}
    return status
