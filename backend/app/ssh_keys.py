"""Lists SSH private keys already mounted from the host, so the
"add machine" form is a dropdown of what's already there instead of a
free-text path -- the app never generates or stores key material itself,
per the user's explicit call: use existing keys unless they deliberately
add a new one (which, for now, means bind-mounting it in
docker-compose.yml the same way, not through this app)."""

import os
from pathlib import Path

SSH_KEYS_DIR = Path(os.environ.get("SINDRI_SSH_KEYS_DIR", "/home/sindri/.ssh-host"))
NON_KEY_NAMES = {"known_hosts", "config", "authorized_keys"}


def list_available_keys() -> list[str]:
    if not SSH_KEYS_DIR.is_dir():
        return []
    keys = []
    for path in sorted(SSH_KEYS_DIR.iterdir()):
        if not path.is_file():
            continue
        if path.suffix == ".pub" or path.name in NON_KEY_NAMES:
            continue
        try:
            first_line = path.read_text(errors="ignore").splitlines()[0]
        except (IndexError, OSError):
            continue
        if "PRIVATE KEY" in first_line:
            keys.append(str(path))
    return keys
