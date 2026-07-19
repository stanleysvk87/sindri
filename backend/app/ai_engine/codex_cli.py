import subprocess
import tempfile
from pathlib import Path

from .base import AIEngineError, ProviderUnavailableError

UNAVAILABLE_STDERR_SIGNALS = (
    "authentication",
    "unauthorized",
    "401",
    "403",
    "429",
    "rate limit",
    "quota",
    "no such file or directory",
)


def _is_unavailable(stderr: str) -> bool:
    lowered = stderr.lower()
    return any(signal in lowered for signal in UNAVAILABLE_STDERR_SIGNALS)


class CodexCLIProvider:
    name = "codex_cli"

    def complete(self, prompt: str) -> str:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as out_f:
            output_path = Path(out_f.name)

        # POZOR: prompt musi byt HNED za "exec", rovnaky dovod ako v
        # Muninn ai_engine/codex_cli.py.
        cmd = [
            "codex",
            "exec",
            prompt,
            "-s",
            "read-only",
            "--skip-git-repo-check",
            "--ephemeral",
            "-o",
            str(output_path),
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise ProviderUnavailableError(f"codex exec zlyhalo: {exc}") from exc

        if proc.returncode != 0:
            output_path.unlink(missing_ok=True)
            if _is_unavailable(proc.stderr or ""):
                raise ProviderUnavailableError(f"codex exec vrátilo chybu: {proc.stderr[:500]}")
            raise AIEngineError(f"codex exec vrátilo chybu: {proc.stderr[:500]}")

        try:
            result_text = output_path.read_text()
        finally:
            output_path.unlink(missing_ok=True)

        if not result_text.strip():
            raise AIEngineError("codex exec vrátilo prázdnu odpoveď")
        return result_text
