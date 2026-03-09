"""Data models for demo web server configuration and run state."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class DemoWebConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    assets_dir: str = "privacy_circuits/params"
    analyze_duration: int = 20
    zk_timeout: int = 120
    traffic_nodes: int = 12
    pin_mode: str = "prefer-live"
    log_level: str = "warning"

    def validate(self) -> None:
        if not self.host:
            raise ValueError("host is required")
        if self.port < 1 or self.port > 65535:
            raise ValueError("port must be in range 1..65535")
        if self.analyze_duration < 1:
            raise ValueError("analyze-duration must be >= 1")
        if self.zk_timeout < 1:
            raise ValueError("zk-timeout must be >= 1")
        if self.traffic_nodes < 8 or self.traffic_nodes > 13:
            raise ValueError("traffic-nodes must be in range 8..13")
        if self.pin_mode not in {"prefer-live", "live", "mock"}:
            raise ValueError("pin-mode must be one of: prefer-live, live, mock")

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DemoRunState:
    run_id: str
    status: str
    message: str

    def as_dict(self) -> Dict[str, str]:
        return {"run_id": self.run_id, "status": self.status, "message": self.message}


def default_runs_dir() -> Path:
    return Path("demo_reports") / "web"

