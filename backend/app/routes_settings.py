import os

from fastapi import APIRouter, Depends, HTTPException

from app.audit import recent
from app.auth import require_auth
from app.db import get_conn
from app.machines import get_machine
from app.models import AIConfigUpdate, HostStatusRequest
from app.remote_exec import RemoteExecError, run_remote
from app.settings_store import get_setting, set_setting

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_auth)])

HOST_STATUS_SCRIPT = """\
echo "Host: $(hostname)"
uptime
echo
echo "Disk /:"
df -h / | tail -1
echo
free -h
echo
echo "Docker kontajnery bežia: $(docker ps -q 2>/dev/null | wc -l)"
"""


@router.get("/audit-log")
def audit_log(limit: int = 100):
    return {"entries": recent(limit)}


@router.get("/stats")
def stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM scripts").fetchone()["c"]
        by_source = conn.execute(
            "SELECT source_type, COUNT(*) c FROM scripts GROUP BY source_type"
        ).fetchall()
        by_host = conn.execute(
            "SELECT host, COUNT(*) c FROM scripts WHERE host != '' GROUP BY host"
        ).fetchall()
        secrets = conn.execute(
            "SELECT COUNT(*) c FROM scripts WHERE has_possible_secret = 1"
        ).fetchone()["c"]
    return {
        "total_scripts": total,
        "by_source_type": {r["source_type"]: r["c"] for r in by_source},
        "by_host": {r["host"]: r["c"] for r in by_host},
        "possible_secrets": secrets,
    }


@router.get("/ai")
def get_ai_config():
    mode = get_setting("ai_provider_mode") or os.environ.get("SINDRI_AI_PROVIDER_MODE", "auto")
    has_db_key = bool(get_setting("ai_anthropic_api_key"))
    has_env_key = bool(os.environ.get("SINDRI_ANTHROPIC_API_KEY"))
    return {
        "provider_mode": mode,
        # never echo the key itself back, only whether one is configured
        "has_api_key": has_db_key or has_env_key,
        "api_key_source": "settings" if has_db_key else ("env" if has_env_key else None),
    }


@router.put("/ai")
def update_ai_config(payload: AIConfigUpdate):
    if payload.provider_mode is not None:
        set_setting("ai_provider_mode", payload.provider_mode)
    if payload.anthropic_api_key is not None:
        set_setting("ai_anthropic_api_key", payload.anthropic_api_key)
    return get_ai_config()


@router.post("/host-status")
def host_status(payload: HostStatusRequest):
    """Reuses the same SSH plumbing as remote-exec, just with a fixed
    read-only diagnostic script instead of a catalog script -- no new
    privileged host mount needed (no /proc, no docker.sock) to show
    "how's the machine this runs on doing", since the machine itself is
    reachable the same way any other registered machine is."""
    machine = get_machine(payload.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    try:
        return run_remote(machine, HOST_STATUS_SCRIPT, None)
    except RemoteExecError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
