import os
from configparser import ConfigParser
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


class ConfigError(Exception):
    """Exception raised for configuration errors."""

    pass


class ForwardJob:
    """Represents a single message forwarding task."""

    def __init__(self, name: str, from_chat: str, to_chat: str, initial_offset: int = 0):
        self.name = name
        self.from_chat = from_chat
        self.to_chat = to_chat
        self.initial_offset = initial_offset

    def __repr__(self):
        return f"ForwardJob(name='{self.name}', from='{self.from_chat}', to='{self.to_chat}', initial_offset={self.initial_offset})"


class AppConfig:
    """Holds configuration settings for the entire application."""

    def __init__(self, config_file_path: str = "config.ini"):
        self.config_file_path = config_file_path
        self.parser = ConfigParser()
        if os.path.exists(config_file_path):
            self.parser.read(config_file_path)

        # Load & validate general settings
        self.api_id = self._get_int("API_ID", "api_id", None)
        self.api_hash = self._get_str("API_HASH", "api_hash", None)
        self.string_session = self._get_str("STRING_SESSION", "string_session", "")
        self.download_dir = self._get_str("DOWNLOAD_DIR", "download_dir", "downloads")
        self.log_level = self._get_str("LOG_LEVEL", "log_level", "INFO").upper()
        self.keep_downloads = self._get_bool("KEEP_DOWNLOADS", "keep_downloads", False)
        self.max_retries = self._get_int("MAX_RETRIES", "max_retries", 3)
        self.upload_delay = self._get_float("UPLOAD_DELAY", "upload_delay", 3.0)
        self.flood_wait_limit = self._get_int("FLOOD_WAIT_LIMIT", "flood_wait_limit", 300)
        self.state_file_path = self._get_str(
            "STATE_FILE_PATH", "state_file_path", "data/state.json"
        )

        self.jobs = []
        self._load_jobs()

    def _get_str(self, env_key: str, ini_key: str, default: str) -> str:
        # Priority: Env Var > Config.ini [General] > Default
        val = os.getenv(env_key)
        if val is not None:
            return val
        if self.parser.has_option("General", ini_key):
            return self.parser.get("General", ini_key)
        return default

    def _get_int(self, env_key: str, ini_key: str, default: int) -> int:
        val_str = self._get_str(env_key, ini_key, str(default) if default is not None else "")
        if not val_str:
            return default
        try:
            return int(val_str)
        except ValueError:
            raise ConfigError(f"Invalid integer value for {env_key}/{ini_key}: '{val_str}'")

    def _get_float(self, env_key: str, ini_key: str, default: float) -> float:
        val_str = self._get_str(env_key, ini_key, str(default) if default is not None else "")
        if not val_str:
            return default
        try:
            return float(val_str)
        except ValueError:
            raise ConfigError(f"Invalid float value for {env_key}/{ini_key}: '{val_str}'")

    def _get_bool(self, env_key: str, ini_key: str, default: bool) -> bool:
        val_str = self._get_str(env_key, ini_key, str(default)).lower()
        if val_str in ("true", "1", "yes", "on"):
            return True
        if val_str in ("false", "0", "no", "off"):
            return False
        raise ConfigError(f"Invalid boolean value for {env_key}/{ini_key}: '{val_str}'")

    def _load_jobs(self):
        """Loads jobs from the config file. Any section that is not General is considered a job."""
        for section in self.parser.sections():
            if section.lower() == "general":
                continue

            if not self.parser.has_option(section, "from") or not self.parser.has_option(
                section, "to"
            ):
                raise ConfigError(f"Job section [{section}] is missing 'from' or 'to' key.")

            from_chat = self.parser.get(section, "from").strip()
            to_chat = self.parser.get(section, "to").strip()
            initial_offset = 0

            if self.parser.has_option(section, "offset"):
                try:
                    initial_offset = self.parser.getint(section, "offset")
                except ValueError:
                    raise ConfigError(f"Job section [{section}] has invalid offset value.")

            if not from_chat or not to_chat:
                raise ConfigError(
                    f"Job section [{section}] cannot have empty 'from' or 'to' parameters."
                )

            self.jobs.append(ForwardJob(section, from_chat, to_chat, initial_offset))

    def validate(self):
        """Performs validation of the loaded config parameters."""
        if not self.api_id:
            raise ConfigError(
                "API_ID is required. Please set it in .env, environment variables or config.ini."
            )
        if not self.api_hash:
            raise ConfigError(
                "API_HASH is required. Please set it in .env, environment variables or config.ini."
            )
        if len(self.api_hash) != 32:
            raise ConfigError("API_HASH must be exactly 32 characters long.")
        if self.max_retries < 0:
            raise ConfigError("MAX_RETRIES must be a non-negative integer.")
        if self.upload_delay < 0:
            raise ConfigError("UPLOAD_DELAY must be a non-negative float.")
        if self.flood_wait_limit < 0:
            raise ConfigError("FLOOD_WAIT_LIMIT must be a non-negative integer.")

        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            raise ConfigError(f"LOG_LEVEL must be one of {valid_log_levels}")

        # Verify paths can be created
        try:
            Path(self.download_dir).mkdir(parents=True, exist_ok=True)
            Path(self.state_file_path).parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ConfigError(f"Failed to create configuration directories: {e}")

        # Check jobs
        if not self.jobs:
            raise ConfigError(
                "No forwarding jobs defined. Define at least one section (other than [General]) in config.ini."
            )


def load_config(config_file_path: str = "config.ini") -> AppConfig:
    """Utility function to load and validate configurations."""
    config = AppConfig(config_file_path)
    config.validate()
    return config
