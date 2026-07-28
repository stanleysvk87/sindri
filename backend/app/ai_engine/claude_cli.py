import json
import subprocess

from .base import AIEngineError, ProviderUnavailableError

UNAVAILABLE_API_STATUSES = {401, 403, 429, 500, 502, 503, 529}


class ClaudeCLIProvider:
    name = "claude_cli"

    def complete(self, prompt: str) -> str:
        # NOTE: the prompt must come IMMEDIATELY after -p, same reason as
        # in Muninn's ai_engine/claude_cli.py -- though no variadic flag
        # (--add-dir etc.) is used here at all, since nothing is
        # generated from a file, only from text.
        #
        # --disallowedTools: without it, claude sometimes reads "write a
        # script" as a task to write a FILE and returns a "I need
        # permission to write a file" narrative instead of plain text
        # (found while testing 2026-07-19). Denying Write/Edit/Bash/Read
        # forces a clean text answer with no tool attempt.
        try:
            proc = subprocess.run(
                [
                    "claude", "-p", prompt,
                    "--output-format", "json",
                    "--disallowedTools", "Write,Edit,Bash,Read",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise ProviderUnavailableError(f"claude -p failed: {exc}") from exc

        if proc.returncode != 0:
            try:
                error_envelope = json.loads(proc.stdout)
            except json.JSONDecodeError:
                error_envelope = None
            if error_envelope and error_envelope.get("api_error_status") in UNAVAILABLE_API_STATUSES:
                raise ProviderUnavailableError(
                    f"claude -p API error {error_envelope.get('api_error_status')}: "
                    f"{error_envelope.get('result')}"
                )
            raise AIEngineError(f"claude -p returned an error: {proc.stderr[:500]}")

        try:
            outer = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise AIEngineError(f"claude -p returned an invalid JSON envelope: {exc}") from exc

        result_text = outer.get("result") or ""
        if not result_text:
            raise AIEngineError("claude -p returned an empty response")
        return result_text
