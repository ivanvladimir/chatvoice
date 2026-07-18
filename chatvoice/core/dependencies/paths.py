import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError
from fastapi import Depends
from fastapi.templating import Jinja2Templates


class PathsConfig(BaseModel):
    templates: Path
    content: Path
    static: Path

class AppSettings(BaseModel):
    paths: PathsConfig

def get_runtime_settings() -> AppSettings:
    """Fetches the env var, parses JSON, and validates it into an AppSettings object."""
    config_str = os.getenv("CHATVOICE_RUNTIME_CONFIG")
    if not config_str:
        raise RuntimeError("CHATVOICE_RUNTIME_CONFIG environment variable is not set.")
    
    try:
        raw_data = json.loads(config_str)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in CHATVOICE_RUNTIME_CONFIG: {e}")

    try:
        # Pydantic automatically converts the strings into pathlib.Path objects
        settings = AppSettings(**raw_data)
    except ValidationError as e:
        raise RuntimeError(f"Invalid configuration structure: {e}")

    # Resolve to absolute paths immediately
    settings.paths.templates = settings.paths.templates.resolve()
    settings.paths.content = settings.paths.content.resolve()
    settings.paths.static = settings.paths.static.resolve()
    
    return settings


class RuntimeContext(BaseModel):
    """The Aggregate Dependency: Groups everything the routes need."""
    content_path: Path
    templates_engine: Any  # Jinja2Templates doesn't have a strict type, so we use Any

def get_runtime_context(settings: AppSettings = Depends(get_runtime_settings)) -> RuntimeContext:
    """Initializes the template engine and packages it with the content path."""
    return RuntimeContext(
        content_path=settings.paths.content,
        templates_engine=Jinja2Templates(directory=str(settings.paths.templates))
    )

