"""Local pin-service mock placeholder (implemented in later steps)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PinMockServer:
    host: str = "127.0.0.1"
    port: int = 8787

    def start(self) -> None:
        """No-op placeholder for Step 1."""
        return None

    def stop(self) -> None:
        """No-op placeholder for Step 1."""
        return None

