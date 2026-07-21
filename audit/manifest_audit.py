#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]).resolve()
manifest_path = root / "validation/release_manifest.json"
sums_path = root / "validation/SHA256SUMS"

if not manifest_path.is_file() or not sums_path.is_file():
    print("Manifest oder SHA256SUMS fehlt; Arbeitskopie statt Release-Bundle.")
    raise SystemExit(2)

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
errors = []
for entry in manifest.get("files", []):
    rel = entry["path"]
    path = root / rel
    if not path.is_file():
        errors.append(f"MISSING {rel}")
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != entry["sha256"]:
        errors.append(f"SHA256 {rel}")
    if path.stat().st_size != entry["size"]:
        errors.append(f"SIZE {rel}")

print(json.dumps({
    "project": manifest.get("project"),
    "version": manifest.get("version"),
    "files": len(manifest.get("files", [])),
    "errors": errors,
    "pass": not errors,
}, indent=2, ensure_ascii=False))
raise SystemExit(0 if not errors else 2)
