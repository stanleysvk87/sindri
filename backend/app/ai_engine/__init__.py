import os
import shutil

from .anthropic_api import AnthropicAPIProvider
from .base import AIProvider, AIEngineError
from .claude_cli import ClaudeCLIProvider
from .codex_cli import CodexCLIProvider

__all__ = ["AIProvider", "AIEngineError", "get_provider", "get_provider_chain", "ai_status"]


def _claude_cli() -> AIProvider | None:
    return ClaudeCLIProvider() if shutil.which("claude") else None


def _codex_cli() -> AIProvider | None:
    return CodexCLIProvider() if shutil.which("codex") else None


def _anthropic_api() -> AIProvider | None:
    api_key = os.environ.get("SINDRI_ANTHROPIC_API_KEY", "")
    return AnthropicAPIProvider(api_key) if api_key else None


def get_provider_chain() -> list[AIProvider]:
    """Candidate providers in priority order. Mode "auto" (default) tries
    whatever's actually available on this host/container -- CLI logins
    reuse an existing subscription at no extra cost, the API key is only
    a fallback for hosts without claude/codex installed. See
    docs/AI_FEATURES.md."""
    mode = os.environ.get("SINDRI_AI_PROVIDER_MODE", "auto")

    if mode == "claude_cli":
        candidates = [_claude_cli()]
    elif mode == "codex_cli":
        candidates = [_codex_cli()]
    elif mode == "anthropic_api":
        candidates = [_anthropic_api()]
    else:
        candidates = [_claude_cli(), _codex_cli(), _anthropic_api()]

    return [p for p in candidates if p is not None]


def get_provider() -> AIProvider:
    chain = get_provider_chain()
    if not chain:
        raise AIEngineError(
            "Žiadny AI provider nie je k dispozícii — nainštaluj/prihlás sa do "
            "claude alebo codex CLI na hostiteľovi, alebo nastav "
            "SINDRI_ANTHROPIC_API_KEY."
        )
    return chain[0]


def ai_status() -> dict:
    chain = get_provider_chain()
    if not chain:
        return {"available": False, "provider": None}
    return {"available": True, "provider": chain[0].name}
