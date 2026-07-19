import json
import subprocess

from .base import AIEngineError, ProviderUnavailableError

UNAVAILABLE_API_STATUSES = {401, 403, 429, 500, 502, 503, 529}


class ClaudeCLIProvider:
    name = "claude_cli"

    def complete(self, prompt: str) -> str:
        # POZOR: prompt musi byt HNED za -p, rovnaky dovod ako v Muninn
        # ai_engine/claude_cli.py -- ziadny variadicky flag (--add-dir a
        # pod.) tu ale ani nepouzivame, kedze negenerujeme z ziadneho
        # suboru, len z textu.
        try:
            proc = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise ProviderUnavailableError(f"claude -p zlyhalo: {exc}") from exc

        if proc.returncode != 0:
            try:
                error_envelope = json.loads(proc.stdout)
            except json.JSONDecodeError:
                error_envelope = None
            if error_envelope and error_envelope.get("api_error_status") in UNAVAILABLE_API_STATUSES:
                raise ProviderUnavailableError(
                    f"claude -p API chyba {error_envelope.get('api_error_status')}: "
                    f"{error_envelope.get('result')}"
                )
            raise AIEngineError(f"claude -p vrátilo chybu: {proc.stderr[:500]}")

        try:
            outer = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise AIEngineError(f"claude -p vrátilo neplatný JSON obal: {exc}") from exc

        result_text = outer.get("result") or ""
        if not result_text:
            raise AIEngineError("claude -p vrátilo prázdnu odpoveď")
        return result_text
