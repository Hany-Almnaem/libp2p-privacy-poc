"""Run orchestration for web demo (Step 2 core flow)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .models import DemoWebConfig, default_runs_dir

SERVER_LISTEN_ADDR = "/ip4/127.0.0.1/tcp/50140"
ANALYZE_LISTEN_ADDR = "/ip4/127.0.0.1/tcp/50158"
FALLBACK_TEXT = "falling back to legacy simulation"

_SERVER_MULTIADDR_RE = re.compile(r"^Listening:\s+(\S+/p2p/\S+)\s*$", re.MULTILINE)
_ANALYZE_MULTIADDR_RE = re.compile(r"Listening on:\s+(\S+/p2p/\S+)")


@dataclass(frozen=True)
class RunArtifacts:
    run_dir: Path
    server_log: Path
    analyze_log: Path
    dial_log: Path
    report_json: Path
    summary_json: Path


def extract_server_multiaddr(log_text: str) -> Optional[str]:
    match = _SERVER_MULTIADDR_RE.search(log_text or "")
    if not match:
        return None
    return match.group(1)


def extract_analyzer_multiaddr(log_text: str) -> Optional[str]:
    match = _ANALYZE_MULTIADDR_RE.search(log_text or "")
    if not match:
        return None
    return match.group(1)


def classify_run_status(core_error: bool, fallback_detected: bool) -> Tuple[str, str]:
    if core_error:
        return "failed", "Demo orchestration failed."
    if fallback_detected:
        return "fallback", "Fallback detected during analysis."
    return "success", "Demo orchestration completed successfully."


class DemoRunner:
    """Run end-to-end orchestration for the dashboard backend."""

    def __init__(
        self,
        config: DemoWebConfig,
        *,
        root_dir: Optional[Path] = None,
        python_executable: Optional[str] = None,
    ) -> None:
        self._config = config
        self._config.validate()
        self._root_dir = root_dir or Path(__file__).resolve().parents[2]
        self._runs_dir = self._root_dir / default_runs_dir()
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        self._python = python_executable or self._infer_python_executable()

    def run_full_demo(self) -> Dict[str, Any]:
        run_id = self._make_run_id()
        artifacts = self._create_run_artifacts(run_id)
        sequence: list[str] = []
        started_at = _utc_now()

        server_proc: Optional[subprocess.Popen] = None
        analyze_proc: Optional[subprocess.Popen] = None
        dial_proc: Optional[subprocess.Popen] = None

        server_multiaddr: Optional[str] = None
        analyzer_multiaddr: Optional[str] = None
        analyze_exit_code: Optional[int] = None
        dial_exit_code: Optional[int] = None
        fallback_detected = False
        error: Optional[str] = None

        try:
            sequence.append("zk-serve")
            server_proc = self._start_process(
                self._build_zk_serve_cmd(),
                artifacts.server_log,
            )
            server_multiaddr = self._wait_for_server_multiaddr(
                artifacts.server_log,
                timeout_seconds=25.0,
                process=server_proc,
            )
            if not server_multiaddr:
                raise RuntimeError("failed to parse server multiaddr from zk-serve output")

            sequence.append("analyze")
            analyze_proc = self._start_process(
                self._build_analyze_cmd(server_multiaddr, artifacts.report_json),
                artifacts.analyze_log,
            )
            analyzer_multiaddr = self._wait_for_analyzer_multiaddr(
                artifacts.analyze_log,
                timeout_seconds=25.0,
                process=analyze_proc,
            )
            if not analyzer_multiaddr:
                raise RuntimeError(
                    "failed to parse analyzer multiaddr from analyze output"
                )

            sequence.append("zk-dial")
            dial_proc = self._start_process(
                self._build_zk_dial_cmd(analyzer_multiaddr),
                artifacts.dial_log,
            )

            analyze_exit_code = analyze_proc.wait(
                timeout=max(self._config.analyze_duration + self._config.zk_timeout + 30, 30)
            )
            dial_exit_code = dial_proc.wait(
                timeout=max(self._config.analyze_duration + 30, 30)
            )
            fallback_detected = self._file_contains(
                artifacts.analyze_log, FALLBACK_TEXT
            )
        except Exception as exc:  # pragma: no cover - defensive path
            error = str(exc)
        finally:
            self._terminate_process(dial_proc)
            self._terminate_process(analyze_proc)
            self._terminate_process(server_proc)

        core_error = bool(error)
        if analyze_exit_code not in (None, 0):
            core_error = True
            error = error or f"analyze exited with code {analyze_exit_code}"
        if dial_exit_code not in (None, 0):
            core_error = True
            error = error or f"zk-dial exited with code {dial_exit_code}"
        if not artifacts.report_json.exists():
            core_error = True
            error = error or "analyze report.json missing"

        status, message = classify_run_status(core_error, fallback_detected)
        if error:
            message = error

        summary: Dict[str, Any] = {
            "run_id": run_id,
            "status": status,
            "message": message,
            "config": self._config.as_dict(),
            "sequence": sequence,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "server_multiaddr": server_multiaddr,
            "analyzer_multiaddr": analyzer_multiaddr,
            "fallback_detected": fallback_detected,
            "analyze_exit_code": analyze_exit_code,
            "dial_exit_code": dial_exit_code,
            "artifacts": {
                "run_dir": str(artifacts.run_dir),
                "server_log": str(artifacts.server_log),
                "analyze_log": str(artifacts.analyze_log),
                "dial_log": str(artifacts.dial_log),
                "report_json": str(artifacts.report_json),
                "summary_json": str(artifacts.summary_json),
            },
            "planned_steps": list(self.planned_step_names()),
            "commands": {
                "zk_serve": self._build_zk_serve_cmd(),
                "analyze": self._build_analyze_cmd(
                    server_multiaddr or "<missing-server-multiaddr>",
                    artifacts.report_json,
                ),
                "zk_dial": self._build_zk_dial_cmd(
                    analyzer_multiaddr or "<missing-analyzer-multiaddr>"
                ),
            },
        }
        self._write_json(artifacts.summary_json, summary)
        return summary

    @staticmethod
    def planned_step_names() -> tuple[str, str, str]:
        return ("zk-serve", "analyze", "zk-dial")

    def _build_zk_serve_cmd(self) -> list[str]:
        return [
            self._python,
            "-m",
            "libp2p_privacy_poc.cli",
            "--log-level",
            self._config.log_level,
            "zk-serve",
            "--listen-addr",
            SERVER_LISTEN_ADDR,
            "--prove-mode",
            "real",
            "--assets-dir",
            self._config.assets_dir,
        ]

    def _build_analyze_cmd(self, server_multiaddr: str, report_json: Path) -> list[str]:
        return [
            self._python,
            "-m",
            "libp2p_privacy_poc.cli",
            "--log-level",
            self._config.log_level,
            "analyze",
            "--duration",
            str(self._config.analyze_duration),
            "--listen-addr",
            ANALYZE_LISTEN_ADDR,
            "--connect-to",
            server_multiaddr,
            "--zk-peer",
            server_multiaddr,
            "--zk-statement",
            "all",
            "--zk-timeout",
            str(self._config.zk_timeout),
            "--zk-assets-dir",
            self._config.assets_dir,
            "--format",
            "json",
            "--output",
            str(report_json),
        ]

    def _build_zk_dial_cmd(self, analyzer_multiaddr: str) -> list[str]:
        return [
            self._python,
            "-m",
            "libp2p_privacy_poc.cli",
            "--log-level",
            self._config.log_level,
            "zk-dial",
            "--peer",
            analyzer_multiaddr,
            "--count",
            str(self._config.traffic_nodes),
            "--duration",
            str(max(self._config.analyze_duration + 2, 5)),
        ]

    def _create_run_artifacts(self, run_id: str) -> RunArtifacts:
        run_dir = self._runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return RunArtifacts(
            run_dir=run_dir,
            server_log=run_dir / "zk_serve.log",
            analyze_log=run_dir / "analyze.log",
            dial_log=run_dir / "zk_dial.log",
            report_json=run_dir / "report.json",
            summary_json=run_dir / "summary.json",
        )

    def _start_process(self, cmd: list[str], log_path: Path) -> subprocess.Popen:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = log_path.open("w", encoding="utf-8")
        env = self._base_env()
        return subprocess.Popen(
            cmd,
            cwd=self._root_dir,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )

    def _wait_for_server_multiaddr(
        self,
        log_path: Path,
        *,
        timeout_seconds: float,
        process: Optional[subprocess.Popen],
    ) -> Optional[str]:
        return self._wait_for_multiaddr(
            log_path,
            extractor=extract_server_multiaddr,
            timeout_seconds=timeout_seconds,
            process=process,
        )

    def _wait_for_analyzer_multiaddr(
        self,
        log_path: Path,
        *,
        timeout_seconds: float,
        process: Optional[subprocess.Popen],
    ) -> Optional[str]:
        return self._wait_for_multiaddr(
            log_path,
            extractor=extract_analyzer_multiaddr,
            timeout_seconds=timeout_seconds,
            process=process,
        )

    def _wait_for_multiaddr(
        self,
        log_path: Path,
        *,
        extractor,
        timeout_seconds: float,
        process: Optional[subprocess.Popen],
    ) -> Optional[str]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            text = self._read_text(log_path)
            addr = extractor(text)
            if addr:
                return addr
            if process is not None and process.poll() is not None:
                return None
            time.sleep(0.1)
        return None

    @staticmethod
    def _read_text(path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _file_contains(path: Path, needle: str) -> bool:
        text = DemoRunner._read_text(path)
        return needle in text

    @staticmethod
    def _terminate_process(proc: Optional[subprocess.Popen]) -> None:
        if proc is None:
            return
        if proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _make_run_id() -> str:
        now = datetime.now(timezone.utc)
        return now.strftime("%Y%m%d-%H%M%S-%f")

    def _infer_python_executable(self) -> str:
        venv_python = self._root_dir / "venv" / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)
        return sys.executable

    def _base_env(self) -> Dict[str, str]:
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        return env


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
