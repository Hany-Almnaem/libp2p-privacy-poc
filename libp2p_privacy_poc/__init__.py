"""
libp2p Privacy Analysis Tool (Proof of Concept)

A privacy analysis tool for py-libp2p that detects privacy leaks and demonstrates
zero-knowledge proof concepts for cryptographic privacy guarantees.

⚠️ PROOF OF CONCEPT - NOT PRODUCTION READY
Mock ZK proofs are used for demonstration purposes only.
"""

__version__ = "0.1.0"
__author__ = "Hany Almnaem"

from libp2p_privacy_poc.metadata_collector import MetadataCollector, ConnectionMetadata
from libp2p_privacy_poc.privacy_analyzer import PrivacyAnalyzer, PrivacyReport
from libp2p_privacy_poc.mock_zk_proofs import MockZKProofSystem, ZKProofType
from libp2p_privacy_poc.report_generator import ReportGenerator

__all__ = [
    "MetadataCollector",
    "ConnectionMetadata",
    "PrivacyAnalyzer",
    "PrivacyReport",
    "MockZKProofSystem",
    "ZKProofType",
    "ReportGenerator",
]

# Version and disclaimer
DISCLAIMER = """
⚠️  PROOF OF CONCEPT - NOT PRODUCTION READY

This tool uses MOCK zero-knowledge proofs for demonstration purposes only.
Real cryptographic implementation is required for production use.

Current limitations:
- Mock ZK proofs (no cryptographic guarantees)
- Basic privacy analysis algorithms
- No security audit
- Performance not optimized

For production use, see roadmap in README.md
"""

def print_disclaimer():
    """Print the PoC disclaimer."""
    print(DISCLAIMER)

