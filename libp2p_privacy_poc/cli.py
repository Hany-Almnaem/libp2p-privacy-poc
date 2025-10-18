"""
Command-Line Interface for libp2p Privacy Analysis Tool

Provides easy-to-use commands for privacy analysis, reporting, and demonstrations.
"""

import click
import json
import sys
import time
from pathlib import Path
from typing import Optional

from libp2p import new_host
from multiaddr import Multiaddr

from libp2p_privacy_poc import print_disclaimer
from libp2p_privacy_poc.metadata_collector import MetadataCollector
from libp2p_privacy_poc.privacy_analyzer import PrivacyAnalyzer
from libp2p_privacy_poc.mock_zk_proofs import MockZKProofSystem
from libp2p_privacy_poc.report_generator import ReportGenerator
from libp2p_privacy_poc.zk_integration import ZKDataPreparator


@click.group()
@click.version_option(version="0.1.0")
def main():
    """
    libp2p Privacy Analysis Tool - Proof of Concept
    
    A privacy analysis tool for py-libp2p that detects privacy leaks and
    demonstrates zero-knowledge proof concepts.
    
    ⚠️  PROOF OF CONCEPT - NOT PRODUCTION READY
    """
    pass


@main.command()
@click.option(
    '--format',
    type=click.Choice(['console', 'json', 'html'], case_sensitive=False),
    default='console',
    help='Output format for the report'
)
@click.option(
    '--output',
    type=click.Path(),
    help='Output file path (default: stdout for console, privacy_report.{format} for others)'
)
@click.option(
    '--with-zk-proofs',
    is_flag=True,
    help='Include mock ZK proofs in the report'
)
@click.option(
    '--simulate',
    is_flag=True,
    default=True,
    help='Use simulated data for demonstration (default: True)'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Enable verbose output'
)
def analyze(format, output, with_zk_proofs, simulate, verbose):
    """
    Run privacy analysis on libp2p node.
    
    By default, uses simulated data for demonstration purposes.
    In production, this would connect to real py-libp2p nodes.
    
    Examples:
    
        # Basic console analysis
        libp2p-privacy analyze
        
        # Generate JSON report
        libp2p-privacy analyze --format json --output report.json
        
        # Generate HTML report with ZK proofs
        libp2p-privacy analyze --format html --with-zk-proofs --output report.html
    """
    try:
        click.echo("\n" + "=" * 70)
        click.echo(click.style("libp2p Privacy Analysis Tool", fg="cyan", bold=True))
        click.echo("=" * 70)
        
        if simulate:
            click.echo(click.style("\n⚠️  Using simulated data for demonstration", fg="yellow"))
            click.echo("In production, this would connect to real py-libp2p nodes\n")
        
        # Create collector with simulated data
        if verbose:
            click.echo("Creating MetadataCollector...")
        collector = MetadataCollector(libp2p_host=None)
        
        # Simulate network activity
        if verbose:
            click.echo("Simulating network activity...")
        _simulate_network_activity(collector, verbose)
        
        # Run analysis
        if verbose:
            click.echo("\nRunning privacy analysis...")
        analyzer = PrivacyAnalyzer(collector)
        report = analyzer.analyze()
        
        click.echo(f"\n{click.style('✓ Analysis Complete!', fg='green')}")
        click.echo(f"  Risk Score: {report.overall_risk_score:.2f}/1.00")
        click.echo(f"  Risks Detected: {len(report.risks)}")
        
        # Generate ZK proofs if requested
        zk_proofs = None
        if with_zk_proofs:
            if verbose:
                click.echo("\nGenerating mock ZK proofs...")
            zk_proofs = _generate_zk_proofs(collector, verbose)
            click.echo(click.style(f"✓ Generated {sum(len(v) for v in zk_proofs.values())} ZK proofs", fg="green"))
        
        # Generate report
        if verbose:
            click.echo(f"\nGenerating {format} report...")
        
        report_gen = ReportGenerator()
        
        if format == 'console':
            report_content = report_gen.generate_console_report(report, zk_proofs, verbose=verbose)
            if output:
                Path(output).write_text(report_content)
                click.echo(f"\n{click.style(f'✓ Report saved to: {output}', fg='green')}")
            else:
                click.echo("\n" + report_content)
        
        elif format == 'json':
            report_content = report_gen.generate_json_report(report, zk_proofs)
            output_path = output or "privacy_report.json"
            Path(output_path).write_text(report_content)
            click.echo(f"\n{click.style(f'✓ JSON report saved to: {output_path}', fg='green')}")
            
        elif format == 'html':
            report_content = report_gen.generate_html_report(report, zk_proofs)
            output_path = output or "privacy_report.html"
            Path(output_path).write_text(report_content)
            click.echo(f"\n{click.style(f'✓ HTML report saved to: {output_path}', fg='green')}")
        
        click.echo("\n" + "=" * 70)
        
    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg="red"), err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option(
    '--scenario',
    type=click.Choice(['all', 'timing', 'linkability', 'anonymity'], case_sensitive=False),
    default='all',
    help='Which demonstration scenario to run'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Enable verbose output'
)
def demo(scenario, verbose):
    """
    Run demonstration scenarios showing privacy analysis capabilities.
    
    Demonstrates various privacy leak detection techniques and ZK proof concepts.
    
    Examples:
    
        # Run all demonstrations
        libp2p-privacy demo
        
        # Run timing correlation demo
        libp2p-privacy demo --scenario timing
    """
    try:
        click.echo("\n" + "=" * 70)
        click.echo(click.style("Privacy Analysis Demonstrations", fg="cyan", bold=True))
        click.echo("=" * 70)
        
        if scenario in ['all', 'timing']:
            _demo_timing_correlation(verbose)
        
        if scenario in ['all', 'linkability']:
            _demo_peer_linkability(verbose)
        
        if scenario in ['all', 'anonymity']:
            _demo_anonymity_set(verbose)
        
        click.echo("\n" + "=" * 70)
        click.echo(click.style("✓ Demonstrations Complete!", fg="green"))
        click.echo("=" * 70 + "\n")
        
    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg="red"), err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
def version():
    """Show version and disclaimer information."""
    click.echo("\nlibp2p Privacy Analysis Tool v0.1.0")
    click.echo("Proof of Concept - Not Production Ready\n")
    print_disclaimer()


def _simulate_network_activity(collector: MetadataCollector, verbose: bool = False):
    """Simulate network activity for demonstration."""
    peers = [
        ("QmPeer1abc123def456", "/ip4/192.168.1.100/tcp/4001"),
        ("QmPeer2xyz789ghi012", "/ip4/192.168.1.101/tcp/4001"),
        ("QmPeer3jkl345mno678", "/ip4/192.168.1.102/tcp/4001"),
        ("QmPeer1abc123def456", "/ip4/192.168.1.100/tcp/4002"),
        ("QmPeer4pqr901stu234", "/ip4/192.168.1.103/tcp/4001"),
    ]
    
    for i, (peer_id_str, addr_str) in enumerate(peers):
        collector.on_connection_opened(
            peer_id=peer_id_str,
            multiaddr=Multiaddr(addr_str),
            direction="outbound" if i % 2 == 0 else "inbound"
        )
        time.sleep(0.05)
    
    # Simulate protocol negotiations
    collector.on_protocol_negotiated("QmPeer1abc123def456", "/ipfs/id/1.0.0")
    collector.on_protocol_negotiated("QmPeer1abc123def456", "/ipfs/bitswap/1.2.0")
    
    # Simulate stream activity
    collector.on_stream_opened("QmPeer1abc123def456")
    collector.on_stream_opened("QmPeer2xyz789ghi012")


def _generate_zk_proofs(collector: MetadataCollector, verbose: bool = False):
    """Generate mock ZK proofs for demonstration."""
    zk_system = MockZKProofSystem()
    zk_proofs = {}
    
    peer_ids = list(collector.peers.keys())
    if peer_ids:
        # Anonymity set proof
        anonymity_proof = zk_system.generate_anonymity_set_proof(
            peer_id=peer_ids[0],
            anonymity_set_size=len(peer_ids)
        )
        zk_proofs["anonymity_set"] = [anonymity_proof]
        
        # Unlinkability proof (if multiple peers)
        if len(peer_ids) >= 2:
            unlinkability_proof = zk_system.generate_unlinkability_proof(
                session_1_id=peer_ids[0],
                session_2_id=peer_ids[1]
            )
            zk_proofs["unlinkability"] = [unlinkability_proof]
    
    return zk_proofs


def _demo_timing_correlation(verbose: bool):
    """Demonstrate timing correlation detection."""
    click.echo("\n" + "-" * 70)
    click.echo(click.style("Demo: Timing Correlation Detection", fg="cyan", bold=True))
    click.echo("-" * 70)
    click.echo("\nThis demo shows how timing patterns can leak privacy information.")
    
    collector = MetadataCollector()
    
    # Create regular timing pattern
    for i in range(5):
        collector.on_connection_opened(
            peer_id=f"QmPeer{i}",
            multiaddr=Multiaddr("/ip4/127.0.0.1/tcp/4001"),
            direction="outbound"
        )
        time.sleep(0.1)  # Regular interval
    
    analyzer = PrivacyAnalyzer(collector)
    report = analyzer.analyze()
    
    timing_risks = [r for r in report.risks if r.risk_type == "Timing Correlation"]
    click.echo(f"\n{click.style(f'✓ Detected {len(timing_risks)} timing-related risks', fg='yellow')}")
    
    for risk in timing_risks:
        click.echo(f"  • {risk.description}")


def _demo_peer_linkability(verbose: bool):
    """Demonstrate peer linkability detection."""
    click.echo("\n" + "-" * 70)
    click.echo(click.style("Demo: Peer Linkability Detection", fg="cyan", bold=True))
    click.echo("-" * 70)
    click.echo("\nThis demo shows how multiple connections can be linked to the same peer.")
    
    collector = MetadataCollector()
    
    # Same peer, multiple addresses
    peer_id = "QmTestPeer123"
    for i in range(3):
        collector.on_connection_opened(
            peer_id=peer_id,
            multiaddr=Multiaddr(f"/ip4/192.168.1.100/tcp/{4001+i}"),
            direction="outbound"
        )
    
    analyzer = PrivacyAnalyzer(collector)
    report = analyzer.analyze()
    
    click.echo(f"\n{click.style('✓ Analysis complete', fg='yellow')}")
    click.echo(f"  • Detected connections from same peer across {len(collector.peers[peer_id].multiaddrs)} addresses")


def _demo_anonymity_set(verbose: bool):
    """Demonstrate anonymity set analysis."""
    click.echo("\n" + "-" * 70)
    click.echo(click.style("Demo: Anonymity Set Analysis with ZK Proofs", fg="cyan", bold=True))
    click.echo("-" * 70)
    click.echo("\nThis demo shows anonymity set analysis and ZK proof generation.")
    
    collector = MetadataCollector()
    
    # Simulate connections to various peers
    for i in range(10):
        collector.on_connection_opened(
            peer_id=f"QmPeer{i}",
            multiaddr=Multiaddr(f"/ip4/192.168.1.{100+i}/tcp/4001"),
            direction="outbound"
        )
    
    analyzer = PrivacyAnalyzer(collector)
    report = analyzer.analyze()
    
    # Generate ZK proof
    zk_system = MockZKProofSystem()
    peer_ids = list(collector.peers.keys())
    proof = zk_system.generate_anonymity_set_proof(
        peer_id=peer_ids[0],
        anonymity_set_size=len(peer_ids)
    )
    
    click.echo(f"\n{click.style('✓ Anonymity analysis complete', fg='yellow')}")
    click.echo(f"  • Anonymity set size: {len(peer_ids)}")
    click.echo(f"  • Generated ZK proof: {proof.proof_type}")
    click.echo(f"  • Proof verified: {click.style('✓', fg='green') if zk_system.verify_proof(proof) else click.style('✗', fg='red')}")


if __name__ == "__main__":
    main()

