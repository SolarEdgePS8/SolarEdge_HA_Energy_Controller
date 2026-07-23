from __future__ import annotations

import json
import socket
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from testbench.fake_evcc.app import FIXTURES, FakeEvccServer


@pytest.fixture()
def fake_evcc() -> str:
    server = FakeEvccServer(("127.0.0.1", 0), "normal")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _json(url: str, *, method: str = "GET", timeout: float = 3) -> dict:
    request = Request(url, method=method)
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def test_all_documented_evopt_actions_and_failures_are_available() -> None:
    assert {
        "normal",
        "holdcharge",
        "charge",
        "discharge",
        "stale",
        "missing_evopt",
        "multiple_batteries",
        "not_controllable",
        "invalid_json",
        "http_404",
        "http_500",
        "timeout",
    } <= set(FIXTURES)


def test_fake_evcc_serves_and_switches_scenarios(fake_evcc: str) -> None:
    payload = _json(fake_evcc + "/api/state")
    assert payload["evopt"]["suggestion"]["action"] == "normal"

    switched = _json(fake_evcc + "/__scenario/holdcharge", method="POST")
    assert switched == {"scenario": "holdcharge"}
    payload = _json(fake_evcc + "/api/state")
    assert payload["evopt"]["suggestion"]["action"] == "holdcharge"


def test_fake_evcc_exposes_health_endpoint(fake_evcc: str) -> None:
    assert _json(fake_evcc + "/healthz") == {"status": "ok"}


def test_unknown_scenario_is_rejected(fake_evcc: str) -> None:
    with pytest.raises(HTTPError) as exc:
        _json(fake_evcc + "/__scenario/not-a-scenario", method="POST")
    assert exc.value.code == 400


def test_invalid_json_fixture_is_really_invalid(fake_evcc: str) -> None:
    _json(fake_evcc + "/__scenario/invalid_json", method="POST")
    with urlopen(fake_evcc + "/api/state", timeout=3) as response:
        body = response.read().decode("utf-8")
    with pytest.raises(json.JSONDecodeError):
        json.loads(body)


@pytest.mark.parametrize("scenario,status", [("http_404", 404), ("http_500", 500)])
def test_fake_evcc_returns_selectable_http_errors(
    fake_evcc: str, scenario: str, status: int
) -> None:
    _json(fake_evcc + f"/__scenario/{scenario}", method="POST")
    with pytest.raises(HTTPError) as exc:
        _json(fake_evcc + "/api/state")
    assert exc.value.code == status


def test_fake_evcc_can_reproduce_a_client_timeout(fake_evcc: str) -> None:
    _json(fake_evcc + "/__scenario/timeout", method="POST")
    with pytest.raises((TimeoutError, socket.timeout, URLError)):
        _json(fake_evcc + "/api/state", timeout=0.05)
