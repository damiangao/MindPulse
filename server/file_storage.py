"""File storage utility for managing workspace files."""

from pathlib import Path


def save_file(content: bytes, user_id: str, filename: str, project_root: str) -> str:
    """Save file content to {project_root}/{user_id}/{filename}.

    Returns the relative path: {user_id}/{filename}
    """
    user_dir = Path(project_root) / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / filename
    file_path.write_bytes(content)
    return f"{user_id}/{filename}"


def get_file_path(relative_path: str, project_root: str) -> Path:
    """Convert relative path to full file path for reading."""
    full_path = Path(project_root) / relative_path
    # Resolve to absolute path and verify it stays within project_root
    resolved = full_path.resolve()
    project_root_resolved = Path(project_root).resolve()
    if not str(resolved).startswith(str(project_root_resolved)):
        raise ValueError("Path traversal attempt detected")
    return full_path


def list_directory(relative_path: str, project_root: str) -> list[dict]:
    """List files and directories in {project_root}/{relative_path}.

    Returns list of {name, is_dir, path} dicts.
    """
    dir_path = get_file_path(relative_path, project_root)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {relative_path}")
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {relative_path}")

    result = []
    for item in sorted(dir_path.iterdir()):
        result.append({
            "name": item.name,
            "is_dir": item.is_dir(),
            "path": str(item.relative_to(Path(project_root))),
        })
    return result


def delete_path(relative_path: str, project_root: str) -> None:
    """Delete file or directory at {project_root}/{relative_path}."""
    path = get_file_path(relative_path, project_root)
    if path.is_dir():
        import shutil
        shutil.rmtree(path)
    else:
        path.unlink()


def rename_path(old_relative_path: str, new_relative_path: str, project_root: str) -> dict:
    """Rename file or directory from old_path to new_path.

    Both paths are relative to project_root.
    """
    old_path = get_file_path(old_relative_path, project_root)
    new_path = get_file_path(new_relative_path, project_root)

    if not old_path.exists():
        raise FileNotFoundError(f"Path not found: {old_relative_path}")

    # Verify parent of new path exists
    new_path.parent.mkdir(parents=True, exist_ok=True)

    old_path.rename(new_path)
    return {"path": new_relative_path}


def create_directory(relative_path: str, project_root: str) -> dict:
    """Create directory at {project_root}/{relative_path}.

    relative_path should be the full path including dir name, e.g. "user123/mynewdir"
    """
    dir_path = get_file_path(relative_path, project_root)
    dir_path.mkdir(parents=True, exist_ok=True)
    return {"path": relative_path}