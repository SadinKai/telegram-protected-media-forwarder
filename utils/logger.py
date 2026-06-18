import logging
import os
from logging.handlers import RotatingFileHandler

from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Custom formatter to inject terminal color codes into log levels."""

    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        message = super().format(record)
        if color:
            # Colorize the level name or entire log message
            message = message.replace(
                record.levelname, f"{color}{record.levelname}{Style.RESET_ALL}"
            )
        return message


def setup_logger(
    log_level: str = "INFO", log_dir: str = "logs", log_file: str = "app.log"
) -> logging.Logger:
    """Configures and returns the main application logger with console and rotating file handlers."""
    logger = logging.getLogger("forwarder")
    logger.setLevel(log_level)

    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger

    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    # File handler: Rotating log files (5MB size, max 5 files backups)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] (%(name)s) %(filename)s:%(lineno)d: %(message)s"
    )
    file_handler = RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler: Colored console log output
    console_formatter = ColoredFormatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger() -> logging.Logger:
    """Convenience getter for the configured logger."""
    return logging.getLogger("forwarder")
