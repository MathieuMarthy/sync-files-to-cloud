import fnmatch
import logging
import os.path
import tempfile
import zipfile
from pathlib import Path

from src.dao.get_clouddao_from_cloud_enum import get_clouddao_from_cloud_enum
from src.exceptions.DaoException import NoCredentialFileException, NoInternet
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
        if not os.path.exists(self.folder.local_path):
            logging.warning(f"Folder does not exist: '{self.folder.local_path}'")
            return []

        local_path = Path(self.folder.local_path)

        # if it's a file, just return that file
        if local_path.is_file():
            folders_files = [local_path]
        else:
            folders_files = list(local_path.rglob("*"))
        folders_files = [file for file in folders_files if file.is_file()]

        if self.folder.exclude_patterns is None or len(self.folder.exclude_patterns) == 0:
            return folders_files

        # Filter files based on exclude patterns
        filtered_files: list[Path] = []

        for file in folders_files:
            # Check if the file matches any exclude pattern
            relative_path = str(file.relative_to(self.folder.local_path))
            should_exclude = False
            for pattern in self.folder.exclude_patterns:
                if fnmatch.fnmatch(relative_path, pattern):
                    should_exclude = True
                    break

            if not should_exclude:
                filtered_files.append(file)

        return filtered_files

    def _compress_files(self, files_to_compress: list[Path]) -> str:
        # Get the system temp directory
        temp_dir = tempfile.gettempdir()

        # Full path to the zip file
        zip_name = f"{self.folder.name}.zip"
        zip_path = os.path.join(temp_dir, zip_name)

        # Create the zip file
        logging.debug(f"Compressing {len(files_to_compress)} files to '{zip_path}'")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in files_to_compress:
                # Add file with only its basename (not full path)
                zf.write(file, file.relative_to(self.folder.local_path))

        logging.debug("Compression completed")
        return zip_path
