import cyclopts
from typing import Annotated
from pathlib import Path
from rich import print

from core.config import settings 
from core.logger import setup_logging, get_logger

cli = cyclopts.App(
    name="chatvoice",
    help="CLI for running the chat in different modes.")

@cli.command
def console(
        conversation: Annotated[Path, cyclopts.Parameter(validator=cyclopts.validators.Path(exists=True))],
        *,
        name: str = "chatvoice",
        logging_json: bool = False,
        logging_level: str = "debug",
        logging_file: str = "logs/chatvoice.log",
):
    """Runs the chat from the console.

    Parameters
    ----------

    conversation: Directory with the conversation to have with the chat.
    """

    setup_logging(json_output=logging_json, log_file=logging_file, log_level=logging_level)
    
    log = get_logger("chatvoice.console")

    print(f"Running [yellow]{conversation}[/] conversation from the console as [green]{name}[/].")
    log.debug("Starting console chat", conversation=str(conversation), name=name)

@cli.command
def server():
    """Runs the server chat.

    Parameters
    ----------

    """
    print(f"Running the [yellow]server chat[/].")

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
