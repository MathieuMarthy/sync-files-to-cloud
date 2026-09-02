import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

from src import utils
from src.dao.cloudDAO import CloudDAO
from src.exceptions.DaoException import (
    AuthentificationRequiredException,
    DaoConnectionException,
    NoInternet,
)

logger = logging.getLogger("sync_files_to_cloud")

CREDENTIALS_PATH = "credentials/protondrive_credentials.json"
DEFAULT_CONFLICT_STRATEGY = "replace"
DEFAULT_CLI_PATH = "proton-drive"
DEFAULT_RCLONE_PATH = "rclone"
DEFAULT_RCLONE_REMOTE = "protondrive"


class ProtonDriveCloudDAO(CloudDAO):
    def __init__(self):
        super().__init__()
        self.backend = "official_cli"
        self.cli_path = DEFAULT_CLI_PATH
        self.rclone_path = DEFAULT_RCLONE_PATH
        self.rclone_remote = DEFAULT_RCLONE_REMOTE
        self.conflict_strategy = DEFAULT_CONFLICT_STRATEGY
        self._folder_cache = set(["/my-files", "/devices", "/shared-with-me"])
        self._load_config()


    def _load_config(self):
        """Loads configuration from credentials/protondrive_credentials.json if available."""
        creds_file = utils.path(CREDENTIALS_PATH)
        if not os.path.exists(creds_file):
            logger.debug(
                f"ProtonDrive: No credentials file at {CREDENTIALS_PATH}, using default CLI settings."
            )
            return

        try:
            with open(creds_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            self.backend = config.get("backend", self.backend).lower()
            self.cli_path = config.get("cli_path", self.cli_path)
            self.rclone_path = config.get("rclone_path", self.rclone_path)
            self.rclone_remote = config.get("rclone_remote", self.rclone_remote)
            self.conflict_strategy = config.get(
                "conflict_strategy", self.conflict_strategy
            )
            logger.debug("ProtonDrive: Configuration loaded successfully.")
        except Exception as e:
            logger.warning(
                f"ProtonDrive: Failed to parse credentials file {CREDENTIALS_PATH}: {e}. Using defaults."
            )

    def init_connection(self, can_open_connection_page: bool = False, folder=None):
        """Initializes connection to Proton Drive and verifies authentication.

        Args:
            can_open_connection_page (bool): If True, allows launching interactive login flow.
            folder: Optional folder configuration.
        """
        self._load_config()

        if self.backend == "rclone":
            self._init_rclone_connection(can_open_connection_page)
        else:
            self._init_cli_connection(can_open_connection_page)

    def _init_cli_connection(self, can_open_connection_page: bool = False):
        resolved_bin = shutil.which(self.cli_path)
        if not resolved_bin and not (
            os.path.isfile(self.cli_path) and os.access(self.cli_path, os.X_OK)
        ):
            raise DaoConnectionException(
                f"ProtonDrive: CLI executable '{self.cli_path}' not found in PATH or not executable. "
                f"Please install the Proton Drive CLI or configure 'cli_path' in {CREDENTIALS_PATH}. "
                "See documentation/connect-to-proton-drive.md for setup instructions."
            )

        cmd = [self.cli_path, "filesystem", "list", "/"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise NoInternet("ProtonDrive: Connection check timed out.")
        except Exception as e:
            raise DaoConnectionException(
                f"ProtonDrive: Failed to execute CLI command: {e}"
            )

        if res.returncode != 0:
            err_output = (res.stderr or res.stdout or "").strip()
            err_lower = err_output.lower()

            if any(
                k in err_lower
                for k in [
                    "not logged in",
                    "unauthorized",
                    "unauthenticated",
                    "authentication required",
                    "session expired",
                    "no active session",
                    "login required",
                ]
            ):
                if can_open_connection_page:
                    logger.info("ProtonDrive: Launching interactive login...")
                    try:
                        login_res = subprocess.run([self.cli_path, "auth", "login"])
                        if login_res.returncode != 0:
                            raise DaoConnectionException(
                                "ProtonDrive: Interactive authentication failed or was cancelled."
                            )
                    except Exception as e:
                        raise DaoConnectionException(
                            f"ProtonDrive: Failed to run login command: {e}"
                        )
                else:
                    raise AuthentificationRequiredException(
                        "ProtonDrive: Authentication required. Please run 'proton-drive auth login' or click Reconnect."
                    )
            elif any(
                k in err_lower
                for k in [
                    "could not resolve",
                    "connection refused",
                    "network is unreachable",
                    "no internet",
                    "timed out",
                ]
            ):
                raise NoInternet(
                    f"ProtonDrive: Network error while checking connection: {err_output}"
                )
            else:
                logger.warning(
                    f"ProtonDrive: Status check non-zero return code ({res.returncode}): {err_output}"
                )

        logger.debug("ProtonDrive: Connection and session verified successfully.")

    def _init_rclone_connection(self, can_open_connection_page: bool = False):
        resolved_bin = shutil.which(self.rclone_path)
        if not resolved_bin and not (
            os.path.isfile(self.rclone_path) and os.access(self.rclone_path, os.X_OK)
        ):
            raise DaoConnectionException(
                f"ProtonDrive: Rclone executable '{self.rclone_path}' not found in PATH. "
                "Please install rclone or configure 'rclone_path'."
            )

        cmd = [self.rclone_path, "lsf", f"{self.rclone_remote}:", "--max-depth", "1"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise NoInternet("ProtonDrive (rclone): Connection check timed out.")
        except Exception as e:
            raise DaoConnectionException(
                f"ProtonDrive (rclone): Execution failure: {e}"
            )

        if res.returncode != 0:
            err_output = (res.stderr or res.stdout or "").strip()
            err_lower = err_output.lower()
            if any(
                k in err_lower
                for k in [
                    "could not resolve",
                    "connection refused",
                    "network is unreachable",
                    "dial tcp",
                ]
            ):
                raise NoInternet(
                    f"ProtonDrive (rclone): Network error: {err_output}"
                )
            elif any(
                k in err_lower
                for k in ["unauthorized", "authentication failed", "auth"]
            ):
                raise AuthentificationRequiredException(
                    f"ProtonDrive (rclone): Remote '{self.rclone_remote}' requires authentication: {err_output}"
                )
            else:
                raise DaoConnectionException(
                    f"ProtonDrive (rclone): Failed to list remote '{self.rclone_remote}': {err_output}"
                )

    def _normalize_remote_path(self, remote_folder: str) -> str:
        """Normalizes remote path according to the active backend (official CLI root is /my-files)."""
        clean = remote_folder.strip("/") if remote_folder else ""
        if self.backend == "rclone":
            return f"/{clean}" if clean else "/"

        if not clean:
            return "/my-files"
        if (
            clean.startswith("my-files")
            or clean.startswith("devices")
            or clean.startswith("shared-with-me")
        ):
            return f"/{clean}"
        return f"/my-files/{clean}"


    def _ensure_folder_exists(self, target_folder: str):
        """Ensures that the remote parent folder structure exists on Proton Drive."""
        parts = [p for p in target_folder.split("/") if p]
        if not parts:
            return

        current_path = f"/{parts[0]}"
        for part in parts[1:]:
            folder_path = f"{current_path}/{part}"
            if folder_path not in self._folder_cache:
                info_res = subprocess.run(
                    [self.cli_path, "filesystem", "info", folder_path],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                output = (info_res.stderr or "") + " " + (info_res.stdout or "")
                if info_res.returncode != 0 or "node not found" in output.lower():
                    logger.debug(
                        f"ProtonDrive: Creating remote folder '{folder_path}'..."
                    )
                    create_res = subprocess.run(
                        [
                            self.cli_path,
                            "filesystem",
                            "create-folder",
                            current_path,
                            part,
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if create_res.returncode != 0:
                        err = (
                            create_res.stderr or create_res.stdout or ""
                        ).strip()
                        if "already exists" not in err.lower():
                            logger.warning(
                                f"ProtonDrive: Failed to create folder '{folder_path}': {err}"
                            )
                self._folder_cache.add(folder_path)
            current_path = folder_path

    def upload_files(
        self, remote_folder: str, files: list[Path], local_base_path: Path = None
    ):
        """Uploads files to the specified remote folder on Proton Drive."""
        if not files:
            logger.info("ProtonDrive: No files to upload.")
            return

        normalized_remote = self._normalize_remote_path(remote_folder)
        logger.info(
            f"ProtonDrive: Preparing upload of {len(files)} files to '{normalized_remote}'"
        )

        for file_entry in files:
            file_path = Path(file_entry)
            if not file_path.exists():
                logger.warning(
                    f"ProtonDrive: File '{file_path}' does not exist, skipping."
                )
                continue

            target_folder = self._determine_target_folder(
                file_path, normalized_remote, local_base_path
            )

            if self.backend == "rclone":
                self._upload_single_file_rclone(file_path, target_folder)
            else:
                self._upload_single_file_cli(file_path, target_folder)

    def _determine_target_folder(
        self,
        file: Path,
        remote_folder: str,
        local_base_path: Path = None,
    ) -> str:
        """Determines remote destination folder preserving relative subdirectory structure."""
        if (
            local_base_path
            and isinstance(local_base_path, Path)
            and file.is_relative_to(local_base_path)
        ):
            relative_path = file.relative_to(local_base_path)
            if relative_path.parent != Path("."):
                sub_dir = relative_path.parent.as_posix().strip("/")
                if remote_folder == "/":
                    return f"/{sub_dir}"
                return f"{remote_folder.rstrip('/')}/{sub_dir}"

        return remote_folder

    def _upload_single_file_cli(self, file_path: Path, target_folder: str):
        self._ensure_folder_exists(target_folder)

        cmd = [
            self.cli_path,
            "filesystem",
            "upload",
            "-f",
            self.conflict_strategy,
            "-d",
            "merge",
            str(file_path),
            target_folder,
        ]

        logger.debug(
            f"ProtonDrive: Uploading '{file_path.name}' to '{target_folder}'..."
        )
        try:
            res = subprocess.run(

                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as e:
            raise DaoConnectionException(
                f"ProtonDrive: Error invoking CLI for '{file_path.name}': {e}"
            )

        if res.returncode != 0:
            err_output = (res.stderr or res.stdout or "").strip()
            err_lower = err_output.lower()

            if any(
                k in err_lower
                for k in [
                    "could not resolve",
                    "connection refused",
                    "network is unreachable",
                    "no internet",
                    "connection reset",
                    "timed out",
                ]
            ):
                raise NoInternet(
                    f"ProtonDrive: Network error uploading '{file_path.name}': {err_output}"
                )
            elif any(
                k in err_lower
                for k in [
                    "not logged in",
                    "unauthorized",
                    "authentication required",
                    "session expired",
                    "login required",
                ]
            ):
                raise AuthentificationRequiredException(
                    f"ProtonDrive: Authentication expired during upload of '{file_path.name}': {err_output}"
                )
            else:
                raise DaoConnectionException(
                    f"ProtonDrive: Failed to upload '{file_path.name}': {err_output}"
                )

        logger.debug(f"ProtonDrive: Successfully uploaded '{file_path.name}'.")

    def _upload_single_file_rclone(self, file_path: Path, target_folder: str):
        remote_dest = (
            f"{self.rclone_remote}:{target_folder.lstrip('/')}/{file_path.name}"
        )
        cmd = [self.rclone_path, "copyto", str(file_path), remote_dest]

        logger.debug(
            f"ProtonDrive (rclone): Copying '{file_path.name}' -> '{remote_dest}'..."
        )
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as e:
            raise DaoConnectionException(
                f"ProtonDrive (rclone): Execution error for '{file_path.name}': {e}"
            )

        if res.returncode != 0:
            err_output = (res.stderr or res.stdout or "").strip()
            err_lower = err_output.lower()

            if any(
                k in err_lower
                for k in [
                    "could not resolve",
                    "connection refused",
                    "network is unreachable",
                    "dial tcp",
                ]
            ):
                raise NoInternet(
                    f"ProtonDrive (rclone): Network error uploading '{file_path.name}': {err_output}"
                )
            elif any(
                k in err_lower
                for k in ["unauthorized", "authentication failed", "auth"]
            ):
                raise AuthentificationRequiredException(
                    f"ProtonDrive (rclone): Auth error uploading '{file_path.name}': {err_output}"
                )
            else:
                raise DaoConnectionException(
                    f"ProtonDrive (rclone): Upload error for '{file_path.name}': {err_output}"
                )

    def download_files(self):
        raise NotImplementedError("ProtonDrive download_files is not implemented.")
