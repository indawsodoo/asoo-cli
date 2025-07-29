# src/asoo_cli.py
import argparse
import sys
import os

# Absolute imports from the 'src' package
from common.logger_utils import setup_logger
from common.cli_config import CLIConfig
from submodule.commands import SubmoduleCommands

# Get CLI configuration for the program name
cli_config = CLIConfig()
CLI_COMMAND_NAME = cli_config.get_command_name()

# Configure the main logger
logger = setup_logger("CLI_Manager")


class AsooCli:
    """
    Main class for managing the command-line interface and dispatching commands.
    """
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog=CLI_COMMAND_NAME,
            description="A modular CLI tool for Git repository management and other operations.",
            formatter_class=argparse.RawTextHelpFormatter
        )
        self.subparsers = self.parser.add_subparsers(
            dest="command",
            help="Available commands",
            required=True
        )
        self.execution_path = os.getcwd()
        self._register_commands()

    def _register_commands(self):
        """
        Registers different commands (e.g., 'git', 'ci', etc.).
        Each command is added through its own handler class.
        """
        # Register the 'git' command
        submodule_commands_handler = SubmoduleCommands(self)
        submodule_commands_handler.add_subparser(
            self.subparsers,
            CLI_COMMAND_NAME
        )

        # You could register other commands here in the future:
        # ci_commands_handler = CICommands()
        # ci_commands_handler.add_subparser(self.subparsers, CLI_COMMAND_NAME)

    def run(self):
        """
        Executes the parser and dispatches the corresponding command.
        """
        args = self.parser.parse_args()

        # If the subcommand has an associated function (set by set_defaults), call it
        if hasattr(args, 'func'):
            args.func(args)
        else:
            # This should not be executed if required=True is set for subparsers, but it's a good fallback
            logger.error(f"Command not implemented or incomplete arguments for: {args.command}")
            self.parser.print_help()
            sys.exit(1)


def asoo_cli():
    """
    Entry point function for the CLI, called by console_scripts.
    """
    cli = AsooCli()
    cli.run()


if __name__ == "__main__":
    asoo_cli()
