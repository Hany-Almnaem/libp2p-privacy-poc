"""
Basic Privacy Analysis Example

This example demonstrates how to use the Privacy Analysis Tool with simulated
py-libp2p connection data.

Since setting up multiple py-libp2p nodes requires network configuration,
this example uses simulated data to show the analysis capabilities.
"""

import time
from libp2p import new_host
from multiaddr import Multiaddr
from libp2p.peer.id import ID as PeerID

from libp2p_privacy_poc.metadata_collector import MetadataCollector
from libp2p_privacy_poc.privacy_analyzer import PrivacyAnalyzer
from libp2p_privacy_poc.mock_zk_proofs import MockZKProofSystem
from libp2p_privacy_poc.report_generator import ReportGenerator
from libp2p_privacy_poc.zk_integration import ZKDataPreparator


def simulate_connections(collector: MetadataCollector):
    """Simulate some connection events for demonstration."""
    
    print("\n" + "=" * 60)
    print("Simulating Privacy-Relevant Network Activity")
    print("=" * 60)
    
    # Simulate connections to multiple peers
    peers = [
        ("QmPeer1abc123def456", "/ip4/192.168.1.100/tcp/4001"),
        ("QmPeer2xyz789ghi012", "/ip4/192.168.1.101/tcp/4001"),
        ("QmPeer3jkl345mno678", "/ip4/192.168.1.102/tcp/4001"),
        ("QmPeer1abc123def456", "/ip4/192.168.1.100/tcp/4002"),  # Same peer, different addr
        ("QmPeer4pqr901stu234", "/ip4/192.168.1.103/tcp/4001"),
    ]
    
    print("\nSimulating connections...")
    for i, (peer_id_str, addr_str) in enumerate(peers):
        # Create proper peer ID and multiaddr
        try:
            # For simulation, we'll use the string directly since creating real PeerIDs
            # requires private keys
            collector.on_connection_opened(
                peer_id=peer_id_str,  # Use string directly
                multiaddr=Multiaddr(addr_str),
                direction="outbound" if i % 2 == 0 else "inbound"
            )
            print(f"  ✓ Connection {i+1}: {peer_id_str[:20]}... ({addr_str})")
            time.sleep(0.1)  # Simulate timing between connections
        except Exception as e:
            print(f"  ✗ Error simulating connection: {e}")
    
    # Simulate some protocol negotiations
    print("\nSimulating protocol negotiations...")
    collector.on_protocol_negotiated("QmPeer1abc123def456", "/ipfs/id/1.0.0")
    collector.on_protocol_negotiated("QmPeer1abc123def456", "/ipfs/bitswap/1.2.0")
    collector.on_protocol_negotiated("QmPeer2xyz789ghi012", "/ipfs/id/1.0.0")
    print("  ✓ Protocols negotiated")
    
    # Simulate some stream activity
    print("\nSimulating stream activity...")
    collector.on_stream_opened("QmPeer1abc123def456")
    collector.on_stream_opened("QmPeer2xyz789ghi012")
    print("  ✓ Streams opened")
    
    print("\n" + "=" * 60)


def main():
    """Run the basic privacy analysis example."""
    
    print("\n" + "=" * 70)
    print("libp2p Privacy Analysis Tool - Basic Example")
    print("=" * 70)
    
    print("\n⚠️  Using simulated data for demonstration")
    print("In production, this would connect to real py-libp2p nodes\n")
    
    # Create a basic libp2p host (for structure, not actual networking)
    print("1. Creating libp2p host structure...")
    host = new_host()
    print(f"   Host ID: {host.get_id()}")
    
    # Note: We're not registering the notifee here since we're simulating
    # Create collector without auto-hooking
    print("\n2. Creating MetadataCollector...")
    collector = MetadataCollector(libp2p_host=None)  # No auto-hook for simulation
    print("   ✓ Collector created")
    
    # Simulate network activity
    simulate_connections(collector)
    
    # Run privacy analysis
    print("\n3. Running Privacy Analysis...")
    analyzer = PrivacyAnalyzer(collector)
    report = analyzer.analyze()
    
    print(f"\n   Analysis Complete!")
    print(f"   - Overall Risk Score: {report.overall_risk_score:.2f}/1.00")
    print(f"   - Risks Detected: {len(report.risks)}")
    print(f"   - Critical Risks: {len(report.get_critical_risks())}")
    print(f"   - High Risks: {len(report.get_high_risks())}")
    
    # Display summary
    print("\n" + "=" * 70)
    print("Privacy Analysis Summary")
    print("=" * 70)
    print(report.summary())
    
    # Generate ZK proofs (mock)
    print("\n" + "=" * 70)
    print("Generating Mock ZK Proofs")
    print("=" * 70)
    
    zk_system = MockZKProofSystem()
    preparator = ZKDataPreparator()
    
    # Generate anonymity set proof
    print("\n4. Generating anonymity set proof...")
    peer_ids = list(collector.peers.keys())
    if peer_ids:
        anonymity_proof = zk_system.generate_anonymity_set_proof(
            peer_id=peer_ids[0],
            anonymity_set_size=len(peer_ids)
        )
        print(f"   ✓ Proof generated")
        print(f"   Type: {anonymity_proof.proof_type}")
        print(f"   Claim: Peer is one of {len(peer_ids)} peers")
        
        # Verify proof
        is_valid = zk_system.verify_proof(anonymity_proof)
        print(f"   Verification: {'✓ Valid' if is_valid else '✗ Invalid'}")
    
    # Generate enhanced report with ZK proofs
    print("\n5. Generating reports...")
    
    # Generate proofs for the report (as dictionary)
    zk_proofs = {}
    if peer_ids:
        anonymity_proof = zk_system.generate_anonymity_set_proof(
            peer_id=peer_ids[0],
            anonymity_set_size=len(peer_ids)
        )
        zk_proofs["anonymity_set"] = [anonymity_proof]
    
    # Generate reports in different formats
    report_gen = ReportGenerator()
    
    # Console report
    print("\n   Generating console report...")
    console_report = report_gen.generate_console_report(report, zk_proofs)
    
    # JSON report
    print("   Generating JSON report...")
    json_report = report_gen.generate_json_report(report, zk_proofs)
    
    # HTML report  
    print("   Generating HTML report...")
    html_report = report_gen.generate_html_report(report, zk_proofs)
    
    print(f"\n   ✓ All reports generated successfully")
    
    # Export statistics
    print("\n6. Exporting statistics...")
    stats = collector.get_statistics()
    print(f"\n   Network Statistics:")
    print(f"   - Total connections: {stats['total_connections']}")
    print(f"   - Active connections: {stats['active_connections']}")
    print(f"   - Unique peers: {stats['unique_peers']}")
    print(f"   - Protocols seen: {stats['protocols_used']}")
    
    print("\n" + "=" * 70)
    print("✓ Analysis Complete!")
    print("=" * 70)
    
    print("\n💡 Next Steps:")
    print("   - Review the privacy risks identified above")
    print("   - Consider implementing recommended mitigations")
    print("   - Run periodic analyses to monitor privacy posture")
    print("   - In production, integrate with real py-libp2p event hooks\n")


if __name__ == "__main__":
    main()

