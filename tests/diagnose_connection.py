"""
Diagnostic script to understand py-libp2p connection issues.
"""
import trio
from libp2p import new_host
from libp2p.peer.peerinfo import info_from_p2p_addr
from multiaddr import Multiaddr
import time


async def test_basic_connection():
    """Test basic connection between two hosts."""
    print("\n" + "=" * 60)
    print("Diagnostic: py-libp2p Connection Test")
    print("=" * 60)
    
    # Create two hosts
    print("\n1. Creating hosts...")
    host1 = new_host()
    host2 = new_host()
    print(f"   Host 1 ID: {host1.get_id()}")
    print(f"   Host 2 ID: {host2.get_id()}")
    
    # Get networks
    network1 = host1.get_network()
    network2 = host2.get_network()
    
    print(f"\n2. Network info:")
    print(f"   Host1 network: {network1}")
    print(f"   Host2 network: {network2}")
    print(f"   Host1 transports: {network1.transport}")
    print(f"   Host2 transports: {network2.transport}")
    
    # Start listeners
    print(f"\n3. Starting listeners...")
    listen_addr1 = Multiaddr("/ip4/127.0.0.1/tcp/10100")
    listen_addr2 = Multiaddr("/ip4/127.0.0.1/tcp/10101")
    
    try:
        async with trio.open_nursery() as nursery:
            # Start listeners
            print(f"   Starting listener on {listen_addr1}...")
            nursery.start_soon(network1.listen, listen_addr1)
            
            print(f"   Starting listener on {listen_addr2}...")
            nursery.start_soon(network2.listen, listen_addr2)
            
            # Wait for listeners to start
            print(f"\n4. Waiting for listeners to start...")
            await trio.sleep(2.0)
            
            # Check if listeners are ready
            print(f"\n5. Checking listener status:")
            print(f"   Host1 listeners: {len(network1.listeners)}")
            for i, listener in enumerate(network1.listeners):
                print(f"     Listener {i}: {listener}")
                if hasattr(listener, 'get_addrs'):
                    addrs = listener.get_addrs()
                    print(f"       Addresses: {addrs}")
            
            print(f"   Host2 listeners: {len(network2.listeners)}")
            for i, listener in enumerate(network2.listeners):
                print(f"     Listener {i}: {listener}")
                if hasattr(listener, 'get_addrs'):
                    addrs = listener.get_addrs()
                    print(f"       Addresses: {addrs}")
            
            # Try to get the actual listening address
            if network1.listeners:
                actual_addrs = network1.listeners[0].get_addrs() if hasattr(network1.listeners[0], 'get_addrs') else []
                if actual_addrs:
                    listen_addr1 = actual_addrs[0]
                    print(f"\n   Using actual host1 address: {listen_addr1}")
            
            # Construct full multiaddr with peer ID
            print(f"\n6. Constructing connection address...")
            full_addr = listen_addr1.encapsulate(Multiaddr(f"/p2p/{host1.get_id()}"))
            print(f"   Full address: {full_addr}")
            
            # Create peer info
            try:
                peer_info = info_from_p2p_addr(full_addr)
                print(f"   Peer info created: {peer_info.peer_id}")
                print(f"   Peer addrs: {peer_info.addrs}")
            except Exception as e:
                print(f"   ✗ Failed to create peer info: {e}")
                nursery.cancel_scope.cancel()
                return
            
            # Try to connect
            print(f"\n7. Attempting connection from host2 to host1...")
            try:
                await host2.connect(peer_info)
                print(f"   ✓ Connection successful!")
                
                # Check connections
                print(f"\n8. Verifying connection:")
                conns1 = network1.connections
                conns2 = network2.connections
                print(f"   Host1 connections: {len(conns1)}")
                print(f"   Host2 connections: {len(conns2)}")
                
                for peer_id, conns in conns2.items():
                    print(f"   Host2 -> {peer_id}: {len(conns)} connection(s)")
                
            except Exception as e:
                print(f"   ✗ Connection failed: {e}")
                print(f"\n   Diagnostic info:")
                print(f"   - Host1 listening: {len(network1.listeners) > 0}")
                print(f"   - Host2 listening: {len(network2.listeners) > 0}")
                print(f"   - Target address: {full_addr}")
                
                # Try with peerstore
                print(f"\n   Checking peerstore...")
                peerstore = host2.get_peerstore()
                print(f"   Peerstore: {peerstore}")
                
                import traceback
                traceback.print_exc()
            
            # Cleanup
            print(f"\n9. Cleaning up...")
            await host1.close()
            await host2.close()
            
            nursery.cancel_scope.cancel()
            
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Diagnostic complete")
    print("=" * 60)


if __name__ == "__main__":
    trio.run(test_basic_connection)

