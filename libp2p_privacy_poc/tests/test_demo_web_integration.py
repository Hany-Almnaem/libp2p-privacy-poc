"""Opt-in integration tests for demo web flow and sponsor pin flow."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path

import pytest
from click.testing import CliRunner

from libp2p_privacy_poc import cli
from libp2p_privacy_poc.demo_web.models import DemoWebConfig
from libp2p_privacy_poc.demo_web.runner import DemoRunner


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "privacy_circuits").is_dir():
            return parent
    raise RuntimeError("repo root not found")


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


@pytest.mark.network
def test_demo_runner_network_smoke() -> None:
    if os.environ.get("RUN_NETWORK_TESTS") != "1":
        pytest.skip("RUN_NETWORK_TESTS not set")
    pytest.importorskip("libp2p")

    if not _port_is_available(50140) or not _port_is_available(50158):
        pytest.skip("demo runner fixed ports 50140/50158 are busy")

    repo_root = _find_repo_root()
    assets_dir = repo_root / "privacy_circuits" / "params"
    if not assets_dir.is_dir():
        pytest.skip("privacy_circuits/params not available")

    cfg = DemoWebConfig(
        host="127.0.0.1",
        port=8080,
        assets_dir=str(assets_dir),
        analyze_duration=10,
        zk_timeout=60,
        traffic_nodes=8,
        pin_mode="mock",
        log_level="warning",
    )
    runner = DemoRunner(cfg, root_dir=repo_root)
    summary = runner.run_full_demo()

    assert summary["status"] in {"success", "fallback"}
    assert Path(summary["artifacts"]["report_json"]).exists()
    assert summary["pin"]["backend_used"] == "mock"


@pytest.mark.pin
def test_pin_cli_all_statements_live_roundtrip() -> None:
    if os.environ.get("RUN_PIN_TESTS") != "1":
        pytest.skip("RUN_PIN_TESTS not set")

    endpoint = os.environ.get("FILECOIN_PIN_ENDPOINT")
    token = os.environ.get("FILECOIN_PIN_TOKEN")
    if not endpoint or not token:
        pytest.skip(
            "FILECOIN_PIN_ENDPOINT and FILECOIN_PIN_TOKEN are required for pin tests"
        )

    repo_root = _find_repo_root()
    assets_dir = repo_root / "privacy_circuits" / "params"
    if not assets_dir.is_dir():
        pytest.skip("privacy_circuits/params not available")

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        [
            "pin-proof-record",
            "--statement",
            "all",
            "--assets-dir",
            str(assets_dir),
            "--prove-mode",
            "real",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    records = payload.get("results", [])
    assert len(records) == 3

    cids = [item.get("cid") for item in records if item.get("cid")]
    assert len(cids) == 3

    for cid in cids:
        fetch_result = runner.invoke(
            cli.main,
            [
                "fetch-proof-record",
                "--cid",
                cid,
                "--recheck-assets-dir",
                str(assets_dir),
                "--json",
            ],
        )
        assert fetch_result.exit_code == 0
        fetch_payload = json.loads(fetch_result.output)
        assert fetch_payload["recheck"]["ok"] is True
