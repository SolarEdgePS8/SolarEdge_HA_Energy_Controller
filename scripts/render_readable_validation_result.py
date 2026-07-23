#!/usr/bin/env python3
"""Run lightweight repository checks and render a plain-language Markdown result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml


ROOTS_PYTHON = ("audit", "scripts", "tests", "testbench", "custom_components")
ROOTS_SHELL = ("scripts", "audit", "tools")
SKIP_PARTS = {".git", ".pytest_cache", "artifacts", "dist", "extracted", "__pycache__"}


class LenientLoader(yaml.SafeLoader):
    """Accept Home-Assistant-specific YAML tags while still parsing the file."""


def construct_unknown(loader: LenientLoader, node: yaml.Node) -> Any:
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return None


LenientLoader.add_constructor(None, construct_unknown)


def files(root: Path, patterns: tuple[str, ...], bases: tuple[str, ...] | None = None) -> list[Path]:
    search_roots = [root / name for name in bases] if bases else [root]
    result: list[Path] = []
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for pattern in patterns:
            for path in search_root.rglob(pattern):
                if path.is_file() and not any(part in SKIP_PARTS for part in path.parts):
                    result.append(path)
    return sorted(set(result))


def check_yaml(root: Path) -> tuple[int, list[str]]:
    paths = files(root, ("*.yaml", "*.yml"))
    errors: list[str] = []
    for path in paths:
        try:
            yaml.load(path.read_text(encoding="utf-8"), Loader=LenientLoader)
        except yaml.MarkedYAMLError as exc:
            mark = getattr(exc, "problem_mark", None)
            line = mark.line + 1 if mark else "?"
            column = mark.column + 1 if mark else "?"
            problem = getattr(exc, "problem", None) or str(exc).splitlines()[0]
            errors.append(f"{path.relative_to(root)}:{line}:{column}: {problem}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path.relative_to(root)}: {type(exc).__name__}: {exc}")
    return len(paths), errors


def check_python(root: Path) -> tuple[int, list[str]]:
    paths = files(root, ("*.py",), ROOTS_PYTHON)
    errors: list[str] = []
    for path in paths:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            errors.append(
                f"{path.relative_to(root)}:{exc.lineno or '?'}:{exc.offset or '?'}: {exc.msg}"
            )
    return len(paths), errors


def check_shell(root: Path) -> tuple[int, list[str]]:
    paths = files(root, ("*.sh",), ROOTS_SHELL)
    errors: list[str] = []
    for path in paths:
        result = subprocess.run(
            ["bash", "-n", str(path)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            detail = (result.stderr or result.stdout or "Syntaxfehler").strip()
            errors.append(f"{path.relative_to(root)}: {detail}")
    return len(paths), errors


def check_release_gate(root: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "audit/readonly_audit.py", ".", "--release-gate"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    combined = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    return result.returncode == 0, combined


def package_count(root: Path) -> int:
    return len(list((root / "package").glob("*.yaml")))


def section(title: str, count: int, errors: list[str]) -> list[str]:
    ok = not errors
    lines = [f"### {'✅' if ok else '❌'} {title}", "", f"Geprüfte Dateien: **{count}**"]
    if errors:
        lines.extend(["", "Gefundene Fehler:"])
        lines.extend(f"- `{error}`" for error in errors[:20])
        if len(errors) > 20:
            lines.append(f"- … und {len(errors) - 20} weitere Fehler")
    else:
        lines.extend(["", "Keine Fehler gefunden."])
    lines.append("")
    return lines


def render(root: Path) -> tuple[str, bool]:
    yaml_count, yaml_errors = check_yaml(root)
    python_count, python_errors = check_python(root)
    shell_count, shell_errors = check_shell(root)
    release_ok, release_output = check_release_gate(root)
    packages = package_count(root)
    packages_ok = packages == 18
    passed = not yaml_errors and not python_errors and not shell_errors and release_ok and packages_ok

    lines = [
        "# Verständlicher Schnelltest",
        "",
        f"## {'✅ BESTANDEN' if passed else '❌ FEHLGESCHLAGEN'}",
        "",
        "Dieser Bericht prüft lesbar, ob die Dateien grundsätzlich installierbar sind. "
        "Der ausführliche 96-Stunden-Bericht wird zusätzlich im Deep Testbench erzeugt.",
        "",
        "### Ergebnis auf einen Blick",
        "",
        f"- {'✅' if not yaml_errors else '❌'} YAML-Dateien lesbar: **{yaml_count - len(yaml_errors)} von {yaml_count}**",
        f"- {'✅' if not python_errors else '❌'} Python-Dateien syntaktisch korrekt: **{python_count - len(python_errors)} von {python_count}**",
        f"- {'✅' if not shell_errors else '❌'} Shell-Skripte syntaktisch korrekt: **{shell_count - len(shell_errors)} von {shell_count}**",
        f"- {'✅' if packages_ok else '❌'} Controller-Pakete vorhanden: **{packages} von 18**",
        f"- {'✅' if release_ok else '❌'} Read-only Release-Gate: **{'bestanden' if release_ok else 'fehlgeschlagen'}**",
        "",
    ]
    lines.extend(section("YAML-Prüfung", yaml_count, yaml_errors))
    lines.extend(section("Python-Prüfung", python_count, python_errors))
    lines.extend(section("Shell-Prüfung", shell_count, shell_errors))

    lines.extend(["### Read-only Release-Gate", ""])
    if release_ok:
        lines.append("✅ Architektur, Single-Writer-Verträge, Manifest und Release-Regeln sind konsistent.")
    else:
        lines.append("❌ Das Release-Gate ist fehlgeschlagen. Die letzten Ausgaben:")
        lines.append("")
        lines.append("```text")
        lines.extend(release_output.splitlines()[-40:])
        lines.append("```")
    lines.extend(
        [
            "",
            "### Einordnung",
            "",
            "- Ein YAML-Fehler wird mit **Datei, Zeile und Spalte** angezeigt.",
            "- Ein grüner Schnelltest bedeutet noch nicht, dass alle vier Modi 24 Stunden korrekt laufen.",
            "- Dafür ist der separate Bericht **Deep SolarEdge Controller Testbench** maßgeblich.",
        ]
    )
    return "\n".join(lines) + "\n", passed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    report, passed = render(root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(report)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
