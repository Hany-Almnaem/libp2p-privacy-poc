"""Record schema and hashing for pinned proof verification records."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import cbor2

from libp2p_privacy_poc.network.privacyzk.constants import STATEMENT_TYPES

from .errors import RecordValidationError

TOOL_NAME = "privacy-protocol-toolkit-p2p"
RECORD_SCHEMA_V = 1

_VK_DOMAIN = b"privacy-protocol-toolkit-p2p:vk:v1"
_PUBLIC_INPUTS_DOMAIN = b"privacy-protocol-toolkit-p2p:public_inputs:v1"
_PROOF_DOMAIN = b"privacy-protocol-toolkit-p2p:proof:v1"


def _domain_hash(domain_prefix: bytes, payload: bytes | bytearray) -> bytes:
    if not isinstance(payload, (bytes, bytearray)):
        raise RecordValidationError("hash input must be bytes")
    return hashlib.sha256(domain_prefix + bytes(payload)).digest()


def hash_vk_bytes(vk_bytes: bytes | bytearray) -> bytes:
    return _domain_hash(_VK_DOMAIN, vk_bytes)


def hash_public_inputs_bytes(public_inputs_bytes: bytes | bytearray) -> bytes:
    return _domain_hash(_PUBLIC_INPUTS_DOMAIN, public_inputs_bytes)


def hash_proof_bytes(proof_bytes: bytes | bytearray) -> bytes:
    return _domain_hash(_PROOF_DOMAIN, proof_bytes)


@dataclass(frozen=True)
class ProofHashes:
    vk_sha256: bytes
    public_inputs_sha256: bytes
    proof_sha256: bytes

    def validate(self) -> None:
        for name, value in (
            ("vk_sha256", self.vk_sha256),
            ("public_inputs_sha256", self.public_inputs_sha256),
            ("proof_sha256", self.proof_sha256),
        ):
            if not isinstance(value, (bytes, bytearray)):
                raise RecordValidationError(f"{name} must be bytes")
            if len(value) != 32:
                raise RecordValidationError(f"{name} must be 32 bytes")


@dataclass(frozen=True)
class ProofVerificationRecord:
    v: int
    statement_type: str
    schema_v: int
    depth: int
    ts_utc: str
    hashes: ProofHashes
    verify_ok: bool
    prove_mode: str
    assets_path: str
    tool_name: str
    tool_version: str
    fixture_id: Optional[str] = None
    peer_id: Optional[str] = None
    peer_multiaddr: Optional[str] = None

    def validate(self) -> None:
        if self.v != RECORD_SCHEMA_V:
            raise RecordValidationError(f"unsupported record schema version: {self.v}")
        if self.statement_type not in STATEMENT_TYPES:
            raise RecordValidationError("unsupported statement_type")
        if not isinstance(self.schema_v, int) or self.schema_v < 1:
            raise RecordValidationError("schema_v must be >= 1")
        if not isinstance(self.depth, int) or self.depth < 0:
            raise RecordValidationError("depth must be >= 0")
        if not isinstance(self.ts_utc, str) or not self.ts_utc:
            raise RecordValidationError("ts_utc is required")
        if self.prove_mode not in {"real", "fixture"}:
            raise RecordValidationError("prove_mode must be real or fixture")
        if not isinstance(self.assets_path, str) or not self.assets_path:
            raise RecordValidationError("assets_path is required")
        if not isinstance(self.tool_name, str) or not self.tool_name:
            raise RecordValidationError("tool_name is required")
        if not isinstance(self.tool_version, str) or not self.tool_version:
            raise RecordValidationError("tool_version is required")
        for optional_name, value in (
            ("fixture_id", self.fixture_id),
            ("peer_id", self.peer_id),
            ("peer_multiaddr", self.peer_multiaddr),
        ):
            if value is not None and not isinstance(value, str):
                raise RecordValidationError(f"{optional_name} must be str when present")
        self.hashes.validate()


def build_hashes(
    vk_bytes: bytes | bytearray,
    public_inputs_bytes: bytes | bytearray,
    proof_bytes: bytes | bytearray,
) -> ProofHashes:
    return ProofHashes(
        vk_sha256=hash_vk_bytes(vk_bytes),
        public_inputs_sha256=hash_public_inputs_bytes(public_inputs_bytes),
        proof_sha256=hash_proof_bytes(proof_bytes),
    )


def encode_record(record: ProofVerificationRecord) -> bytes:
    record.validate()
    payload: Dict[str, Any] = {
        "v": record.v,
        "statement_type": record.statement_type,
        "schema_v": record.schema_v,
        "depth": record.depth,
        "ts_utc": record.ts_utc,
        "hashes": {
            "vk_sha256": bytes(record.hashes.vk_sha256),
            "public_inputs_sha256": bytes(record.hashes.public_inputs_sha256),
            "proof_sha256": bytes(record.hashes.proof_sha256),
        },
        "verify_ok": record.verify_ok,
        "prove_mode": record.prove_mode,
        "assets_path": record.assets_path,
        "tool_name": record.tool_name,
        "tool_version": record.tool_version,
    }
    if record.fixture_id is not None:
        payload["fixture_id"] = record.fixture_id
    if record.peer_id is not None:
        payload["peer_id"] = record.peer_id
    if record.peer_multiaddr is not None:
        payload["peer_multiaddr"] = record.peer_multiaddr
    return cbor2.dumps(payload, canonical=True)


def decode_record(data: bytes | bytearray) -> ProofVerificationRecord:
    if not isinstance(data, (bytes, bytearray)):
        raise RecordValidationError("record payload must be bytes")
    payload = cbor2.loads(bytes(data))
    if not isinstance(payload, dict):
        raise RecordValidationError("record payload must be a CBOR map")

    hashes_map = payload.get("hashes")
    if not isinstance(hashes_map, dict):
        raise RecordValidationError("hashes map is required")

    hashes = ProofHashes(
        vk_sha256=_require_bytes(hashes_map.get("vk_sha256"), "hashes.vk_sha256"),
        public_inputs_sha256=_require_bytes(
            hashes_map.get("public_inputs_sha256"), "hashes.public_inputs_sha256"
        ),
        proof_sha256=_require_bytes(
            hashes_map.get("proof_sha256"), "hashes.proof_sha256"
        ),
    )
    record = ProofVerificationRecord(
        v=_require_int(payload.get("v"), "v"),
        statement_type=_require_str(payload.get("statement_type"), "statement_type"),
        schema_v=_require_int(payload.get("schema_v"), "schema_v"),
        depth=_require_int(payload.get("depth"), "depth"),
        ts_utc=_require_str(payload.get("ts_utc"), "ts_utc"),
        hashes=hashes,
        verify_ok=_require_bool(payload.get("verify_ok"), "verify_ok"),
        prove_mode=_require_str(payload.get("prove_mode"), "prove_mode"),
        assets_path=_require_str(payload.get("assets_path"), "assets_path"),
        tool_name=_require_str(payload.get("tool_name"), "tool_name"),
        tool_version=_require_str(payload.get("tool_version"), "tool_version"),
        fixture_id=_optional_str(payload.get("fixture_id"), "fixture_id"),
        peer_id=_optional_str(payload.get("peer_id"), "peer_id"),
        peer_multiaddr=_optional_str(payload.get("peer_multiaddr"), "peer_multiaddr"),
    )
    record.validate()
    return record


def record_to_dict(record: ProofVerificationRecord) -> Dict[str, Any]:
    return {
        "v": record.v,
        "statement_type": record.statement_type,
        "schema_v": record.schema_v,
        "depth": record.depth,
        "ts_utc": record.ts_utc,
        "hashes": {
            "vk_sha256": record.hashes.vk_sha256.hex(),
            "public_inputs_sha256": record.hashes.public_inputs_sha256.hex(),
            "proof_sha256": record.hashes.proof_sha256.hex(),
        },
        "verify_ok": record.verify_ok,
        "prove_mode": record.prove_mode,
        "assets_path": record.assets_path,
        "fixture_id": record.fixture_id,
        "tool_name": record.tool_name,
        "tool_version": record.tool_version,
        "peer_id": record.peer_id,
        "peer_multiaddr": record.peer_multiaddr,
    }


def make_timestamp_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _require_int(value: Any, field: str) -> int:
    if not isinstance(value, int):
        raise RecordValidationError(f"{field} must be int")
    return value


def _require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise RecordValidationError(f"{field} must be bool")
    return value


def _require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise RecordValidationError(f"{field} must be non-empty str")
    return value


def _optional_str(value: Any, field: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RecordValidationError(f"{field} must be str when present")
    return value


def _require_bytes(value: Any, field: str) -> bytes:
    if not isinstance(value, (bytes, bytearray)):
        raise RecordValidationError(f"{field} must be bytes")
    return bytes(value)

