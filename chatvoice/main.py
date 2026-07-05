import cyclopts
from typing import Annotated
from pathlib import Path
from rich import print

from core.config import get_settings
from core.logger import setup_logging, get_logger
from core.interpreter import Interpreter

from utils.llm import get_llm_client, init_llm_client

settings = get_settings()

cli = cyclopts.App(
    name="chatvoice",
    help="CLI for running the chat in different modes.")

@cli.command
def console(
        project_pathname: Annotated[Path, cyclopts.Parameter(validator=cyclopts.validators.Path(exists=True))],
        *,
        name: str = "chatvoice",
        logging_json: bool = False,
        logging_level: str = "error",
        logging_file: str = "logs/chatvoice.log",
):
    """Runs the chat from the console.

    Parameters
    ----------

    conversation: Directory with the conversation to have with the chat.
    """
    from transport.console import Console

    setup_logging(json_output=logging_json, log_file=logging_file, log_level=logging_level)
    log = get_logger(__name__)

    print(f"Initializing LLM client.")
    llm_client=init_llm_client(settings)
    print(f"Running [yellow]{project_pathname}[/] conversation from the console as [green]{name}[/].")
    console = Console()
    user=console.authenticate_user()
    if not user:
        print("[red]Authentication failed. Please check your credentials and try again.[/]")
        return None


    interpreter = Interpreter(
        project_pathname, 
        user_id = users.id, 
        settings = {"_name_system":name},
        llm_client = llm_client    
    )
    console.run(users.id, interpreter)

@cli.command
def server(
    logging_json: bool = False,
    logging_level: str = "error",
    logging_file: str = "logs/chatvoice.log",
):
    """Runs the server chat.

    Parameters
    ----------

    """
    setup_logging(json_output=logging_json, log_file=logging_file, log_level=logging_level)
    log = get_logger(__name__)

    print("Running the [yellow]server chat[/].")
    log.info("Starting server chat")
    
@cli.command
def create_admin(
        logging_json: bool = False,
        logging_level: str = "debug",
        logging_file: str = "logs/chatvoice.log",
):
    """Creates admin user.

    Parameters
    ----------

    """
    from utils.admin import create_admin_user

    setup_logging(json_output=logging_json, log_file=logging_file, log_level=logging_level)
    log = get_logger(__name__)

    print("About to create [yellow]admin user[/].")
    create_admin_user()

@cli.command
def create_tier(
        logging_json: bool = False,
        logging_level: str = "debug",
        logging_file: str = "logs/chatvoice.log",
):
    """Creates tier.

    Parameters
    ----------

    """
    from utils.admin import create_tier

    setup_logging(json_output=logging_json, log_file=logging_file, log_level=logging_level)
    log = get_logger(__name__)

    print("About to create a [yellow]tier[/].")
    create_tier()

# Meta definition to load the config and run the app with the tokens passed as arguments.
@cli.meta.default
def meta(
    *tokens: Annotated[str, cyclopts.Parameter(show=False, allow_leading_hyphen=True)],
    config: Path = Path("config.toml"),
    root_keys: Annotated[list[str], cyclopts.Parameter(converter=lambda rks : rks.split("."))] = ['default'],
):
    cli.config = [
            cyclopts.config.Env("CHATVOICE_"),
            cyclopts.config.Toml(
                config,
                root_keys=root_keys,
                search_parents=True,
            )]
    cli(tokens)


if __name__ == "__main__":
    cli.meta()
