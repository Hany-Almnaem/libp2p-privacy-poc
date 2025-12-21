"""
WARNING: DRAFT - requires cryptographic review before production use.

Test suite for PedersenBackend commitment opening proofs.
"""

import copy
import hashlib

import pytest

from ..backend import PedersenBackend
from ..commitments import (
    clear_curve_params_cache,
    commit,
    get_cached_curve_params,
    validate_commitment_format,
)
from ..schnorr import generate_schnorr_pok
from ...config import POINT_SIZE_BYTES
from ...types import ProofContext, ZKProof, ZKProofType


SCALAR_BYTES = get_cached_curve_params().scalar_bytes
RESPONSE_BYTES = 2 * SCALAR_BYTES


def _tamper_bytes(data: bytes) -> bytes:
    if not data:
        return data
    tampered = bytearray(data)
    tampered[0] ^= 0x01
    return bytes(tampered)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def backend():
    return PedersenBackend()


@pytest.fixture
def ctx():
    return ProofContext(
        peer_id="QmTest123",
        session_id="session_001",
        metadata={
            "purpose": "commitment_opening_pok",
            "anonymity_set_size": 4,
        },
    )


# ============================================================================
# BASIC FUNCTIONALITY TESTS
# ============================================================================


def test_generate_proof_valid_inputs(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    assert proof.proof_type == ZKProofType.ANONYMITY_SET_MEMBERSHIP.value
    assert isinstance(proof.commitment, bytes)
    assert len(proof.commitment) == POINT_SIZE_BYTES
    assert isinstance(proof.challenge, bytes)
    assert len(proof.challenge) == SCALAR_BYTES
    assert isinstance(proof.response, bytes)
    assert len(proof.response) == RESPONSE_BYTES
    assert proof.public_inputs["v"] == 1
    assert proof.public_inputs["curve"] == backend.params.curve_name
    assert proof.public_inputs["anonymity_set_size"] == ctx.metadata["anonymity_set_size"]
    assert proof.public_inputs["ctx_hash"] == hashlib.sha256(ctx.to_bytes()).digest()
    assert proof.public_inputs["claim_only"] is True
    assert isinstance(proof.public_inputs["A"], (bytes, str))


def test_verify_valid_proof(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    assert backend.verify_proof(proof) is True


def test_round_trip_generate_verify(ctx):
    generator = PedersenBackend()
    verifier = PedersenBackend()
    proof = generator.generate_commitment_opening_proof(ctx)
    assert verifier.verify_proof(proof) is True


def test_multiple_proofs_different_peer_ids(backend):
    peer_ids = ["QmPeerA", "QmPeerB", "QmPeerC", "QmPeerD"]
    for peer_id in peer_ids:
        ctx = ProofContext(peer_id=peer_id, session_id="session_multi")
        proof = backend.generate_commitment_opening_proof(ctx)
        assert backend.verify_proof(proof) is True


def test_generate_proof_uses_cached_params():
    clear_curve_params_cache()
    backend = PedersenBackend()
    assert backend.params is get_cached_curve_params()


def test_verify_proof_with_cached_params(ctx):
    backend = PedersenBackend()
    proof = backend.generate_commitment_opening_proof(ctx)
    verifier = PedersenBackend()
    assert verifier.verify_proof(proof) is True


def test_peer_id_with_special_characters(backend):
    ctx = ProofContext(
        peer_id="peer!@#$%^&*()_+-=[]{}|;':,.<>/?",
        session_id="session_special",
    )
    proof = backend.generate_commitment_opening_proof(ctx)
    assert backend.verify_proof(proof) is True


def test_very_long_peer_id(backend):
    ctx = ProofContext(peer_id="A" * 10_240, session_id="session_long")
    proof = backend.generate_commitment_opening_proof(ctx)
    assert backend.verify_proof(proof) is True


# ============================================================================
# INVALID INPUT HANDLING
# ============================================================================


def test_empty_peer_id_raises_value_error(backend):
    ctx = ProofContext(peer_id="", session_id="session_001")
    with pytest.raises(ValueError, match="peer_id cannot be empty"):
        backend.generate_commitment_opening_proof(ctx)


def test_missing_session_id_raises_value_error(backend):
    ctx = ProofContext(peer_id="QmTest123", session_id=None)
    with pytest.raises(TypeError, match="session_id must be str"):
        backend.generate_commitment_opening_proof(ctx)


def test_empty_session_id_raises_value_error(backend):
    ctx = ProofContext(peer_id="QmTest123", session_id="")
    with pytest.raises(ValueError, match="session_id cannot be empty"):
        backend.generate_commitment_opening_proof(ctx)


def test_invalid_context_type_raises_type_error(backend):
    with pytest.raises(TypeError, match="ctx must be ProofContext"):
        backend.generate_commitment_opening_proof("not_ctx")


def test_wrong_proof_type_in_verification(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    proof.proof_type = ZKProofType.RANGE_PROOF.value
    assert backend.verify_proof(proof) is False


def test_tampered_commitment_in_verification(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    tampered = copy.deepcopy(proof)
    tampered.commitment = _tamper_bytes(proof.commitment)
    assert backend.verify_proof(tampered) is False


def test_tampered_challenge_in_verification(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    tampered = copy.deepcopy(proof)
    tampered.challenge = _tamper_bytes(proof.challenge)
    assert backend.verify_proof(tampered) is False


def test_tampered_response_in_verification(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    tampered = copy.deepcopy(proof)
    tampered.response = _tamper_bytes(proof.response)
    assert backend.verify_proof(tampered) is False


def test_missing_ctx_hash_in_public_inputs(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    tampered = copy.deepcopy(proof)
    tampered.public_inputs = {"v": 1, "A": proof.public_inputs["A"]}
    assert backend.verify_proof(tampered) is False


def test_invalid_commitment_size(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    tampered = copy.deepcopy(proof)
    tampered.commitment = b"\x00" * (POINT_SIZE_BYTES - 1)
    assert backend.verify_proof(tampered) is False


def test_invalid_challenge_size(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    tampered = copy.deepcopy(proof)
    tampered.challenge = b"\x00" * (SCALAR_BYTES - 1)
    assert backend.verify_proof(tampered) is False


def test_invalid_response_size(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    tampered = copy.deepcopy(proof)
    tampered.response = b"\x00" * (RESPONSE_BYTES - 1)
    assert backend.verify_proof(tampered) is False


# ============================================================================
# CONTEXT BINDING AND UNLINKABILITY
# ============================================================================


def test_commitment_value_deterministic_same_peer_id(backend):
    value_a = backend._derive_commitment_value("peer_x")
    value_b = backend._derive_commitment_value("peer_x")
    assert value_a == value_b


def test_commitment_value_changes_across_peer_ids(backend):
    value_a = backend._derive_commitment_value("peer_x")
    value_b = backend._derive_commitment_value("peer_y")
    assert value_a != value_b


def test_replay_across_session_id_fails(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    tampered = copy.deepcopy(proof)
    other_ctx = ProofContext(
        peer_id=ctx.peer_id,
        session_id="session_other",
        metadata=ctx.metadata,
        timestamp=ctx.timestamp,
    )
    tampered.public_inputs["ctx_hash"] = hashlib.sha256(
        other_ctx.to_bytes()
    ).digest()
    assert backend.verify_proof(tampered) is False


def test_tampered_context_fails_verification(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    tampered = copy.deepcopy(proof)
    tampered.public_inputs["ctx_hash"] = _tamper_bytes(
        proof.public_inputs["ctx_hash"]
    )
    assert backend.verify_proof(tampered) is False


def test_public_inputs_statement_only(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    assert proof.public_inputs.get("claim_only") is True


# ============================================================================
# SECURITY STRUCTURE TESTS
# ============================================================================


def test_serialized_proof_does_not_contain_raw_peer_id(backend):
    peer_id = "peer-" + ("x" * 80)
    ctx = ProofContext(peer_id=peer_id, session_id="session_no_leak")
    proof = backend.generate_commitment_opening_proof(ctx)
    serialized = proof.serialize()
    assert peer_id.encode("utf-8") not in serialized


def test_commitment_hiding_different_peer_ids(backend):
    ctx_a = ProofContext(peer_id="QmHideA", session_id="session_hide")
    ctx_b = ProofContext(peer_id="QmHideB", session_id="session_hide")
    proof_a = backend.generate_commitment_opening_proof(ctx_a)
    proof_b = backend.generate_commitment_opening_proof(ctx_b)
    assert proof_a.commitment != proof_b.commitment


def test_nonce_uniqueness_multiple_proofs(backend, ctx):
    proof_a = backend.generate_commitment_opening_proof(ctx)
    proof_b = backend.generate_commitment_opening_proof(ctx)
    assert proof_a.commitment != proof_b.commitment


# ============================================================================
# BATCH VERIFICATION
# ============================================================================


def test_batch_verify_empty_list(backend):
    assert backend.batch_verify([]) is True


def test_batch_verify_single_proof(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    assert backend.batch_verify([proof]) is True


def test_batch_verify_one_invalid_proof_fails(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    tampered = copy.deepcopy(proof)
    tampered.challenge = _tamper_bytes(proof.challenge)
    assert backend.batch_verify([proof, tampered]) is False


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


def test_integration_commitment_format(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    assert validate_commitment_format(proof.commitment) is True


def test_integration_commit_and_schnorr_pok(backend):
    ctx = ProofContext(
        peer_id="QmIntegration",
        session_id="session_integration",
        metadata={"anonymity_set_size": 1},
    )
    params = get_cached_curve_params()
    value = backend._derive_commitment_value(ctx.peer_id)
    commitment, blinding = commit(value, params=params)
    context = hashlib.sha256(ctx.to_bytes()).digest()
    schnorr = generate_schnorr_pok(
        commitment=commitment,
        value=value,
        blinding=blinding,
        context=context,
        params=params,
    )
    challenge_bytes = int.from_bytes(schnorr["c"], "big").to_bytes(
        SCALAR_BYTES, "big"
    )
    response_bytes = (
        int.from_bytes(schnorr["z_v"], "big").to_bytes(SCALAR_BYTES, "big")
        + int.from_bytes(schnorr["z_b"], "big").to_bytes(SCALAR_BYTES, "big")
    )
    proof = ZKProof(
        proof_type=ZKProofType.ANONYMITY_SET_MEMBERSHIP.value,
        commitment=commitment,
        challenge=challenge_bytes,
        response=response_bytes,
        public_inputs={
            "v": 1,
            "curve": params.curve_name,
            "anonymity_set_size": ctx.metadata["anonymity_set_size"],
            "ctx_hash": context,
            "A": schnorr["A"],
            "claim_only": True,
        },
    )
    assert backend.verify_proof(proof) is True


def test_integration_with_proof_context(backend):
    ctx = ProofContext(
        peer_id="QmCtxIntegration",
        session_id="session_ctx",
        metadata={"network": "testnet"},
    )
    proof = backend.generate_commitment_opening_proof(ctx)
    assert backend.verify_proof(proof) is True


def test_integration_with_zkproof_serialization(backend, ctx):
    proof = backend.generate_commitment_opening_proof(ctx)
    serialized = proof.serialize()
    restored = ZKProof.deserialize(serialized)
    assert backend.verify_proof(restored) is True
