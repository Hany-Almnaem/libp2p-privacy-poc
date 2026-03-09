"""CLI tests for pin-proof-record and fetch-proof-record."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from click.testing import CliRunner

from libp2p_privacy_poc import cli
from libp2p_privacy_poc.filecoin_pin.models import (
    ProofVerificationRecord,
    build_hashes,
    decode_record,
    encode_record,
)


def _write_fixture_assets(base: Path) -> None:
    membership = base / "membership" / "v2" / "depth-16"
    membership.mkdir(parents=True, exist_ok=True)
    (membership / "membership_vk.bin").write_bytes(b"vk-membership")
    (membership / "public_inputs.bin").write_bytes(b"public-membership")
    (membership / "membership_proof.bin").write_bytes(b"proof-membership")


def test_pin_proof_record_builds_and_pins(monkeypatch, tmp_path: Path) -> None:
    _write_fixture_assets(tmp_path)
    captured: Dict[str, bytes] = {}

    def _fake_pin(data: bytes, name: str | None = None) -> str:
        captured["data"] = data
        captured["name"] = (name or "").encode("utf-8")
        return "bafy-test-cid"

    def _fake_verify(**kwargs):
        return True

    monkeypatch.setattr(cli, "pin_bytes", _fake_pin)
    monkeypatch.setattr(cli.SnarkBackend, "verify", staticmethod(_fake_verify))

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        [
            "pin-proof-record",
            "--statement",
            "membership",
            "--assets-dir",
            str(tmp_path),
            "--prove-mode",
            "real",
            "--json",
        ],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["results"][0]["cid"] == "bafy-test-cid"
    assert output["results"][0]["verify_ok"] is True

    record = decode_record(captured["data"])
    assert record.statement_type == "membership"
    assert record.schema_v == 2
    assert record.depth == 16
    assert record.prove_mode == "real"
    assert record.verify_ok is True


def test_fetch_proof_record_recheck_assets(monkeypatch, tmp_path: Path) -> None:
    _write_fixture_assets(tmp_path)
    membership = tmp_path / "membership" / "v2" / "depth-16"

    record = ProofVerificationRecord(
        v=1,
        statement_type="membership",
        schema_v=2,
        depth=16,
        ts_utc="2026-01-01T00:00:00Z",
        hashes=build_hashes(
            (membership / "membership_vk.bin").read_bytes(),
            (membership / "public_inputs.bin").read_bytes(),
            (membership / "membership_proof.bin").read_bytes(),
        ),
        verify_ok=True,
        prove_mode="fixture",
        assets_path=str(membership),
        fixture_id="membership/v2/depth-16",
        tool_name="privacy-protocol-toolkit-p2p",
        tool_version="0.1.0",
    )
    blob = encode_record(record)

    monkeypatch.setattr(cli, "fetch_bytes", lambda cid: blob)

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        [
            "fetch-proof-record",
            "--cid",
            "bafy-test-cid",
            "--recheck-assets-dir",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["cid"] == "bafy-test-cid"
    assert payload["recheck"]["ok"] is True
    assert payload["statement_type"] == "membership"

