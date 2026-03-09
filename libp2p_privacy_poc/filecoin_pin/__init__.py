"""Filecoin Pin integration helpers (opt-in)."""

from .client import fetch_bytes, pin_bytes
from .errors import (
    PinClientError,
    PinConfigError,
    PinPayloadTooLargeError,
    PinResponseError,
    RecordValidationError,
)
from .models import (
    ProofHashes,
    ProofVerificationRecord,
    build_hashes,
    decode_record,
    encode_record,
    hash_proof_bytes,
    hash_public_inputs_bytes,
    hash_vk_bytes,
    make_timestamp_utc,
    record_to_dict,
)

__all__ = [
    "PinClientError",
    "PinConfigError",
    "PinPayloadTooLargeError",
    "PinResponseError",
    "RecordValidationError",
    "ProofHashes",
    "ProofVerificationRecord",
    "pin_bytes",
    "fetch_bytes",
    "build_hashes",
    "hash_vk_bytes",
    "hash_public_inputs_bytes",
    "hash_proof_bytes",
    "encode_record",
    "decode_record",
    "record_to_dict",
    "make_timestamp_utc",
]

