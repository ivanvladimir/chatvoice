from __future__ import annotations

import cyclopts
import json
import os
from functools import wraps
from pathlib import Path
from typing import Annotated, Literal

from rich import print

from .core.config import get_settings
from .core.interpreter import Interpreter
from .core.logger import get_logger, setup_logging
from .utils.llm import init_llm_client


# Default configuration values
CHATVOICE_CONFIG_PATH = Path("config.toml")
CHATVOICE_LOG_FILE = "logs/chatvoice.log"
CHATVOICE_LOG_LEVEL = "error"
CHATVOICE_NAME = "chatvoice"
CHATVOICE_HOST = "0.0.0.0"
CHATVOICE_PORT = 9000
CHATVOICE_RELOAD = True
CHATVOICE_WORKERS = 1
CHATVOICE_LOG_JSON = False
CHATVOICE_TEMPLATES_PATH = "chatvoice/front/templates"
CHATVOICE_CONTENT_PATH = "chatvoice/content"
CHATVOICE_STATIC_PATH = "chatvoice/static"
CHATVOICE_ROOT_KEYS = ["chatvoice"]

LogLevel = Literal["critical", "error", "warning", "info", "debug", "trace"]

def with_logging(func):
    """Decorator to setup logging before command execution.
    
    Extracts logging-related keyword arguments, configures logging,
    and calls the wrapped function without those parameters.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        setup_logging(
            json_output=kwargs.pop("logging_json", False),
            log_file=kwargs.pop("logging_file", CHATVOICE_LOG_FILE),
            log_level=kwargs.pop("logging_level", CHATVOICE_LOG_LEVEL),
        )
        return func(*args, **kwargs)
    return wrapper



cli = cyclopts.App(
    name="chatvoice",
    help="CLI for running the chat in different modes.",
)


@cli.command
@with_logging
def console(
    project_pathname: Annotated[Path, cyclopts.Parameter(validator=cyclopts.validators.Path(exists=True))],
    *,
    name: str = CHATVOICE_NAME,
    logging_json: bool = False,
    logging_level: LogLevel = CHATVOICE_LOG_LEVEL,
    logging_file: str = CHATVOICE_LOG_FILE,
) -> None:
    """Run the chat from the console.
    
    Parameters
    ----------
    project_pathname : Path
        Directory containing the conversation to have with the chat.
    name : str
        Name identifier for the chat system.
    """
    from .transport.console import Console

    settings = get_settings()  # Moved inside to load after config is processed

    print("Initializing LLM client.")
    llm_client = init_llm_client(settings)
    print(f"Running [yellow]{project_pathname}[/] conversation from the console as [green]{name}[/].")

    console = Console()
    user = console.authenticate_user()
    
    if not user:
        print("[red]Authentication failed. Please check your credentials and try again.[/]")
        return

    interpreter = Interpreter(
        project_pathname,
        user_id=user.id,
        settings={"_name_system": name},
        llm_client=llm_client,
    )
    console.run(user.id, interpreter)


@cli.command
@with_logging
def server(
    host: str = CHATVOICE_HOST,
    port: int = CHATVOICE_PORT,
    content_path: Path = CHATVOICE_CONTENT_PATH,
    templates_path: Path = CHATVOICE_TEMPLATES_PATH,
    static_path: Path = CHATVOICE_STATIC_PATH,
    reload: bool = CHATVOICE_RELOAD,
    workers: int = CHATVOICE_WORKERS,
    logging_json: bool = CHATVOICE_LOG_JSON,
    logging_level: LogLevel = CHATVOICE_LOG_LEVEL,
    logging_file: str = CHATVOICE_LOG_FILE,
) -> None:
    """Run the server chat."""
    log = get_logger(__name__)

    os.environ["CHATVOICE_RUNTIME_CONFIG"] = json.dumps({
        "paths":{
            "content": str(content_path),
            "templates": str(templates_path),
            "static": str(static_path)
        }
    })

    import uvicorn
    
    log.info("Starting server chat")
    print("Running the [yellow]server chat[/].")
    uvicorn.run("chatvoice.asgi:create_app",
                host=host,
                port=port,
                reload=reload,
                workers=workers,
#                log_level=logging_level,
                factory=True)
    log.info("Ending server chat")


@cli.command
@with_logging
def create_user(
    logging_json: bool = False,
    logging_level: str = "debug",  # More verbose for admin operations
    logging_file: str = CHATVOICE_LOG_FILE,
) -> None:
    """Create user."""
    log = get_logger(__name__)
    from .utils.user import create_user

    print("About to create [yellow]admin user[/].")
    username,role = create_user()
    if role:
        log.info(f"User '{username}' created successfully with role '{role}'.")
        print(f"[green]User '{username}' created successfully with role '{role}'.[/]")
    else:
        log.info(f"User '{username}' was not created.")
        print(f"[red]User '{username}' was not created.[/]")


@cli.command
@with_logging
def create_admin(
    logging_json: bool = False,
    logging_level: str = "debug",  # More verbose for admin operations
    logging_file: str = CHATVOICE_LOG_FILE,
) -> None:
    """Create an admin user."""
    log = get_logger(__name__)
    from .utils.user import create_admin_user

    print("About to create [yellow]admin user[/].")
    username, status = create_admin_user()
    if status:
        log.info(f"Admin '{username}' created successfully.")
        print(f"[green]Admin '{username}' created successfully.[/]")
    else:
        log.info(f"Admin '{username}' was not created.")
        print(f"[red]Admin '{username}' was not created.[/]")



@cli.command
@with_logging
def create_tier(
    logging_json: bool = False,
    logging_level: str = "debug",  # More verbose for admin operations
    logging_file: str = CHATVOICE_LOG_FILE,
) -> None:
    """Create a tier."""
    from utils.admin import create_tier

    print("About to create a [yellow]tier[/].")
    create_tier()

@cli.meta.default
def meta(
    *tokens: Annotated[str, cyclopts.Parameter(show=False, allow_leading_hyphen=True)],
    config: Path = CHATVOICE_CONFIG_PATH,
    root_keys: Annotated[
        list[str] | None,
        cyclopts.Parameter(converter=lambda type_, tokens: [
            k for t in tokens for k in t.value.split(".")
        ])
    ] = None,
) -> None:
    """Load configuration and run the app."""
    if root_keys is None:
        command_name = tokens[0] if tokens else None
        root_keys = ["chatvoice", command_name] if command_name else ["chatvoice"]

    # Build cascade: most specific -> least specific, always ending at ["chatvoice"]
    levels = [root_keys[:i] for i in range(len(root_keys), 0, -1)]

    toml_sources = [
        cyclopts.config.Toml(
            config,
            root_keys=level,
            search_parents=True,
            use_commands_as_keys=False,
            allow_unknown=True,
        )
        for level in levels
    ]

    cli.config = [
        cyclopts.config.Env("CHATVOICE_"),
        *toml_sources,
    ]
    cli(tokens)

if __name__ == "__main__":
    cli.meta()
