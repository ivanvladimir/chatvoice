import tomllib

from functools import lru_cache
from fastapi import HTTPException
from fastapi.templating import Jinja2Templates
from ..config import get_settings
from pathlib import Path
from dataclasses import dataclass

settings = get_settings()

@dataclass(frozen=True)
class RuntimeContext:
    root: Path
    content_dir: Path
    templates_front: Jinja2Templates
    templates_api: Jinja2Templates

default_runtime_context = RuntimeContext(
            root = settings.resolved_conversation_dir(),
            content_dir = settings.CONTENT_DIR_PATH,
            templates_front = Jinja2Templates(settings.TEMPLATES_FRONT_PATH),
            templates_api = Jinja2Templates(settings.TEMPLATES_API_PATH)
        )


@lru_cache(maxsize=None)
def _build_jinja(username: Path, project_name: str) -> RuntimeContext:
    if not username or not project_name:
        return default_runtime_context
    directory = Path(settings.resolved_conversation_dir()) / username / projectname
    config_path = directory / "config.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:  # must open in binary mode
            data = tomllib.load(f)
        return RuntimeContext(
            root = directory,
            content_dir = directory / data['content'],
            templates_front = Jinja2Templates(directory / data['templates_front']),
            templates_api = Jinja2Templates(directory / data['templates_api'])
        )
    else:
        return default_runtime_context
     
def get_project_context(username: str = None, project_name: str = None) -> RuntimeContext:
    return _build_jinja(username, project_name)
