"""
Basic integration test for MetadataCollector with real py-libp2p nodes.

This test verifies that the MetadataCollector can successfully hook into
py-libp2p's event system and collect connection metadata.
"""
import trio
import pytest
from libp2p import new_host
from libp2p.peer.peerinfo import info_from_p2p_addr
from multiaddr import Multiaddr

from libp2p_privacy_poc.metadata_collector import MetadataCollector
from libp2p_privacy_poc.privacy_analyzer import PrivacyAnalyzer


@pytest.mark.trio
async def test_metadata_collection_with_two_nodes():
    """Test that MetadataCollector captures connection events between two nodes."""
    
    print("\n" + "=" * 60)
    print("Testing MetadataCollector with 2 py-libp2p nodes")
    print("=" * 60)
    
    # Create two hosts
    print("\n1. Creating two libp2p hosts...")
    host1 = new_host()
    host2 = new_host()
    
    print(f"   Host 1 ID: {host1.get_id()}")
    print(f"   Host 2 ID: {host2.get_id()}")
    
    # Attach metadata collector to host1
    print("\n2. Attaching MetadataCollector to host1...")
    collector = MetadataCollector(host1)
    
    # Start listening on both hosts
    print("\n3. Starting listeners...")
    
    # Use explicit ports for simpler testing
    host1_listen_addr = Multiaddr("/ip4/127.0.0.1/tcp/10000")
    host2_listen_addr = Multiaddr("/ip4/127.0.0.1/tcp/10001")
    
    async with trio.open_nursery() as nursery:
        # Start listeners in background
        nursery.start_soon(host1.get_network().listen, host1_listen_addr)
        nursery.start_soon(host2.get_network().listen, host2_listen_addr)
        
        # Give listeners time to start
        await trio.sleep(1.0)
        
        print(f"   Host 1 should be listening on: {host1_listen_addr}/p2p/{host1.get_id()}")
        print(f"   Host 2 should be listening on: {host2_listen_addr}/p2p/{host2.get_id()}")
        
        # Connect from host2 to host1
        print("\n4. Connecting host2 to host1...")
        host1_full_addr = host1_listen_addr.encapsulate(Multiaddr(f"/p2p/{host1.get_id()}"))
        host1_peer_info = info_from_p2p_addr(host1_full_addr)
        
        await host2.connect(host1_peer_info)
        print("   ✓ Connection established")
        
        # Give the notifee time to process events
        await trio.sleep(0.5)
        
        # Check collected metadata
        print("\n5. Verifying collected metadata...")
        active_connections = collector.get_active_connections()
        print(f"   Active connections: {len(active_connections)}")
        
        assert len(active_connections) >= 1, "Should have at least 1 active connection"
        
        conn = active_connections[0]
        print(f"   Connection details:")
        print(f"     - Peer ID: {conn.peer_id}")
        print(f"     - Direction: {conn.direction}")
        print(f"     - Transport: {conn.transport_type}")
        print(f"     - Duration: {time.time() - conn.timestamp_start:.2f}s")
        
        # Verify peer tracking
        peer_ids = list(collector.peers.keys())
        print(f"\n   Tracked peers: {len(peer_ids)}")
        assert len(peer_ids) >= 1, "Should have tracked at least 1 peer"
        
        # Test privacy analyzer
        print("\n6. Running privacy analysis...")
        analyzer = PrivacyAnalyzer(collector)
        report = analyzer.analyze()
        
        print(f"   Risk score: {report.overall_risk_score:.2f}")
        print(f"   Risks detected: {len(report.risks)}")
        
        # Close connection
        print("\n7. Closing connection...")
        await host2.close()
        await host1.close()
        
        # Give notifee time to process disconnect event
        await trio.sleep(0.1)
        
        print("\n" + "=" * 60)
        print("✓ Integration test passed!")
        print("=" * 60)
        
        # Cancel the nursery to stop listeners
        nursery.cancel_scope.cancel()


@pytest.mark.trio
async def test_metadata_collection_statistics():
    """Test that MetadataCollector correctly tracks statistics."""
    
    print("\n" + "=" * 60)
    print("Testing MetadataCollector Statistics")
    print("=" * 60)
    
    # Create hosts
    host1 = new_host()
    host2 = new_host()
    collector = MetadataCollector(host1)
    
    host1_listen_addr = Multiaddr("/ip4/127.0.0.1/tcp/10002")
    host2_listen_addr = Multiaddr("/ip4/127.0.0.1/tcp/10003")
    
    async with trio.open_nursery() as nursery:
        nursery.start_soon(host1.get_network().listen, host1_listen_addr)
        nursery.start_soon(host2.get_network().listen, host2_listen_addr)
        await trio.sleep(1.0)
        
        # Connect
        host1_full_addr = host1_listen_addr.encapsulate(Multiaddr(f"/p2p/{host1.get_id()}"))
        host1_peer_info = info_from_p2p_addr(host1_full_addr)
        await host2.connect(host1_peer_info)
        await trio.sleep(0.2)
        
        # Check statistics
        stats = collector.get_statistics()
        print(f"\nStatistics:")
        print(f"  Total connections: {stats['total_connections']}")
        print(f"  Active connections: {stats['active_connections']}")
        print(f"  Unique peers: {stats['unique_peers']}")
        
        assert stats['total_connections'] >= 1
        assert stats['active_connections'] >= 1
        assert stats['unique_peers'] >= 1
        
        # Cleanup
        await host2.close()
        await host1.close()
        nursery.cancel_scope.cancel()
    
    print("\n✓ Statistics test passed!")


if __name__ == "__main__":
    # Run tests directly
    import time
    
    async def run_tests():
        await test_metadata_collection_with_two_nodes()
        await test_metadata_collection_statistics()
    
    trio.run(run_tests)

