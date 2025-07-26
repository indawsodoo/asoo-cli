# src/git/commands.py
import argparse
import os
import sys

from typing import Dict, Any

# Absolute imports from the 'src' package
from common.logger_utils import setup_logger
from common.config import GitConfigManager
from git.git_operations import GitOperations

logger = setup_logger(__name__)


class GitCommands:
    """
    Manages Git-related subcommands (clone, update, etc.).
    """
    def __init__(self, cli_instance):
        self.cli = cli_instance
        self.git_operations = GitOperations(self.cli, logger) # Pass the logger instance to GitOperations

    def add_subparser(self, subparsers: argparse._SubParsersAction, cli_command_name: str):
        """
        Adds the 'git' subcommand and its operations to a main parser.
        """
        git_parser = subparsers.add_parser(
            "git",
            help="Operations related to Git (clone, update, etc.).",
            description=f"""
Commands for managing Git repositories.

Usage:
  {cli_command_name} git clone -f <config_file.yml> [--update-yaml] [--env-file <env_file>]
  {cli_command_name} git update -f <config_file.yml> [--update-yaml] [--env-file <env_file>]
            """,
            formatter_class=argparse.RawTextHelpFormatter
        )

        git_subparsers = git_parser.add_subparsers(
            dest="git_command",
            help="Available Git operations",
            required=True
        )

        # 'git clone' subcommand
        clone_parser = git_subparsers.add_parser(
            "clone",
            help="Clones or updates repositories listed in a YAML file.",
            description="""
Clones repositories specified in the YAML file.
If a repository already exists, it will attempt to update it.
            """
        )
        clone_parser.add_argument(
            "-f", "--file",
            dest="config_file",
            default=os.path.join(self.cli.execution_path, 'repositories.yml'),
            help="Path to the YAML file containing repository configurations. "
                 "Default: 'repositories.yml' in the 'src' root directory."
        )
        clone_parser.add_argument(
            "--env-file",
            dest="env_file",
            default=None,
            help="Path to the .env file to load environment variables. Default: searches for '.env' in CWD."
        )
        clone_parser.add_argument(
            "--update-yaml",
            action="store_true",
            help="Updates the YAML file with the latest commit hash of each repository after the operation. "
                 "Useful for replicating the exact state on another server."
        )
        clone_parser.add_argument(
            "-r", "--repository-names",
            dest="repository_names",
            default=None,
            help="Names of the repositories to clone or update."
        )
        clone_parser.set_defaults(func=self.handle_git_operation)

        # 'git update' subcommand
        update_parser = git_subparsers.add_parser(
            "update",
            help="Updates existing repositories to their latest commit or specified commit.",
            description="""
Updates already cloned repositories.
This option is similar to 'clone' but focused on existing repositories.
            """
        )
        update_parser.add_argument(
            "-f", "--file",
            dest="config_file",
            default=os.path.join(self.cli.execution_path, 'repositories.yml'),
            help="Path to the YAML file containing repository configurations."
        )
        update_parser.add_argument(
            "--env-file",
            dest="env_file",
            default=None,
            help="Path to the .env file to load environment variables. Default: searches for '.env' in CWD."
        )
        update_parser.add_argument(
            "--update-yaml",
            action="store_true",
            help="Updates the YAML file with the latest commit hash of each repository after the operation."
        )
        update_parser.add_argument(
            "-r", "--remote",
            action="store_true",
            help="Update repositories from remote origin."
        )
        update_parser.add_argument(
            "-rn", "--repository-names",
            dest="repository_names",
            default=None,
            help="Names of the repositories to clone or update."
        )
        update_parser.set_defaults(func=self.handle_git_operation)


    def handle_git_operation(self, args: argparse.Namespace):
        """
        Handles the logic for 'git clone' and 'git update' commands.
        """
        logger.info(f"Starting Git operation with configuration file: {args.config_file}")
        logger.info(f"Using .env file: {args.env_file if args.env_file else 'Default (.env in CWD)'}")
        logger.info(f"Update YAML after operation: {args.update_yaml}")
        config_file_path = os.path.join(self.cli.execution_path, args.config_file) if not os.path.isabs(args.config_file) else args.config_file
        if not os.path.exists(config_file_path):
            logger.critical(f"Configuration file not found: {config_file_path}")
            sys.exit(1)

        config_path = os.path.dirname(config_file_path)
        config_manager = GitConfigManager(config_file_path, env_path=args.env_file)
        if not config_manager.load_config():
            logger.critical("Could not load repository configuration. Exiting.")
            sys.exit(1)

        if args.repository_names:
            repos_config = [
                repo
                for repo in config_manager.get_repositories()
                if repo.get('name') in args.repository_names.split(',')
            ]
        else:
            repos_config = config_manager.get_repositories()

        if not repos_config:
            logger.warning("No repositories found in the configuration file.")
            sys.exit(0)

        logger.info(f"Found {len(repos_config)} repositories to process.")

        for repo_data in repos_config:
            repo_name = repo_data.get('name', 'UNKNOWN_REPO')
            logger.info(f"Processing repository: {repo_name}")
            try:
                method = getattr(self, f"command_{args.git_command}")
            except AttributeError:
                logger.error(f"Invalid Git command: {args.git_command}")
                sys.exit(1)

            try:
                method(
                    repo_data,
                    config_path,
                    config_manager,
                    args,
                )
            except Exception as e:
                logger.error(f"Error processing '{repo_name}': {e}")

        if args.update_yaml:
            logger.info("Saving changes to the YAML file...")
            if config_manager.save_config():
                logger.info("YAML file successfully updated and saved.")
            else:
                logger.error("Failed to save updated YAML file.")
        else:
            logger.info("Git operations completed. YAML file not modified.")

    def command_clone(
        self,
        repo_data: Dict[str, Any],
        path: str,
        config_manager: GitConfigManager,
        args: argparse.Namespace,
    ):
        repo_name = repo_data.get('name', 'UNKNOWN_REPO')
        current_hash = self.git_operations.clone(repo_data, path=path)
        if args.update_yaml and current_hash:
            self.update_yaml(repo_name, current_hash, config_manager)

    def command_update(
        self,
        repo_data: Dict[str, Any],
        path: str,
        config_manager: GitConfigManager,
        args: argparse.Namespace,
    ):
        repo_name = repo_data.get('name', 'UNKNOWN_REPO')
        current_hash = self.git_operations.update(
            repo_data,
            path=path,
            remote=args.remote
        )
        if args.update_yaml and current_hash:
            self.update_yaml(repo_name, current_hash, config_manager)
        return current_hash

    def update_yaml(
        self,
        repo_name: str,
        current_hash: str,
        config_manager: GitConfigManager,
    ):
        if config_manager.update_repository_commit(repo_name, current_hash):
            logger.info(f"Commit for '{repo_name}' updated in memory to {current_hash[:7]}.")
        else:
            logger.warning(f"Could not update commit for '{repo_name}' in memory.")