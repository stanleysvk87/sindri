import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import require_auth
from app.db import init_db
from app.routes_ai import router as ai_router
from app.routes_auth import router as auth_router
from app.routes_sandbox import router as sandbox_router
from app.routes_scripts import router as scripts_router

app = FastAPI(title="sindri")

# Frontend is a static build served by the same reverse proxy (Caddy) in
# production; CORS with credentials is only needed for local `npm run dev`
# hitting the backend on a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(scripts_router)
app.include_router(ai_router)
app.include_router(sandbox_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/settings", dependencies=[Depends(require_auth)])
def get_settings():
    """remote_exec_enabled is a hard off-switch, not a per-request check --
    there is no execution code path in this app at all yet. This flag
    only exists so the frontend can render the (disabled) button and the
    intent is on record before any real implementation happens. See
    docs/REMOTE_EXEC.md: turning this on for real requires a sudo
    password verification step per call, not just flipping this env var."""
    return {
        "remote_exec_enabled": os.environ.get("SINDRI_REMOTE_EXEC_ENABLED", "false").lower()
        == "true"
    }
