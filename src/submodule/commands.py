# src/submodule/commands.py
import argparse
import os
import sys

from typing import Dict, Any

# Absolute imports from the 'src' package
from common.logger_utils import setup_logger
from submodule.config import SubmoduleConfig
from submodule.operations import SubmoduleOperations

logger = setup_logger(__name__)


class SubmoduleCommands:
    """
    Manages Git-related subcommands (clone, update, etc.).
    """
    def __init__(self, cli_instance):
        self.cli = cli_instance
        self.operations = SubmoduleOperations(self.cli, logger)
        self.config = None
        self.config_path = None

    def add_subparser(self, subparsers: argparse._SubParsersAction, cli_command_name: str):
        """
        Adds the 'git' subcommand and its operations to a main parser.
        """
        submodule_parser = subparsers.add_parser(
            "submodule",
            help="Operations related to Git (clone, update, etc.).",
            description=f"""
Commands for managing Git repositories.

Usage:
  {cli_command_name} submodule add -f <config_file.yml> [-b <branch>] [--update-yaml] [--env-file <env_file>] repository_uri repository_name
  {cli_command_name} submodule update -f <config_file.yml> [--update-yaml] [--env-file <env_file>] [path] [--remote]
            """,
            formatter_class=argparse.RawTextHelpFormatter
        )

        submodule_subparsers = submodule_parser.add_subparsers(
            dest="command",
            help="Available Git operations",
            required=True
        )

        # 'submodule add' subcommand
        add_parser = submodule_subparsers.add_parser(
            "add",
            help="Adds a new repository to the YAML file.",
            description="""
Adds a new repository to the YAML file.
            """
        )
        add_parser.add_argument(
            "-b", "--branch",
            help="Branch of the repository to add (e.g., main)."
        )
        add_parser.add_argument(
            "url",
            help="URL of the repository to add (e.g., https://github.com/user/repo.git)."
        )
        add_parser.add_argument(
            "path",
            help="Normally relative to the root of the project. Path to the repository to add (e.g., path/to/repo)."
        )
        add_parser.add_argument(
            "-f", "--file",
            dest="config_file",
            default=os.path.join(self.cli.execution_path, 'repositories.yml'),
            help="Path to the YAML file containing repository configurations. "
                 "Default: 'repositories.yml' in the 'src' root directory."
        )
        add_parser.add_argument(
            "--env-file",
            dest="env_file",
            default=None,
            help="Path to the .env file to load environment variables. Default: searches for '.env' in CWD."
        )
        add_parser.add_argument(
            "-c", "--commit",
            help="Commit hash of the repository to add (e.g., 1234567890)."
        )
        add_parser.add_argument(
            "-d", "--depth",
            default=1,
            help="Depth of the repository to add (e.g., 1)."
        )
        add_parser.set_defaults(func=self.handle_submodule_operation)

        # 'submodule update' subcommand
        update_parser = submodule_subparsers.add_parser(
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
            "-p", "--path",
            help="Relative path of config file to the repository to update (e.g., path/to/repo)."
        )
        update_parser.add_argument(
            "-r", "--remote",
            action="store_true",
            help="Update repositories from remote origin."
        )
        update_parser.set_defaults(func=self.handle_submodule_operation)

    def load_config(self, args: argparse.Namespace):
        config_file_path = os.path.join(
            self.cli.execution_path,
            args.config_file
        ) if not os.path.isabs(args.config_file) else args.config_file
        if not os.path.exists(config_file_path):
            logger.critical(
                f"Configuration file not found: {config_file_path}"
            )
            sys.exit(1)
        self.config = SubmoduleConfig(config_file_path, env_path=args.env_file)
        self.config_path = os.path.dirname(config_file_path)

        if not self.config.load_config():
            logger.critical("Could not load repository configuration. Exiting.")
            sys.exit(1)

    def handle_submodule_operation(self, args: argparse.Namespace):
        try:
            self.load_config(args)
            method = getattr(self, f"command_{args.command}")
            method(args)
        except AttributeError:
            logger.error(f"Invalid submodule command: {args.command}")
            sys.exit(1)

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
        config_manager = SubmoduleConfig(config_file_path, env_path=args.env_file)
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

    def command_add(
        self,
        args: argparse.Namespace,
    ):
        if self.config.get_repositories(path=args.path):
            logger.error(f"Repository '{args.path}' already exists.")
            sys.exit(1)

        # get arguments
        path = args.path
        url = args.url
        branch = args.branch
        commit = args.commit
        depth = args.depth

        # Add repository to config
        self.config.add_repository(
            path=path,
            url=url,
            branch=branch,
            commit=commit,
            depth=depth
        )

        # Clone or update repository
        repo_data = self.config.get_repositories(path=path)
        commit = self.operations.clone(repo_data, self.config_path)

        # Update YAML file
        self.config.update_repository_commit(path, commit)
        self.config.save_config()

    def command_update(
        self,
        args: argparse.Namespace,
    ):
        # Get repositories to update
        if args.path:
            repos = [self.config.get_repositories(path=args.path)]
        else:
            repos = self.config.get_repositories()

        for repo_data in repos:
            # Update repository
            commit = self.operations.update(
                repo_data,
                self.config_path,
                args.remote
            )
            # Update YAML file
            self.config.update_repository_commit(repo_data.get('path'), commit)
            self.config.save_config()
