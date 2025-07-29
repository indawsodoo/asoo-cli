# src/common/logger_utils.py
import logging
import sys

from colorlog import ColoredFormatter


def setup_logger(name: str = "CLI_Tool", level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a logger with colored console output.

    Args:
        name (str): The name of the logger.
        level (int): The minimum logging level for messages (e.g., logging.INFO, logging.DEBUG).

    Returns:
        logging.Logger: A configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding multiple handlers if the logger has already been configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        # Log format: Colored Level, Timestamp, Logger Name, Message
        formatter = ColoredFormatter(
            "%(log_color)s%(levelname)s%(reset)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red,bg_white',
            },
            secondary_log_colors={},
            style='%'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
