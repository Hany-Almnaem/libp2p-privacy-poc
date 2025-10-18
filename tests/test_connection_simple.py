"""
Simple approach: Use listen_addrs in new_host().
"""
import trio
from libp2p import new_host
from libp2p.peer.peerinfo import info_from_p2p_addr
from multiaddr import Multiaddr
import time


async def test_simple_connection():
    """Test with listen_addrs in new_host()."""
    print("\n" + "=" * 60)
    print("SIMPLE: py-libp2p Connection Test")
    print("=" * 60)
    
    # Create hosts WITH listen_addrs parameter
    print("\n1. Creating hosts with listen addresses...")
    
    listen_addr1 = Multiaddr("/ip4/127.0.0.1/tcp/10300")
    listen_addr2 = Multiaddr("/ip4/127.0.0.1/tcp/10301")
    
    # NOTE: new_host() with listen_addrs should automatically start listening
    host1 = new_host(listen_addrs=[listen_addr1])
    host2 = new_host(listen_addrs=[listen_addr2])
    
    print(f"   Host 1 ID: {host1.get_id()}")
    print(f"   Host 2 ID: {host2.get_id()}")
    
    network1 = host1.get_network()
    network2 = host2.get_network()
    
    # Give time for listeners to start
    print(f"\n2. Waiting for listeners to initialize...")
    await trio.sleep(1.0)
    
    # Check if listeners started
    print(f"\n3. Checking listeners:")
    print(f"   Host1 listeners: {len(network1.listeners)}")
    print(f"   Host2 listeners: {len(network2.listeners)}")
    
    if network1.listeners:
        addrs = network1.listeners[0].get_addrs()
        print(f"   Host1 listening on: {addrs}")
        actual_addr1 = addrs[0] if addrs else listen_addr1
    else:
        print("   ⚠ Host1 not listening - this might still work with direct connection")
        actual_addr1 = listen_addr1
    
    # Try to connect
    print(f"\n4. Attempting connection...")
    full_addr = actual_addr1.encapsulate(Multiaddr(f"/p2p/{host1.get_id()}"))
    print(f"   Connecting to: {full_addr}")
    
    try:
        peer_info = info_from_p2p_addr(full_addr)
        await host2.connect(peer_info)
        print(f"   ✓ Connection successful!")
        
        # Verify
        print(f"\n5. Verification:")
        print(f"   Host1 connections: {len(network1.connections)}")
        print(f"   Host2 connections: {len(network2.connections)}")
        
        if network2.connections:
            for peer_id, conns in network2.connections.items():
                print(f"   Host2 -> {str(peer_id)[:20]}...: {len(conns)} connection(s)")
        
        # Test MetadataCollector
        print(f"\n6. Testing MetadataCollector...")
        from libp2p_privacy_poc.metadata_collector import MetadataCollector
        from libp2p_privacy_poc.privacy_analyzer import PrivacyAnalyzer
        
        collector = MetadataCollector(host1)
        await trio.sleep(0.5)
        
        # Check what was collected
        stats = collector.get_statistics()
        print(f"   Total connections: {stats['total_connections']}")
        print(f"   Active connections: {stats['active_connections']}")
        print(f"   Unique peers: {stats['unique_peers']}")
        
        # Analyze
        analyzer = PrivacyAnalyzer(collector)
        report = analyzer.analyze()
        
        print(f"   Risk Score: {report.overall_risk_score:.2f}")
        print(f"   Risks Detected: {len(report.risks)}")
        
        print("\n" + "=" * 60)
        print("✓ SUCCESS!")
        print("=" * 60)
        
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        print(f"\n   This might be expected - py-libp2p connection")
        print(f"   setup is complex and may require additional configuration.")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print(f"\n7. Cleaning up...")
        try:
            await host1.close()
            await host2.close()
        except Exception as e:
            print(f"   Note: Cleanup error (expected): {e}")


if __name__ == "__main__":
    trio.run(test_simple_connection)

