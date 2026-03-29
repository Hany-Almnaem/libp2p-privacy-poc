"""HTTP server for the local judge-facing demo dashboard."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import urlparse

from .models import DemoWebConfig
from .runner import DemoRunner

_ALLOWED_LOGS = {
    "server": "server_log",
    "analyze": "analyze_log",
    "dial": "dial_log",
    "pin": "pin_log",
    "fetch": "fetch_log",
}

_ALLOWED_ARTIFACTS = {
    "report.json": "report_json",
    "summary.json": "summary_json",
}


class DemoWebApp:
    """In-memory run manager for dashboard API endpoints."""

    def __init__(
        self,
        config: DemoWebConfig,
        *,
        runner_factory: Optional[Callable[[], DemoRunner]] = None,
    ) -> None:
        self._config = config
        self._runner_factory = runner_factory or (lambda: DemoRunner(self._config))
        self._lock = threading.Lock()
        self._runs: Dict[str, Dict[str, Any]] = {}

    def health(self) -> Dict[str, Any]:
        with self._lock:
            run_count = len(self._runs)
            active = sum(1 for run in self._runs.values() if run["status"] == "running")
        return {
            "status": "ok",
            "mode": "dashboard",
            "config": self._config.as_dict(),
            "runs": {"total": run_count, "active": active},
        }

    def start_run(self) -> Dict[str, Any]:
        run_id = _new_run_id()
        record: Dict[str, Any] = {
            "run_id": run_id,
            "status": "running",
            "message": "Run started",
            "started_at": _utc_now(),
            "finished_at": None,
            "summary": None,
            "thread": None,
        }
        with self._lock:
            self._runs[run_id] = record

        thread = threading.Thread(
            target=self._run_worker,
            args=(run_id,),
            daemon=True,
            name=f"demo-web-run-{run_id}",
        )
        record["thread"] = thread
        thread.start()
        return self.get_run_payload(run_id) or {
            "run_id": run_id,
            "status": "running",
            "message": "Run started",
        }

    def get_run_payload(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return None
            payload = {
                "run_id": record["run_id"],
                "status": record["status"],
                "message": record["message"],
                "started_at": record["started_at"],
                "finished_at": record["finished_at"],
                "config": self._config.as_dict(),
            }
            summary = record.get("summary")

        if summary:
            payload["summary"] = summary
            report = self._load_report(summary)
            if report is not None:
                payload["report"] = report
        return payload

    def resolve_log_path(self, run_id: str, name: str) -> Path:
        return self._resolve_artifact_path(run_id, name, _ALLOWED_LOGS)

    def resolve_artifact_path(self, run_id: str, name: str) -> Path:
        return self._resolve_artifact_path(run_id, name, _ALLOWED_ARTIFACTS)

    def _run_worker(self, run_id: str) -> None:
        try:
            summary = self._runner_factory().run_full_demo()
            status = str(summary.get("status", "failed"))
            message = str(summary.get("message", "Run finished"))
        except Exception as exc:  # pragma: no cover - defensive
            summary = None
            status = "failed"
            message = f"Runner error: {exc}"

        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return
            record["status"] = status
            record["message"] = message
            record["finished_at"] = _utc_now()
            record["summary"] = summary

    def _resolve_artifact_path(
        self,
        run_id: str,
        name: str,
        allowed_map: Dict[str, str],
    ) -> Path:
        key = allowed_map.get(name)
        if key is None:
            raise KeyError("unsupported file name")

        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                raise FileNotFoundError("run not found")
            summary = record.get("summary")
            if not isinstance(summary, dict):
                raise FileNotFoundError("run summary is not ready")
            artifacts = summary.get("artifacts")
            if not isinstance(artifacts, dict):
                raise FileNotFoundError("artifact map missing")
            raw_path = artifacts.get(key)
            run_dir_raw = artifacts.get("run_dir")

        if not isinstance(raw_path, str) or not raw_path:
            raise FileNotFoundError("artifact path missing")
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError("artifact file missing")

        if isinstance(run_dir_raw, str) and run_dir_raw:
            run_dir = Path(run_dir_raw).resolve()
            resolved = path.resolve()
            try:
                resolved.relative_to(run_dir)
            except ValueError as exc:
                raise PermissionError("artifact path escapes run directory") from exc
        return path

    @staticmethod
    def _load_report(summary: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        artifacts = summary.get("artifacts")
        if not isinstance(artifacts, dict):
            return None
        report_path = artifacts.get("report_json")
        if not isinstance(report_path, str) or not report_path:
            return None
        path = Path(report_path)
        if not path.exists() or not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None


def run_demo_server(config: DemoWebConfig) -> None:
    """Run the dashboard server until interrupted."""
    config.validate()
    server, _app = create_demo_http_server(config)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def create_demo_http_server(
    config: DemoWebConfig,
    *,
    runner_factory: Optional[Callable[[], DemoRunner]] = None,
) -> Tuple[ThreadingHTTPServer, DemoWebApp]:
    """Create HTTP server and app manager; useful for tests."""
    static_dir = Path(__file__).resolve().parent / "static"
    app = DemoWebApp(config, runner_factory=runner_factory)
    handler_cls = _build_handler(config, static_dir, app)
    server = ThreadingHTTPServer((config.host, config.port), handler_cls)
    return server, app


def _build_handler(config: DemoWebConfig, static_dir: Path, app: DemoWebApp):
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            if path in ("/", "/index.html"):
                self._send_file(static_dir / "index.html", "text/html; charset=utf-8")
                return
            if path == "/app.js":
                self._send_file(
                    static_dir / "app.js",
                    "application/javascript; charset=utf-8",
                )
                return
            if path == "/styles.css":
                self._send_file(
                    static_dir / "styles.css",
                    "text/css; charset=utf-8",
                )
                return
            if path == "/api/health":
                self._send_json(app.health(), status=HTTPStatus.OK)
                return

            run_details = match_run_api_path(path)
            if run_details:
                run_id, endpoint_type, name = run_details
                if endpoint_type == "run":
                    payload = app.get_run_payload(run_id)
                    if payload is None:
                        self._send_json(
                            {"error": "run not found", "run_id": run_id},
                            status=HTTPStatus.NOT_FOUND,
                        )
                    else:
                        self._send_json(payload, status=HTTPStatus.OK)
                    return
                if endpoint_type == "log":
                    self._send_run_file(
                        resolver=partial(app.resolve_log_path, run_id, name),
                        content_type="text/plain; charset=utf-8",
                    )
                    return
                if endpoint_type == "artifact":
                    content_type = (
                        "application/json; charset=utf-8"
                        if name.endswith(".json")
                        else "application/octet-stream"
                    )
                    self._send_run_file(
                        resolver=partial(app.resolve_artifact_path, run_id, name),
                        content_type=content_type,
                    )
                    return

            self._send_json(
                {"error": "not found", "path": path},
                status=HTTPStatus.NOT_FOUND,
            )

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/runs":
                payload = app.start_run()
                self._send_json(payload, status=HTTPStatus.ACCEPTED)
                return
            self._send_json(
                {"error": "not found", "path": parsed.path},
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

        def _send_run_file(self, resolver: Callable[[], Path], content_type: str) -> None:
            try:
                path = resolver()
            except FileNotFoundError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
                return
            except (PermissionError, KeyError) as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
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


def match_run_api_path(path: str) -> Optional[Tuple[str, str, str]]:
    # /api/runs/{run_id}
    # /api/runs/{run_id}/logs/{name}
    # /api/runs/{run_id}/artifacts/{name}
    parts = [part for part in path.split("/") if part]
    if len(parts) == 3 and parts[0] == "api" and parts[1] == "runs":
        return parts[2], "run", ""
    if len(parts) == 5 and parts[0] == "api" and parts[1] == "runs":
        endpoint = parts[3]
        if endpoint == "logs":
            return parts[2], "log", parts[4]
        if endpoint == "artifacts":
            return parts[2], "artifact", parts[4]
    return None


def _new_run_id() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("web-%Y%m%d-%H%M%S-%f")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
