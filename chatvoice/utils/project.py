import shutil
from pathlib import Path
from dataclasses import dataclass
from pathlib import Path
from ..core.config import get_settings

ALLOWED_EXTENSIONS = {".yaml", ".yml", ".html", ".md", ".txt"}

settings = get_settings()

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


def project_directory_exists(
    username: str,
    project_name: str,
    base_path: str | Path = "conversations",
) -> bool:
    """
    Check whether the project directory for a given username/project_name exists.

    Args:
        username: Owner's username.
        project_name: Project's normalized name.
        base_path: Root directory under which user/project folders live.

    Returns:
        True if the directory exists (and is a directory), False otherwise.
    """
    project_dir = Path(base_path) / username / project_name
    return project_dir.is_dir()


def list_project_files(
    username: str,
    project_name: str,
    base_path: str | Path = "conversations",
    allowed_extensions: set[str] | None = None,
) -> list[str]:
    """
    Return a list of file paths inside the project directory, relative to the
    project directory itself (i.e. without the base_path/username/project_name
    prefix), including files nested in subdirectories.

    Args:
        username: Owner's username.
        project_name: Project's normalized name.
        base_path: Root directory under which user/project folders live.
        allowed_extensions: If provided, only files with these extensions are
            returned (e.g. {".py", ".md", ".txt"}). Matching is case-insensitive.
            If None, all files are returned.

    Returns:
        List of relative file paths as strings (e.g. "src/main.py").

    Raises:
        FileNotFoundError: If the project directory doesn't exist.
    """
    project_dir = Path(base_path) / username / project_name

    if not project_dir.is_dir():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")

    if allowed_extensions is not None:
        allowed_extensions = {
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in allowed_extensions
        }

    files = []

    for f in project_dir.rglob("*"):
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
            # Get the path relative to the project root (e.g., "templates/base.html")
            rel_path = f.relative_to(project_dir)

            # Extract just the directory part (e.g., "templates" or ".")
            dir_name = str(rel_path.parent)
            if dir_name == ".":
                dir_name = "./"  # Makes the root directory look clean

            files.append(
                {
                    "name": f.name,
                    "size": f.stat().st_size,
                    "dir": dir_name,
                    "rel_path": str(rel_path),  # Crucial: used for the <a> href
                }
            )

    return files


