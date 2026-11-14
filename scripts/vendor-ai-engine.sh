#!/bin/bash
# Builds the midgard-ai-engine wheel from the local clone into backend/vendor/ for docker build
# (the repo is private, the image cannot fetch it). Run before `docker compose build`.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC=${MIDGARD_AI_ENGINE_SRC:-$HOME/projects/midgard-ai-engine}
[ -d "$SRC" ] || { echo "missing $SRC" >&2; exit 1; }
git -C "$SRC" pull -q --ff-only 2>/dev/null || true
rm -f "$ROOT"/backend/vendor/midgard_ai_engine-*.whl
python3 -m pip wheel -q --no-deps -w "$ROOT/backend/vendor" "$SRC"
ls "$ROOT"/backend/vendor/*.whl
