# libp2p Privacy PoC

⚠️ **Prototype / Experimental - Not Production Ready**  
Includes real network integration and a real Pedersen+Schnorr commitment-opening proof; other proofs are mock.

## Summary
This project analyzes privacy risks from real py-libp2p network activity and produces reports (console/JSON/HTML). Phase 2A adds a real cryptographic core using Pedersen commitments and Schnorr proof of knowledge; mock proofs remain the default for demo scenarios.

## Why it matters
- Helps operators detect privacy risks in P2P networks using real connection metadata.
- Adds a verifiable cryptographic proof path without changing existing mock-based demos.

## Real vs mock (current state)
- Real: Pedersen commitments, Schnorr commitment-opening proof, backend verification.
- Mock: Anonymity set, unlinkability, and range proofs used in reports.

## Status: Phase 2A Complete
- Pedersen commitments and Schnorr commitment-opening proofs implemented and tested.
- Privacy protocol backend and factory available (`mock` or `pedersen`).
- Optional real ZK proof path integrated into the CLI via `--with-real-zk`.

## What can be proven today
- Knowledge of a Pedersen commitment opening bound to `peer_id` and `session_id`.
- Not yet: anonymity set membership, unlinkability, or range proofs.

## Usage Example
```bash
# Install
python -m venv venv
source venv/bin/activate
pip install -e .

# Simulated analysis with mock + real proof (real proof is opt-in)
libp2p-privacy analyze --simulate --with-zk-proofs --with-real-zk --format console

# Real network analysis (add a second node to connect)
libp2p-privacy analyze --duration 10 --with-real-zk --format console
```

## Development Notes
- Phase 2A overview: `docs/PHASE_2A_OVERVIEW.md`
- Phase 2A progress: `docs/PHASE_2A_PROGRESS.md`
- Privacy protocol API: `docs/PRIVACY_PROTOCOL_API.md`
- Real network guide: `docs/REAL_NETWORK_GUIDE.md`
- Documentation index: `docs/DOCUMENTATION.md`
