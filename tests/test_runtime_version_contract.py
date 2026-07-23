from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_CHECKER = ROOT / "audit" / "runtime" / "se_controller_runtime_checker.py"
INSTALLER = ROOT / "scripts" / "install_package.sh"
README = ROOT / "README.md"


def _runtime_checker_version() -> str:
    tree = ast.parse(RUNTIME_CHECKER.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "VERSION" for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    raise AssertionError("VERSION fehlt im Runtime-Checker")


def _installer_version() -> str:
    text = INSTALLER.read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, flags=re.MULTILINE)
    assert match, "Installer schreibt keine eindeutige Runtime-Manifest-Version"
    return match.group(1)


def _readme_version() -> str:
    text = README.read_text(encoding="utf-8")
    match = re.search(r"\*\*Version: `v([^`]+)`", text)
    assert match, "README enthält keine eindeutige Projektversion"
    return match.group(1)


def test_runtime_checker_uses_same_version_as_installer_and_readme() -> None:
    checker = _runtime_checker_version()
    installer = _installer_version()
    readme = _readme_version()

    assert checker == installer == readme, (
        "Versionswiderspruch: Runtime-Checker, Installer und README müssen "
        f"denselben Stand melden; checker={checker}, installer={installer}, readme={readme}"
    )
