#!/usr/bin/env bash
set -Eeuo pipefail

STAGE="${1:-unknown-stage}"
shift || true
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_ROOT="${SE_TEST_ARTIFACTS:-$ROOT/artifacts}/failure-bundles"
WORK="$(mktemp -d)"
DEST="$WORK/$STAGE"
ARCHIVE="$OUT_ROOT/${STAGE}.tar.gz"

cleanup() {
  rm -rf "$WORK"
}
trap cleanup EXIT

mkdir -p "$DEST" "$OUT_ROOT"

if [ "$#" -eq 0 ]; then
  set -- "$ROOT/artifacts"
fi

for source in "$@"; do
  if [ -e "$source" ]; then
    base="$(basename "$source")"
    cp -a "$source" "$DEST/$base"
  fi
done

{
  printf 'stage=%s\n' "$STAGE"
  printf 'created_utc=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'github_sha=%s\n' "${GITHUB_SHA:-local}"
  printf 'github_run_id=%s\n' "${GITHUB_RUN_ID:-local}"
  printf 'github_job=%s\n' "${GITHUB_JOB:-local}"
  if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    printf 'git_head=%s\n' "$(git -C "$ROOT" rev-parse HEAD)"
    git -C "$ROOT" status --short
  fi
} > "$DEST/context.txt"

python3 - "$DEST" <<'PY'
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
files = []
for path in sorted(root.rglob("*")):
    if not path.is_file() or path.name == "manifest.json":
        continue
    files.append(
        {
            "path": str(path.relative_to(root)),
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
(root / "manifest.json").write_text(
    json.dumps({"files": files, "count": len(files)}, indent=2) + "\n",
    encoding="utf-8",
)
PY

tar -C "$WORK" -czf "$ARCHIVE" "$STAGE"
printf 'Failure bundle: %s\n' "$ARCHIVE"
if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
  printf '::error title=%s failed::Failure bundle created at %s\n' "$STAGE" "$ARCHIVE"
fi
