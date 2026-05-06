from __future__ import annotations

from pathlib import Path


def _workspace_root() -> Path:
    return Path.cwd().resolve()


def _resolve_workspace_path(path: str) -> Path:
    root = _workspace_root()
    target = (root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()

    if target != root and root not in target.parents:
        raise ValueError(f"path is outside workspace: {path}")

    return target


def read_file(path: str, start_line: int = 1, max_lines: int = 200) -> dict:
    """Read a UTF-8 text file from the current workspace."""
    if start_line < 1:
        raise ValueError("start_line must be >= 1")
    if max_lines < 1:
        raise ValueError("max_lines must be >= 1")

    target = _resolve_workspace_path(path)
    if not target.exists():
        raise FileNotFoundError(f"file does not exist: {path}")
    if not target.is_file():
        raise ValueError(f"path is not a file: {path}")

    lines = target.read_text(encoding="utf-8").splitlines()
    start_index = start_line - 1
    selected = lines[start_index : start_index + max_lines]

    return {
        "ok": True,
        "tool": "read_file",
        "path": str(target),
        "start_line": start_line,
        "line_count": len(selected),
        "total_lines": len(lines),
        "content": "\n".join(selected),
    }
