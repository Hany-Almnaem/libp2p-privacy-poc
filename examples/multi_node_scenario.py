"""
Multi-node privacy analysis scenario.

This example demonstrates privacy analysis across multiple interconnected
nodes, showing how privacy leaks can emerge from network-wide patterns.

NOTE: Uses simulated connection events due to py-libp2p listener initialization
issues. See KNOWN_ISSUES.md for details.
"""
import trio
import time
from libp2p import new_host
from libp2p.peer.id import ID as PeerID
from multiaddr import Multiaddr

from libp2p_privacy_poc.metadata_collector import MetadataCollector
from libp2p_privacy_poc.privacy_analyzer import PrivacyAnalyzer
from libp2p_privacy_poc.report_generator import ReportGenerator
from libp2p_privacy_poc.mock_zk_proofs import MockZKProofSystem


class NetworkNode:
    """Represents a node in the network."""
    
    def __init__(self, name: str, host):
        self.name = name
        self.host = host
        self.collector = MetadataCollector(host)
        self.peer_id = host.get_id()
        self.connections = []
    
    def simulate_connection(self, peer_id: PeerID, multiaddr: Multiaddr, direction: str):
        """Simulate a connection event."""
        self.collector.on_connection_opened(peer_id, multiaddr, direction)
        self.connections.append((peer_id, multiaddr, direction))
    
    def simulate_disconnect(self, peer_id: PeerID, multiaddr: Multiaddr):
        """Simulate a disconnection event."""
        self.collector.on_connection_closed(peer_id, multiaddr)
    
    def simulate_protocol(self, peer_id: PeerID, protocol: str):
        """Simulate protocol negotiation."""
        self.collector.on_protocol_negotiated(peer_id, protocol)
    
    def simulate_stream(self, peer_id: PeerID):
        """Simulate stream opening."""
        self.collector.on_stream_opened(peer_id)
    
    def analyze(self) -> tuple:
        """Run privacy analysis."""
        analyzer = PrivacyAnalyzer(self.collector)
        report = analyzer.analyze()
        return report, self.collector.get_statistics()


async def main():
    """Main demonstration."""
    print("\n" + "=" * 70)
    print("MULTI-NODE PRIVACY ANALYSIS SCENARIO")
    print("=" * 70)
    print("\nThis example demonstrates:")
    print("- Privacy analysis across 5 interconnected nodes")
    print("- Detection of network-wide privacy patterns")
    print("- Comparative risk analysis between nodes")
    print("- Identification of high-risk connection patterns")
    
    # Create 5 nodes
    print("\n" + "-" * 70)
    print("1. Creating 5 network nodes...")
    print("-" * 70)
    
    nodes = []
    for i in range(5):
        host = new_host()
        node = NetworkNode(f"Node-{i+1}", host)
        nodes.append(node)
        print(f"   {node.name}: {node.peer_id}")
    
    # Simulate network topology: Star network with Node-1 as hub
    print("\n" + "-" * 70)
    print("2. Simulating star network topology...")
    print("-" * 70)
    print("   Node-1 (hub) connects to all other nodes")
    print("   Other nodes connect only to Node-1")
    
    hub = nodes[0]
    spoke_nodes = nodes[1:]
    
    # Hub connects to all spokes
    for i, spoke in enumerate(spoke_nodes):
        multiaddr = Multiaddr(f"/ip4/127.0.0.1/tcp/{5000 + i}")
        
        # Outbound from hub
        hub.simulate_connection(spoke.peer_id, multiaddr, "outbound")
        
        # Inbound to spoke
        spoke.simulate_connection(hub.peer_id, multiaddr, "inbound")
        
        # Wait a bit (timing matters for privacy!)
        await trio.sleep(0.05)
        
        # Simulate protocol negotiation
        hub.simulate_protocol(spoke.peer_id, "/ipfs/id/1.0.0")
        hub.simulate_protocol(spoke.peer_id, "/ipfs/ping/1.0.0")
        spoke.simulate_protocol(hub.peer_id, "/ipfs/id/1.0.0")
        spoke.simulate_protocol(hub.peer_id, "/ipfs/ping/1.0.0")
        
        # Simulate some streams
        hub.simulate_stream(spoke.peer_id)
        spoke.simulate_stream(hub.peer_id)
    
    print(f"   ✓ Network topology established")
    print(f"   ✓ Hub has {len(hub.connections)} connections")
    print(f"   ✓ Each spoke has 1 connection")
    
    # Simulate some additional traffic patterns
    print("\n" + "-" * 70)
    print("3. Simulating traffic patterns...")
    print("-" * 70)
    
    # Hub node makes additional connections in quick succession (timing leak!)
    print("   Hub making rapid connections (privacy leak!)...")
    # Create some external peer IDs (using actual hosts)
    external_peers = [new_host().get_id() for _ in range(3)]
    
    for i, external_peer in enumerate(external_peers):
        external_addr = Multiaddr(f"/ip4/1.2.3.{i+10}/tcp/4001")
        
        hub.simulate_connection(external_peer, external_addr, "outbound")
        hub.simulate_protocol(external_peer, "/ipfs/bitswap/1.2.0")
        await trio.sleep(0.02)  # Very short interval = timing correlation!
    
    print(f"   ✓ Hub made 3 additional connections in 60ms")
    
    # Spoke nodes make connections at different times
    print("   Spoke nodes making connections...")
    spoke_external_peers = [new_host().get_id() for _ in range(len(spoke_nodes))]
    
    for i, (spoke, external_peer) in enumerate(zip(spoke_nodes, spoke_external_peers)):
        external_addr = Multiaddr(f"/ip4/10.0.0.{i+1}/tcp/4001")
        
        spoke.simulate_connection(external_peer, external_addr, "outbound")
        spoke.simulate_protocol(external_peer, "/ipfs/dht/1.0.0")
        await trio.sleep(0.2)  # Longer interval = better privacy
    
    print(f"   ✓ Spoke nodes made connections with better timing")
    
    # Analyze each node
    print("\n" + "-" * 70)
    print("4. Running privacy analysis on each node...")
    print("-" * 70)
    
    results = []
    for node in nodes:
        report, stats = node.analyze()
        results.append((node, report, stats))
        
        # Determine risk level from score
        if report.overall_risk_score >= 0.7:
            risk_level = "CRITICAL"
        elif report.overall_risk_score >= 0.5:
            risk_level = "HIGH"
        elif report.overall_risk_score >= 0.3:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        print(f"\n   {node.name} Analysis:")
        print(f"   {'─' * 60}")
        print(f"     Connections: {stats['total_connections']}")
        print(f"     Unique Peers: {stats['unique_peers']}")
        print(f"     Protocols: {stats['protocols_used']}")
        print(f"     Risk Score: {report.overall_risk_score:.2f}/1.00")
        print(f"     Risk Level: {risk_level}")
        print(f"     Risks Detected: {len(report.risks)}")
        
        if report.risks:
            print(f"     Top Risks:")
            for risk in report.risks[:3]:
                print(f"       • {risk.severity}: {risk.risk_type}")
    
    # Comparative analysis
    print("\n" + "-" * 70)
    print("5. Comparative Analysis")
    print("-" * 70)
    
    # Find highest risk node
    highest_risk_node = max(results, key=lambda x: x[1].overall_risk_score)
    lowest_risk_node = min(results, key=lambda x: x[1].overall_risk_score)
    
    print(f"\n   🔴 Highest Risk: {highest_risk_node[0].name}")
    print(f"      Score: {highest_risk_node[1].overall_risk_score:.2f}")
    print(f"      Reason: Hub node with many connections and timing correlations")
    
    print(f"\n   🟢 Lowest Risk: {lowest_risk_node[0].name}")
    print(f"      Score: {lowest_risk_node[1].overall_risk_score:.2f}")
    print(f"      Reason: Fewer connections with better timing distribution")
    
    # Network-wide statistics
    print("\n   📊 Network-Wide Statistics:")
    total_connections = sum(stats['total_connections'] for _, _, stats in results)
    avg_risk = sum(report.overall_risk_score for _, report, _ in results) / len(results)
    total_risks = sum(len(report.risks) for _, report, _ in results)
    
    print(f"      Total Connections: {total_connections}")
    print(f"      Average Risk Score: {avg_risk:.2f}")
    print(f"      Total Privacy Risks: {total_risks}")
    
    # Generate detailed report for hub node
    print("\n" + "-" * 70)
    print("6. Generating detailed report for hub node...")
    print("-" * 70)
    
    hub_report = highest_risk_node[1]
    report_gen = ReportGenerator()
    
    # Generate console report
    console_report = report_gen.generate_console_report(
        report=hub_report,
        verbose=True
    )
    
    print("\n" + console_report)
    
    # Key insights
    print("\n" + "=" * 70)
    print("KEY INSIGHTS")
    print("=" * 70)
    
    print("""
1. **Hub Node Risk**: The central hub has the highest risk due to:
   - High connection count (anonymity set correlation)
   - Rapid connection timing (timing correlation leak)
   - Multiple protocols (fingerprinting risk)

2. **Spoke Node Privacy**: Spoke nodes have better privacy because:
   - Fewer connections (smaller attack surface)
   - Better-spaced connection timing
   - Limited protocol diversity

3. **Network Topology Impact**: Star topology creates:
   - Single point of identification (hub)
   - Correlation opportunities through hub traffic
   - Potential for network-wide de-anonymization

4. **Recommendations**:
   - Implement random delays between connections
   - Use more decentralized topology (mesh)
   - Limit connections per node
   - Rotate connection patterns
   - Use timing obfuscation techniques
    """)
    
    print("\n" + "=" * 70)
    print("SCENARIO COMPLETE")
    print("=" * 70)
    print("\nThis demonstrates how privacy risks vary across network topology")
    print("and connection patterns. Use these insights to improve your network design!")
    
    # Cleanup
    for node in nodes:
        await node.host.close()


if __name__ == "__main__":
    trio.run(main)

