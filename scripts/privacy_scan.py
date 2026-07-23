#!/usr/bin/env python3
"""Privacy gate for public test fixtures and generated test artifacts.

The scanner is intentionally conservative for data files. It rejects private
network addresses, credentials, hardware identifiers and Home Assistant entity
IDs. Source code is not scanned by default because neutral test entities are
part of the testbench implementation; public fixtures must contain roles only.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import sys
from typing import Iterable

PRIVATE_IPV4 = re.compile(
    r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
    r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"
)
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]{8,})?\b")
BEARER = re.compile(r"(?i)\bauthorization\s*[:=]\s*bearer\s+\S+")
MAC = re.compile(r"(?i)\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b")
HA_ENTITY = re.compile(
    r"\b(?:sensor|binary_sensor|number|input_number|input_text|input_boolean|"
    r"input_select|switch|select|weather|device_tracker|person)\."
    r"(?!test_|example_|se_replay_)[a-z0-9_]+\b"
)
CREDENTIAL_KEYS = {
    "access_token",
    "refresh_token",
    "token",
    "password",
    "api_key",
    "apikey",
    "secret",
    "client_secret",
}
IDENTIFIER_KEYS = {
    "serial_number",
    "serial",
    "device_id",
    "account_id",
    "user_id",
    "mac",
    "host",
    "hostname",
    "ip_address",
    "entity_id",
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    excerpt: str


def _excerpt(text: str, start: int, width: int = 100) -> str:
    line = text[max(0, text.rfind("\n", 0, start) + 1) : text.find("\n", start) if "\n" in text[start:] else len(text)]
    return line.strip()[:width]


def _regex_findings(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    rules = {
        "private_ipv4": PRIVATE_IPV4,
        "jwt": JWT,
        "bearer_token": BEARER,
        "mac_address": MAC,
        "home_assistant_entity_id": HA_ENTITY,
    }
    for rule, pattern in rules.items():
        for match in pattern.finditer(text):
            findings.append(
                Finding(
                    path=str(path),
                    line=text.count("\n", 0, match.start()) + 1,
                    rule=rule,
                    excerpt=_excerpt(text, match.start()),
                )
            )
    return findings


def _json_key_findings(path: Path, value: object, trail: tuple[str, ...] = ()) -> list[Finding]:
    findings: list[Finding] = []
    if isinstance(value, dict):
        for raw_key, item in value.items():
            key = str(raw_key).lower()
            current = (*trail, str(raw_key))
            if key in CREDENTIAL_KEYS:
                findings.append(
                    Finding(str(path), 1, "credential_key", ".".join(current))
                )
            if key in IDENTIFIER_KEYS:
                findings.append(
                    Finding(str(path), 1, "private_identifier_key", ".".join(current))
                )
            findings.extend(_json_key_findings(path, item, current))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_json_key_findings(path, item, (*trail, str(index))))
    return findings


def scan_file(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8", errors="replace")
    findings = _regex_findings(path, text)
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            findings.append(Finding(str(path), 1, "invalid_json", "JSON parsing failed"))
        else:
            findings.extend(_json_key_findings(path, payload))
    return findings


def iter_files(paths: Iterable[Path]) -> Iterable[Path]:
    allowed = {".json", ".jsonl", ".csv", ".yaml", ".yml", ".txt", ".log"}
    for path in paths:
        if path.is_file() and path.suffix.lower() in allowed:
            yield path
        elif path.is_dir():
            for candidate in sorted(path.rglob("*")):
                if candidate.is_file() and candidate.suffix.lower() in allowed:
                    yield candidate


def scan_paths(paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_files(paths):
        findings.extend(scan_file(path))
    return findings


def self_test() -> None:
    bad = "\n".join(
        [
            "host=192.168.1.20",
            "Authorization: Bearer secret-token",
            "sensor.private_roof_power",
            "AA:BB:CC:DD:EE:FF",
            "eyJhbGciOiJIUzI1NiJ9.abcdefghijk.signature",
        ]
    )
    rules = {item.rule for item in _regex_findings(Path("self-test.txt"), bad)}
    expected = {
        "private_ipv4",
        "bearer_token",
        "home_assistant_entity_id",
        "mac_address",
        "jwt",
    }
    missing = expected - rules
    if missing:
        raise RuntimeError(f"privacy scanner self-test missed rules: {sorted(missing)}")


def write_report(path: Path, findings: list[Finding], scanned: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "pass": not findings,
                "scanned": scanned,
                "finding_count": len(findings),
                "findings": [asdict(item) for item in findings],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("testbench/fixtures")])
    parser.add_argument("--report", type=Path, default=Path("artifacts/privacy-report.json"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()

    findings = scan_paths(args.paths)
    scanned = [str(path) for path in iter_files(args.paths)]
    write_report(args.report, findings, scanned)

    for item in findings:
        message = f"{item.rule}: {item.excerpt}"
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::error file={item.path},line={item.line},title=Privacy gate::{message}")
        else:
            print(f"{item.path}:{item.line}: {message}", file=sys.stderr)

    print(
        json.dumps(
            {
                "pass": not findings,
                "scanned_files": len(scanned),
                "finding_count": len(findings),
                "report": str(args.report),
            },
            ensure_ascii=False,
        )
    )
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
