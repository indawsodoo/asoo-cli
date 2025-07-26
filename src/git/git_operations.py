# src/git/git_operations.py
import os
import subprocess
from typing import Optional, Dict, Any


class GitOperations:
    """
    Handles low-level Git operations using subprocess calls.
    """
    def __init__(self, cli_instance, logger_instance):
        self.cli = cli_instance
        self.logger = logger_instance

    def _run_git_command(self, command: list, path: str, env: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Runs a Git command in the specified path and returns its stdout.
        Handles errors and logs output.
        """
        full_command = ["git"] + command
        self.logger.debug(f"Executing command: {' '.join(map(str, full_command))} in {path}")
        try:
            process = subprocess.run(
                list(map(str, full_command)),
                cwd=path,
                capture_output=True,
                text=True,
                check=True, # Raise an exception for non-zero exit codes
                env=env # Pass custom environment variables (e.g., GIT_SSH_COMMAND)
            )
            self.logger.debug(f"Command stdout: {process.stdout.strip()}")
            return process.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git command failed: {' '.join(full_command)}")
            self.logger.error(f"Stderr: {e.stderr.strip()}")
            self.logger.error(f"Stdout: {e.stdout.strip()}")
            raise RuntimeError(f"Git command failed: {e.stderr.strip()}") from e
        except FileNotFoundError:
            self.logger.error("Git executable not found. Please ensure Git is installed and in your PATH.")
            raise
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while running Git command: {e}")
            raise

    def clone_or_update(self, repo_data: Dict[str, Any], path: str) -> Optional[str]:
        """
        Clones a repository if it doesn't exist, or updates it if it does.
        Handles branch, commit, depth, and squash_history options.
        Returns the final commit hash.
        """
        repo_name = repo_data.get('name', 'unknown_repo')
        repo_url = repo_data.get('url')
        repo_path = repo_data.get('path')
        branch = repo_data.get('branch')
        commit = repo_data.get('commit')
        depth = repo_data.get('depth')

        if not repo_url or not repo_path:
            self.logger.error(f"Skipping '{repo_name}': 'url' or 'path' is missing.")
            return None

        # Resolve relative path to absolute path
        abs_repo_path = os.path.abspath(os.path.join(path, repo_path))
        parent_dir = os.path.dirname(abs_repo_path)

        # Ensure parent directory exists
        if not os.path.exists(parent_dir):
            self.logger.info(f"Creating parent directory: {parent_dir}")
            os.makedirs(parent_dir)

        # Clone if repository does not exist
        try:
            if not os.path.exists(os.path.join(abs_repo_path, '.git')):
                self.logger.info(f"Repository '{repo_name}' does not exist at {abs_repo_path}. Cloning...")
                clone_command = ["clone"]
                if depth:
                    clone_command.extend(["--depth", str(depth)])
                if branch:
                    clone_command.extend(["--branch", branch])
                clone_command.extend(["--filter=blob:none"])
                clone_command.extend([repo_url, abs_repo_path])
                self._run_git_command(clone_command, parent_dir)

            if commit:
                self._run_git_command(["fetch", "--depth", '1', 'origin', commit], abs_repo_path)
                self._run_git_command(["reset", "--quiet", "--hard", commit], abs_repo_path)
                self._run_git_command(["clean", "-ffd"], abs_repo_path)

            return self.get_current_commit_hash(abs_repo_path)
        except Exception as e:
            self.logger.error(f"Failed to update repository '{repo_name}': {e}")
            return None

    def update(self, repo_data: Dict[str, Any], path: str, remote: bool = False) -> Optional[str]:
        """
        Updates a repository to the specified commit hash.
        """
        repo_name = repo_data.get('name', 'unknown_repo')
        repo_path = repo_data.get('path')
        commit = repo_data.get('commit')
        branch = str(repo_data.get('branch'))
        resource = commit if not remote and commit else branch
        reset_resource = f"origin/{resource}" if remote else resource

        abs_repo_path = os.path.abspath(os.path.join(path, repo_path))
        if not os.path.exists(os.path.join(abs_repo_path, '.git')):
            self.logger.error(f"Repository '{repo_name}' does not exist at {abs_repo_path}. Cannot update.")
            return None
        try:
            self._run_git_command(["fetch", 'origin', resource], abs_repo_path)
            self._run_git_command(["reset", "--quiet", "--hard", reset_resource], abs_repo_path)
            self._run_git_command(["clean", "-ffd"], abs_repo_path)

            return self.get_current_commit_hash(abs_repo_path)
        except Exception as e:
            self.logger.error(f"Failed to update repository '{repo_name}': {e}")
            return None

    def get_current_commit_hash(self, repo_path: str) -> Optional[str]:
        """
        Retrieves the current HEAD commit hash of a repository.
        """
        abs_repo_path = os.path.abspath(repo_path)
        if not os.path.exists(abs_repo_path) or not os.path.isdir(os.path.join(abs_repo_path, '.git')):
            self.logger.warning(f"Repository path does not exist or is not a Git repo: {abs_repo_path}")
            return None
        try:
            return self._run_git_command(["rev-parse", "HEAD"], abs_repo_path)
        except Exception as e:
            self.logger.error(f"Failed to get current commit hash for {repo_path}: {e}")
            return None
