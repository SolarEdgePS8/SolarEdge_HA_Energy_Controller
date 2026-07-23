from __future__ import annotations

import json
from pathlib import Path

from scripts.render_test_stage_summary import STAGES, effective_status, render


def test_success_explains_what_was_checked_and_what_green_means() -> None:
    text = render(STAGES["model"], "success")

    assert "✅ Steuerungslogik und Grenzfälle: BESTANDEN" in text
    assert "Was wird hier geprüft?" in text
    assert "Was bedeutet dieses Ergebnis?" in text
    assert "Was ist jetzt zu tun?" in text
    assert "echten EVOpt-Fail-open-Fehler" in text
    assert "Live-Test" in text


def test_failure_gives_a_concrete_next_step() -> None:
    text = render(STAGES["ha-smoke"], "failure")

    assert "❌ Home Assistant startet mit dem Package: NICHT BESTANDEN" in text
    assert "ERROR" in text
    assert "Invalid config" in text


def test_nonblocking_stable_failure_is_shown_as_warning(tmp_path: Path) -> None:
    status_file = tmp_path / "artifacts" / "stable-preview" / "status.json"
    status_file.parent.mkdir(parents=True)
    status_file.write_text(
        json.dumps({"pass": False, "smoke_exit": 0, "replay_exit": 1}),
        encoding="utf-8",
    )

    status = effective_status("stable-preview", "success", tmp_path)
    text = render(STAGES["stable-preview"], status)

    assert status == "warning"
    assert "⚠️ Vorschau auf die aktuelle HA-Stable-Version: WARNUNG – PRÜFEN" in text
    assert "blockiert bewusst noch nicht" in text


def test_successful_stable_preview_stays_green(tmp_path: Path) -> None:
    status_file = tmp_path / "artifacts" / "stable-preview" / "status.json"
    status_file.parent.mkdir(parents=True)
    status_file.write_text(json.dumps({"pass": True}), encoding="utf-8")

    assert effective_status("stable-preview", "success", tmp_path) == "success"
