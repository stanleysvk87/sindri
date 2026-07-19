import re

CODE_FENCE_RE = re.compile(r"^```[a-zA-Z]*\n?|```$", re.MULTILINE)


def build_generate_prompt(description: str) -> str:
    return (
        "Write a single, correct, portable shell script (bash, POSIX-compatible "
        "where reasonable) that does the following:\n\n"
        f"{description}\n\n"
        "Rules: output ONLY the script content, starting with a shebang line. "
        "No markdown code fences, no explanation before or after. Use `set -euo "
        "pipefail`. Add a comment only where the reasoning isn't obvious from the "
        "code itself -- do not narrate what each line does. If Python is clearly "
        "more appropriate than bash for this task, write Python instead and start "
        "with a `#!/usr/bin/env python3` shebang."
    )


def build_review_prompt(name: str, content: str) -> str:
    return (
        f"Review this script named `{name}` for a homelab/personal script catalog. "
        "Be concise -- a handful of bullet points, not an essay. Cover, in order "
        "of importance: (1) hardcoded secrets/passwords/tokens that should be "
        "environment variables instead, (2) actual bugs or unsafe behavior "
        "(unquoted variables, missing error handling, destructive commands "
        "without confirmation), (3) portability issues if it assumes a specific "
        "distro/tool that might not be present elsewhere. If the script is fine, "
        "say so briefly instead of inventing nitpicks.\n\n"
        f"```\n{content}\n```"
    )


def strip_code_fences(text: str) -> str:
    """Defensive cleanup: models sometimes wrap output in ```bash ... ```
    even when told not to. Strip a leading/trailing fence line if present,
    leave everything else untouched."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = CODE_FENCE_RE.sub("", stripped).strip()
    return stripped
