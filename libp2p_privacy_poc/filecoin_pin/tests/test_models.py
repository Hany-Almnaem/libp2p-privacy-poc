"""Unit tests for ProofVerificationRecord schema and hashing."""

from __future__ import annotations

import hashlib

import cbor2
import pytest

from libp2p_privacy_poc.filecoin_pin.errors import RecordValidationError
from libp2p_privacy_poc.filecoin_pin.models import (
    ProofVerificationRecord,
    build_hashes,
    decode_record,
    encode_record,
    hash_proof_bytes,
    hash_public_inputs_bytes,
    hash_vk_bytes,
)


def test_domain_separated_hash_vectors() -> None:
    vk = b"vk-test"
    public_inputs = b"public-inputs-test"
    proof = b"proof-test"

    assert hash_vk_bytes(vk) == hashlib.sha256(
        b"privacy-protocol-toolkit-p2p:vk:v1" + vk
    ).digest()
    assert hash_public_inputs_bytes(public_inputs) == hashlib.sha256(
        b"privacy-protocol-toolkit-p2p:public_inputs:v1" + public_inputs
    ).digest()
    assert hash_proof_bytes(proof) == hashlib.sha256(
        b"privacy-protocol-toolkit-p2p:proof:v1" + proof
    ).digest()


def test_record_encode_decode_roundtrip_deterministic() -> None:
    hashes = build_hashes(b"vk", b"public", b"proof")
    record = ProofVerificationRecord(
        v=1,
        statement_type="membership",
        schema_v=2,
        depth=16,
        ts_utc="2026-01-01T00:00:00Z",
        hashes=hashes,
        verify_ok=True,
        prove_mode="real",
        assets_path="privacy_circuits/params/membership/v2/depth-16",
        fixture_id="membership/v2/depth-16",
        tool_name="privacy-protocol-toolkit-p2p",
        tool_version="0.1.0",
    )

    blob_a = encode_record(record)
    blob_b = encode_record(record)
    assert blob_a == blob_b

    decoded = decode_record(blob_a)
    assert decoded == record


def test_decode_record_rejects_invalid_mode() -> None:
    hashes = build_hashes(b"vk", b"public", b"proof")
    record = ProofVerificationRecord(
        v=1,
        statement_type="continuity",
        schema_v=2,
        depth=0,
        ts_utc="2026-01-01T00:00:00Z",
        hashes=hashes,
        verify_ok=False,
        prove_mode="fixture",
        assets_path="privacy_circuits/params/continuity/v2/depth-0",
        fixture_id="continuity/v2/depth-0",
        tool_name="privacy-protocol-toolkit-p2p",
        tool_version="0.1.0",
    )
    payload_map = cbor2.loads(encode_record(record))
    payload_map["prove_mode"] = "unknown"
    tampered = cbor2.dumps(payload_map, canonical=True)

    with pytest.raises(RecordValidationError):
        decode_record(tampered)
