"""Logging configuration for the SolarFarmer SDK.

This module provides a centralized logging setup following Python library best practices.
By default, the SDK is silent (NullHandler). Users can enable output via configure_logging().
"""

import logging
import os
import sys

# SDK logger - all SDK modules should use this logger or child loggers
logger = logging.getLogger("solarfarmer")
logger.addHandler(logging.NullHandler())  # Silent by default (library best practice)

# Default format for SDK log messages
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_FORMAT_SIMPLE = "%(levelname)s: %(message)s"


def configure_logging(
    level: str = "INFO",
    verbose: bool = False,
    handler: logging.Handler | None = None,
    format_string: str | None = None,
) -> logging.Logger:
    """Configure SDK logging behavior.

    By default, the SDK produces no output. Call this function to enable logging.

    Parameters
    ----------
    level : str, default "INFO"
        Minimum logging level. One of: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL".
        If verbose=True, this is overridden to "DEBUG".
    verbose : bool, default False
        If True, sets level to DEBUG for maximum output.
    handler : logging.Handler, optional
        Custom handler to add. If None and no handlers exist (besides NullHandler),
        a StreamHandler to stderr is added.
    format_string : str, optional
        Custom format string. If None, uses a simple format.

    Returns
    -------
    logging.Logger
        The configured solarfarmer logger.

    Examples
    --------
    >>> import solarfarmer
    >>> solarfarmer.configure_logging()  # Enable INFO-level output
    >>> solarfarmer.configure_logging(verbose=True)  # Enable DEBUG-level output
    >>> solarfarmer.configure_logging(level="WARNING")  # Only warnings and errors
    """
    # Determine effective level
    if verbose:
        effective_level = logging.DEBUG
    else:
        effective_level = getattr(logging, level.upper(), logging.INFO)

    logger.setLevel(effective_level)

    # Remove existing handlers (except NullHandler on first call)
    for h in logger.handlers[:]:
        if not isinstance(h, logging.NullHandler):
            logger.removeHandler(h)

    # Add handler
    if handler is not None:
        logger.addHandler(handler)
    else:
        # Add default StreamHandler
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setLevel(effective_level)

        # Set format
        fmt = format_string or DEFAULT_FORMAT_SIMPLE
        formatter = logging.Formatter(fmt)
        stream_handler.setFormatter(formatter)

        logger.addHandler(stream_handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger for SDK modules.

    Parameters
    ----------
    name : str, optional
        Child logger name. If None, returns the root SDK logger.
        If provided, returns a child logger (e.g., "solarfarmer.endpoint").

    Returns
    -------
    logging.Logger
        The requested logger.
    """
    if name is None:
        return logger
    return logging.getLogger(f"solarfarmer.{name}")


# Check for environment variable configuration on import
_env_level = os.getenv("SF_LOG_LEVEL")
_env_verbose = os.getenv("SF_VERBOSE", "").lower() in ("1", "true", "yes")

if _env_verbose or _env_level:
    configure_logging(
        level=_env_level or "DEBUG" if _env_verbose else "INFO",
        verbose=_env_verbose,
    )
