"""Compatibility routes exposing /analyze endpoints at the root path.

These simply delegate to the existing handlers defined in
`api.routes.interview` which are mounted under the /interview prefix.
This keeps the frontend compatible with older paths that post to
`/analyze` or `/analyze/upload`.
"""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, File

from api.routes import interview as interview_route

router = APIRouter()


@router.post("/analyze/upload")
async def analyze_upload(file: UploadFile = File(...)):
    # delegate to interview.analyze_upload
    return await interview_route.analyze_upload(file)


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    # delegate to interview.analyze (which itself delegates to analyze_upload)
    return await interview_route.analyze(file)
