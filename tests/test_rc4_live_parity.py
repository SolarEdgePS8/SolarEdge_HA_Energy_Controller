from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_all_public_packages_match_verified_live_export() -> None:
    manifest = json.loads(
        (ROOT / "validation/live_package_sha256_rc4.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == "0.1.0-rc.4"

    expected = {item["path"]: item["sha256"] for item in manifest["files"]}
    actual_files = sorted((ROOT / "package").glob("se_controller_*.yaml"))
    actual_paths = {path.relative_to(ROOT).as_posix() for path in actual_files}

    assert len(actual_files) == 18
    assert actual_paths == set(expected)

    for relative, digest in expected.items():
        path = ROOT / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, relative
