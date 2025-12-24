# Privacy Protocol API (Phase 2A)

## Overview
- Implements Pedersen commitments and Schnorr commitment-opening proofs on secp256k1 using petlib.
- Exposes a backend interface, factory selection, and a compatibility adapter for mock proofs.
- Intended for testing and integration; not production-ready.

## Installation
- Create a virtual environment and install the project in editable mode.

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

Dependencies include `petlib` for elliptic-curve operations and `cbor2` for proof serialization.

## Basic Usage Examples

### Commit and verify
```python
from libp2p_privacy_poc.privacy_protocol.pedersen.commitments import (
    setup_curve,
    commit,
    verify_commitment,
)

params = setup_curve()
commitment, blinding = commit(42, params=params)
assert verify_commitment(commitment, 42, blinding, params)
```

### Generate and verify a Schnorr commitment-opening proof
```python
from libp2p_privacy_poc.privacy_protocol.pedersen.schnorr import (
    generate_schnorr_pok,
    verify_schnorr_pok,
)
from libp2p_privacy_poc.privacy_protocol.types import ProofContext
from libp2p_privacy_poc.privacy_protocol.pedersen.commitments import commit, setup_curve

params = setup_curve()
commitment, blinding = commit(7, params=params)
ctx = ProofContext(peer_id="peer-1", session_id="session-1")
proof = generate_schnorr_pok(commitment, 7, blinding, ctx.to_bytes(), params)
assert verify_schnorr_pok(commitment, proof, ctx.to_bytes(), params)
```

### Use the backend factory (Pedersen)
```python
from libp2p_privacy_poc.privacy_protocol.factory import get_zk_backend
from libp2p_privacy_poc.privacy_protocol.types import ProofContext

backend = get_zk_backend(prefer="pedersen")
ctx = ProofContext(peer_id="peer-1", session_id="session-1")
proof = backend.generate_commitment_opening_proof(ctx)
assert backend.verify_proof(proof) is True
```

## API Reference

### Public Types
- `ProofContext` (in `privacy_protocol/types.py`)
  - Fields: `peer_id`, `session_id`, `metadata`, `timestamp`
  - Serialization: `to_bytes()` uses deterministic JSON.
- `ZKProof` (in `privacy_protocol/types.py`)
  - Fields: `proof_type`, `commitment`, `challenge`, `response`, `public_inputs`, `timestamp`
  - Serialization: `serialize()` / `deserialize()` using CBOR.
- `ZKProofType` (in `privacy_protocol/types.py`)
  - Enum of proof type strings for compatibility.

### Backend Selection & Factory
- `privacy_protocol.factory.get_zk_backend(prefer=None, override=None)`
  - Returns a backend instance (`mock` or `pedersen`).
- `privacy_protocol.feature_flags.get_backend_type()` / `set_backend_type()`
  - Also reads `PRIVACY_PROTOCOL_BACKEND` environment variable.

### Pedersen Commitments
Module: `privacy_protocol/pedersen/commitments.py`
- `setup_curve()`
- `commit(value, blinding=None, params=None, randomness_source=None)`
- `verify_commitment(commitment, value, blinding, params)`
- `open_commitment(commitment, value, blinding, params)`
- `add_commitments()`, `add_commitment_values()`, `add_commitment_blindings()`
- `commitment_to_point()`, `validate_commitment_format()`

### Schnorr Proof of Knowledge
Module: `privacy_protocol/pedersen/schnorr.py`
- `generate_schnorr_pok(commitment, value, blinding, context, params, randomness_source=None)`
- `verify_schnorr_pok(commitment, proof, context, params)`

### Pedersen Backend
Module: `privacy_protocol/pedersen/backend.py`
- `PedersenBackend.generate_commitment_opening_proof(ctx)`
- `PedersenBackend.verify_proof(proof)`
- `PedersenBackend.generate_proof(context, witness, public_inputs)`
- `PedersenBackend.batch_verify(proofs)`
- `PedersenBackend.get_backend_info()`

### Mock Adapter Compatibility
Module: `privacy_protocol/adapters/mock_adapter.py`
- `MockZKProofSystemAdapter.generate_proof(context, witness, public_inputs)`
- `MockZKProofSystemAdapter.verify_proof(proof)`

## Configuration
- `privacy_protocol/config.py` defines curve and serialization parameters.
  - `CURVE_NAME = "secp256k1"`
  - `CURVE_LIBRARY = "petlib"`
  - `GROUP_ORDER` and `POINT_SIZE_BYTES` for encoding sizes
- Schnorr Fiat-Shamir challenge uses SHA-256 with length-prefixed encoding.
- The Pedersen backend binds proofs to `ProofContext` by hashing `ctx.to_bytes()`.

## Security Properties
- Concrete HVZK simulator test for Schnorr transcripts.
- Concrete soundness test (proof bound to commitment).
- Concrete special soundness extraction test.
- Constant-time comparison is used for challenge validation.

## Known Limitations
- Prototype implementation; no formal security audit.
- Only commitment-opening PoK is real; other proof types remain mock.
- Hash-to-point uses petlib `hash_to_point` (try-and-increment).
- Python arithmetic and timing are not guaranteed constant-time.

## Performance Notes
- Benchmarks are defined in the Pedersen test suite.
- Run `pytest libp2p_privacy_poc/privacy_protocol/pedersen/tests -q` to see benchmark output.
