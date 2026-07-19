"""Throwaway, isolated container per test run -- explicitly NOT the same
trust boundary as the disabled remote-exec placeholder in
docs/REMOTE_EXEC.md. A sandbox run has no network, a hard memory/pid/cpu
cap, a read-only root filesystem, drops all Linux capabilities, and runs
as an unprivileged user -- so whatever the *script* does is contained.

What is NOT contained: the backend process itself needs /var/run/
docker.sock mounted in to spawn these sibling containers (Docker-outside-
of-Docker), which is itself a sensitive grant (anyone who can reach
docker.sock has host-root-equivalent power). That's a property of the
backend's own deployment, not of any individual sandbox run -- see
docs/SANDBOX.md for the full trade-off writeup. Disabled by default
(SINDRI_SANDBOX_ENABLED=false) for exactly that reason.
"""

import os
import time

SANDBOX_TIMEOUT_SECONDS = 15
MAX_OUTPUT_CHARS = 20_000
IMAGE_BY_TYPE = {
    "bash": "bash:5",
    "python": "python:3.12-slim",
}


class SandboxError(Exception):
    pass


class SandboxUnavailableError(SandboxError):
    """Feature disabled, or docker.sock isn't reachable from here."""
    pass


def sandbox_enabled() -> bool:
    return os.environ.get("SINDRI_SANDBOX_ENABLED", "false").lower() == "true"


def detect_script_type(content: str) -> str:
    first_line = content.splitlines()[0] if content.splitlines() else ""
    return "python" if "python" in first_line else "bash"


def sandbox_status() -> dict:
    if not sandbox_enabled():
        return {"available": False, "reason": "SINDRI_SANDBOX_ENABLED je false"}
    try:
        import docker

        client = docker.from_env()
        client.ping()
    except Exception as exc:  # docker.errors.DockerException + anything else from a bad socket
        return {"available": False, "reason": f"docker.sock nedostupný: {exc}"}
    return {"available": True, "reason": None}


def run_in_sandbox(content: str, script_type: str | None = None) -> dict:
    if not sandbox_enabled():
        raise SandboxUnavailableError("Sandbox je vypnutý (SINDRI_SANDBOX_ENABLED=false).")

    import docker
    from docker.errors import DockerException

    try:
        client = docker.from_env()
    except DockerException as exc:
        raise SandboxUnavailableError(f"Docker nie je dostupný z backendu: {exc}") from exc

    resolved_type = script_type if script_type in IMAGE_BY_TYPE else detect_script_type(content)
    image = IMAGE_BY_TYPE[resolved_type]
    command = ["python3", "-c", content] if resolved_type == "python" else ["bash", "-c", content]

    container = None
    timed_out = False
    exit_code = None
    stdout = ""
    stderr = ""
    start = time.monotonic()

    try:
        container = client.containers.run(
            image,
            command,
            detach=True,
            network_disabled=True,
            mem_limit="128m",
            memswap_limit="128m",
            nano_cpus=500_000_000,  # 0.5 CPU
            pids_limit=50,
            read_only=True,
            tmpfs={"/tmp": "size=16m,noexec,nosuid"},
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            user="65534:65534",  # nobody -- never root inside the sandbox
        )
        try:
            result = container.wait(timeout=SANDBOX_TIMEOUT_SECONDS)
            exit_code = result.get("StatusCode")
        except Exception:
            timed_out = True
            try:
                container.kill()
            except DockerException:
                pass

        stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
        stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
    except DockerException as exc:
        raise SandboxError(f"Sandbox spustenie zlyhalo: {exc}") from exc
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except DockerException:
                pass

    duration_ms = int((time.monotonic() - start) * 1000)
    if timed_out:
        stderr = (
            stderr + f"\n[sandbox timeout po {SANDBOX_TIMEOUT_SECONDS}s, kontajner zabitý]"
        ).strip()

    return {
        "stdout": stdout[:MAX_OUTPUT_CHARS],
        "stderr": stderr[:MAX_OUTPUT_CHARS],
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "image": image,
        "script_type": resolved_type,
    }
