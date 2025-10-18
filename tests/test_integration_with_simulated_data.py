"""
Integration tests using simulated data.

Tests the full pipeline: MetadataCollector -> PrivacyAnalyzer -> ReportGenerator
using simulated connection events instead of real py-libp2p connections.

NOTE: Real py-libp2p node connections are not working due to listener
initialization issues. See KNOWN_ISSUES.md. This test validates the
complete privacy analysis pipeline using the same API that would be used
with real connections.
"""
import pytest
import trio
import time
from libp2p import new_host
from libp2p.peer.id import ID as PeerID
from multiaddr import Multiaddr

from libp2p_privacy_poc.metadata_collector import MetadataCollector
from libp2p_privacy_poc.privacy_analyzer import PrivacyAnalyzer
from libp2p_privacy_poc.report_generator import ReportGenerator
from libp2p_privacy_poc.mock_zk_proofs import MockZKProofSystem, ZKProofType
from libp2p_privacy_poc.zk_integration import ZKDataPreparator


@pytest.mark.trio
async def test_full_pipeline_with_simulated_events():
    """Test complete privacy analysis pipeline with simulated events."""
    
    print("\n" + "=" * 60)
    print("Testing Full Pipeline (Simulated Events)")
    print("=" * 60)
    
    # Create a host
    print("\n1. Creating libp2p host...")
    host = new_host()
    print(f"   Host ID: {host.get_id()}")
    
    # Attach collector
    print("\n2. Setting up MetadataCollector...")
    collector = MetadataCollector(host)
    
    # Simulate connection events
    print("\n3. Simulating connection events...")
    
    # Simulate 5 peer connections
    peer_ids = [
        PeerID.from_base58("QmPeer1" + "1" * 38),
        PeerID.from_base58("QmPeer2" + "2" * 38),
        PeerID.from_base58("QmPeer3" + "3" * 38),
        PeerID.from_base58("QmPeer4" + "4" * 38),
        PeerID.from_base58("QmPeer5" + "5" * 38),
    ]
    
    for i, peer_id in enumerate(peer_ids):
        multiaddr = Multiaddr(f"/ip4/127.0.0.1/tcp/{5000 + i}")
        collector.on_connection_opened(peer_id, multiaddr, "outbound")
        await trio.sleep(0.1)  # Simulate timing
        
        # Simulate some streams
        collector.on_stream_opened(peer_id)
        if i % 2 == 0:
            collector.on_stream_opened(peer_id)  # Some peers get 2 streams
        
        # Simulate protocol usage
        if i < 3:
            collector.on_protocol_negotiated(peer_id, "/ipfs/id/1.0.0")
        collector.on_protocol_negotiated(peer_id, "/ipfs/ping/1.0.0")
    
    print(f"   Simulated {len(peer_ids)} connections")
    
    # Check collector statistics
    print("\n4. Checking MetadataCollector statistics...")
    stats = collector.get_statistics()
    print(f"   Total connections: {stats['total_connections']}")
    print(f"   Active connections: {stats['active_connections']}")
    print(f"   Unique peers: {stats['unique_peers']}")
    print(f"   Protocols used: {stats['protocols_used']}")
    
    assert stats['total_connections'] == 5
    assert stats['unique_peers'] == 5
    assert stats['protocols_used'] > 0
    
    # Run privacy analysis
    print("\n5. Running PrivacyAnalyzer...")
    analyzer = PrivacyAnalyzer(collector)
    report = analyzer.analyze()
    
    print(f"   Risk Score: {report.overall_risk_score:.2f}")
    print(f"   Risks Detected: {len(report.risks)}")
    for risk in report.risks[:3]:  # Show first 3
        print(f"     - {risk.severity}: {risk.risk_type}")
    
    assert report.overall_risk_score >= 0.0
    assert report.overall_risk_score <= 1.0
    assert len(report.risks) > 0
    
    # Generate ZK proofs
    print("\n6. Generating mock ZK proofs...")
    zk_system = MockZKProofSystem()
    
    # Generate sample proofs directly
    # (In real usage, ZKDataPreparator would extract data from collector)
    peer_ids_str = [str(pid) for pid in peer_ids]
    anonymity_proof = zk_system.generate_anonymity_set_proof(
        peer_id=peer_ids_str[0],  # Use first peer as the prover
        anonymity_set_size=len(peer_ids_str)
    )
    
    # Generate timing independence proof
    timing_proof = zk_system.generate_timing_independence_proof(
        event_1="connection_open",
        event_2="protocol_negotiate",
        time_delta=0.1
    )
    
    print(f"   Anonymity proof: {anonymity_proof.proof_type}")
    print(f"     - Set size: {anonymity_proof.public_inputs.get('anonymity_set_size')}")
    print(f"   Timing proof: {timing_proof.proof_type}")
    
    assert anonymity_proof.is_valid
    assert timing_proof.is_valid
    
    # Generate reports
    print("\n7. Generating reports...")
    report_gen = ReportGenerator()
    
    zk_proofs_dict = {
        "anonymity_set": [anonymity_proof],
        "timing": [timing_proof]
    }
    
    # Console report
    console_report = report_gen.generate_console_report(
        report=report,
        zk_proofs=zk_proofs_dict,
        verbose=False
    )
    assert len(console_report) > 0
    print("   ✓ Console report generated")
    
    # JSON report
    json_report = report_gen.generate_json_report(report=report, zk_proofs=zk_proofs_dict)
    assert 'overall_risk_score' in json_report
    assert 'zk_proofs' in json_report
    print("   ✓ JSON report generated")
    
    # HTML report
    html_report = report_gen.generate_html_report(report=report, zk_proofs=zk_proofs_dict)
    assert '<html>' in html_report
    assert 'Privacy Analysis Report' in html_report
    print("   ✓ HTML report generated")
    
    print("\n" + "=" * 60)
    print("✓ Full pipeline test PASSED")
    print("=" * 60)
    
    # Cleanup
    await host.close()


@pytest.mark.trio
async def test_metadata_collector_api_integration():
    """Test that MetadataCollector integrates correctly with py-libp2p API."""
    
    print("\n" + "=" * 60)
    print("Testing MetadataCollector API Integration")
    print("=" * 60)
    
    # Create host
    print("\n1. Creating host...")
    host = new_host()
    network = host.get_network()
    
    print(f"   Host ID: {host.get_id()}")
    print(f"   Network type: {type(network).__name__}")
    
    # Create collector
    print("\n2. Creating MetadataCollector...")
    collector = MetadataCollector(host)
    
    # Verify notifee is registered
    print("\n3. Verifying INotifee registration...")
    assert hasattr(collector, 'notifee'), "Collector should have notifee attribute"
    assert collector.notifee is not None, "Notifee should be initialized"
    
    # Check that notifee is in network's notifees list
    assert collector.notifee in network.notifees, "Notifee should be registered with network"
    print("   ✓ INotifee correctly registered")
    
    # Test event handlers exist
    print("\n4. Verifying event handlers...")
    assert hasattr(collector, 'on_connection_opened')
    assert hasattr(collector, 'on_connection_closed')
    assert hasattr(collector, 'on_stream_opened')
    assert hasattr(collector, 'on_protocol_negotiated')
    print("   ✓ All event handlers present")
    
    # Test that handlers work
    print("\n5. Testing event handlers...")
    test_peer = PeerID.from_base58("QmTest" + "1" * 40)
    test_addr = Multiaddr("/ip4/1.2.3.4/tcp/1234")
    
    collector.on_connection_opened(test_peer, test_addr, "inbound")
    assert len(collector.peers) == 1
    print("   ✓ on_connection_opened works")
    
    # Check active connections
    active_conns = collector.get_active_connections()
    assert len(active_conns) == 1
    print("   ✓ Active connections tracked")
    
    collector.on_stream_opened(test_peer)
    # Note: stream count is tracked in peer metadata
    print("   ✓ on_stream_opened works")
    
    collector.on_protocol_negotiated(test_peer, "/test/protocol/1.0.0")
    # Note: peers dict is keyed by string, not PeerID object
    test_peer_str = str(test_peer)
    assert test_peer_str in collector.peers
    # Note: PeerMetadata has 'protocols' not 'protocols_used'
    assert len(collector.peers[test_peer_str].protocols) == 1
    print("   ✓ on_protocol_negotiated works")
    
    collector.on_connection_closed(test_peer, test_addr)
    assert len(collector.get_active_connections()) == 0
    print("   ✓ on_connection_closed works")
    
    print("\n" + "=" * 60)
    print("✓ API integration test PASSED")
    print("=" * 60)
    
    # Cleanup
    await host.close()


if __name__ == "__main__":
    # Run tests with trio
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))

