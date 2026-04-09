from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(tags=["Code Runner"])


class RunCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=20000)
    input: str = Field(default="", max_length=5000)


class RunCodeResponse(BaseModel):
    output: str
    error: str
    timed_out: bool = False


@router.post("/run-code", response_model=RunCodeResponse, summary="Execute candidate code safely")
async def run_code(body: RunCodeRequest) -> RunCodeResponse:
    code = body.code.strip()
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code cannot be empty.",
        )

    with tempfile.TemporaryDirectory(prefix="ai-interview-runner-") as tmp_dir:
        tmp_path = Path(tmp_dir) / "temp.py"
        tmp_path.write_text(code, encoding="utf-8")

        env = {"PYTHONUNBUFFERED": "1", "PATH": os.getenv("PATH", "")}

        try:
            proc = subprocess.run(
                ["python3", "-I", str(tmp_path)],
                input=body.input,
                capture_output=True,
                text=True,
                cwd=tmp_dir,
                env=env,
                timeout=5,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return RunCodeResponse(
                output="",
                error="Execution timed out after 5 seconds.",
                timed_out=True,
            )

        return RunCodeResponse(
            output=(proc.stdout or "").strip(),
            error=(proc.stderr or "").strip(),
            timed_out=False,
        )

