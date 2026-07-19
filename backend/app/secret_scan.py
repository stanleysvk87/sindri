import re

# Deliberately loose heuristics, not a security scanner -- just enough to
# put a "double-check before sharing this" badge on the catalog entry.
# False positives are fine (over-warn); false negatives just mean no badge.
_PATTERNS = [
    re.compile(r"(?i)\b(pass(word)?|passwd|pwd)\s*[:=]\s*['\"][^'\"]{4,}"),
    re.compile(r"(?i)\b(token|api[_-]?key|secret|apikey)\s*[:=]\s*['\"][^'\"]{6,}"),
    re.compile(r"(?i)\bbot\d{6,}:[a-zA-Z0-9_-]{20,}"),  # Telegram bot token shape
    re.compile(r"(?i)\bBearer\s+[a-zA-Z0-9._-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(AKIA|ASIA)[0-9A-Z]{16}\b"),  # AWS access key id shape
]


def looks_like_it_has_a_secret(content: str) -> bool:
    return any(p.search(content) for p in _PATTERNS)
