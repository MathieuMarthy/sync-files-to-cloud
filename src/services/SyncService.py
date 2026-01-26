import logging
import os.path
import tempfile
import zipfile
from pathlib import Path

import pathspec

from src.dao.get_clouddao_from_cloud_enum import get_clouddao_from_cloud_enum
from src.exceptions.DaoException import NoInternet
from src.models.sync_parameters import FolderParameter


class SyncService:
    folder: FolderParameter

    def __init__(self, folder: FolderParameter):
        self.folder = folder

    def sync_folder(self):
        logging.info(f"Starting sync for folder: '{self.folder.name}'")

        # Initialize cloud connection
        dao = get_clouddao_from_cloud_enum(self.folder.cloud_provider)
        dao.init_connection()

        # Find files
        files = self._get_files()
        logging.debug(f"Found {len(files)} files to sync")

        if len(files) == 0:
            logging.info("No files to sync. Exiting.")
            return

        # Compress files if needed
        if self.folder.compress:
            files = [self._compress_files(files)]
            local_base_path = None  # No structure preservation needed for zip
        else:
            local_base_path = Path(self.folder.local_path)

        # Upload files
        try:
            dao.upload_files(self.folder.remote_path, files, local_base_path)
            logging.info(f"Sync {len(files)} files for folder: '{self.folder.name}'")
        except NoInternet as e:
            logging.error(f"failed to upload files to the cloud, error: {str(e)}")

    def _get_files(self) -> list[Path]:
        if isinstance(self.folder.local_path, list):
            all_files = []

            for directory in self.folder.local_path:
                all_files.extend(self.__get_file_from_directory(directory))

            return all_files
        elif isinstance(self.folder.local_path, str):
            return self.__get_file_from_directory(self.folder.local_path)

        return []

    def __get_file_from_directory(self, directory: str) -> list[Path]:
        if not os.path.exists(directory):
            logging.warning(f"Folder does not exist: '{directory}'")
            return []

        local_path = Path(directory)

        # if it's a file, just return that file
        if local_path.is_file():
            folders_files = [local_path]
        else:
            folders_files = list(local_path.rglob("*"))
        folders_files = [file for file in folders_files if file.is_file()]

        if (
            self.folder.exclude_patterns is None
            or len(self.folder.exclude_patterns) == 0
        ):
            return folders_files

        # Filter files based on exclude patterns using gitignore syntax
        spec = pathspec.PathSpec.from_lines(
            "gitwildmatch", self.folder.exclude_patterns
        )

        filtered_files = [
            file
            for file in folders_files
            if not spec.match_file(str(file.relative_to(directory)))
        ]

        return filtered_files

    def _compress_files(self, files_to_compress: list[Path]) -> str:
        # Get the system temp directory
        temp_dir = tempfile.gettempdir()

        # Full path to the zip file
        zip_name = f"{self.folder.name}.zip"
        zip_path = os.path.join(temp_dir, zip_name)

        if isinstance(self.folder.local_path, list):
            try:
                common_path = Path(os.path.commonpath(self.folder.local_path))
            except ValueError:
                # No common path (e.g., different drives on Windows), use absolute paths
                logging.warning(
                    "No common path found for directories. Zip archive will store "
                    "absolute paths, which may cause unexpected directory structures "
                    "when extracting."
                )
                common_path = None

        # Create the zip file
        logging.debug(f"Compressing {len(files_to_compress)} files to '{zip_path}'")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in files_to_compress:
                # Add file with only its basename (not full path)
                if isinstance(self.folder.local_path, list):
                    if common_path is not None:
                        zf.write(file, str(file.relative_to(common_path)))
                    else:
                        # Use a sanitized, relative-like path to avoid name collisions
                        arcname = file.as_posix().lstrip("/").replace(":", "_")
                        zf.write(file, arcname)
                else:
                    zf.write(file, str(Path(file).relative_to(self.folder.local_path)))

        logging.debug("Compression completed")
        return zip_path
