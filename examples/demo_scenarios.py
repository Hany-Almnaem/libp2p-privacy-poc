"""
Privacy Analysis Demo Scenarios.

This script demonstrates different privacy leak scenarios and shows how
the analysis tool detects them, along with ZK proof demonstrations.

Each scenario is self-contained and includes:
1. Setup and simulation
2. Privacy analysis
3. ZK proof generation
4. Results and interpretation
"""
import trio
import time
from libp2p import new_host
from libp2p.peer.id import ID as PeerID
from multiaddr import Multiaddr

from libp2p_privacy_poc.metadata_collector import MetadataCollector
from libp2p_privacy_poc.privacy_analyzer import PrivacyAnalyzer
from libp2p_privacy_poc.report_generator import ReportGenerator
from libp2p_privacy_poc.mock_zk_proofs import MockZKProofSystem, ZKProofType


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_subheader(title: str):
    """Print a formatted subheader."""
    print("\n" + "-" * 70)
    print(f"  {title}")
    print("-" * 70)


async def scenario_1_timing_correlation():
    """
    Scenario 1: Timing Correlation Attack
    
    This scenario demonstrates how rapid, sequential connections can
    create timing correlations that leak privacy information.
    """
    print_header("SCENARIO 1: Timing Correlation Attack")
    
    print("\n📖 Description:")
    print("   A node makes multiple connections in rapid succession, creating")
    print("   a distinctive timing pattern that can be used to identify the node.")
    
    print_subheader("Simulation")
    
    host = new_host()
    collector = MetadataCollector(host)
    
    # Create peer IDs
    peers = [new_host().get_id() for _ in range(5)]
    
    # Simulate rapid connections (BAD - creates timing correlation)
    print("   Making 5 connections in rapid succession...")
    for i, peer_id in enumerate(peers):
        multiaddr = Multiaddr(f"/ip4/10.1.1.{i+1}/tcp/4001")
        collector.on_connection_opened(peer_id, multiaddr, "outbound")
        collector.on_protocol_negotiated(peer_id, "/ipfs/id/1.0.0")
        await trio.sleep(0.01)  # Very short delay - THIS IS THE LEAK!
    
    print("   ✓ Connections made with 10ms intervals")
    
    # Analyze
    print_subheader("Analysis")
    analyzer = PrivacyAnalyzer(collector)
    report = analyzer.analyze()
    
    print(f"   Risk Score: {report.overall_risk_score:.2f}/1.00")
    print(f"   Timing Risks Detected: {len([r for r in report.risks if 'Timing' in r.risk_type])}")
    
    for risk in report.risks:
        if "Timing" in risk.risk_type:
            print(f"   🔴 {risk.severity.upper()}: {risk.risk_type}")
            print(f"      {risk.description}")
            for rec in risk.recommendations[:2]:
                print(f"      → {rec}")
    
    # ZK Proof Demonstration
    print_subheader("ZK Proof: Timing Independence")
    zk_system = MockZKProofSystem()
    
    proof = zk_system.generate_timing_independence_proof(
        event_1="connection_1",
        event_2="connection_2",
        time_delta=0.01
    )
    
    print(f"   Proof Type: {proof.proof_type.value}")
    print(f"   Proof Valid: {proof.is_valid}")
    print(f"\n   With ZK proofs, you could prove that events are timing-independent")
    print(f"   without revealing the actual timing values!")
    
    # Cleanup
    await host.close()
    
    print("\n✅ Scenario 1 Complete")


async def scenario_2_anonymity_set():
    """
    Scenario 2: Small Anonymity Set
    
    This scenario demonstrates how connecting to too few peers reduces
    anonymity and makes the node easier to identify.
    """
    print_header("SCENARIO 2: Small Anonymity Set")
    
    print("\n📖 Description:")
    print("   A node connects to only 2 peers, creating a very small anonymity set.")
    print("   This makes it easier to identify and correlate the node's activity.")
    
    print_subheader("Simulation")
    
    host = new_host()
    collector = MetadataCollector(host)
    
    # Only 2 peers - VERY BAD for privacy!
    print("   Connecting to only 2 peers (small anonymity set)...")
    peer1 = new_host().get_id()
    peer2 = new_host().get_id()
    
    collector.on_connection_opened(peer1, Multiaddr("/ip4/10.2.1.1/tcp/4001"), "outbound")
    await trio.sleep(0.1)
    collector.on_connection_opened(peer2, Multiaddr("/ip4/10.2.1.2/tcp/4001"), "outbound")
    
    print(f"   ✓ Connected to 2 peers only")
    
    # Analyze
    print_subheader("Analysis")
    analyzer = PrivacyAnalyzer(collector)
    report = analyzer.analyze()
    
    stats = collector.get_statistics()
    print(f"   Risk Score: {report.overall_risk_score:.2f}/1.00")
    print(f"   Anonymity Set Size: {stats['unique_peers']}")
    print(f"   Anonymity Risks Detected: {len([r for r in report.risks if 'Anonymity' in r.risk_type])}")
    
    for risk in report.risks:
        if "Anonymity" in risk.risk_type:
            print(f"   🔴 {risk.severity.upper()}: {risk.risk_type}")
            print(f"      {risk.description}")
            for rec in risk.recommendations[:2]:
                print(f"      → {rec}")
    
    # ZK Proof Demonstration
    print_subheader("ZK Proof: Anonymity Set Membership")
    zk_system = MockZKProofSystem()
    
    proof = zk_system.generate_anonymity_set_proof(
        peer_id=str(host.get_id()),
        anonymity_set_size=2  # Small set!
    )
    
    print(f"   Proof Type: {proof.proof_type.value}")
    print(f"   Anonymity Set Size: {proof.public_inputs['anonymity_set_size']}")
    print(f"   Proof Valid: {proof.is_valid}")
    print(f"\n   With ZK proofs, you could prove you're one of N peers")
    print(f"   without revealing which one!")
    print(f"   (But N=2 is still too small for good privacy!)")
    
    # Cleanup
    await host.close()
    
    print("\n✅ Scenario 2 Complete")


async def scenario_3_protocol_fingerprinting():
    """
    Scenario 3: Protocol Fingerprinting
    
    This scenario demonstrates how using unique protocol combinations
    can create a fingerprint that identifies the node.
    """
    print_header("SCENARIO 3: Protocol Fingerprinting")
    
    print("\n📖 Description:")
    print("   A node uses an unusual combination of protocols that creates")
    print("   a unique fingerprint, making the node easily identifiable.")
    
    print_subheader("Simulation")
    
    host = new_host()
    collector = MetadataCollector(host)
    
    # Connect to peers
    peers = [new_host().get_id() for _ in range(4)]
    
    print("   Making connections with unusual protocol combinations...")
    for i, peer_id in enumerate(peers):
        multiaddr = Multiaddr(f"/ip4/10.3.1.{i+1}/tcp/4001")
        collector.on_connection_opened(peer_id, multiaddr, "outbound")
        
        # Use a mix of common and uncommon protocols
        collector.on_protocol_negotiated(peer_id, "/ipfs/id/1.0.0")  # Common
        collector.on_protocol_negotiated(peer_id, "/ipfs/ping/1.0.0")  # Common
        
        if i % 2 == 0:
            # Unusual protocol - creates fingerprint!
            collector.on_protocol_negotiated(peer_id, "/custom/unusual-protocol/1.0.0")
        
        await trio.sleep(0.1)
    
    stats = collector.get_statistics()
    print(f"   ✓ Used {stats['protocols_used']} different protocols")
    
    # Analyze
    print_subheader("Analysis")
    analyzer = PrivacyAnalyzer(collector)
    report = analyzer.analyze()
    
    print(f"   Risk Score: {report.overall_risk_score:.2f}/1.00")
    print(f"   Protocol Risks Detected: {len([r for r in report.risks if 'Protocol' in r.risk_type or 'Fingerprint' in r.risk_type])}")
    
    for risk in report.risks:
        if "Protocol" in risk.risk_type or "Fingerprint" in risk.risk_type:
            print(f"   🔴 {risk.severity.upper()}: {risk.risk_type}")
            print(f"      {risk.description}")
            for rec in risk.recommendations[:2]:
                print(f"      → {rec}")
    
    print("\n   💡 Insight: Using uncommon protocols makes your node stand out!")
    
    # Cleanup
    await host.close()
    
    print("\n✅ Scenario 3 Complete")


async def scenario_4_zk_proof_showcase():
    """
    Scenario 4: Zero-Knowledge Proof Showcase
    
    This scenario demonstrates all types of ZK proofs available in the
    mock system and explains their privacy benefits.
    """
    print_header("SCENARIO 4: Zero-Knowledge Proof Showcase")
    
    print("\n📖 Description:")
    print("   Demonstrating all types of mock ZK proofs and their privacy benefits.")
    
    zk_system = MockZKProofSystem()
    host = new_host()
    
    # 1. Anonymity Set Membership Proof
    print_subheader("1. Anonymity Set Membership Proof")
    print("   Claim: 'I am one of N peers, but I won't tell you which one'")
    
    proof1 = zk_system.generate_anonymity_set_proof(
        peer_id=str(host.get_id()),
        anonymity_set_size=100
    )
    
    print(f"   ✓ Proof Type: {proof1.proof_type.value}")
    print(f"   ✓ Set Size: {proof1.public_inputs['anonymity_set_size']}")
    print(f"   ✓ Valid: {proof1.is_valid}")
    print(f"   ✓ Mock Proof Size: ~128 bytes")
    print(f"\n   Privacy Benefit: Hides your exact identity within a group")
    
    # 2. Session Unlinkability Proof
    print_subheader("2. Session Unlinkability Proof")
    print("   Claim: 'These two sessions cannot be linked to the same peer'")
    
    proof2 = zk_system.generate_unlinkability_proof(
        session_1_id="session_abc123",
        session_2_id="session_def456"
    )
    
    print(f"   ✓ Proof Type: {proof2.proof_type.value}")
    print(f"   ✓ Valid: {proof2.is_valid}")
    print(f"   ✓ Mock Proof Size: ~128 bytes")
    print(f"\n   Privacy Benefit: Prevents tracking across sessions")
    
    # 3. Range Proof
    print_subheader("3. Range Proof (Data Volume)")
    print("   Claim: 'I transferred between X and Y bytes, but not the exact amount'")
    
    proof3 = zk_system.generate_range_proof(
        value_name="data_transfer_bytes",
        min_value=1000,
        max_value=2000,
        actual_value=1500
    )
    
    print(f"   ✓ Proof Type: {proof3.proof_type.value}")
    print(f"   ✓ Range: [{proof3.public_inputs['min_value']}, {proof3.public_inputs['max_value']}]")
    print(f"   ✓ Valid: {proof3.is_valid}")
    print(f"   ✓ Mock Proof Size: ~128 bytes")
    print(f"\n   Privacy Benefit: Hides exact transfer amounts")
    
    # 4. Timing Independence Proof
    print_subheader("4. Timing Independence Proof")
    print("   Claim: 'These events are not timing-correlated'")
    
    proof4 = zk_system.generate_timing_independence_proof(
        event_1="connect",
        event_2="transfer",
        time_delta=5.0
    )
    
    print(f"   ✓ Proof Type: {proof4.proof_type.value}")
    print(f"   ✓ Valid: {proof4.is_valid}")
    print(f"   ✓ Mock Proof Size: ~128 bytes")
    print(f"\n   Privacy Benefit: Prevents timing analysis attacks")
    
    # Batch verification
    print_subheader("Batch Proof Verification")
    print("   Verifying all 4 proofs at once...")
    
    all_proofs = [proof1, proof2, proof3, proof4]
    valid_count = sum(1 for p in all_proofs if zk_system.verify_proof(p))
    
    print(f"   ✓ Valid Proofs: {valid_count}/{len(all_proofs)}")
    print(f"   ✓ Batch verification successful!")
    
    # Proof statistics
    print_subheader("Proof Statistics")
    mock_size_per_proof = 128  # Mock size for demonstration
    total_size = mock_size_per_proof * len(all_proofs)
    print(f"   Total Mock Proof Size: ~{total_size} bytes")
    print(f"   Average Mock Proof Size: ~{mock_size_per_proof} bytes")
    print(f"   Verification Time: < 1ms (mock)")
    
    print("\n   💡 Note: These are MOCK proofs for demonstration.")
    print("      Real ZK proofs would use Groth16, PLONK, or similar schemes.")
    
    # Cleanup
    await host.close()
    
    print("\n✅ Scenario 4 Complete")


async def scenario_5_comprehensive_report():
    """
    Scenario 5: Comprehensive Report Generation
    
    This scenario creates a complex network situation and generates
    a full privacy report with recommendations.
    """
    print_header("SCENARIO 5: Comprehensive Privacy Report")
    
    print("\n📖 Description:")
    print("   Creating a complex scenario with multiple privacy issues and")
    print("   generating a comprehensive report with ZK proofs.")
    
    print_subheader("Simulation")
    
    host = new_host()
    collector = MetadataCollector(host)
    
    # Simulate various privacy-problematic behaviors
    print("   Simulating node with multiple privacy issues...")
    
    # Small anonymity set
    peers = [new_host().get_id() for _ in range(3)]
    
    # Timing correlations
    for i, peer_id in enumerate(peers):
        multiaddr = Multiaddr(f"/ip4/10.5.1.{i+1}/tcp/4001")
        collector.on_connection_opened(peer_id, multiaddr, "outbound")
        
        # Various protocols
        collector.on_protocol_negotiated(peer_id, "/ipfs/id/1.0.0")
        collector.on_protocol_negotiated(peer_id, "/ipfs/bitswap/1.2.0")
        collector.on_protocol_negotiated(peer_id, "/custom/unique/1.0.0")
        
        # Multiple streams
        for _ in range(2 + i):
            collector.on_stream_opened(peer_id)
        
        await trio.sleep(0.015)  # Rapid timing
    
    print("   ✓ Simulation complete")
    
    # Analyze
    print_subheader("Analysis")
    analyzer = PrivacyAnalyzer(collector)
    report = analyzer.analyze()
    
    print(f"   Risk Score: {report.overall_risk_score:.2f}/1.00")
    print(f"   Total Risks: {len(report.risks)}")
    print(f"   Critical: {len(report.get_critical_risks())}")
    print(f"   High: {len(report.get_high_risks())}")
    
    # Generate ZK proofs
    print_subheader("Generating ZK Proofs")
    zk_system = MockZKProofSystem()
    
    zk_proofs = {
        "anonymity": [zk_system.generate_anonymity_set_proof(
            peer_id=str(host.get_id()),
            anonymity_set_size=3
        )],
        "timing": [zk_system.generate_timing_independence_proof(
            event_1="conn1",
            event_2="conn2",
            time_delta=0.015
        )]
    }
    
    print(f"   ✓ Generated {sum(len(v) for v in zk_proofs.values())} ZK proofs")
    
    # Generate comprehensive report
    print_subheader("Comprehensive Report")
    report_gen = ReportGenerator()
    
    console_report = report_gen.generate_console_report(
        report=report,
        zk_proofs=zk_proofs,
        verbose=True
    )
    
    print(console_report)
    
    # Cleanup
    await host.close()
    
    print("\n✅ Scenario 5 Complete")


async def main():
    """Run all demo scenarios."""
    print("\n" + "=" * 70)
    print("  PRIVACY ANALYSIS DEMO SCENARIOS")
    print("=" * 70)
    print("\n  This demonstration showcases:")
    print("  • Various privacy leak scenarios")
    print("  • Privacy analysis and risk detection")
    print("  • Zero-knowledge proof concepts")
    print("  • Comprehensive reporting")
    
    scenarios = [
        ("Timing Correlation Attack", scenario_1_timing_correlation),
        ("Small Anonymity Set", scenario_2_anonymity_set),
        ("Protocol Fingerprinting", scenario_3_protocol_fingerprinting),
        ("Zero-Knowledge Proof Showcase", scenario_4_zk_proof_showcase),
        ("Comprehensive Privacy Report", scenario_5_comprehensive_report),
    ]
    
    for i, (name, scenario_func) in enumerate(scenarios, 1):
        print(f"\n\n{'=' * 70}")
        print(f"  Running Scenario {i}/{len(scenarios)}")
        print(f"{'=' * 70}")
        
        await scenario_func()
        
        if i < len(scenarios):
            print("\n  Press Ctrl+C to stop, or wait 2s for next scenario...")
            await trio.sleep(2)
    
    print("\n\n" + "=" * 70)
    print("  ALL SCENARIOS COMPLETE!")
    print("=" * 70)
    print("\n  Key Takeaways:")
    print("  1. Timing correlations leak identity information")
    print("  2. Small anonymity sets reduce privacy significantly")
    print("  3. Unusual protocol usage creates fingerprints")
    print("  4. ZK proofs can prove properties without revealing data")
    print("  5. Multiple small leaks can combine into major privacy risks")
    print("\n  Use these insights to build more private libp2p applications!")
    print("\n")


if __name__ == "__main__":
    trio.run(main)

