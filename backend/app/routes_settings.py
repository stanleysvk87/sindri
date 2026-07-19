from fastapi import APIRouter, Depends

from app.audit import recent
from app.auth import require_auth
from app.db import get_conn

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_auth)])


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
