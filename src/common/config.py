# src/common/config.py
import yaml
import os
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from .logger_utils import setup_logger

logger = setup_logger(__name__)


class GitConfigManager:
    """
    Manages reading and writing the YAML configuration file for Git repositories,
    with support for environment variables.
    """
    def __init__(self, config_path: str, env_path: Optional[str] = None):
        self.config_path = config_path
        self.config_data: Optional[Dict[str, Any]] = None

        # Load environment variables upon initialization
        if env_path and os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path)
            logger.info(f"Environment variables loaded from specified file: '{env_path}'.")
        else:
            # If no specific path is provided or the file doesn't exist,
            # load_dotenv() will search for '.env' in the current directory.
            load_dotenv()
            if env_path: # If a non-existent path was explicitly given
                logger.warning(f"Specified .env file '{env_path}' not found. "
                               "Attempting to load '.env' from current directory by default.")
            else: # If no path was specified, use load_dotenv's default behavior
                logger.info("Attempting to load environment variables from default '.env' (if it exists).")


    def _resolve_env_variables(self, data: Any) -> Any:
        """
        Recursively traverses a data structure (dict/list) and replaces
        environment variables in the format ${VAR_NAME}.
        """
        if isinstance(data, dict):
            return {k: self._resolve_env_variables(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_env_variables(item) for item in data]
        elif isinstance(data, str):
            # Searches for patterns like ${VAR_NAME}
            def replace_var(match):
                var_name = match.group(1)
                value = os.getenv(var_name)
                if value is None:
                    logger.warning(f"Environment variable '{var_name}' not found in .env or environment. "
                                   "Placeholder will be kept in YAML.")
                    return match.group(0) # Return the original placeholder if variable is not found
                return value
            # Use re.sub to replace all occurrences of the pattern
            return re.sub(r'\$\{(\w+)\}', replace_var, data)
        return data


    def load_config(self) -> Optional[Dict[str, Any]]:
        """
        Loads the configuration from the YAML file and resolves environment variables.
        """
        if not os.path.exists(self.config_path):
            logger.error(f"Configuration file not found: {self.config_path}")
            return None
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)

            # Resolve environment variables after loading the YAML
            self.config_data = self._resolve_env_variables(raw_config)

            logger.info(f"Configuration loaded from: {self.config_path}")
            return self.config_data
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {self.config_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading YAML file: {e}")
            return None

    def get_repositories(self) -> List[Dict[str, Any]]:
        """
        Returns the list of repository dictionaries.
        """
        if self.config_data and 'repositories' in self.config_data:
            return self.config_data.get('repositories', [])
        return []

    def update_repository_commit(self, repo_name: str, new_commit_hash: str) -> bool:
        """
        Updates the commit hash for a specific repository in the configuration.
        """
        if not self.config_data or 'repositories' not in self.config_data:
            logger.warning("No configuration data loaded or 'repositories' section is missing.")
            return False

        found = False
        for repo in self.config_data['repositories']:
            if repo.get('name') == repo_name:
                repo['commit'] = new_commit_hash
                found = True
                logger.info(f"Commit updated for '{repo_name}': {new_commit_hash[:7]}")
                break

        if not found:
            logger.warning(f"Repository with name '{repo_name}' not found in configuration.")
            return False
        return found

    def save_config(self) -> bool:
        """
        Saves the current configuration back to the YAML file.
        """
        if self.config_data is None:
            logger.error("No configuration data to save.")
            return False
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.config_data, f, indent=2, default_flow_style=False, sort_keys=False)
            logger.info(f"Configuration saved to: {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration to {self.config_path}: {e}")
            return False
