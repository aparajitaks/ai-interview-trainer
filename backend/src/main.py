import os
import sys

# Ensure parent directory is in sys.path so 'src' packages can be imported when run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.ai_interview import router as ai_interview_router
from src.api.code_runner import router as code_runner_router
from src.api.evaluation import router as evaluation_router
from src.api.interview import public_router as interview_public_router
from src.api.interview import router as interview_router
from src.api.live_feedback import router as live_feedback_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview_router)
app.include_router(interview_public_router)
app.include_router(evaluation_router)
app.include_router(ai_interview_router)
app.include_router(live_feedback_router)
app.include_router(code_runner_router)


@app.get("/")
def root():
    return {"message": "AI Interview Backend Running"}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)



