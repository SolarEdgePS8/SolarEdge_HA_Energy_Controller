#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


FIXTURES: dict[str, dict[str, Any] | str] = {
    "normal": {
        "evopt": {
            "status": "healthy",
            "solverStatus": "optimal",
            "suggestion": {"action": "normal", "charge": 0, "discharge": 0},
            "batteries": [{"title": "Test Battery", "controllable": True}],
            "plan": [{"start": "2026-07-22T12:00:00+02:00", "action": "normal"}],
        }
    },
    "holdcharge": {
        "evopt": {
            "status": "healthy",
            "solverStatus": "optimal",
            "suggestion": {"action": "holdcharge", "charge": 0, "discharge": 0},
            "batteries": [{"title": "Test Battery", "controllable": True}],
            "plan": [
                {"start": "2026-07-22T12:00:00+02:00", "action": "holdcharge"}
            ],
        }
    },
    "charge": {
        "evopt": {
            "status": "healthy",
            "solverStatus": "optimal",
            "suggestion": {"action": "charge", "charge": 5000, "discharge": 0},
            "batteries": [{"title": "Test Battery", "controllable": True}],
            "plan": [{"start": "2026-07-22T12:00:00+02:00", "action": "charge"}],
        }
    },
    "discharge": {
        "evopt": {
            "status": "healthy",
            "solverStatus": "optimal",
            "suggestion": {"action": "discharge", "charge": 0, "discharge": 3000},
            "batteries": [{"title": "Test Battery", "controllable": True}],
            "plan": [
                {"start": "2026-07-22T12:00:00+02:00", "action": "discharge"}
            ],
        }
    },
    "stale": {
        "evopt": {
            "status": "stale",
            "solverStatus": "optimal",
            "suggestion": {"action": "normal"},
            "batteries": [{"title": "Test Battery", "controllable": True}],
            "plan": [],
        }
    },
    "missing_evopt": {"site": {"title": "Synthetic site"}},
    "multiple_batteries": {
        "evopt": {
            "status": "healthy",
            "solverStatus": "optimal",
            "suggestion": {"action": "normal"},
            "batteries": [
                {"title": "Test Battery", "controllable": True},
                {"title": "Second Battery", "controllable": True},
            ],
            "plan": [],
        }
    },
    "not_controllable": {
        "evopt": {
            "status": "healthy",
            "solverStatus": "optimal",
            "suggestion": {"action": "normal"},
            "batteries": [{"title": "Test Battery", "controllable": False}],
            "plan": [],
        }
    },
    "invalid_json": "{not-json",
    # Transport-level fixtures are explicitly selectable so the testbench can
    # reproduce API outages without any external network or real evcc instance.
    "http_404": {"error": "synthetic not found"},
    "http_500": {"error": "synthetic server error"},
    "timeout": {"error": "synthetic delayed response"},
}


class ScenarioState:
    def __init__(self, scenario: str = "normal") -> None:
        if scenario not in FIXTURES:
            raise ValueError(scenario)
        self._scenario = scenario
        self._lock = threading.Lock()

    def set(self, scenario: str) -> None:
        if scenario not in FIXTURES:
            raise KeyError(scenario)
        with self._lock:
            self._scenario = scenario

    def get(self) -> str:
        with self._lock:
            return self._scenario


class FakeEvccServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], scenario: str = "normal") -> None:
        self.scenarios = ScenarioState(scenario)
        super().__init__(address, FakeEvccHandler)


class FakeEvccHandler(BaseHTTPRequestHandler):
    server: FakeEvccServer

    def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            # Expected when the timeout test deliberately closes the client.
            return

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/healthz":
            self._send(HTTPStatus.OK, b'{"status":"ok"}')
            return
        if path == "/api/state":
            scenario = self.server.scenarios.get()
            if scenario == "http_404":
                self._send(HTTPStatus.NOT_FOUND, b'{"error":"synthetic"}')
                return
            if scenario == "http_500":
                self._send(HTTPStatus.INTERNAL_SERVER_ERROR, b'{"error":"synthetic"}')
                return
            if scenario == "timeout":
                time.sleep(1.0)
            payload = FIXTURES[scenario]
            if isinstance(payload, str):
                self._send(HTTPStatus.OK, payload.encode("utf-8"))
            else:
                self._send(
                    HTTPStatus.OK,
                    json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                )
            return
        if path == "/__scenario":
            body = json.dumps({"scenario": self.server.scenarios.get()}).encode("utf-8")
            self._send(HTTPStatus.OK, body)
            return
        self._send(HTTPStatus.NOT_FOUND, b'{"error":"not found"}')

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        prefix = "/__scenario/"
        if not path.startswith(prefix):
            self._send(HTTPStatus.NOT_FOUND, b'{"error":"not found"}')
            return
        scenario = path[len(prefix) :]
        try:
            self.server.scenarios.set(scenario)
        except KeyError:
            self._send(HTTPStatus.BAD_REQUEST, b'{"error":"unknown scenario"}')
            return
        self._send(HTTPStatus.OK, json.dumps({"scenario": scenario}).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7070)
    parser.add_argument("--scenario", choices=sorted(FIXTURES), default="normal")
    args = parser.parse_args()
    server = FakeEvccServer((args.host, args.port), args.scenario)
    print(f"fake-evcc listening on {args.host}:{args.port} scenario={args.scenario}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
