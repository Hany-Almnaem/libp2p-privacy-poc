# Documentation

## Scope
This repository is a prototype/experimental system for privacy analysis on real py-libp2p connections. ZK proofs are mock by default; a single real commitment-opening proof (Pedersen + Schnorr) is available via an opt-in flag. This is not production-ready and has not undergone a security audit.

## Documentation Index
- Phase 2A overview: `docs/PHASE_2A_OVERVIEW.md`
- Phase 2A progress checklist: `docs/PHASE_2A_PROGRESS.md`
- Privacy protocol API: `docs/PRIVACY_PROTOCOL_API.md`
- Real network integration guide: `docs/REAL_NETWORK_GUIDE.md`
- Project summary and quick start: `README.md`

## Architecture Summary
- `MetadataCollector` attaches to the libp2p network and records connection metadata.
- `PrivacyAnalyzer` evaluates privacy risks from collected events.
- `ReportGenerator` renders console/JSON/HTML outputs.
- `privacy_protocol` provides cryptographic primitives and the proof backend.
- The CLI orchestrates data capture, analysis, and optional proof generation.

## Getting Started
```bash
python -m venv venv
source venv/bin/activate
pip install -e .

# Simulated run (fast)
libp2p-privacy analyze --simulate --format console

# Include mock ZK proofs (demo only)
libp2p-privacy analyze --simulate --with-zk-proofs --format console

# Include the real commitment-opening proof (experimental)
libp2p-privacy analyze --simulate --with-real-zk --format console
```

## CLI Usage (Key Options)
- `--simulate`: run without a live network.
- `--with-zk-proofs`: include mock proofs in the report.
- `--with-real-zk`: include a real Pedersen+Schnorr commitment-opening proof.
- `--format {console,json,html}`: choose output format.

## Python Integration (Minimal)
```python
import trio
from libp2p import new_host
from libp2p.tools.async_service import background_trio_service
from libp2p_privacy_poc import MetadataCollector, PrivacyAnalyzer

async def main():
    host = new_host()
    collector = MetadataCollector(host)
    async with background_trio_service(host.get_network()):
        report = PrivacyAnalyzer(collector).analyze()
        print(report.summary())

trio.run(main)
```

## Privacy Protocol (Phase 2A)
- Pedersen commitments and Schnorr commitment-opening proofs are implemented in `libp2p_privacy_poc/privacy_protocol/`.
- The backend factory selects between `mock` and `pedersen` backends.
- The demo uses mock proofs by default; the real proof path is opt-in.

## Security Model (Phase 2A)
- The real proof attests knowledge of a Pedersen commitment opening bound to `peer_id` and `session_id`.
- Challenges are computed via length-prefixed SHA-256, and verification uses constant-time comparison.
- Mock proofs are non-cryptographic placeholders and must not be treated as security guarantees.

## Threats Not Addressed
- No formal security audit or side-channel review.
- Proof composition for analysis claims (anonymity set, unlinkability, range) is not implemented.
- Python runtime behavior is not guaranteed constant-time.

## Testing Summary
- Run `pytest libp2p_privacy_poc -q` for the full local test suite.
- Cryptographic tests live under `libp2p_privacy_poc/privacy_protocol/pedersen/tests/`.

## Legacy and Archived Notes
Historical planning and issue notes were removed from the repo after Phase 2A documentation was consolidated. Refer to git history for older drafts if needed.
