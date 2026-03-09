"""Unit tests for demo web runner orchestration helpers."""

from __future__ import annotations

from pathlib import Path

from libp2p_privacy_poc.demo_web.models import DemoWebConfig
from libp2p_privacy_poc.demo_web.runner import (
    DemoRunner,
    classify_run_status,
    extract_analyzer_multiaddr,
    extract_server_multiaddr,
)


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


def test_extract_server_multiaddr() -> None:
    text = (
        "Peer ID: QmServer\n"
        "Listening: /ip4/127.0.0.1/tcp/50140/p2p/QmServer\n"
        "Serving privacyzk protocol.\n"
    )
    assert (
        extract_server_multiaddr(text)
        == "/ip4/127.0.0.1/tcp/50140/p2p/QmServer"
    )


def test_extract_analyzer_multiaddr() -> None:
    text = "✓ Listening on: /ip4/127.0.0.1/tcp/50158/p2p/QmAnalyzer\n"
    assert (
        extract_analyzer_multiaddr(text)
        == "/ip4/127.0.0.1/tcp/50158/p2p/QmAnalyzer"
    )


def test_classify_run_status() -> None:
    assert classify_run_status(core_error=False, fallback_detected=False)[0] == "success"
    assert classify_run_status(core_error=False, fallback_detected=True)[0] == "fallback"
    assert classify_run_status(core_error=True, fallback_detected=False)[0] == "failed"


def test_runner_command_building_and_sequence(tmp_path: Path) -> None:
    runner = DemoRunner(
        _config(),
        root_dir=tmp_path,
        python_executable="/tmp/fake-python",
    )
    assert runner.planned_step_names() == ("zk-serve", "analyze", "zk-dial")

    serve_cmd = runner._build_zk_serve_cmd()
    assert serve_cmd[:3] == ["/tmp/fake-python", "-m", "libp2p_privacy_poc.cli"]
    assert "zk-serve" in serve_cmd
    assert "--prove-mode" in serve_cmd
    assert "real" in serve_cmd

    report_path = tmp_path / "demo_reports" / "web" / "r1" / "report.json"
    analyze_cmd = runner._build_analyze_cmd(
        "/ip4/127.0.0.1/tcp/50140/p2p/QmServer", report_path
    )
    assert "analyze" in analyze_cmd
    assert "--zk-statement" in analyze_cmd
    assert "all" in analyze_cmd
    assert str(report_path) in analyze_cmd

    dial_cmd = runner._build_zk_dial_cmd("/ip4/127.0.0.1/tcp/50158/p2p/QmAnalyzer")
    assert "zk-dial" in dial_cmd
    assert "--count" in dial_cmd
    assert "12" in dial_cmd
    assert "--peer" in dial_cmd


def test_runner_fails_when_server_multiaddr_missing(monkeypatch, tmp_path: Path) -> None:
    class _FakeProc:
        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0

        def terminate(self):
            return None

        def kill(self):
            return None

    runner = DemoRunner(
        _config(),
        root_dir=tmp_path,
        python_executable="/tmp/fake-python",
    )

    monkeypatch.setattr(runner, "_start_process", lambda cmd, log_path: _FakeProc())
    monkeypatch.setattr(
        runner,
        "_wait_for_server_multiaddr",
        lambda log_path, timeout_seconds, process: None,
    )

    result = runner.run_full_demo()
    assert result["status"] == "failed"
    assert "failed to parse server multiaddr" in result["message"]
    assert Path(result["artifacts"]["summary_json"]).exists()

