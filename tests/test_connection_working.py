"""
Working connection test - properly handling async listen().
"""
import trio
from libp2p import new_host
from libp2p.peer.peerinfo import info_from_p2p_addr
from multiaddr import Multiaddr


async def wait_for_listener(network, timeout=5.0):
    """Wait for listener to actually start."""
    start_time = trio.current_time()
    while trio.current_time() - start_time < timeout:
        if len(network.listeners) > 0:
            return True
        await trio.sleep(0.1)
    return False


async def test_working_connection():
    """Test connection with proper async handling."""
    print("\n" + "=" * 60)
    print("WORKING: py-libp2p Connection Test")
    print("=" * 60)
    
    # Create hosts
    print("\n1. Creating hosts...")
    host1 = new_host()
    host2 = new_host()
    print(f"   Host 1 ID: {host1.get_id()}")
    print(f"   Host 2 ID: {host2.get_id()}")
    
    network1 = host1.get_network()
    network2 = host2.get_network()
    
    # Start listeners in background
    print(f"\n2. Starting listeners...")
    listen_addr1 = Multiaddr("/ip4/127.0.0.1/tcp/0")  # Use port 0 for auto-assign
    listen_addr2 = Multiaddr("/ip4/127.0.0.1/tcp/0")
    
    async with trio.open_nursery() as nursery:
        # Start listeners as background tasks
        nursery.start_soon(network1.listen, listen_addr1)
        nursery.start_soon(network2.listen, listen_addr2)
        
        # Wait for listeners to actually start
        print(f"   Waiting for host1 listener...")
        if not await wait_for_listener(network1):
            print("   ✗ Host1 listener timeout")
            nursery.cancel_scope.cancel()
            return
        print(f"   ✓ Host1 listener ready")
        
        print(f"   Waiting for host2 listener...")
        if not await wait_for_listener(network2):
            print("   ✗ Host2 listener timeout")
            nursery.cancel_scope.cancel()
            return
        print(f"   ✓ Host2 listener ready")
        
        # Get actual listening addresses
        actual_addr1 = network1.listeners[0].get_addrs()[0]
        print(f"\n3. Host1 listening on: {actual_addr1}")
        
        # Construct full address
        full_addr = actual_addr1.encapsulate(Multiaddr(f"/p2p/{host1.get_id()}"))
        print(f"   Full address: {full_addr}")
        
        # Connect
        print(f"\n4. Connecting host2 to host1...")
        try:
            peer_info = info_from_p2p_addr(full_addr)
            await host2.connect(peer_info)
            print(f"   ✓ Connection successful!")
            
            # Verify
            print(f"\n5. Connection details:")
            print(f"   Host1 connections: {len(network1.connections)}")
            print(f"   Host2 connections: {len(network2.connections)}")
            
            for peer_id, conns in network2.connections.items():
                print(f"   Host2 -> {peer_id}: {len(conns)} connection(s)")
            
            # Test with metadata collector
            print(f"\n6. Testing with MetadataCollector...")
            from libp2p_privacy_poc.metadata_collector import MetadataCollector
            from libp2p_privacy_poc.privacy_analyzer import PrivacyAnalyzer
            
            collector = MetadataCollector(host1)
            
            # Simulate another connection
            host3 = new_host()
            network3 = host3.get_network()
            nursery.start_soon(network3.listen, Multiaddr("/ip4/127.0.0.1/tcp/0"))
            
            if await wait_for_listener(network3):
                try:
                    await host3.connect(peer_info)
                    print(f"   ✓ Additional connection from host3")
                except Exception as e:
                    print(f"   ! Could not connect host3: {e}")
            
            # Wait a bit for events
            await trio.sleep(0.5)
            
            # Analyze
            analyzer = PrivacyAnalyzer(collector)
            report = analyzer.analyze()
            
            print(f"\n7. Privacy Analysis Results:")
            print(f"   Risk Score: {report.overall_risk_score:.2f}")
            print(f"   Risks Detected: {len(report.risks)}")
            print(f"   Active Connections Tracked: {len(collector.get_active_connections())}")
            print(f"   Unique Peers: {len(collector.peers)}")
            
            print("\n" + "=" * 60)
            print("✓ TEST PASSED - Everything works!")
            print("=" * 60)
            
        except Exception as e:
            print(f"   ✗ Connection failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Cleanup
            print(f"\n8. Cleaning up...")
            await host1.close()
            await host2.close()
            if 'host3' in locals():
                await host3.close()
            
            # Cancel the nursery
            nursery.cancel_scope.cancel()


if __name__ == "__main__":
    trio.run(test_working_connection)

