"""Minimal HTTP server for the local web dashboard (Step 1 skeleton)."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from .models import DemoWebConfig


def run_demo_server(config: DemoWebConfig) -> None:
    """Run the minimal dashboard server until interrupted."""
    config.validate()
    static_dir = Path(__file__).resolve().parent / "static"
    handler_cls = _build_handler(config, static_dir)
    server = ThreadingHTTPServer((config.host, config.port), handler_cls)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def _build_handler(config: DemoWebConfig, static_dir: Path):
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index.html"):
                self._send_file(static_dir / "index.html", "text/html; charset=utf-8")
                return
            if self.path == "/app.js":
                self._send_file(
                    static_dir / "app.js",
                    "application/javascript; charset=utf-8",
                )
                return
            if self.path == "/styles.css":
                self._send_file(
                    static_dir / "styles.css",
                    "text/css; charset=utf-8",
                )
                return
            if self.path == "/api/health":
                payload = {
                    "status": "ok",
                    "mode": "skeleton",
                    "config": config.as_dict(),
                }
                self._send_json(payload, status=HTTPStatus.OK)
                return
            self._send_json(
                {"error": "not found", "path": self.path},
                status=HTTPStatus.NOT_FOUND,
            )

        def log_message(self, fmt: str, *args) -> None:  # noqa: A003
            return None

        def _send_file(self, path: Path, content_type: str) -> None:
            if not path.exists() or not path.is_file():
                self._send_json({"error": "file missing"}, status=HTTPStatus.NOT_FOUND)
                return
            data = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_json(self, payload: dict, status: HTTPStatus) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return _Handler

