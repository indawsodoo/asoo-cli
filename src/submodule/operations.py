# src/submodule/operations.py
import os
import subprocess
import shutil
import git
import yaml
from collections import OrderedDict

from typing import Optional, Dict, Any

from helpers.yaml import OrderedDictDumper


class SubmoduleOperations:
    """
    Handles low-level Git operations using subprocess calls.
    """
    def __init__(self, cli_instance, logger_instance):
        self.cli = cli_instance
        self.logger = logger_instance

    # ------------------------------
    # BASH COMMANDS METHODS
    # ------------------------------

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

    # ------------------------------
    # OPERATIONS METHODS
    # ------------------------------

    def clone(self, repo_data: Dict[str, Any], path: str, git_clean: bool = True) -> Optional[str]:
        """
        Adds a new repository to the YAML file.
        Returns the final commit hash.
        """
        repo_url = repo_data.get('url')
        repo_path = repo_data.get('path')
        branch = repo_data.get('branch')
        commit = repo_data.get('commit')
        depth = repo_data.get('depth')

        if not repo_url or not repo_path:
            self.logger.error(f"Skipping '{repo_path}': 'url' or 'path' is missing.")
            return None

        # Resolve relative path to absolute path
        abs_repo_path = os.path.abspath(os.path.join(path, repo_path))
        parent_dir = os.path.dirname(abs_repo_path)

        # Recreate Git repository
        self._recreate_git(repo_url, branch, commit, abs_repo_path)

        # Ensure parent directory exists
        if not os.path.exists(parent_dir):
            self.logger.info(f"Creating parent directory: {parent_dir}")
            os.makedirs(parent_dir)

        # Clone if repository does not exist
        try:
            if not os.path.exists(os.path.join(abs_repo_path, '.git')):
                self._clone(repo_url, abs_repo_path, branch, depth, parent_dir)

            if commit:
                self._fetch_and_reset(commit, commit, abs_repo_path)

            commit = self._current_commit_hash(abs_repo_path)
            if git_clean:
                self._remove_git(abs_repo_path)
            return commit
        except Exception as e:
            self.logger.error(f"Failed to update repository '{repo_path}': {e}")
            return None

    def update(self, repo_data: Dict[str, Any], path: str, remote: bool = False, git_clean: bool = False) -> Optional[str]:
        """
        Updates a repository to the specified commit hash.
        """
        repo_path = repo_data.get('path')
        repo_url = repo_data.get('url')
        commit = repo_data.get('commit')
        branch = str(repo_data.get('branch'))

        abs_repo_path = os.path.abspath(os.path.join(path, repo_path))

        # Recreate Git repository
        self._recreate_git(repo_url, branch, commit, abs_repo_path)

        if not os.path.exists(os.path.join(abs_repo_path, '.git')):
            self.clone(repo_data, path)
        try:

            if remote:
                self._fetch_and_reset(branch, f"origin/{branch}", abs_repo_path)
            else:
                self._fetch_and_reset(commit, commit, abs_repo_path)

            commit = self._current_commit_hash(abs_repo_path)
            if git_clean:
                self._remove_git(abs_repo_path)
            return commit
        except Exception as e:
            self.logger.error(f"Failed to update repository '{repo_path}': {e}")
            return None

    def rm(self, repo_data: Dict[str, Any], path: str) -> Optional[str]:
        """
        Removes a repository from the YAML file.
        """
        repo_path = repo_data.get('path')
        if not os.path.exists(os.path.join(path, repo_path)):
            return None
        shutil.rmtree(os.path.join(path, repo_path))
        return None

    def generate(self, gitmodules_file: str, output_file: str) -> Optional[str]:
        """
        Generates a new YAML from .gitmodules file.
        """
        repo_path = os.path.dirname(gitmodules_file)
        repo = git.Repo(repo_path)
        repositories = []
        for submodule in repo.submodules:
            repositories.append(OrderedDict({
                'path': submodule.path,
                'url': submodule.url,
                'branch': submodule.branch_name,
                'commit': submodule.hexsha,
                'depth': 1
            }))

        with open(output_file, 'w') as f:
            yaml.dump(
                {'repositories': repositories},
                f,
                Dumper=OrderedDictDumper
            )
        return repositories

    # ------------------------------
    # GIT COMMANDS METHODS
    # ------------------------------

    def _clone(self, repo_url: str, repo_path: str, branch: str, depth: int, path: str) -> Optional[str]:
        """
        Clones a repository.
        """
        self.logger.info(f"Repository '{repo_path}' does not exist at {repo_path}. Cloning...")
        clone_command = ["clone"]
        if depth:
            clone_command.extend(["--depth", str(depth)])
        if branch:
            clone_command.extend(["--branch", branch])
        clone_command.extend(["--filter=blob:none"])
        clone_command.extend(["--single-branch"])
        clone_command.extend([repo_url, repo_path])
        self._run_git_command(clone_command, path)

    def _fetch_and_reset(self, fetch_resource: str, reset_resource: str, path: str) -> Optional[str]:
        """
        Fetches and resets a repository to the specified commit hash.
        """
        self._run_git_command([
            "fetch", "--depth", '1', 'origin', fetch_resource],
            path
        )
        self._run_git_command([
            "reset", "--quiet", "--hard", reset_resource],
            path
        )
        self._run_git_command(["clean", "-ffd"], path)

    def _current_commit_hash(self, repo_path: str) -> Optional[str]:
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

    def _remove_git(self, path: str) -> Optional[str]:
        """
        Removes a Git repository.
        """
        shutil.rmtree(os.path.join(path, '.git'))
        return None

    def _recreate_git(self, url: str, branch: str, commit: str, path: str) -> Optional[str]:
        """
        Recreates a Git repository.
        """
        if not os.path.exists(path) or os.path.exists(
            os.path.join(path, '.git')
        ):
            return None
        self._run_git_command(["init"], path)
        self._run_git_command(['remote', 'add', 'origin', url], path)
        self._run_git_command(['checkout', '-b', branch], path)
        self._fetch_and_reset(commit, commit, path)
        return None
