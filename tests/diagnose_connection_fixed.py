"""
Fixed diagnostic script - using listen() correctly.
"""
import trio
from libp2p import new_host
from libp2p.peer.peerinfo import info_from_p2p_addr
from multiaddr import Multiaddr


async def test_connection_fixed():
    """Test connection with proper listen() usage."""
    print("\n" + "=" * 60)
    print("FIXED: py-libp2p Connection Test")
    print("=" * 60)
    
    # Create hosts
    print("\n1. Creating hosts...")
    host1 = new_host()
    host2 = new_host()
    print(f"   Host 1 ID: {host1.get_id()}")
    print(f"   Host 2 ID: {host2.get_id()}")
    
    # Start listeners - listen() is SYNCHRONOUS, not async!
    print(f"\n2. Starting listeners (synchronously)...")
    listen_addr1 = Multiaddr("/ip4/127.0.0.1/tcp/10200")
    listen_addr2 = Multiaddr("/ip4/127.0.0.1/tcp/10201")
    
    network1 = host1.get_network()
    network2 = host2.get_network()
    
    # Call listen() directly - it's not async!
    result1 = network1.listen(listen_addr1)
    print(f"   Host1 listen result: {result1}")
    
    result2 = network2.listen(listen_addr2)
    print(f"   Host2 listen result: {result2}")
    
    # Give the listeners a moment to fully initialize
    await trio.sleep(0.5)
    
    # Check listener status
    print(f"\n3. Checking listener status:")
    print(f"   Host1 listeners: {len(network1.listeners)}")
    if network1.listeners:
        for i, listener in enumerate(network1.listeners):
            addrs = listener.get_addrs() if hasattr(listener, 'get_addrs') else []
            print(f"     Listener {i}: {addrs}")
    
    print(f"   Host2 listeners: {len(network2.listeners)}")
    if network2.listeners:
        for i, listener in enumerate(network2.listeners):
            addrs = listener.get_addrs() if hasattr(listener, 'get_addrs') else []
            print(f"     Listener {i}: {addrs}")
    
    if not network1.listeners:
        print("\n✗ Host1 listeners not started - test cannot continue")
        return
    
    # Get actual listening address
    actual_addr1 = network1.listeners[0].get_addrs()[0]
    print(f"\n4. Actual host1 address: {actual_addr1}")
    
    # Construct full address with peer ID
    full_addr = actual_addr1.encapsulate(Multiaddr(f"/p2p/{host1.get_id()}"))
    print(f"   Full address: {full_addr}")
    
    # Create peer info and connect
    print(f"\n5. Connecting host2 to host1...")
    try:
        peer_info = info_from_p2p_addr(full_addr)
        await host2.connect(peer_info)
        print(f"   ✓ Connection successful!")
        
        # Verify connections
        print(f"\n6. Verifying connections:")
        print(f"   Host1 connections: {len(network1.connections)}")
        print(f"   Host2 connections: {len(network2.connections)}")
        
        for peer_id, conns in network2.connections.items():
            print(f"   Host2 connected to {peer_id}: {len(conns)} connection(s)")
        
        print("\n" + "=" * 60)
        print("✓ TEST PASSED - Connection works!")
        print("=" * 60)
        
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print(f"\n7. Cleaning up...")
        await host1.close()
        await host2.close()


if __name__ == "__main__":
    trio.run(test_connection_fixed)

