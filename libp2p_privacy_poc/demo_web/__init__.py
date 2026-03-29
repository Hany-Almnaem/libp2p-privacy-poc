"""Minimal web demo wrapper for the CLI-based privacy protocol demo."""

from .models import DemoWebConfig
from .server import run_demo_server

__all__ = ["DemoWebConfig", "run_demo_server"]

