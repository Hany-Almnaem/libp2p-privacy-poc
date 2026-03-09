"""Unit tests for demo web API/app contracts (socket-free)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from libp2p_privacy_poc.demo_web.models import DemoWebConfig
from libp2p_privacy_poc.demo_web.server import DemoWebApp, match_run_api_path


class _FakeRunner:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def run_full_demo(self):
        run_id = "fake-run"
        run_dir = self._base_dir / "demo_reports" / "web" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        server_log = run_dir / "zk_serve.log"
        analyze_log = run_dir / "analyze.log"
        dial_log = run_dir / "zk_dial.log"
        pin_log = run_dir / "pin.log"
        fetch_log = run_dir / "fetch.log"
        report_json = run_dir / "report.json"
        summary_json = run_dir / "summary.json"

        server_log.write_text("server up\n", encoding="utf-8")
        analyze_log.write_text("analysis done\n", encoding="utf-8")
        dial_log.write_text("dial done\n", encoding="utf-8")
        pin_log.write_text("pin ok\n", encoding="utf-8")
        fetch_log.write_text("fetch ok\n", encoding="utf-8")

        report_payload = {
            "report_id": "demo-report",
            "privacy_report": {
                "statistics": {
                    "unique_peers": 9,
                    "total_connections": 12,
                }
            },
            "snark_phase2b_proofs": [
                {"statement": "membership_v2", "verified": True, "prove_mode": "real"},
                {"statement": "continuity_v2", "verified": True, "prove_mode": "real"},
                {"statement": "unlinkability_v2", "verified": True, "prove_mode": "real"},
            ],
        }
        report_json.write_text(json.dumps(report_payload), encoding="utf-8")

        summary = {
            "run_id": run_id,
            "status": "success",
            "message": "Demo orchestration completed successfully.",
            "pin": {
                "mode_requested": "prefer-live",
                "backend_used": "mock",
                "fell_back_to_mock": True,
                "pin_results": [
                    {
                        "statement": "membership",
                        "schema": 2,
                        "depth": 16,
                        "verify_ok": True,
                        "cid": "bafy-test",
                        "error": None,
                    }
                ],
            },
            "artifacts": {
                "run_dir": str(run_dir),
                "server_log": str(server_log),
                "analyze_log": str(analyze_log),
                "dial_log": str(dial_log),
                "pin_log": str(pin_log),
                "fetch_log": str(fetch_log),
                "report_json": str(report_json),
                "summary_json": str(summary_json),
            },
        }
        summary_json.write_text(json.dumps(summary), encoding="utf-8")
        return summary


def _config() -> DemoWebConfig:
    return DemoWebConfig(
        host="127.0.0.1",
        port=8080,
        assets_dir="privacy_circuits/params",
        analyze_duration=20,
        zk_timeout=120,
        traffic_nodes=12,
        pin_mode="prefer-live",
        log_level="warning",
    )


def _wait_until_complete(app: DemoWebApp, run_id: str, timeout_s: float = 2.0):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        payload = app.get_run_payload(run_id)
        assert payload is not None
        if payload["status"] != "running":
            return payload
        time.sleep(0.01)
    raise AssertionError("run did not finish in time")


def test_match_run_api_path() -> None:
    assert match_run_api_path("/api/runs/r1") == ("r1", "run", "")
    assert match_run_api_path("/api/runs/r1/logs/analyze") == (
        "r1",
        "log",
        "analyze",
    )
    assert match_run_api_path("/api/runs/r1/artifacts/report.json") == (
        "r1",
        "artifact",
        "report.json",
    )
    assert match_run_api_path("/api/health") is None


def test_demo_web_app_run_lifecycle_and_payload_contract(tmp_path: Path) -> None:
    app = DemoWebApp(_config(), runner_factory=lambda: _FakeRunner(tmp_path))

    started = app.start_run()
    assert started["status"] == "running"
    assert started["run_id"].startswith("web-")

    payload = _wait_until_complete(app, started["run_id"])
    assert payload["status"] == "success"
    assert "summary" in payload
    assert "report" in payload
    assert payload["report"]["report_id"] == "demo-report"
    assert len(payload["report"]["snark_phase2b_proofs"]) == 3


def test_demo_web_app_resolve_logs_and_artifacts(tmp_path: Path) -> None:
    app = DemoWebApp(_config(), runner_factory=lambda: _FakeRunner(tmp_path))
    run_id = app.start_run()["run_id"]
    _wait_until_complete(app, run_id)

    analyze_log = app.resolve_log_path(run_id, "analyze")
    assert analyze_log.read_text(encoding="utf-8") == "analysis done\n"

    report_path = app.resolve_artifact_path(run_id, "report.json")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["report_id"] == "demo-report"


def test_demo_web_static_ui_contract() -> None:
    static_dir = Path("libp2p_privacy_poc/demo_web/static")
    index_html = (static_dir / "index.html").read_text(encoding="utf-8")
    app_js = (static_dir / "app.js").read_text(encoding="utf-8")

    assert "Run Full Demo" in index_html
    assert "/api/runs" in app_js
    assert "/api/runs/${currentRunId}/logs/" in app_js
