"""API forward helper for edge gateway."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest
from verge_edge.forward import forward_to_api


class _Handler(BaseHTTPRequestHandler):
    received: list[dict] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode())
        _Handler.received.append({
            "path": self.path,
            "body": body,
            "headers": dict(self.headers),
        })
        self.send_response(200)
        self.end_headers()

    def log_message(self, *_args) -> None:
        return


@pytest.fixture
def api_server():
    _Handler.received = []
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_forward_reading(api_server: str) -> None:
    forward_to_api(
        api_server,
        {
            "type": "reading",
            "ts": "2025-01-13T07:00:00+00:00",
            "sensorId": "LEL-04",
            "kind": "gas-lel",
            "unit": "%LEL",
            "zoneId": "B-04",
            "value": 91.5,
            "traceId": "edge-trace-12345678",
        },
    )
    assert _Handler.received[0]["path"] == "/api/readings/ingest"
    assert _Handler.received[0]["body"]["sensorId"] == "LEL-04"
    assert _Handler.received[0]["headers"]["X-Verge-Trace-Id"] == "edge-trace-12345678"


def test_forward_permit(api_server: str) -> None:
    forward_to_api(
        api_server,
        {
            "type": "permit",
            "permitId": "PW-EDGE-1",
            "kind": "hot-work",
            "zoneId": "B-04",
            "validFrom": "2025-01-13T06:40:00+00:00",
            "validTo": "2025-01-13T10:40:00+00:00",
        },
    )
    assert _Handler.received[0]["path"] == "/api/permits/upsert"
    assert _Handler.received[0]["body"]["permitId"] == "PW-EDGE-1"
