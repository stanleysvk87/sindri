import anthropic

from .base import AIEngineError, ProviderUnavailableError

UNAVAILABLE_STATUS_CODES = {401, 403, 429, 500, 502, 503, 529}


class AnthropicAPIProvider:
    name = "anthropic_api"
    model = "claude-sonnet-5"

    def __init__(self, api_key: str):
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, prompt: str) -> str:
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIConnectionError as exc:
            raise ProviderUnavailableError(f"Anthropic API nedostupné: {exc}") from exc
        except anthropic.APIStatusError as exc:
            if exc.status_code in UNAVAILABLE_STATUS_CODES:
                raise ProviderUnavailableError(f"Anthropic API zlyhalo ({exc.status_code}): {exc}") from exc
            raise AIEngineError(f"Anthropic API zlyhalo: {exc}") from exc

        if response.stop_reason == "refusal":
            raise AIEngineError("Model odmietol požiadavku")

        text = next((b.text for b in response.content if b.type == "text"), None)
        if not text:
            raise AIEngineError("Prázdna odpoveď od API")
        return text
