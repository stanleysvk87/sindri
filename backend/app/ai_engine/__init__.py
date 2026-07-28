import os
import shutil

from app.settings_store import get_setting

from .anthropic_api import AnthropicAPIProvider
from .base import AIProvider, AIEngineError, ProviderUnavailableError
from .claude_cli import ClaudeCLIProvider
from .codex_cli import CodexCLIProvider

__all__ = [
    "AIProvider",
    "AIEngineError",
    "ProviderUnavailableError",
    "complete",
    "get_provider",
    "get_provider_chain",
    "ai_status",
]


def _claude_cli() -> AIProvider | None:
    return ClaudeCLIProvider() if shutil.which("claude") else None


def _codex_cli() -> AIProvider | None:
    return CodexCLIProvider() if shutil.which("codex") else None


def _anthropic_api() -> AIProvider | None:
    # DB-stored key (set via Settings UI) wins over the env var, so a key
    # can be added/rotated without redeploying the container.
    api_key = get_setting("ai_anthropic_api_key") or os.environ.get("SINDRI_ANTHROPIC_API_KEY", "")
    return AnthropicAPIProvider(api_key) if api_key else None


def get_provider_chain() -> list[AIProvider]:
    """Candidate providers in priority order. Mode "auto" (default) tries
    whatever's actually available on this host/container -- CLI logins
    reuse an existing subscription at no extra cost, the API key is only
    a fallback for hosts without claude/codex installed. See
    docs/AI_FEATURES.md."""
    mode = get_setting("ai_provider_mode") or os.environ.get("SINDRI_AI_PROVIDER_MODE", "auto")

    if mode == "claude_cli":
        candidates = [_claude_cli()]
    elif mode == "codex_cli":
        candidates = [_codex_cli()]
    elif mode == "anthropic_api":
        candidates = [_anthropic_api()]
    else:
        candidates = [_claude_cli(), _codex_cli(), _anthropic_api()]

    return [p for p in candidates if p is not None]


_NO_PROVIDER_MESSAGE = (
    "No AI provider is available -- install/log in to the claude or codex "
    "CLI on the host, or set SINDRI_ANTHROPIC_API_KEY."
)


def complete(prompt: str) -> tuple[str, str]:
    """Run `prompt` through the provider chain and return (text, provider
    name). A provider that can't be reached at all (missing binary, auth
    failure, rate limit, timeout -> ProviderUnavailableError) falls
    through to the next candidate; a provider that ran fine but produced
    a bad answer (plain AIEngineError) does not, because retrying it
    elsewhere would just repeat the same work.

    This is what makes mode "auto" actually mean what its docstring and
    the README claim. Before, get_provider() returned chain[0] and no
    caller ever iterated, so a rate-limited claude CLI made every AI call
    fail with 503 even when a perfectly good API key was configured."""
    chain = get_provider_chain()
    if not chain:
        raise AIEngineError(_NO_PROVIDER_MESSAGE)

    last_error: AIEngineError | None = None
    for provider in chain:
        try:
            return provider.complete(prompt), provider.name
        except ProviderUnavailableError as exc:
            last_error = exc
            continue
    raise AIEngineError(
        f"No AI provider could handle the request (tried: "
        f"{', '.join(p.name for p in chain)}). Last error: {last_error}"
    )


def get_provider() -> AIProvider:
    """First available provider, without fallback -- kept for callers that
    only need to name the provider (see ai_status). Use complete() for
    anything that actually sends a prompt."""
    chain = get_provider_chain()
    if not chain:
        raise AIEngineError(_NO_PROVIDER_MESSAGE)
    return chain[0]


def ai_status() -> dict:
    chain = get_provider_chain()
    if not chain:
        return {"available": False, "provider": None}
    return {"available": True, "provider": chain[0].name}
