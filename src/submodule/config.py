# src/common/config.py
import yaml
import os
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from common.logger_utils import setup_logger

logger = setup_logger(__name__)


class SubmoduleConfig:
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
        else:
            # If no specific path is provided or the file doesn't exist,
            # load_dotenv() will search for '.env' in the current directory.
            load_dotenv()

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
            return None
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)

            # Resolve environment variables after loading the YAML
            self.config_data = self._resolve_env_variables(raw_config)
            return self.config_data
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {self.config_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading YAML file: {e}")
            return None

    def get_repositories(self, path: str = None) -> List[Dict[str, Any]]:
        """
        Returns the list of repository dictionaries.
        """
        if self.config_data and 'repositories' in self.config_data:
            repositories = self.config_data.get('repositories') or []
            if path:
                repo = [
                    repo
                    for repo in repositories
                    if repo.get('path') == path
                ]
                return repo[0] if repo else None
            else:
                return repositories
        return []

    def update_repository_commit(self, repo_path: str, new_commit_hash: str) -> bool:
        """
        Updates the commit hash for a specific repository in the configuration.
        """
        if not self.config_data or 'repositories' not in self.config_data:
            logger.warning("No configuration data loaded or 'repositories' section is missing.")
            return False

        found = False
        for repo in self.config_data['repositories']:
            if repo.get('path') == repo_path:
                repo['commit'] = new_commit_hash
                found = True
                break

        if not found:
            logger.warning(f"Repository with name '{repo_name}' not found in configuration.")
            return False
        return found

    def add_repository(
        self,
        path: str,
        url: str,
        branch: str,
        commit: str = None,
        depth: int = None,
    ) -> bool:
        """
        Adds a new repository to the configuration.
        """
        if not self.config_data or 'repositories' not in self.config_data:
            logger.warning("No configuration data loaded or 'repositories' section is missing.")
            return False

        if not self.config_data['repositories']:
            self.config_data['repositories'] = []

        self.config_data['repositories'].append({
            'path': path,
            'url': url,
            'branch': branch,
            'commit': commit,
            'depth': depth,
        })

    def remove_repository(self, path: str) -> bool:
        """
        Removes a repository from the configuration.
        """
        if not self.config_data or 'repositories' not in self.config_data:
            logger.warning("No configuration data loaded or 'repositories' section is missing.")
            return False

        self.config_data['repositories'] = [
            repo
            for repo in self.config_data['repositories']
            if repo.get('path') != path
        ]
        return True

    def save_config(self, config_path: str = None) -> bool:
        """
        Saves the current configuration back to the YAML file.
        """
        if self.config_data is None:
            logger.error("No configuration data to save.")
            return False
        try:
            config_path = config_path or self.config_path
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(
                    self.config_data,
                    f,
                    indent=2,
                    default_flow_style=False,
                    sort_keys=False
                )
            return True
        except Exception as e:
            logger.error(f"Error saving configuration to {self.config_path}: {e}")
            return False
