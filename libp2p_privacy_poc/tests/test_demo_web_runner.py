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
    assert runner.planned_step_names() == (
        "zk-serve",
        "analyze",
        "zk-dial",
        "pin-proof-record",
        "fetch-proof-record",
    )

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

    pin_cmd = runner._build_pin_proof_record_cmd(
        "/ip4/127.0.0.1/tcp/50140/p2p/QmServer"
    )
    assert "pin-proof-record" in pin_cmd
    assert "--statement" in pin_cmd
    assert "all" in pin_cmd
    assert "--json" in pin_cmd

    fetch_cmd = runner._build_fetch_proof_record_cmd("bafy-test")
    assert "fetch-proof-record" in fetch_cmd
    assert "--cid" in fetch_cmd
    assert "--recheck-assets-dir" in fetch_cmd


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


def test_pin_mode_prefer_live_falls_back_to_mock(monkeypatch, tmp_path: Path) -> None:
    runner = DemoRunner(
        _config(),
        root_dir=tmp_path,
        python_executable="/tmp/fake-python",
    )
    artifacts = runner._create_run_artifacts("run-fallback")
    calls = []

    def _fake_backend(*, backend, artifacts, server_multiaddr):
        calls.append(backend)
        if backend == "live":
            return {
                "backend_used": "live",
                "error": "live unavailable",
                "pin_exit_code": None,
                "fetch_exit_codes": {},
                "pin_results": [],
                "fetch_results": [],
            }
        return {
            "backend_used": "mock",
            "error": None,
            "pin_exit_code": 0,
            "fetch_exit_codes": {"bafy-mock": 0},
            "pin_results": [
                {
                    "statement": "membership",
                    "schema": 2,
                    "depth": 16,
                    "verify_ok": True,
                    "cid": "bafy-mock",
                    "error": None,
                }
            ],
            "fetch_results": [
                {
                    "cid": "bafy-mock",
                    "statement": "membership",
                    "exit_code": 0,
                    "recheck_ok": True,
                }
            ],
        }

    monkeypatch.setattr(runner, "_run_pin_backend", _fake_backend)
    result = runner._run_pin_flow(
        artifacts,
        "/ip4/127.0.0.1/tcp/50140/p2p/QmServer",
    )

    assert calls == ["live", "mock"]
    assert result["mode_requested"] == "prefer-live"
    assert result["backend_used"] == "mock"
    assert result["fell_back_to_mock"] is True
    assert result["live_error"] == "live unavailable"
    assert result["error"] is None


def test_pin_mode_live_is_strict(monkeypatch, tmp_path: Path) -> None:
    cfg = DemoWebConfig(
        **{**_config().as_dict(), "pin_mode": "live"}
    )
    runner = DemoRunner(
        cfg,
        root_dir=tmp_path,
        python_executable="/tmp/fake-python",
    )
    artifacts = runner._create_run_artifacts("run-live")
    calls = []

    def _fake_backend(*, backend, artifacts, server_multiaddr):
        calls.append(backend)
        return {
            "backend_used": backend,
            "error": "missing FILECOIN_PIN_ENDPOINT",
            "pin_exit_code": None,
            "fetch_exit_codes": {},
            "pin_results": [],
            "fetch_results": [],
        }

    monkeypatch.setattr(runner, "_run_pin_backend", _fake_backend)
    result = runner._run_pin_flow(
        artifacts,
        "/ip4/127.0.0.1/tcp/50140/p2p/QmServer",
    )

    assert calls == ["live"]
    assert result["mode_requested"] == "live"
    assert result["fell_back_to_mock"] is False
    assert result["error"] == "missing FILECOIN_PIN_ENDPOINT"


def test_run_pin_backend_mock_roundtrip_path(monkeypatch, tmp_path: Path) -> None:
    runner = DemoRunner(
        _config(),
        root_dir=tmp_path,
        python_executable="/tmp/fake-python",
    )
    artifacts = runner._create_run_artifacts("run-mock")
    captured = {"endpoint": None, "token": None}
    mock_server_state = {"started": False, "stopped": False}

    class _FakePinMockServer:
        token = "demo-web-mock-token"
        endpoint = "http://127.0.0.1:8899"

        def start(self) -> None:
            mock_server_state["started"] = True

        def stop(self) -> None:
            mock_server_state["stopped"] = True

    monkeypatch.setattr(
        "libp2p_privacy_poc.demo_web.runner.PinMockServer",
        _FakePinMockServer,
    )

    def _fake_run_json(cmd, *, log_path, env, timeout_seconds, append):
        if "pin-proof-record" in cmd:
            captured["endpoint"] = env.get("FILECOIN_PIN_ENDPOINT")
            captured["token"] = env.get("FILECOIN_PIN_TOKEN")
            return (
                {
                    "results": [
                        {
                            "statement": "membership",
                            "schema": 2,
                            "depth": 16,
                            "verify_ok": True,
                            "cid": "bafy-mock",
                            "error": None,
                        }
                    ]
                },
                0,
            )
        if "fetch-proof-record" in cmd:
            assert env.get("FILECOIN_PIN_ENDPOINT") == captured["endpoint"]
            return ({"cid": "bafy-mock", "recheck": {"ok": True}}, 0)
        raise AssertionError("unexpected command")

    monkeypatch.setattr(runner, "_run_json_command", _fake_run_json)
    result = runner._run_pin_backend(
        backend="mock",
        artifacts=artifacts,
        server_multiaddr="/ip4/127.0.0.1/tcp/50140/p2p/QmServer",
    )

    assert result["backend_used"] == "mock"
    assert result["error"] is None
    assert result["pin_exit_code"] == 0
    assert result["fetch_exit_codes"]["bafy-mock"] == 0
    assert result["fetch_results"][0]["recheck_ok"] is True
    assert isinstance(captured["endpoint"], str)
    assert captured["endpoint"] == "http://127.0.0.1:8899"
    assert captured["token"] == "demo-web-mock-token"
    assert mock_server_state["started"] is True
    assert mock_server_state["stopped"] is True
