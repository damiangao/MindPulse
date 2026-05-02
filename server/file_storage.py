"""File storage utility for saving uploaded files to workspace."""
from pathlib import Path


def save_file(content: bytes, chat_id: str, filename: str, project_root: str) -> str:
    """Save file content to workspace/{chat_id}/{filename}.

    Returns the relative path: workspace/{chat_id}/{filename}
    """
    workspace_dir = Path(project_root) / "workspace" / chat_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    file_path = workspace_dir / filename
    file_path.write_bytes(content)
    return f"workspace/{chat_id}/{filename}"


def get_file_path(relative_path: str, project_root: str) -> Path:
    """Convert relative path to full file path for reading."""
    full_path = Path(project_root) / relative_path
    # Resolve to absolute path and verify it stays within project_root
    resolved = full_path.resolve()
    project_root_resolved = Path(project_root).resolve()
    if not str(resolved).startswith(str(project_root_resolved)):
        raise ValueError("Path traversal attempt detected")
    return full_path
