"""
WARNING: DRAFT - requires crypto review before production use.

Integration tests for backend selection and proof round trips.
"""

import pytest

from ..backend import PedersenBackend
from ... import factory
from ...adapters.mock_adapter import MockZKProofSystemAdapter
from ...types import ProofContext, ZKProofType


def _make_context(anonymity_set_size: int = 3) -> ProofContext:
    return ProofContext(
        peer_id="peer-1",
        session_id="session-1",
        metadata={"anonymity_set_size": anonymity_set_size},
        timestamp=1234567890.0,
    )


def test_factory_pedersen_backend_round_trip():
    backend = factory.get_zk_backend(prefer="pedersen")
    assert isinstance(backend, PedersenBackend)

    ctx = _make_context()
    proof = backend.generate_commitment_opening_proof(ctx)

    assert proof.proof_type == ZKProofType.ANONYMITY_SET_MEMBERSHIP.value
    assert backend.verify_proof(proof) is True


def test_factory_mock_backend_round_trip():
    backend = factory.get_zk_backend(prefer="mock")
    assert isinstance(backend, MockZKProofSystemAdapter)

    ctx = _make_context(anonymity_set_size=4)
    proof = backend.generate_proof(
        ctx, witness={}, public_inputs={"anonymity_set_size": 4}
    )

    assert proof.proof_type == ZKProofType.ANONYMITY_SET_MEMBERSHIP.value
    assert backend.verify_proof(proof) is True


def test_generate_proof_round_trip_via_interface():
    backend = PedersenBackend()
    ctx = _make_context()

    proof = backend.generate_proof(
        ctx, witness={}, public_inputs={"session_id": ctx.session_id}
    )

    assert backend.verify_proof(proof) is True


def test_cross_backend_proofs_are_not_interchangeable():
    pedersen_backend = PedersenBackend()
    mock_backend = MockZKProofSystemAdapter()
    ctx = _make_context(anonymity_set_size=2)

    pedersen_proof = pedersen_backend.generate_commitment_opening_proof(ctx)
    mock_proof = mock_backend.generate_anonymity_set_proof(
        ctx, anonymity_set_size=2
    )

    assert pedersen_proof.proof_type == ZKProofType.ANONYMITY_SET_MEMBERSHIP.value
    assert mock_proof.proof_type == ZKProofType.ANONYMITY_SET_MEMBERSHIP.value

    assert pedersen_backend.verify_proof(pedersen_proof) is True
    assert mock_backend.verify_proof(mock_proof) is True
    assert pedersen_backend.verify_proof(mock_proof) is False
    assert mock_backend.verify_proof(pedersen_proof) is False
