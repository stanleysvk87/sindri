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


def to_host_path(container_path: str) -> str:
    """Translate an in-container key path back to the path it has on the
    real host, for display in copy-paste commands the user runs in their
    own terminal (outside this container) -- e.g. for the
    "copy as SSH command" button. Relies on docker-compose.yml mounting
    ${HOME}/.ssh at SSH_KEYS_DIR and setting the container's own HOME to
    mirror the real host HOME (see docker-compose.yml comments). Falls
    back to the unchanged container path if it isn't under SSH_KEYS_DIR,
    so a manually-typed path doesn't get silently mangled."""
    host_home = os.environ.get("HOME", "")
    if not host_home or not container_path.startswith(str(SSH_KEYS_DIR) + "/"):
        return container_path
    return f"{host_home}/.ssh/{container_path[len(str(SSH_KEYS_DIR)) + 1:]}"


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
