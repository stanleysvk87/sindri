from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_auth
from app.models import SandboxRunRequest
from app.sandbox import SandboxError, run_in_sandbox, sandbox_status

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"], dependencies=[Depends(require_auth)])


@router.get("/status")
def status():
    return sandbox_status()


@router.post("/run")
def run(payload: SandboxRunRequest):
    try:
        return run_in_sandbox(payload.content, payload.script_type)
    except SandboxError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
