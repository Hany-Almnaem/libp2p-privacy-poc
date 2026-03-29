"""Local in-process pin-service mock for demo fallback flows."""

from __future__ import annotations

import base64
import hashlib
import json
import threading
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse


class _PinMockHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_class, token: str):
        super().__init__(server_address, handler_class)
        self.token = token
        self.store: Dict[str, bytes] = {}


def _build_handler():
    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/pin":
                self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
                return
            if not self._auth_ok():
                self._send_json({"error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
                return
            body = self._read_json()
            if not isinstance(body, dict):
                self._send_json(
                    {"error": "invalid json body"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            data_b64 = body.get("data_b64")
            if not isinstance(data_b64, str):
                self._send_json(
                    {"error": "missing data_b64"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                payload = base64.b64decode(data_b64, validate=True)
            except Exception:
                self._send_json(
                    {"error": "invalid data_b64"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            cid = self._build_cid(payload)
            self._mock_server().store[cid] = payload
            self._send_json({"cid": cid}, status=HTTPStatus.OK)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/fetch":
                self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
                return
            if not self._auth_ok():
                self._send_json({"error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
                return

            qs = parse_qs(parsed.query)
            cid = (qs.get("cid") or [None])[0]
            if not isinstance(cid, str) or not cid:
                self._send_json(
                    {"error": "missing cid"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            payload = self._mock_server().store.get(cid)
            if payload is None:
                self._send_json(
                    {"error": "cid not found"},
                    status=HTTPStatus.NOT_FOUND,
                )
                return
            self._send_json(
                {"cid": cid, "data_b64": base64.b64encode(payload).decode("ascii")},
                status=HTTPStatus.OK,
            )

        def log_message(self, fmt: str, *args) -> None:  # noqa: A003
            return None

        def _auth_ok(self) -> bool:
            header = self.headers.get("Authorization", "")
            expected = f"Bearer {self._mock_server().token}"
            return header == expected

        def _read_json(self) -> Optional[dict]:
            length_raw = self.headers.get("Content-Length", "")
            try:
                length = int(length_raw)
            except ValueError:
                return None
            if length < 0:
                return None
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                return None
            return payload if isinstance(payload, dict) else None

        def _send_json(self, payload: dict, status: HTTPStatus) -> None:
            body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
                "utf-8"
            )
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        @staticmethod
        def _build_cid(payload: bytes) -> str:
            digest = hashlib.sha256(payload).hexdigest()
            return f"bafy{digest[:56]}"

        def _mock_server(self) -> _PinMockHTTPServer:
            return self.server  # type: ignore[return-value]

    return _Handler


@dataclass
class PinMockServer:
    host: str = "127.0.0.1"
    port: int = 0
    token: str = "demo-web-mock-token"
    _server: Optional[_PinMockHTTPServer] = field(default=None, init=False, repr=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False, repr=False)

    def start(self) -> None:
        if self._server is not None:
            return
        handler_cls = _build_handler()
        self._server = _PinMockHTTPServer((self.host, self.port), handler_cls, self.token)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._server = None

    @property
    def endpoint(self) -> str:
        if self._server is None:
            raise RuntimeError("pin mock server is not running")
        host, port = self._server.server_address
        return f"http://{host}:{port}"
