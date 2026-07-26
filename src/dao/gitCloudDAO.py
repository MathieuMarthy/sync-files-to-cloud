import hashlib
import json
import logging
import os.path
import shutil
import urllib.parse
from pathlib import Path

import git
from git.exc import GitCommandError

from src import utils
from src.dao.cloudDAO import CloudDAO
from src.exceptions.DaoException import (
    AuthentificationRequiredException,
    DaoConnectionException,
    NoCredentialFileException,
    NoInternet,
)

logger = logging.getLogger("sync_files_to_cloud")

CREDENTIALS_PATH = "credentials/git_credentials.json"
CACHE_DIR_PATH = ".cache/git_repos"


class GitCloudDAO(CloudDAO):
    def __init__(self):
        super().__init__()
        self.repo = None
        self.repo_url = None
        self.auth_type = None
        self.ssh_key_path = None
        self.username = None
        self.token = None
        self.branch = "main"
        self.author_name = "Sync Files Bot"
        self.author_email = "bot@sync-files-to-cloud.local"
        self.local_repo_path = None
        self.git_env = {}

    def init_connection(self, can_open_connection_page: bool = False, folder=None):
        creds_file = utils.path(CREDENTIALS_PATH)
        if not os.path.exists(creds_file):
            raise NoCredentialFileException(
                f"Git: missing credentials file for authentication. Please provide the file at {CREDENTIALS_PATH}"
            )

        try:
            with open(creds_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            raise NoCredentialFileException(
                f"Git: invalid credentials JSON file at {CREDENTIALS_PATH}: {e}"
            )

        self.repo_url = (folder and getattr(folder, "repository_url", None)) or config.get("repository_url")
        if not self.repo_url:
            raise NoCredentialFileException(
                f"Git: 'repository_url' is missing in config.yaml or {CREDENTIALS_PATH}"
            )

        self.auth_type = config.get("auth_type", "none").lower()
        self.branch = (folder and getattr(folder, "branch", None)) or config.get("branch", "main")
        self.author_name = config.get("author_name", "Sync Files Bot")
        self.author_email = config.get("author_email", "bot@sync-files-to-cloud.local")
        self.ssh_key_path = config.get("ssh_key_path")
        self.username = config.get("username", "")
        self.token = config.get("token", "")

        self.git_env = os.environ.copy()
        auth_repo_url = self.repo_url

        if self.auth_type == "ssh":
            if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                self.git_env["GIT_SSH_COMMAND"] = (
                    f'ssh -i "{self.ssh_key_path}" -o StrictHostKeyChecking=accept-new'
                )
            elif self.ssh_key_path and not os.path.exists(self.ssh_key_path):
                raise DaoConnectionException(
                    f"Git: SSH key file not found at {self.ssh_key_path}"
                )
            else:
                self.git_env["GIT_SSH_COMMAND"] = (
                    "ssh -o StrictHostKeyChecking=accept-new"
                )
        elif self.auth_type == "token":
            if not self.token:
                if not can_open_connection_page:
                    raise AuthentificationRequiredException(
                        "Git: token missing in credentials configuration"
                    )
                else:
                    raise DaoConnectionException(
                        f"Git: 'token' parameter is missing in {CREDENTIALS_PATH}"
                    )
            auth_repo_url = self._get_token_url(
                self.repo_url, self.username, self.token
            )

        # Generate a unique cache directory for this repository URL
        url_hash = hashlib.md5(self.repo_url.encode("utf-8")).hexdigest()[:10]
        repo_name = os.path.basename(self.repo_url.rstrip("/")).replace(".git", "")
        self.local_repo_path = Path(
            utils.path(os.path.join(CACHE_DIR_PATH, f"{repo_name}_{url_hash}"))
        )

        try:
            if not self.local_repo_path.exists():
                logger.debug(
                    f"Git: cloning repository {self.repo_url} into {self.local_repo_path} (branch: {self.branch})"
                )
                os.makedirs(self.local_repo_path.parent, exist_ok=True)
                try:
                    self.repo = git.Repo.clone_from(
                        auth_repo_url,
                        str(self.local_repo_path),
                        branch=self.branch,
                        env=self.git_env,
                    )
                except GitCommandError as clone_err:
                    if "Remote branch" in str(clone_err) or "not found" in str(clone_err):
                        logger.debug(
                            f"Git: branch '{self.branch}' not found on remote (possibly empty repository). Cloning without branch flag..."
                        )
                        self.repo = git.Repo.clone_from(
                            auth_repo_url,
                            str(self.local_repo_path),
                            env=self.git_env,
                        )
                        try:
                            self.repo.git.checkout("-b", self.branch)
                        except GitCommandError:
                            try:
                                self.repo.git.checkout(self.branch)
                            except GitCommandError:
                                pass
                    else:
                        raise clone_err
            else:
                logger.debug(
                    f"Git: repository exists in cache at {self.local_repo_path}, updating..."
                )
                self.repo = git.Repo(str(self.local_repo_path))
                with self.repo.git.custom_environment(**self.git_env):
                    self.repo.git.remote("set-url", "origin", auth_repo_url)
                    try:
                        self.repo.git.fetch("origin", self.branch)
                        self.repo.git.reset("--hard", f"origin/{self.branch}")
                    except GitCommandError:
                        logger.debug(
                            f"Git: could not fetch origin/{self.branch} (branch may not exist remotely yet)."
                        )
                    try:
                        self.repo.git.checkout(self.branch)
                    except GitCommandError:
                        self.repo.git.checkout("-b", self.branch)

            # Restore original clean URL in git config to prevent storing tokens on disk
            if self.auth_type == "token":
                self.repo.git.remote("set-url", "origin", self.repo_url)

            logger.debug("Git: connection initialized successfully")
        except GitCommandError as e:
            err_str = str(e)
            if self.token and self.token in err_str:
                err_str = err_str.replace(self.token, "********")
            logger.error(f"Git connection/sync error: {err_str}")

            if (
                "Authentication failed" in err_str
                or "Permission denied" in err_str
                or "Could not read from remote" in err_str
            ):
                if not can_open_connection_page:
                    raise AuthentificationRequiredException(
                        f"Git: Authentication failed for {self.repo_url}"
                    )
                raise DaoConnectionException(f"Git authentication error: {err_str}")
            elif (
                "Could not resolve host" in err_str
                or "unable to access" in err_str
                or "Connection timed out" in err_str
            ):
                raise NoInternet(
                    f"No Internet access or remote git server is unreachable: {err_str}"
                )
            else:
                raise DaoConnectionException(
                    f"Git synchronization failed during init: {err_str}"
                )

    def _get_token_url(self, repo_url: str, username: str, token: str) -> str:
        """Inject username and token into HTTPS repo URL securely in memory."""
        if not repo_url.startswith("http://") and not repo_url.startswith("https://"):
            return repo_url
        parsed = urllib.parse.urlsplit(repo_url)
        user_part = (
            f"{urllib.parse.quote_plus(username) if username else 'oauth2'}:{urllib.parse.quote_plus(token)}"
        )
        netloc = f"{user_part}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        return urllib.parse.urlunsplit(
            (parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)
        )

    def upload_files(
        self, remote_folder: str, files: list[Path], local_base_path: Path = None
    ):
        if not self.repo or not self.local_repo_path:
            raise DaoConnectionException(
                "Git: connection not initialized. Call init_connection() first."
            )

        logger.info(
            f"Git: preparing upload of {len(files)} files to folder '{remote_folder}'"
        )

        rel_target_dir = remote_folder.strip("/")
        if rel_target_dir:
            dest_folder = self.local_repo_path / rel_target_dir
        else:
            dest_folder = self.local_repo_path

        os.makedirs(dest_folder, exist_ok=True)
        files_modified = 0

        for file in files:
            if local_base_path and file.is_relative_to(local_base_path):
                rel_path = file.relative_to(local_base_path)
                target_file_path = dest_folder / rel_path
            else:
                target_file_path = dest_folder / file.name

            os.makedirs(target_file_path.parent, exist_ok=True)

            if target_file_path.exists():
                local_md5 = utils.calculate_md5(file)
                remote_md5 = utils.calculate_md5(target_file_path)
                if local_md5 == remote_md5:
                    logger.debug(
                        f"Git: file '{file.name}' already up-to-date, skipping."
                    )
                    continue

            logger.debug(f"Git: copying '{file}' -> '{target_file_path}'")
            shutil.copy2(file, target_file_path)
            files_modified += 1

        try:
            with self.repo.git.custom_environment(**self.git_env):
                add_path = rel_target_dir if rel_target_dir else "."
                self.repo.git.add(add_path)

                status = self.repo.git.status("--porcelain")
                if not status.strip():
                    logger.info(
                        "Git: no changes detected in files, nothing to commit or push."
                    )
                    return

                author = f"{self.author_name} <{self.author_email}>"
                commit_msg = (
                    f"Sync: update {files_modified} file(s) in {remote_folder or '/'}"
                )
                self.repo.git.commit("-m", commit_msg, f"--author={author}")
                logger.debug(f"Git: committed changes with message: '{commit_msg}'")

                auth_repo_url = self.repo_url
                if self.auth_type == "token":
                    auth_repo_url = self._get_token_url(
                        self.repo_url, self.username, self.token
                    )
                    self.repo.git.remote("set-url", "origin", auth_repo_url)

                try:
                    self.repo.git.push("-u", "origin", self.branch)
                    logger.info(f"Git: pushed commit successfully to {self.branch}")
                finally:
                    if self.auth_type == "token":
                        self.repo.git.remote("set-url", "origin", self.repo_url)

        except GitCommandError as e:
            err_str = str(e)
            if self.token and self.token in err_str:
                err_str = err_str.replace(self.token, "********")
            logger.error(f"Git error during commit/push: {err_str}")
            if (
                "Could not resolve host" in err_str
                or "unable to access" in err_str
                or "Connection timed out" in err_str
            ):
                raise NoInternet(f"Failed to push to remote server: {err_str}")
            raise DaoConnectionException(f"Git push failed: {err_str}")

    def download_files(self):
        raise NotImplementedError()
