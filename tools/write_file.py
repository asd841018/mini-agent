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


def write_file(
    path: str,
    content: str,
    append: bool = False,
    create_dirs: bool = True,
) -> dict:
    """Write UTF-8 text to a file in the current workspace."""
    target = _resolve_workspace_path(path)

    if target.exists() and target.is_dir():
        raise ValueError(f"path is a directory: {path}")

    if create_dirs:
        target.parent.mkdir(parents=True, exist_ok=True)
    elif not target.parent.exists():
        raise FileNotFoundError(f"parent directory does not exist: {target.parent}")

    mode = "a" if append else "w"
    with target.open(mode, encoding="utf-8") as file:
        file.write(content)

    return {
        "ok": True,
        "tool": "write_file",
        "path": str(target),
        "bytes_written": len(content.encode("utf-8")),
        "append": append,
    }
