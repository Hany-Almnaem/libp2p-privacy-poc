"""Run orchestration placeholder for web demo (implemented in later steps)."""

from __future__ import annotations

from typing import Dict, Any

from .models import DemoWebConfig


class DemoRunner:
    """Skeleton runner for the web dashboard."""

    def __init__(self, config: DemoWebConfig) -> None:
        self._config = config

    def run_full_demo(self) -> Dict[str, Any]:
        """Placeholder response for Step 1."""
        return {
            "status": "not_implemented",
            "message": "Demo runner orchestration will be added in Step 2.",
            "config": self._config.as_dict(),
        }

