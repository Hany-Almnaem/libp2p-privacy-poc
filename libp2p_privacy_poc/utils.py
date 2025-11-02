"""
Utility functions for the privacy analysis tool.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from multiaddr import Multiaddr


def get_peer_listening_address(host) -> Multiaddr:
    """
    Get the full listening address of a host including peer ID.
    
    This is a common pattern when connecting to py-libp2p hosts.
    
    Args:
        host: libp2p Host object with active network
        
    Returns:
        Multiaddr: Full address with /p2p/<peer-id> suffix
        
    Raises:
        ValueError: If host has no active listeners
        
    Example:
        >>> full_addr = get_peer_listening_address(host2)
        >>> await host1.connect(info_from_p2p_addr(full_addr))
    """
    network = host.get_network()
    if not network.listeners:
        raise ValueError(f"Host {host.get_id()} has no active listeners")
    
    listener_key = list(network.listeners.keys())[0]
    listener = network.listeners[listener_key]
    actual_addr = listener.get_addrs()[0]
    return actual_addr.encapsulate(Multiaddr(f"/p2p/{host.get_id()}"))



def format_timestamp(timestamp: float) -> str:
    """Format a Unix timestamp as human-readable string."""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def format_duration(seconds: float) -> str:
    """Format duration in seconds as human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_bytes(bytes_count: int) -> str:
    """Format byte count as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f}{unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f}PB"


def truncate_peer_id(peer_id: str, length: int = 16) -> str:
    """Truncate a peer ID for display."""
    if len(peer_id) <= length:
        return peer_id
    return f"{peer_id[:length]}..."


def calculate_entropy(values: List[Any]) -> float:
    """
    Calculate Shannon entropy of a list of values.
    
    Higher entropy = more randomness/unpredictability
    Lower entropy = more patterns/predictability
    """
    if not values:
        return 0.0
    
    from collections import Counter
    import math
    
    counts = Counter(values)
    total = len(values)
    
    entropy = 0.0
    for count in counts.values():
        probability = count / total
        if probability > 0:
            entropy -= probability * math.log2(probability)
    
    return entropy


def save_json(data: dict, filepath: str, pretty: bool = True):
    """Save data as JSON file."""
    with open(filepath, 'w') as f:
        if pretty:
            json.dump(data, f, indent=2)
        else:
            json.dump(data, f)


def load_json(filepath: str) -> dict:
    """Load data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def generate_report_id() -> str:
    """Generate a unique report ID."""
    import hashlib
    timestamp = str(time.time())
    return hashlib.sha256(timestamp.encode()).hexdigest()[:16]


def color_text(text: str, color: str) -> str:
    """
    Add ANSI color codes to text for terminal display.
    
    Args:
        text: The text to color
        color: Color name (red, green, yellow, blue, etc.)
    
    Returns:
        Colored text string
    """
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'reset': '\033[0m',
    }
    
    color_code = colors.get(color.lower(), colors['reset'])
    reset_code = colors['reset']
    
    return f"{color_code}{text}{reset_code}"


def format_risk_severity(severity: str) -> str:
    """Format risk severity with color."""
    severity_colors = {
        'critical': 'red',
        'high': 'red',
        'medium': 'yellow',
        'low': 'green',
    }
    
    color = severity_colors.get(severity.lower(), 'white')
    return color_text(severity.upper(), color)


def create_progress_bar(current: int, total: int, width: int = 50) -> str:
    """Create a text-based progress bar."""
    if total == 0:
        return "[" + "=" * width + "]"
    
    filled = int(width * current / total)
    bar = "=" * filled + "-" * (width - filled)
    percentage = 100 * current / total
    
    return f"[{bar}] {percentage:.1f}%"

