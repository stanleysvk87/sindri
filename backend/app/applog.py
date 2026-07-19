"""File-backed application log, separate from audit_log (which is "what
did a user do") -- this is "what did the app itself do/break", so
errors are discoverable from Settings instead of only via `docker logs`
(which the user has to think to go look at, and won't have if this ever
runs somewhere they don't have shell access). Rotates to stay small,
lives on the persistent /data volume so it survives a container
restart."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_PATH = Path(os.environ.get("SINDRI_DB_PATH", "./data/scripts.db")).resolve().parent / "app.log"

logger = logging.getLogger("sindri")


def setup_logging():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=2)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    # also catch uvicorn's own error logger (unhandled exceptions in
    # endpoints, startup failures) without needing every route to
    # remember to log manually
    logging.getLogger("uvicorn.error").addHandler(handler)


def tail(n: int = 200) -> str:
    if not LOG_PATH.exists():
        return ""
    with open(LOG_PATH, "r", errors="replace") as f:
        lines = f.readlines()
    return "".join(lines[-n:])
