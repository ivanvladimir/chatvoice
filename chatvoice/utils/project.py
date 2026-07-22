import os
import shutil
from pathlib import Path


def create_project_directory(
    username: str,
    project_name: str,
    template_dir: str | Path = "conversations/hello_name",
    base_path: str | Path = "conversations",
) -> Path:
    """
    Create a project directory at base_path/username/project_name and populate
    it with the contents of template_dir.

    Args:
        username: Owner's username (used as a subdirectory).
        project_name: Project's normalized name (used as a subdirectory).
        template_dir: Path to the template directory to copy files from.
        base_path: Root directory under which user/project folders live.

    Returns:
        Path to the newly created project directory.

    Raises:
        FileNotFoundError: If template_dir doesn't exist.
        FileExistsError: If the target project directory already exists.
    """
    template_dir = Path(template_dir)
    if not template_dir.is_dir():
        raise FileNotFoundError(f"Template directory not found: {template_dir}")

    project_dir = Path(base_path) / username / project_name

    if project_dir.exists():
        raise FileExistsError(f"Project directory already exists: {project_dir}")

    # Create parent dirs (base_path/username) if needed
    project_dir.parent.mkdir(parents=True, exist_ok=True)

    # Copy template contents into the new project directory
    shutil.copytree(template_dir, project_dir)

    return project_dir
