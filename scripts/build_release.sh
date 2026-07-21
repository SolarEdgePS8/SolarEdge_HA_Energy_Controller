#!/usr/bin/env bash
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/dist}"
VERSION="${2:-0.1.0-rc.2}"

python3 "$ROOT/audit/readonly_audit.py" "$ROOT" --release-gate

python3 - "$ROOT" "$OUT" "$VERSION" <<'PY'
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
version = sys.argv[3]
out.mkdir(parents=True, exist_ok=True)

name = f"SolarEdge_HA_Energy_Controller_v{version}"
zip_path = out / f"{name}.zip"
sha_path = out / f"{name}.zip.sha256"

with tempfile.TemporaryDirectory(prefix="se_controller_release_") as tmp:
    stage = Path(tmp) / "SolarEdge_HA_Energy_Controller"
    shutil.copytree(
        root,
        stage,
        ignore=shutil.ignore_patterns(
            ".git", ".github", ".pytest_cache", "tests",
            "requirements-dev.txt", "dist", "build", "__pycache__", "*.pyc",
            "site_config.env", "private_migration_values.env",
            "*.zip", "*.tar.gz",
        ),
    )

    for stale in [
        stage / "validation/release_manifest.json",
        stage / "validation/SHA256SUMS",
    ]:
        stale.unlink(missing_ok=True)

    files = sorted(
        p for p in stage.rglob("*")
        if p.is_file()
        and p.relative_to(stage).as_posix() not in {
            "validation/release_manifest.json",
            "validation/SHA256SUMS",
        }
    )

    entries = []
    sums = []
    for path in files:
        rel = path.relative_to(stage).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append({
            "path": rel,
            "size": path.stat().st_size,
            "sha256": digest,
        })
        sums.append(f"{digest}  {rel}")

    manifest = {
        "project": "SolarEdge_HA_Energy_Controller",
        "version": version,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "files": entries,
    }
    (stage / "validation/release_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (stage / "validation/SHA256SUMS").write_text(
        "\n".join(sums) + "\n",
        encoding="utf-8",
    )

    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in stage.rglob("*") if p.is_file()):
            archive.write(path, arcname=f"SolarEdge_HA_Energy_Controller/{path.relative_to(stage).as_posix()}")

digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
sha_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")
print(zip_path)
print(sha_path)
PY
