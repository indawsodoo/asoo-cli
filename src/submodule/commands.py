# src/submodule/commands.py
import argparse
import os
import sys

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
        self.operations = SubmoduleOperations(self.cli, self, logger)
        self.config = None
        self.config_path = None
        self.config_name = None
        self.hidden_config = None
        self.hidden_config_name = None

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
  {cli_command_name} submodule rm -f <config_file.yml> path
  {cli_command_name} submodule generate -gm <gitmodules_file.yml> -o <output_file.yml>
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
            type=str,
            help="Branch of the repository to add (e.g., main)."
        )
        add_parser.add_argument(
            "url",
            type=str,
            help="URL of the repository to add (e.g., https://github.com/user/repo.git)."
        )
        add_parser.add_argument(
            "path",
            type=str,
            help="Normally relative to the root of the project. Path to the repository to add (e.g., path/to/repo)."
        )
        add_parser.add_argument(
            "-f", "--file",
            type=str,
            dest="config_file",
            default=os.path.join(self.cli.execution_path, 'repositories.yml'),
            help="Path to the YAML file containing repository configurations. "
                 "Default: 'repositories.yml' in the 'src' root directory."
        )
        add_parser.add_argument(
            "--env-file",
            type=str,
            dest="env_file",
            default=None,
            help="Path to the .env file to load environment variables. Default: searches for '.env' in CWD."
        )
        add_parser.add_argument(
            "-c", "--commit",
            type=str,
            help="Commit hash of the repository to add (e.g., 1234567890)."
        )
        add_parser.add_argument(
            "-d", "--depth",
            type=int,
            default=1,
            help="Depth of the repository to add (e.g., 1)."
        )
        add_parser.add_argument(
            "-gc", "--git-clean",
            action="store_true",
            help="Clean .git path of the repository to save space on disk."
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
            type=str,
            dest="config_file",
            default=os.path.join(self.cli.execution_path, 'repositories.yml'),
            help="Path to the YAML file containing repository configurations."
        )
        update_parser.add_argument(
            "--env-file",
            type=str,
            dest="env_file",
            default=None,
            help="Path to the .env file to load environment variables. Default: searches for '.env' in CWD."
        )
        update_parser.add_argument(
            "-p", "--path",
            type=str,
            help="Relative path of config file to the repository to update (e.g., path/to/repo)."
        )
        update_parser.add_argument(
            "-r", "--remote",
            action="store_true",
            help="Update repositories from remote origin."
        )
        update_parser.add_argument(
            "-gc", "--git-clean",
            action="store_true",
            help="Clean .git path of the repository to save space on disk."
        )
        update_parser.add_argument(
            "-ilc", "--ignore-local-changes",
            action="store_true",
            help="Ignore local changes in repositories and lose them"
        )
        update_parser.set_defaults(func=self.handle_submodule_operation)

        # 'submodule rm' subcommand
        rm_parser = submodule_subparsers.add_parser(
            "rm",
            help="Removes a repository from the YAML file.",
            description="""
Removes a repository from the YAML file.
            """
        )
        rm_parser.add_argument(
            "-f", "--file",
            type=str,
            dest="config_file",
            default=os.path.join(self.cli.execution_path, 'repositories.yml'),
            help="Path to the YAML file containing repository configurations."
        )
        rm_parser.add_argument(
            "--env-file",
            type=str,
            dest="env_file",
            default=None,
            help="Path to the .env file to load environment variables. Default: searches for '.env' in CWD."
        )
        rm_parser.add_argument(
            "path",
            type=str,
            help="Path to the repository to remove (e.g., path/to/repo)."
        )
        rm_parser.set_defaults(func=self.handle_submodule_operation)

        # 'submodule generate' subcommand
        generate_parser = submodule_subparsers.add_parser(
            "generate",
            help="Generate a new YAML from .gitmodules file.",
            description="""
Generate a new YAML from .gitmodules file.
            """
        )
        generate_parser.add_argument(
            "-gm", "--gitmodules",
            type=str,
            dest="gitmodules_file",
            default=os.path.join(self.cli.execution_path, '.gitmodules'),
            help="Path to the .gitmodules file to generate the YAML from."
        )
        generate_parser.add_argument(
            "-o", "--output",
            type=str,
            dest="output_file",
            default=os.path.join(self.cli.execution_path, 'repositories.yml'),
            help="Path to the YAML file to generate."
        )
        generate_parser.set_defaults(func=self.handle_submodule_operation)

    def load_config(self, args: argparse.Namespace):
        if not hasattr(args, 'config_file'):
            return

        config_file_path = os.path.join(
            self.cli.execution_path,
            args.config_file
        ) if not os.path.isabs(args.config_file) else args.config_file
        if not os.path.exists(config_file_path):
            logger.critical(
                f"Configuration file not found: {config_file_path}"
            )
            sys.exit(1)

        # Load config
        self.config = SubmoduleConfig(config_file_path, env_path=args.env_file)
        self.config_path = os.path.dirname(config_file_path)
        self.config_name = os.path.basename(config_file_path)
        if not self.config.load_config():
            logger.critical("Could not load repository configuration. Exiting.")
            sys.exit(1)

        # Load hidden config
        self.hidden_config_name = f'.{self.config_name}'
        self.hidden_config = SubmoduleConfig(
            os.path.join(self.config_path, self.hidden_config_name),
            env_path=args.env_file
        )
        self.hidden_config.load_config()

    def handle_submodule_operation(self, args: argparse.Namespace):
        try:
            method = getattr(self, f"command_{args.command}")
        except AttributeError:
            logger.error(f"Invalid submodule command: {args.command}")
            sys.exit(1)

        self.remove_deleted_submodules(args)
        method(args)

        # Save backup config file
        if self.hidden_config and self.config:
            self.config.save_config(self.hidden_config.config_path)

    def remove_deleted_submodules(self, args: argparse.Namespace):
        self.load_config(args)
        if not self.config:
            return

        repositories = [r.get('path') for r in self.config.get_repositories()]
        old_repositories = self.hidden_config.get_repositories()
        for repository in old_repositories:
            if repository.get('path') not in repositories:
                self.operations.rm(repository, self.config_path)

    def command_add(
        self,
        args: argparse.Namespace,
    ):
        self.load_config(args)
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
        commit = self.operations.clone(
            repo_data,
            self.config_path,
            args.git_clean
        )

        # Update YAML file
        self.config.update_repository_commit(path, commit)
        self.config.save_config()

    def command_update(
        self,
        args: argparse.Namespace,
    ):
        self.load_config(args)

        # Get repositories to update
        if args.path:
            repos = self.config.get_repositories(path=args.path)
            if not repos:
                logger.error(
                    f"Submodule \033[1;33;1m{args.path}\033[0m not found"
                )
                sys.exit(1)
            repos = [repos]
        else:
            repos = self.config.get_repositories()

        for repo_data in repos:
            # Update repository
            commit = self.operations.update(
                repo_data,
                self.config_path,
                args.remote,
                args.git_clean,
                args.ignore_local_changes
            )
            if not commit:
                continue

            # Update YAML file
            self.config.update_repository_commit(repo_data.get('path'), commit)
            self.config.save_config()

    def command_rm(
        self,
        args: argparse.Namespace,
    ):
        self.load_config(args)
        repo_data = self.config.get_repositories(path=args.path)
        if not repo_data:
            logger.error(f"Repository '{args.path}' not found.")
            sys.exit(1)

        # Remove repository from filesystem
        self.operations.rm(repo_data, self.config_path)

        # Remove repository from config
        self.config.remove_repository(args.path)
        self.config.save_config()

    def command_generate(
        self,
        args: argparse.Namespace,
    ):
        self.operations.generate(args.gitmodules_file, args.output_file)
