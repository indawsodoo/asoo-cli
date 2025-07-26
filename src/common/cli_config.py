# src/common/cli_config.py
import os
import yaml
from typing import Dict, Any, Optional

from .logger_utils import setup_logger

logger = setup_logger(__name__)


class CLIConfig:
    """
    Manages the global CLI configuration, such as the main command name.
    """
    _instance = None
    _config_data: Dict[str, Any] = {}
    _is_loaded = False

    def __new__(cls, config_file_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(CLIConfig, cls).__new__(cls)
            cls._instance._load_config(config_file_path)
        return cls._instance

    def _load_config(self, config_file_path: Optional[str] = None):
        """
        Loads CLI configuration from a YAML file.
        If no path is provided, it searches in predefined locations.
        """
        if self._is_loaded:
            return

        # Default paths (order of preference)
        # 1. Current working directory
        # 2. Inside the 'common' package directory
        default_paths = [
            'cli_config.yml',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cli_config.yml')
        ]

        actual_config_path = config_file_path
        if not actual_config_path:
            for p in default_paths:
                if os.path.exists(p):
                    actual_config_path = p
                    break

        if actual_config_path and os.path.exists(actual_config_path):
            try:
                with open(actual_config_path, 'r', encoding='utf-8') as f:
                    self._config_data = yaml.safe_load(f)
                logger.info(f"CLI configuration loaded from: {actual_config_path}")
            except yaml.YAMLError as e:
                logger.error(f"Error parsing CLI configuration file {actual_config_path}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error loading CLI configuration: {e}")
        else:
            logger.info("CLI configuration file not found. Using default values.")

        self._is_loaded = True

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a value from the CLI configuration.
        """
        return self._config_data.get(key, default)

    def get_command_name(self) -> str:
        """
        Retrieves the main CLI command name.
        """
        return self.get('cli_name', 'incloud') # Default to 'incloud'
