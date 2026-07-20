import logging
import logging.handlers
from pathlib import Path

import structlog


def setup_logging(
    json_output: bool = False,
    log_file: str | None = None,
    log_level: str = "DEBUG",
):
    level = logging.getLevelName(log_level.upper())

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    root_logger = logging.getLogger()
    root_logger.setLevel(level)  # ← set on root logger

    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(level)  # ← set on each handler
    root_logger.addHandler(stdout_handler)

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)  # ← and on the file handler
        root_logger.addHandler(file_handler)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),  # ← and here
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    return structlog.get_logger(name)
