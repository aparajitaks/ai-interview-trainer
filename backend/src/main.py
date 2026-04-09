from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.ai_interview import router as ai_interview_router
from src.api.code_runner import router as code_runner_router
from src.api.evaluation import router as evaluation_router
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
