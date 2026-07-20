#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_NAME="local-info"
DEST="$ROOT/.trae/skills/$SKILL_NAME"

python3 "$ROOT/scripts/sync-codex-skills.py" \
  --skill "$SKILL_NAME" \
  --output-dir ".trae/skills"

if [ ! -f "$DEST/SKILL.md" ]; then
  echo "Missing generated skill: $DEST/SKILL.md" >&2
  exit 1
fi

echo "Installed $SKILL_NAME for this repository only:"
echo "  $DEST/SKILL.md"
echo "Restart TraeX in this repository, then use /skills to confirm it is loaded."
