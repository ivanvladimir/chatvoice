from __future__ import annotations

import cyclopts
from functools import wraps
from pathlib import Path
from typing import Annotated, Literal

from rich import print

from .core.config import get_settings
from .core.interpreter import Interpreter
from .core.logger import get_logger, setup_logging
from .utils.llm import init_llm_client

# Default configuration values
DEFAULT_CONFIG_PATH = Path("config.toml")
DEFAULT_LOG_FILE = "logs/chatvoice.log"
DEFAULT_LOG_LEVEL = "error"
DEFAULT_NAME = "chatvoice"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9000
DEFAULT_RELOAD = True
DEFAULT_WORKERS = 1
DEFAULT_LOG_JSON = False
DEFAULT_ROOT_KEYS = ["default"]

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
            log_file=kwargs.pop("logging_file", DEFAULT_LOG_FILE),
            log_level=kwargs.pop("logging_level", DEFAULT_LOG_LEVEL),
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
    name: str = DEFAULT_NAME,
    logging_json: bool = False,
    logging_level: LogLevel = DEFAULT_LOG_LEVEL,
    logging_file: str = DEFAULT_LOG_FILE,
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
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    reload: bool = DEFAULT_RELOAD,
    workers: int = DEFAULT_WORKERS,
    logging_json: bool = DEFAULT_LOG_JSON,
    logging_level: LogLevel = DEFAULT_LOG_LEVEL,
    logging_file: str = DEFAULT_LOG_FILE,
) -> None:
    """Run the server chat."""
    log = get_logger(__name__)
    import uvicorn
    
    print("Running the [yellow]server chat[/].")
    log.info("Starting server chat")
    uvicorn.run("chatvoice.asgi:create_app",
                host=host,
                port=port,
                reload=reload,
                workers=workers,
                #log_level=logging_level, fix behaviour
                #log_config=None,
                factory=True)


@cli.command
@with_logging
def create_admin(
    logging_json: bool = False,
    logging_level: str = "debug",  # More verbose for admin operations
    logging_file: str = DEFAULT_LOG_FILE,
) -> None:
    """Create an admin user."""
    from .utils.admin import create_admin_user

    print("About to create [yellow]admin user[/].")
    create_admin_user()


@cli.command
@with_logging
def create_tier(
    logging_json: bool = False,
    logging_level: str = "debug",  # More verbose for admin operations
    logging_file: str = DEFAULT_LOG_FILE,
) -> None:
    """Create a tier."""
    from utils.admin import create_tier

    print("About to create a [yellow]tier[/].")
    create_tier()


@cli.meta.default
def meta(
    *tokens: Annotated[str, cyclopts.Parameter(show=False, allow_leading_hyphen=True)],
    config: Path = DEFAULT_CONFIG_PATH,
    root_keys: Annotated[
        list[str],
        cyclopts.Parameter(converter=lambda rks: rks.split("."))
    ] = DEFAULT_ROOT_KEYS,
) -> None:
    """Load configuration and run the app."""
    cli.config = [
        cyclopts.config.Env("CHATVOICE_"),
        cyclopts.config.Toml(
            config,
            root_keys=root_keys,
            search_parents=True,
        ),
    ]
    cli(tokens)


if __name__ == "__main__":
    cli.meta()
