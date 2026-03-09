"""Opt-in live pin round-trip test."""

from __future__ import annotations

import os

import pytest

from libp2p_privacy_poc.filecoin_pin.client import fetch_bytes, pin_bytes


@pytest.mark.pin
def test_live_pin_fetch_roundtrip() -> None:
    if os.environ.get("RUN_PIN_TESTS") != "1":
        pytest.skip("RUN_PIN_TESTS not set")
    endpoint = os.environ.get("FILECOIN_PIN_ENDPOINT")
    token = os.environ.get("FILECOIN_PIN_TOKEN")
    if not endpoint or not token:
        pytest.skip(
            "FILECOIN_PIN_ENDPOINT and FILECOIN_PIN_TOKEN are required for pin tests"
        )

    payload = b"privacy-protocol-toolkit-p2p pin roundtrip"
    cid = pin_bytes(payload, name="pytest-roundtrip")
    fetched = fetch_bytes(cid)
    assert fetched == payload

