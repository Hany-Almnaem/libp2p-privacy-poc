"""
FINAL WORKING VERSION: Properly initialize network with run() before listen().
"""
import trio
from libp2p import new_host
from libp2p.peer.peerinfo import info_from_p2p_addr
from multiaddr import Multiaddr


async def test_final_working():
    """Test with proper network initialization."""
    print("\n" + "=" * 60)
    print("FINAL: py-libp2p Connection Test")
    print("=" * 60)
    
    # Create hosts
    print("\n1. Creating hosts...")
    host1 = new_host()
    host2 = new_host()
    print(f"   Host 1 ID: {host1.get_id()}")
    print(f"   Host 2 ID: {host2.get_id()}")
    
    network1 = host1.get_network()
    network2 = host2.get_network()
    
    print(f"\n2. Starting network run() tasks...")
    async with trio.open_nursery() as nursery:
        # CRITICAL: Start network.run() FIRST - this creates the internal nursery
        nursery.start_soon(network1.run)
        nursery.start_soon(network2.run)
        
        # Give networks time to initialize
        await trio.sleep(0.3)
        
        # Now listeners can be started
        print(f"\n3. Starting listeners...")
        listen_addr1 = Multiaddr("/ip4/127.0.0.1/tcp/0")
        listen_addr2 = Multiaddr("/ip4/127.0.0.1/tcp/0")
        
        nursery.start_soon(network1.listen, listen_addr1)
        nursery.start_soon(network2.listen, listen_addr2)
        
        # Wait for listeners to start
        await trio.sleep(0.5)
        
        # Check listeners
        print(f"   Host1 listeners: {len(network1.listeners)}")
        print(f"   Host2 listeners: {len(network2.listeners)}")
        
        if not network1.listeners or not network2.listeners:
            print("   ✗ Listeners not started")
            nursery.cancel_scope.cancel()
            return
        
        # Get actual addresses
        actual_addr1 = network1.listeners[0].get_addrs()[0]
        print(f"   Host1 listening on: {actual_addr1}")
        
        # Connect
        print(f"\n4. Connecting...")
        full_addr = actual_addr1.encapsulate(Multiaddr(f"/p2p/{host1.get_id()}"))
        
        try:
            peer_info = info_from_p2p_addr(full_addr)
            await host2.connect(peer_info)
            print(f"   ✓ Connection successful!")
            
            # Verify
            print(f"\n5. Verification:")
            print(f"   Host1 connections: {len(network1.connections)}")
            print(f"   Host2 connections: {len(network2.connections)}")
            
            for peer_id, conns in network2.connections.items():
                print(f"   Host2 -> {peer_id[:16]}...: {len(conns)} connection(s)")
            
            # Test with MetadataCollector
            print(f"\n6. Testing MetadataCollector...")
            from libp2p_privacy_poc.metadata_collector import MetadataCollector
            from libp2p_privacy_poc.privacy_analyzer import PrivacyAnalyzer
            
            collector = MetadataCollector(host1)
            await trio.sleep(0.3)  # Let events process
            
            # Analyze
            analyzer = PrivacyAnalyzer(collector)
            report = analyzer.analyze()
            
            print(f"   Risk Score: {report.overall_risk_score:.2f}")
            print(f"   Risks Detected: {len(report.risks)}")
            print(f"   Connections Tracked: {len(collector.get_active_connections())}")
            
            print("\n" + "=" * 60)
            print("✓ SUCCESS - All systems working!")
            print("=" * 60)
            
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Cleanup
            print(f"\n7. Cleaning up...")
            await host1.close()
            await host2.close()
            nursery.cancel_scope.cancel()


if __name__ == "__main__":
    trio.run(test_final_working)

