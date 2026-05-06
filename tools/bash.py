from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


UNSAFE_COMMAND_PATTERNS = (
    r"\brm\b",
    r"\bsudo\b",
    r"\bchmod\b",
    r"\bchown\b",
    r"\bdd\b",
    r"\bmkfs\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bgit\s+reset\b",
    r"\bgit\s+clean\b",
    r">",
)


def _workspace_root() -> Path:
    return Path.cwd().resolve()


def _resolve_workspace_dir(path: str | None) -> Path:
    root = _workspace_root()
    target = root if path in (None, "") else (root / path).resolve()

    if target != root and root not in target.parents:
        raise ValueError(f"cwd is outside workspace: {path}")
    if not target.exists():
        raise FileNotFoundError(f"cwd does not exist: {path}")
    if not target.is_dir():
        raise ValueError(f"cwd is not a directory: {path}")

    return target


def _assert_safe_command(command: str) -> None:
    allow_unsafe = os.environ.get("MINI_AGENT_ALLOW_UNSAFE_BASH") == "true"
    if allow_unsafe:
        return

    for pattern in UNSAFE_COMMAND_PATTERNS:
        if re.search(pattern, command):
            raise ValueError(
                "blocked unsafe bash command. Set MINI_AGENT_ALLOW_UNSAFE_BASH=true "
                "only if you intentionally want to allow unsafe shell commands."
            )


def bash(command: str, cwd: str | None = None, timeout_seconds: int = 30) -> dict:
    """Run a bash command in the current workspace and return captured output."""
    if not command.strip():
        raise ValueError("command must not be empty")
    if timeout_seconds < 1 or timeout_seconds > 300:
        raise ValueError("timeout_seconds must be between 1 and 300")

    run_cwd = _resolve_workspace_dir(cwd)
    _assert_safe_command(command)

    completed = subprocess.run(
        command,
        cwd=run_cwd,
        executable="/bin/bash",
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )

    return {
        "ok": completed.returncode == 0,
        "tool": "bash",
        "command": command,
        "cwd": str(run_cwd),
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-12000:],
        "stderr": completed.stderr[-12000:],
    }
