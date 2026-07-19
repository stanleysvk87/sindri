import os

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.applog import logger, setup_logging
from app.auth import require_auth
from app.db import init_db
from app.routes_ai import router as ai_router
from app.routes_auth import router as auth_router
from app.routes_machines import router as machines_router
from app.routes_sandbox import router as sandbox_router
from app.routes_scripts import router as scripts_router
from app.routes_settings import router as settings_router

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
app.include_router(machines_router)
app.include_router(settings_router)


@app.on_event("startup")
def on_startup():
    setup_logging()
    init_db()


@app.exception_handler(Exception)
async def log_unhandled_exception(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/settings", dependencies=[Depends(require_auth)])
def get_settings():
    """remote_exec_enabled gates app/remote_exec.py's real SSH execution
    path (POST /api/scripts/{id}/remote-exec) -- see docs/REMOTE_EXEC.md
    for the safety properties (per-call sudo password, never persisted,
    only ever targets a registered machine, SSH key always mounted from
    the host not generated/stored by this app)."""
    return {
        "remote_exec_enabled": os.environ.get("SINDRI_REMOTE_EXEC_ENABLED", "false").lower()
        == "true"
    }
